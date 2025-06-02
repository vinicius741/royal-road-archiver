import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from ebooklib import epub, ITEM_IMAGE # Corrected import
import requests # For mocking requests.Response

# Assuming your project structure allows this import
from core.epub_builder import build_epubs_for_story

class TestBuildEpubsIntegration(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for all test artifacts
        self.test_dir = tempfile.mkdtemp(prefix="epub_builder_test_")
        self.input_folder = os.path.join(self.test_dir, "processed_chapters")
        self.output_folder = os.path.join(self.test_dir, "epubs_output")
        os.makedirs(self.input_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)

        # Create dummy HTML chapter files
        self.dummy_chapters_content = [
            "<html><head><title>Chapter 1</title></head><body><h1>Chapter 1 Title</h1><p>Content of chapter 1.</p></body></html>",
            "<html><head><title>Chapter 2</title></head><body><h1>Chapter 2 Title</h1><p>Content of chapter 2.</p></body></html>",
        ]
        for i, content in enumerate(self.dummy_chapters_content):
            with open(os.path.join(self.input_folder, f"chapter_{i+1:03d}.html"), "w", encoding="utf-8") as f:
                f.write(content)

    def tearDown(self):
        # Remove the temporary directory and all its contents
        shutil.rmtree(self.test_dir)

    @patch('requests.get')
    def test_build_epub_with_full_metadata(self, mock_requests_get):
        # Configure mock for requests.get (cover download)
        mock_cover_response = requests.Response()
        mock_cover_response.status_code = 200
        mock_cover_response._content = b'fake_image_bytes_jpeg' # Simulate image data
        mock_cover_response.headers['Content-Type'] = 'image/jpeg'
        mock_requests_get.return_value = mock_cover_response

        test_author_name = "Test Author"
        test_story_title = "My Awesome Test Story"
        test_cover_url = "http://example.com/cover.jpg"
        test_description = "This is a fantastic story about testing."
        test_tags = ["Fantasy", "Adventure", "Test Tag"]
        test_publisher = "Test Publisher Inc."

        build_epubs_for_story(
            input_folder=self.input_folder,
            output_folder=self.output_folder,
            chapters_per_epub=50, # All in one for this test
            author_name=test_author_name,
            story_title=test_story_title,
            cover_image_url=test_cover_url,
            story_description=test_description,
            tags=test_tags,
            publisher_name=test_publisher
        )

        # Verify EPUB was created
        # Filename construction in build_epubs_for_story:
        # f"Ch{first_chap_num:03d}-Ch{last_chap_num:03d}_{story_title_slug}.epub"
        # For 2 chapters, 50 per epub: Ch001-Ch002_my-awesome-test-story.epub
        expected_epub_filename = "Ch001-Ch002_my-awesome-test-story.epub" 
        epub_filepath = os.path.join(self.output_folder, expected_epub_filename)
        self.assertTrue(os.path.exists(epub_filepath), f"EPUB file was not created at {epub_filepath}")

        # Read and inspect the EPUB
        book = epub.read_epub(epub_filepath)

        # Title (includes chapter range if multiple volumes, or all chapters for single volume)
        # current_epub_title = f"{effective_story_title}{current_epub_title_suffix}"
        # suffix for single volume with 2 chapters: " (Ch 1-2)"
        self.assertEqual(book.get_metadata('DC', 'title')[0][0], f"{test_story_title} (Ch 1-2)")
        self.assertEqual(book.get_metadata('DC', 'creator')[0][0], test_author_name)
        self.assertEqual(book.get_metadata('DC', 'description')[0][0], test_description)
        
        # Tags (DC:subject)
        dc_subjects = book.get_metadata('DC', 'subject')
        retrieved_tags = [s[0] for s in dc_subjects]
        self.assertCountEqual(retrieved_tags, test_tags) # Use assertCountEqual for list comparison regardless of order

        self.assertEqual(book.get_metadata('DC', 'publisher')[0][0], test_publisher)
        
        self.assertEqual(book.get_metadata('DC', 'publisher')[0][0], test_publisher)
        
        self.assertEqual(book.get_metadata('DC', 'publisher')[0][0], test_publisher)
        
        self.assertEqual(book.get_metadata('DC', 'publisher')[0][0], test_publisher)
        
        self.assertEqual(book.get_metadata('DC', 'publisher')[0][0], test_publisher)
        
        # Cover image check
        # From debug output, the ID assigned by EbookLib's set_cover to the image item is 'cover-img'
        # and its name is the filename passed to set_cover ("cover.jpg").
        cover_image_item = book.get_item_with_id('cover-img')
        
        self.assertIsNotNone(cover_image_item, "Cover image item with ID 'cover-img' not found.")
        self.assertEqual(cover_image_item.get_name(), "cover.jpg", "Cover image filename mismatch.") # Filename given to set_cover
        self.assertEqual(cover_image_item.get_content(), b'fake_image_bytes_jpeg', "Cover image content does not match mocked content.")
        self.assertEqual(cover_image_item.media_type, "image/jpeg", "Cover image media type is incorrect.")
        
        # The check for manifest properties like "cover-image" is removed due to 'EpubBook' object has no attribute 'manifest'
        # The core functionality of adding the image with correct content and type is tested above.

        # Verify requests.get was called for the cover
        mock_requests_get.assert_called_once_with(test_cover_url, stream=True, timeout=15)

if __name__ == '__main__':
    unittest.main()
