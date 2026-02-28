from app.agents.agent_base import BaseAgent


class ClinicalAgent(BaseAgent):
    """
    Clinical Agent with deterministic real-time prerequisite validation.
    """

    async def get_real_time_feedback(
        self,
        action_type: str,
        performed_actions: list[dict],
        prerequisite_map: dict[str, list[str]] | None = None,
        **_: object,
    ) -> dict:
        if prerequisite_map is None:
            prerequisite_map = {}

        completed = [a["action_type"] for a in performed_actions]
        prerequisites = prerequisite_map.get(action_type, [])
        if action_type not in prerequisite_map:
            self.logger.warning(
                f"Action '{action_type}' not found in dynamic prerequisite map. "
                "Treating as no prerequisites."
            )
        missing = [p for p in prerequisites if p not in completed]

        if not missing:
            status = "complete"
            can_proceed = True
            action_name = action_type.replace("action_", "").replace("_", " ").title()
            message = f"{action_name}: Done correctly."
        else:
            status = "missing_prerequisites"
            can_proceed = False
            action_name = action_type.replace("action_", "").replace("_", " ").title()
            missing_names = [
                m.replace("action_", "").replace("_", " ").title()
                for m in missing
            ]
            message = f"{action_name}: Missing \u2014 {', '.join(missing_names)}."

        return {
            "status": status,
            "message": message,
            "missing_actions": missing,
            "can_proceed": can_proceed,
            "action_type": action_type,
            "total_actions_so_far": len(performed_actions) + 1
        }
