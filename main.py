import typer
import os
import shutil
import traceback
from typing import Optional, Callable

from core.crawler import download_story # fetch_story_metadata_and_first_chapter is now used by cli_helpers
from core.processor import process_story_chapters
from core.epub_builder import build_epubs_for_story
from core.cli_helpers import (
    resolve_crawl_url_and_metadata,
    determine_story_slug_for_folders,
    finalize_epub_metadata,
)

app = typer.Typer(help="CLI for downloading and processing stories from Royal Road.", no_args_is_help=True)

# Define a type for the logger callback for clarity
LoggerCallback = Optional[Callable[[str, Optional[str]], None]]

def _ensure_base_folder(folder_path: str, logger_callback: LoggerCallback = None) -> str:
    """Ensures a base folder exists, creating it if necessary."""
    abs_folder_path = os.path.abspath(folder_path)
    log_message = lambda msg, style=None: typer.echo(msg) if logger_callback is None else logger_callback(msg, style)
    
    if not os.path.exists(abs_folder_path):
        try:
            os.makedirs(abs_folder_path, exist_ok=True)
            log_message(f"Base folder created/confirmed: {abs_folder_path}", "green")
        except OSError as e:
            log_message(f"Error creating base folder '{abs_folder_path}': {e}", "red")
            # Re-raise for _execute_full_process to catch, or Typer for direct calls
            raise 
    else:
        log_message(f"Using existing base folder: {abs_folder_path}", "blue")
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
    def cli_logger(message: str, style: Optional[str] = None):
        if style:
            typer.secho(message, fg=getattr(typer.colors, style.upper(), typer.colors.WHITE))
        else:
            typer.echo(message)

    cli_logger(f"Starting crawl command for story URL: {story_url}")
    try:
        abs_output_folder = _ensure_base_folder(output_folder, cli_logger)

        crawl_entry_point_url, fetched_metadata, initial_slug = resolve_crawl_url_and_metadata(
            story_url_arg=story_url,
            start_chapter_url_param=start_chapter_url,
            logger_callback=cli_logger
        )

        if not crawl_entry_point_url:
            cli_logger("Critical: Could not determine a valid URL to start crawling. Exiting.", "red")
            raise typer.Exit(code=1)
        
        story_slug_for_folder = determine_story_slug_for_folders(
            story_url_arg=story_url,
            start_chapter_url_param=start_chapter_url,
            fetched_metadata=fetched_metadata,
            initial_slug_from_resolve=initial_slug,
            title_param=None,
            logger_callback=cli_logger
        )
        
        cli_logger(f"Final crawl will start from: {crawl_entry_point_url} into subfolder related to slug: {story_slug_for_folder}")

        downloaded_story_path = download_story(
            first_chapter_url=crawl_entry_point_url, 
            output_folder=abs_output_folder, 
            story_slug_override=story_slug_for_folder,
            logger_callback=cli_logger
        )
        if downloaded_story_path:
            cli_logger(f"\nDownload of raw HTML files completed successfully at: {downloaded_story_path}", "green")
        else:
            cli_logger("\nDownload seems to have failed or did not return a path.", "red")
            raise typer.Exit(code=1)
    except typer.Exit:
        raise # Re-raise Typer Exit exceptions
    except Exception as e:
        cli_logger(f"\nAn error occurred during download: {e}", "red")
        cli_logger(traceback.format_exc(), "yellow")
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
    def cli_logger(message: str, style: Optional[str] = None):
        if style:
            typer.secho(message, fg=getattr(typer.colors, style.upper(), typer.colors.WHITE))
        else:
            typer.echo(message)

    cli_logger(f"Initiating processing for story files in: {input_story_folder}")
    try:
        abs_input_story_folder = os.path.abspath(input_story_folder)
        abs_output_base_folder = _ensure_base_folder(output_base_folder, cli_logger)

        if not os.path.isdir(abs_input_story_folder):
            cli_logger(f"Error: Input story folder '{abs_input_story_folder}' not found or is not a directory.", "red")
            raise typer.Exit(code=1)

        story_slug_for_processed = os.path.basename(os.path.normpath(abs_input_story_folder))
        specific_output_folder = os.path.join(abs_output_base_folder, story_slug_for_processed)

        _ensure_base_folder(specific_output_folder, cli_logger) 

        process_story_chapters(abs_input_story_folder, specific_output_folder, logger_callback=cli_logger)
        cli_logger(f"\nProcessing of story chapters concluded successfully! Output in: {specific_output_folder}", "green")
    except typer.Exit:
        raise
    except Exception as e:
        cli_logger(f"\nAn error occurred during processing: {e}", "red")
        cli_logger(traceback.format_exc(), "yellow")
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
    def cli_logger(message: str, style: Optional[str] = None):
        if style:
            typer.secho(message, fg=getattr(typer.colors, style.upper(), typer.colors.WHITE))
        else:
            typer.echo(message)

    cli_logger(f"Initiating EPUB generation for story files in: {input_processed_folder}")
    try:
        abs_input_processed_folder = os.path.abspath(input_processed_folder)
        abs_output_epub_folder = _ensure_base_folder(output_epub_folder, cli_logger)

        if not os.path.isdir(abs_input_processed_folder):
            cli_logger(f"Error: Input processed folder '{abs_input_processed_folder}' not found or is not a directory.", "red")
            raise typer.Exit(code=1)
        
        story_slug = os.path.basename(os.path.normpath(abs_input_processed_folder))
        story_specific_output_folder = os.path.join(abs_output_epub_folder, story_slug)
        _ensure_base_folder(story_specific_output_folder, cli_logger)
        
        build_epubs_for_story(
            input_folder=abs_input_processed_folder, 
            output_folder=story_specific_output_folder,   
            chapters_per_epub=chapters_per_epub, 
            author_name=author_name,
            story_title=story_title,
            logger_callback=cli_logger
        )
        cli_logger(f"\nEPUB generation concluded successfully! Files in {story_specific_output_folder}", "green")
    except typer.Exit:
        raise
    except Exception as e:
        cli_logger(f"\nAn error occurred during EPUB generation: {e}", "red")
        cli_logger(traceback.format_exc(), "yellow")
        raise typer.Exit(code=1)

# --- Refactored Core Logic ---
def _execute_full_process(
    story_url: str,
    start_chapter_url: Optional[str],
    chapters_per_epub: int,
    author_name_param: Optional[str],
    story_title_param: Optional[str],
    keep_intermediate_files: bool,
    download_base_folder_name: str = "downloaded_stories",
    processed_base_folder_name: str = "processed_stories",
    epub_base_folder_name: str = "epubs",
    logger_callback: LoggerCallback = None
) -> tuple[bool, str, Optional[str]]:
    """
    Core logic for the full download, process, and build EPUB sequence.
    Returns a tuple: (success_status, message, output_path).
    """
    log = lambda msg, style=None: logger_callback(msg, style) if logger_callback else typer.echo(msg)

    try:
        abs_download_base_folder = _ensure_base_folder(download_base_folder_name, logger_callback)
        abs_processed_base_folder = _ensure_base_folder(processed_base_folder_name, logger_callback)
        abs_epub_base_folder = _ensure_base_folder(epub_base_folder_name, logger_callback)
        
        log(f"\n--- Step 0: Initializing and resolving URLs/metadata from {story_url} ---", "cyan")
        actual_crawl_start_url, fetched_metadata, initial_slug = resolve_crawl_url_and_metadata(
            story_url_arg=story_url,
            start_chapter_url_param=start_chapter_url,
            logger_callback=logger_callback
        )

        if not actual_crawl_start_url:
            msg = "Critical: Could not determine a valid URL to start crawling for full-process."
            log(msg, "red")
            return False, msg, None

        story_slug_for_folders = determine_story_slug_for_folders(
            story_url_arg=story_url,
            start_chapter_url_param=start_chapter_url,
            fetched_metadata=fetched_metadata,
            initial_slug_from_resolve=initial_slug,
            title_param=story_title_param,
            logger_callback=logger_callback
        )

        final_story_title, final_author_name = finalize_epub_metadata(
            title_param=story_title_param,
            author_param=author_name_param,
            fetched_metadata=fetched_metadata,
            story_slug=story_slug_for_folders,
            logger_callback=logger_callback
        )

        story_specific_download_folder = os.path.join(abs_download_base_folder, story_slug_for_folders)
        story_specific_processed_folder = os.path.join(abs_processed_base_folder, story_slug_for_folders)
        story_specific_epub_output_folder = os.path.join(abs_epub_base_folder, story_slug_for_folders)

        # --- 1. Download Step ---
        log(f"\n--- Step 1: Downloading chapters starting from {actual_crawl_start_url} ---", "cyan")
        returned_download_path = download_story(
            actual_crawl_start_url, 
            abs_download_base_folder, 
            story_slug_override=story_slug_for_folders,
            logger_callback=logger_callback
        )
        if not returned_download_path or not os.path.isdir(returned_download_path):
            msg = f"Error: Download step did not return a valid directory path. Expected: '{story_specific_download_folder}', Got: '{returned_download_path}'"
            log(msg, "red")
            return False, msg, None
        story_specific_download_folder = returned_download_path 
        log(f"Download successful. Raw content in: {story_specific_download_folder}", "green")

        # --- 2. Process Step ---
        log(f"\n--- Step 2: Processing story chapters from {story_specific_download_folder} ---", "cyan")
        _ensure_base_folder(story_specific_processed_folder, logger_callback)
        process_story_chapters(story_specific_download_folder, story_specific_processed_folder, logger_callback=logger_callback)
        if not os.path.isdir(story_specific_processed_folder):
             msg = f"Error: Processed story folder '{story_specific_processed_folder}' was not created/found after processing."
             log(msg, "red")
             return False, msg, None
        log(f"Processing successful. Cleaned content in: {story_specific_processed_folder}", "green")

        # --- 3. Build EPUB Step ---
        log(f"\n--- Step 3: Building EPUB(s) from {story_specific_processed_folder} ---", "cyan")
        _ensure_base_folder(story_specific_epub_output_folder, logger_callback)
        build_epubs_for_story(
            input_folder=story_specific_processed_folder,
            output_folder=story_specific_epub_output_folder,  
            chapters_per_epub=chapters_per_epub,
            author_name=final_author_name,
            story_title=final_story_title,
            logger_callback=logger_callback
        )
        log(f"EPUB generation process finished. Files should be in: {story_specific_epub_output_folder}", "green")

        # --- 4. Cleanup Step ---
        if not keep_intermediate_files:
            log("\n--- Step 4: Cleaning up intermediate files ---", "cyan")
            try:
                if os.path.exists(story_specific_download_folder):
                    shutil.rmtree(story_specific_download_folder)
                    log(f"Successfully deleted raw download folder: {story_specific_download_folder}")
                else:
                    log(f"Raw download folder not found (already deleted or never created): {story_specific_download_folder}", "yellow")

                if os.path.exists(story_specific_processed_folder):
                    shutil.rmtree(story_specific_processed_folder)
                    log(f"Successfully deleted processed content folder: {story_specific_processed_folder}")
                else:
                    log(f"Processed content folder not found (already deleted or never created): {story_specific_processed_folder}", "yellow")
            except OSError as e:
                log(f"Error during cleanup of intermediate folders: {e}", "red")
                log(f"Please manually check and remove if necessary:\n- {story_specific_download_folder}\n- {story_specific_processed_folder}", "yellow")
        else:
            log("\n--- Step 4: Skipping cleanup of intermediate files as per --keep-intermediate-files option. ---", "cyan")
            log(f"Raw download folder retained at: {story_specific_download_folder}")
            log(f"Processed content folder retained at: {story_specific_processed_folder}")

        return True, f"Full process completed successfully! EPUBs in: {story_specific_epub_output_folder}", story_specific_epub_output_folder

    except Exception as e:
        error_msg = f"An unexpected error occurred during the full process: {e}"
        log(error_msg, "red")
        log(traceback.format_exc(), "yellow")
        return False, error_msg, None


@app.command(name="full-process")
def full_process_command(
    story_url: str = typer.Argument(..., help="The full URL of the story's overview page OR a chapter URL."),
    start_chapter_url: Optional[str] = typer.Option(
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
    author_name_param: Optional[str] = typer.Option(
        None, 
        "--author",
        "-a",
        help="Author name for EPUB. Overrides fetched metadata."
    ),
    story_title_param: Optional[str] = typer.Option(
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
    def cli_logger(message: str, style: Optional[str] = None):
        color = None
        if style:
            style_upper = style.upper()
            if hasattr(typer.colors, style_upper):
                color = getattr(typer.colors, style_upper)
        
        if color:
            typer.secho(message, fg=color)
        else:
            typer.echo(message)

    success, message, output_path = _execute_full_process(
        story_url=story_url,
        start_chapter_url=start_chapter_url,
        chapters_per_epub=chapters_per_epub,
        author_name_param=author_name_param,
        story_title_param=story_title_param,
        keep_intermediate_files=keep_intermediate_files,
        logger_callback=cli_logger
    )

    if success:
        cli_logger(f"\n--- Full process completed! Output: {output_path} ---", "cyan")
    else:
        cli_logger(f"\n--- Full process failed: {message} ---", "red")
        raise typer.Exit(code=1)

# --- GUI Command ---
# Import the GUI starter function at the module level
try:
    from gui import start_gui_application
    gui_available = True
except ImportError:
    gui_available = False
    start_gui_application = None # Placeholder

@app.command(name="gui")
def start_gui_command():
    """
    Launches the Graphical User Interface for the story processor.
    Tkinter needs to be available.
    """
    if not gui_available or start_gui_application is None:
        typer.secho("GUI could not be loaded. Please ensure tkinter is installed and gui.py is present.", fg=typer.colors.RED)
        typer.echo("If you are running in an environment without a display (e.g., some servers), the GUI may not be usable.")
        raise typer.Exit(code=1)
    
    typer.echo("Launching GUI...")
    try:
        start_gui_application()
    except Exception as e:
        typer.secho(f"An error occurred while running the GUI: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()