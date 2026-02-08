import json

from pydantic import ValidationError
from app.agents.agent_base import BaseAgent
from app.utils.schema import EvaluatorResponse

class ClinicalAgent(BaseAgent):
    """
    Evaluates clinical and procedural correctness for cleaning and dressing preparation.
    
    REAL-TIME MODE: Provides immediate feedback when action is performed
    FINAL MODE: No final evaluation - real-time feedback is sufficient
    
    Actions and sequences are defined in RAG guidelines, not hardcoded.
    """

    def __init__(self):
        super().__init__()

    async def get_real_time_feedback(
        self,
        action_type: str,
        performed_actions: list[dict],
        rag_guidelines: str
    ) -> dict:
        """
        Provides immediate feedback when an action is performed.
        
        Uses RAG guidelines to determine if:
        1. This action is appropriate at this point
        2. Any prerequisite actions are missing
        3. This action completes correctly
        
        Returns simple, actionable feedback for the student.
        """
        
        # Format previously performed actions
        action_history = "\n".join([
            f"- {i+1}. {act['action_type'].replace('action_', '').replace('_', ' ').title()}"
            for i, act in enumerate(performed_actions)
        ])
        
        if not action_history:
            action_history = "No actions performed yet."
        
        system_prompt = (
            "You are a clinical skills evaluator providing REAL-TIME feedback during wound care preparation.\n\n"
            "ROLE: Evaluate if the current action is appropriate given what has been done so far.\n\n"
            "REFERENCE GUIDELINES:\n"
            f"{rag_guidelines}\n\n"
            "EVALUATION FOCUS:\n"
            "1. Is this action appropriate at this point in the sequence?\n"
            "2. Are there any missing prerequisite actions?\n"
            "3. What should the student do next (if anything is missing)?\n\n"
            "RESPONSE RULES:\n"
            "- Keep feedback SHORT and ACTIONABLE (1-2 sentences)\n"
            "- If action is correct: Acknowledge positively\n"
            "- If prerequisites missing: State what's missing clearly\n"
            "- Do NOT lecture or explain in detail\n"
            "- Do NOT mention the next step after this one\n"
            "- Focus only on the current action and immediate prerequisites\n\n"
            "You MUST respond with valid JSON:\n"
            "{\n"
            '  "status": "complete" | "missing_prerequisites",\n'
            '  "message": "Brief feedback message",\n'
            '  "missing_actions": ["action1", "action2"] or [],\n'
            '  "can_proceed": true | false\n'
            "}\n"
        )
        
        current_action_name = self._format_action_name(action_type)
        
        user_prompt = (
            f"ACTIONS COMPLETED SO FAR:\n{action_history}\n\n"
            f"CURRENT ACTION BEING PERFORMED:\n{current_action_name}\n\n"
            "Based on the reference guidelines:\n"
            "1. Is this action appropriate now?\n"
            "2. What prerequisites (if any) are missing?\n"
            "3. Should the student do something else first?\n\n"
            "Provide real-time feedback in JSON format."
        )
        
        raw_response = await self.run(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )
        
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            feedback = json.loads(clean_json)
            
            # Add metadata
            feedback["action_type"] = action_type
            feedback["total_actions_so_far"] = len(performed_actions) + 1
            
            return feedback
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Real-time feedback parsing failed: {e}")
            # Fallback: Simple acknowledgment
            return {
                "status": "complete",
                "message": f"{current_action_name.capitalize()} recorded.",
                "missing_actions": [],
                "can_proceed": True,
                "action_type": action_type,
                "total_actions_so_far": len(performed_actions) + 1
            }

    def _format_action_name(self, action_type: str) -> str:
        """Convert action_type to readable name"""
        return action_type.replace("action_", "").replace("_", " ").title()

    async def evaluate(
        self,
        current_step: str,
        student_input: str,
        scenario_metadata: dict,
        rag_response: str,
    ) -> EvaluatorResponse:
        """
        NO FINAL EVALUATION for cleaning_and_dressing step.
        Real-time feedback during actions is sufficient.
        
        This method returns None to indicate no evaluation needed.
        """
        
        # Return None to indicate this step doesn't need final evaluation
        return None
