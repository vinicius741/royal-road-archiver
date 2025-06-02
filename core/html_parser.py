import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from core.logging_utils import log_info, log_warning, log_error, log_debug

def _sanitize_filename(filename):
    """Sanitizes a filename by removing or replacing invalid characters."""
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.replace('\n', '_').replace('\r', '_')
    filename = filename.strip()
    if not filename:
        filename = "untitled"
    return filename

def parse_story_metadata_from_html(overview_url: str, html_content: str) -> dict:
    """
    Parses story metadata from the provided HTML content.
    """
    # Placeholder for metadata extraction logic
    # This will be adapted from core/crawler.py
    log_debug(f"Parsing story metadata from HTML for URL: {overview_url}")
    soup = BeautifulSoup(html_content, 'html.parser')
    metadata = {
        'overview_url': overview_url,
        'story_title': "Unknown Title", # Renamed from 'title' for consistency
        'author_name': "Unknown Author", # Renamed from 'author' for consistency
        'story_slug': None,
        'cover_image_url': None,
        'description': None,
        'tags': [],
        'publisher': None,
        'story_id': None,
        # Fields not in crawler.py's fetch_story_metadata_and_first_chapter, but kept from initial version
        'status': "Unknown",
        'published_date': "Unknown",
        'updated_date': "Unknown",
        'rating': "N/A",
        'chapters': [] # This will be populated by chapter parsing logic elsewhere
    }

    # Attempt to parse JSON-LD
    json_ld_data = None
    script_tag_ld = soup.find('script', type='application/ld+json')
    if script_tag_ld:
        try:
            json_ld_data = json.loads(script_tag_ld.string)
        except json.JSONDecodeError as e:
            log_warning(f"Error parsing JSON-LD from {overview_url}: {e}")

    # Extract Title
    title_tag = soup.select_one('div.fic-title h1.font-white')
    if title_tag:
        metadata['story_title'] = title_tag.text.strip()
        log_info(f"Found title: {metadata['story_title']} (from h1.font-white)", url=overview_url)
    else:
        # Fallback to the page's <title> tag
        page_title_tag = soup.find('title')
        if page_title_tag:
            full_title = page_title_tag.text.strip()
            metadata['story_title'] = full_title.split('|')[0].strip() # Takes the part before the pipe
            log_info(f"Found title: {metadata['story_title']} (from page title tag)", url=overview_url)
        else:
            log_warning("Title not found.", url=overview_url)

    # Extract Author
    author_link = soup.select_one('div.fic-title h4 span a[href*="/profile/"]')
    if author_link:
        metadata['author_name'] = author_link.text.strip()
        log_info(f"Found author: {metadata['author_name']} (from profile link)", url=overview_url)
    elif json_ld_data:
        try:
            if isinstance(json_ld_data.get('author'), str):
                metadata['author_name'] = json_ld_data['author'].strip()
                log_info(f"Found author: {metadata['author_name']} (from JSON-LD string)", url=overview_url)
            elif isinstance(json_ld_data.get('author'), dict) and json_ld_data['author'].get('name'):
                metadata['author_name'] = json_ld_data['author']['name'].strip()
                log_info(f"Found author: {metadata['author_name']} (from JSON-LD object)", url=overview_url)
            elif isinstance(json_ld_data.get('author'), list) and len(json_ld_data['author']) > 0:
                first_author = json_ld_data['author'][0]
                if isinstance(first_author, str):
                    metadata['author_name'] = first_author.strip()
                    log_info(f"Found author: {metadata['author_name']} (from JSON-LD list of strings)", url=overview_url)
                elif isinstance(first_author, dict) and first_author.get('name'):
                    metadata['author_name'] = first_author['name'].strip()
                    log_info(f"Found author: {metadata['author_name']} (from JSON-LD list of objects)", url=overview_url)
        except Exception as e:
            log_warning(f"Error processing JSON-LD for author name from {overview_url}: {e}")
    if metadata['author_name'] == "Unknown Author":
        log_warning("Author not found.", url=overview_url)


    # Extract Tags (Keywords)
    tags_list = []
    keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
    if keywords_tag and keywords_tag.get('content'):
        tags_list.extend([tag.strip() for tag in keywords_tag['content'].split(',') if tag.strip()])

    if json_ld_data:
        if isinstance(json_ld_data.get('genre'), str):
            tags_list.append(json_ld_data['genre'].strip())
        elif isinstance(json_ld_data.get('genre'), list):
            tags_list.extend([g.strip() for g in json_ld_data['genre'] if isinstance(g, str) and g.strip()])
        if isinstance(json_ld_data.get('keywords'), str):
            tags_list.extend([tag.strip() for tag in json_ld_data['keywords'].split(',') if tag.strip()])
        elif isinstance(json_ld_data.get('keywords'), list):
            tags_list.extend([k.strip() for k in json_ld_data['keywords'] if isinstance(k, str) and k.strip()])

    if tags_list:
        metadata['tags'] = sorted(list(set(tags_list)))
        log_info(f"Found tags: {metadata['tags']}", url=overview_url)
    else:
        log_warning("Tags not found.", url=overview_url)

    # Extract Description
    og_description_tag = soup.find('meta', property='og:description')
    if og_description_tag and og_description_tag.get('content'):
        metadata['description'] = og_description_tag['content']
        log_info("Found description (from og:description).", url=overview_url)
    else:
        twitter_description_tag = soup.find('meta', attrs={'name': 'twitter:description'})
        if twitter_description_tag and twitter_description_tag.get('content'):
            metadata['description'] = twitter_description_tag['content']
            log_info("Found description (from twitter:description).", url=overview_url)
        elif json_ld_data and isinstance(json_ld_data.get('description'), str):
            metadata['description'] = json_ld_data['description']
            log_info("Found description (from JSON-LD).", url=overview_url)
        else:
            log_warning("Description not found.", url=overview_url)
            metadata['description'] = "<p>No description available.</p>" # Default

    # Extract Cover Image URL
    og_image_tag = soup.find('meta', property='og:image')
    if og_image_tag and og_image_tag.get('content'):
        metadata['cover_image_url'] = urljoin(overview_url, og_image_tag['content'])
    else:
        twitter_image_tag = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image_tag and twitter_image_tag.get('content'):
            metadata['cover_image_url'] = urljoin(overview_url, twitter_image_tag['content'])
        elif json_ld_data:
            image_data = json_ld_data.get('image')
            if isinstance(image_data, str):
                metadata['cover_image_url'] = urljoin(overview_url, image_data)
            elif isinstance(image_data, dict) and isinstance(image_data.get('url'), str):
                metadata['cover_image_url'] = urljoin(overview_url, image_data['url'])
            elif isinstance(image_data, list) and len(image_data) > 0:
                first_image = image_data[0]
                if isinstance(first_image, str):
                    metadata['cover_image_url'] = urljoin(overview_url, first_image)
                elif isinstance(first_image, dict) and isinstance(first_image.get('url'), str):
                    metadata['cover_image_url'] = urljoin(overview_url, first_image['url'])
    if metadata['cover_image_url']:
        log_info(f"Found cover image URL: {metadata['cover_image_url']}", url=overview_url)
    else:
        log_warning("Cover image not found.", url=overview_url)

    # Extract Publisher
    if json_ld_data:
        if isinstance(json_ld_data.get('publisher'), dict) and isinstance(json_ld_data['publisher'].get('name'), str):
            metadata['publisher'] = json_ld_data['publisher']['name'].strip()
        elif isinstance(json_ld_data.get('sourceOrganization'), dict) and isinstance(json_ld_data['sourceOrganization'].get('name'), str):
            metadata['publisher'] = json_ld_data['sourceOrganization']['name'].strip()
    if metadata['publisher']:
        log_info(f"Found publisher: {metadata['publisher']}", url=overview_url)
    else:
        log_warning("Publisher not found.", url=overview_url)


    # Story ID (extracted from overview_url - consistent with crawler.py's usage pattern for story_id)
    # Example fiction URL: https://www.royalroad.com/fiction/12345/some-story-name
    # Example chapter URL (less ideal for story ID): https://www.royalroad.com/fiction/12345/some-story-name/chapter/123456/chapter-one
    # The crawler.py extracts story_id from the overview_url.
    story_id_match = re.search(r'/fiction/(\d+)', overview_url)
    if story_id_match:
        metadata['story_id'] = story_id_match.group(1)
        log_info(f"Extracted Story ID: {metadata['story_id']} from URL: {overview_url}")
    else:
        log_warning("Could not extract Story ID from overview URL using /fiction/(\\d+)", url=overview_url)
        # Attempt with /story/ as per original html_parser version, if applicable to other sites
        story_id_match_alt = re.search(r'/story/(\d+)', overview_url)
        if story_id_match_alt:
            metadata['story_id'] = story_id_match_alt.group(1)
            log_info(f"Extracted Story ID: {metadata['story_id']} from URL (alt pattern /story/): {overview_url}")
        else:
            log_warning("Could not extract Story ID from overview URL using /story/(\\d+) either.", url=overview_url)


    # Slug for filenames/directories (based on title)
    if metadata['story_title'] and metadata['story_title'] != "Unknown Title":
        metadata['story_slug'] = _sanitize_filename(metadata['story_title'])
    else:
        # Fallback slug if title is not found or is "Unknown Title"
        # The crawler.py has more complex slug generation from URLs, but here we only have HTML and overview_url
        # If story_id is available, it's a good candidate for a unique slug component
        if metadata['story_id']:
            metadata['story_slug'] = _sanitize_filename(f"story_{metadata['story_id']}")
            log_info(f"Generated slug from story_id due to missing/generic title: {metadata['story_slug']}", url=overview_url)
        else:
            # Last resort, similar to crawler.py's timestamped slug, but trying to be deterministic if overview_url is consistent
            url_based_slug_part = re.sub(r'[^a-zA-Z0-9]+', '_', overview_url.split('/')[-1] or overview_url.split('/')[-2] or "unknown_story")
            metadata['story_slug'] = _sanitize_filename(f"story_{url_based_slug_part}")
            log_warning(f"Generated generic slug from URL components due to missing title and story_id: {metadata['story_slug']}", url=overview_url)


    log_info(f"Successfully parsed metadata for story: {metadata.get('story_title', 'N/A')}", url=overview_url)
    return metadata

def parse_chapter_data_from_html(chapter_html_content: str, current_page_url: str) -> dict:
    """
    Parses chapter data (title, content, next chapter URL) from the provided HTML content.
    """
    log_debug(f"Parsing chapter data from HTML for URL: {current_page_url}")
    soup = BeautifulSoup(chapter_html_content, 'html.parser')
    parsed_data = {
        'title': "Unknown Chapter Title", # Default
        'content_html': "<p>Content not found.</p>", # Default
        'next_chapter_url': None,
        'chapter_id': None # Default
    }

    # Chapter Title Extraction (adapted from _parse_chapter_html in crawler.py)
    title_tag_h1_specific = soup.select_one('div.fic-header h1.font-white.break-word, h1.break-word[property="name"]')
    title_tag_chapter_content_h1 = soup.select_one('div.chapter-content h1') # As per crawler.py comment
    title_tag_general_h1 = soup.find('h1') # General h1
    page_title_tag = soup.find('title') # Page <title>

    title_str = "Unknown Chapter Title" # Temp variable
    if title_tag_h1_specific:
        title_str = title_tag_h1_specific.text.strip()
        log_info(f"Found chapter title (specific h1): {title_str}", url=current_page_url)
    elif title_tag_chapter_content_h1:
        title_str = title_tag_chapter_content_h1.text.strip()
        log_info(f"Found chapter title (chapter-content h1): {title_str}", url=current_page_url)
    elif title_tag_general_h1:
        title_str = title_tag_general_h1.text.strip()
        log_info(f"Found chapter title (general h1): {title_str}", url=current_page_url)
    elif page_title_tag:
        title_text_full = page_title_tag.text.split('|')[0].strip()
        # Heuristic to remove story name from chapter title if present (from crawler.py)
        parts = title_text_full.split(' - ')
        if len(parts) > 1 and len(parts[0]) < len(parts[1]): # Chapter title often shorter than story title
            title_str = parts[0].strip()
        else:
            title_str = title_text_full
        log_info(f"Found chapter title (page title tag): {title_str}", url=current_page_url)
    else:
        log_warning("Chapter title not found using any known method.", url=current_page_url)
    
    parsed_data['title'] = title_str

    # Chapter Content Extraction (adapted from _parse_chapter_html in crawler.py)
    content_div = soup.find('div', class_='chapter-content')
    if not content_div:
        content_div = soup.find('div', class_='prose') # Fallback from crawler.py
    
    if content_div:
        parsed_data['content_html'] = str(content_div)
        log_info("Found chapter content.", url=current_page_url)
    else:
        log_error("Chapter content container not found (tried .chapter-content, .prose).", url=current_page_url)
        # parsed_data['content_html'] remains default "<p>Content not found.</p>"

    # Next Chapter URL Extraction (adapted from _parse_chapter_html in crawler.py)
    next_chapter_url_val = None # Temp variable
    next_link_tag_rel = soup.find('link', rel='next') # Priority: rel="next"
    if next_link_tag_rel and next_link_tag_rel.get('href'):
        relative_url = next_link_tag_rel['href']
        next_chapter_url_val = urljoin(current_page_url, relative_url)
        log_info(f"Found next chapter URL (rel=next): {next_chapter_url_val}", url=current_page_url)
    else:
        # Fallback to buttons/links with text "Next", "Próximo", etc.
        next_buttons = soup.select('a.btn[href], a.button[href], a[class*="next" i][href]')
        found_button = False
        for button in next_buttons:
            button_text = button.text.strip().lower()
            if "next" in button_text or "próximo" in button_text or "proximo" in button_text:
                relative_url = button.get('href')
                if relative_url and relative_url != "#" and "javascript:void(0)" not in relative_url:
                    next_chapter_url_val = urljoin(current_page_url, relative_url)
                    log_info(f"Found next chapter URL (button heuristic): {next_chapter_url_val}", url=current_page_url)
                    found_button = True
                    break
        if not found_button:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                link_text = link.text.strip().lower()
                # Avoid "previous" links and ensure it's likely a chapter progression link
                if ("next" in link_text or "próximo" in link_text or "proximo" in link_text) and \
                   ("previous" not in link_text and "anterior" not in link_text):
                    relative_url = link.get('href')
                    if relative_url and relative_url != "#" and "javascript:void(0)" not in relative_url:
                        # Check if it looks like a chapter URL (from crawler.py)
                        if '/chapter/' in relative_url or '/fiction/' in relative_url or re.match(r'.*/\d+/?$', relative_url):
                            next_chapter_url_val = urljoin(current_page_url, relative_url)
                            log_info(f"Found next chapter URL (generic link text search): {next_chapter_url_val}", url=current_page_url)
                            break
    
    if next_chapter_url_val:
        # Basic check to prevent loop or non-chapter pages (similar to original html_parser)
        if next_chapter_url_val != current_page_url and ("/chapter/" in next_chapter_url_val or "/fiction/" in next_chapter_url_val or re.search(r'/\d+(?:/[^/]+)?$', next_chapter_url_val)): # Relaxed check, as some sites might not use /chapter/
            parsed_data['next_chapter_url'] = next_chapter_url_val
        else:
            log_info(f"Next chapter link found ({next_chapter_url_val}), but it might be same page or not a valid chapter progression. Discarding.", url=current_page_url)
            parsed_data['next_chapter_url'] = None # Explicitly set to None
    else:
        log_info("No next chapter link found. This might be the last chapter.", url=current_page_url)

    # Chapter ID Extraction (from current_page_url, as in original html_parser)
    chapter_id_match = re.search(r'/chapter/(\d+)', current_page_url)
    if chapter_id_match:
        parsed_data['chapter_id'] = chapter_id_match.group(1)
        log_info(f"Extracted Chapter ID: {parsed_data['chapter_id']} from URL: {current_page_url}")
    else:
        # Fallback: use sanitized title if no direct ID is available from URL
        if parsed_data['title'] != "Unknown Chapter Title":
            parsed_data['chapter_id'] = _sanitize_filename(parsed_data['title'])
            log_info(f"Generated Chapter ID from title: {parsed_data['chapter_id']}", url=current_page_url)
        else:
            # Fallback for truly unknown chapters, perhaps a number based on URL segment if any
            url_parts = current_page_url.split('/')
            potential_id_part = url_parts[-1] if url_parts[-1] else url_parts[-2] if len(url_parts) > 1 else "unknown"
            parsed_data['chapter_id'] = _sanitize_filename(f"chapter_{potential_id_part}")
            log_warning(f"Could not extract chapter_id from URL, generated generic ID: {parsed_data['chapter_id']}", url=current_page_url)

    return parsed_data
