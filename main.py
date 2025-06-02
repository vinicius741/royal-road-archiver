import typer
import os
import shutil
import traceback
from typing import Optional

from core.logging_utils import log_info, log_warning, log_error, log_debug, log_success, DEBUG_MODE
from core.crawler import download_story # fetch_story_metadata_and_first_chapter is now used by cli_helpers
from core.processor import process_story_chapters
from core.epub_builder import build_epubs_for_story
from core.cli_helpers import (
    resolve_crawl_url_and_metadata,
    determine_story_slug_for_folders,
    finalize_epub_metadata,
)
# from core.epub_builder import modify_epub_content # Old import
from core.epub_modifier import modify_epub_content # New import for sentence removal
from core.gdrive_uploader import authenticate_gdrive, upload_story_files, APP_ROOT_FOLDER_NAME
import json # Added for remove-sentences

app = typer.Typer(help="CLI for downloading and processing stories from Royal Road.", no_args_is_help=True)

def _ensure_base_folder(folder_path: str) -> str:
    """Ensures a base folder exists, creating it if necessary."""
    abs_folder_path = os.path.abspath(folder_path)
    if not os.path.exists(abs_folder_path):
        try:
            os.makedirs(abs_folder_path, exist_ok=True)
            log_debug(f"Base folder created/confirmed: {abs_folder_path}")
        except OSError as e:
            log_error(f"Error creating base folder '{abs_folder_path}': {e}")
            raise typer.Exit(code=1)
    else:
        log_debug(f"Using existing base folder: {abs_folder_path}")
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
    log_info(f"Starting crawl command for story URL: {story_url}")
    abs_output_folder = _ensure_base_folder(output_folder)

    crawl_entry_point_url, fetched_metadata, initial_slug, resolved_overview_url = resolve_crawl_url_and_metadata(
        story_url_arg=story_url,
        start_chapter_url_param=start_chapter_url
    )

    if not crawl_entry_point_url:
        log_error("Critical: Could not determine a valid URL to start crawling. Exiting.")
        raise typer.Exit(code=1)
    
    # For crawl, slug is primarily for the folder name. Title from params isn't available here.
    story_slug_for_folder = determine_story_slug_for_folders(
        story_url_arg=story_url,
        start_chapter_url_param=start_chapter_url,
        fetched_metadata=fetched_metadata,
        initial_slug_from_resolve=initial_slug,
        title_param=None # Not applicable for crawl command's slug determination directly
    )
    
    log_debug(f"Final crawl will start from: {crawl_entry_point_url} into subfolder related to slug: {story_slug_for_folder}")

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
            log_success(f"\nDownload of raw HTML files completed successfully at: {downloaded_story_path}")
        else:
            log_error("\nDownload seems to have failed or did not return a path.")
            raise typer.Exit(code=1)
    except Exception as e:
        log_error(f"\nAn error occurred during download: {e}")
        log_debug(traceback.format_exc())
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
    log_info(f"Initiating processing for story files in: {input_story_folder}")

    abs_input_story_folder = os.path.abspath(input_story_folder)
    abs_output_base_folder = _ensure_base_folder(output_base_folder)

    if not os.path.isdir(abs_input_story_folder):
        log_error(f"Error: Input story folder '{abs_input_story_folder}' not found or is not a directory.")
        raise typer.Exit(code=1)

    story_slug_for_processed = os.path.basename(os.path.normpath(abs_input_story_folder))
    specific_output_folder = os.path.join(abs_output_base_folder, story_slug_for_processed)

    # Ensure specific output folder for processed files exists
    _ensure_base_folder(specific_output_folder) # _ensure_base_folder can also create specific ones

    try:
        process_story_chapters(abs_input_story_folder, specific_output_folder)
        log_success(f"\nProcessing of story chapters concluded successfully! Output in: {specific_output_folder}")
        # return specific_output_folder # Not typically returned from Typer commands directly to CLI
    except Exception as e:
        log_error(f"\nAn error occurred during processing: {e}")
        log_debug(traceback.format_exc()) 
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
    log_info(f"Initiating EPUB generation for story files in: {input_processed_folder}")

    abs_input_processed_folder = os.path.abspath(input_processed_folder)
    abs_output_epub_folder = _ensure_base_folder(output_epub_folder)

    if not os.path.isdir(abs_input_processed_folder):
        log_error(f"Error: Input processed folder '{abs_input_processed_folder}' not found or is not a directory.")
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
        log_success(f"\nEPUB generation concluded successfully! Files in {story_specific_output_folder}")
    except Exception as e:
        log_error(f"\nAn error occurred during EPUB generation: {e}")
        log_debug(traceback.format_exc())
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
    ),
    sentence_removal_json_path: Optional[str] = typer.Option(
        "core/default_sentences_to_remove.json",
        "--remove-sentences-json",
        "-rsj",
        help="Optional path to a JSON file with sentences to remove from the final EPUBs. Defaults to core/default_sentences_to_remove.json containing a common boilerplate sentence."
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
    typer.secho(f"\n--- Step 1: Downloading chapters starting from {init_data['actual_crawl_start_url']} ---", fg=typer.colors.CYAN)
    story_specific_download_folder = _run_download_step(
        actual_crawl_start_url=init_data['actual_crawl_start_url'],
        abs_download_base_folder=init_data['abs_download_base_folder'],
        story_slug_for_folders=init_data['story_slug_for_folders'],
        resolved_overview_url=init_data['resolved_overview_url'],
        story_title=init_data['final_story_title'], # Using finalized title
        author_name=init_data['final_author_name']  # Using finalized author
    )

    # --- 2. Process Step ---
    typer.secho(f"\n--- Step 2: Processing story chapters from {story_specific_download_folder} ---", fg=typer.colors.CYAN)
    story_specific_processed_folder = _run_process_step(
        story_specific_download_folder=story_specific_download_folder,
        abs_processed_base_folder=init_data['abs_processed_base_folder'],
        story_slug_for_folders=init_data['story_slug_for_folders']
    )

    # --- 3. Build EPUB Step ---
    typer.secho(f"\n--- Step 3: Building EPUB(s) from {story_specific_processed_folder} ---", fg=typer.colors.CYAN)
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

    # --- Step 3.5: Optional Sentence Removal ---
    if sentence_removal_json_path:
        typer.secho(f"\n--- Step 3.5: Optionally removing sentences based on {sentence_removal_json_path} ---", fg=typer.colors.CYAN)
        if not os.path.exists(sentence_removal_json_path):
            log_warning(f"Sentence removal JSON file not found: {sentence_removal_json_path}. Skipping sentence removal.")
        else:
            sentences_to_remove = None
            try:
                log_info(f"Attempting to load sentences for removal from: {sentence_removal_json_path}")
                with open(sentence_removal_json_path, 'r', encoding='utf-8') as f:
                    sentences_to_remove = json.load(f)
                if not isinstance(sentences_to_remove, list) or not all(isinstance(s, str) for s in sentences_to_remove):
                    log_warning("Content of sentence removal JSON is not a list of strings. Skipping sentence removal.")
                    sentences_to_remove = None # Ensure it's None if not valid
                elif not sentences_to_remove:
                    log_info("Sentence removal JSON file is empty. No sentences to remove.")
                else:
                    log_info(f"Successfully loaded {len(sentences_to_remove)} sentences for removal.")
            except FileNotFoundError: # Should be caught by os.path.exists, but as a fallback
                log_warning(f"Sentence removal JSON file not found (despite earlier check): {sentence_removal_json_path}. Skipping sentence removal.")
            except json.JSONDecodeError as e:
                log_warning(f"Error decoding JSON from {sentence_removal_json_path}: {e}. Skipping sentence removal.")
            except IOError as e:
                log_warning(f"Error reading sentence file {sentence_removal_json_path}: {e}. Skipping sentence removal.")

            if sentences_to_remove and story_specific_epub_output_folder and os.path.isdir(story_specific_epub_output_folder):
                log_info(f"Processing EPUBs in: {story_specific_epub_output_folder} for sentence removal.")
                for item_name in os.listdir(story_specific_epub_output_folder):
                    if item_name.lower().endswith(".epub"):
                        epub_file_path = os.path.join(story_specific_epub_output_folder, item_name)
                        log_info(f"Applying sentence removal to: {epub_file_path}")
                        try:
                            # modify_epub_content logs its own success/failure for the modification part
                            modify_epub_content(epub_file_path, sentences_to_remove)
                        except Exception as e_mod: # Catch unexpected errors from modify_epub_content itself
                            log_error(f"Error during sentence removal for {epub_file_path}: {e_mod}")
                            log_debug(traceback.format_exc())
            elif not sentences_to_remove: # Handles cases where loading failed or file was empty
                 log_info("No valid sentences loaded for removal or file was empty. Proceeding without modifying EPUBs.")
            else:
                log_warning(f"EPUB output folder {story_specific_epub_output_folder} not found or is not a directory. Skipping sentence removal.")
    else:
        log_debug("No sentence removal JSON path provided. Skipping optional sentence removal step.")
    
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
    
    typer.secho(f"\n--- Step 0: Initializing and resolving URLs/metadata from {story_url} ---", fg=typer.colors.CYAN)
    actual_crawl_start_url, fetched_metadata, initial_slug, resolved_overview_url = resolve_crawl_url_and_metadata(
        story_url_arg=story_url,
        start_chapter_url_param=start_chapter_url
    )

    if not actual_crawl_start_url:
        log_error("Critical: Could not determine a valid URL to start crawling for full-process. Exiting.")
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
            log_error(f"Error: Download step did not return a valid directory path. Expected: '{story_specific_download_folder}', Got: '{returned_download_path}'")
            raise typer.Exit(code=1)
        story_specific_download_folder = returned_download_path 
        log_success(f"Download successful. Raw content in: {story_specific_download_folder}")
        return story_specific_download_folder
    except Exception as e:
        log_error(f"An error occurred during the download step: {e}")
        log_debug(traceback.format_exc())
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
             log_error(f"Error: Processed story folder '{story_specific_processed_folder}' was not created/found after processing.")
             raise typer.Exit(code=1)
        log_success(f"Processing successful. Cleaned content in: {story_specific_processed_folder}")
        return story_specific_processed_folder
    except Exception as e:
        log_error(f"An error occurred during the processing step: {e}")
        log_debug(traceback.format_exc())
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
        log_success(f"EPUB generation process finished. Files should be in: {story_specific_epub_output_folder}")
        return story_specific_epub_output_folder
    except Exception as e:
        log_error(f"An error occurred during the EPUB building step: {e}")
        log_debug(traceback.format_exc())
        raise typer.Exit(code=1)

def _run_cleanup_step(
    keep_intermediate_files: bool,
    story_specific_download_folder: str,
    story_specific_processed_folder: str
):
    """Handles Step 4: Cleaning up intermediate files."""
    if not keep_intermediate_files:
        typer.secho("\n--- Step 4: Cleaning up intermediate files ---", fg=typer.colors.CYAN)
        try:
            if os.path.exists(story_specific_download_folder):
                shutil.rmtree(story_specific_download_folder)
                log_info(f"Successfully deleted raw download folder: {story_specific_download_folder}")
            else:
                log_info(f"Raw download folder not found (already deleted or never created): {story_specific_download_folder}")

            if os.path.exists(story_specific_processed_folder):
                shutil.rmtree(story_specific_processed_folder)
                log_info(f"Successfully deleted processed content folder: {story_specific_processed_folder}")
            else:
                log_info(f"Processed content folder not found (already deleted or never created): {story_specific_processed_folder}")
        except OSError as e:
            log_error(f"Error during cleanup of intermediate folders: {e}")
            log_info(f"Please manually check and remove if necessary:\n- {story_specific_download_folder}\n- {story_specific_processed_folder}")
    else:
        typer.secho("\n--- Step 4: Skipping cleanup of intermediate files as per --keep-intermediate-files option. ---", fg=typer.colors.CYAN)
        log_info(f"Raw download folder retained at: {story_specific_download_folder}")
        log_info(f"Processed content folder retained at: {story_specific_processed_folder}")


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
    log_info("Attempting to authenticate with Google Drive...")
    try:
        service = authenticate_gdrive()
        if not service:
            log_error("Failed to authenticate with Google Drive. Please ensure 'credentials.json' is set up correctly and you've completed the authentication flow.")
            raise typer.Exit(code=1)
        log_success("Successfully authenticated with Google Drive.")
        log_info(f"Files will be uploaded to a root folder named: '{APP_ROOT_FOLDER_NAME}'")

        if story_slug_or_all.upper() == "ALL":
            log_info("Attempting to upload all stories...")
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
                log_warning("No story slugs found in 'epubs' or 'metadata_store' directories.")
                return

            log_info(f"Found {len(story_slugs)} potential story slug(s): {', '.join(sorted(list(story_slugs)))}")
            for slug in sorted(list(story_slugs)):
                log_info(f"--- Uploading story: {slug} ---")
                upload_story_files(service, slug)
                log_info(f"--- Finished uploading story: {slug} ---\n")
            log_success("All stories processed.")

        else:
            story_slug = story_slug_or_all
            log_info(f"Attempting to upload story: {story_slug}")
            upload_story_files(service, story_slug)
            log_success(f"Finished uploading story: {story_slug}")

    except FileNotFoundError as e: # Specifically for credentials.json missing
        log_error(f"Configuration error: {e}")
        log_error("Please ensure 'credentials.json' is in the project root and you have authenticated if it's your first time.")
        raise typer.Exit(code=1)
    except Exception as e:
        log_error(f"An error occurred during the Google Drive upload process: {e}")
        log_debug(traceback.format_exc())
        raise typer.Exit(code=1)


@app.command(name="remove-sentences")
def remove_sentences_command(
    epub_directory: str = typer.Option("epubs", "--dir", "-d", help="Directory containing EPUB files to process."),
    json_sentences_path: str = typer.Argument(..., help="Path to the JSON file containing the list of sentences to remove."),
    output_directory: Optional[str] = typer.Option(None, "--out", "-o", help="Optional. Directory to save modified EPUBs. If not provided, original EPUBs are overwritten.")
):
    """
    Removes a list of specified sentences from all EPUB files in a directory.
    The sentences to remove are provided via a JSON file (a list of strings).
    """
    log_info(f"Starting sentence removal process. EPUBs in: '{epub_directory}', Sentences from: '{json_sentences_path}'")

    # 1. Load sentences from JSON
    if not os.path.exists(json_sentences_path):
        log_error(f"Sentence file not found: {json_sentences_path}")
        raise typer.Exit(code=1)

    try:
        with open(json_sentences_path, 'r', encoding='utf-8') as f:
            loaded_sentences = json.load(f)
        if not isinstance(loaded_sentences, list) or not all(isinstance(s, str) for s in loaded_sentences):
            log_error("Invalid format in sentence file: Must be a JSON list of strings.")
            raise typer.Exit(code=1)
        if not loaded_sentences:
            log_warning("Sentence file is empty. No sentences to remove.")
            # Optionally exit or proceed to do nothing
            # raise typer.Exit(code=0) 
            return # Or just return if doing nothing is acceptable.
        log_info(f"Successfully loaded {len(loaded_sentences)} sentences to remove.")
    except json.JSONDecodeError:
        log_error(f"Error decoding JSON from sentence file: {json_sentences_path}")
        raise typer.Exit(code=1)
    except IOError as e:
        log_error(f"Error reading sentence file {json_sentences_path}: {e}")
        raise typer.Exit(code=1)

    # 2. Validate epub_directory
    abs_epub_directory = os.path.abspath(epub_directory)
    if not os.path.isdir(abs_epub_directory):
        log_error(f"EPUB directory not found or is not a directory: {abs_epub_directory}")
        raise typer.Exit(code=1)

    # 3. Prepare output directory
    abs_output_directory = None
    if output_directory:
        abs_output_directory = os.path.abspath(output_directory)
        if not os.path.exists(abs_output_directory):
            try:
                os.makedirs(abs_output_directory, exist_ok=True)
                log_info(f"Created output directory: {abs_output_directory}")
            except OSError as e:
                log_error(f"Error creating output directory '{abs_output_directory}': {e}")
                raise typer.Exit(code=1)
        else:
            log_info(f"Using existing output directory: {abs_output_directory}")
    else:
        log_info("No output directory specified. Original EPUB files will be overwritten.")

    # 4. Find and process EPUB files
    processed_count = 0
    modified_count = 0
    found_epub_files = False

    for item_name in os.listdir(abs_epub_directory):
        # Check if the item is a directory (story slug folder)
        story_slug_path = os.path.join(abs_epub_directory, item_name)
        if os.path.isdir(story_slug_path):
            # This is a story slug directory, e.g., 'epubs/my-cool-story'
            # Iterate through files inside this story slug directory
            for file_name in os.listdir(story_slug_path):
                if file_name.lower().endswith('.epub'):
                    found_epub_files = True
                    epub_file_path = os.path.join(story_slug_path, file_name)
                    log_info(f"Processing EPUB: {epub_file_path}")

                    target_epub_path = epub_file_path # Default: overwrite
                    
                    if abs_output_directory:
                        # Create a corresponding slug subfolder in the output directory
                        output_story_slug_path = os.path.join(abs_output_directory, item_name)
                        if not os.path.exists(output_story_slug_path):
                            try:
                                os.makedirs(output_story_slug_path, exist_ok=True)
                            except OSError as e:
                                log_error(f"Error creating output slug directory '{output_story_slug_path}': {e}")
                                continue # Skip this file or handle error differently
                        
                        target_epub_path = os.path.join(output_story_slug_path, file_name)
                        
                        if target_epub_path != epub_file_path: # Ensure we are not copying to itself
                            try:
                                shutil.copy2(epub_file_path, target_epub_path)
                                log_debug(f"Copied '{epub_file_path}' to '{target_epub_path}' for modification.")
                            except shutil.Error as e:
                                log_error(f"Error copying '{epub_file_path}' to '{target_epub_path}': {e}")
                                continue # Skip this file
                    
                    # modify_epub_content works on the target_epub_path (which is a copy if output_dir is set, else original)
                    # It will print its own success/failure for the modification itself.
                    # We capture the return or check if the file was indeed modified if modify_epub_content is changed to return a status
                    try:
                        # Assuming modify_epub_content logs its own errors/success for the modification part
                        # And it overwrites the file at target_epub_path
                        modify_epub_content(target_epub_path, loaded_sentences)
                        # To track if modify_epub_content actually made changes, it would ideally return a boolean.
                        # For now, we assume if it runs without error, it's "processed".
                        # A more robust way would be to check file modification times or hash before/after,
                        # or have modify_epub_content return a status.
                        # Let's assume modify_epub_content prints if it saved or not.
                        # We'll count it as processed if the call completes.
                        # If modify_epub_content is updated to return True if modified, we can use that.
                        # For now, just increment processed_count.
                        # modified_count would require more direct feedback from modify_epub_content.
                        processed_count += 1
                    except Exception as e:
                        log_error(f"An unexpected error occurred while calling modify_epub_content for {target_epub_path}: {e}")
                        log_debug(traceback.format_exc())

    if not found_epub_files:
        log_warning(f"No .epub files found directly in subdirectories of '{abs_epub_directory}'. Please ensure EPUBs are organized in story-specific subfolders (e.g. epubs/story-slug/file.epub).")
    elif processed_count > 0:
        log_success(f"Sentence removal process completed. Processed {processed_count} EPUB file(s).")
    else:
        log_info("Sentence removal process finished, but no EPUB files were processed (or none required modification based on current logic).")


if __name__ == "__main__":
    app()