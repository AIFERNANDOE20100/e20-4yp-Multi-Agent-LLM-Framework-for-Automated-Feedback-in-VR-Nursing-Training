import json
import logging
from openai import AsyncOpenAI
from app.agents.agent_base import BaseAgent
from app.core.config import (
    OPENAI_API_KEY,
    VECTOR_STORE_ID,
    OPENAI_CHAT_MODEL,
)

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not configured")

if not VECTOR_STORE_ID:
    raise RuntimeError("VECTOR_STORE_ID not configured")

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def retrieve_with_rag(
    query: str,
    scenario_id: str,
    system_instruction: str = "You are a nursing guideline retrieval assistant."
):
    """
    Perform RAG using OpenAI Responses API + managed Vector Store.

    - Stateless
    - File-first
    - No manual chunking
    - No top_k
    """

    try:
        response = await client.responses.create(
            model=OPENAI_CHAT_MODEL,
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [VECTOR_STORE_ID]
                }
            ],
            input=[
                {
                    "role": "system",
                    "content": (
                        f"{system_instruction}\n"
                        f"CONSTRAINT: Use only information relevant to scenario_id={scenario_id}.\n"
                        f"Do NOT invent facts. If information is missing, say so."
                    )
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
        )

        # -----------------------------
        # SAFE OUTPUT EXTRACTION
        # -----------------------------
        rag_text = ""

        if hasattr(response, "output"):
            for item in response.output:
                if getattr(item, "type", None) == "message":
                    for part in getattr(item, "content", []):
                        if getattr(part, "type", "") in ["text", "output_text"]:
                            rag_text += getattr(part, "text", "")

        rag_text = rag_text.strip()
        print(f"RAG retrieved text: {rag_text}")
        if not rag_text:
            logger.warning("RAG returned empty context")

        return {
            "text": rag_text,
            "raw_response": response
        }

    except Exception as e:
        logger.error(f"RAG retrieval failed: {e}")
        return {
            "text": "",
            "raw_response": None
        }


async def extract_prerequisite_map(
    rag_text: str,
    base_agent: BaseAgent
) -> dict[str, list[str]]:
    try:
        response = await base_agent.run(
            system_prompt=(
                "You are a clinical guideline parser.\n"
                "Extract the prerequisite map from the provided nursing guideline text.\n"
                "Return ONLY a valid JSON object. No markdown, no explanation,\n"
                "no code fences. Nothing else.\n"
                "Format:\n"
                "{\n"
                '  "action_key": ["prerequisite_action_key", ...],\n'
                "  ...\n"
                "}\n"
                "Rules:\n"
                "- Use exact action key names as they appear in the document\n"
                "  (e.g. action_initial_hand_hygiene)\n"
                "- If an action has no prerequisites, map it to an empty list []\n"
                "- Include ALL actions found in the document\n"
                "- Do NOT invent action keys not present in the document"
            ),
            user_prompt=rag_text,
            temperature=0.0,
        )
        parsed = json.loads(response)
        if isinstance(parsed, dict):
            return parsed
        logger.warning("extract_prerequisite_map() returned non-dict JSON. Falling back to empty map.")
        return {}
    except Exception as e:
        logger.warning(f"Failed to extract prerequisite map from RAG text: {e}")
        return {}
