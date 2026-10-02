"""The agent graph.

    START → write → check_tone ─┬─ passes ─────────────→ human_review ─┬─ approve → END
                ↑               ├─ fails, retries left → write         └─ feedback → write
                └───────────────┘
                                └─ fails, out of retries → human_review (with the judge's notes)
"""

from functools import cache
from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Checkpointer, interrupt

from polite_email.models import Judge, Writer, claude_judge, claude_writer
from polite_email.state import State

MAX_REVISIONS = 3
PASS_SCORE = 4


def build_graph(
    writer: Writer | None = None,
    judge: Judge | None = None,
    *,
    human_review: bool = True,
    checkpointer: Checkpointer = None,
):
    """Build the graph.

    writer/judge default to Claude (created lazily, so importing needs no API key).
    human_review=False ends after the automatic checks; use it for evals and batch runs.
    A checkpointer is required for human_review when running outside LangGraph Studio/Server.
    """
    get_writer = (lambda: writer) if writer else cache(claude_writer)
    get_judge = (lambda: judge) if judge else cache(claude_judge)

    def write(state: State) -> State:
        draft = get_writer()(state["request"], state.get("draft"), state.get("feedback"))
        return {"draft": draft, "revisions": state.get("revisions", -1) + 1, "status": "drafting"}

    def check_tone(state: State) -> State:
        report = get_judge()(state["request"], state["draft"])
        return {"report": report, "feedback": "\n".join(f"- {issue}" for issue in report.issues)}

    def route_after_check(state: State) -> Literal["write", "human_review", "__end__"]:
        report = state["report"]
        passed = report.polite and report.score >= PASS_SCORE
        if not passed and state["revisions"] < MAX_REVISIONS:
            return "write"
        if human_review:
            return "human_review"
        return END

    def review(state: State) -> Command[Literal["write", "__end__"]]:
        # Pauses the run. Resume with Command(resume={"action": "approve"})
        # or Command(resume={"action": "revise", "feedback": "..."}).
        decision = interrupt(
            {
                "draft": state["draft"],
                "report": state["report"].model_dump(),
                "revisions": state["revisions"],
            }
        )
        if decision.get("action") == "approve":
            return Command(goto=END, update={"status": "approved"})
        return Command(goto="write", update={"feedback": decision.get("feedback", "")})

    def finish(state: State) -> State:
        report = state["report"]
        ok = report.polite and report.score >= PASS_SCORE
        return {"status": "approved" if ok else "gave_up"}

    builder = StateGraph(State)
    builder.add_node("write", write)
    builder.add_node("check_tone", check_tone)
    builder.add_edge(START, "write")
    builder.add_edge("write", "check_tone")
    if human_review:
        builder.add_node("human_review", review)
        builder.add_conditional_edges("check_tone", route_after_check, ["write", "human_review"])
    else:
        builder.add_node("finish", finish)
        builder.add_conditional_edges(
            "check_tone", route_after_check, {"write": "write", "human_review": "finish", END: "finish"}
        )
        builder.add_edge("finish", END)
    return builder.compile(checkpointer=checkpointer)


# Entry point for LangGraph Studio (`langgraph dev`), which supplies its own persistence.
graph = build_graph()
