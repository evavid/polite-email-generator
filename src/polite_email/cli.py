"""Interactive command-line run: draft → automatic tone check → you approve or ask for changes."""

import argparse
import uuid

from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from polite_email.graph import build_graph


def ask(label: str, value: str | None) -> str:
    return value if value else input(f"{label}: ").strip()


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Draft a polite email with a self-checking agent.")
    parser.add_argument("--recipient")
    parser.add_argument("--affiliation")
    parser.add_argument("--purpose")
    parser.add_argument("--signature")
    args = parser.parse_args()

    request = {
        "recipient": ask("Recipient", args.recipient),
        "affiliation": ask("Affiliation", args.affiliation),
        "purpose": ask("What should the email say", args.purpose),
        "signature": ask("Signature", args.signature),
    }

    graph = build_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke({"request": request}, config)

    while "__interrupt__" in result:
        review = result["__interrupt__"][0].value
        report = review["report"]
        print("\n" + "-" * 60)
        print(review["draft"])
        print("-" * 60)
        print(f"Tone check: {'polite' if report['polite'] else 'NOT polite'}, score {report['score']}/5, "
              f"{review['revisions']} automatic revision(s)")
        for issue in report["issues"]:
            print(f"  · {issue}")

        answer = input("\nPress Enter to approve, or type what to change: ").strip()
        resume = {"action": "approve"} if not answer else {"action": "revise", "feedback": answer}
        result = graph.invoke(Command(resume=resume), config)

    print("\nApproved. Final email:\n")
    print(result["draft"])


if __name__ == "__main__":
    main()
