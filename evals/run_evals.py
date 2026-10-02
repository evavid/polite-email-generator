"""Run the agent over the eval dataset in LangSmith and score every email.

    uv run python evals/run_evals.py                 # creates the dataset on first run
    uv run python evals/run_evals.py --prefix sonnet # label the experiment

Results appear in LangSmith under Datasets & Experiments → polite-email-generator.
"""

import argparse
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import Client
from pydantic import BaseModel, Field

from polite_email.graph import build_graph

load_dotenv()

DATASET = "polite-email-generator"
DATA_FILE = Path(__file__).with_name("dataset.jsonl")
GREETING = re.compile(r"^(dear|hello|hi|good (morning|afternoon|evening)|spoštovan|pozdravljen|živjo|draga?\b)", re.I)


def ensure_dataset(client: Client) -> None:
    if client.has_dataset(dataset_name=DATASET):
        return
    dataset = client.create_dataset(DATASET, description="Email requests, including rude and non-English ones.")
    for line in DATA_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            client.create_example(inputs=row["inputs"], outputs=row["outputs"], dataset_id=dataset.id)
    print(f"Created dataset '{DATASET}'.")


# --- target: the agent without the human step ---------------------------------------------

agent = build_graph(human_review=False)


def target(inputs: dict) -> dict:
    result = agent.invoke({"request": inputs})
    return {"email": result["draft"], "status": result["status"], "revisions": result["revisions"]}


# --- evaluators ---------------------------------------------------------------------------


def has_greeting_and_signature(inputs: dict, outputs: dict) -> dict:
    lines = [l.strip() for l in outputs["email"].splitlines() if l.strip()]
    greeting = bool(lines) and bool(GREETING.match(lines[0]))
    first_name = inputs["signature"].split(",")[0].split()[0]
    signed = any(first_name in l for l in lines[-3:])
    return {"key": "greeting_and_signature", "score": greeting and signed}


def no_placeholders(outputs: dict) -> dict:
    return {"key": "no_placeholders", "score": not re.search(r"\[[^\]]{2,}\]", outputs["email"])}


def mentions_key_facts(outputs: dict, reference_outputs: dict) -> dict:
    facts = reference_outputs.get("must_mention", [])
    text = outputs["email"].lower()
    hits = sum(any(alt.lower() in text for alt in fact.split("|")) for fact in facts)
    return {"key": "key_facts", "score": hits / len(facts) if facts else 1.0}


def revisions_needed(outputs: dict) -> dict:
    return {"key": "revisions", "score": outputs["revisions"]}


class Grade(BaseModel):
    score: int = Field(ge=1, le=5, description="1 = would not send, 5 = would send as is")
    reasoning: str


# A separate, stronger grader than the in-loop judge, so the agent isn't marking its own homework.
grader = ChatAnthropic(model=os.getenv("EVAL_MODEL", "claude-sonnet-5-5"), temperature=0).with_structured_output(Grade, method="json_schema")


def would_send(inputs: dict, outputs: dict) -> dict:
    grade = grader.invoke(
        [
            SystemMessage(
                "You grade emails written on someone's behalf. A 5 is polite, clear, achieves the purpose, "
                "keeps the facts, fits the recipient and language, and could be sent without edits."
            ),
            HumanMessage(f"Request: {json.dumps(inputs, ensure_ascii=False)}\n\nEmail:\n{outputs['email']}"),
        ]
    )
    return {"key": "would_send", "score": (grade.score - 1) / 4, "comment": grade.reasoning}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="polite-email", help="experiment name prefix")
    args = parser.parse_args()

    client = Client()
    ensure_dataset(client)
    client.evaluate(
        target,
        data=DATASET,
        evaluators=[has_greeting_and_signature, no_placeholders, mentions_key_facts, revisions_needed, would_send],
        experiment_prefix=args.prefix,
        max_concurrency=2,
    )


if __name__ == "__main__":
    main()
