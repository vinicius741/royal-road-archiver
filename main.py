# main.py
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

def _ensure_base_folder(folder_path: str):
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

def _infer_slug_from_url(url: str, default_slug_prefix: str = "story") -> str | None:
    """Tries to infer a story slug from a URL."""
    try:
        # Example: https://www.royalroad.com/fiction/12345/some-story-slug/chapter/123456/chapter-name
        # We want "some-story-slug"
        parts = url.split('/fiction/')
        if len(parts) > 1:
            slug_part = parts[1].split('/')
            if len(slug_part) > 1 and slug_part[1]: # slug_part[0] is ID, slug_part[1] is slug
                slug = re.sub(r'[\\/*?:"<>|]', "", slug_part[1])
                slug = re.sub(r'\s+', '_', slug).lower()[:100] # Sanitize and shorten
                return slug
    except IndexError:
        pass # Failed to infer
    return None


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
    Can start from a story overview page or a direct chapter URL.
    The --start-chapter-url option can specify a precise starting point for crawling.
    """
    typer.echo(f"Starting download for story URL: {story_url}")
    if start_chapter_url:
        typer.echo(f"Specified starting chapter for crawl: {start_chapter_url}")

    abs_output_folder = _ensure_base_folder(output_folder)

    crawl_entry_point_url = story_url
    story_slug_for_folder = None
    metadata_source_url = story_url # URL used primarily for metadata if it's an overview

    if is_overview_url(metadata_source_url):
        typer.echo("Story URL detected as overview page. Fetching metadata...")
        metadata = fetch_story_metadata_and_first_chapter(metadata_source_url)
        if not metadata:
            typer.secho("Failed to get metadata from overview page.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        
        story_slug_for_folder = metadata.get('story_slug')
        # If start_chapter_url is not given, use the first chapter from overview
        if not start_chapter_url:
            crawl_entry_point_url = metadata.get('first_chapter_url')
            if not crawl_entry_point_url:
                typer.secho("Could not determine first chapter URL from overview metadata.", fg=typer.colors.RED)
                raise typer.Exit(code=1)
            typer.echo(f"First chapter from overview: {crawl_entry_point_url}")
        else:
            crawl_entry_point_url = start_chapter_url # User override
            typer.echo(f"Using user-specified start chapter URL: {crawl_entry_point_url} (overview URL was {story_url})")

    else: # story_url is a chapter URL
        typer.echo("Story URL detected as a chapter page.")
        if not start_chapter_url:
            crawl_entry_point_url = story_url # Start from the given chapter URL
        else:
            crawl_entry_point_url = start_chapter_url # User override for starting point
            typer.echo(f"Using user-specified start chapter URL: {crawl_entry_point_url} (original chapter URL was {story_url})")
        
        # Try to infer slug from the original story_url if not found from overview
        if not story_slug_for_folder:
            story_slug_for_folder = _infer_slug_from_url(story_url)

    # If start_chapter_url was provided and slug is still missing, try inferring from it
    if start_chapter_url and not story_slug_for_folder:
        story_slug_for_folder = _infer_slug_from_url(start_chapter_url)

    # Fallback for slug if still not determined
    if not story_slug_for_folder:
        story_slug_for_folder = f"story_{int(time.time())}"
        typer.echo(f"Could not determine story slug, using generic: {story_slug_for_folder}")
    else:
        typer.echo(f"Story slug for folder name: {story_slug_for_folder}")
    
    if not crawl_entry_point_url or "/chapter/" not in crawl_entry_point_url :
        typer.secho(f"Invalid crawl entry point: '{crawl_entry_point_url}'. Must be a valid chapter URL.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo(f"Final crawl will start from: {crawl_entry_point_url}")

    try:
        downloaded_story_path = download_story(crawl_entry_point_url, abs_output_folder, story_slug_override=story_slug_for_folder)
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

    if not os.path.exists(specific_output_folder):
        try:
            os.makedirs(specific_output_folder, exist_ok=True)
            typer.echo(f"Output folder for processed files created: {specific_output_folder}")
        except OSError as e:
            typer.secho(f"Error creating specific output folder for processed files '{specific_output_folder}': {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"Using existing specific output folder for processed files: {specific_output_folder}")

    try:
        process_story_chapters(abs_input_story_folder, specific_output_folder)
        typer.secho(f"\nProcessing of story chapters concluded successfully! Output in: {specific_output_folder}", fg=typer.colors.GREEN)
        return specific_output_folder 
    except ImportError:
         typer.secho("Critical Error: Could not import 'process_story_chapters' from 'core.processor'. Check file and project structure.", fg=typer.colors.RED)
         raise typer.Exit(code=1)
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
    abs_output_epub_folder = _ensure_base_folder(output_epub_folder)

    if not os.path.isdir(abs_input_processed_folder):
        typer.secho(f"Error: Input processed folder '{abs_input_processed_folder}' not found or is not a directory.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    effective_chapters_per_epub = chapters_per_epub if chapters_per_epub > 0 else 999999

    try:
        build_epubs_for_story(
            input_folder=abs_input_processed_folder, 
            output_folder=abs_output_epub_folder,   
            chapters_per_epub=effective_chapters_per_epub,
            author_name=author_name,
            story_title=story_title 
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
    story_url: str = typer.Argument(..., help="The full URL of the story's overview page OR a chapter URL."),
    start_chapter_url: str = typer.Option( # New parameter
        None,
        "--start-chapter-url",
        "-scu",
        help="Optional URL of a specific chapter to start downloading from. Overrides the first chapter if story_url is an overview or a different chapter."
    ),
    chapters_per_epub: int = typer.Option(
        50,
        "--chapters-per-epub",
        "-c",
        min=0,
        help="Number of chapters to include in each EPUB file. Set to 0 for a single EPUB."
    ),
    author_name_param: str = typer.Option(
        None, 
        "--author",
        "-a",
        help="Author name for EPUB metadata. If not provided and fetching from overview, uses that."
    ),
    story_title_param: str = typer.Option(
        None, 
        "--title",
        "-t",
        help="Story title for EPUB metadata. If not provided and fetching from overview, uses that."
    )
):
    """
    Performs the full sequence: download, process, and build EPUB for a story.
    The main story_url is used for metadata (if overview) and slug generation.
    The --start-chapter-url option can specify a precise starting point for crawling.
    """
    download_base_folder_name = "downloaded_stories"
    processed_base_folder_name = "processed_stories"
    epub_base_folder_name = "epubs"

    # Ensure base folders exist and get absolute paths
    abs_download_base_folder = _ensure_base_folder(download_base_folder_name)
    abs_processed_base_folder = _ensure_base_folder(processed_base_folder_name)
    abs_epub_base_folder = _ensure_base_folder(epub_base_folder_name)
    
    # Variables for metadata and paths
    actual_crawl_start_url = None
    story_slug_for_folders = None
    final_story_title = story_title_param
    final_author_name = author_name_param
    
    metadata_source_url = story_url # The URL used to fetch metadata
    default_first_chapter_from_metadata = None

    # --- 0. Fetch metadata (if overview URL) and determine slug ---
    typer.echo(f"\n--- Step 0: Initializing and fetching metadata from {metadata_source_url} ---")
    if is_overview_url(metadata_source_url):
        metadata = fetch_story_metadata_and_first_chapter(metadata_source_url)
        if not metadata:
            typer.secho("Failed to get metadata from overview page. Some details might be missing or generic.", fg=typer.colors.YELLOW)
        else:
            default_first_chapter_from_metadata = metadata.get('first_chapter_url')
            if not story_slug_for_folders: # Prioritize slug from metadata
                story_slug_for_folders = metadata.get('story_slug')
            if not final_story_title and metadata.get('story_title') != "Unknown Title":
                final_story_title = metadata['story_title']
            if not final_author_name and metadata.get('author_name') != "Unknown Author":
                final_author_name = metadata['author_name']
    else: # metadata_source_url is likely a chapter URL
        default_first_chapter_from_metadata = metadata_source_url # It's already a chapter link

    # Determine actual_crawl_start_url
    if start_chapter_url:
        if "/chapter/" not in start_chapter_url:
            typer.secho(f"Warning: Provided --start-chapter-url '{start_chapter_url}' does not look like a valid chapter URL. Proceeding, but crawling might fail.", fg=typer.colors.YELLOW)
        actual_crawl_start_url = start_chapter_url
        typer.echo(f"Crawling will start from user-specified chapter: {actual_crawl_start_url}")
    elif default_first_chapter_from_metadata:
        actual_crawl_start_url = default_first_chapter_from_metadata
        typer.echo(f"Crawling will start from chapter derived from metadata/story_url: {actual_crawl_start_url}")
    else: # Fallback if no start URL could be determined (should be rare)
        actual_crawl_start_url = story_url # Use the primary story_url as last resort if it's a chapter
        if "/chapter/" not in actual_crawl_start_url:
             typer.secho(f"Error: Could not determine a valid starting chapter URL. Last attempt was '{actual_crawl_start_url}'. Please provide a valid chapter URL via --start-chapter-url or ensure story_url is a chapter/valid overview.", fg=typer.colors.RED)
             raise typer.Exit(code=1)
        typer.echo(f"Crawling will start from (fallback) story_url: {actual_crawl_start_url}")


    # Refine slug determination
    if not story_slug_for_folders: # If not from metadata (overview)
        story_slug_for_folders = _infer_slug_from_url(metadata_source_url) # Try from main story_url
    if not story_slug_for_folders and start_chapter_url: # Then try from start_chapter_url if provided
        story_slug_for_folders = _infer_slug_from_url(start_chapter_url)
    
    if not story_slug_for_folders: # Fallback to title or generic
        if final_story_title and final_story_title not in ["Archived Royal Road Story", "Unknown Story"]:
            story_slug_for_folders = re.sub(r'[\\/*?:"<>|]', "", final_story_title)
            story_slug_for_folders = re.sub(r'\s+', '_', story_slug_for_folders).lower()[:50]
            typer.echo(f"Slug for folders (generated from title): {story_slug_for_folders}")
        else:
            story_slug_for_folders = f"story_{int(time.time())}"
            typer.echo(f"WARNING: Using generic slug for folders: {story_slug_for_folders}")
    else:
        typer.echo(f"Final story slug for folders: {story_slug_for_folders}")

    # Finalize title and author with defaults if still not set
    if not final_story_title:
        if story_slug_for_folders and not story_slug_for_folders.startswith("story_"):
             final_story_title = story_slug_for_folders.replace('-', ' ').replace('_', ' ').title()
             typer.echo(f"EPUB title (inferred from slug): {final_story_title}")
        else:
            final_story_title = "Archived Royal Road Story" 
            typer.echo(f"EPUB title (default): {final_story_title}")
    else:
        typer.echo(f"EPUB title (from params/metadata): {final_story_title}")

    if not final_author_name:
        final_author_name = "Royal Road Archiver"
        typer.echo(f"EPUB author (default): {final_author_name}")
    else:
        typer.echo(f"EPUB author (from params/metadata): {final_author_name}")


    # --- 1. Download Step ---
    typer.echo(f"\n--- Step 1: Downloading chapters starting from {actual_crawl_start_url} ---")
    story_specific_download_folder = None
    try:
        story_specific_download_folder = download_story(
            actual_crawl_start_url, 
            abs_download_base_folder, 
            story_slug_override=story_slug_for_folders
        )
        if not story_specific_download_folder or not os.path.isdir(story_specific_download_folder):
            typer.secho("Error: The story download folder was not created or returned correctly by the crawler.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        typer.secho(f"Download successful. Raw content in: {story_specific_download_folder}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"An error occurred during the download step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

    # --- 2. Process Step ---
    typer.echo(f"\n--- Step 2: Processing story chapters from {story_specific_download_folder} ---")
    story_specific_processed_folder = os.path.join(abs_processed_base_folder, story_slug_for_folders)
    
    try:
        process_story_chapters(story_specific_download_folder, story_specific_processed_folder)
        if not os.path.isdir(story_specific_processed_folder):
             typer.secho(f"Error: Processed story folder '{story_specific_processed_folder}' was not created/found after processing.", fg=typer.colors.RED)
             raise typer.Exit(code=1)
        typer.secho(f"Processing successful. Cleaned content in: {story_specific_processed_folder}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"An error occurred during the processing step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

    # --- 3. Build EPUB Step ---
    typer.echo(f"\n--- Step 3: Building EPUB(s) from {story_specific_processed_folder} ---")
    effective_chapters_per_epub = chapters_per_epub if chapters_per_epub > 0 else 999999

    try:
        # build_epubs_for_story is expected to not return a value, success is determined by lack of exception
        # and the user checking the output folder.
        build_epubs_for_story(
            input_folder=story_specific_processed_folder,
            output_folder=abs_epub_base_folder,  
            chapters_per_epub=effective_chapters_per_epub,
            author_name=final_author_name,
            story_title=final_story_title
        )
        # To give a more direct feedback, we can check if files were created, but that's more involved.
        # For now, relying on the function not throwing an error is the indicator.
        typer.secho(f"EPUB generation process finished. Files should be in: {abs_epub_base_folder}", fg=typer.colors.GREEN)
        
    except Exception as e:
        typer.secho(f"An error occurred during the EPUB building step: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        raise typer.Exit(code=1)

    typer.secho("\n--- Full process completed! ---", fg=typer.colors.CYAN)


if __name__ == "__main__":
    app()