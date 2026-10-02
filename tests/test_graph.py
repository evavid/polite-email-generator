"""Graph behaviour with fake writer/judge: no API keys or network needed."""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from polite_email.graph import MAX_REVISIONS, build_graph
from polite_email.state import ToneReport

REQUEST = {"recipient": "Ana", "affiliation": "ACME", "purpose": "Ask for the report", "signature": "Eva"}
GOOD = ToneReport(polite=True, score=5, issues=[])
RUDE = ToneReport(polite=False, score=2, issues=["Too blunt"])


def fake_writer(calls: list):
    def write(request, draft, feedback):
        calls.append(feedback)
        return f"draft {len(calls)}"

    return write


def judge_sequence(*reports):
    it = iter(reports)
    return lambda request, draft: next(it)


def run(graph, payload, thread="t1"):
    return graph.invoke(payload, {"configurable": {"thread_id": thread}})


def test_good_first_draft_goes_to_human_and_approves():
    calls = []
    graph = build_graph(fake_writer(calls), judge_sequence(GOOD), checkpointer=InMemorySaver())

    result = run(graph, {"request": REQUEST})
    assert result["__interrupt__"][0].value["draft"] == "draft 1"

    result = run(graph, Command(resume={"action": "approve"}))
    assert result["status"] == "approved"
    assert result["draft"] == "draft 1"
    assert len(calls) == 1


def test_failed_check_revises_with_judge_feedback():
    calls = []
    graph = build_graph(fake_writer(calls), judge_sequence(RUDE, GOOD), human_review=False)

    result = graph.invoke({"request": REQUEST})
    assert result["status"] == "approved"
    assert result["draft"] == "draft 2"
    assert calls == [None, "- Too blunt"]


def test_stops_after_max_revisions():
    calls = []
    graph = build_graph(fake_writer(calls), judge_sequence(*[RUDE] * 10), human_review=False)

    result = graph.invoke({"request": REQUEST})
    assert result["status"] == "gave_up"
    assert result["revisions"] == MAX_REVISIONS
    assert len(calls) == MAX_REVISIONS + 1


def test_human_feedback_triggers_another_revision():
    calls = []
    graph = build_graph(fake_writer(calls), judge_sequence(GOOD, GOOD), checkpointer=InMemorySaver())

    run(graph, {"request": REQUEST})
    result = run(graph, Command(resume={"action": "revise", "feedback": "Make it shorter"}))
    assert result["__interrupt__"][0].value["draft"] == "draft 2"
    assert calls[-1] == "Make it shorter"

    result = run(graph, Command(resume={"action": "approve"}))
    assert result["status"] == "approved"
