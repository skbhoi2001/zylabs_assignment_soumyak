from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class GraphState(TypedDict):
    session_id: str
    company_name: str
    website: str
    objective: str
    research_plan: List[str]
    raw_findings: Dict[str, Any]
    report_sections: Dict[str, str]
    quality_score: int
    gaps: List[str]
    retry_count: int
    final_report: Dict[str, Any]
    error: Optional[str]
    sources: List[str]
