from pydantic import BaseModel, Field
from typing import Literal


class NarratedFeedbackItem(BaseModel):
    """
    Student-facing narrated feedback unit.

    This is a PRESENTATION-LAYER schema.
    It is derived from raw Feedback objects and rewritten
    by the FeedbackNarratorAgent.

    This schema is safe for:
    - UI display
    - Text-to-Speech (Groq)
    - VR subtitles / overlays
    """

    speaker: Literal["system", "staff_nurse"] = Field(
        ...,
        description="Who is speaking the feedback"
    )

    message_text: str = Field(
        ...,
        description="Student-friendly narrated feedback text"
    )

    category: Literal["communication", "knowledge", "clinical"] = Field(
        ...,
        description="Educational category of feedback"
    )

    severity: Literal["positive", "neutral", "corrective"] = Field(
        ...,
        description="Tone/severity of the feedback message"
    )

    step: str = Field(
        ...,
        description="Procedure step this feedback refers to"
    )

    sequence_index: int = Field(
        ...,
        ge=0,
        description="Ordering index for sequencing feedback messages"
    )
