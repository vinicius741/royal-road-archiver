import random
import requests
# BeautifulSoup import will be removed after refactoring fetch_story_metadata_and_first_chapter
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime # For timestamps
import time
# import re # No longer explicitly used in this file after refactoring
from urllib.parse import urljoin

from core.logging_utils import log_info, log_warning, log_error, log_debug, log_success
from .html_parser import parse_story_metadata_from_html, parse_chapter_data_from_html, _sanitize_filename as _sanitize_filename_parser

# Header to simulate a browser and avoid simple blocks
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
METADATA_ROOT_FOLDER = "metadata_store" # Centralized metadata storage

def _load_download_status(metadata_filepath: str) -> dict:
    """
    Loads the download status from a JSON metadata file.
    Returns a default structure if the file doesn't exist or is corrupt.
    """
    default_status = {
        "overview_url": None,
        "story_title": None,
        "author_name": None,
        "last_downloaded_url": None,
        "next_expected_chapter_url": None,
        "chapters": [] # List of dicts: {'url': str, 'title': str, 'filename': str, 'downloaded_at': str}
    }
    if not os.path.exists(metadata_filepath):
        return default_status
    try:
        with open(metadata_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Basic validation, can be expanded
            if not isinstance(data, dict) or "chapters" not in data:
                log_warning(f"Metadata file {metadata_filepath} has unexpected structure. Resetting.")
                return default_status
            return data
    except json.JSONDecodeError:
        log_warning(f"Corrupt metadata file: {metadata_filepath}. Resetting to default.")
        return default_status
    except IOError as e:
        log_error(f"ERROR reading metadata file {metadata_filepath}: {e}. Returning default.")
        return default_status

def _save_download_status(metadata_filepath: str, data: dict):
    """
    Saves the download status to a JSON metadata file.
    """
    try:
        # Ensure the directory exists before trying to save the file
        os.makedirs(os.path.dirname(metadata_filepath), exist_ok=True)
        with open(metadata_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        log_success(f"Download status saved to: {metadata_filepath}")
    except IOError as e:
        log_error(f"ERROR saving download status to {metadata_filepath}: {e}")
    except Exception as ex:
        log_error(f"UNEXPECTED ERROR saving download status to {metadata_filepath}: {ex}")

def _download_page_html(page_url: str) -> requests.Response | None:
    """
    Downloads the HTML content of a URL.
    Returns the request's response object or None in case of error.
    """
    log_debug(f"Trying to download: {page_url}")
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=15) # 15s timeout
        response.raise_for_status()  # Raises an error for 4xx/5xx HTTP codes
        return response
    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error downloading {page_url}: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error downloading {page_url}: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_warning(f"Timeout downloading {page_url}: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"General error downloading {page_url}: {req_err}")
    return None

def fetch_story_metadata_and_first_chapter(overview_url: str) -> dict | None:
    """
    Fetches story metadata (title, author, first chapter URL)
    from the story overview page.
    """
    log_info(f"Fetching metadata from overview page: {overview_url}")
    response = _download_page_html(overview_url)
    if not response:
        log_error("Failed to download the overview page.", url=overview_url)
        return None

    # Delegate parsing to the new html_parser function
    # Note: parse_story_metadata_from_html returns a more comprehensive metadata dict
    # including title, author, slug, cover_image_url, description, tags, publisher, story_id
    parsed_metadata = parse_story_metadata_from_html(overview_url, response.text)

    # The crucial part that REMAINS in crawler.py: finding the first chapter URL
    # This logic is specific to how a crawler navigates a site, not just parsing a single page's content.
    first_chapter_url = None
    soup = BeautifulSoup(response.text, 'html.parser') # Still need soup for this specific task

    start_reading_link = soup.select_one('a.btn.btn-primary[href*="/chapter/"]')
    if start_reading_link and start_reading_link.get('href'):
        relative_url = start_reading_link['href']
        first_chapter_url = urljoin(overview_url, relative_url)
        log_info(f"First chapter URL found (button): {first_chapter_url}", url=overview_url)
    else:
        log_warning("First chapter URL (button) not found on overview page. Trying table fallback.", url=overview_url)
        first_chapter_row_link = soup.select_one('table#chapters tbody tr[data-url] a')
        if first_chapter_row_link and first_chapter_row_link.get('href'):
            relative_url = first_chapter_row_link['href']
            first_chapter_url = urljoin(overview_url, relative_url)
            log_info(f"First chapter URL (table fallback) found: {first_chapter_url}", url=overview_url)
        else:
            log_error("CRITICAL: Could not find the first chapter URL on the overview page.", url=overview_url)
            # Return None because without the first chapter URL, crawling cannot proceed for this story.
            # The parsed_metadata might have some info, but it's incomplete for crawling purposes.
            return None

    # Combine the parsed metadata with the first_chapter_url
    # The parse_story_metadata_from_html already includes overview_url, story_title, author_name, story_slug etc.
    # So, we just need to add/update the first_chapter_url.
    final_metadata = parsed_metadata
    final_metadata['first_chapter_url'] = first_chapter_url
    
    # Ensure essential fields for downstream processing are present, even if from parser they were None/default
    if not final_metadata.get('story_title') or final_metadata['story_title'] == "Unknown Title":
        log_warning("Story title is unknown after parsing. Downstream processes might be affected.", url=overview_url)
    
    if not final_metadata.get('story_slug'):
        # If html_parser couldn't make a good slug (e.g. no title, no story_id),
        # crawler.py can try its own more complex logic based on URLs if needed,
        # or use a timestamp as a last resort.
        # The current html_parser's slug generation is quite robust, so this might be less necessary.
        # For now, we rely on the slug from html_parser. If it's None, it will be handled by `download_story`.
        log_warning(f"Story slug is None or generic after parsing: {final_metadata.get('story_slug')}. This might be handled by download_story.", url=overview_url)


    # The new parser already handles story_id extraction from overview_url.
    # It also handles slug generation. If the slug is still None or generic,
    # download_story has its own fallbacks.

    log_info(f"Successfully fetched and processed metadata for: {final_metadata.get('story_title', 'N/A')}", url=overview_url)
    return final_metadata


def _download_chapter_html(chapter_url: str) -> requests.Response | None:
    """
    Downloads the HTML content of a chapter URL.
    Returns the request's response object or None in case of error.
    """
    return _download_page_html(chapter_url) # Reuses the generic function

# ... (rest of _parse_chapter_html, _sanitize_filename remain the same)
def _parse_chapter_html(html_content: str, current_page_url: str) -> dict:
    """
    Parses the raw HTML of a chapter and extracts title, content, and next chapter URL.
    """
    # Delegate parsing entirely to the new html_parser function
    log_debug(f"Delegating chapter parsing to parse_chapter_data_from_html for URL: {current_page_url}")
    return parse_chapter_data_from_html(html_content, current_page_url)

# _sanitize_filename is now imported from html_parser, so the local definition is removed.

def download_story(first_chapter_url: str, output_folder: str, story_slug_override: str = None, overview_url: str = None, story_title: str = None, author_name: str = None):
    """
    Downloads all chapters of a story, starting from the first chapter URL,
    and manages download progress using a metadata file.
    """
    if story_slug_override:
        story_specific_folder_name = _sanitize_filename_parser(story_slug_override)
    else:
        # Tries to extract the slug from the URL if not provided
        # This logic might be simplified if html_parser.parse_story_metadata_from_html provides a reliable slug
        # based on overview_url, which can be passed as story_slug_override.
        # For now, retain this as a fallback if story_slug_override is not given.
        try:
            # Example: /fiction/12345/story-slug/chapter/... -> story-slug
            slug_parts = first_chapter_url.split('/fiction/')
            if len(slug_parts) > 1:
                sub_path = slug_parts[1] # e.g., "12345/story-slug/chapter/..."
                # Take the part after the ID, before the next segment (usually 'chapter')
                # This assumes a structure like /fiction/ID/SLUG/...
                potential_slug = sub_path.split('/')[1]
                if potential_slug and potential_slug != "chapter": # Basic check
                     story_specific_folder_name = _sanitize_filename_parser(potential_slug)
                else: # Fallback if slug extraction is not clean
                    story_specific_folder_name = _sanitize_filename_parser(story_title if story_title else f"story_{int(time.time())}")
                    log_warning(f"Could not clearly extract story slug from first_chapter_url, used title or timestamp: {story_specific_folder_name}", url=first_chapter_url)
            else: # Fallback if /fiction/ not in URL or structure is different
                story_specific_folder_name = _sanitize_filename_parser(story_title if story_title else f"story_{int(time.time())}")
                log_warning(f"Could not extract story slug from first_chapter_url using /fiction/ delimiter, used title or timestamp: {story_specific_folder_name}", url=first_chapter_url)

        except IndexError:
            # If extraction fails, uses a generic time-based name for the subfolder
            story_specific_folder_name = f"story_{int(time.time())}" # _sanitize_filename_parser not strictly needed here as it's time based
            log_warning(f"Failed to extract story name from first_chapter_url, using generic slug for folder: {story_specific_folder_name}", url=first_chapter_url)

    # The 'output_folder' passed to download_story should already be the base
    # where the story folder (story_specific_folder_name) will be created or used.
    story_output_folder_final = os.path.join(output_folder, story_specific_folder_name)

    if not os.path.exists(story_output_folder_final):
        log_info(f"Creating output folder for story chapters: {story_output_folder_final}")
        os.makedirs(story_output_folder_final, exist_ok=True)
    else:
        log_info(f"Using existing output folder for story chapters: {story_output_folder_final}")

    # New metadata path construction
    story_specific_metadata_folder = os.path.join(METADATA_ROOT_FOLDER, story_specific_folder_name)
    # The _save_download_status function will ensure story_specific_metadata_folder is created.
    metadata_filepath = os.path.join(story_specific_metadata_folder, "download_status.json")
    
    log_info(f"Metadata will be loaded from/saved to: {metadata_filepath}") # For clarity
    metadata = _load_download_status(metadata_filepath)

    # Initial Metadata Setup (for new downloads)
    if metadata.get('overview_url') is None and overview_url:
        metadata['overview_url'] = overview_url
    if metadata.get('story_title') is None and story_title:
        metadata['story_title'] = story_title
    if metadata.get('author_name') is None and author_name:
        metadata['author_name'] = author_name
    # Save initial metadata if it was just populated
    if overview_url or story_title or author_name:
         _save_download_status(metadata_filepath, metadata)


    # Determine Start URL
    current_chapter_url = first_chapter_url # Default to first_chapter_url
    if metadata.get('next_expected_chapter_url') and isinstance(metadata['next_expected_chapter_url'], str) and metadata['next_expected_chapter_url'].strip():
        log_info(f"Resuming download from: {metadata['next_expected_chapter_url']}")
        current_chapter_url = metadata['next_expected_chapter_url']
    else:
        log_info(f"Starting new download from: {first_chapter_url}")
        metadata['chapters'] = [] # Ensure chapters list is clean if not resuming

    chapter_number_counter = len(metadata.get('chapters', [])) + 1

    while current_chapter_url:
        log_info(f"\nProcessing chapter {chapter_number_counter} (URL: {current_chapter_url})...")

        # Existing Chapter Check
        found_entry = None
        for entry in metadata.get('chapters', []):
            if entry.get('url') == current_chapter_url:
                found_entry = entry
                break
        
        if found_entry:
            log_info(f"Chapter already downloaded: {found_entry.get('filename', 'N/A')}. Skipping.")
            current_chapter_url = found_entry.get('next_url_from_page') # Use the next URL stored at the time of its download
            if not current_chapter_url:
                log_info("No further link found from this previously downloaded chapter. Ending process for this story.")
                break
            time.sleep(0.1) # Short delay
            # No chapter_number_counter increment here as we are skipping to the *next* one.
            # The next iteration will handle the new current_chapter_url.
            continue

        # Download & Parse
        response = _download_chapter_html(current_chapter_url)
        if not response:
            log_error(f"Failed to download chapter {chapter_number_counter} from {current_chapter_url}.")
            metadata['next_expected_chapter_url'] = current_chapter_url # Save current URL to resume later
            _save_download_status(metadata_filepath, metadata)
            break

        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            log_warning(f"Content from {current_chapter_url} is not HTML (Content-Type: {content_type}). Skipping.")
            # Potentially save this URL as 'problematic' or 'skipped' in metadata if needed
            metadata['next_expected_chapter_url'] = None # Or decide how to handle
            _save_download_status(metadata_filepath, metadata)
            break 

        chapter_data = _parse_chapter_html(response.text, current_chapter_url)
        parsed_title = chapter_data['title']
        parsed_content_html = chapter_data['content_html']
        next_chapter_link_on_page = chapter_data['next_chapter_url']

        # Filename Generation
        if parsed_title == "Unknown Title" and chapter_number_counter == 1 and story_slug_override:
             final_title = story_slug_override.replace('-', ' ').title() + f" - Chapter {chapter_number_counter}"
        elif parsed_title == "Unknown Title":
            final_title = f"Chapter {chapter_number_counter}"
        else:
            final_title = parsed_title

        log_info(f"Chapter Title: {final_title}")

        safe_title_segment = _sanitize_filename_parser(final_title if final_title else f"chapter_{chapter_number_counter:03d}")
        filename = f"chapter_{chapter_number_counter:03d}_{safe_title_segment[:100]}.html"
        filepath = os.path.join(story_output_folder_final, filename)

        # Save Chapter File
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n")
                f.write(f"  <meta charset=\"UTF-8\">\n  <title>{final_title}</title>\n")
                f.write("  <style>\n")
                f.write("    body { font-family: sans-serif; margin: 20px; line-height: 1.6; }\n")
                f.write("    .chapter-content { max-width: 800px; margin: 0 auto; padding: 1em; }\n")
                f.write("    h1 { font-size: 1.8em; margin-bottom: 1em; }\n")
                f.write("    p { margin-bottom: 1em; }\n")
                f.write("  </style>\n")
                f.write("</head>\n<body>\n")
                f.write(f"<h1>{final_title}</h1>\n")
                f.write(parsed_content_html)
                f.write("\n</body>\n</html>")
            log_success(f"Saved to: {filepath}")
        except IOError as e:
            log_error(f"ERROR saving file {filepath}: {e}. Will attempt to resume from this chapter next time.")
            metadata['next_expected_chapter_url'] = current_chapter_url
            _save_download_status(metadata_filepath, metadata)
            break 
        except Exception as ex:
            log_error(f"UNEXPECTED ERROR saving file {filepath}: {ex}. Will attempt to resume from this chapter next time.")
            metadata['next_expected_chapter_url'] = current_chapter_url
            _save_download_status(metadata_filepath, metadata)
            break

        # Update Metadata
        new_chapter_info = {
            "url": current_chapter_url,
            "title": parsed_title, # Store the original parsed title
            "filename": filename,
            "download_timestamp": datetime.utcnow().isoformat() + "Z",
            "next_url_from_page": next_chapter_link_on_page, # Next link as found on *this* page
            "download_order": chapter_number_counter
        }
        metadata['chapters'].append(new_chapter_info)
        metadata['last_downloaded_url'] = current_chapter_url
        metadata['next_expected_chapter_url'] = next_chapter_link_on_page
        _save_download_status(metadata_filepath, metadata)

        # Advance to Next Chapter
        current_chapter_url = next_chapter_link_on_page

        if not current_chapter_url:
            log_info("\nEnd of story reached (next chapter link was not found or was invalid).")
            break
        
        # Check for loop on same URL
        if response and current_chapter_url == response.url:
             log_warning(f"\nNext chapter URL ({current_chapter_url}) is the same as the current page. Stopping to avoid loop.")
             metadata['next_expected_chapter_url'] = None # Prevent trying this again
             _save_download_status(metadata_filepath, metadata)
             break

        chapter_number_counter += 1
        delay = random.uniform(1.5, 3.5)
        log_debug(f"Waiting {delay:.1f} seconds before next chapter...")
        time.sleep(delay)

    log_info("\nChapter download process completed.")
    return story_output_folder_final # Returns the path of the folder where chapters were saved


if __name__ == '__main__':
    # Quick test for fetch_story_metadata_and_first_chapter
    # test_overview_url = "https://www.royalroad.com/fiction/115305/pioneer-of-the-abyss-an-underwater-livestreamed" # User example URL
    test_overview_url = "https://www.royalroad.com/fiction/76844/the-final-wish-a-litrpg-adventure" # Another example
    # test_overview_url = "https://www.royalroad.com/fiction/21220/mother-of-learning" # MoL
    log_info(f"Starting metadata fetch test for: {test_overview_url}")
    fetched_data = fetch_story_metadata_and_first_chapter(test_overview_url) # Renamed 'metadata' to 'fetched_data' for clarity
    if fetched_data:
        log_info("\nFetched data (metadata + first chapter URL):")
        for key, value in fetched_data.items():
            log_debug(f"  {key}: {value}") # Use log_debug for verbose output, or remove loop

        # Quick test for download_story (optional, this would usually go in main.py)
        # Ensure that the keys used here match what `fetch_story_metadata_and_first_chapter` now returns
        # It should return a dictionary containing 'first_chapter_url' and 'story_slug' from the parsed metadata.
        first_chapter_url_test = fetched_data.get('first_chapter_url')
        story_slug_test = fetched_data.get('story_slug') # This comes from parse_story_metadata_from_html
        story_title_test = fetched_data.get('story_title')
        author_name_test = fetched_data.get('author_name')


        if first_chapter_url_test and story_slug_test:
            test_output_base_folder = "downloaded_story_test_from_overview"
            if not os.path.exists(test_output_base_folder):
                os.makedirs(test_output_base_folder, exist_ok=True)

            log_info(f"\nStarting download test for: {first_chapter_url_test} (Slug: {story_slug_test})")
            # Passes test_output_base_folder, and download_story will create the slug subfolder within it.
            downloaded_to = download_story(
                first_chapter_url=first_chapter_url_test,
                output_folder=test_output_base_folder,
                story_slug_override=story_slug_test, # Use the slug from fetched_data
                overview_url=test_overview_url, 
                story_title=story_title_test, 
                author_name=author_name_test 
            )
            log_success(f"Test download completed. Chapters in: {downloaded_to}")
        else:
            log_warning("\nCould not test download, incomplete fetched data (first_chapter_url or story_slug missing).")
            if not first_chapter_url_test: log_warning("Missing: first_chapter_url_test")
            if not story_slug_test: log_warning(f"Missing: story_slug_test (current value: {story_slug_test})")


    else:
        log_error("\nMetadata fetch test failed (fetch_story_metadata_and_first_chapter returned None).")