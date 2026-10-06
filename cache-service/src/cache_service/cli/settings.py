from cache_service.config import Settings


class CLISettings(Settings):
    """Pydantic Settings for the CLI (database connection, etc.).

    Argument parsing (--input/--output/--json/--repeat) is handled separately
    by argparse in cli/main.py; this class only covers environment-based
    deployment configuration shared with the web app.
    """


cli_settings = CLISettings()
