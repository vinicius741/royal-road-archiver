import unittest
from typing import Dict, Optional, List

# Assuming your project structure allows this import
from core.cli_helpers import finalize_epub_metadata

class TestFinalizeEpubMetadata(unittest.TestCase):

    def test_cli_params_override_fetched(self):
        title_param = "CLI Title"
        author_param = "CLI Author"
        cover_url_param = "cli_cover.jpg"
        description_param = "CLI Description."
        tags_param = "tag1,tag2, tag3 " # Comma-separated with potential extra spaces
        publisher_param = "CLI Publisher"
        
        fetched_metadata: Dict = {
            'story_title': "Fetched Title",
            'author_name': "Fetched Author",
            'cover_image_url': "fetched_cover.jpg",
            'description': "Fetched Description.",
            'tags': ['fetched_tag1', 'fetched_tag2'],
            'publisher': "Fetched Publisher"
        }
        story_slug = "test-slug"

        final_title, final_author, final_cover, final_desc, final_tags, final_publisher = finalize_epub_metadata(
            title_param=title_param,
            author_param=author_param,
            cover_url_param=cover_url_param,
            description_param=description_param,
            tags_param=tags_param,
            publisher_param=publisher_param,
            fetched_metadata=fetched_metadata,
            story_slug=story_slug
        )

        self.assertEqual(final_title, title_param)
        self.assertEqual(final_author, author_param)
        self.assertEqual(final_cover, cover_url_param)
        self.assertEqual(final_desc, description_param)
        self.assertEqual(final_tags, ['tag1', 'tag2', 'tag3']) # Expect parsed and stripped list
        self.assertEqual(final_publisher, publisher_param)

    def test_fetched_metadata_used_when_cli_none(self):
        fetched_story_title = "Fetched Story Title"
        fetched_author_name = "Fetched Story Author"
        fetched_cover_url = "http://example.com/fetched_cover.png"
        fetched_description = "This is the fetched description."
        fetched_tags_list = ["Fantasy", "Adventure", "Fetched"]
        fetched_publisher = "Fetched Publishing House"

        fetched_metadata: Dict = {
            'story_title': fetched_story_title,
            'author_name': fetched_author_name,
            'cover_image_url': fetched_cover_url,
            'description': fetched_description,
            'tags': fetched_tags_list, # Already a list
            'publisher': fetched_publisher
        }
        story_slug = "another-slug"

        final_title, final_author, final_cover, final_desc, final_tags, final_publisher = finalize_epub_metadata(
            title_param=None,
            author_param=None,
            cover_url_param=None,
            description_param=None,
            tags_param=None, # CLI tags are None
            publisher_param=None,
            fetched_metadata=fetched_metadata,
            story_slug=story_slug
        )

        self.assertEqual(final_title, fetched_story_title)
        self.assertEqual(final_author, fetched_author_name)
        self.assertEqual(final_cover, fetched_cover_url)
        self.assertEqual(final_desc, fetched_description)
        self.assertEqual(final_tags, fetched_tags_list)
        self.assertEqual(final_publisher, fetched_publisher)

    def test_defaults_and_slug_fallback(self):
        # Case 1: Everything is None or empty
        final_title, final_author, final_cover, final_desc, final_tags, final_publisher = finalize_epub_metadata(
            title_param=None,
            author_param=None,
            cover_url_param=None,
            description_param=None,
            tags_param=None,
            publisher_param=None,
            fetched_metadata=None, # No fetched metadata
            story_slug="a-good-slug"
        )

        self.assertEqual(final_title, "A Good Slug") # Title from slug
        self.assertEqual(final_author, "Royal Road Archiver") # Default author
        self.assertIsNone(final_cover)
        self.assertIsNone(final_desc)
        self.assertEqual(final_tags, []) # Empty list for tags
        self.assertIsNone(final_publisher)
        
        # Case 2: Fetched metadata is present but all relevant fields are None or empty
        fetched_metadata_empty: Dict = {
            'story_title': None, # or "Unknown Title" which is also a fallback condition
            'author_name': None, # or "Unknown Author"
            'cover_image_url': None,
            'description': None,
            'tags': [], # Empty list
            'publisher': None
        }
        final_title_2, final_author_2, final_cover_2, final_desc_2, final_tags_2, final_publisher_2 = finalize_epub_metadata(
            title_param=None,
            author_param=None,
            cover_url_param=None,
            description_param=None,
            tags_param=None,
            publisher_param=None,
            fetched_metadata=fetched_metadata_empty,
            story_slug="another-cool-slug"
        )
        self.assertEqual(final_title_2, "Another Cool Slug") # Title from slug
        self.assertEqual(final_author_2, "Royal Road Archiver") # Default author
        self.assertIsNone(final_cover_2)
        self.assertIsNone(final_desc_2)
        self.assertEqual(final_tags_2, [])
        self.assertIsNone(final_publisher_2)

        # Case 3: Slug is also generic, so title defaults
        final_title_3, _, _, _, _, _ = finalize_epub_metadata(
            title_param=None, author_param=None, cover_url_param=None, description_param=None,
            tags_param=None, publisher_param=None, fetched_metadata=None, story_slug="story_12345"
        )
        self.assertEqual(final_title_3, "Archived Royal Road Story")


if __name__ == '__main__':
    unittest.main()


from unittest.mock import patch, MagicMock # Added MagicMock
import time # For determine_story_slug_for_folders_logic fallback slug

# Import the _logic functions
from core.cli_helpers import (
    resolve_crawl_url_and_metadata_logic,
    determine_story_slug_for_folders_logic,
    finalize_epub_metadata_logic,
    _infer_slug_from_url # if needed for some assertions, though it's private
)

class TestCliHelpersLogic(unittest.TestCase):

    @patch('core.cli_helpers.fetch_story_metadata_and_first_chapter')
    def test_resolve_overview_url_success(self, mock_fetch_metadata):
        mock_fetch_metadata.return_value = {
            'story_slug': 'test-slug',
            'first_chapter_url': 'http://example.com/fiction/123/test-slug/chapter/456/chapter-one',
            'story_title': 'Test Story',
            'author_name': 'Test Author'
        }
        story_url = "http://example.com/fiction/123/test-slug"
        result = resolve_crawl_url_and_metadata_logic(story_url, None)

        self.assertEqual(result['actual_crawl_start_url'], 'http://example.com/fiction/123/test-slug/chapter/456/chapter-one')
        self.assertIsNotNone(result['fetched_metadata'])
        self.assertEqual(result['initial_slug'], 'test-slug')
        self.assertTrue(any("Metadata fetched. Initial slug: 'test-slug'" in log['message'] for log in result['logs']))
        self.assertTrue(any(f"Story URL '{story_url}' detected as overview" in log['message'] for log in result['logs']))

    @patch('core.cli_helpers.fetch_story_metadata_and_first_chapter')
    def test_resolve_overview_url_with_start_chapter_param(self, mock_fetch_metadata):
        mock_fetch_metadata.return_value = {
            'story_slug': 'test-slug',
            'first_chapter_url': 'http://example.com/fiction/123/test-slug/chapter/456/chapter-one',
        }
        story_url = "http://example.com/fiction/123/test-slug"
        user_start_chapter = "http://example.com/fiction/123/test-slug/chapter/789/custom-start"
        result = resolve_crawl_url_and_metadata_logic(story_url, user_start_chapter)

        self.assertEqual(result['actual_crawl_start_url'], user_start_chapter)
        self.assertEqual(result['initial_slug'], 'test-slug')
        self.assertTrue(any(f"Using user-specified start chapter URL: {user_start_chapter}" in log['message'] for log in result['logs']))

    @patch('core.cli_helpers.fetch_story_metadata_and_first_chapter')
    def test_resolve_overview_url_metadata_fetch_fails(self, mock_fetch_metadata):
        mock_fetch_metadata.return_value = None # Simulate failure
        story_url = "http://example.com/fiction/123/test-slug-fail"
        result = resolve_crawl_url_and_metadata_logic(story_url, None)

        # Even if metadata fails, if it's an overview and no start_chapter_url_param, it's an error state for URL determination
        self.assertIsNone(result['actual_crawl_start_url'])
        self.assertIsNone(result['fetched_metadata'])
        self.assertIsNone(result['initial_slug'])
        self.assertTrue(any(f"Warning: Failed to fetch metadata from {story_url}" in log['message'] for log in result['logs']))
        self.assertTrue(any("Error: Overview URL provided but could not determine first chapter URL" in log['message'] for log in result['logs']))

    @patch('core.cli_helpers.fetch_story_metadata_and_first_chapter')
    def test_resolve_overview_url_metadata_fetch_fails_with_start_param(self, mock_fetch_metadata):
        mock_fetch_metadata.return_value = None # Simulate failure
        story_url = "http://example.com/fiction/123/test-slug-fail"
        user_start_chapter = "http://example.com/custom/start/chapter"
        result = resolve_crawl_url_and_metadata_logic(story_url, user_start_chapter)

        self.assertEqual(result['actual_crawl_start_url'], user_start_chapter)
        self.assertIsNone(result['fetched_metadata']) # Still None as fetch failed
        self.assertIsNone(result['initial_slug']) # No metadata to get slug from
        self.assertTrue(any(f"Warning: Failed to fetch metadata from {story_url}" in log['message'] for log in result['logs']))
        self.assertTrue(any(f"Using user-specified start chapter URL: {user_start_chapter}" in log['message'] for log in result['logs']))


    def test_resolve_chapter_url_no_param(self):
        story_url = "http://example.com/fiction/123/a-story/chapter/456/the-chapter"
        # No call to fetch_story_metadata_and_first_chapter should happen
        result = resolve_crawl_url_and_metadata_logic(story_url, None)

        self.assertEqual(result['actual_crawl_start_url'], story_url)
        self.assertIsNone(result['fetched_metadata'])
        self.assertEqual(result['initial_slug'], 'a-story') # Inferred from chapter URL
        self.assertTrue(any(f"Story URL '{story_url}' detected as a chapter page." in log['message'] for log in result['logs']))
        self.assertTrue(any(f"Using provided chapter URL as start point: {story_url}" in log['message'] for log in result['logs']))
        self.assertTrue(any(f"Inferred initial slug from chapter URL '{story_url}': 'a-story'" in log['message'] for log in result['logs']))

    def test_resolve_chapter_url_with_start_chapter_param(self):
        story_url = "http://example.com/fiction/123/a-story/chapter/456/the-chapter"
        user_start_chapter = "http://example.com/fiction/123/a-story/chapter/789/custom-start"
        result = resolve_crawl_url_and_metadata_logic(story_url, user_start_chapter)

        self.assertEqual(result['actual_crawl_start_url'], user_start_chapter)
        self.assertIsNone(result['fetched_metadata'])
        # initial_slug is inferred from the original story_url_arg, not the start_chapter_url_param in this path
        self.assertEqual(result['initial_slug'], 'a-story')
        self.assertTrue(any(f"Using user-specified start chapter URL: {user_start_chapter}" in log['message'] for log in result['logs']))

    def test_resolve_url_warning_if_not_chapter_like(self):
        story_url = "http://example.com/fiction/123/test-slug" # Overview, but let's say metadata gives non-chapter URL
        
        with patch('core.cli_helpers.fetch_story_metadata_and_first_chapter') as mock_fetch:
            mock_fetch.return_value = {'first_chapter_url': 'http://example.com/not-a-chapter', 'story_slug': 'test-slug'}
            result = resolve_crawl_url_and_metadata_logic(story_url, None)
            self.assertEqual(result['actual_crawl_start_url'], 'http://example.com/not-a-chapter')
            self.assertTrue(any("Warning: Resolved crawl URL 'http://example.com/not-a-chapter' does not appear to be a valid chapter URL." in log['message'] for log in result['logs']))

        # Scenario: chapter URL is provided, but it's not chapter-like (less common)
        chapter_like_url = "http://example.com/some/path/that/is/not/a/chapter"
        result_chap = resolve_crawl_url_and_metadata_logic(chapter_like_url, None)
        self.assertEqual(result_chap['actual_crawl_start_url'], chapter_like_url)
        self.assertTrue(any(f"Warning: Resolved crawl URL '{chapter_like_url}' does not appear to be a valid chapter URL." in log['message'] for log in result_chap['logs']))

    # --- Tests for determine_story_slug_for_folders_logic ---

    def test_determine_slug_from_fetched_metadata(self):
        fetched_metadata = {'story_slug': 'meta-slug'}
        result = determine_story_slug_for_folders_logic("url", None, fetched_metadata, "init-slug", "title")
        self.assertEqual(result['story_slug'], 'meta-slug')
        self.assertTrue(any("Using slug from fetched metadata: 'meta-slug'" in log['message'] for log in result['logs']))

    def test_determine_slug_from_initial_resolve(self):
        result = determine_story_slug_for_folders_logic("url", None, None, "init-slug", "title")
        self.assertEqual(result['story_slug'], 'init-slug')
        self.assertTrue(any("Using initial slug from URL resolve step: 'init-slug'" in log['message'] for log in result['logs']))

    def test_determine_slug_infer_from_story_url_arg(self):
        story_url = "https://www.royalroad.com/fiction/12345/my-awesome-story/chapter/1/ch1"
        # _infer_slug_from_url should extract "my-awesome-story"
        result = determine_story_slug_for_folders_logic(story_url, None, None, None, "title")
        self.assertEqual(result['story_slug'], 'my-awesome-story')
        self.assertTrue(any("Inferred slug from story_url_arg" in log['message'] and "'my-awesome-story'" in log['message'] for log in result['logs']))

    def test_determine_slug_infer_from_start_chapter_url_param(self):
        start_url = "https://www.royalroad.com/fiction/54321/another-story-here/chapter/1/ch1"
        # _infer_slug_from_url should extract "another-story-here"
        result = determine_story_slug_for_folders_logic("main_url", start_url, None, None, "title")
        self.assertEqual(result['story_slug'], 'another-story-here')
        self.assertTrue(any("Inferred slug from start_chapter_url_param" in log['message'] and "'another-story-here'" in log['message'] for log in result['logs']))
    
    def test_determine_slug_generate_from_title_param(self):
        title = "My Story Title With Spaces & Chars!"
        # Expected: my_story_title_with_spaces_chars, limited to 50
        expected_slug = "my_story_title_with_spaces_chars" 
        result = determine_story_slug_for_folders_logic("url", None, None, None, title)
        self.assertEqual(result['story_slug'], expected_slug)
        self.assertTrue(any(f"Generated slug from title_param: '{expected_slug}'" in log['message'] for log in result['logs']))

    def test_determine_slug_fallback_to_timed_slug(self):
        with patch('time.time', return_value=1234567890): # Mock time
            result = determine_story_slug_for_folders_logic(None, None, None, None, None) # All sources fail
            expected_slug = "story_1234567890"
            self.assertEqual(result['story_slug'], expected_slug)
            self.assertTrue(any(f"Warning: Could not determine a descriptive slug. Using generic timed slug: '{expected_slug}'" in log['message'] for log in result['logs']))
        
        # Also test if title is default/generic
        with patch('time.time', return_value=1234567891):
            result_default_title = determine_story_slug_for_folders_logic(None, None, None, None, "Archived Royal Road Story")
            expected_slug_2 = "story_1234567891"
            self.assertEqual(result_default_title['story_slug'], expected_slug_2)
            self.assertTrue(any(f"Warning: Could not determine a descriptive slug. Using generic timed slug: '{expected_slug_2}'" in log['message'] for log in result_default_title['logs']))


    # --- Tests for finalize_epub_metadata_logic ---

    def test_finalize_all_params_override_fetched(self):
        params = {
            'title_param': "CLI Title", 'author_param': "CLI Author", 'cover_url_param': "cli_cover.jpg",
            'description_param': "CLI Description.", 'tags_param': "tag1,tag2", 'publisher_param': "CLI Publisher"
        }
        fetched_metadata = {
            'story_title': "Fetched Title", 'author_name': "Fetched Author", 'cover_image_url': "fetched_cover.jpg",
            'description': "Fetched Description.", 'tags': ['fetched_tag1'], 'publisher': "Fetched Publisher"
        }
        story_slug = "test-slug"
        
        result = finalize_epub_metadata_logic(**params, fetched_metadata=fetched_metadata, story_slug=story_slug)

        self.assertEqual(result['final_story_title'], params['title_param'])
        self.assertEqual(result['final_author_name'], params['author_param'])
        self.assertEqual(result['final_cover_image_url'], params['cover_url_param'])
        self.assertEqual(result['final_description'], params['description_param'])
        self.assertEqual(result['final_tags'], ['tag1', 'tag2'])
        self.assertEqual(result['final_publisher'], params['publisher_param'])
        self.assertTrue(len(result['logs']) == 1) # Should have one summary log
        self.assertTrue("EPUB Metadata: Title='CLI Title'" in result['logs'][0]['message'])

    def test_finalize_fetched_metadata_used(self):
        fetched_metadata = {
            'story_title': "Fetched Story Title", 'author_name': "Fetched Story Author", 
            'cover_image_url': "http://example.com/fetched_cover.png",
            'description': "This is the fetched description.", 'tags': ["Fantasy", "Adventure"],
            'publisher': "Fetched Publishing House"
        }
        story_slug = "another-slug"
        
        result = finalize_epub_metadata_logic(None, None, None, None, None, None, fetched_metadata, story_slug)

        self.assertEqual(result['final_story_title'], fetched_metadata['story_title'])
        self.assertEqual(result['final_author_name'], fetched_metadata['author_name'])
        self.assertEqual(result['final_cover_image_url'], fetched_metadata['cover_image_url'])
        self.assertEqual(result['final_description'], fetched_metadata['description'])
        self.assertEqual(result['final_tags'], fetched_metadata['tags'])
        self.assertEqual(result['final_publisher'], fetched_metadata['publisher'])
        self.assertTrue("EPUB Metadata: Title='Fetched Story Title'" in result['logs'][0]['message'])

    def test_finalize_defaults_and_slug_title_fallback(self):
        # Case 1: Everything is None, title from good slug
        result1 = finalize_epub_metadata_logic(None, None, None, None, None, None, None, "a-good-slug")
        self.assertEqual(result1['final_story_title'], "A Good Slug")
        self.assertEqual(result1['final_author_name'], "Royal Road Archiver") # Default
        self.assertIsNone(result1['final_cover_image_url'])
        self.assertEqual(result1['final_tags'], [])
        self.assertTrue("EPUB Metadata: Title='A Good Slug'" in result1['logs'][0]['message'])

        # Case 2: Slug is generic, title defaults
        result2 = finalize_epub_metadata_logic(None, None, None, None, None, None, None, "story_123")
        self.assertEqual(result2['final_story_title'], "Archived Royal Road Story") # Default
        self.assertTrue("EPUB Metadata: Title='Archived Royal Road Story'" in result2['logs'][0]['message'])
        
    def test_finalize_tags_parsing(self):
        result = finalize_epub_metadata_logic(None, None, None, None, "tag1, tag2 , tag3 ", None, None, "slug")
        self.assertEqual(result['final_tags'], ["tag1", "tag2", "tag3"])

        result_no_tags = finalize_epub_metadata_logic(None, None, None, None, None, None, None, "slug")
        self.assertEqual(result_no_tags['final_tags'], [])

        result_empty_tag_string = finalize_epub_metadata_logic(None, None, None, None, " , ", None, None, "slug")
        self.assertEqual(result_empty_tag_string['final_tags'], [])
