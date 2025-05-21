# main.py
import typer
import os
import traceback # Keep for detailed error reporting in crawl

from core.crawler import download_story
from core.processor import process_story_chapters
from core.epub_builder import build_epubs_for_story # New import

app = typer.Typer(help="CLI for downloading and processing stories from Royal Road.", no_args_is_help=True)

@app.command(name="crawl")
def crawl_story_command(
    first_chapter_url: str = typer.Argument(..., help="The full URL of the first chapter of the story."),
    output_folder: str = typer.Option(
        "downloaded_stories",
        "--out",
        "-o",
        help="Base folder where the raw HTML chapters of the story will be saved (a subfolder with the story name will be created here)."
    )
):
    """
    Downloads a story from Royal Road chapter by chapter as raw HTML files.
    """
    typer.echo(f"Initiating download for story from: {first_chapter_url}")

    abs_output_folder = os.path.abspath(output_folder)

    # The download_story function itself creates a subfolder for the story
    # So, abs_output_folder is the base where 'story-slug' subfolder will be created.
    if not os.path.exists(abs_output_folder):
        try:
            os.makedirs(abs_output_folder, exist_ok=True)
            typer.echo(f"Base output folder for downloads created/confirmed: {abs_output_folder}")
        except OSError as e:
            typer.secho(f"Error creating base output folder '{abs_output_folder}': {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Using existing base output folder for downloads: {abs_output_folder}")

    try:
        download_story(first_chapter_url, abs_output_folder)
        typer.secho("\nDownload of story raw HTML files concluded successfully!", fg=typer.colors.GREEN)
    except ImportError:
         typer.secho("Critical Error: Could not import 'download_story' from 'core.crawler'. Check the file and project structure.", fg=typer.colors.RED)
         raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"\nAn error occurred during download: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

@app.command(name="process")
def process_story_command(
    input_story_folder: str = typer.Argument(..., help="Path to the folder containing the raw HTML chapters of a single story (e.g., downloaded_stories/story-slug)."),
    output_base_folder: str = typer.Option(
        "processed_stories",
        "--out",
        "-o",
        help="Base folder where the cleaned HTML chapters will be saved (a subfolder with the story name will be created here)."
    )
):
    """
    Processes raw HTML chapters of a story: cleans HTML, removes unwanted tags,
    and saves the processed chapters.
    """
    typer.echo(f"Initiating processing for story files in: {input_story_folder}")

    abs_input_story_folder = os.path.abspath(input_story_folder)
    abs_output_base_folder = os.path.abspath(output_base_folder)

    if not os.path.isdir(abs_input_story_folder):
        typer.secho(f"Error: Input story folder '{abs_input_story_folder}' not found or is not a directory.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not os.path.exists(abs_output_base_folder):
        try:
            os.makedirs(abs_output_base_folder, exist_ok=True)
            typer.echo(f"Base output folder for processed files created: {abs_output_base_folder}")
        except OSError as e:
            typer.secho(f"Error creating base output folder for processed files '{abs_output_base_folder}': {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Using existing base output folder for processed files: {abs_output_base_folder}")

    try:
        process_story_chapters(abs_input_story_folder, abs_output_base_folder)
        typer.secho("\nProcessing of story chapters concluded successfully!", fg=typer.colors.GREEN)
    except ImportError:
         typer.secho("Critical Error: Could not import 'process_story_chapters' from 'core.processor'. Check file and project structure.", fg=typer.colors.RED)
         raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"\nAn error occurred during processing: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc()) # For more detailed error
        raise typer.Exit(code=1)

@app.command(name="build-epub")
def build_epub_command(
    input_processed_folder: str = typer.Argument(..., help="Path to the folder containing the CLEANED HTML chapters of a single story (e.g., processed_stories/story-slug)."),
    output_epub_folder: str = typer.Option(
        "epubs",
        "--out",
        "-o",
        help="Base folder where the generated EPUB files will be saved (a subfolder with the story name might be created here if needed)."
    ),
    chapters_per_epub: int = typer.Option(
        50,
        "--chapters-per-epub",
        "-c",
        min=1,
        help="Number of chapters to include in each EPUB file. Set to 0 or a very large number for a single EPUB."
    ),
    author_name: str = typer.Option(
        "Royal Road Archiver",
        "--author",
        "-a",
        help="Author name to be used in the EPUB metadata."
    ),
    story_title: str = typer.Option(
        "Archived Royal Road Story",
        "--title",
        "-t",
        help="Story title to be used in the EPUB metadata. If not provided, it will attempt to extract from the first chapter file."
    )
):
    """
    Generates EPUB files from cleaned HTML chapters.
    """
    typer.echo(f"Initiating EPUB generation for story files in: {input_processed_folder}")

    abs_input_processed_folder = os.path.abspath(input_processed_folder)
    abs_output_epub_folder = os.path.abspath(output_epub_folder)

    if not os.path.isdir(abs_input_processed_folder):
        typer.secho(f"Error: Input processed folder '{abs_input_processed_folder}' not found or is not a directory.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not os.path.exists(abs_output_epub_folder):
        try:
            os.makedirs(abs_output_epub_folder, exist_ok=True)
            typer.echo(f"Base output folder for EPUBs created: {abs_output_epub_folder}")
        except OSError as e:
            typer.secho(f"Error creating base output folder for EPUBs '{abs_output_epub_folder}': {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Using existing base output folder for EPUBs: {abs_output_epub_folder}")

    try:
        build_epubs_for_story(
            input_folder=abs_input_processed_folder,
            output_folder=abs_output_epub_folder,
            chapters_per_epub=chapters_per_epub,
            author_name=author_name,
            story_title=story_title
        )
        typer.secho("\nEPUB generation concluded successfully!", fg=typer.colors.GREEN)
    except ImportError:
         typer.secho("Critical Error: Could not import 'build_epubs_for_story' from 'core.epub_builder'. Check file and project structure.", fg=typer.colors.RED)
         raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"\nAn error occurred during EPUB generation: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

@app.command()
def test():
    """
    A simple test command for Typer setup.
    """
    typer.echo("CLI 'test' command executed successfully!")

if __name__ == "__main__":
    app()