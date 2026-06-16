import json
from app.core.logging import get_logger
from app.workflow.state import GraphState
from app.workflow.gemini import generate, strip_fences

logger = get_logger(__name__)

PLANNER_PROMPT = """You are a senior research strategist. Given a company and a research objective,
break the objective into 4–6 specific, targeted research sub-tasks that will produce a thorough report.

Company: {company_name}
Website: {website}
Research Objective: {objective}

Return a JSON object with a single key "research_plan" whose value is a list of 4–6 specific research sub-task strings.
Each sub-task should be a clear, actionable search query or investigation topic.

Example format:
{{"research_plan": [
  "What are {company_name}'s core products and primary revenue streams?",
  "Who are {company_name}'s main competitors and how do they differentiate?",
  "What is {company_name}'s recent news, funding, or strategic announcements?",
  "What technology stack and infrastructure does {company_name} use?",
  "Who are {company_name}'s key executives and what is the company culture like?"
]}}

Return ONLY valid JSON, no markdown fences, no explanation."""


def planner_node(state: GraphState) -> GraphState:
    logger.info("Planner node starting", extra={"session_id": state["session_id"], "node_name": "planner"})
    try:
        prompt = PLANNER_PROMPT.format(
            company_name=state["company_name"],
            website=state["website"],
            objective=state["objective"],
        )
        raw = strip_fences(generate(prompt))
        plan = json.loads(raw).get("research_plan", [])
        logger.info(f"Planner produced {len(plan)} sub-tasks", extra={"session_id": state["session_id"], "node_name": "planner"})
        return {**state, "research_plan": plan, "error": None}
    except Exception as exc:
        logger.error(f"Planner node failed: {exc}", extra={"session_id": state["session_id"], "node_name": "planner"}, exc_info=True)
        return {**state, "error": f"Planner failed: {exc}"}
