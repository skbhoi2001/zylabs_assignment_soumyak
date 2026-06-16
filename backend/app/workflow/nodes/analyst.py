import json
from app.core.logging import get_logger
from app.workflow.state import GraphState
from app.workflow.gemini import generate, strip_fences

logger = get_logger(__name__)

ANALYST_PROMPT = """You are a senior business analyst. Using the research findings below, write a comprehensive
company research report for {company_name}. The research objective is: {objective}

RESEARCH FINDINGS:
{findings}

Produce all 9 sections of the report. Return a JSON object with exactly these keys:
{{
  "company_overview": "...",
  "products_and_services": "...",
  "target_market": "...",
  "competitive_landscape": "...",
  "recent_news_and_developments": "...",
  "financials_and_funding": "...",
  "technology_and_infrastructure": "...",
  "team_and_culture": "...",
  "strategic_insights": "..."
}}

Each section should be 2–4 paragraphs of substantive, factual analysis based on the research.
If data for a section is limited, note what is known and what gaps remain.
Return ONLY valid JSON, no markdown fences, no extra commentary."""


def analyst_node(state: GraphState) -> GraphState:
    logger.info("Analyst node starting", extra={"session_id": state["session_id"], "node_name": "analyst"})
    try:
        findings_parts = []
        for task, content in (state.get("raw_findings") or {}).items():
            header = "## Company Website Content" if task.startswith("_") else f"## {task}"
            findings_parts.append(f"{header}\n{content}")
        findings_text = "\n\n".join(findings_parts)[:15000]

        prompt = ANALYST_PROMPT.format(
            company_name=state["company_name"],
            objective=state["objective"],
            findings=findings_text,
        )
        raw = strip_fences(generate(prompt))
        report_sections = json.loads(raw)

        logger.info("Analyst produced 9 report sections", extra={"session_id": state["session_id"], "node_name": "analyst"})
        return {**state, "report_sections": report_sections, "error": None}
    except Exception as exc:
        logger.error(f"Analyst node failed: {exc}", extra={"session_id": state["session_id"], "node_name": "analyst"}, exc_info=True)
        return {**state, "error": f"Analyst failed: {exc}"}
