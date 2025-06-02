import os
import re
import time
import typer
from typing import Tuple, Optional, Dict

from .logging_utils import log_info, log_warning, log_error, log_debug
# It's better to import this if it's going to be used by helpers,
# rather than passing the function around or re-implementing.
from .crawler import fetch_story_metadata_and_first_chapter

def is_overview_url(url: str) -> bool:
    """Checks if the URL is likely an overview page (does not contain /chapter/)."""
    return "/chapter/" not in url and "/fiction/" in url

def _infer_slug_from_url(url: str) -> Optional[str]:
    """Tries to infer a story slug from a URL."""
    if not url:
        return None
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

def resolve_crawl_url_and_metadata_logic(
    story_url_arg: str,
    start_chapter_url_param: Optional[str]
) -> Dict:
    """
    Determines the actual URL to start crawling from and fetches metadata if applicable.
    This is the logic-only version.
    """
    logs = []
    fetched_metadata: Optional[Dict] = None
    actual_crawl_start_url: Optional[str] = None
    initial_slug: Optional[str] = None
    resolved_overview_url: Optional[str] = None

    if is_overview_url(story_url_arg):
        logs.append({'level': 'info', 'message': f"Story URL '{story_url_arg}' detected as overview. Fetching metadata..."})
        resolved_overview_url = story_url_arg # story_url_arg is the overview URL
        metadata_result = fetch_story_metadata_and_first_chapter(story_url_arg)
        if not metadata_result:
            logs.append({'level': 'warning', 'message': f"Warning: Failed to fetch metadata from {story_url_arg}. Proceeding with potentially limited info."})
            # In this case, fetched_metadata remains None, but resolved_overview_url is still story_url_arg
        else:
            fetched_metadata = metadata_result
            initial_slug = fetched_metadata.get('story_slug')
            # overview_url should now be part of metadata_result directly
            # resolved_overview_url = fetched_metadata.get('overview_url', story_url_arg) # Ensure it's set
            logs.append({'level': 'info', 'message': f"Metadata fetched. Initial slug: '{initial_slug}', First chapter from meta: '{fetched_metadata.get('first_chapter_url')}', Overview URL from meta: '{fetched_metadata.get('overview_url')}'"})

        if start_chapter_url_param:
            actual_crawl_start_url = start_chapter_url_param
            logs.append({'level': 'info', 'message': f"Using user-specified start chapter URL: {actual_crawl_start_url}"})
        elif fetched_metadata and fetched_metadata.get('first_chapter_url'):
            actual_crawl_start_url = fetched_metadata['first_chapter_url']
            logs.append({'level': 'info', 'message': f"Using first chapter URL from metadata: {actual_crawl_start_url}"})
        else:
            logs.append({'level': 'error', 'message': f"Error: Overview URL provided but could not determine first chapter URL and no --start-chapter-url given."})
            return {
                'actual_crawl_start_url': None,
                'fetched_metadata': fetched_metadata,
                'initial_slug': initial_slug,
                'resolved_overview_url': resolved_overview_url,
                'logs': logs
            } # Error case

    else: # story_url_arg is a chapter URL
        logs.append({'level': 'info', 'message': f"Story URL '{story_url_arg}' detected as a chapter page."})
        # If it's a chapter URL, we don't have an immediate overview URL unless metadata is fetched later
        # For now, resolved_overview_url remains None. It might be populated if metadata is fetched
        # based on some other logic, but this function primarily handles the direct story_url_arg.
        # The task implies download_story will get it, so if it's not an overview_url,
        # fetch_story_metadata_and_first_chapter won't be called here.
        # This means resolved_overview_url will be None if a chapter URL is given.
        # This seems to be the intended logic: overview_url is only resolved if story_url_arg is an overview.
        if start_chapter_url_param:
            actual_crawl_start_url = start_chapter_url_param
            logs.append({'level': 'info', 'message': f"Using user-specified start chapter URL: {actual_crawl_start_url}"})
        else:
            actual_crawl_start_url = story_url_arg
            logs.append({'level': 'info', 'message': f"Using provided chapter URL as start point: {actual_crawl_start_url}"})
        
        if not initial_slug: 
            initial_slug = _infer_slug_from_url(story_url_arg)
            logs.append({'level': 'info', 'message': f"Inferred initial slug from chapter URL '{story_url_arg}': '{initial_slug}'"})

    if actual_crawl_start_url and "/chapter/" not in actual_crawl_start_url:
        logs.append({'level': 'warning', 'message': f"Warning: Resolved crawl URL '{actual_crawl_start_url}' does not appear to be a valid chapter URL."})

    return {
        'actual_crawl_start_url': actual_crawl_start_url,
        'fetched_metadata': fetched_metadata,
        'initial_slug': initial_slug,
        'resolved_overview_url': resolved_overview_url, # Added
        'logs': logs
    }

def resolve_crawl_url_and_metadata(
    story_url_arg: str,
    start_chapter_url_param: Optional[str]
) -> Tuple[Optional[str], Optional[Dict], Optional[str], Optional[str]]:
    """
    Determines the actual URL to start crawling from and fetches metadata if applicable.
    This function now calls the _logic version and handles CLI output.
    Returns: actual_crawl_start_url, fetched_metadata, initial_slug, resolved_overview_url
    """
    result = resolve_crawl_url_and_metadata_logic(story_url_arg, start_chapter_url_param)

    for log_entry in result['logs']:
        if log_entry['level'] == 'info':
            log_info(log_entry['message'])
        elif log_entry['level'] == 'warning':
            log_warning(log_entry['message'])
        elif log_entry['level'] == 'error':
            log_error(log_entry['message'])

    return result['actual_crawl_start_url'], result['fetched_metadata'], result['initial_slug'], result['resolved_overview_url']

def determine_story_slug_for_folders_logic(
    story_url_arg: str,
    start_chapter_url_param: Optional[str],
    fetched_metadata: Optional[Dict],
    initial_slug_from_resolve: Optional[str],
    title_param: Optional[str]
) -> Dict:
    """Determines the definitive story slug for use in folder naming. Logic-only version."""
    logs = []
    story_slug: Optional[str] = None

    if fetched_metadata and fetched_metadata.get('story_slug'):
        story_slug = fetched_metadata['story_slug']
        logs.append({'level': 'info', 'message': f"Using slug from fetched metadata: '{story_slug}'"})
    elif initial_slug_from_resolve:
        story_slug = initial_slug_from_resolve
        logs.append({'level': 'info', 'message': f"Using initial slug from URL resolve step: '{story_slug}'"})
    
    if not story_slug: 
        story_slug = _infer_slug_from_url(story_url_arg) 
        if story_slug:
            logs.append({'level': 'info', 'message': f"Inferred slug from story_url_arg '{story_url_arg}': '{story_slug}'"})

    if not story_slug and start_chapter_url_param:
        story_slug = _infer_slug_from_url(start_chapter_url_param) 
        if story_slug:
            logs.append({'level': 'info', 'message': f"Inferred slug from start_chapter_url_param '{start_chapter_url_param}': '{story_slug}'"})

    if not story_slug:
        if title_param and title_param not in ["Archived Royal Road Story", "Unknown Story"]:
            slug_from_title = re.sub(r'[^\w\s-]', '', title_param).strip()
            slug_from_title = re.sub(r'\s+', '_', slug_from_title).lower()
            story_slug = slug_from_title[:50] 
            logs.append({'level': 'info', 'message': f"Generated slug from title_param: '{story_slug}'"})
        else:
            story_slug = f"story_{int(time.time())}"
            logs.append({'level': 'warning', 'message': f"Warning: Could not determine a descriptive slug. Using generic timed slug: '{story_slug}'"})
    
    if story_slug: # Ensure story_slug is not None before sanitizing
        story_slug = re.sub(r'[\\/*?:"<>|]', "", story_slug)
        story_slug = re.sub(r'\s+', '_', story_slug).lower()
    
    final_slug = story_slug if story_slug else f"story_{int(time.time())}" 
    logs.append({'level': 'info', 'message': f"Final story slug for folders: '{final_slug}'"})
    
    return {'story_slug': final_slug, 'logs': logs}

def determine_story_slug_for_folders(
    story_url_arg: str,
    start_chapter_url_param: Optional[str],
    fetched_metadata: Optional[Dict],
    initial_slug_from_resolve: Optional[str],
    title_param: Optional[str]
) -> str:
    """Determines the definitive story slug for use in folder naming."""
    result = determine_story_slug_for_folders_logic(
        story_url_arg,
        start_chapter_url_param,
        fetched_metadata,
        initial_slug_from_resolve,
        title_param
    )

    for log_entry in result['logs']:
        if log_entry['level'] == 'info':
            log_info(log_entry['message'])
        elif log_entry['level'] == 'warning':
            log_warning(log_entry['message'])
        # No error level defined for this function's logs in the original code

    return result['story_slug']

def finalize_epub_metadata_logic(
    title_param: Optional[str],
    author_param: Optional[str],
    cover_url_param: Optional[str],
    description_param: Optional[str],
    tags_param: Optional[str], # Comma-separated string from Typer
    publisher_param: Optional[str],
    fetched_metadata: Optional[Dict],
    story_slug: str
) -> Dict:
    """Finalizes metadata for EPUB creation. Logic-only version."""
    logs = []
    final_story_title = "Archived Royal Road Story" # Default
    final_author_name = "Royal Road Archiver"   # Default
    final_cover_image_url: Optional[str] = None
    final_description: Optional[str] = None
    final_tags: list = []
    final_publisher: Optional[str] = None

    if title_param:
        final_story_title = title_param
    elif fetched_metadata and fetched_metadata.get('story_title') and fetched_metadata['story_title'] != "Unknown Title":
        final_story_title = fetched_metadata['story_title']
    elif story_slug and not story_slug.startswith("story_"): # Infer from a good slug
        final_story_title = story_slug.replace('-', ' ').replace('_', ' ').title()

    if author_param:
        final_author_name = author_param
    elif fetched_metadata and fetched_metadata.get('author_name') and fetched_metadata['author_name'] != "Unknown Author":
        final_author_name = fetched_metadata['author_name']

    # Finalize Cover Image URL
    if cover_url_param:
        final_cover_image_url = cover_url_param
    elif fetched_metadata and fetched_metadata.get('cover_image_url'):
        final_cover_image_url = fetched_metadata['cover_image_url']

    # Finalize Description
    if description_param:
        final_description = description_param
    elif fetched_metadata and fetched_metadata.get('description'):
        final_description = fetched_metadata['description']

    # Finalize Tags
    if tags_param: # Comma-separated string
        final_tags = [tag.strip() for tag in tags_param.split(',') if tag.strip()]
    elif fetched_metadata and fetched_metadata.get('tags'): # Already a list
        final_tags = fetched_metadata['tags']
    
    # Finalize Publisher
    if publisher_param:
        final_publisher = publisher_param
    elif fetched_metadata and fetched_metadata.get('publisher'):
        final_publisher = fetched_metadata['publisher']

    logs.append({'level': 'info', 'message': f"EPUB Metadata: Title='{final_story_title}', Author='{final_author_name}', Cover='{final_cover_image_url}', Publisher='{final_publisher}', Tags='{final_tags}', Description Length='{len(final_description) if final_description else 0}'"})
    
    return {
        'final_story_title': final_story_title,
        'final_author_name': final_author_name,
        'final_cover_image_url': final_cover_image_url,
        'final_description': final_description,
        'final_tags': final_tags,
        'final_publisher': final_publisher,
        'logs': logs
    }

def finalize_epub_metadata(
    title_param: Optional[str],
    author_param: Optional[str],
    cover_url_param: Optional[str],
    description_param: Optional[str],
    tags_param: Optional[str], # Comma-separated string from Typer
    publisher_param: Optional[str],
    fetched_metadata: Optional[Dict],
    story_slug: str
) -> Tuple[str, str, Optional[str], Optional[str], list, Optional[str]]:
    """Finalizes metadata for EPUB creation."""
    result = finalize_epub_metadata_logic(
        title_param,
        author_param,
        cover_url_param,
        description_param,
        tags_param,
        publisher_param,
        fetched_metadata,
        story_slug
    )

    for log_entry in result['logs']:
        # Assuming all logs from this function are info level as per original
        if log_entry['level'] == 'info':
            log_info(log_entry['message'])
        # Add other levels here if they were used in the original, e.g.
        # elif log_entry['level'] == 'warning':
        #     log_warning(log_entry['message'])

    return (
        result['final_story_title'],
        result['final_author_name'],
        result['final_cover_image_url'],
        result['final_description'],
        result['final_tags'],
        result['final_publisher']
    )