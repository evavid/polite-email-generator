from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class EmailRequest(TypedDict):
    recipient: str  # e.g. "Prof. Novak"
    affiliation: str  # e.g. "University of Ljubljana"
    purpose: str  # what the email needs to say, in the user's own words
    signature: str  # how to sign off, e.g. "Eva Vidmar"


class ToneReport(BaseModel):
    """The judge's verdict on a draft."""

    polite: bool = Field(description="True if the email is polite, respectful and free of harsh wording.")
    score: int = Field(ge=1, le=5, description="Overall quality: 1 = unusable, 5 = ready to send.")
    issues: list[str] = Field(
        default_factory=list,
        description="Concrete problems to fix (tone, missing information, structure). Empty if none.",
    )


class State(TypedDict, total=False):
    request: EmailRequest
    draft: str
    report: ToneReport
    # What the next revision should address: the judge's issues or the human's feedback.
    feedback: str
    revisions: int
    status: Literal["drafting", "awaiting_review", "approved", "gave_up"]
