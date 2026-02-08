from app.agents.agent_base import BaseAgent
from app.core.step_guidance import STEP_GUIDANCE


class StaffNurseAgent(BaseAgent):
    """
    Conversational supervising nurse (GUIDANCE + VERIFICATION).
    
    Two modes:
    1. GUIDANCE: Explains current/next step
    2. VERIFICATION: Checks solution/dressing materials when asked
    
    Does NOT evaluate, approve progression, or block steps.
    """

    FINISH_KEYWORDS = [
        "finished",
        "done",
        "what next",
        "next step",
        "can i proceed",
        "ready",
        "move on",
        "complete"
    ]

    VERIFICATION_KEYWORDS = [
        "verify",
        "check",
        "confirm",
        "is this correct",
        "is this right",
        "can you check",
        "look at this",
        "expired",
        "expiration",
        "solution",
        "dressing packet",
        "sterile",
        "surgical spirit",
        "dry dressing",
        "bottle",
        "packet"
    ]

    def __init__(self):
        super().__init__()

    def _is_student_finishing(self, student_input: str) -> bool:
        """Detect if student is asking about next step."""
        student_lower = student_input.lower()
        return any(keyword in student_lower for keyword in self.FINISH_KEYWORDS)

    def _is_verification_request(self, student_input: str) -> bool:
        """Detect if student is asking for material verification."""
        student_lower = student_input.lower()
        return any(keyword in student_lower for keyword in self.VERIFICATION_KEYWORDS)

    async def respond(
        self,
        student_input: str,
        current_step: str,
        next_step: str | None
    ) -> str:

        is_finishing = self._is_student_finishing(student_input)
        is_verification = self._is_verification_request(student_input)

        current_guidance = STEP_GUIDANCE.get(current_step, "")
        next_guidance = STEP_GUIDANCE.get(next_step, "") if next_step else ""

        # ================================================
        # MODE 1: VERIFICATION (for cleaning_and_dressing)
        # ================================================
        if is_verification and current_step == "cleaning_and_dressing":
            system_prompt = (
                "You are a supervising staff nurse verifying materials with a nursing student.\n\n"
                "VERIFICATION ROLE:\n"
                "- The student is showing you a cleaning solution or dressing packet.\n"
                "- Listen to what the student tells you about the item.\n"
                "- The student should state: name/type, expiration date, package integrity.\n\n"
                "VERIFICATION PROCESS:\n"
                "- If student provides complete info → Acknowledge and approve\n"
                "- If student provides incomplete info → Ask for missing details\n"
                "- If student mentions 'expired' or 'damaged' → Instruct to get replacement\n"
                "- Assume items are correct if student states them properly\n\n"
                "EXPECTED MATERIALS:\n"
                "- Cleaning solution: Surgical spirit\n"
                "- Dressing packet: Dry dressing (sterile)\n\n"
                "RESPONSE STYLE:\n"
                "- Be supportive and professional\n"
                "- Use simple, clear language\n"
                "- Give specific feedback: 'Surgical spirit, expires [date], bottle intact - looks good.'\n"
                "- End with clear approval: 'You may use it' or 'You can proceed.'\n"
            )

            user_prompt = (
                f"CURRENT STEP: {current_step}\n"
                f"STUDENT REQUEST:\n{student_input}\n\n"
                f"The student is asking you to verify materials.\n"
                "Respond as a staff nurse checking what the student tells you."
            )

        # ================================================
        # MODE 2: NEXT STEP GUIDANCE (when student finishes)
        # ================================================
        elif is_finishing and next_guidance:
            system_prompt = (
                "You are a supervising staff nurse guiding a nursing student.\n\n"
                "ROLE RULES:\n"
                "- Provide guidance only\n"
                "- Do NOT evaluate performance\n"
                "- Do NOT grant permission to proceed\n"
                "- The student controls step progression\n\n"
                "TASK:\n"
                "- Student indicated they are finished with current step\n"
                "- Explain the NEXT step briefly\n"
                "- Keep responses short, clear, and spoken-friendly\n"
            )

            user_prompt = (
                f"CURRENT STEP: {current_step}\n"
                f"NEXT STEP: {next_step}\n"
                f"NEXT STEP GUIDANCE:\n{next_guidance}\n\n"
                f"STUDENT MESSAGE:\n{student_input}\n"
            )

        # ================================================
        # MODE 3: CURRENT STEP GUIDANCE (default)
        # ================================================
        else:
            system_prompt = (
                "You are a supervising staff nurse guiding a nursing student.\n\n"
                "ROLE RULES:\n"
                "- Provide guidance only\n"
                "- Do NOT evaluate performance\n"
                "- Do NOT grant permission to proceed\n"
                "- The student controls step progression\n\n"
                "TASK:\n"
                "- Student is asking about the CURRENT step\n"
                "- Explain what they should be doing now\n"
                "- Keep responses short, clear, and spoken-friendly\n"
            )

            user_prompt = (
                f"CURRENT STEP: {current_step}\n"
                f"CURRENT STEP GUIDANCE:\n{current_guidance}\n\n"
                f"STUDENT MESSAGE:\n{student_input}\n"
            )

        return await self.run(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3
        )
