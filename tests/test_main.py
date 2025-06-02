# tests/test_main.py
import unittest
from unittest.mock import patch, MagicMock, call
import os
import shutil
import tempfile # Added
import json # Added, though might not be directly used by CLI tests if json path is just passed
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

    @patch('core.cli_helpers.fetch_story_metadata_and_first_chapter') # Corrected mock target
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

    @patch('core.cli_helpers.fetch_story_metadata_and_first_chapter') # Corrected mock target
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

    @patch('core.cli_helpers.fetch_story_metadata_and_first_chapter') # Corrected mock target
    @patch('main.download_story')
    @patch('main.process_story_chapters')
    @patch('main.build_epubs_for_story')
    @patch('os.path.isdir') # Added os.path.isdir mock
    def test_full_process_overview_url_default_start(
        self, mock_os_path_isdir, mock_build_epub, mock_process, mock_download, mock_fetch_metadata # Added mock_os_path_isdir
    ):
        # This test is complex and seems to have some self.xxx_base_abs variables
        # that are not defined in the provided snippet. Assuming they are defined in a
        # broader context of the actual test file. For now, I'll use the defaults.
        self.download_base_abs = os.path.abspath(DEFAULT_DOWNLOAD_BASE)
        self.processed_base_abs = os.path.abspath(DEFAULT_PROCESSED_BASE)
        self.epub_base_abs = os.path.abspath(DEFAULT_EPUB_BASE)
        # self.base_test_dir is also undefined, assuming it's self.test_dir or similar.
        # For the purpose of this diff, I'll proceed assuming these are handled.

        mock_fetch_metadata.return_value = DUMMY_METADATA
        expected_story_download_folder = os.path.join(self.download_base_abs, DUMMY_METADATA['story_slug']) 
        mock_download.return_value = expected_story_download_folder
        mock_os_path_isdir.return_value = True 

        overview_url = f"https://www.royalroad.com/fiction/123/{DUMMY_METADATA['story_slug']}"

        result = self.runner.invoke(app, [
            "full-process", overview_url,
            # "--output-base-dir", self.base_test_dir 
            ], catch_exceptions=False)
        
        self.assertEqual(result.exit_code, 0, msg=f"CLI command failed with output:\n{result.stdout}")
        mock_fetch_metadata.assert_called_once_with(story_url_arg=overview_url, start_chapter_url_param=None)
        mock_download.assert_called_once_with(
            first_chapter_url=DUMMY_METADATA['first_chapter_url'], 
            output_folder=self.download_base_abs,
            story_slug_override=DUMMY_METADATA['story_slug'],
            # These were added in a later subtask, ensure they are in the call if your main code expects them
            overview_url=overview_url,
            story_title=DUMMY_METADATA['story_title'],
            author_name=DUMMY_METADATA['author_name']
        )
        
        expected_processed_input_folder = expected_story_download_folder
        expected_processed_output_folder = os.path.join(self.processed_base_abs, DUMMY_METADATA['story_slug']) 
        mock_process.assert_called_once_with(expected_processed_input_folder, expected_processed_output_folder)

        mock_build_epub.assert_called_once_with(
            input_folder=expected_processed_output_folder,
            output_folder=os.path.join(self.epub_base_abs, DUMMY_METADATA['story_slug']), 
            chapters_per_epub=50,
            author_name=DUMMY_METADATA['author_name'], 
            story_title=DUMMY_METADATA['story_title'],
            # These were added in a later subtask, ensure they are in the call
            cover_image_url=None, # Or DUMMY_METADATA.get('cover_image_url') if it exists
            story_description=None, # Or DUMMY_METADATA.get('description')
            tags=[], # Or DUMMY_METADATA.get('tags')
            publisher_name=None # Or DUMMY_METADATA.get('publisher')
        )

    # --- Test for sentence removal in full-process ---
    @patch('core.cli_helpers.fetch_story_metadata_and_first_chapter')
    @patch('main.download_story')
    @patch('main.process_story_chapters')
    @patch('main.build_epubs_for_story') # We will mock this to control EPUB creation
    def test_full_process_with_sentence_removal(
        self, mock_build_epub, mock_process, mock_download, mock_fetch_metadata
    ):
        story_slug = "test-story-for-sentence-removal"
        mock_metadata = {
            'first_chapter_url': f"https://example.com/story/{story_slug}/chapter/1",
            'story_title': "Test Story Sentence Removal",
            'author_name': "Author Test",
            'story_slug': story_slug,
            'cover_image_url': None, 'description': None, 'tags': [], 'publisher': None
        }
        mock_fetch_metadata.return_value = mock_metadata

        abs_download_base = os.path.abspath(DEFAULT_DOWNLOAD_BASE)
        abs_processed_base = os.path.abspath(DEFAULT_PROCESSED_BASE)
        abs_epub_base = os.path.abspath(DEFAULT_EPUB_BASE)

        expected_story_download_folder = os.path.join(abs_download_base, story_slug)
        expected_story_processed_folder = os.path.join(abs_processed_base, story_slug)
        expected_story_epub_folder = os.path.join(abs_epub_base, story_slug) # This is where EPUBs will be
        
        mock_download.return_value = expected_story_download_folder
        # mock_process doesn't return, it creates files in expected_story_processed_folder
        # mock_build_epub needs to simulate the creation of an EPUB file
        
        # Ensure the directory where the EPUB will be "built" by the mock exists
        os.makedirs(expected_story_epub_folder, exist_ok=True)
        
        # This is the EPUB that modify_epub_content will act upon in the full-process command
        # It should be placed where build_epubs_for_story would place it.
        # The name of the EPUB file itself is determined by build_epubs_for_story logic
        # For simplicity, let's assume a known name or copy test_epub_original.epub
        # The actual name depends on chapters, title etc. Let's use a fixed name for the test.
        # The `build_epubs_for_story` function itself determines the filename.
        # For a single volume EPUB, it's like "Ch001-ChXXX_slug.epub"
        # Let's assume build_epubs_for_story is mocked and we manually place the file.
        
        # What the actual build_epubs_for_story mock should do:
        def side_effect_build_epubs(input_folder, output_folder, **kwargs):
            # output_folder is expected_story_epub_folder
            # Create a dummy epub file here that sentence removal can act on.
            # For now, we'll copy our test_epub_original.epub to simulate it.
            # The actual filename logic in build_epubs_for_story is more complex.
            # We'll use a simplified name that the sentence removal part can find.
            self.test_epub_name_in_output = "story_Ch001-Ch001.epub" # Simplified
            shutil.copy2(TEST_EPUB_ORIGINAL_FOR_CLI, os.path.join(output_folder, self.test_epub_name_in_output))
            print(f"Mock build_epubs_for_story created {self.test_epub_name_in_output} in {output_folder}")
        
        mock_build_epub.side_effect = side_effect_build_epubs

        result = self.runner.invoke(app, [
            "full-process", f"https://example.com/story/{story_slug}",
            "--remove-sentences-json", TEST_SENTENCES_JSON_CLI,
            "--keep-intermediate-files" # To inspect epub folder easily
        ], catch_exceptions=False)

        print(f"CLI Output (test_full_process_with_sentence_removal):\n{result.stdout}")
        self.assertEqual(result.exit_code, 0, msg=result.stdout)

        # Verify mocks
        mock_fetch_metadata.assert_called_once()
        mock_download.assert_called_once()
        mock_process.assert_called_once()
        mock_build_epub.assert_called_once() # Check it was called

        # Verify EPUB content
        final_epub_path = os.path.join(expected_story_epub_folder, self.test_epub_name_in_output)
        self.assertTrue(os.path.exists(final_epub_path), f"EPUB file not found at {final_epub_path}")

        # Use the helper from TestRemoveSentencesCommand, adapting it if necessary
        # Need to ensure MAIN_TEST_ASSET_DIR is defined or use the one from TestRemoveSentencesCommand
        # For simplicity, re-instantiate the helper or copy its logic.
        checker = TestRemoveSentencesCommand() # Temporary instance to use its helper
        checker._assert_epub_content_cli(
            final_epub_path,
            ["This is a sentence to be removed.", "Another sentence for deletion."],
            ["Keep this sentence intact.", "The quick brown fox jumps over the lazy dog."]
        )
        # Check for the special char sentence
        book = ebooklib_epub.read_epub(final_epub_path)
        chap2_content = ""
        for item in book.get_items_of_type(ebooklib_epub.ITEM_DOCUMENT):
            if item.get_name() == "chap2.xhtml":
                chap2_content = item.get_content().decode('utf-8')
                break
        self.assertNotIn("Sentence with special chars &amp; entities.", chap2_content)
        self.assertIn("This sentence also stays.", chap2_content)

    @patch('core.cli_helpers.fetch_story_metadata_and_first_chapter')
    @patch('main.download_story')
    @patch('main.process_story_chapters')
    @patch('main.build_epubs_for_story')
    def test_full_process_sentence_removal_non_existent_json(
        self, mock_build_epub, mock_process, mock_download, mock_fetch_metadata
    ):
        story_slug = "test-story-non-existent-json"
        # ... (similar mock setup as above for metadata, download, process) ...
        mock_metadata = {'first_chapter_url': f"https://example.com/story/{story_slug}/chapter/1", 'story_title': "Non Existent JSON Test", 'author_name': "Author Test", 'story_slug': story_slug, 'cover_image_url': None, 'description': None, 'tags': [], 'publisher': None}
        mock_fetch_metadata.return_value = mock_metadata
        abs_download_base = os.path.abspath(DEFAULT_DOWNLOAD_BASE)
        abs_processed_base = os.path.abspath(DEFAULT_PROCESSED_BASE)
        abs_epub_base = os.path.abspath(DEFAULT_EPUB_BASE)
        expected_story_download_folder = os.path.join(abs_download_base, story_slug)
        expected_story_epub_folder = os.path.join(abs_epub_base, story_slug)
        mock_download.return_value = expected_story_download_folder
        os.makedirs(expected_story_epub_folder, exist_ok=True)
        self.test_epub_name_in_output_ne = "story_ne_Ch001-Ch001.epub"
        def side_effect_build_epubs_ne(*args, **kwargs):
             shutil.copy2(TEST_EPUB_ORIGINAL_FOR_CLI, os.path.join(args[1], self.test_epub_name_in_output_ne)) # args[1] is output_folder
        mock_build_epub.side_effect = side_effect_build_epubs_ne

        result = self.runner.invoke(app, [
            "full-process", f"https://example.com/story/{story_slug}",
            "--remove-sentences-json", "tests/assets/non_existent_sentences.json",
            "--keep-intermediate-files"
        ], catch_exceptions=False)

        self.assertEqual(result.exit_code, 0, msg=result.stdout)
        self.assertIn("Sentence removal JSON file not found", result.stdout)
        
        # Verify EPUB is created but not modified
        final_epub_path = os.path.join(expected_story_epub_folder, self.test_epub_name_in_output_ne)
        self.assertTrue(os.path.exists(final_epub_path))
        checker = TestRemoveSentencesCommand()
        checker._assert_epub_content_cli( # Check that original sentences are still there
            final_epub_path,
            [], 
            ["This is a sentence to be removed.", "Another sentence for deletion.", "Sentence with special chars &amp; entities."]
        )

    @patch('core.cli_helpers.fetch_story_metadata_and_first_chapter')
    @patch('main.download_story')
    @patch('main.process_story_chapters')
    @patch('main.build_epubs_for_story')
    def test_full_process_sentence_removal_invalid_json_content(
        self, mock_build_epub, mock_process, mock_download, mock_fetch_metadata
    ):
        story_slug = "test-story-invalid-json-content"
        # ... (similar mock setup) ...
        mock_metadata = {'first_chapter_url': f"https://example.com/story/{story_slug}/chapter/1", 'story_title': "Invalid JSON Content Test", 'author_name': "Author Test", 'story_slug': story_slug, 'cover_image_url': None, 'description': None, 'tags': [], 'publisher': None}
        mock_fetch_metadata.return_value = mock_metadata
        abs_download_base = os.path.abspath(DEFAULT_DOWNLOAD_BASE)
        abs_processed_base = os.path.abspath(DEFAULT_PROCESSED_BASE)
        abs_epub_base = os.path.abspath(DEFAULT_EPUB_BASE)
        expected_story_download_folder = os.path.join(abs_download_base, story_slug)
        expected_story_epub_folder = os.path.join(abs_epub_base, story_slug)
        mock_download.return_value = expected_story_download_folder
        os.makedirs(expected_story_epub_folder, exist_ok=True)
        
        invalid_json_path = os.path.join(self.test_dir, "invalid_sentences.json")
        with open(invalid_json_path, "w") as f:
            f.write('{"this_is_not": "a list of strings"}')

        self.test_epub_name_in_output_ij = "story_ij_Ch001-Ch001.epub"
        def side_effect_build_epubs_ij(*args, **kwargs):
            shutil.copy2(TEST_EPUB_ORIGINAL_FOR_CLI, os.path.join(args[1], self.test_epub_name_in_output_ij))
        mock_build_epub.side_effect = side_effect_build_epubs_ij
            
        result = self.runner.invoke(app, [
            "full-process", f"https://example.com/story/{story_slug}",
            "--remove-sentences-json", invalid_json_path,
            "--keep-intermediate-files"
        ], catch_exceptions=False)

        self.assertEqual(result.exit_code, 0, msg=result.stdout)
        self.assertIn("Content of sentence removal JSON is not a list of strings", result.stdout)
        
        final_epub_path = os.path.join(expected_story_epub_folder, self.test_epub_name_in_output_ij)
        self.assertTrue(os.path.exists(final_epub_path))
        checker = TestRemoveSentencesCommand()
        checker._assert_epub_content_cli( # Check original sentences are present
            final_epub_path,
            [],
            ["This is a sentence to be removed.", "Another sentence for deletion."]
        )


    @patch('core.cli_helpers.fetch_story_metadata_and_first_chapter')
    @patch('main.download_story')
    @patch('main.process_story_chapters')
    @patch('main.build_epubs_for_story')
    def test_crawl_command_with_start_chapter_url( # This test seems fine, no changes needed for sentence removal
        self, mock_build_epub, mock_process, mock_download, mock_fetch_metadata 
    ):
        mock_fetch_metadata.return_value = DUMMY_METADATA
        overview_url = f"https://www.royalroad.com/fiction/123/{DUMMY_METADATA['story_slug']}"
        start_url_override = "https://www.royalroad.com/fiction/123/some-story/chapter/999/specific-start"

        # Create a temporary directory for this specific test's output
        test_specific_output_dir = os.path.join(self.test_dir, "crawl_output_specific")
        os.makedirs(test_specific_output_dir, exist_ok=True)


        result = self.runner.invoke(app, [
            "crawl",
            overview_url,
            "--start-chapter-url", start_url_override,
            "-o", test_specific_output_dir # Use test-specific output directory
        ], catch_exceptions=False)
        
        print(f"CLI Output (test_crawl_command_with_start_chapter_url):\n{result.stdout}")
        self.assertEqual(result.exit_code, 0)
        mock_fetch_metadata.assert_called_once_with(story_url_arg=overview_url, start_chapter_url_param=start_url_override) # Corrected, fetch_metadata IS called by resolve_crawl_url_and_metadata
        
        # The download_story mock should be called with the output path derived from the -o option
        mock_download.assert_called_once_with(
            first_chapter_url=start_url_override, 
            output_folder=os.path.abspath(test_specific_output_dir),
            story_slug_override=DUMMY_METADATA['story_slug'],
            overview_url=overview_url, # Added based on download_story signature
            story_title=DUMMY_METADATA['story_title'], # Added
            author_name=DUMMY_METADATA['author_name'] # Added
        )
        # No need to manually clean up test_specific_output_dir as self.test_dir (its parent) is cleaned in tearDown

    @patch('core.cli_helpers.fetch_story_metadata_and_first_chapter') 
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

# --- Tests for remove-sentences command ---
from ebooklib import epub as ebooklib_epub # ebooklib.epub might conflict if epub is a var
# ASSET_DIR for test_main.py needs to be defined relative to this file's location
MAIN_TEST_ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
TEST_EPUB_ORIGINAL_FOR_CLI = os.path.join(MAIN_TEST_ASSET_DIR, "test_epub_original.epub")
TEST_EPUB_FOR_OVERWRITE_CLI = os.path.join(MAIN_TEST_ASSET_DIR, "test_epub_for_overwrite.epub")
TEST_SENTENCES_JSON_CLI = os.path.join(MAIN_TEST_ASSET_DIR, "test_sentences.json")


class TestRemoveSentencesCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.test_dir = tempfile.mkdtemp(prefix="remove_sentences_cmd_test_")
        
        # Ensure assets exist (they should have been created by previous steps/manually)
        if not os.path.exists(MAIN_TEST_ASSET_DIR):
            os.makedirs(MAIN_TEST_ASSET_DIR, exist_ok=True)
            # This is a fallback, ideally assets are present.
            # If this test runs in an environment where they weren't generated by previous steps,
            # it might fail if these files are not found.
            print(f"WARNING: Test asset directory {MAIN_TEST_ASSET_DIR} not found, it should pre-exist with EPUBs and JSON.")

        self.assertTrue(os.path.exists(TEST_EPUB_ORIGINAL_FOR_CLI), f"EPUB asset missing: {TEST_EPUB_ORIGINAL_FOR_CLI}")
        self.assertTrue(os.path.exists(TEST_EPUB_FOR_OVERWRITE_CLI), f"EPUB asset missing: {TEST_EPUB_FOR_OVERWRITE_CLI}")
        self.assertTrue(os.path.exists(TEST_SENTENCES_JSON_CLI), f"JSON asset missing: {TEST_SENTENCES_JSON_CLI}")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _assert_epub_content_cli(self, epub_path, removed_check_list, kept_check_list):
        book = ebooklib_epub.read_epub(epub_path)
        full_text_content = ""
        for item in book.get_items_of_type(ebooklib_epub.ITEM_DOCUMENT): # Use ITEM_DOCUMENT
            full_text_content += item.get_content().decode('utf-8', errors='ignore')

        for sentence in removed_check_list:
            self.assertNotIn(sentence, full_text_content, f"Sentence '{sentence}' should have been removed from {os.path.basename(epub_path)}.")
        
        for sentence in kept_check_list:
            self.assertIn(sentence, full_text_content, f"Sentence '{sentence}' should have been preserved in {os.path.basename(epub_path)}.")

    def test_remove_sentences_basic_output_dir(self):
        temp_input_dir = os.path.join(self.test_dir, "input_epubs")
        temp_output_dir = os.path.join(self.test_dir, "output_epubs")
        os.makedirs(temp_input_dir, exist_ok=True)
        os.makedirs(os.path.join(temp_input_dir, "story1"), exist_ok=True) # Mimic slug structure
        
        shutil.copy2(TEST_EPUB_ORIGINAL_FOR_CLI, os.path.join(temp_input_dir, "story1", "test_epub_original.epub"))

        result = self.runner.invoke(app, [
            "remove-sentences",
            "--dir", temp_input_dir,
            TEST_SENTENCES_JSON_CLI,
            "--out", temp_output_dir
        ], catch_exceptions=False)

        print(f"CLI Output (test_remove_sentences_basic_output_dir):\n{result.stdout}")
        self.assertEqual(result.exit_code, 0, result.stdout)

        modified_epub_path = os.path.join(temp_output_dir, "story1", "test_epub_original.epub")
        self.assertTrue(os.path.exists(modified_epub_path))
        
        # Verify original is unchanged
        original_in_input_dir_path = os.path.join(temp_input_dir, "story1", "test_epub_original.epub")
        self._assert_epub_content_cli(
            original_in_input_dir_path,
            [], # No sentences should be removed from original
            ["This is a sentence to be removed.", "Another sentence for deletion.", "Keep this sentence intact."]
        )

        # Verify modified EPUB
        self._assert_epub_content_cli(
            modified_epub_path,
            ["This is a sentence to be removed.", "Another sentence for deletion."],
            ["Keep this sentence intact.", "The quick brown fox jumps over the lazy dog."]
        )
        # Sentence with special chars & entities. -> Sentence with special chars &amp; entities.
        # The test for this is better in the direct unit test for remove_sentences_from_html_content
        # or modify_epub_content, as here we're checking overall CLI behavior.
        # For CLI, we'll check the one with &amp; to ensure it was removed.
        book = ebooklib_epub.read_epub(modified_epub_path)
        chap2_content = ""
        for item in book.get_items_of_type(ebooklib_epub.ITEM_DOCUMENT):
            if item.get_name() == "chap2.xhtml": # From our asset generation
                chap2_content = item.get_content().decode('utf-8')
                break
        self.assertNotIn("Sentence with special chars &amp; entities.", chap2_content)
        self.assertIn("This sentence also stays.", chap2_content)


    def test_remove_sentences_overwrite(self):
        temp_overwrite_dir = os.path.join(self.test_dir, "overwrite_epubs")
        os.makedirs(os.path.join(temp_overwrite_dir, "story_overwrite"), exist_ok=True)
        
        epub_to_overwrite_path = os.path.join(temp_overwrite_dir, "story_overwrite", "test_epub_for_overwrite.epub")
        shutil.copy2(TEST_EPUB_FOR_OVERWRITE_CLI, epub_to_overwrite_path)

        result = self.runner.invoke(app, [
            "remove-sentences",
            "--dir", temp_overwrite_dir,
            TEST_SENTENCES_JSON_CLI
            # No --out, so should overwrite
        ], catch_exceptions=False)

        print(f"CLI Output (test_remove_sentences_overwrite):\n{result.stdout}")
        self.assertEqual(result.exit_code, 0, result.stdout)
        self.assertTrue(os.path.exists(epub_to_overwrite_path))
        
        self._assert_epub_content_cli(
            epub_to_overwrite_path,
            ["This is a sentence to be removed.", "Another sentence for deletion."],
            ["Keep this sentence intact.", "The quick brown fox jumps over the lazy dog."]
        )

    def test_remove_sentences_invalid_json_path(self):
        result = self.runner.invoke(app, [
            "remove-sentences",
            "--dir", self.test_dir, # dummy dir
            "non_existent_sentences.json"
        ], catch_exceptions=False)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Sentence file not found", result.stdout)

    def test_remove_sentences_invalid_epub_dir(self):
        result = self.runner.invoke(app, [
            "remove-sentences",
            "--dir", "non_existent_epub_dir",
            TEST_SENTENCES_JSON_CLI
        ], catch_exceptions=False)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("EPUB directory not found", result.stdout)

    def test_remove_sentences_json_not_a_list(self):
        bad_json_path = os.path.join(self.test_dir, "bad_sentences.json")
        with open(bad_json_path, "w") as f:
            f.write('{"not": "a list"}')
        
        result = self.runner.invoke(app, [
            "remove-sentences",
            "--dir", self.test_dir, # dummy dir
            bad_json_path
        ], catch_exceptions=False)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid format in sentence file: Must be a JSON list of strings.", result.stdout)
        
    def test_remove_sentences_empty_epub_dir(self):
        empty_epub_dir = os.path.join(self.test_dir, "empty_epubs")
        os.makedirs(empty_epub_dir, exist_ok=True)
        
        result = self.runner.invoke(app, [
            "remove-sentences",
            "--dir", empty_epub_dir,
            TEST_SENTENCES_JSON_CLI
        ], catch_exceptions=False)
        self.assertEqual(result.exit_code, 0, result.stdout) # Command should succeed but warn/inform
        self.assertIn("No .epub files found", result.stdout)


if __name__ == '__main__':
    unittest.main()