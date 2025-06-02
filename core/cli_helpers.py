import os
import re
import time
import typer
from typing import Tuple, Optional, Dict

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

def resolve_crawl_url_and_metadata(
    story_url_arg: str,
    start_chapter_url_param: Optional[str]
) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
    """
    Determines the actual URL to start crawling from and fetches metadata if applicable.

    Returns:
        A tuple containing:
        - actual_crawl_start_url (str | None): The URL to start crawling from.
        - fetched_metadata (dict | None): Fetched metadata if story_url_arg was an overview.
        - initial_slug (str | None): An initial slug derived from metadata or URL.
    """
    fetched_metadata: Optional[Dict] = None
    actual_crawl_start_url: Optional[str] = None
    initial_slug: Optional[str] = None

    if is_overview_url(story_url_arg):
        typer.echo(f"Story URL '{story_url_arg}' detected as overview. Fetching metadata...")
        metadata_result = fetch_story_metadata_and_first_chapter(story_url_arg)
        if not metadata_result:
            typer.secho(f"Warning: Failed to fetch metadata from {story_url_arg}. Proceeding with potentially limited info.", fg=typer.colors.YELLOW)
        else:
            fetched_metadata = metadata_result
            initial_slug = fetched_metadata.get('story_slug')
            typer.echo(f"Metadata fetched. Initial slug: '{initial_slug}', First chapter from meta: '{fetched_metadata.get('first_chapter_url')}'")

        if start_chapter_url_param:
            actual_crawl_start_url = start_chapter_url_param
            typer.echo(f"Using user-specified start chapter URL: {actual_crawl_start_url}")
        elif fetched_metadata and fetched_metadata.get('first_chapter_url'):
            actual_crawl_start_url = fetched_metadata['first_chapter_url']
            typer.echo(f"Using first chapter URL from metadata: {actual_crawl_start_url}")
        else:
            typer.secho(f"Error: Overview URL provided but could not determine first chapter URL and no --start-chapter-url given.", fg=typer.colors.RED)
            return None, fetched_metadata, initial_slug # Error case

    else: # story_url_arg is a chapter URL
        typer.echo(f"Story URL '{story_url_arg}' detected as a chapter page.")
        if start_chapter_url_param:
            actual_crawl_start_url = start_chapter_url_param
            typer.echo(f"Using user-specified start chapter URL: {actual_crawl_start_url}")
        else:
            actual_crawl_start_url = story_url_arg
            typer.echo(f"Using provided chapter URL as start point: {actual_crawl_start_url}")
        
        # Try to infer slug from the chapter URL if no metadata pass was made
        if not initial_slug: # Should be true here
            initial_slug = _infer_slug_from_url(story_url_arg)
            typer.echo(f"Inferred initial slug from chapter URL '{story_url_arg}': '{initial_slug}'")


    if actual_crawl_start_url and "/chapter/" not in actual_crawl_start_url:
        typer.secho(f"Warning: Resolved crawl URL '{actual_crawl_start_url}' does not appear to be a valid chapter URL.", fg=typer.colors.YELLOW)

    return actual_crawl_start_url, fetched_metadata, initial_slug

def determine_story_slug_for_folders(
    story_url_arg: str,
    start_chapter_url_param: Optional[str],
    fetched_metadata: Optional[Dict],
    initial_slug_from_resolve: Optional[str],
    title_param: Optional[str]
) -> str:
    """Determines the definitive story slug for use in folder naming."""
    story_slug: Optional[str] = None

    if fetched_metadata and fetched_metadata.get('story_slug'):
        story_slug = fetched_metadata['story_slug']
        typer.echo(f"Using slug from fetched metadata: '{story_slug}'")
    elif initial_slug_from_resolve:
        story_slug = initial_slug_from_resolve
        typer.echo(f"Using initial slug from URL resolve step: '{story_slug}'")
    
    if not story_slug: # If metadata didn't provide it or resolve didn't find it
        story_slug = _infer_slug_from_url(story_url_arg) # Try main story URL
        if story_slug:
             typer.echo(f"Inferred slug from story_url_arg '{story_url_arg}': '{story_slug}'")

    if not story_slug and start_chapter_url_param:
        story_slug = _infer_slug_from_url(start_chapter_url_param) # Then try from start_chapter_url
        if story_slug:
            typer.echo(f"Inferred slug from start_chapter_url_param '{start_chapter_url_param}': '{story_slug}'")

    if not story_slug:
        if title_param and title_param not in ["Archived Royal Road Story", "Unknown Story"]:
            # Sanitize title to create a slug
            slug_from_title = re.sub(r'[^\w\s-]', '', title_param).strip()
            slug_from_title = re.sub(r'\s+', '_', slug_from_title).lower()
            story_slug = slug_from_title[:50] # Limit length
            typer.echo(f"Generated slug from title_param: '{story_slug}'")
        else:
            story_slug = f"story_{int(time.time())}"
            typer.secho(f"Warning: Could not determine a descriptive slug. Using generic timed slug: '{story_slug}'", fg=typer.colors.YELLOW)
    
    # Final sanitization (though _infer_slug_from_url already does some)
    story_slug = re.sub(r'[\\/*?:"<>|]', "", story_slug)
    story_slug = re.sub(r'\s+', '_', story_slug).lower()
    
    typer.echo(f"Final story slug for folders: '{story_slug}'")
    return story_slug if story_slug else f"story_{int(time.time())}" # Ensure it's never empty

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

    typer.echo(f"EPUB Metadata: Title='{final_story_title}', Author='{final_author_name}', Cover='{final_cover_image_url}', Publisher='{final_publisher}', Tags='{final_tags}', Description Length='{len(final_description) if final_description else 0}'")
    return final_story_title, final_author_name, final_cover_image_url, final_description, final_tags, final_publisher