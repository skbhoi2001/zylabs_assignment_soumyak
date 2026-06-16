from datetime import datetime, timezone
from app.core.logging import get_logger
from app.workflow.state import GraphState

logger = get_logger(__name__)

SECTION_LABELS = {
    "company_overview": "Company Overview",
    "products_and_services": "Products & Services",
    "target_market": "Target Market",
    "competitive_landscape": "Competitive Landscape",
    "recent_news_and_developments": "Recent News & Developments",
    "financials_and_funding": "Financials & Funding",
    "technology_and_infrastructure": "Technology & Infrastructure",
    "team_and_culture": "Team & Culture",
    "strategic_insights": "Strategic Insights",
}


def report_generator_node(state: GraphState) -> GraphState:
    logger.info("ReportGenerator node starting", extra={"session_id": state["session_id"], "node_name": "report_generator"})
    try:
        sections = state.get("report_sections") or {}
        sources = state.get("sources") or []

        formatted_sections = []
        for key, label in SECTION_LABELS.items():
            content = sections.get(key, "")
            formatted_sections.append({
                "key": key,
                "label": label,
                "content": content,
                "word_count": len(content.split()) if content else 0,
            })

        final_report = {
            "company_name": state["company_name"],
            "website": state["website"],
            "objective": state["objective"],
            "quality_score": state.get("quality_score", 0),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sections": formatted_sections,
            "sources": sources[:20],  # cap at 20 sources
            "retry_count": state.get("retry_count", 0),
            "summary": sections.get("company_overview", "")[:500],
        }

        logger.info("ReportGenerator produced final report", extra={"session_id": state["session_id"], "node_name": "report_generator"})
        return {**state, "final_report": final_report, "error": None}
    except Exception as exc:
        logger.error(f"ReportGenerator node failed: {exc}", extra={"session_id": state["session_id"], "node_name": "report_generator"}, exc_info=True)
        return {**state, "error": f"ReportGenerator failed: {exc}"}
