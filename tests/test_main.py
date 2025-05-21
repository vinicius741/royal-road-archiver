import unittest
from unittest.mock import patch, MagicMock
import os
import shutil # For cleaning up created directories
from typer.testing import CliRunner

# Adjust import path if main.py is in the parent directory or a specific app structure
# Assuming main.py is in the parent directory of 'tests'
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app # Your Typer app instance

# Expected base folders
DEFAULT_DOWNLOAD_BASE = "downloaded_stories"
DEFAULT_PROCESSED_BASE = "processed_stories"
DEFAULT_EPUB_BASE = "epubs"
MOCK_STORY_SLUG = "mock-story-slug" # This will be the name of the folder "created" by download_story mock

class TestFullProcessCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        # Ensure clean state for base folders before each test
        self.cleanup_folders()
        # Create base folders as the command expects them to exist or creates them
        os.makedirs(DEFAULT_DOWNLOAD_BASE, exist_ok=True)
        os.makedirs(DEFAULT_PROCESSED_BASE, exist_ok=True)
        os.makedirs(DEFAULT_EPUB_BASE, exist_ok=True)


    def tearDown(self):
        self.cleanup_folders()

    def cleanup_folders(self):
        # Clean up any folders created during the test
        if os.path.exists(DEFAULT_DOWNLOAD_BASE):
            shutil.rmtree(DEFAULT_DOWNLOAD_BASE)
        if os.path.exists(DEFAULT_PROCESSED_BASE):
            shutil.rmtree(DEFAULT_PROCESSED_BASE)
        if os.path.exists(DEFAULT_EPUB_BASE):
            shutil.rmtree(DEFAULT_EPUB_BASE)

    @patch('main.build_epubs_for_story')
    @patch('main.process_story_chapters')
    @patch('main.download_story')
    def test_full_process_invokes_core_functions_with_correct_paths(
        self,
        mock_download_story: MagicMock,
        mock_process_story_chapters: MagicMock,
        mock_build_epubs_for_story: MagicMock
    ):
        # --- Mock Configuration ---
        abs_download_base = os.path.abspath(DEFAULT_DOWNLOAD_BASE)
        abs_processed_base = os.path.abspath(DEFAULT_PROCESSED_BASE)
        abs_epub_base = os.path.abspath(DEFAULT_EPUB_BASE)

        # This is the folder that download_story is expected to create
        expected_story_download_folder = os.path.join(abs_download_base, MOCK_STORY_SLUG)
        # This is the folder that process_story_chapters is expected to create
        expected_story_processed_folder = os.path.join(abs_processed_base, MOCK_STORY_SLUG)

        def download_side_effect(url, output_folder):
            # Simulate download_story creating the story-specific subfolder
            self.assertEqual(output_folder, abs_download_base) # Check it's called with the base
            os.makedirs(expected_story_download_folder, exist_ok=True)
            print(f"Mock download: Created {expected_story_download_folder}")
            # download_story in the actual code doesn't return anything,
            # the main command infers the folder by listing directories.

        def process_side_effect(input_story_folder, output_base_folder):
            # Simulate process_story_chapters creating its output folder
            self.assertEqual(input_story_folder, expected_story_download_folder)
            self.assertEqual(output_base_folder, abs_processed_base)
            os.makedirs(expected_story_processed_folder, exist_ok=True)
            print(f"Mock process: Created {expected_story_processed_folder}")
            # process_story_chapters also doesn't return anything.

        mock_download_story.side_effect = download_side_effect
        mock_process_story_chapters.side_effect = process_side_effect
        # mock_build_epubs_for_story doesn't need a side effect for folder creation in this test,
        # as the command only checks its inputs.

        # --- Invoke Command ---
        test_url = "http://example.com/fiction/123/mock-story-slug/chapter/1" # Use MOCK_STORY_SLUG in URL for consistency if it matters
        result = self.runner.invoke(app, [
            "full-process",
            test_url,
            "--author", "Test Author",
            "--title", "Test Story Title"
        ], catch_exceptions=False) # Set catch_exceptions=False to see full traceback

        print(f"CLI Output:\n{result.stdout}")
        self.assertEqual(result.exit_code, 0, f"CLI command failed with output: {result.stdout}")

        # --- Assertions ---
        # 1. download_story called correctly
        mock_download_story.assert_called_once()
        args, kwargs = mock_download_story.call_args
        self.assertEqual(args[0], test_url)
        self.assertEqual(args[1], abs_download_base)

        # 2. process_story_chapters called correctly
        mock_process_story_chapters.assert_called_once()
        args, kwargs = mock_process_story_chapters.call_args
        self.assertEqual(args[0], expected_story_download_folder) # Input is the folder created by download_story
        self.assertEqual(args[1], abs_processed_base)

        # 3. build_epubs_for_story called correctly
        mock_build_epubs_for_story.assert_called_once()
        args, kwargs = mock_build_epubs_for_story.call_args
        self.assertEqual(kwargs['input_folder'], expected_story_processed_folder) # Input is folder from process_story_chapters
        self.assertEqual(kwargs['output_folder'], abs_epub_base)
        self.assertEqual(kwargs['chapters_per_epub'], 50) # Default
        self.assertEqual(kwargs['author_name'], "Test Author")
        self.assertEqual(kwargs['story_title'], "Test Story Title")


    @patch('main.build_epubs_for_story')
    @patch('main.process_story_chapters')
    @patch('main.download_story')
    def test_full_process_default_title_author(
        self,
        mock_download_story: MagicMock,
        mock_process_story_chapters: MagicMock,
        mock_build_epubs_for_story: MagicMock
    ):
        # Simplified setup, focusing on default title/author
        abs_download_base = os.path.abspath(DEFAULT_DOWNLOAD_BASE)
        abs_processed_base = os.path.abspath(DEFAULT_PROCESSED_BASE)
        expected_story_download_folder = os.path.join(abs_download_base, MOCK_STORY_SLUG)
        expected_story_processed_folder = os.path.join(abs_processed_base, MOCK_STORY_SLUG)

        def download_side_effect(url, output_folder):
            os.makedirs(expected_story_download_folder, exist_ok=True)
        def process_side_effect(input_story_folder, output_base_folder):
            os.makedirs(expected_story_processed_folder, exist_ok=True)

        mock_download_story.side_effect = download_side_effect
        mock_process_story_chapters.side_effect = process_side_effect
        
        # Use a URL that allows slug inference for title
        test_url = f"http://example.com/fiction/12345/{MOCK_STORY_SLUG}/chapter/1"
        result = self.runner.invoke(app, [
            "full-process",
            test_url
        ], catch_exceptions=False)

        self.assertEqual(result.exit_code, 0, f"CLI command failed with output: {result.stdout}")

        mock_build_epubs_for_story.assert_called_once()
        kwargs = mock_build_epubs_for_story.call_args.kwargs
        self.assertEqual(kwargs['author_name'], "Royal Road Archiver") # Default author
        # Title should be inferred from slug: "Mock Story Slug"
        self.assertEqual(kwargs['story_title'], "Mock Story Slug") 


if __name__ == '__main__':
    unittest.main()
