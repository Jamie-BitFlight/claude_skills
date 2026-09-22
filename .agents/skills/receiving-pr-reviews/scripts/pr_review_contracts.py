"""Provider-neutral targets, actions, and mutation results."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, RootModel, field_validator, model_validator

ProviderName = Literal["github", "gitlab"]
ReviewTransport = Literal["github_cli", "github_mcp", "gitlab_cli"]


def validate_non_blank(value: str) -> str:
    """Validate shared action text once.

    Returns:
        The original non-blank value.
    """
    if not value.strip():
        message = "action text must contain non-whitespace text"
        raise ValueError(message)
    return value


NonBlankText = Annotated[str, Field(min_length=1), AfterValidator(validate_non_blank)]


class RepositoryTarget(BaseModel):
    """A forge repository selected before any read or mutation occurs."""

    model_config = ConfigDict(strict=True)

    provider: ProviderName
    hostname: str = Field(min_length=1)
    full_name: str = Field(min_length=3)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        """Require unambiguous namespace and repository segments.

        Returns:
            The validated repository full name.
        """
        if value.startswith("/") or value.endswith("/") or "//" in value or "/" not in value:
            message = "repository full_name must contain non-empty namespace and repository segments"
            raise ValueError(message)
        return value


class ChangeRequestTarget(BaseModel):
    """One pull or merge request within a resolved repository target."""

    model_config = ConfigDict(strict=True)

    repository: RepositoryTarget
    number: int = Field(gt=0)


class ReplyAction(BaseModel):
    """Post an inline response to the authorized review input."""

    model_config = ConfigDict(strict=True)

    kind: Literal["reply"] = "reply"
    body: NonBlankText


class ResolveAction(BaseModel):
    """Resolve the authorized review input after communication succeeds."""

    model_config = ConfigDict(strict=True)

    kind: Literal["resolve"] = "resolve"


class TopLevelCommentAction(BaseModel):
    """Post a change-request-level response with stable input references."""

    model_config = ConfigDict(strict=True)

    kind: Literal["comment"] = "comment"
    body: NonBlankText
    references: list[str] = Field(default_factory=list)

    @field_validator("references")
    @classmethod
    def validate_references(cls, value: list[str]) -> list[str]:
        """Reject empty or duplicate references before provider mutation.

        Returns:
            The validated stable references.
        """
        if any(not reference.strip() for reference in value):
            message = "comment references must be non-empty"
            raise ValueError(message)
        if len(value) != len(set(value)):
            message = "comment references must be unique"
            raise ValueError(message)
        return value


ReviewAction = Annotated[ReplyAction | ResolveAction | TopLevelCommentAction, Field(discriminator="kind")]


class ReviewActionResult(BaseModel):
    """Validated provider result for one mutation."""

    provider: ProviderName
    action_kind: Literal["reply", "resolve", "comment"]
    success: bool
    provider_object_id: str | None = None
    resolved: bool | None = None
    raw: dict[str, object]


class BatchReviewAction(BaseModel):
    """One validated reply-and-resolve entry from a batch input file."""

    model_config = ConfigDict(strict=True)

    input_id: str = Field(min_length=1)
    body: NonBlankText


class BatchReviewActions(RootModel[list[BatchReviewAction]]):
    """A complete batch validated before its first provider mutation."""

    @model_validator(mode="after")
    def require_unique_inputs(self) -> BatchReviewActions:
        """Reject ambiguous duplicate work before mutation.

        Returns:
            This validated batch.
        """
        input_ids = [entry.input_id for entry in self.root]
        if len(input_ids) != len(set(input_ids)):
            message = "batch input_id values must be unique"
            raise ValueError(message)
        return self
