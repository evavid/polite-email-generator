"""Default LLM-backed writer and judge. Swappable: build_graph() accepts any callables with the same shape."""

import os
from collections.abc import Callable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from polite_email import prompts
from polite_email.state import EmailRequest, ToneReport

# writer(request, draft, feedback) -> email text. draft/feedback are None for the first draft.
Writer = Callable[[EmailRequest, str | None, str | None], str]
# judge(request, draft) -> ToneReport
Judge = Callable[[EmailRequest, str], ToneReport]


def claude_writer() -> Writer:
    llm = ChatAnthropic(model=os.getenv("WRITER_MODEL", "claude-sonnet-5-5"), temperature=0.7)

    def write(request: EmailRequest, draft: str | None, feedback: str | None) -> str:
        if draft is None:
            user = prompts.WRITER_FIRST_DRAFT.format(**request)
        else:
            user = prompts.WRITER_REVISION.format(**request, draft=draft, feedback=feedback or "")
        reply = llm.invoke([SystemMessage(prompts.WRITER_SYSTEM), HumanMessage(user)])
        return reply.text.strip()

    return write


def claude_judge() -> Judge:
    llm = ChatAnthropic(model=os.getenv("JUDGE_MODEL", "claude-haiku-4-5-20251001"), temperature=0)
    structured = llm.with_structured_output(ToneReport, method="json_schema")

    def judge(request: EmailRequest, draft: str) -> ToneReport:
        user = prompts.JUDGE_USER.format(purpose=request["purpose"], signature=request["signature"], draft=draft)
        return structured.invoke([SystemMessage(prompts.JUDGE_SYSTEM), HumanMessage(user)])

    return judge
