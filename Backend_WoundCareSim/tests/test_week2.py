import pytest
from fastapi.testclient import TestClient

# Our app
from app.main import app

# Core modules
from app.core.state_machine import Step, next_step, validate_action
from app.core.coordinator import coordinate

# Agents
from app.agents.communication_agent import CommunicationAgent
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.clinical_agent import ClinicalAgent

# RAG + services
from app.rag.vector_client import VectorClient
from app.rag.retriever import Retriever
from app.services.scenario_loader import ScenarioLoader
from app.services.session_manager import SessionManager
from app.services.evaluation_service import EvaluationService


client = TestClient(app)

# ---------------------------------------------------------
# 1. STATE MACHINE TESTS
# ---------------------------------------------------------

def test_state_machine_forward_transitions():
    assert next_step(Step.HISTORY) == Step.ASSESSMENT
    assert next_step(Step.ASSESSMENT) == Step.CLEANING
    assert next_step(Step.CLEANING) == Step.DRESSING
    assert next_step(Step.DRESSING) == Step.COMPLETED

    with pytest.raises(ValueError):
        next_step(Step.COMPLETED)


def test_validate_action():
    assert validate_action(Step.HISTORY, "voice_transcript")
    assert validate_action(Step.ASSESSMENT, "mcq_answer")
    assert not validate_action(Step.HISTORY, "visual_assessment")


# ---------------------------------------------------------
# 2. COORDINATOR AGGREGATION
# ---------------------------------------------------------

def test_coordinator_aggregation():
    sample = [
        {"agent": "communication", "confidence": 0.8, "score": 0.7, "rationale": "ok"},
        {"agent": "clinical", "confidence": 0.9, "score": 0.9, "rationale": "great"}
    ]
    result = coordinate(sample)

    assert "final_score" in result
    assert result["final_score"] == pytest.approx((0.7 + 0.9) / 2, rel=1e-3)
    assert "final_feedback" in result
    assert "actions" in result
    assert "confidences" in result


# ---------------------------------------------------------
# 3. AGENT EVALUATION TESTS
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_communication_agent():
    agent = CommunicationAgent()
    out = await agent.evaluate({
        "step": "history",
        "transcript": "Hello I am here to assess you, may I check the wound? Thank you.",
        "actions": []
    })

    assert out.agent == "communication"
    assert 0 <= out.score <= 1
    assert out.confidence >= 0
    assert isinstance(out.suggested_actions, list)


@pytest.mark.asyncio
async def test_knowledge_agent():
    agent = KnowledgeAgent()
    out = await agent.evaluate({
        "step": "history",
        "transcript": "Patient has diabetes and allergy to penicillin.",
        "mcq_answers": {"q1": "A"},
        "expected_mcq": {"q1": "A"}
    })

    assert out.agent == "knowledge"
    assert out.score >= 0
    assert out.confidence >= 0


@pytest.mark.asyncio
async def test_clinical_agent():
    agent = ClinicalAgent()
    out = await agent.evaluate({
        "step": "cleaning",
        "actions": [
            {"action": "wash_hands"},
            {"action": "don_gloves"},
            {"action": "clean_wound"},
            {"action": "apply_dressing"}
        ]
    })

    assert out.agent == "clinical"
    assert out.score == 1.0
    assert out.raw["order_ok"] is True


# ---------------------------------------------------------
# 4. RAG LAYER TESTS
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_vectorstore_query_stub():
    # Should return static dummy chunks
    client = VectorClient()
    chunks = await client.query("test query", "scenario_1", "history")
    assert isinstance(chunks, list)
    assert "content" in chunks[0]

@pytest.mark.asyncio
async def test_retriever_layer():
    retriever = Retriever(vector_client=VectorClient())
    ctx = await retriever.get_context("pain", "scenario_1", "history")
    assert isinstance(ctx, list)
    assert len(ctx) > 0


# ---------------------------------------------------------
# 5. SCENARIO LOADER + SESSION MANAGER
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_scenario_loader():
    loader = ScenarioLoader()
    # load_scenario is async, so it needs to be awaited
    data = await loader.load_scenario("scenario_1")
    assert "scenario_id" in data
    assert "patient_name" in data
    assert "condition" in data


def test_session_manager():
    sm = SessionManager()
    sid = sm.create_session("scenario_x", "student_99")

    session = sm.get_session(sid)
    assert session["scenario_id"] == "scenario_x"
    assert session["current_step"] == Step.HISTORY.value

    new_step = sm.advance_step(sid)
    assert new_step == Step.ASSESSMENT.value


@pytest.mark.asyncio
async def test_evaluation_service_payload():
    # EvaluationService requires retriever and scenario_loader on init
    evaluation_service = EvaluationService(retriever=Retriever(vector_client=VectorClient()), scenario_loader=ScenarioLoader())
    # The service prepares the context payload for the agents.
    payload = await evaluation_service.prepare_agent_context(
        transcript="Patient has fever",
        scenario_id="scenario_1",
        step="history"
    )

    assert "transcript" in payload
    assert "rag_chunks" in payload
    assert payload["step"] == "history"


# ---------------------------------------------------------
# 6. API ENDPOINTS
# ---------------------------------------------------------

def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_api_start_session():
    res = client.post("/session/start", json={
        "scenario_id": "scenario_1",
        "student_id": "stu_1"
    })

    assert res.status_code == 200
    body = res.json()
    assert "session_id" in body
    assert body["current_step"] == "history"


def test_api_step_flow():
    # Start session
    res = client.post("/session/start", json={
        "scenario_id": "scenario_1",
        "student_id": "stu_1"
    })
    sid = res.json()["session_id"]

    # Send fake evaluator outputs
    res2 = client.post("/session/step", json={
        "session_id": sid,
        "step": "history",
        "evaluator_outputs": [
            {"agent": "communication", "score": 0.8, "confidence": 0.7, "rationale": "ok"},
            {"agent": "knowledge", "score": 0.6, "confidence": 0.8, "rationale": "fine"}
        ]
    })

    assert res2.status_code == 200
    body = res2.json()

    assert "evaluation" in body
    assert "next_step" in body
    assert body["next_step"] == "assessment"
