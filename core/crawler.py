import random
import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime # For timestamps
import time
import re # To clean filenames
from urllib.parse import urljoin # To build absolute URLs

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
                print(f"   WARNING: Metadata file {metadata_filepath} has unexpected structure. Resetting.")
                return default_status
            return data
    except json.JSONDecodeError:
        print(f"   WARNING: Corrupt metadata file: {metadata_filepath}. Resetting to default.")
        return default_status
    except IOError as e:
        print(f"   ERROR reading metadata file {metadata_filepath}: {e}. Returning default.")
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
        print(f"   Download status saved to: {metadata_filepath}")
    except IOError as e:
        print(f"   ERROR saving download status to {metadata_filepath}: {e}")
    except Exception as ex:
        print(f"   UNEXPECTED ERROR saving download status to {metadata_filepath}: {ex}")

def _download_page_html(page_url: str) -> requests.Response | None:
    """
    Downloads the HTML content of a URL.
    Returns the request's response object or None in case of error.
    """
    print(f"   Trying to download: {page_url}")
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=15) # 15s timeout
        response.raise_for_status()  # Raises an error for 4xx/5xx HTTP codes
        return response
    except requests.exceptions.HTTPError as http_err:
        print(f"   HTTP error downloading {page_url}: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"   Connection error downloading {page_url}: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"   Timeout downloading {page_url}: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"   General error downloading {page_url}: {req_err}")
    return None

def fetch_story_metadata_and_first_chapter(overview_url: str) -> dict | None:
    """
    Fetches story metadata (title, author, first chapter URL)
    from the story overview page.
    """
    print(f"Fetching metadata from overview page: {overview_url}")
    response = _download_page_html(overview_url)
    if not response:
        print("   Failed to download the overview page.")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    metadata = {
        'overview_url': overview_url, # Added overview_url
        'first_chapter_url': None,
        'story_title': "Unknown Title",
        'author_name': "Unknown Author",
        'story_slug': None,
        'cover_image_url': None,
        'description': None,
        'tags': [],
        'publisher': None
    }

    # Attempt to parse JSON-LD
    json_ld_data = None
    script_tag_ld = soup.find('script', type='application/ld+json')
    if script_tag_ld:
        try:
            json_ld_data = json.loads(script_tag_ld.string)
        except json.JSONDecodeError as e:
            print(f"   WARNING: Error parsing JSON-LD: {e}")

    # Extract cover_image_url
    og_image_tag = soup.find('meta', property='og:image')
    if og_image_tag and og_image_tag.get('content'):
        metadata['cover_image_url'] = og_image_tag['content']
    else:
        twitter_image_tag = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image_tag and twitter_image_tag.get('content'):
            metadata['cover_image_url'] = twitter_image_tag['content']
        elif json_ld_data and isinstance(json_ld_data.get('image'), str):
            metadata['cover_image_url'] = json_ld_data['image']
        elif json_ld_data and isinstance(json_ld_data.get('image'), dict) and isinstance(json_ld_data['image'].get('url'), str):
            metadata['cover_image_url'] = json_ld_data['image']['url'] # Handle cases where image is an object
        elif json_ld_data and isinstance(json_ld_data.get('image'), list) and len(json_ld_data['image']) > 0:
             # Handle cases where image is a list of images, take the first one
            first_image = json_ld_data['image'][0]
            if isinstance(first_image, str):
                 metadata['cover_image_url'] = first_image
            elif isinstance(first_image, dict) and isinstance(first_image.get('url'), str):
                 metadata['cover_image_url'] = first_image['url']


    # Extract description
    og_description_tag = soup.find('meta', property='og:description')
    if og_description_tag and og_description_tag.get('content'):
        metadata['description'] = og_description_tag['content']
    else:
        twitter_description_tag = soup.find('meta', attrs={'name': 'twitter:description'})
        if twitter_description_tag and twitter_description_tag.get('content'):
            metadata['description'] = twitter_description_tag['content']
        elif json_ld_data and isinstance(json_ld_data.get('description'), str):
            metadata['description'] = json_ld_data['description']

    # Extract tags
    tags_list = []
    keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
    if keywords_tag and keywords_tag.get('content'):
        tags_list.extend([tag.strip() for tag in keywords_tag['content'].split(',') if tag.strip()])

    if json_ld_data:
        if isinstance(json_ld_data.get('genre'), str):
            tags_list.append(json_ld_data['genre'].strip())
        elif isinstance(json_ld_data.get('genre'), list):
            tags_list.extend([g.strip() for g in json_ld_data['genre'] if isinstance(g, str) and g.strip()])
        # Also check for keywords in JSON-LD as some sites might use it
        if isinstance(json_ld_data.get('keywords'), str):
            tags_list.extend([tag.strip() for tag in json_ld_data['keywords'].split(',') if tag.strip()])
        elif isinstance(json_ld_data.get('keywords'), list):
            tags_list.extend([k.strip() for k in json_ld_data['keywords'] if isinstance(k, str) and k.strip()])


    if tags_list:
        metadata['tags'] = sorted(list(set(tags_list))) # Keep unique tags and sort them

    # Extract publisher
    if json_ld_data and isinstance(json_ld_data.get('publisher'), dict) and isinstance(json_ld_data['publisher'].get('name'), str):
        metadata['publisher'] = json_ld_data['publisher']['name'].strip()
    elif json_ld_data and isinstance(json_ld_data.get('sourceOrganization'), dict) and isinstance(json_ld_data['sourceOrganization'].get('name'), str): # Common alternative
        metadata['publisher'] = json_ld_data['sourceOrganization']['name'].strip()


    # Extrair URL do primeiro capítulo
    # Look for the "Start Reading" button or similar that leads to the first chapter
    # <a href="/fiction/115305/pioneer-of-the-abyss-an-underwater-livestreamed/chapter/2251704/b1-chapter-1" class="btn btn-lg btn-primary">
    start_reading_link = soup.select_one('a.btn.btn-primary[href*="/chapter/"]')
    if start_reading_link and start_reading_link.get('href'):
        relative_url = start_reading_link['href']
        metadata['first_chapter_url'] = urljoin(overview_url, relative_url)
        print(f"   First chapter URL found: {metadata['first_chapter_url']}")
    else:
        print("   WARNING: First chapter URL not found on overview page.")
        # Tries to find in the chapter table if the button doesn't exist
        first_chapter_row_link = soup.select_one('table#chapters tbody tr[data-url] a')
        if first_chapter_row_link and first_chapter_row_link.get('href'):
            relative_url = first_chapter_row_link['href']
            metadata['first_chapter_url'] = urljoin(overview_url, relative_url)
            print(f"   First chapter URL (table fallback) found: {metadata['first_chapter_url']}")
        else:
            print("   CRITICAL ERROR: Could not find the first chapter URL.")
            return None # Essential to continue

    # Extrair título da história
    # <h1 class="font-white">Pioneer of the Abyss: An Underwater Livestreamed Isekai LitRPG</h1>
    title_tag = soup.select_one('div.fic-title h1.font-white')
    if title_tag:
        metadata['story_title'] = title_tag.text.strip()
        print(f"   Story title found: {metadata['story_title']}")
    else:
        # Fallback to the page's <title> tag
        page_title_tag = soup.find('title')
        if page_title_tag:
            # Ex: "Pioneer of the Abyss: An Underwater Livestreamed Isekai LitRPG | Royal Road"
            full_title = page_title_tag.text.strip()
            metadata['story_title'] = full_title.split('|')[0].strip() # Takes the part before the pipe
            print(f"   Story title (title tag fallback) found: {metadata['story_title']}")
        else:
            print("   WARNING: Story title not found.")


    # Extrair nome do autor
    # <span><a href="/profile/102324" class="font-white">WolfShine</a></span>
    author_link = soup.select_one('div.fic-title h4 span a[href*="/profile/"]')
    if author_link:
        metadata['author_name'] = author_link.text.strip()
        print(f"   Author name found: {metadata['author_name']}")
    else:
        # Fallback: Try to find in the JSON LD schema
        script_tag = soup.find('script', type='application/ld+json')
        if json_ld_data: # Use pre-parsed json_ld_data
            try:
                # Check if author is a string (some schemas might have simple name string)
                if isinstance(json_ld_data.get('author'), str):
                    metadata['author_name'] = json_ld_data['author'].strip()
                    print(f"   Author name (JSON-LD fallback - string) found: {metadata['author_name']}")
                # Check if author is a dictionary (standard)
                elif isinstance(json_ld_data.get('author'), dict) and json_ld_data['author'].get('name'):
                    metadata['author_name'] = json_ld_data['author']['name'].strip()
                    print(f"   Author name (JSON-LD fallback - object) found: {metadata['author_name']}")
                # Check if author is a list of authors (take the first one)
                elif isinstance(json_ld_data.get('author'), list) and len(json_ld_data['author']) > 0:
                    first_author = json_ld_data['author'][0]
                    if isinstance(first_author, str):
                         metadata['author_name'] = first_author.strip()
                         print(f"   Author name (JSON-LD fallback - list of strings) found: {metadata['author_name']}")
                    elif isinstance(first_author, dict) and first_author.get('name'):
                        metadata['author_name'] = first_author['name'].strip()
                        print(f"   Author name (JSON-LD fallback - list of objects) found: {metadata['author_name']}")
            except Exception as e: # Catch any unexpected errors during processing
                print(f"   WARNING: Error processing JSON-LD for author name: {e}")
        if metadata['author_name'] == "Unknown Author": # If still not found
            print("   WARNING: Author name not found.")


    # Extract story slug from the first chapter URL (more reliable)
    if metadata['first_chapter_url']:
        try:
            # Ex: https://www.royalroad.com/fiction/12345/some-story/chapter/123456/chapter-one
            # We want "some-story"
            parts = metadata['first_chapter_url'].split('/fiction/')
            if len(parts) > 1:
                slug_part = parts[1].split('/')
                if len(slug_part) > 1:
                     metadata['story_slug'] = _sanitize_filename(slug_part[1]) # slug_part[0] is the fiction ID
                     print(f"   Story slug (from chapter URL) found: {metadata['story_slug']}")
        except IndexError:
            pass # Leaves slug as None if extraction fails

    if not metadata['story_slug']: # Fallback to the overview URL
        try:
            parts = overview_url.split('/fiction/')
            if len(parts) > 1:
                slug_part = parts[1].split('/')
                if len(slug_part) > 1: # /fiction/ID/slug/...
                    metadata['story_slug'] = _sanitize_filename(slug_part[1])
                    print(f"   Story slug (from overview URL) found: {metadata['story_slug']}")
                elif len(slug_part) == 1 and slug_part[0]: # /fiction/ID (if there's no slug in the URL)
                    # In this case, the title can be a good alternative for the folder name
                    metadata['story_slug'] = _sanitize_filename(metadata['story_title'])
                    print(f"   Story slug (title fallback) used: {metadata['story_slug']}")

        except IndexError:
            print("   WARNING: Could not extract story slug from overview URL. Using title.")
            metadata['story_slug'] = _sanitize_filename(metadata['story_title'])

    if not metadata['story_slug'] or metadata['story_slug'] == "unknown-title":
        # Last resort, use a generic name if everything fails
        timestamp_slug = f"story_{int(time.time())}"
        print(f"   WARNING: Story slug could not be determined, using generic slug: {timestamp_slug}")
        metadata['story_slug'] = timestamp_slug


    return metadata


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


def download_story(first_chapter_url: str, output_folder: str, story_slug_override: str = None, overview_url: str = None, story_title: str = None, author_name: str = None):
    """
    Downloads all chapters of a story, starting from the first chapter URL,
    and manages download progress using a metadata file.
    """
    if story_slug_override:
        story_specific_folder_name = _sanitize_filename(story_slug_override)
    else:
        # Tries to extract the slug from the URL if not provided
        try:
            story_specific_folder_name = first_chapter_url.split('/fiction/')[1].split('/')[1]
            story_specific_folder_name = _sanitize_filename(story_specific_folder_name)
        except IndexError:
            # If extraction fails, uses a generic time-based name for the subfolder
            story_specific_folder_name = f"story_{int(time.time())}"
            print(f"Could not extract story name from URL, using generic slug for folder: {story_specific_folder_name}")

    # The 'output_folder' passed to download_story should already be the base
    # where the story folder (story_specific_folder_name) will be created or used.
    story_output_folder_final = os.path.join(output_folder, story_specific_folder_name)

    if not os.path.exists(story_output_folder_final):
        print(f"Creating output folder for story chapters: {story_output_folder_final}")
        os.makedirs(story_output_folder_final, exist_ok=True)
    else:
        print(f"Using existing output folder for story chapters: {story_output_folder_final}")

    # New metadata path construction
    story_specific_metadata_folder = os.path.join(METADATA_ROOT_FOLDER, story_specific_folder_name)
    # The _save_download_status function will ensure story_specific_metadata_folder is created.
    metadata_filepath = os.path.join(story_specific_metadata_folder, "download_status.json")
    
    print(f"Metadata will be loaded from/saved to: {metadata_filepath}") # For clarity
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
        print(f"Resuming download from: {metadata['next_expected_chapter_url']}")
        current_chapter_url = metadata['next_expected_chapter_url']
    else:
        print(f"Starting new download from: {first_chapter_url}")
        metadata['chapters'] = [] # Ensure chapters list is clean if not resuming

    chapter_number_counter = len(metadata.get('chapters', [])) + 1

    while current_chapter_url:
        print(f"\nProcessing chapter {chapter_number_counter} (URL: {current_chapter_url})...")

        # Existing Chapter Check
        found_entry = None
        for entry in metadata.get('chapters', []):
            if entry.get('url') == current_chapter_url:
                found_entry = entry
                break
        
        if found_entry:
            print(f"   Chapter already downloaded: {found_entry.get('filename', 'N/A')}. Skipping.")
            current_chapter_url = found_entry.get('next_url_from_page') # Use the next URL stored at the time of its download
            if not current_chapter_url:
                print("   No further link found from this previously downloaded chapter. Ending process for this story.")
                break
            time.sleep(0.1) # Short delay
            # No chapter_number_counter increment here as we are skipping to the *next* one.
            # The next iteration will handle the new current_chapter_url.
            continue

        # Download & Parse
        response = _download_chapter_html(current_chapter_url)
        if not response:
            print(f"   Failed to download chapter {chapter_number_counter} from {current_chapter_url}.")
            metadata['next_expected_chapter_url'] = current_chapter_url # Save current URL to resume later
            _save_download_status(metadata_filepath, metadata)
            break

        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            print(f"   WARNING: Content from {current_chapter_url} is not HTML (Content-Type: {content_type}). Skipping.")
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

        print(f"   Chapter Title: {final_title}")

        safe_title_segment = _sanitize_filename(final_title if final_title else f"chapter_{chapter_number_counter:03d}")
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
            print(f"   Saved to: {filepath}")
        except IOError as e:
            print(f"   ERROR saving file {filepath}: {e}. Will attempt to resume from this chapter next time.")
            metadata['next_expected_chapter_url'] = current_chapter_url
            _save_download_status(metadata_filepath, metadata)
            break 
        except Exception as ex:
            print(f"   UNEXPECTED ERROR saving file {filepath}: {ex}. Will attempt to resume from this chapter next time.")
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
            print("\nEnd of story reached (next chapter link was not found or was invalid).")
            break
        
        # Check for loop on same URL
        if response and current_chapter_url == response.url:
             print(f"\nWARNING: Next chapter URL ({current_chapter_url}) is the same as the current page. Stopping to avoid loop.")
             metadata['next_expected_chapter_url'] = None # Prevent trying this again
             _save_download_status(metadata_filepath, metadata)
             break

        chapter_number_counter += 1
        delay = random.uniform(1.5, 3.5)
        print(f"   Waiting {delay:.1f} seconds before next chapter...")
        time.sleep(delay)

    print("\nChapter download process completed.")
    return story_output_folder_final # Returns the path of the folder where chapters were saved


if __name__ == '__main__':
    # Quick test for fetch_story_metadata_and_first_chapter
    # test_overview_url = "https://www.royalroad.com/fiction/115305/pioneer-of-the-abyss-an-underwater-livestreamed" # User example URL
    test_overview_url = "https://www.royalroad.com/fiction/76844/the-final-wish-a-litrpg-adventure" # Another example
    # test_overview_url = "https://www.royalroad.com/fiction/21220/mother-of-learning" # MoL
    print(f"Starting metadata fetch test for: {test_overview_url}")
    metadata = fetch_story_metadata_and_first_chapter(test_overview_url)
    if metadata:
        print("\nMetadata found:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")

        # Quick test for download_story (optional, this would usually go in main.py)
        if metadata.get('first_chapter_url') and metadata.get('story_slug'):
            test_output_base_folder = "downloaded_story_test_from_overview"
            if not os.path.exists(test_output_base_folder):
                os.makedirs(test_output_base_folder, exist_ok=True)

            print(f"\nStarting download test for: {metadata['first_chapter_url']}")
            # Passes test_output_base_folder, and download_story will create the slug subfolder within it.
            downloaded_to = download_story(
                first_chapter_url=metadata['first_chapter_url'],
                output_folder=test_output_base_folder,
                story_slug_override=metadata['story_slug'],
                overview_url=test_overview_url, # Pass the new param
                story_title=metadata['story_title'], # Pass the new param
                author_name=metadata['author_name'] # Pass the new param
            )
            print(f"Test download completed. Chapters in: {downloaded_to}")
        else:
            print("\nCould not test download, incomplete metadata (first chapter URL or slug missing).")

    else:
        print("\nMetadata fetch test failed.")