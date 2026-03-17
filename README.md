# Multi-Agent LLM Framework for Automated Feedback in VR Nursing Training

> **Final Year Project — Group 27**
> Department of Computer Engineering

---

## Overview

This project presents a **multi-agent Large Language Model (LLM) framework** that delivers automated, real-time, clinically grounded feedback to nursing students practising in a Virtual Reality simulation environment.

Traditional clinical training relies entirely on human supervisors who must be physically present for every session — a model that does not scale. Existing VR nursing simulations lack intelligent feedback: students complete procedures without knowing whether their clinical technique was appropriate. This system addresses both gaps by deploying six specialised AI agents, each evaluating a different dimension of nursing competence simultaneously, and synthesising their outputs into clear formative feedback delivered by voice inside the VR headset.

The platform was built around a post-operative **wound care nursing** scenario. Students work through three sequential clinical steps — history taking with a virtual patient, wound assessment, and wound cleaning and dressing preparation — and receive feedback at every stage grounded in real clinical guidelines through a Retrieval-Augmented Generation (RAG) pipeline.

A dedicated **Teacher Portal** allows clinical educators to create and manage scenarios, upload clinical guideline files to expand the knowledge base, and review detailed per-session student performance logs — all without requiring developer involvement.

---

## Key Features

- **Six-agent multi-agent framework** — Patient Agent, Staff Nurse Agent, Knowledge Agent, Communication Agent, Clinical Agent, and Feedback Narrator Agent, each specialised for a distinct evaluation role
- **Hybrid deterministic + LLM architecture** — safety-critical pass/fail decisions (procedural prerequisite validation) are 100% deterministic; the LLM is used only for educational explanation, preventing hallucination in clinical judgements
- **RAG-grounded feedback** — all AI feedback is anchored to embedded clinical guideline documents via OpenAI Vector Stores, not general model knowledge
- **Real-time multi-voice audio** — Groq Whisper STT captures student voice input; Groq Orpheus TTS delivers distinct voiced responses for each character role (patient, staff nurse, feedback narrator)
- **Scenario-adaptive evaluation** — patient risk factors (e.g. Type 2 Diabetes Mellitus) modify agent behaviour, checklist criteria, scoring rubrics, and feedback tone across the entire pipeline
- **Teacher Portal** — full scenario CRUD with validation, RAG knowledge base expansion via file upload, and detailed student performance monitoring with per-step breakdowns and critical safety concern flagging
- **Incremental session logging** — student performance data is saved to Firebase Firestore after each step, so even incomplete sessions are fully captured for educator review

---

## System Architecture

![System Architecture](code/diagram.png)

---

## Clinical Workflow

The simulation follows a strict three-step state machine — steps must be completed in order:

| Step | Description | Evaluated by |
|---|---|---|
| **1. History Taking** | Student interviews the virtual AI patient using voice or text — confirming identity, checking allergies, assessing pain, taking a medical history, and explaining the procedure | Knowledge Agent (60%) + Communication Agent (40%) |
| **2. Wound Assessment** | Student answers MCQs about the wound shown in VR — wound type, location, exudate, tissue colour, infection signs | Deterministic MCQ evaluator |
| **3. Cleaning & Dressing Preparation** | Student performs nine sequential preparation actions in VR — hand hygiene, trolley cleaning, solution and dressing selection and verification, materials arrangement, trolley transport | Clinical Agent (real-time, deterministic) |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI (Python) |
| LLM engine | OpenAI GPT (Responses API) |
| RAG / Vector Store | OpenAI Vector Stores |
| Speech-to-Text | Groq Whisper Large v3 |
| Text-to-Speech | Groq Orpheus v1 English |
| Database | Firebase Firestore |
| Real-time communication | WebSockets |
| VR application | Unity |
| Teacher portal frontend | React + Vite |

---

## Repository Structure

```
e20-4yp-Multi-Agent-LLM-Framework-for-Automated-Feedback-in-VR-Nursing-Training/
├── code/
│   ├── Backend_WoundCareSim/
│   │   └── app/
│   │       ├── agents/                 # Multi-agent implementations
│   │       │   ├── agent_base.py
│   │       │   ├── clinical_agent.py
│   │       │   ├── communication_agent.py
│   │       │   ├── feedback_narrator_agent.py
│   │       │   ├── knowledge_agent.py
│   │       │   ├── patient_agent.py
│   │       │   └── staff_nurse_agent.py
│   │       ├── api/                    # FastAPI routes
│   │       │   ├── audio_routes.py
│   │       │   ├── scenario_routes.py
│   │       │   ├── session_routes.py
│   │       │   ├── student_routes.py
│   │       │   └── websocket_routes.py
│   │       ├── core/                   # Core business logic & state machine
│   │       ├── data/                   # Data storage and schemas
│   │       ├── rag/                    # Retrieval-Augmented Generation logic
│   │       ├── services/               # External service integrations (TTS, STT, etc.)
│   │       ├── teacher_portal/         # Backend logic for the teacher portal
│   │       ├── utils/                  # Helper functions and utilities
│   │       └── main.py                 # FastAPI application entry point
│   ├── evaluation/                     # Evaluation framework and scripts
│   │   ├── performance/                # Performance metrics scripts
│   │   ├── reliability/                # Reliability testing scripts
│   │   ├── results/                    # Stored evaluation results
│   │   ├── golden_dataset.json         # Reference dataset for agent evaluation
│   │   ├── metrics.py                  # Evaluation metric definitions
│   │   ├── run_agent_evaluation.py     # Script to evaluate specific agents
│   │   └── run_judge_evaluation.py     # Script for LLM-as-a-judge evaluation
│   ├── teacher-portal-frontend/        # React/Vite-based teacher portal UI
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── pages/
│   │   │   └── services/
│   │   ├── index.html
│   │   ├── package.json
│   │   └── vite.config.js
│   ├── tests/                          # Unit and integration tests
│   │   ├── integration/                # End-to-end integration tests
│   │   ├── conftest.py
│   │   ├── test_clinical_agent.py
│   │   ├── test_communication_agent.py
│   │   ├── test_mcq_evaluator.py
│   │   ├── test_scoring.py
│   │   └── test_state_machine.py
│   └── requirements.txt                # Python dependencies
├── docs/                               # Project documentation
└── README.md
```

---

## Unity VR Application

The VR client is maintained in a separate repository:

**[FYP-WoundCareSim-Unity](https://github.com/kushanmalintha/FYP-WoundCareSim-Unity.git)**

The Unity project handles the VR environment, patient bed scene, wound visualisation, interaction events, and audio playback. It communicates with the backend via REST APIs and WebSockets.

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js (for the teacher portal frontend)
- A Firebase project with Firestore enabled and a service account credentials file
- An OpenAI API key with access to the Responses API and Vector Stores
- A Groq API key
- A configured OpenAI Vector Store ID with your clinical guideline documents uploaded

### Environment Variables

Create a `.env` file in `code/Backend_WoundCareSim/` with the following:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_CHAT_MODEL=gpt-5-mini
OPENAI_EMBED_MODEL=text-embedding-3-small
VECTOR_STORE_ID=your_vector_store_id

GROQ_API_KEY=your_groq_api_key
GROQ_STT_MODEL=whisper-large-v3
GROQ_TTS_MODEL=canopylabs/orpheus-v1-english
GROQ_TTS_VOICE=

FIREBASE_CREDENTIALS_PATH=path/to/your/firebase_credentials.json
```

### 1. Start the Backend

```bash
cd code/Backend_WoundCareSim
pip install -r ../../requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`. Interactive API docs are at `http://localhost:8000/docs`.

### 2. Start the Teacher Portal Frontend

```bash
cd code/teacher-portal-frontend
npm install
npm run dev
```

Open the teacher portal in your browser. Use it to select a scenario and start a session before launching the VR application.

### 3. Run the VR Application

Open the Unity project from the [Unity repository](https://github.com/kushanmalintha/FYP-WoundCareSim-Unity.git). Inside the project, set the backend server IP address to your PC's local network IP. Build and deploy the application to your VR headset. Both the PC and the VR headset must be on the same local network.

**Required start order:**
1. Start the backend server
2. Open the teacher portal and select a scenario to start a session
3. Launch the VR application — it will automatically connect to the active session via WebSocket

---

## Running the Tests

```bash
cd code
pytest tests/ -v
```

This runs all 37 tests covering unit tests (state machine, MCQ evaluator, scoring engine, clinical agent, communication agent) and integration tests (API endpoints, session lifecycle, WebSocket events, RAG retriever, student logs).

---

## Evaluation

The `code/evaluation/` directory contains all scripts used to evaluate the system.

```bash
# AI agent evaluation (Knowledge Agent + Communication Agent)
python code/evaluation/run_agent_evaluation.py

# LLM-as-judge evaluation (Feedback Narrator Agent)
python code/evaluation/run_judge_evaluation.py
```

Performance and reliability evaluation scripts are in `code/evaluation/performance/` and `code/evaluation/reliability/` respectively. All results are saved to `code/evaluation/results/`.

### Evaluation Results Summary

| Pillar | Method | Result |
|---|---|---|
| Unit Testing | pytest — 22 tests | 100% pass rate |
| Integration Testing | FastAPI TestClient — 15 tests | 100% pass rate |
| Knowledge Agent | Golden dataset — Precision / Recall / F1 | 0.96 / 0.93 / 0.94 |
| Communication Agent | Verdict accuracy + consistency rate | 1.00 accuracy · 95% consistency |
| Reliability | Fault injection — 4 failure scenarios | 100% recovery · 0 crashes |
| STT (Groq Whisper) | Word Error Rate across 12 samples | Average WER: 0.13 |
| TTS (Groq Orpheus) | Round-trip intelligibility WER | 0.13 |
| STT Latency | P50 / P95 | 0.67s / 0.89s |
| TTS Latency | P50 / P95 | 0.82s / 0.98s |

---

## Links

- **Unity VR Application:** [FYP-WoundCareSim-Unity](https://github.com/kushanmalintha/FYP-WoundCareSim-Unity.git)
- **Project Documentation:** `docs/`

---

## Team

| Name | Index |
|---|---|
| Malintha K.M.K. | E/20/243 |
| Fernando A.I. | E/20/100 |
| Wickramaarachchi P.A. | E/20/434 |

**Supervisors:** Mrs. Yasodha Vimukthi · Dr. Upul Jayasinghe
Department of Computer Engineering
