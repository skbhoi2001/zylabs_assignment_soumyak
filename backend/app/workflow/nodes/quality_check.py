import json
from app.core.logging import get_logger
from app.workflow.state import GraphState
from app.workflow.gemini import generate, strip_fences

logger = get_logger(__name__)

REQUIRED_SECTIONS = [
    "company_overview", "products_and_services", "target_market",
    "competitive_landscape", "recent_news_and_developments",
    "financials_and_funding", "technology_and_infrastructure",
    "team_and_culture", "strategic_insights",
]

QUALITY_PROMPT = """You are a research quality auditor. Evaluate the completeness and quality of this
company research report for {company_name}.

REPORT SECTIONS:
{sections}

Score the report on a scale of 0–100:
- Completeness: all 9 sections present and substantive (40 pts)
- Factual specificity: concrete facts vs vague generalities (30 pts)
- Relevance to objective "{objective}" (20 pts)
- Overall coherence (10 pts)

Return a JSON object:
{{
  "quality_score": <integer 0-100>,
  "gaps": ["gap description 1", "gap description 2", ...]
}}

Return ONLY valid JSON, no markdown fences."""


def quality_check_node(state: GraphState) -> GraphState:
    logger.info("QualityCheck node starting", extra={"session_id": state["session_id"], "node_name": "quality_check"})
    try:
        report_sections = state.get("report_sections") or {}
        present = [s for s in REQUIRED_SECTIONS if report_sections.get(s, "").strip()]
        structural_score = int((len(present) / len(REQUIRED_SECTIONS)) * 40)

        if structural_score < 20:
            gaps = [s for s in REQUIRED_SECTIONS if not report_sections.get(s, "").strip()]
            return {**state, "quality_score": structural_score, "gaps": gaps, "error": None}

        prompt = QUALITY_PROMPT.format(
            company_name=state["company_name"],
            objective=state["objective"],
            sections=json.dumps(report_sections, indent=2)[:8000],
        )
        raw = strip_fences(generate(prompt))
        result = json.loads(raw)
        quality_score = int(result.get("quality_score", 0))
        gaps = result.get("gaps", [])

        logger.info(f"QualityCheck score={quality_score}, gaps={len(gaps)}", extra={"session_id": state["session_id"], "node_name": "quality_check"})
        return {**state, "quality_score": quality_score, "gaps": gaps, "error": None}
    except Exception as exc:
        logger.error(f"QualityCheck node failed: {exc}", extra={"session_id": state["session_id"], "node_name": "quality_check"}, exc_info=True)
        # On failure, pass with a passing score to avoid infinite loops
        return {**state, "quality_score": 70, "gaps": [], "error": f"QualityCheck failed: {exc}"}


def quality_router(state: GraphState) -> str:
    score = state.get("quality_score", 0)
    retry_count = state.get("retry_count", 0)
    if score >= 70:
        logger.info(f"Quality passed (score={score}) -> ReportGenerator", extra={"session_id": state["session_id"]})
        return "report_generator"
    elif retry_count < 2:
        logger.info(f"Quality insufficient (score={score}, retry={retry_count}) -> Researcher", extra={"session_id": state["session_id"]})
        return "researcher"
    else:
        logger.info(f"Max retries (score={score}) -> ReportGenerator best-effort", extra={"session_id": state["session_id"]})
        return "report_generator"
