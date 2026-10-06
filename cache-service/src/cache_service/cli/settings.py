from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class CLISettings(BaseSettings):
    """Submit two lists of strings to the cache service and print the generated payload.

    Prints one JSON object per iteration, one per line, to --output.
    """

    # ``-h`` is reserved for ``--help``, so the host's short option is ``-H``
    # (the assignment text assigns ``-h`` to both). Matching is case-sensitive
    # so ``-H`` and ``-h`` stay distinct.
    model_config = SettingsConfigDict(
        case_sensitive=True,
        cli_prog_name="cache-cli",
        cli_exit_on_error=False,
    )

    host: str = Field(
        "http://localhost:8000",
        validation_alias=AliasChoices("H", "host"),
        description="URL of the cache service API",
    )
    repeat: int = Field(
        1,
        ge=1,
        validation_alias=AliasChoices("r", "repeat"),
        description="Number of iterations; each one submits the request and reads the payload back",
    )
    input: str | None = Field(
        None,
        validation_alias=AliasChoices("i", "input"),
        description="JSON input file, or '-' for standard input",
    )
    json_data: str | None = Field(
        None,
        validation_alias=AliasChoices("j", "json"),
        description="JSON input given directly as an argument; mutually exclusive with --input",
    )
    output: str = Field(
        "-",
        validation_alias=AliasChoices("o", "output"),
        description="Output file, or '-' for standard output (one JSON object per iteration, one per line)",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Only command-line arguments are honoured: generic variables such as HOST
        # commonly exist in the environment and must not silently redirect requests.
        return (init_settings,)

    @model_validator(mode="after")
    def require_exactly_one_input(self) -> "CLISettings":
        if self.input is not None and self.json_data is not None:
            raise ValueError("--input and --json are mutually exclusive")
        if self.input is None and self.json_data is None:
            raise ValueError("one of --input or --json is required")
        return self
