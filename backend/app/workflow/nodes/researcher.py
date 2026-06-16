import httpx
from tavily import TavilyClient
from app.core.config import settings
from app.core.logging import get_logger
from app.workflow.state import GraphState

logger = get_logger(__name__)


def _scrape_website(url: str) -> str:
    """Attempt a simple text scrape of the company website."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ZyLabsBot/1.0)"}
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            text = resp.text
            # Strip to plain text approximation — just grab content between tags
            import re
            clean = re.sub(r"<[^>]+>", " ", text)
            clean = re.sub(r"\s+", " ", clean).strip()
            return clean[:3000]
    except Exception as exc:
        logger.warning(f"Website scrape failed for {url}: {exc}")
        return ""


def researcher_node(state: GraphState) -> GraphState:
    logger.info("Researcher node starting", extra={"session_id": state["session_id"], "node_name": "researcher"})
    try:
        tavily = TavilyClient(api_key=settings.tavily_api_key)

        raw_findings: dict = dict(state.get("raw_findings") or {})
        all_sources: list = list(state.get("sources") or [])

        # Re-research gaps if we're on a retry
        gaps = state.get("gaps") or []
        plan = state.get("research_plan") or []
        tasks_to_run = gaps if gaps and state.get("retry_count", 0) > 0 else plan

        # Scrape website once
        website_content = _scrape_website(state["website"])
        if website_content:
            raw_findings["_website_content"] = website_content

        for task in tasks_to_run:
            try:
                results = tavily.search(
                    query=f"{state['company_name']} {task}",
                    max_results=5,
                    search_depth="advanced",
                )
                findings_text = []
                for r in results.get("results", []):
                    findings_text.append(f"[{r.get('title', '')}] {r.get('content', '')}")
                    url = r.get("url", "")
                    if url and url not in all_sources:
                        all_sources.append(url)
                raw_findings[task] = "\n\n".join(findings_text)
            except Exception as exc:
                logger.warning(f"Tavily search failed for task '{task}': {exc}")
                raw_findings[task] = f"Search unavailable: {exc}"

        logger.info(f"Researcher completed {len(tasks_to_run)} tasks", extra={"session_id": state["session_id"], "node_name": "researcher"})
        return {**state, "raw_findings": raw_findings, "sources": all_sources, "error": None}
    except Exception as exc:
        logger.error(f"Researcher node failed: {exc}", extra={"session_id": state["session_id"], "node_name": "researcher"}, exc_info=True)
        return {**state, "error": f"Researcher failed: {exc}"}
