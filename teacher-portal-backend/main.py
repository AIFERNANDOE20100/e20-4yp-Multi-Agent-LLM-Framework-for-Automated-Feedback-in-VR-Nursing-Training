from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, firestore
import firebase_admin
from openai import OpenAI

# Load environment variables from .env in this folder
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID", "")
FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT", "")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")
if not VECTOR_STORE_ID:
    raise RuntimeError("VECTOR_STORE_ID is required")
if not FIREBASE_SERVICE_ACCOUNT:
    raise RuntimeError("FIREBASE_SERVICE_ACCOUNT is required")

# -----------------------------
# Firebase initialization
# -----------------------------

def _load_firebase_credentials(value: str):
    # Value can be a file path or raw JSON string
    if value.strip().startswith("{"):
        return credentials.Certificate(json.loads(value))

    path = Path(value)
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()

    if not path.exists():
        raise RuntimeError(f"Firebase service account file not found: {path}")

    return credentials.Certificate(str(path))


if not firebase_admin._apps:
    cred = _load_firebase_credentials(FIREBASE_SERVICE_ACCOUNT)
    firebase_admin.initialize_app(cred)

DB = firestore.client()
COLLECTION = "scenarios"

# -----------------------------
# Constants
# -----------------------------

HARDCODED_WOUND_DETAILS: Dict[str, Any] = {
    "location": "Left forearm, external surface (lateral aspect)",
    "wound_type": "Clean surgical wound (Class I)",
    "appearance": "Sutured incision with no visible discharge",
    "size": "Approximately 8 cm linear incision",
    "wound_age": "5 days post-operative",
    "suture_type": "Non-absorbable interrupted sutures",
    "expected_healing": "Primary intention healing",
    "dressing_status": "Primary dressing in place, appears dry and intact",
}

app = FastAPI(title="Teacher Portal Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Helpers
# -----------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _get_doc(doc_id: str) -> Optional[Dict[str, Any]]:
    doc = DB.collection(COLLECTION).document(doc_id).get()
    return doc.to_dict() if doc.exists else None


# -----------------------------
# Routes
# -----------------------------

@app.get("/scenarios")
def list_scenarios() -> List[Dict[str, Any]]:
    docs = DB.collection(COLLECTION).stream()
    results = []

    for doc in docs:
        data = doc.to_dict() or {}
        patient_name = data.get("patient_history", {}).get("name", "")
        created_at = data.get("created_at", "")
        results.append({
            "id": doc.id,
            "patient_name": patient_name,
            "created_at": created_at,
        })

    return results


@app.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str) -> Dict[str, Any]:
    scenario = _get_doc(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@app.delete("/scenarios/{scenario_id}")
def delete_scenario(scenario_id: str) -> Dict[str, Any]:
    doc_ref = DB.collection(COLLECTION).document(scenario_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Scenario not found")
    doc_ref.delete()
    return {"deleted": scenario_id}


@app.post("/scenarios")
def create_scenario(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Create document with auto-generated ID
    doc_ref = DB.collection(COLLECTION).document()
    scenario_id = doc_ref.id

    data = dict(payload or {})

    # Enforce required fields expected by simulation backend
    data["scenario_id"] = scenario_id
    data["scenario_title"] = data.get("scenario_title") or f"Custom Scenario - {data.get('patient_history', {}).get('name', 'Patient')}"
    data["wound_details"] = HARDCODED_WOUND_DETAILS
    data["created_at"] = _now_iso()
    data["vector_store_namespace"] = scenario_id

    doc_ref.set(data)

    return {"scenario_id": scenario_id}


@app.post("/guidelines/upload")
def upload_guidelines(
    file: UploadFile = File(...),
    guideline_type: str = Form(...),
) -> Dict[str, Any]:
    if not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")

    client = OpenAI(api_key=OPENAI_API_KEY)

    uploaded = client.files.create(
        file=file.file,
        purpose="assistants",
    )

    client.vector_stores.files.create(
        vector_store_id=VECTOR_STORE_ID,
        file_id=uploaded.id,
    )

    return {
        "file_id": uploaded.id,
        "guideline_type": guideline_type,
    }
