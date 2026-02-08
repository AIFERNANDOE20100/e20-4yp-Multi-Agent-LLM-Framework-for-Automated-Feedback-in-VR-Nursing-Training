from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.services.session_manager import SessionManager
from app.services.evaluation_service import EvaluationService
from app.core.coordinator import Coordinator
from app.core.state_machine import Step
from app.services.action_event_service import ActionEventService
from app.rag.retriever import retrieve_with_rag

from app.agents.patient_agent import PatientAgent
from app.agents.communication_agent import CommunicationAgent
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.clinical_agent import ClinicalAgent
from app.agents.staff_nurse_agent import StaffNurseAgent
from app.agents.feedback_narrator_agent import FeedbackNarratorAgent

from app.utils.mcq_evaluator import MCQEvaluator

router = APIRouter(prefix="/session", tags=["Session"])

# -------------------------------------------------
# Core services (singletons)
# -------------------------------------------------

session_manager = SessionManager()
coordinator = Coordinator()

evaluation_service = EvaluationService(
    coordinator=coordinator,
    session_manager=session_manager,
    staff_nurse_agent=StaffNurseAgent(),
    feedback_narrator_agent=FeedbackNarratorAgent(),
)

action_event_service = ActionEventService(session_manager)

patient_agent = PatientAgent()
conversation_manager = evaluation_service.conversation_manager

communication_agent = CommunicationAgent()
knowledge_agent = KnowledgeAgent()
clinical_agent = ClinicalAgent()
mcq_evaluator = MCQEvaluator()

# -------------------------------------------------
# Request models
# -------------------------------------------------

class StartSessionRequest(BaseModel):
    scenario_id: str
    student_id: str


class MessageInput(BaseModel):
    session_id: str
    message: str


class StepInput(BaseModel):
    session_id: str
    step: str
    user_input: Optional[str] = None
    student_mcq_answers: Optional[Dict[str, str]] = None


class StaffNurseInput(BaseModel):
    session_id: str
    message: str


class MCQAnswerInput(BaseModel):
    session_id: str
    question_id: str
    answer: str


class ActionInput(BaseModel):
    session_id: str
    action_type: str
    metadata: Optional[Dict[str, Any]] = None


class VerifyMaterialInput(BaseModel):
    session_id: str
    material_type: str  # "solution" or "dressing"
    material_name: str
    expiry_date: str
    package_condition: str  # "intact", "damaged", etc.


# -------------------------------------------------
# Routes
# -------------------------------------------------

@router.post("/start")
def start_session(payload: StartSessionRequest):
    """
    Start a new training session.
    """
    session_id = session_manager.create_session(
        scenario_id=payload.scenario_id,
        student_id=payload.student_id
    )
    return {"session_id": session_id}


@router.get("/{session_id}")
def get_session_info(session_id: str):
    """
    Get current session state and information.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "scenario_id": session["scenario_id"],
        "student_id": session["student_id"],
        "current_step": session["current_step"],
        "scenario_metadata": session["scenario_metadata"],
        "last_evaluation": session.get("last_evaluation"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at")
    }


@router.post("/message")
async def send_message(payload: MessageInput):
    """
    Multi-turn student ↔ patient conversation.
    HISTORY step only.
    """
    session = session_manager.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["current_step"] != Step.HISTORY.value:
        raise HTTPException(
            status_code=400,
            detail="Conversation allowed only during HISTORY step"
        )

    scenario_meta = session["scenario_metadata"]
    patient_history = scenario_meta["patient_history"]

    conversation_manager.add_turn(
        payload.session_id,
        Step.HISTORY.value,
        "student",
        payload.message
    )

    response = await patient_agent.respond(
        patient_history=patient_history,
        conversation_history=conversation_manager.conversations[payload.session_id][Step.HISTORY.value],
        student_message=payload.message
    )

    conversation_manager.add_turn(
        payload.session_id,
        Step.HISTORY.value,
        "patient",
        response
    )

    return {"patient_response": response}


@router.post("/staff-nurse")
async def ask_staff_nurse(payload: StaffNurseInput):
    """
    Ask the staff nurse for guidance (available at any time).
    
    The staff nurse provides high-level guidance only.
    Does not evaluate, approve, or block the student.
    
    NOTE: For material verification during cleaning_and_dressing step,
    use the /verify-material endpoint instead to ensure verification is tracked as an action.
    """
    session = session_manager.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    current_step = session["current_step"]
    
    # Determine next step
    try:
        from app.core.state_machine import next_step as get_next_step
        next_step_enum = get_next_step(Step(current_step))
        next_step_str = next_step_enum.value
    except ValueError:
        next_step_str = None
    
    staff_nurse = StaffNurseAgent()
    response = await staff_nurse.respond(
        student_input=payload.message,
        current_step=current_step,
        next_step=next_step_str
    )
    
    return {
        "staff_nurse_response": response,
        "current_step": current_step
    }


@router.post("/verify-material")
async def verify_material(payload: VerifyMaterialInput):
    """
    Student requests staff nurse to verify cleaning solution or dressing packet.
    
    This is an ACTION endpoint (not just conversation).
    Records the verification action AND provides nurse verbal feedback.
    
    Use this endpoint instead of /staff-nurse for verification to ensure
    the action is properly tracked for evaluation.
    
    Args:
        material_type: "solution" or "dressing"
        material_name: What the student identifies it as
        expiry_date: Date stated by student
        package_condition: "intact", "damaged", etc.
    
    Returns:
        - Nurse's verbal verification response
        - Action recorded confirmation
        - Real-time feedback
    """
    session = session_manager.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    current_step = session["current_step"]
    
    # Only allow verification during CLEANING_AND_DRESSING step
    if current_step != Step.CLEANING_AND_DRESSING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Material verification only allowed during cleaning_and_dressing step"
        )
    
    # Generate nurse verbal response
    staff_nurse = StaffNurseAgent()
    nurse_response = await staff_nurse.verify_material(
        material_type=payload.material_type,
        material_name=payload.material_name,
        expiry_date=payload.expiry_date,
        package_condition=payload.package_condition
    )
    
    # Record as action with metadata
    action_type = f"action_verify_{payload.material_type}"
    
    # Get current action events BEFORE recording this one (for real-time feedback)
    performed_actions = session.get("action_events", [])
    
    # Retrieve RAG guidelines for real-time evaluation
    rag_result = await retrieve_with_rag(
        query="wound cleaning and dressing preparation steps sequence prerequisites verification",
        scenario_id=session["scenario_id"]
    )
    
    rag_guidelines = rag_result.get("text", "")
    
    # Get real-time feedback
    real_time_feedback = await clinical_agent.get_real_time_feedback(
        action_type=action_type,
        performed_actions=performed_actions,
        rag_guidelines=rag_guidelines
    )
    
    # Record the verification action
    result = action_event_service.record_action(
        session_id=payload.session_id,
        action_type=action_type,
        step=current_step,
        metadata={
            "material_type": payload.material_type,
            "material_name": payload.material_name,
            "expiry_date": payload.expiry_date,
            "package_condition": payload.package_condition,
            "nurse_approval": nurse_response
        }
    )
    
    # Print to terminal for debugging
    print("\n" + "="*60)
    print(f"MATERIAL VERIFICATION - Type: {payload.material_type}")
    print("="*60)
    print(f"Material: {payload.material_name}")
    print(f"Expiry: {payload.expiry_date}")
    print(f"Condition: {payload.package_condition}")
    print(f"Nurse Response: {nurse_response}")
    print(f"Feedback Status: {real_time_feedback.get('status')}")
    print(f"Feedback Message: {real_time_feedback.get('message')}")
    print("="*60 + "\n")
    
    return {
        "nurse_response": nurse_response,
        "action_recorded": True,
        "action_type": action_type,
        "timestamp": result.get("timestamp"),
        "feedback": {
            "message": real_time_feedback.get("message"),
            "status": real_time_feedback.get("status"),
            "can_proceed": real_time_feedback.get("can_proceed")
        }
    }


@router.post("/action")
async def record_action(payload: ActionInput):
    """
    Record a preparation action with REAL-TIME FEEDBACK using RAG guidelines.
    
    For CLEANING_AND_DRESSING step:
    1. Records the action
    2. Retrieves RAG guidelines for this step
    3. Provides immediate, contextual feedback based on:
       - What actions have been completed
       - What the current action is
       - What prerequisites might be missing (ALL of them, not just previous)
    
    Returns actionable real-time feedback to guide the student.
    
    NOTE: For verification actions (verify solution/dressing), 
    use /verify-material endpoint instead.
    """
    session = session_manager.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    current_step = session["current_step"]
    
    # Only allow actions for CLEANING_AND_DRESSING step
    if current_step != Step.CLEANING_AND_DRESSING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Actions not allowed in {current_step} step"
        )
    
    # Get current action events BEFORE recording this one
    performed_actions = session.get("action_events", [])
    
    # Retrieve RAG guidelines for real-time evaluation
    rag_result = await retrieve_with_rag(
        query="wound cleaning and dressing preparation steps sequence prerequisites required actions",
        scenario_id=session["scenario_id"]
    )
    
    rag_guidelines = rag_result.get("text", "")
    
    # Get real-time feedback BEFORE recording (to check prerequisites)
    real_time_feedback = await clinical_agent.get_real_time_feedback(
        action_type=payload.action_type,
        performed_actions=performed_actions,
        rag_guidelines=rag_guidelines
    )
    
    # Record the action (regardless of feedback - no blocking)
    result = action_event_service.record_action(
        session_id=payload.session_id,
        action_type=payload.action_type,
        step=current_step,
        metadata=payload.metadata
    )
    
    # Print to terminal for debugging (agent-level feedback)
    print("\n" + "="*60)
    print(f"REAL-TIME FEEDBACK - Action: {payload.action_type}")
    print("="*60)
    print(f"Status: {real_time_feedback.get('status')}")
    print(f"Message: {real_time_feedback.get('message')}")
    if real_time_feedback.get('missing_actions'):
        print(f"Missing Prerequisites: {real_time_feedback.get('missing_actions')}")
    print(f"Can Proceed: {real_time_feedback.get('can_proceed')}")
    print(f"Total Actions: {real_time_feedback.get('total_actions_so_far')}")
    print("="*60 + "\n")
    
    # Return simplified feedback to student (what they see in UI)
    return {
        "action_recorded": True,
        "action_type": payload.action_type,
        "step": current_step,
        "timestamp": result.get("timestamp"),
        "feedback": {
            "message": real_time_feedback.get("message"),
            "status": real_time_feedback.get("status"),
            "can_proceed": real_time_feedback.get("can_proceed"),
            "missing_actions": real_time_feedback.get("missing_actions", [])
        }
    }


@router.post("/mcq-answer")
def answer_mcq_question(payload: MCQAnswerInput):
    """
    Evaluate a single MCQ answer immediately.
    
    Returns immediate feedback without LLM evaluation.
    """
    session = session_manager.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["current_step"] != Step.ASSESSMENT.value:
        raise HTTPException(
            status_code=400,
            detail="MCQ answers allowed only during ASSESSMENT step"
        )
    
    # Get the question from scenario metadata
    questions = session["scenario_metadata"].get("assessment_questions", [])
    question = next((q for q in questions if q.get("id") == payload.question_id), None)
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Check if answer is correct
    correct_answer = question.get("correct_answer")
    is_correct = payload.answer == correct_answer
    
    # Store the answer in session for final evaluation
    if "mcq_answers" not in session:
        session["mcq_answers"] = {}
    session["mcq_answers"][payload.question_id] = payload.answer
    
    # Print to terminal for debugging
    print("\n" + "="*60)
    print(f"MCQ ANSWER - Question: {payload.question_id}")
    print("="*60)
    print(f"Question: {question.get('question')}")
    print(f"Student Answer: {payload.answer}")
    print(f"Correct Answer: {correct_answer}")
    print(f"Result: {'✓ CORRECT' if is_correct else '✗ INCORRECT'}")
    print("="*60 + "\n")
    
    return {
        "question_id": payload.question_id,
        "is_correct": is_correct,
        "explanation": question.get("explanation", "No explanation provided."),
        "status": "correct" if is_correct else "incorrect"
    }


@router.post("/step")
async def run_step(payload: StepInput):
    """
    Complete current step and get comprehensive feedback.
    
    Flow:
    1. Run evaluator agents (only for HISTORY step)
    2. Aggregate evaluations into scores + raw feedback
    3. Generate narrated feedback paragraph (only for HISTORY step)
    4. Return BOTH to client:
       - HISTORY: narrated_feedback + score (for student UI)
       - ASSESSMENT: mcq_result only (no narration)
       - CLEANING_AND_DRESSING: summary only (no evaluation)
       - agent_feedback (printed to terminal for debugging)
    5. Advance to next step
    """
    session = session_manager.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    current_step = session["current_step"]

    if payload.step != current_step:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step. Current step is '{current_step}'."
        )

    # ---------------------------------------------
    # Step-specific evaluation
    # ---------------------------------------------
    evaluator_outputs = []

    if current_step == Step.HISTORY.value:
        # Prepare evaluation context
        context = await evaluation_service.prepare_agent_context(
            session_id=payload.session_id,
            step=current_step
        )
        
        # Run both communication and knowledge agents
        evaluator_outputs.append(
            await communication_agent.evaluate(
                current_step=current_step,
                student_input=context["transcript"],
                scenario_metadata=context["scenario_metadata"],
                rag_response=context["rag_context"]
            )
        )
        evaluator_outputs.append(
            await knowledge_agent.evaluate(
                current_step=current_step,
                student_input=context["transcript"],
                scenario_metadata=context["scenario_metadata"],
                rag_response=context["rag_context"]
            )
        )

    elif current_step == Step.ASSESSMENT.value:
        # ASSESSMENT step uses MCQ-only evaluation (no agents)
        pass

    elif current_step == Step.CLEANING_AND_DRESSING.value:
        # NO FINAL EVALUATION for this step
        # Real-time feedback was sufficient
        pass

    # ---------------------------------------------
    # Print agent feedback to terminal (for debugging)
    # Only if we have evaluator outputs
    # ---------------------------------------------
    if evaluator_outputs:
        print("\n" + "="*80)
        print(f"AGENT EVALUATIONS - Step: {current_step}")
        print("="*80)
        for ev in evaluator_outputs:
            print(f"\n--- {ev.agent_name} ---")
            print(f"Verdict: {ev.verdict} (Confidence: {ev.confidence})")
            print(f"Strengths: {ev.strengths}")
            print(f"Issues: {ev.issues_detected}")
            print(f"Explanation: {ev.explanation}")
        print("="*80 + "\n")

    # ---------------------------------------------
    # Aggregate + narrate feedback
    # ---------------------------------------------
    if current_step == Step.ASSESSMENT.value:
        mcq_answers = session.get("mcq_answers", payload.student_mcq_answers or {})
    else:
        mcq_answers = payload.student_mcq_answers
    
    evaluation = await evaluation_service.aggregate_evaluations(
        session_id=payload.session_id,
        evaluator_outputs=evaluator_outputs,
        student_mcq_answers=mcq_answers,
        student_message_to_nurse=payload.user_input
    )

    # ---------------------------------------------
    # Print final scores to terminal (for debugging)
    # Only if we have scores
    # ---------------------------------------------
    if evaluation.get('scores'):
        print("\n" + "="*80)
        print(f"FINAL EVALUATION SCORES - Step: {current_step}")
        print("="*80)
        print(f"Step Quality Indicator: {evaluation.get('scores', {}).get('step_quality_indicator')}")
        print(f"Interpretation: {evaluation.get('scores', {}).get('interpretation')}")
        print(f"Agent Scores: {evaluation.get('scores', {}).get('agent_scores')}")
        print("="*80 + "\n")
    
    if evaluation.get('mcq_result'):
        mcq = evaluation['mcq_result']
        print("\n" + "="*80)
        print(f"MCQ RESULTS - Step: {current_step}")
        print("="*80)
        print(f"Correct: {mcq.get('correct_count')}/{mcq.get('total_questions')}")
        print(f"Score: {mcq.get('score')}")
        print(f"Summary: {mcq.get('summary')}")
        print("="*80 + "\n")

    # ---------------------------------------------
    # Cleanup: Clear step-specific data after evaluation
    # ---------------------------------------------
    if current_step == Step.HISTORY.value:
        conversation_manager.clear_step(payload.session_id, Step.HISTORY.value)
    
    elif current_step == Step.ASSESSMENT.value:
        session = session_manager.get_session(payload.session_id)
        if session:
            session["mcq_answers"] = {}
    
    elif current_step == Step.CLEANING_AND_DRESSING.value:
        # Clear action events
        session = session_manager.get_session(payload.session_id)
        if session:
            session["action_events"] = []

    # ---------------------------------------------
    # Advance step (always allowed)
    # ---------------------------------------------
    next_step = session_manager.advance_step(payload.session_id)

    # ---------------------------------------------
    # Return STUDENT-FACING feedback only
    # Agent feedback was printed to terminal
    # ---------------------------------------------
    
    # For CLEANING_AND_DRESSING step, provide summary
    if current_step == Step.CLEANING_AND_DRESSING.value:
        completed_count = len(session.get("action_events", []))
        return {
            "session_id": payload.session_id,
            "current_step": current_step,
            "next_step": next_step,
            "summary": {
                "message": "Preparation step completed. Review real-time feedback for details.",
                "actions_completed": completed_count,
                "expected_actions": 9
            }
        }
    
    # For ASSESSMENT step, only return MCQ results (no narration)
    if current_step == Step.ASSESSMENT.value:
        return {
            "session_id": payload.session_id,
            "current_step": current_step,
            "next_step": next_step,
            "mcq_result": evaluation.get("mcq_result")
        }
    
    # For HISTORY step, provide narrated feedback + score
    return {
        "session_id": payload.session_id,
        "current_step": current_step,
        "next_step": next_step,
        "feedback": {
            "narrated_feedback": evaluation.get("narrated_feedback"),
            "score": evaluation.get("scores", {}).get("step_quality_indicator"),
            "interpretation": evaluation.get("scores", {}).get("interpretation")
        }
    }
