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
        
        ENHANCED: Reports ALL missing prerequisite actions, not just the immediate one.
        
        Uses RAG guidelines to determine if:
        1. This action is appropriate at this point
        2. ANY prerequisite actions are missing (comprehensive check)
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
            "2. Identify ALL missing prerequisite actions (not just the immediate previous one)\n"
            "3. What should the student do to correct the sequence?\n\n"
            "CRITICAL INSTRUCTION - COMPREHENSIVE PREREQUISITE CHECK:\n"
            "- If the student skips multiple actions (e.g., does Action 1, then jumps to Action 5)\n"
            "- You MUST list ALL missing actions (Actions 2, 3, 4)\n"
            "- Do NOT only mention the immediate previous action\n"
            "- This ensures the student understands ALL gaps in their procedure\n\n"
            "RESPONSE RULES:\n"
            "- Keep feedback SHORT and ACTIONABLE (2-3 sentences)\n"
            "- If action is correct: Acknowledge positively\n"
            "- If prerequisites missing: List ALL missing actions clearly\n"
            "- Do NOT lecture or explain in detail\n"
            "- Do NOT mention the next step after this one\n"
            "- Focus on what's been skipped and what needs to be done\n\n"
            "You MUST respond with valid JSON:\n"
            "{\n"
            '  "status": "complete" | "missing_prerequisites",\n'
            '  "message": "Brief feedback message listing ALL missing actions if applicable",\n'
            '  "missing_actions": ["action1", "action2", "action3"] or [],\n'
            '  "can_proceed": true | false\n'
            "}\n"
        )
        
        current_action_name = self._format_action_name(action_type)
        
        user_prompt = (
            f"ACTIONS COMPLETED SO FAR:\n{action_history}\n\n"
            f"CURRENT ACTION BEING PERFORMED:\n{current_action_name}\n\n"
            "Based on the reference guidelines:\n"
            "1. Is this action appropriate now?\n"
            "2. List ALL prerequisite actions that should have been completed before this action\n"
            "3. Which of those prerequisite actions are missing from the completed actions?\n"
            "4. What should the student do to correct the sequence?\n\n"
            "IMPORTANT: If multiple actions were skipped, list ALL of them in missing_actions array.\n\n"
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
            
            # Enhanced message formatting if multiple actions are missing
            if feedback.get("missing_actions") and len(feedback["missing_actions"]) > 1:
                missing_names = [self._format_action_name(act) for act in feedback["missing_actions"]]
                feedback["message"] = (
                    f"You skipped multiple steps. Please complete: {', '.join(missing_names)}. "
                    f"{feedback.get('message', '')}"
                )
            
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
