import typer
import os
import shutil
import traceback
from typing import Optional

from core.crawler import download_story # fetch_story_metadata_and_first_chapter is now used by cli_helpers
from core.processor import process_story_chapters
from core.epub_builder import build_epubs_for_story
from core.cli_helpers import (
    resolve_crawl_url_and_metadata,
    determine_story_slug_for_folders,
    finalize_epub_metadata,
)
from core.gdrive_uploader import authenticate_gdrive, upload_story_files, APP_ROOT_FOLDER_NAME

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

    crawl_entry_point_url, fetched_metadata, initial_slug, resolved_overview_url = resolve_crawl_url_and_metadata(
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
            story_slug_override=story_slug_for_folder,
            overview_url=resolved_overview_url,
            story_title=fetched_metadata.get('story_title') if fetched_metadata else "Unknown Title",
            author_name=fetched_metadata.get('author_name') if fetched_metadata else "Unknown Author"
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
    ),
    cover_url_param: Optional[str] = typer.Option(
        None,
        "--cover-url",
        "-cu",
        help="URL of the cover image for the EPUB."
    ),
    description_param: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Description for the EPUB metadata."
    ),
    tags_param: Optional[str] = typer.Option(
        None,
        "--tags",
        "-tg",
        help="Comma-separated list of tags/genres for the EPUB metadata."
    ),
    publisher_param: Optional[str] = typer.Option(
        None,
        "--publisher",
        "-p",
        help="Publisher name for the EPUB metadata."
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
    
    story_slug = os.path.basename(os.path.normpath(abs_input_processed_folder))
    story_specific_output_folder = os.path.join(abs_output_epub_folder, story_slug)
    _ensure_base_folder(story_specific_output_folder)
    
    # chapters_per_epub=0 means all in one for build_epubs_for_story
    # The epub_builder handles the logic of '0 means all chapters' effectively.

    try:
        build_epubs_for_story(
            input_folder=abs_input_processed_folder, 
            output_folder=story_specific_output_folder,   
            chapters_per_epub=chapters_per_epub, # Pass directly
            author_name=author_name,
            story_title=story_title,
            cover_image_url=cover_url_param,
            story_description=description_param,
            tags=tags_param.split(',') if tags_param else None,
            publisher_name=publisher_param
        )
        typer.secho(f"\nEPUB generation concluded successfully! Files in {story_specific_output_folder}", fg=typer.colors.GREEN)
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
    ),
    keep_intermediate_files: bool = typer.Option(
        False,
        "--keep-intermediate-files",
        help="If True, preserves the downloaded and processed chapter folders. Defaults to False (deleting them)."
    )
):
    """
    Performs the full sequence: download, process, and build EPUB.
    """
    download_base_folder_name = "downloaded_stories"
    processed_base_folder_name = "processed_stories"
    """
    Performs the full sequence: download, process, and build EPUB.
    """
    
    init_data = _initialize_full_process(
        story_url=story_url,
        start_chapter_url=start_chapter_url,
        story_title_param=story_title_param,
        author_name_param=author_name_param
    )

    if not init_data.get("actual_crawl_start_url"): # Check for critical failure from init
        # Error message already printed by _initialize_full_process
        raise typer.Exit(code=1)

    # --- 1. Download Step ---
    typer.echo(f"\n--- Step 1: Downloading chapters starting from {init_data['actual_crawl_start_url']} ---")
    story_specific_download_folder = _run_download_step(
        actual_crawl_start_url=init_data['actual_crawl_start_url'],
        abs_download_base_folder=init_data['abs_download_base_folder'],
        story_slug_for_folders=init_data['story_slug_for_folders'],
        resolved_overview_url=init_data['resolved_overview_url'],
        story_title=init_data['final_story_title'], # Using finalized title
        author_name=init_data['final_author_name']  # Using finalized author
    )

    # --- 2. Process Step ---
    typer.echo(f"\n--- Step 2: Processing story chapters from {story_specific_download_folder} ---")
    story_specific_processed_folder = _run_process_step(
        story_specific_download_folder=story_specific_download_folder,
        abs_processed_base_folder=init_data['abs_processed_base_folder'],
        story_slug_for_folders=init_data['story_slug_for_folders']
    )

    # --- 3. Build EPUB Step ---
    typer.echo(f"\n--- Step 3: Building EPUB(s) from {story_specific_processed_folder} ---")
    story_specific_epub_output_folder = _run_build_epub_step(
        story_specific_processed_folder=story_specific_processed_folder,
        abs_epub_base_folder=init_data['abs_epub_base_folder'],
        story_slug_for_folders=init_data['story_slug_for_folders'],
        chapters_per_epub=chapters_per_epub,
        final_author_name=init_data['final_author_name'],
        final_story_title=init_data['final_story_title'],
        final_cover_url=init_data['final_cover_url'],
        final_description=init_data['final_description'],
        final_tags=init_data['final_tags'],
        final_publisher=init_data['final_publisher']
    )

    # --- 4. Cleanup Step ---
    _run_cleanup_step(
        keep_intermediate_files=keep_intermediate_files,
        story_specific_download_folder=story_specific_download_folder,
        story_specific_processed_folder=story_specific_processed_folder
    )

    typer.secho("\n--- Full process completed! ---", fg=typer.colors.CYAN)


# Helper functions for full_process_command
def _initialize_full_process(
    story_url: str,
    start_chapter_url: Optional[str],
    story_title_param: Optional[str],
    author_name_param: Optional[str]
) -> dict:
    """Handles Step 0: Initialization, folder setup, URL resolving, metadata finalization."""
    download_base_folder_name = "downloaded_stories"
    processed_base_folder_name = "processed_stories"
    epub_base_folder_name = "epubs"

    abs_download_base_folder = _ensure_base_folder(download_base_folder_name)
    abs_processed_base_folder = _ensure_base_folder(processed_base_folder_name)
    abs_epub_base_folder = _ensure_base_folder(epub_base_folder_name)
    
    typer.echo(f"\n--- Step 0: Initializing and resolving URLs/metadata from {story_url} ---")
    actual_crawl_start_url, fetched_metadata, initial_slug, resolved_overview_url = resolve_crawl_url_and_metadata(
        story_url_arg=story_url,
        start_chapter_url_param=start_chapter_url
    )

    if not actual_crawl_start_url:
        typer.secho("Critical: Could not determine a valid URL to start crawling for full-process. Exiting.", fg=typer.colors.RED)
        # Return a dictionary indicating failure to the main command
        return {
            "actual_crawl_start_url": None,
            "resolved_overview_url": None, # Ensure all expected keys are present on failure
            "story_slug_for_folders": None,
            "abs_download_base_folder": abs_download_base_folder,
            "abs_processed_base_folder": abs_processed_base_folder,
            "abs_epub_base_folder": abs_epub_base_folder,
            "final_story_title": "Unknown Title",
            "final_author_name": "Unknown Author",
            "final_cover_url": None,
            "final_description": None,
            "final_tags": [],
            "final_publisher": None
        }

    story_slug_for_folders = determine_story_slug_for_folders(
        story_url_arg=story_url,
        start_chapter_url_param=start_chapter_url,
        fetched_metadata=fetched_metadata,
        initial_slug_from_resolve=initial_slug,
        title_param=story_title_param # This is story_title_param from full_process_command
    )

    final_story_title, final_author_name, final_cover_url, final_description, final_tags, final_publisher = finalize_epub_metadata(
        title_param=story_title_param, # This is story_title_param from full_process_command
        author_param=author_name_param, # This is author_name_param from full_process_command
        cover_url_param=None, 
        description_param=None,
        tags_param=None, 
        publisher_param=None,
        fetched_metadata=fetched_metadata,
        story_slug=story_slug_for_folders
    )

    return {
        "actual_crawl_start_url": actual_crawl_start_url,
        "story_slug_for_folders": story_slug_for_folders,
        "abs_download_base_folder": abs_download_base_folder,
        "abs_processed_base_folder": abs_processed_base_folder,
        "abs_epub_base_folder": abs_epub_base_folder,
        "final_story_title": final_story_title,
        "final_author_name": final_author_name,
        "final_cover_url": final_cover_url,
        "final_description": final_description,
        "final_tags": final_tags,
        "final_publisher": final_publisher,
        "resolved_overview_url": resolved_overview_url # Added
    }

def _run_download_step(
    actual_crawl_start_url: str,
    abs_download_base_folder: str,
    story_slug_for_folders: str,
    resolved_overview_url: Optional[str], # New
    story_title: str, # New
    author_name: str # New
) -> str:
    """Handles Step 1: Downloading chapters."""
    story_specific_download_folder = os.path.join(abs_download_base_folder, story_slug_for_folders)
    try:
        returned_download_path = download_story(
            first_chapter_url=actual_crawl_start_url,
            output_folder=abs_download_base_folder,
            story_slug_override=story_slug_for_folders,
            overview_url=resolved_overview_url,
            story_title=story_title,
            author_name=author_name
        )
        if not returned_download_path or not os.path.isdir(returned_download_path):
            typer.secho(f"Error: Download step did not return a valid directory path. Expected: '{story_specific_download_folder}', Got: '{returned_download_path}'", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        story_specific_download_folder = returned_download_path 
        typer.secho(f"Download successful. Raw content in: {story_specific_download_folder}", fg=typer.colors.GREEN)
        return story_specific_download_folder
    except Exception as e:
        typer.secho(f"An error occurred during the download step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

def _run_process_step(
    story_specific_download_folder: str,
    abs_processed_base_folder: str,
    story_slug_for_folders: str
) -> str:
    """Handles Step 2: Processing story chapters."""
    story_specific_processed_folder = os.path.join(abs_processed_base_folder, story_slug_for_folders)
    _ensure_base_folder(story_specific_processed_folder)
    try:
        process_story_chapters(story_specific_download_folder, story_specific_processed_folder)
        if not os.path.isdir(story_specific_processed_folder): 
             typer.secho(f"Error: Processed story folder '{story_specific_processed_folder}' was not created/found after processing.", fg=typer.colors.RED)
             raise typer.Exit(code=1)
        typer.secho(f"Processing successful. Cleaned content in: {story_specific_processed_folder}", fg=typer.colors.GREEN)
        return story_specific_processed_folder
    except Exception as e:
        typer.secho(f"An error occurred during the processing step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

def _run_build_epub_step(
    story_specific_processed_folder: str,
    abs_epub_base_folder: str,
    story_slug_for_folders: str,
    chapters_per_epub: int,
    final_author_name: str,
    final_story_title: str,
    final_cover_url: Optional[str],
    final_description: Optional[str],
    final_tags: list,
    final_publisher: Optional[str]
) -> str:
    """Handles Step 3: Building EPUB(s)."""
    story_specific_epub_output_folder = os.path.join(abs_epub_base_folder, story_slug_for_folders)
    _ensure_base_folder(story_specific_epub_output_folder)
    try:
        build_epubs_for_story(
            input_folder=story_specific_processed_folder,
            output_folder=story_specific_epub_output_folder,  
            chapters_per_epub=chapters_per_epub, 
            author_name=final_author_name,
            story_title=final_story_title,
            cover_image_url=final_cover_url,
            story_description=final_description,
            tags=final_tags, 
            publisher_name=final_publisher
        )
        typer.secho(f"EPUB generation process finished. Files should be in: {story_specific_epub_output_folder}", fg=typer.colors.GREEN)
        return story_specific_epub_output_folder
    except Exception as e:
        typer.secho(f"An error occurred during the EPUB building step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

def _run_cleanup_step(
    keep_intermediate_files: bool,
    story_specific_download_folder: str,
    story_specific_processed_folder: str
):
    """Handles Step 4: Cleaning up intermediate files."""
    if not keep_intermediate_files:
        typer.echo("\n--- Step 4: Cleaning up intermediate files ---")
        try:
            if os.path.exists(story_specific_download_folder):
                shutil.rmtree(story_specific_download_folder)
                typer.echo(f"Successfully deleted raw download folder: {story_specific_download_folder}")
            else:
                typer.echo(f"Raw download folder not found (already deleted or never created): {story_specific_download_folder}")

            if os.path.exists(story_specific_processed_folder):
                shutil.rmtree(story_specific_processed_folder)
                typer.echo(f"Successfully deleted processed content folder: {story_specific_processed_folder}")
            else:
                typer.echo(f"Processed content folder not found (already deleted or never created): {story_specific_processed_folder}")
        except OSError as e:
            typer.secho(f"Error during cleanup of intermediate folders: {e}", fg=typer.colors.RED)
            typer.echo(f"Please manually check and remove if necessary:\n- {story_specific_download_folder}\n- {story_specific_processed_folder}")
    else:
        typer.echo("\n--- Step 4: Skipping cleanup of intermediate files as per --keep-intermediate-files option. ---")
        typer.echo(f"Raw download folder retained at: {story_specific_download_folder}")
        typer.echo(f"Processed content folder retained at: {story_specific_processed_folder}")


@app.command(name="upload-to-gdrive")
def upload_to_gdrive_command(
    story_slug_or_all: str = typer.Argument(
        ...,
        help="The slug of the story to upload, or 'ALL' to upload all stories found in the 'epubs' and 'metadata_store' directories."
    )
):
    """
    Uploads EPUB files and download_status.json for a story (or all stories) to Google Drive.
    Ensure 'credentials.json' from Google Cloud Console is in the project root.
    """
    typer.echo("Attempting to authenticate with Google Drive...")
    try:
        service = authenticate_gdrive()
        if not service:
            typer.secho("Failed to authenticate with Google Drive. Please ensure 'credentials.json' is set up correctly and you've completed the authentication flow.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        typer.secho("Successfully authenticated with Google Drive.", fg=typer.colors.GREEN)
        typer.echo(f"Files will be uploaded to a root folder named: '{APP_ROOT_FOLDER_NAME}'")

        if story_slug_or_all.upper() == "ALL":
            typer.echo("Attempting to upload all stories...")
            epubs_base_dir = "epubs"
            metadata_base_dir = "metadata_store"
            story_slugs = set()

            if os.path.exists(epubs_base_dir) and os.path.isdir(epubs_base_dir):
                for slug in os.listdir(epubs_base_dir):
                    if os.path.isdir(os.path.join(epubs_base_dir, slug)):
                        story_slugs.add(slug)
            
            if os.path.exists(metadata_base_dir) and os.path.isdir(metadata_base_dir):
                for slug in os.listdir(metadata_base_dir):
                    if os.path.isdir(os.path.join(metadata_base_dir, slug)):
                        story_slugs.add(slug)

            if not story_slugs:
                typer.secho("No story slugs found in 'epubs' or 'metadata_store' directories.", fg=typer.colors.YELLOW)
                return

            typer.echo(f"Found {len(story_slugs)} potential story slug(s): {', '.join(sorted(list(story_slugs)))}")
            for slug in sorted(list(story_slugs)):
                typer.echo(f"--- Uploading story: {slug} ---")
                upload_story_files(service, slug)
                typer.echo(f"--- Finished uploading story: {slug} ---\n")
            typer.secho("All stories processed.", fg=typer.colors.GREEN)

        else:
            story_slug = story_slug_or_all
            typer.echo(f"Attempting to upload story: {story_slug}")
            upload_story_files(service, story_slug)
            typer.secho(f"Finished uploading story: {story_slug}", fg=typer.colors.GREEN)

    except FileNotFoundError as e: # Specifically for credentials.json missing
        typer.secho(f"Configuration error: {e}", fg=typer.colors.RED)
        typer.secho("Please ensure 'credentials.json' is in the project root and you have authenticated if it's your first time.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"An error occurred during the Google Drive upload process: {e}", fg=typer.colors.RED)
        # import traceback
        # typer.echo(traceback.format_exc()) # Optional: for more detailed error during dev
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()