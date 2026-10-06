from pydantic import BaseModel, ConfigDict, Field, model_validator


class PayloadRequest(BaseModel):
    list_1: list[str] = Field(..., min_length=1)
    list_2: list[str] = Field(..., min_length=1)

    @model_validator(mode="after")
    def check_equal_lengths(self) -> "PayloadRequest":
        if len(self.list_1) != len(self.list_2):
            raise ValueError("list_1 and list_2 must have the same length")
        return self


class PayloadResponse(BaseModel):
    id: str
    request_hash: str
    output: list[str]

    model_config = ConfigDict(from_attributes=True)
