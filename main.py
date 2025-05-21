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

@app.command(name="full-process")
def full_process_command(
    first_chapter_url: str = typer.Argument(..., help="The full URL of the first chapter of the story."),
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
        help="Story title to be used in the EPUB metadata. If not provided, 'build-epub' will attempt to extract from the first chapter file of the processed content."
    )
):
    """
    Performs the full sequence: download, process, and build EPUB for a story.
    """
    download_base_folder = "downloaded_stories"
    processed_base_folder = "processed_stories"
    epub_base_folder = "epubs"

    # Ensure base folders exist
    for folder in [download_base_folder, processed_base_folder, epub_base_folder]:
        abs_folder = os.path.abspath(folder)
        if not os.path.exists(abs_folder):
            try:
                os.makedirs(abs_folder, exist_ok=True)
                typer.echo(f"Base folder created/confirmed: {abs_folder}")
            except OSError as e:
                typer.secho(f"Error creating base folder '{abs_folder}': {e}", fg=typer.colors.RED)
                raise typer.Exit(code=1)
        else:
            typer.echo(f"Using existing base folder: {abs_folder}")

    abs_download_base_folder = os.path.abspath(download_base_folder)
    abs_processed_base_folder = os.path.abspath(processed_base_folder)
    abs_epub_base_folder = os.path.abspath(epub_base_folder)

    story_specific_download_folder = None
    story_slug = None

    # --- 1. Download Step ---
    typer.echo(f"\n--- Step 1: Downloading story from {first_chapter_url} ---")
    typer.echo(f"Raw HTML chapters will be saved in a subfolder under: {abs_download_base_folder}")

    # Determine story_specific_download_folder by observing changes in download_base_folder
    # as download_story does not return the path or slug.
    try:
        # Ensure download_base_folder exists before listing
        if not os.path.exists(abs_download_base_folder):
            os.makedirs(abs_download_base_folder, exist_ok=True)
            typer.echo(f"Created download base folder: {abs_download_base_folder}")

        before_download_content = set(os.listdir(abs_download_base_folder))
        
        download_story(first_chapter_url, abs_download_base_folder) # This function prints its own progress

        after_download_content = set(os.listdir(abs_download_base_folder))
        new_folders = after_download_content - before_download_content

        if len(new_folders) == 1:
            story_slug = new_folders.pop()
            story_specific_download_folder = os.path.join(abs_download_base_folder, story_slug)
            typer.secho(f"Download successful. Story content saved in: {story_specific_download_folder}", fg=typer.colors.GREEN)
            typer.echo(f"Inferred story slug: {story_slug}")
        elif len(new_folders) == 0:
            # This might happen if the folder already existed and download_story populated it.
            # We need to infer the slug from the URL if possible, as crawler.py does.
            # This is a fallback, not ideal.
            try:
                # Attempt to mimic slug extraction from crawler.py
                # Example URL: https://www.royalroad.com/fiction/12345/story-name-here/chapter/56789/chapter-title
                temp_slug = first_chapter_url.split('/fiction/')[1].split('/')[1]
                # Sanitize it the same way crawler.py's _sanitize_filename would (simplified)
                temp_slug_sanitized = re.sub(r'[\\/*?:"<>|]', "", temp_slug)
                temp_slug_sanitized = re.sub(r'\s+', '_', temp_slug_sanitized)[:100]

                potential_folder = os.path.join(abs_download_base_folder, temp_slug_sanitized)
                if os.path.isdir(potential_folder):
                    story_slug = temp_slug_sanitized
                    story_specific_download_folder = potential_folder
                    typer.secho(f"Download folder '{story_specific_download_folder}' likely pre-existed or no new folder detected. Inferred slug: {story_slug}", fg=typer.colors.YELLOW)
                else:
                    typer.secho("Error: No new folder created by download_story and could not reliably determine existing story folder.", fg=typer.colors.RED)
                    raise typer.Exit(code=1)
            except Exception as e:
                typer.secho(f"Error: Could not determine story specific download folder. {e}", fg=typer.colors.RED)
                raise typer.Exit(code=1)

        else: # More than one new folder, ambiguous
            typer.secho(f"Error: Ambiguous state. Multiple new folders found in {abs_download_base_folder} after download: {new_folders}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    except Exception as e:
        typer.secho(f"\nAn error occurred during the download step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

    if not story_specific_download_folder or not story_slug:
        typer.secho("Critical Error: Could not determine story slug or download folder. Aborting.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # --- 2. Process Step ---
    typer.echo(f"\n--- Step 2: Processing story chapters from {story_specific_download_folder} ---")
    typer.echo(f"Processed chapters will be saved in a subfolder under: {abs_processed_base_folder}")
    # process_story_chapters will create processed_base_folder/story_slug
    # So, story_specific_processed_folder will be os.path.join(abs_processed_base_folder, story_slug)

    try:
        process_story_chapters(story_specific_download_folder, abs_processed_base_folder) # This function prints its own progress
        story_specific_processed_folder = os.path.join(abs_processed_base_folder, story_slug)
        if not os.path.isdir(story_specific_processed_folder):
             typer.secho(f"Error: Processed story folder '{story_specific_processed_folder}' was not created as expected.", fg=typer.colors.RED)
             raise typer.Exit(code=1)
        typer.secho(f"Processing successful. Cleaned content saved in: {story_specific_processed_folder}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"\nAn error occurred during the processing step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

    # --- 3. Build EPUB Step ---
    typer.echo(f"\n--- Step 3: Building EPUB(s) from {story_specific_processed_folder} ---")
    typer.echo(f"EPUB files will be saved in: {abs_epub_base_folder}")
    # build_epubs_for_story saves EPUBs directly into the output_folder provided.
    # It does not create a story_slug subfolder within its output_folder.

    try:
        # The story_title parameter for build_epubs_for_story is important.
        # If the user provided one, use it. Otherwise, build_epubs_for_story has its own fallback.
        effective_story_title = story_title
        if story_title == "Archived Royal Road Story": # Default value, try to use slug
            # A slightly better default title if not provided by user
            effective_story_title = story_slug.replace('-', ' ').title()
            typer.echo(f"Using inferred title for EPUB: '{effective_story_title}' (can be overridden with --title)")


        build_epubs_for_story(
            input_folder=story_specific_processed_folder,
            output_folder=abs_epub_base_folder, # This is the base folder, EPUBs go here directly
            chapters_per_epub=chapters_per_epub,
            author_name=author_name,
            story_title=effective_story_title # Pass the user-provided or inferred title
        )
        typer.secho(f"\nEPUB generation successful. Files saved in: {abs_epub_base_folder}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"\nAn error occurred during the EPUB building step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

    typer.secho("\n--- Full process completed successfully! ---", fg=typer.colors.CYAN)

if __name__ == "__main__":
    app()