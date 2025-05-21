import typer
import os
import traceback

from core.crawler import download_story # fetch_story_metadata_and_first_chapter is now used by cli_helpers
from core.processor import process_story_chapters
from core.epub_builder import build_epubs_for_story
from core.cli_helpers import (
    resolve_crawl_url_and_metadata,
    determine_story_slug_for_folders,
    finalize_epub_metadata,
)

app = typer.Typer(help="CLI for downloading and processing stories from Royal Road.", no_args_is_help=True)

def _ensure_base_folder(folder_path: str) -> str:
    """Ensures a base folder exists, creating it if necessary."""
    abs_folder_path = os.path.abspath(folder_path)
    if not os.path.exists(abs_folder_path):
        try:
            os.makedirs(abs_folder_path, exist_ok=True)
            typer.echo(f"Base folder created/confirmed: {abs_folder_path}")
        except OSError as e:
            typer.secho(f"Error creating base folder '{abs_folder_path}': {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Using existing base folder: {abs_folder_path}")
    return abs_folder_path


@app.command(name="crawl")
def crawl_story_command(
    story_url: str = typer.Argument(..., help="The full URL of the story's overview page OR a chapter URL."),
    output_folder: str = typer.Option(
        "downloaded_stories",
        "--out",
        "-o",
        help="Base folder where the raw HTML chapters will be saved (a subfolder with the story name will be created here)."
    ),
    start_chapter_url: str = typer.Option(
        None,
        "--start-chapter-url",
        "-scu",
        help="Optional URL of a specific chapter to start downloading from. Overrides the first chapter if story_url is an overview or a different chapter."
    )
):
    """
    Downloads a story from Royal Road chapter by chapter as raw HTML files.
    """
    typer.echo(f"Starting crawl command for story URL: {story_url}")
    abs_output_folder = _ensure_base_folder(output_folder)

    crawl_entry_point_url, fetched_metadata, initial_slug = resolve_crawl_url_and_metadata(
        story_url_arg=story_url,
        start_chapter_url_param=start_chapter_url
    )

    if not crawl_entry_point_url:
        typer.secho("Critical: Could not determine a valid URL to start crawling. Exiting.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    # For crawl, slug is primarily for the folder name. Title from params isn't available here.
    story_slug_for_folder = determine_story_slug_for_folders(
        story_url_arg=story_url,
        start_chapter_url_param=start_chapter_url,
        fetched_metadata=fetched_metadata,
        initial_slug_from_resolve=initial_slug,
        title_param=None # Not applicable for crawl command's slug determination directly
    )
    
    typer.echo(f"Final crawl will start from: {crawl_entry_point_url} into subfolder related to slug: {story_slug_for_folder}")

    try:
        downloaded_story_path = download_story(
            first_chapter_url=crawl_entry_point_url, 
            output_folder=abs_output_folder, 
            story_slug_override=story_slug_for_folder
        )
        if downloaded_story_path:
            typer.secho(f"\nDownload of raw HTML files completed successfully at: {downloaded_story_path}", fg=typer.colors.GREEN)
        else:
            typer.secho("\nDownload seems to have failed or did not return a path.", fg=typer.colors.RED)
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
    abs_output_base_folder = _ensure_base_folder(output_base_folder)

    if not os.path.isdir(abs_input_story_folder):
        typer.secho(f"Error: Input story folder '{abs_input_story_folder}' not found or is not a directory.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    story_slug_for_processed = os.path.basename(os.path.normpath(abs_input_story_folder))
    specific_output_folder = os.path.join(abs_output_base_folder, story_slug_for_processed)

    # Ensure specific output folder for processed files exists
    _ensure_base_folder(specific_output_folder) # _ensure_base_folder can also create specific ones

    try:
        process_story_chapters(abs_input_story_folder, specific_output_folder)
        typer.secho(f"\nProcessing of story chapters concluded successfully! Output in: {specific_output_folder}", fg=typer.colors.GREEN)
        # return specific_output_folder # Not typically returned from Typer commands directly to CLI
    except Exception as e:
        typer.secho(f"\nAn error occurred during processing: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc()) 
        raise typer.Exit(code=1)


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
        min=0, 
        help="Number of chapters to include in each EPUB file. Set to 0 for a single EPUB."
    ),
    author_name: str = typer.Option(
        "Royal Road Archiver", # Default if not trying to infer
        "--author",
        "-a",
        help="Author name to be used in the EPUB metadata."
    ),
    story_title: str = typer.Option(
        "Archived Royal Road Story", # Default if not trying to infer
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
    abs_output_epub_folder = _ensure_base_folder(output_epub_folder)

    if not os.path.isdir(abs_input_processed_folder):
        typer.secho(f"Error: Input processed folder '{abs_input_processed_folder}' not found or is not a directory.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    # chapters_per_epub=0 means all in one for build_epubs_for_story
    # The epub_builder handles the logic of '0 means all chapters' effectively.

    try:
        build_epubs_for_story(
            input_folder=abs_input_processed_folder, 
            output_folder=abs_output_epub_folder,   
            chapters_per_epub=chapters_per_epub, # Pass directly
            author_name=author_name,
            story_title=story_title 
        )
        typer.secho(f"\nEPUB generation concluded successfully! Files in {abs_output_epub_folder}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"\nAn error occurred during EPUB generation: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)


@app.command(name="full-process")
def full_process_command(
    story_url: str = typer.Argument(..., help="The full URL of the story's overview page OR a chapter URL."),
    start_chapter_url: str = typer.Option(
        None,
        "--start-chapter-url",
        "-scu",
        help="Optional URL of a specific chapter to start downloading from."
    ),
    chapters_per_epub: int = typer.Option(
        50,
        "--chapters-per-epub",
        "-c",
        min=0,
        help="Number of chapters per EPUB. 0 for a single EPUB."
    ),
    author_name_param: str = typer.Option(
        None, 
        "--author",
        "-a",
        help="Author name for EPUB. Overrides fetched metadata."
    ),
    story_title_param: str = typer.Option(
        None, 
        "--title",
        "-t",
        help="Story title for EPUB. Overrides fetched metadata."
    )
):
    """
    Performs the full sequence: download, process, and build EPUB.
    """
    download_base_folder_name = "downloaded_stories"
    processed_base_folder_name = "processed_stories"
    epub_base_folder_name = "epubs"

    abs_download_base_folder = _ensure_base_folder(download_base_folder_name)
    abs_processed_base_folder = _ensure_base_folder(processed_base_folder_name)
    abs_epub_base_folder = _ensure_base_folder(epub_base_folder_name)
    
    typer.echo(f"\n--- Step 0: Initializing and resolving URLs/metadata from {story_url} ---")
    actual_crawl_start_url, fetched_metadata, initial_slug = resolve_crawl_url_and_metadata(
        story_url_arg=story_url,
        start_chapter_url_param=start_chapter_url
    )

    if not actual_crawl_start_url:
        typer.secho("Critical: Could not determine a valid URL to start crawling for full-process. Exiting.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    story_slug_for_folders = determine_story_slug_for_folders(
        story_url_arg=story_url,
        start_chapter_url_param=start_chapter_url,
        fetched_metadata=fetched_metadata,
        initial_slug_from_resolve=initial_slug,
        title_param=story_title_param
    )

    final_story_title, final_author_name = finalize_epub_metadata(
        title_param=story_title_param,
        author_param=author_name_param,
        fetched_metadata=fetched_metadata,
        story_slug=story_slug_for_folders
    )

    # --- 1. Download Step ---
    typer.echo(f"\n--- Step 1: Downloading chapters starting from {actual_crawl_start_url} ---")
    story_specific_download_folder = os.path.join(abs_download_base_folder, story_slug_for_folders)
    try:
        # download_story creates the story_specific_download_folder using story_slug_for_folders
        returned_download_path = download_story(
            actual_crawl_start_url, 
            abs_download_base_folder, # Base folder for downloads
            story_slug_override=story_slug_for_folders
        )
        if not returned_download_path or not os.path.isdir(returned_download_path):
            typer.secho(f"Error: Download step did not return a valid directory path. Expected: '{story_specific_download_folder}', Got: '{returned_download_path}'", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        # Use the returned path as it's confirmed by the crawler
        story_specific_download_folder = returned_download_path 
        typer.secho(f"Download successful. Raw content in: {story_specific_download_folder}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"An error occurred during the download step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

    # --- 2. Process Step ---
    typer.echo(f"\n--- Step 2: Processing story chapters from {story_specific_download_folder} ---")
    story_specific_processed_folder = os.path.join(abs_processed_base_folder, story_slug_for_folders)
    # Ensure the specific target folder for processed files exists before calling process.
    _ensure_base_folder(story_specific_processed_folder)
    try:
        process_story_chapters(story_specific_download_folder, story_specific_processed_folder)
        if not os.path.isdir(story_specific_processed_folder): # Double check
             typer.secho(f"Error: Processed story folder '{story_specific_processed_folder}' was not created/found after processing.", fg=typer.colors.RED)
             raise typer.Exit(code=1)
        typer.secho(f"Processing successful. Cleaned content in: {story_specific_processed_folder}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"An error occurred during the processing step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

    # --- 3. Build EPUB Step ---
    typer.echo(f"\n--- Step 3: Building EPUB(s) from {story_specific_processed_folder} ---")
    try:
        build_epubs_for_story(
            input_folder=story_specific_processed_folder,
            output_folder=abs_epub_base_folder,  
            chapters_per_epub=chapters_per_epub, # Pass directly
            author_name=final_author_name,
            story_title=final_story_title
        )
        typer.secho(f"EPUB generation process finished. Files should be in: {abs_epub_base_folder}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"An error occurred during the EPUB building step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

    typer.secho("\n--- Full process completed! ---", fg=typer.colors.CYAN)


if __name__ == "__main__":
    app()