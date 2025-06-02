import typer
import os

DEBUG_MODE = os.environ.get("APP_DEBUG_MODE", "False").lower() == "true"

def log_info(message: str):
    """Prints an informational message."""
    typer.echo(message)

def log_warning(message: str):
    """Prints a warning message."""
    typer.secho(message, fg=typer.colors.YELLOW)

def log_error(message: str):
    """Prints an error message."""
    typer.secho(message, fg=typer.colors.RED)

def log_debug(message: str):
    """Prints a debug message if DEBUG_MODE is enabled."""
    if DEBUG_MODE:
        typer.secho(message, fg=typer.colors.BRIGHT_BLACK)

def log_success(message: str):
    """Prints a success message."""
    typer.secho(message, fg=typer.colors.GREEN)
