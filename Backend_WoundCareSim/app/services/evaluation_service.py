from typing import Dict, List, Any, Optional

from app.rag.retriever import retrieve_with_rag
from app.core.coordinator import Coordinator
from app.services.session_manager import SessionManager
from app.core.state_machine import Step

from app.utils.mcq_evaluator import MCQEvaluator
from app.utils.schema import EvaluatorResponse
from app.services.conversation_manager import ConversationManager
from app.utils.feedback_schema import Feedback

from app.agents.feedback_narrator_agent import FeedbackNarratorAgent
from app.utils.scoring import aggregate_scores


class EvaluationService:

    def __init__(
        self,
        coordinator: Coordinator,
        session_manager: SessionManager,
        staff_nurse_agent: Optional[Any] = None,
        feedback_narrator_agent: Optional[FeedbackNarratorAgent] = None,
    ):
        self.coordinator = coordinator
        self.session_manager = session_manager
        self.mcq_evaluator = MCQEvaluator()
        self.conversation_manager = ConversationManager()
        self.staff_nurse_agent = staff_nurse_agent
        self.feedback_narrator_agent = feedback_narrator_agent

    # ------------------------------------------------
    # Context Preparation
    # ------------------------------------------------
    async def prepare_agent_context(
        self,
        session_id: str,
        step: str
    ) -> Dict[str, Any]:

        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        scenario_metadata = session["scenario_metadata"]

        transcript = ""
        action_events: List[Dict[str, Any]] = []

        if step == Step.HISTORY.value:
            transcript = self.conversation_manager.get_aggregated_transcript(
                session_id=session_id,
                step=step
            )

        elif step == Step.CLEANING_AND_DRESSING.value:
            action_events = session.get("action_events", [])

        rag_query_map = {
            Step.HISTORY.value:
                "patient history taking guidelines nursing communication assessment questions",
            Step.CLEANING_AND_DRESSING.value:
                "wound cleaning and dressing preparation procedure protocol hand hygiene aseptic technique",
        }

        rag_context = ""
        if step in rag_query_map:
            rag = await retrieve_with_rag(
                query=rag_query_map[step],
                scenario_id=session["scenario_id"]
            )
            rag_context = rag.get("text", "")

        return {
            "step": step,
            "scenario_metadata": scenario_metadata,
            "transcript": transcript,
            "action_events": action_events,
            "rag_context": rag_context
        }

    # ------------------------------------------------
    # Aggregation + Deterministic Scoring + Narration
    # ------------------------------------------------
    async def aggregate_evaluations(
        self,
        session_id: str,
        evaluator_outputs: List[EvaluatorResponse],
        student_mcq_answers: Optional[Dict[str, str]] = None,
        student_message_to_nurse: Optional[str] = None
    ) -> Dict[str, Any]:

        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        current_step = Step(session["current_step"])

        # ------------------------------------------------
        # CLEANING_AND_DRESSING → No Final Evaluation
        # ------------------------------------------------
        if current_step == Step.CLEANING_AND_DRESSING:
            payload = {
                "step": current_step.value,
                "scores": None,
                "narrated_feedback": None,
                "raw_feedback": [],
            }

            self.session_manager.store_last_evaluation(
                session_id=session_id,
                evaluation=payload
            )

            return payload

        # ------------------------------------------------
        # ASSESSMENT → MCQ Only
        # ------------------------------------------------
        if current_step == Step.ASSESSMENT:
            questions = session["scenario_metadata"].get(
                "assessment_questions", []
            )

            if not questions:
                mcq_result = {
                    "total_questions": 0,
                    "correct_count": 0,
                    "score": 0.0,
                    "feedback": [],
                    "summary": "No MCQ questions available"
                }
            else:
                mcq_result = self.mcq_evaluator.validate_mcq_answers(
                    student_answers=student_mcq_answers or {},
                    assessment_questions=questions
                )

            payload = {
                "step": current_step.value,
                "mcq_result": mcq_result,
                "scores": None,
                "narrated_feedback": None,
                "raw_feedback": [],
            }

            self.session_manager.store_last_evaluation(
                session_id=session_id,
                evaluation=payload
            )

            return payload

        # ------------------------------------------------
        # HISTORY → Structured Rubric Scoring
        # ------------------------------------------------

        # Deterministic scoring (NEW)
        scores = aggregate_scores(
            evaluations=evaluator_outputs,
            current_step=current_step.value
        )

        # ----------------------------------------------
        # Build raw feedback (for narration only)
        # ----------------------------------------------
        raw_feedback_items: List[Dict[str, Any]] = []

        for ev in evaluator_outputs:
            parts = []

            if ev.strengths:
                parts.append("Strengths: " + ", ".join(ev.strengths))

            if ev.issues_detected:
                parts.append("Areas for improvement: " + ", ".join(ev.issues_detected))

            if ev.explanation:
                parts.append(ev.explanation)

            raw_feedback_items.append(
                Feedback(
                    text=" ".join(parts),
                    speaker="system",
                    category=(
                        "communication"
                        if ev.agent_name == "CommunicationAgent"
                        else "knowledge"
                    ),
                    timing="post_step"
                ).to_dict()
            )

        # ----------------------------------------------
        # Generate narrated feedback (LLM)
        # ----------------------------------------------
        narrated_feedback_dict = None

        if self.feedback_narrator_agent and raw_feedback_items:
            try:
                narrated_feedback_obj = await self.feedback_narrator_agent.narrate(
                    raw_feedback=raw_feedback_items,
                    step=current_step.value
                )
                if narrated_feedback_obj:
                    narrated_feedback_dict = narrated_feedback_obj.model_dump()
            except Exception as e:
                print(f"⚠ Narration failed: {e}")
                narrated_feedback_dict = {
                    "speaker": "system",
                    "step": current_step.value,
                    "message_text": " ".join(
                        item["text"] for item in raw_feedback_items
                    )
                }

        # ----------------------------------------------
        # Final Payload
        # ----------------------------------------------
        payload = {
            "step": current_step.value,
            "scores": scores,
            "narrated_feedback": narrated_feedback_dict,
            "raw_feedback": raw_feedback_items,
        }

        self.session_manager.store_last_evaluation(
            session_id=session_id,
            evaluation=payload
        )

        return payload
