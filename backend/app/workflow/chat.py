import json
from typing import Any, List, Optional
from app.core.logging import get_logger
from app.workflow.gemini import chat_with_history, generate

logger = get_logger(__name__)

SYSTEM_TEMPLATE = """You are an AI research assistant for ZyLabs. You have access to a detailed research report
about {company_name}. Answer the user's questions based on this report. Be specific, cite sections when relevant,
and clearly flag if something is not covered in the report.

RESEARCH REPORT:
{report_json}
"""


async def generate_chat_reply(
    user_message: str,
    history: List[Any],
    final_report: Optional[dict],
    session: Any,
) -> str:
    try:
        if final_report:
            system = SYSTEM_TEMPLATE.format(
                company_name=session.company_name,
                report_json=json.dumps(final_report, indent=2)[:12000],
            )
        else:
            system = (
                f"You are a research assistant for ZyLabs. The research report for "
                f"{session.company_name} is still being generated. Answer general "
                f"questions about the company if you can, otherwise let the user know."
            )

        # history[-1] is the current user message we just persisted; pass everything before it
        prior_history = history[:-1]
        return chat_with_history(system, prior_history, user_message)
    except Exception as exc:
        logger.error(f"Chat reply failed: {exc}", exc_info=True)
        return f"I encountered an error generating a response: {exc}"
