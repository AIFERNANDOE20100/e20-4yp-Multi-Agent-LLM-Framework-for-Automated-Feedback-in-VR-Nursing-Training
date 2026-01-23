from typing import List, Dict, Any
import json

from app.agents.agent_base import BaseAgent
from app.utils.narrated_feedback_schema import NarratedFeedbackItem


class FeedbackNarratorAgent(BaseAgent):
    """
    Presentation-only LLM agent.

    Converts raw backend feedback into student-friendly,
    supportive narrated feedback.

    DOES NOT:
    - evaluate
    - score
    - access Firestore
    - access RAG
    """

    def __init__(self):
        super().__init__()

    async def narrate(
        self,
        raw_feedback: List[Dict[str, Any]],
        step: str
    ) -> List[NarratedFeedbackItem]:
        """
        raw_feedback: list of Feedback.to_dict()
        step: HISTORY / ASSESSMENT / CLEANING / DRESSING
        """

        system_prompt = self._build_system_prompt(step)
        user_prompt = self._build_user_prompt(raw_feedback)

        # Call BaseAgent.run()
        output_text = await self.run(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3  # slightly higher for natural tone
        )

        return self._parse_output(output_text, step)

    # --------------------------------------------------
    # Prompt construction
    # --------------------------------------------------

    def _build_system_prompt(self, step: str) -> str:
        return f"""
You are a nursing education tutor.

Your job is to rewrite backend-generated feedback
into clear, supportive, student-friendly explanations.

Context:
- This is formative nursing education
- Step: {step}

Rules:
- Do NOT add new medical advice
- Do NOT contradict the feedback
- Do NOT change meaning
- Be encouraging and clear
- Keep explanations concise
- Output ONLY valid JSON
"""

    def _build_user_prompt(self, raw_feedback: List[Dict[str, Any]]) -> str:
        return f"""
Raw backend feedback (JSON list):

{json.dumps(raw_feedback, indent=2)}

Rewrite this feedback into narrated student-facing feedback.

Required JSON output format:
[
  {{
    "speaker": "system",
    "message_text": "...",
    "category": "communication | knowledge | clinical",
    "severity": "positive | neutral | corrective",
    "sequence_index": 0
  }}
]
"""

    # --------------------------------------------------
    # Output parsing
    # --------------------------------------------------

    def _parse_output(
        self,
        output_text: str,
        step: str
    ) -> List[NarratedFeedbackItem]:

        try:
            parsed = json.loads(output_text)

            narrated_items: List[NarratedFeedbackItem] = []

            for idx, item in enumerate(parsed):
                narrated_items.append(
                    NarratedFeedbackItem(
                        speaker=item["speaker"],
                        message_text=item["message_text"],
                        category=item["category"],
                        severity=item["severity"],
                        step=step,
                        sequence_index=item.get("sequence_index", idx)
                    )
                )

            return narrated_items

        except Exception as e:
            # Fallback: narration failed → return empty narrated list
            return []
