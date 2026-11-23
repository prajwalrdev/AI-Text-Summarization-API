"""
Pydantic schemas for request validation and response serialization.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SummarizeRequest(BaseModel):
    """
    Request model for the text summarization endpoint.
    Validates that the input text is provided and not empty or whitespace.
    """

    text: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="The source text to be summarized. Cannot be empty or whitespace.",
        examples=["Type your text here..."],
    )

    @field_validator("text")
    @classmethod
    def validate_text_not_blank(cls, value: str) -> str:
        """
        Validate that the input text contains actual content, not just whitespace.
        """
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("The 'text' field cannot be empty or contain only whitespace.")
        return stripped_value


class SummarizeResponse(BaseModel):
    """
    Response model for the text summarization endpoint.
    Guarantees a consistent JSON structure returning the summary.
    """

    summary: str = Field(
        ...,
        description="The AI-generated concise summary of the input text.",
        examples=["The AI-generated summary will appear here."],
    )


class SummaryRecord(BaseModel):
    """
    Schema representing a stored summary record in the database.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique database identifier.")
    original_text: str = Field(..., description="The original submitted text.")
    generated_summary: str = Field(..., description="The AI-generated summary.")
    created_at: datetime = Field(..., description="Timestamp when the summary was saved.")


class HealthResponse(BaseModel):
    """
    Response model for the health check endpoint.
    """

    status: str = Field(
        "healthy",
        description="Current health status of the service.",
        examples=["healthy"],
    )
    version: str = Field(
        "1.0.0",
        description="Current version of the API.",
        examples=["1.0.0"],
    )
