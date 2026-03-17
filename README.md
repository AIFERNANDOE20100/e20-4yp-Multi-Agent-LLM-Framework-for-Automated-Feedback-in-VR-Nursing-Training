# Multi-Agent LLM Framework for Automated Feedback in VR Nursing Training

**Final Year Project — Group 27**
Department of Computer Engineering

---

## Overview

This project is the backend of a Virtual Reality (VR) nursing education platform that trains student nurses in post-operative wound care procedures. The core contribution is a **multi-agent Large Language Model (LLM) framework** that delivers real-time, automated, and clinically grounded feedback to students as they practise inside a VR simulation — replacing the dependency on a human clinical supervisor being present for every session.

Rather than using a single general-purpose LLM for all evaluation, the system deploys **six specialised AI agents**, each responsible for a distinct dimension of nursing competence. Their outputs are aggregated by a coordinator and synthesised into a single, student-friendly feedback paragraph delivered by voice.

The platform serves two user groups:

- **Students** — interact with the VR simulation, converse with a virtual AI patient using voice, answer wound assessment questions, and perform procedural actions, receiving real-time feedback throughout.
- **Teachers (Clinical Educators)** — manage clinical scenarios, upload new guideline documents to the knowledge base, and review detailed student performance logs through a dedicated teacher portal.

---

## Clinical Workflow

Each training session follows a strict three-step sequence governed by a state machine:

1. **History Taking** — The student interviews a virtual AI patient to gather clinical history: confirming identity, checking allergies, assessing pain, taking medical history, and explaining the procedure. For diabetic patient scenarios, asking about wound healing risk factors is additionally expected.

2. **Wound Assessment** — The student answers Multiple Choice Questions about the wound shown in VR, covering wound type, anatomical location, exudate characteristics, tissue condition, and signs of infection.

3. **Wound Cleaning and Dressing Preparation** — The student performs nine sequential preparation actions in the VR environment (hand hygiene, trolley cleaning, solution and dressing selection and verification, materials arrangement, and trolley transport), each validated in real time.

---

## The Six Agents

| Agent | Role |
|---|---|
| **Patient Agent** | Simulates the virtual patient during history taking. Responses are strictly grounded in scenario data — no facts are invented. |
| **Staff Nurse Agent** | Conversational supervising nurse during the cleaning step. Operates in guidance mode (explains requirements) and verification mode (approves or rejects materials presented by the student). |
| **Knowledge Agent** | Evaluates clinical knowledge from the history-taking transcript using a RAG-grounded boolean checklist. Contributes 60% of the History step quality score. |
| **Communication Agent** | Evaluates communication quality — self-introduction, empathy, questioning style, jargon avoidance, and turn count. Contributes 40% of the History step quality score. |
| **Clinical Agent** | Real-time prerequisite validator during the cleaning step. Pass/fail decisions are 100% deterministic via a hardcoded prerequisite map. The LLM is used only to explain *why* a skipped step matters, personalised to the patient's clinical risk profile. |
| **Feedback Narrator Agent** | Synthesises raw agent outputs into a single supportive, formative feedback paragraph delivered to the student by voice at the end of each step. |

All agents extend a shared `BaseAgent` class that wraps the OpenAI Responses API.

---

## Key Design Decisions

**Deterministic safety validation** — The Clinical Agent's pass/fail decisions are never delegated to the LLM. A hardcoded prerequisite map governs all procedural sequencing. The LLM is only invoked to explain failures, not to determine them. This prevents hallucination in safety-critical clinical decisions.

**Retrieval-Augmented Generation (RAG)** — All agent evaluations are grounded in embedded clinical guideline documents stored in an OpenAI Vector Store. Dynamic queries are generated per step and per scenario, and relevant guideline sections are injected into agent prompts before any feedback is produced.

**Scenario-aware personalisation** — Patient risk factors (particularly Type 2 Diabetes Mellitus) modify agent behaviour across the entire pipeline — from the knowledge checklist, to the clinical safety explanations, to the feedback narrator's tone and clinical emphasis.

**Incremental session logging** — Student performance logs are written to Firestore after each step completes using `merge=True`, so even incomplete sessions retain their partial data for teacher review.

---

## Teacher Portal

The teacher portal (`/teacher` API prefix) is a fully decoupled subsystem that allows clinical educators to manage the platform at runtime without any code changes or redeployment.

**Scenario management** — Create, update, retrieve, and list clinical scenarios stored in Firestore. All payloads are validated by Pydantic schemas and a runtime validator enforcing required fields and MCQ integrity before persistence.

**Knowledge base expansion** — Upload `.txt` clinical guideline files directly to the OpenAI Vector Store. New guidelines are immediately available to all RAG-grounded agents.

**Student performance monitoring** — View all past sessions for any student, including per-step scores, action timelines, conversation transcripts, MCQ breakdowns, prerequisite violation logs, and automatically generated critical safety concerns (e.g. missed hand hygiene, unverified dressing packet).

---

## Technology Stack

| Component | Technology |
|---|---|
| Backend Framework | FastAPI (Python) |
| LLM Engine | OpenAI GPT (Responses API) |
| Knowledge Base / RAG | OpenAI Vector Stores |
| Speech-to-Text | Groq Whisper Large v3 |
| Text-to-Speech | Groq Orpheus v1 English |
| Database | Firebase Firestore |
| Real-time Communication | WebSockets |
| Testing | pytest, FastAPI TestClient |

---

## Authors

- Malintha K.M.K. — E/20/243
- Fernando A.I. — E/20/100
- Wickramaarachchi P.A. — E/20/434

**Supervisors:** Mrs. Yasodha Vimukthi · Dr. Upul Jayasinghe
Department of Computer Engineering
