import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.core.coordinator import Coordinator
from app.services.evaluation_service import EvaluationService
from app.services.session_manager import SessionManager
from app.services.action_event_service import ActionEventService

from app.agents.communication_agent import CommunicationAgent
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.clinical_agent import ClinicalAgent
from app.agents.patient_agent import PatientAgent
from app.agents.staff_nurse_agent import StaffNurseAgent


# -------------------------------------------------
# Logging setup
# -------------------------------------------------
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


async def run_full_system_test():
    """
    Manual end-to-end system validation (Week-8).

    VALIDATES:
    - Multi-turn history taking with real patient responses
    - Deterministic history completeness feedback
    - Staff nurse supervision interaction
    - Action-event ingestion
    - Feedback-only evaluation (no enforcement)
    """

    scenario_id = "week6_mock_scenario"
    student_id = "manual_test_student"

    print("\n================================================")
    print(" FULL SYSTEM MANUAL TEST (Week-8)")
    print("================================================\n")

    log = {
        "scenario_id": scenario_id,
        "student_id": student_id,
        "started_at": datetime.utcnow().isoformat(),
        "steps": []
    }

    # -------------------------------------------------
    # Core services
    # -------------------------------------------------
    session_manager = SessionManager()
    coordinator = Coordinator()

    staff_nurse_agent = StaffNurseAgent()

    evaluation_service = EvaluationService(
        coordinator=coordinator,
        session_manager=session_manager,
        staff_nurse_agent=staff_nurse_agent
    )

    action_service = ActionEventService(session_manager)
    patient_agent = PatientAgent()

    agents = [
        CommunicationAgent(),
        KnowledgeAgent(),
        ClinicalAgent()
    ]

    # -------------------------------------------------
    # Create session
    # -------------------------------------------------
    session_id = session_manager.create_session(
        scenario_id=scenario_id,
        student_id=student_id
    )

    print(f"[SESSION CREATED] {session_id}")

    scenario_meta = session_manager.get_session(session_id)["scenario_metadata"]
    patient_history = scenario_meta.get("patient_history", {})

    # =================================================
    # HISTORY – Multi-turn conversation
    # =================================================
    print("\n================ HISTORY =================")

    conversation = [
        "Hello, I am a nursing student. Can you confirm your name?",
        "Do you have any allergies?",
        "Can you tell me about the surgery you had?"
    ]

    for msg in conversation:
        evaluation_service.conversation_manager.add_turn(
            session_id, "HISTORY", "student", msg
        )
        print("[STUDENT]", msg)

        conversation_history = evaluation_service.conversation_manager.conversations[
            session_id
        ]["HISTORY"]

        patient_response = await patient_agent.respond(
            patient_history=patient_history,
            conversation_history=conversation_history,
            student_message=msg
        )

        print("[PATIENT]", patient_response)

        evaluation_service.conversation_manager.add_turn(
            session_id, "HISTORY", "patient", patient_response
        )

    # ---- Evaluate HISTORY ----
    context = await evaluation_service.prepare_agent_context(
        session_id=session_id,
        step="HISTORY"
    )

    evaluator_outputs = []
    for agent in agents:
        result = await agent.evaluate(
            current_step="HISTORY",
            student_input=context["transcript"],
            scenario_metadata=context["scenario_metadata"],
            rag_response=context["rag_context"]
        )
        evaluator_outputs.append(result)
        print(f"{result.agent_name}: {result.verdict}")

    aggregated = await evaluation_service.aggregate_evaluations(
        session_id=session_id,
        evaluator_outputs=evaluator_outputs
    )

    log["steps"].append({
        "step": "HISTORY",
        "conversation": context["transcript"],
        "feedback": aggregated,
        "timestamp": datetime.utcnow().isoformat()
    })

    # =================================================
    # STAFF NURSE – Supervision request (Week-8)
    # =================================================
    print("\n================ STAFF NURSE =================")

    student_request = "May I proceed with the wound care under your supervision?"

    staff_nurse_reply = await staff_nurse_agent.respond(
        student_input=student_request,
        scenario_metadata=scenario_meta
    )

    print("[STUDENT]", student_request)
    print("[STAFF NURSE]", staff_nurse_reply)

    log["steps"].append({
        "step": "STAFF_NURSE",
        "student_request": student_request,
        "staff_nurse_response": staff_nurse_reply,
        "timestamp": datetime.utcnow().isoformat()
    })

    # =================================================
    # ASSESSMENT – MCQs
    # =================================================
    print("\n================ ASSESSMENT =================")

    student_mcq_answers = {
        "q1": "Remove the old dressing",
        "q2": "Dry wound surface"
    }

    context = await evaluation_service.prepare_agent_context(
        session_id=session_id,
        step="ASSESSMENT"
    )

    evaluator_outputs = []
    for agent in agents:
        result = await agent.evaluate(
            current_step="ASSESSMENT",
            student_input="Assessment completed.",
            scenario_metadata=context["scenario_metadata"],
            rag_response=context["rag_context"]
        )
        evaluator_outputs.append(result)

    aggregated = await evaluation_service.aggregate_evaluations(
        session_id=session_id,
        evaluator_outputs=evaluator_outputs,
        student_mcq_answers=student_mcq_answers
    )

    log["steps"].append({
        "step": "ASSESSMENT",
        "mcq_result": aggregated.get("mcq_result"),
        "feedback": aggregated,
        "timestamp": datetime.utcnow().isoformat()
    })

    # =================================================
    # CLEANING – Action events
    # =================================================
    print("\n================ CLEANING =================")

    actions = ["SKIP_HAND_WASH", "CLEAN_WOUND"]

    for act in actions:
        action_service.record_action(
            session_id=session_id,
            action_type=act,
            step="CLEANING"
        )
        print("[ACTION]", act)

    context = await evaluation_service.prepare_agent_context(
        session_id=session_id,
        step="CLEANING"
    )

    evaluator_outputs = []
    for agent in agents:
        result = await agent.evaluate(
            current_step="CLEANING",
            student_input="",
            scenario_metadata=context["scenario_metadata"],
            rag_response=context["rag_context"]
        )
        evaluator_outputs.append(result)

    aggregated = await evaluation_service.aggregate_evaluations(
        session_id=session_id,
        evaluator_outputs=evaluator_outputs
    )

    log["steps"].append({
        "step": "CLEANING",
        "actions": context["action_events"],
        "feedback": aggregated,
        "timestamp": datetime.utcnow().isoformat()
    })

    # =================================================
    # DRESSING – Action events
    # =================================================
    print("\n================ DRESSING =================")

    actions = ["APPLY_DRESSING", "SECURE_BANDAGE"]

    for act in actions:
        action_service.record_action(
            session_id=session_id,
            action_type=act,
            step="DRESSING"
        )
        print("[ACTION]", act)

    context = await evaluation_service.prepare_agent_context(
        session_id=session_id,
        step="DRESSING"
    )

    evaluator_outputs = []
    for agent in agents:
        result = await agent.evaluate(
            current_step="DRESSING",
            student_input="",
            scenario_metadata=context["scenario_metadata"],
            rag_response=context["rag_context"]
        )
        evaluator_outputs.append(result)

    aggregated = await evaluation_service.aggregate_evaluations(
        session_id=session_id,
        evaluator_outputs=evaluator_outputs
    )

    log["steps"].append({
        "step": "DRESSING",
        "actions": context["action_events"],
        "feedback": aggregated,
        "timestamp": datetime.utcnow().isoformat()
    })

    # -------------------------------------------------
    # Save log
    # -------------------------------------------------
    log["finished_at"] = datetime.utcnow().isoformat()
    log_path = LOG_DIR / f"manual_test_week8_{session_id}.json"

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

    print("\n================================================")
    print(" WEEK-8 MANUAL SYSTEM TEST COMPLETE")
    print(f" JSON LOG SAVED → {log_path}")
    print("================================================\n")


# -------------------------------------------------
# Entry point
# -------------------------------------------------
if __name__ == "__main__":
    asyncio.run(run_full_system_test())
