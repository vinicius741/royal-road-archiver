# tests/test_main.py
import unittest
from unittest.mock import patch, MagicMock, call
import os
import shutil
from typer.testing import CliRunner

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app 

DEFAULT_DOWNLOAD_BASE = "downloaded_stories"
DEFAULT_PROCESSED_BASE = "processed_stories"
DEFAULT_EPUB_BASE = "epubs"
MOCK_STORY_SLUG_FROM_URL = "mock-story-slug-from-url"
MOCK_STORY_SLUG_FROM_METADATA = "mock-story-slug-from-metadata"

# Dummy metadata for fetch_story_metadata_and_first_chapter mock
DUMMY_METADATA = {
    'first_chapter_url': f"https://www.royalroad.com/fiction/123/{MOCK_STORY_SLUG_FROM_METADATA}/chapter/1000/meta-first-chapter",
    'story_title': "Metadata Story Title",
    'author_name': "Metadata Author",
    'story_slug': MOCK_STORY_SLUG_FROM_METADATA
}
DUMMY_METADATA_NO_SLUG = {
    'first_chapter_url': f"https://www.royalroad.com/fiction/123/another-story/chapter/1000/meta-first-chapter",
    'story_title': "Metadata Story Title No Slug",
    'author_name': "Metadata Author No Slug",
    'story_slug': None # Simulate no slug from metadata
}


class TestFullProcessCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.cleanup_folders() # Clean before
        # Create base folders as the command expects them to exist or creates them
        os.makedirs(DEFAULT_DOWNLOAD_BASE, exist_ok=True)
        os.makedirs(DEFAULT_PROCESSED_BASE, exist_ok=True)
        os.makedirs(DEFAULT_EPUB_BASE, exist_ok=True)

    def tearDown(self):
        self.cleanup_folders() # Clean after

    def cleanup_folders(self):
        if os.path.exists(DEFAULT_DOWNLOAD_BASE):
            shutil.rmtree(DEFAULT_DOWNLOAD_BASE)
        if os.path.exists(DEFAULT_PROCESSED_BASE):
            shutil.rmtree(DEFAULT_PROCESSED_BASE)
        if os.path.exists(DEFAULT_EPUB_BASE):
            shutil.rmtree(DEFAULT_EPUB_BASE)

    @patch('main.fetch_story_metadata_and_first_chapter')
    @patch('main.download_story')
    @patch('main.process_story_chapters')
    @patch('main.build_epubs_for_story')
    def test_full_process_overview_url_with_start_chapter_override(
        self, mock_build_epub, mock_process, mock_download, mock_fetch_metadata
    ):
        mock_fetch_metadata.return_value = DUMMY_METADATA
        
        # This is the folder that download_story should create/use
        expected_story_download_folder = os.path.join(os.path.abspath(DEFAULT_DOWNLOAD_BASE), DUMMY_METADATA['story_slug'])
        mock_download.return_value = expected_story_download_folder # Simulate download_story returning the path

        # process_story_chapters does not return a value in the new structure, its success is implied by not raising error
        # and the existence of its output folder, which the command then uses.
        # build_epubs_for_story also does not return a value.

        overview_url = f"https://www.royalroad.com/fiction/123/{DUMMY_METADATA['story_slug']}"
        start_chapter_url_override = f"https://www.royalroad.com/fiction/123/{DUMMY_METADATA['story_slug']}/chapter/7777/my-starting-chapter"

        result = self.runner.invoke(app, [
            "full-process",
            overview_url,
            "--start-chapter-url", start_chapter_url_override,
            "--author", "Test Author",
            "--title", "Test Title"
        ], catch_exceptions=False)

        print(f"CLI Output (test_full_process_overview_url_with_start_chapter_override):\n{result.stdout}")
        self.assertEqual(result.exit_code, 0)

        mock_fetch_metadata.assert_called_once_with(overview_url)
        
        # download_story should be called with the overridden start_chapter_url and the slug from metadata
        mock_download.assert_called_once_with(
            start_chapter_url_override, 
            os.path.abspath(DEFAULT_DOWNLOAD_BASE), 
            story_slug_override=DUMMY_METADATA['story_slug']
        )

        # process_story_chapters should use the folder path derived from download_story's output
        expected_processed_input_folder = expected_story_download_folder
        expected_processed_output_folder = os.path.join(os.path.abspath(DEFAULT_PROCESSED_BASE), DUMMY_METADATA['story_slug'])
        mock_process.assert_called_once_with(expected_processed_input_folder, expected_processed_output_folder)
        
        # build_epubs_for_story should use the output from process
        mock_build_epub.assert_called_once_with(
            input_folder=expected_processed_output_folder,
            output_folder=os.path.abspath(DEFAULT_EPUB_BASE),
            chapters_per_epub=50, # default
            author_name="Test Author",
            story_title="Test Title"
        )

    @patch('main.fetch_story_metadata_and_first_chapter')
    @patch('main.download_story')
    @patch('main.process_story_chapters')
    @patch('main.build_epubs_for_story')
    def test_full_process_chapter_url_no_override(
        self, mock_build_epub, mock_process, mock_download, mock_fetch_metadata
    ):
        # fetch_story_metadata_and_first_chapter should NOT be called if story_url is a chapter URL
        chapter_url = f"https://www.royalroad.com/fiction/456/{MOCK_STORY_SLUG_FROM_URL}/chapter/1/the-start"
        
        expected_story_download_folder = os.path.join(os.path.abspath(DEFAULT_DOWNLOAD_BASE), MOCK_STORY_SLUG_FROM_URL)
        mock_download.return_value = expected_story_download_folder
        
        result = self.runner.invoke(app, [
            "full-process",
            chapter_url,
            # No --start-chapter-url, so chapter_url itself should be used for crawl start
        ], catch_exceptions=False)

        print(f"CLI Output (test_full_process_chapter_url_no_override):\n{result.stdout}")
        self.assertEqual(result.exit_code, 0)

        mock_fetch_metadata.assert_not_called() # IMPORTANT: Not called for chapter URLs
        
        # download_story called with chapter_url as start, and inferred slug
        mock_download.assert_called_once_with(
            chapter_url, 
            os.path.abspath(DEFAULT_DOWNLOAD_BASE), 
            story_slug_override=MOCK_STORY_SLUG_FROM_URL
        )

        expected_processed_input_folder = expected_story_download_folder
        expected_processed_output_folder = os.path.join(os.path.abspath(DEFAULT_PROCESSED_BASE), MOCK_STORY_SLUG_FROM_URL)
        mock_process.assert_called_once_with(expected_processed_input_folder, expected_processed_output_folder)
        
        # Title should be inferred from slug MOCK_STORY_SLUG_FROM_URL -> "Mock Story Slug From Url"
        mock_build_epub.assert_called_once_with(
            input_folder=expected_processed_output_folder,
            output_folder=os.path.abspath(DEFAULT_EPUB_BASE),
            chapters_per_epub=50, 
            author_name="Royal Road Archiver", # Default
            story_title="Mock Story Slug From Url" 
        )

    @patch('main.fetch_story_metadata_and_first_chapter')
    @patch('main.download_story')
    @patch('main.process_story_chapters')
    @patch('main.build_epubs_for_story')
    def test_full_process_overview_url_default_start(
        self, mock_build_epub, mock_process, mock_download, mock_fetch_metadata
    ):
        mock_fetch_metadata.return_value = DUMMY_METADATA
        expected_story_download_folder = os.path.join(os.path.abspath(DEFAULT_DOWNLOAD_BASE), DUMMY_METADATA['story_slug'])
        mock_download.return_value = expected_story_download_folder

        overview_url = f"https://www.royalroad.com/fiction/123/{DUMMY_METADATA['story_slug']}"

        result = self.runner.invoke(app, [
            "full-process",
            overview_url,
            # No --start-chapter-url, so metadata's first_chapter_url should be used
        ], catch_exceptions=False)
        
        print(f"CLI Output (test_full_process_overview_url_default_start):\n{result.stdout}")
        self.assertEqual(result.exit_code, 0)

        mock_fetch_metadata.assert_called_once_with(overview_url)
        
        mock_download.assert_called_once_with(
            DUMMY_METADATA['first_chapter_url'], # From metadata
            os.path.abspath(DEFAULT_DOWNLOAD_BASE), 
            story_slug_override=DUMMY_METADATA['story_slug']
        )
        
        expected_processed_input_folder = expected_story_download_folder
        expected_processed_output_folder = os.path.join(os.path.abspath(DEFAULT_PROCESSED_BASE), DUMMY_METADATA['story_slug'])
        mock_process.assert_called_once_with(expected_processed_input_folder, expected_processed_output_folder)

        mock_build_epub.assert_called_once_with(
            input_folder=expected_processed_output_folder,
            output_folder=os.path.abspath(DEFAULT_EPUB_BASE),
            chapters_per_epub=50,
            author_name=DUMMY_METADATA['author_name'], # From metadata
            story_title=DUMMY_METADATA['story_title']  # From metadata
        )
    
    @patch('main.fetch_story_metadata_and_first_chapter')
    @patch('main.download_story')
    @patch('main.process_story_chapters')
    @patch('main.build_epubs_for_story')
    def test_crawl_command_with_start_chapter_url(
        self, mock_build_epub, mock_process, mock_download, mock_fetch_metadata # Mocks not used by crawl, but patch all to be safe
    ):
        mock_fetch_metadata.return_value = DUMMY_METADATA
        overview_url = f"https://www.royalroad.com/fiction/123/{DUMMY_METADATA['story_slug']}"
        start_url_override = "https://www.royalroad.com/fiction/123/some-story/chapter/999/specific-start"

        result = self.runner.invoke(app, [
            "crawl",
            overview_url,
            "--start-chapter-url", start_url_override,
            "-o", "test_crawl_output"
        ], catch_exceptions=False)
        
        print(f"CLI Output (test_crawl_command_with_start_chapter_url):\n{result.stdout}")
        self.assertEqual(result.exit_code, 0)
        mock_fetch_metadata.assert_called_once_with(overview_url)
        mock_download.assert_called_once_with(
            start_url_override, # Should use the override
            os.path.abspath("test_crawl_output"),
            story_slug_override=DUMMY_METADATA['story_slug'] # Slug from metadata
        )
        # Clean up test_crawl_output
        if os.path.exists("test_crawl_output"):
            shutil.rmtree("test_crawl_output")

    @patch('main.fetch_story_metadata_and_first_chapter')
    @patch('main.download_story')
    def test_crawl_command_chapter_url_as_main_arg(
        self, mock_download, mock_fetch_metadata
    ):
        chapter_as_main_url = f"https://www.royalroad.com/fiction/789/{MOCK_STORY_SLUG_FROM_URL}/chapter/1/actual-chapter"
        
        result = self.runner.invoke(app, [
            "crawl",
            chapter_as_main_url,
            "-o", "test_crawl_output_chap"
        ], catch_exceptions=False)

        print(f"CLI Output (test_crawl_command_chapter_url_as_main_arg):\n{result.stdout}")
        self.assertEqual(result.exit_code, 0)
        mock_fetch_metadata.assert_not_called() # Not called for chapter URLs
        mock_download.assert_called_once_with(
            chapter_as_main_url, # Main URL itself is the start
            os.path.abspath("test_crawl_output_chap"),
            story_slug_override=MOCK_STORY_SLUG_FROM_URL # Slug inferred from chapter_as_main_url
        )
        if os.path.exists("test_crawl_output_chap"):
            shutil.rmtree("test_crawl_output_chap")


if __name__ == '__main__':
    unittest.main()