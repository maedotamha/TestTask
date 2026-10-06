from pydantic import BaseModel, Field, model_validator


class PayloadRequest(BaseModel):
    list_1: list[str] = Field(..., min_length=1)
    list_2: list[str] = Field(..., min_length=1)

    @model_validator(mode="after")
    def check_equal_lengths(self) -> "PayloadRequest":
        if len(self.list_1) != len(self.list_2):
            raise ValueError("list_1 and list_2 must have the same length")
        return self


class PayloadCreatedResponse(BaseModel):
    """Confirmation returned by POST; the id is stable for identical requests."""

    id: str
    message: str


class PayloadResponse(BaseModel):
    """The generated payload: transformed strings interleaved and joined with ', '."""

    output: str
