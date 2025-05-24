import random
import requests
from bs4 import BeautifulSoup
from typing import Optional, Callable # For LoggerCallback
import os
import time
import re # To clean filenames
from urllib.parse import urljoin # To build absolute URLs

# Define LoggerCallback type alias, similar to main.py
LoggerCallback = Optional[Callable[[str, Optional[str]], None]]

# Header to simulate a browser and avoid simple blocks
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def _download_page_html(page_url: str, logger_callback: LoggerCallback = None) -> requests.Response | None:
    """
    Downloads the HTML content of a URL.
    Returns the request's response object or None in case of error.
    """
    log = lambda msg, style=None: logger_callback(msg, style) if logger_callback else print(msg)
    
    log(f"   Trying to download: {page_url}")
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=15) # 15s timeout
        response.raise_for_status()  # Raises an error for 4xx/5xx HTTP codes
        return response
    except requests.exceptions.HTTPError as http_err:
        log(f"   HTTP error downloading {page_url}: {http_err}", "red")
    except requests.exceptions.ConnectionError as conn_err:
        log(f"   Connection error downloading {page_url}: {conn_err}", "red")
    except requests.exceptions.Timeout as timeout_err:
        log(f"   Timeout downloading {page_url}: {timeout_err}", "red")
    except requests.exceptions.RequestException as req_err:
        log(f"   General error downloading {page_url}: {req_err}", "red")
    return None

def fetch_story_metadata_and_first_chapter(overview_url: str, logger_callback: LoggerCallback = None) -> dict | None:
    """
    Fetches story metadata (title, author, first chapter URL)
    from the story overview page.
    """
    log = lambda msg, style=None: logger_callback(msg, style) if logger_callback else print(msg)

    log(f"Fetching metadata from overview page: {overview_url}")
    response = _download_page_html(overview_url, logger_callback)
    if not response:
        log("   Failed to download the overview page.", "red")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    metadata = {
        'first_chapter_url': None,
        'story_title': "Unknown Title",
        'author_name': "Unknown Author",
        'story_slug': None
    }

    start_reading_link = soup.select_one('a.btn.btn-primary[href*="/chapter/"]')
    if start_reading_link and start_reading_link.get('href'):
        relative_url = start_reading_link['href']
        metadata['first_chapter_url'] = urljoin(overview_url, relative_url)
        log(f"   First chapter URL found: {metadata['first_chapter_url']}")
    else:
        log("   WARNING: First chapter URL not found on overview page.", "yellow")
        first_chapter_row_link = soup.select_one('table#chapters tbody tr[data-url] a')
        if first_chapter_row_link and first_chapter_row_link.get('href'):
            relative_url = first_chapter_row_link['href']
            metadata['first_chapter_url'] = urljoin(overview_url, relative_url)
            log(f"   First chapter URL (table fallback) found: {metadata['first_chapter_url']}")
        else:
            log("   CRITICAL ERROR: Could not find the first chapter URL.", "red")
            return None

    title_tag = soup.select_one('div.fic-title h1.font-white')
    if title_tag:
        metadata['story_title'] = title_tag.text.strip()
        log(f"   Story title found: {metadata['story_title']}")
    else:
        page_title_tag = soup.find('title')
        if page_title_tag:
            full_title = page_title_tag.text.strip()
            metadata['story_title'] = full_title.split('|')[0].strip()
            log(f"   Story title (title tag fallback) found: {metadata['story_title']}")
        else:
            log("   WARNING: Story title not found.", "yellow")

    author_link = soup.select_one('div.fic-title h4 span a[href*="/profile/"]')
    if author_link:
        metadata['author_name'] = author_link.text.strip()
        log(f"   Author name found: {metadata['author_name']}")
    else:
        script_tag = soup.find('script', type='application/ld+json')
        if script_tag:
            try:
                import json
                json_data = json.loads(script_tag.string)
                if json_data.get('author') and json_data['author'].get('name'):
                    metadata['author_name'] = json_data['author']['name'].strip()
                    log(f"   Author name (JSON-LD fallback) found: {metadata['author_name']}")
            except Exception as e:
                log(f"   WARNING: Error parsing JSON-LD for author name: {e}", "yellow")
        if metadata['author_name'] == "Unknown Author":
            log("   WARNING: Author name not found.", "yellow")

    if metadata['first_chapter_url']:
        try:
            parts = metadata['first_chapter_url'].split('/fiction/')
            if len(parts) > 1:
                slug_part = parts[1].split('/')
                if len(slug_part) > 1:
                     metadata['story_slug'] = _sanitize_filename(slug_part[1])
                     log(f"   Story slug (from chapter URL) found: {metadata['story_slug']}")
        except IndexError:
            pass

    if not metadata['story_slug']:
        try:
            parts = overview_url.split('/fiction/')
            if len(parts) > 1:
                slug_part = parts[1].split('/')
                if len(slug_part) > 1:
                    metadata['story_slug'] = _sanitize_filename(slug_part[1])
                    log(f"   Story slug (from overview URL) found: {metadata['story_slug']}")
                elif len(slug_part) == 1 and slug_part[0]:
                    metadata['story_slug'] = _sanitize_filename(metadata['story_title'])
                    log(f"   Story slug (title fallback) used: {metadata['story_slug']}")
        except IndexError:
            log("   WARNING: Could not extract story slug from overview URL. Using title.", "yellow")
            metadata['story_slug'] = _sanitize_filename(metadata['story_title'])

    if not metadata['story_slug'] or metadata['story_slug'] == "unknown-title":
        timestamp_slug = f"story_{int(time.time())}"
        log(f"   WARNING: Story slug could not be determined, using generic slug: {timestamp_slug}", "yellow")
        metadata['story_slug'] = timestamp_slug

    return metadata

def _download_chapter_html(chapter_url: str, logger_callback: LoggerCallback = None) -> requests.Response | None:
    """
    Downloads the HTML content of a chapter URL.
    Returns the request's response object or None in case of error.
    """
    return _download_page_html(chapter_url, logger_callback)

def _parse_chapter_html(html_content: str, current_page_url: str, logger_callback: LoggerCallback = None) -> dict:
    """
    Parses the raw HTML of a chapter and extracts title, content, and next chapter URL.
    """
    log = lambda msg, style=None: logger_callback(msg, style) if logger_callback else print(msg) # Not used here but good practice
    soup = BeautifulSoup(html_content, 'html.parser')

    # Título do Capítulo
    # Attempt 1: By the specific h1 in the fiction header on the chapter page
    title_tag_h1_specific = soup.select_one('div.fic-header h1.font-white.break-word, h1.break-word[property="name"]')
    # Attempt 2: By the h1 inside div.chapter-content (if the previous crawler saved it this way)
    title_tag_chapter_content = soup.select_one('div.chapter-content h1')
    # Attempt 3: By the most prominent h1 on the chapter page
    title_tag_general_h1 = soup.find('h1')
    # Attempt 4: By the page's <title> tag
    page_title_tag = soup.find('title')

    title = "Unknown Title"

    if title_tag_h1_specific:
        title = title_tag_h1_specific.text.strip()
    elif title_tag_chapter_content:
        title = title_tag_chapter_content.text.strip()
    elif title_tag_general_h1:
        title = title_tag_general_h1.text.strip()
    elif page_title_tag:
        # Ex: "Chapter Title - Story Name | Royal Road" ou "Chapter Title | Royal Road"
        title_text = page_title_tag.text.split('|')[0].strip()
        # Removes the story name if present, common in page titles
        # This is heuristic and may need adjustment.
        # We will try to remove " - Story Name" if it exists.
        # If the story title could be passed here, it would be more robust.
        parts = title_text.split(' - ')
        if len(parts) > 1 and len(parts[0]) < len(parts[1]): # Heuristic: chapter title is shorter
            title = parts[0].strip()
        else:
            title = title_text

    # Conteúdo da História
    content_div = soup.find('div', class_='chapter-content')
    if not content_div: # Fallback for some different structures
        content_div = soup.find('div', class_='prose') # Example of another content class
    content_html = str(content_div) if content_div else "<p>Content not found.</p>"

    # Link do Próximo Capítulo
    next_chapter_url = None
    # Priority for rel="next" link
    next_link_tag_rel = soup.find('link', rel='next')
    if next_link_tag_rel and next_link_tag_rel.get('href'):
        relative_url = next_link_tag_rel['href']
        next_chapter_url = urljoin(current_page_url, relative_url)
    else:
        # Fallback for "Next", "Próximo", etc. buttons (more comprehensive)
        # Selects links containing "Next" or "Próximo" in text, prioritizing button classes
        next_buttons = soup.select('a.btn[href], a.button[href], a[class*="next" i][href]')
        found_button = False
        for button in next_buttons:
            button_text = button.text.strip().lower()
            if "next" in button_text or "próximo" in button_text or "proximo" in button_text:
                relative_url = button['href']
                if relative_url and relative_url != "#" and "javascript:void(0)" not in relative_url:
                    next_chapter_url = urljoin(current_page_url, relative_url)
                    found_button = True
                    break
        # If not found with specific selector, try a more generic text search
        if not found_button:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                link_text = link.text.strip().lower()
                if ("next" in link_text or "próximo" in link_text or "proximo" in link_text) and \
                   ("previous" not in link_text and "anterior" not in link_text): # Avoid "previous" links
                    relative_url = link['href']
                    if relative_url and relative_url != "#" and "javascript:void(0)" not in relative_url:
                        # Additional check to avoid non-chapter links
                        # (ex: /comment/next, /forum/next)
                        if '/chapter/' in relative_url or '/fiction/' in relative_url or re.match(r'.*/\d+/?$', relative_url):
                             next_chapter_url = urljoin(current_page_url, relative_url)
                             break


    return {
        'title': title,
        'content_html': content_html,
        'next_chapter_url': next_chapter_url
    }

def _sanitize_filename(filename: str) -> str:
    """
    Removes invalid characters from a filename and shortens it if necessary.
    """
    # Removes characters that are problematic in filenames
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Replaces multiple spaces or tabs with a single underscore
    sanitized = re.sub(r'\s+', '_', sanitized)
    # Removes dots at the beginning or end, and multiple dots
    sanitized = re.sub(r'^\.|\.$', '', sanitized)
    sanitized = re.sub(r'\.{2,}', '.', sanitized)
    # Limits length to avoid excessively long filenames
    return sanitized[:100] # Keeps the first 100 characters


def download_story(first_chapter_url: str, output_folder: str, story_slug_override: str = None, logger_callback: LoggerCallback = None):
    """
    Downloads all chapters of a Royal Road story, starting from the first chapter URL.
    """
    log = lambda msg, style=None: logger_callback(msg, style) if logger_callback else print(msg)

    if story_slug_override:
        story_specific_folder_name = _sanitize_filename(story_slug_override)
    else:
        try:
            story_specific_folder_name = first_chapter_url.split('/fiction/')[1].split('/')[1]
            story_specific_folder_name = _sanitize_filename(story_specific_folder_name)
        except IndexError:
            story_specific_folder_name = f"story_{int(time.time())}"
            log(f"Could not extract story name from URL, using generic slug for folder: {story_specific_folder_name}", "yellow")

    story_output_folder_final = os.path.join(output_folder, story_specific_folder_name)

    if not os.path.exists(story_output_folder_final):
        log(f"Creating output folder for chapters: {story_output_folder_final}")
        os.makedirs(story_output_folder_final, exist_ok=True)
    else:
        log(f"Using existing output folder for chapters: {story_output_folder_final}")

    current_chapter_url = first_chapter_url
    chapter_number = 1

    while current_chapter_url:
        log(f"\nDownloading chapter {chapter_number}...")

        response = _download_chapter_html(current_chapter_url, logger_callback)
        if not response:
            log(f"Failed to download chapter {chapter_number} from {current_chapter_url}.", "red")
            break

        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            log(f"   WARNING: Content downloaded from {current_chapter_url} does not appear to be HTML (Content-Type: {content_type}). Attempting to process anyway.", "yellow")

        chapter_data = _parse_chapter_html(response.text, current_chapter_url, logger_callback)

        title = chapter_data['title']
        content_html = chapter_data['content_html']
        next_url = chapter_data['next_chapter_url']

        if title == "Unknown Title" and chapter_number == 1 and story_slug_override:
            title = story_slug_override.replace('-', ' ').title() + " - Chapter 1"

        log(f"   Chapter Title: {title}")
        if not next_url:
            log("   Next chapter link not found on this page.")

        safe_title = _sanitize_filename(title if title else f"chapter_{chapter_number:03d}")
        filename_base = f"chapter_{chapter_number:03d}_{safe_title}"
        filename = f"{filename_base[:150]}.html"
        filepath = os.path.join(story_output_folder_final, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n")
                f.write(f"  <meta charset=\"UTF-8\">\n  <title>{title if title else 'Chapter ' + str(chapter_number)}</title>\n")
                f.write("  <style>\n")
                f.write("    body { font-family: sans-serif; margin: 20px; line-height: 1.6; }\n")
                f.write("    .chapter-content { max-width: 800px; margin: 0 auto; padding: 1em; }\n")
                f.write("    h1 { font-size: 1.8em; margin-bottom: 1em; }\n")
                f.write("    p { margin-bottom: 1em; }\n")
                f.write("  </style>\n")
                f.write("</head>\n<body>\n")
                f.write(f"<h1>{title if title else 'Chapter ' + str(chapter_number)}</h1>\n")
                f.write(content_html)
                f.write("\n</body>\n</html>")
            log(f"   Saved to: {filepath}")
        except IOError as e:
            log(f"   ERROR saving file {filepath}: {e}", "red")
        except Exception as ex:
            log(f"   UNEXPECTED ERROR saving file {filepath}: {ex}", "red")

        current_chapter_url = next_url

        if not current_chapter_url:
            log("\nEnd of story reached (next chapter not found or invalid URL).")
            break

        if current_chapter_url == response.url:
            log(f"\nWARNING: Next chapter URL ({current_chapter_url}) is the same as the current page. Stopping to avoid loop.", "yellow")
            break

        chapter_number += 1
        delay = random.uniform(1.5, 3.5)
        log(f"   Waiting {delay:.1f} seconds before next chapter...")
        time.sleep(delay)

    log("\nChapter download process completed.")
    return story_output_folder_final

if __name__ == '__main__':
    # Define a simple print-based logger for standalone testing
    def test_logger(message: str, style: Optional[str] = None):
        if style:
            print(f"[{style.upper()}] {message}")
        else:
            print(message)

    test_overview_url = "https://www.royalroad.com/fiction/115305/pioneer-of-the-abyss-an-underwater-livestreamed"
    print(f"Starting metadata fetch test for: {test_overview_url}")
    metadata = fetch_story_metadata_and_first_chapter(test_overview_url, logger_callback=test_logger)
    if metadata:
        print("\nMetadata found:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")

        if metadata.get('first_chapter_url') and metadata.get('story_slug'):
            test_output_base_folder = "downloaded_story_test_from_overview"
            if not os.path.exists(test_output_base_folder):
                os.makedirs(test_output_base_folder, exist_ok=True)

            print(f"\nStarting download test for: {metadata['first_chapter_url']}")
            downloaded_to = download_story(
                metadata['first_chapter_url'], 
                test_output_base_folder, 
                story_slug_override=metadata['story_slug'],
                logger_callback=test_logger
            )
            print(f"Test download completed. Chapters in: {downloaded_to}")
        else:
            print("\nCould not test download, incomplete metadata (first chapter URL or slug missing).")
    else:
        print("\nMetadata fetch test failed.")