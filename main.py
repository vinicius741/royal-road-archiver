import re
import typer
import os
import traceback
import time
# Add import for the new function in the crawler
from core.crawler import download_story, fetch_story_metadata_and_first_chapter
from core.processor import process_story_chapters
from core.epub_builder import build_epubs_for_story

app = typer.Typer(help="CLI for downloading and processing stories from Royal Road.", no_args_is_help=True)

def is_overview_url(url: str) -> bool:
    """Checks if the URL is likely an overview page (does not contain /chapter/)."""
    return "/chapter/" not in url and "/fiction/" in url

@app.command(name="crawl")
def crawl_story_command(
    story_url: str = typer.Argument(..., help="The full URL of the story's overview page OR the first chapter."),
    output_folder: str = typer.Option(
        "downloaded_stories",
        "--out",
        "-o",
        help="Base folder where the raw HTML chapters of the story will be saved (a subfolder with the story name will be created here)."
    )
):
    """
    Downloads a story from Royal Road chapter by chapter as raw HTML files.
    Can start from a story overview page or a direct first chapter URL.
    """
    typer.echo(f"Starting download for URL: {story_url}")
    abs_output_folder = os.path.abspath(output_folder)

    if not os.path.exists(abs_output_folder):
        try:
            os.makedirs(abs_output_folder, exist_ok=True)
            typer.echo(f"Base output folder for downloads created/confirmed: {abs_output_folder}")
        except OSError as e:
            typer.secho(f"Error creating base output folder '{abs_output_folder}': {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Using existing base output folder for downloads: {abs_output_folder}")

    first_chapter_to_crawl = story_url
    story_slug_for_folder = None

    if is_overview_url(story_url):
        typer.echo("URL detected as overview page. Fetching metadata...")
        metadata = fetch_story_metadata_and_first_chapter(story_url)
        if not metadata or not metadata.get('first_chapter_url'):
            typer.secho("Failed to get metadata or first chapter URL from overview page.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        first_chapter_to_crawl = metadata['first_chapter_url']
        story_slug_for_folder = metadata.get('story_slug') # Will use the slug to name the folder
        typer.echo(f"First chapter found: {first_chapter_to_crawl}")
        if story_slug_for_folder:
            typer.echo(f"Story slug for folder name: {story_slug_for_folder}")
    else:
        typer.echo("URL detected as chapter page.")
        # Tries to extract the slug from the chapter URL for the folder name
        try:
            story_slug_for_folder = story_url.split('/fiction/')[1].split('/')[1]
            story_slug_for_folder = re.sub(r'[\\/*?:"<>|]', "", story_slug_for_folder)
            story_slug_for_folder = re.sub(r'\s+', '_', story_slug_for_folder)[:100]
            typer.echo(f"Inferred slug from chapter URL: {story_slug_for_folder}")
        except IndexError:
            typer.echo("Could not infer slug from chapter URL. Folder name may be generic.")


    try:
        # download_story now expects the base folder (abs_output_folder) and slug_override
        # It will create abs_output_folder/story_slug_for_folder
        downloaded_story_path = download_story(first_chapter_to_crawl, abs_output_folder, story_slug_override=story_slug_for_folder)
        if downloaded_story_path:
            typer.secho(f"\nDownload of raw HTML files completed successfully at: {downloaded_story_path}", fg=typer.colors.GREEN)
        else:
            typer.secho("\nDownload seems to have failed or did not return a path.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    except ImportError:
         typer.secho("Critical Error: Could not import 'download_story' or 'fetch_story_metadata_and_first_chapter' from 'core.crawler'. Check the file and project structure.", fg=typer.colors.RED)
         raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"\nAn error occurred during download: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

# ... (process command unchanged)
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

    # The subfolder name in processed_stories will be the same as in downloaded_stories
    story_slug_for_processed = os.path.basename(abs_input_story_folder)
    specific_output_folder = os.path.join(abs_output_base_folder, story_slug_for_processed)


    if not os.path.exists(specific_output_folder):
        try:
            os.makedirs(specific_output_folder, exist_ok=True)
            typer.echo(f"Base output folder for processed files created: {specific_output_folder}")
        except OSError as e:
            typer.secho(f"Error creating specific output folder for processed files '{specific_output_folder}': {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Using existing specific output folder for processed files: {specific_output_folder}")

    try:
        # Passes the specific folder where the processed story chapters should go
        process_story_chapters(abs_input_story_folder, specific_output_folder)
        typer.secho(f"\nProcessing of story chapters concluded successfully! Output in: {specific_output_folder}", fg=typer.colors.GREEN)
        return specific_output_folder # Returns the path for use in full-process
    except ImportError:
         typer.secho("Critical Error: Could not import 'process_story_chapters' from 'core.processor'. Check file and project structure.", fg=typer.colors.RED)
         raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"\nAn error occurred during processing: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc()) # For more detailed error
        raise typer.Exit(code=1)


# ... (build-epub command unchanged)
@app.command(name="build-epub")
def build_epub_command(
    input_processed_folder: str = typer.Argument(..., help="Path to the folder containing the CLEANED HTML chapters of a single story (e.g., processed_stories/story-slug)."),
    output_epub_folder: str = typer.Option(
        "epubs",
        "--out",
        "-o",
        help="Base folder where the generated EPUB files will be saved."
    ),
    chapters_per_epub: int = typer.Option(
        50,
        "--chapters-per-epub",
        "-c",
        min=0, # 0 for a single EPUB with all chapters
        help="Number of chapters to include in each EPUB file. Set to 0 for a single EPUB."
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

    # If chapters_per_epub is 0, pass a very large number for ebooklib to make just one.
    # The internal logic of build_epubs_for_story already handles this if chapters_per_epub is large.
    effective_chapters_per_epub = chapters_per_epub if chapters_per_epub > 0 else 999999


    try:
        build_epubs_for_story(
            input_folder=abs_input_processed_folder, # This is the specific folder for the processed story
            output_folder=abs_output_epub_folder,   # EPUBs are saved directly here
            chapters_per_epub=effective_chapters_per_epub,
            author_name=author_name,
            story_title=story_title # The story title should already be correct here
        )
        typer.secho(f"\nEPUB generation concluded successfully! Files in {abs_output_epub_folder}", fg=typer.colors.GREEN)
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
    story_url: str = typer.Argument(..., help="The full URL of the story's overview page OR the first chapter."),
    chapters_per_epub: int = typer.Option(
        50,
        "--chapters-per-epub",
        "-c",
        min=0,
        help="Number of chapters to include in each EPUB file. Set to 0 for a single EPUB."
    ),
    author_name_param: str = typer.Option(
        None, # Default to None so we can know if it was provided
        "--author",
        "-a",
        help="Author name for EPUB metadata. If not provided and fetching from overview, uses that."
    ),
    story_title_param: str = typer.Option(
        None, # Default to None
        "--title",
        "-t",
        help="Story title for EPUB metadata. If not provided and fetching from overview, uses that."
    )
):
    """
    Performs the full sequence: download, process, and build EPUB for a story.
    Can start from a story overview page or a direct first chapter URL.
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

    # Variables to store metadata and paths
    first_chapter_to_crawl = story_url
    final_story_title = story_title_param
    final_author_name = author_name_param
    story_slug_for_folders = None # Will be used to create consistent subfolders

    # --- 0. Fetch metadata if overview URL ---
    if is_overview_url(story_url):
        typer.echo(f"\n--- Step 0: Fetching metadata from {story_url} ---")
        metadata = fetch_story_metadata_and_first_chapter(story_url)
        if not metadata or not metadata.get('first_chapter_url'):
            typer.secho("Failed to get metadata or first chapter URL. Aborting.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        first_chapter_to_crawl = metadata['first_chapter_url']
        story_slug_for_folders = metadata.get('story_slug', None)

        if not final_story_title and metadata.get('story_title') != "Unknown Title":
            final_story_title = metadata['story_title']
            typer.echo(f"Story title (from overview): {final_story_title}")
        if not final_author_name and metadata.get('author_name') != "Unknown Author":
            final_author_name = metadata['author_name']
            typer.echo(f"Author (from overview): {final_author_name}")

        typer.echo(f"First chapter URL for download: {first_chapter_to_crawl}")
        if story_slug_for_folders:
             typer.echo(f"Story slug for folders: {story_slug_for_folders}")

    else: # It's a direct chapter URL
        typer.echo("Provided URL is a direct chapter URL.")
        # Tries to extract the slug from the chapter URL for the folder name
        try:
            slug_parts = first_chapter_to_crawl.split('/fiction/')[1].split('/')
            if len(slug_parts) > 1:
                story_slug_for_folders = re.sub(r'[\\/*?:"<>|]', "", slug_parts[1])
                story_slug_for_folders = re.sub(r'\s+', '_', story_slug_for_folders)[:100]
                typer.echo(f"Inferred slug from chapter URL for folders: {story_slug_for_folders}")
        except IndexError:
            typer.echo("Could not infer slug from chapter URL for folder name.")


    # If the slug has not yet been defined (e.g., invalid chapter URL or overview failed to extract)
    # or if the title/author were not defined and were not provided.
    if not story_slug_for_folders:
        # Generates a slug based on the title if available, or a generic slug
        if final_story_title and final_story_title != "Archived Royal Road Story":
            story_slug_for_folders = re.sub(r'[\\/*?:"<>|]', "", final_story_title)
            story_slug_for_folders = re.sub(r'\s+', '_', story_slug_for_folders).lower()[:50]
            typer.echo(f"Slug for folders generated from title: {story_slug_for_folders}")
        else:
            story_slug_for_folders = f"story_{int(time.time())}" # Very generic fallback
            typer.echo(f"WARNING: Using generic slug for folders: {story_slug_for_folders}")


    # Defines defaults if not yet filled by metadata or parameters
    if not final_story_title:
        # If the slug was well defined and the title was not, try to use the slug as a basis for the title
        if story_slug_for_folders and not story_slug_for_folders.startswith("story_"):
             final_story_title = story_slug_for_folders.replace('-', ' ').replace('_', ' ').title()
             typer.echo(f"EPUB title (inferred from slug): {final_story_title}")
        else:
            final_story_title = "Archived Royal Road Story" # Typer default
            typer.echo(f"EPUB title (default): {final_story_title}")

    if not final_author_name:
        final_author_name = "Royal Road Archiver" # Typer default
        typer.echo(f"EPUB author (default): {final_author_name}")


    # --- 1. Download Step ---
    typer.echo(f"\n--- Step 1: Downloading chapters from {first_chapter_to_crawl} ---")
    typer.echo(f"Raw HTML chapters will be saved in a subfolder under: {abs_download_base_folder}")

    story_specific_download_folder = None
    try:
        # download_story will create the subfolder {story_slug_for_folders} inside abs_download_base_folder
        story_specific_download_folder = download_story(first_chapter_to_crawl, abs_download_base_folder, story_slug_override=story_slug_for_folders)
        if not story_specific_download_folder or not os.path.isdir(story_specific_download_folder):
            typer.secho("Error: The story download folder was not created or returned correctly.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        typer.secho(f"Download successful. Content saved in: {story_specific_download_folder}", fg=typer.colors.GREEN)

    except Exception as e:
        typer.secho(f"\nAn error occurred during the download step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)


    # --- 2. Process Step ---
    typer.echo(f"\n--- Step 2: Processing story chapters from {story_specific_download_folder} ---")
    # The processed folder will be abs_processed_base_folder/story_slug_for_folders
    story_specific_processed_folder = os.path.join(abs_processed_base_folder, story_slug_for_folders)
    typer.echo(f"Processed chapters will be saved in: {story_specific_processed_folder}")

    try:
        # process_story_chapters receives the input folder (download) and the specific output folder for the processed story
        process_story_chapters(story_specific_download_folder, story_specific_processed_folder)
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

    effective_chapters_per_epub = chapters_per_epub if chapters_per_epub > 0 else 999999

    try:
        success = build_epubs_for_story(
            input_folder=story_specific_processed_folder, # Specific folder with cleaned HTMLs
            output_folder=abs_epub_base_folder,       # Base folder to save the .epub files
            chapters_per_epub=effective_chapters_per_epub,
            author_name=final_author_name,
            story_title=final_story_title
        )
        if success:
            typer.secho(f"\nEPUB generation successful. Files saved in: {abs_epub_base_folder}", fg=typer.colors.GREEN)
        else:
            typer.secho(f"\nEPUB generation was skipped or failed. Check logs above.", fg=typer.colors.YELLOW)
    except Exception as e:
        typer.secho(f"\nAn error occurred during the EPUB building step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

    typer.secho("\n--- Full process completed successfully! ---", fg=typer.colors.CYAN)


if __name__ == "__main__":
    # Add to allow import random in crawler.py if it's there
    import random
    app()