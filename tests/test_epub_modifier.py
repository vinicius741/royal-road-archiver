import unittest
import os
import tempfile
import shutil
import json
from ebooklib import epub
from core.epub_builder import modify_epub_content, load_epub_for_modification

# ASSET_DIR will be set up to point to tests/assets
ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
TEST_EPUB_ORIGINAL = os.path.join(ASSET_DIR, "test_epub_original.epub")
TEST_SENTENCES_JSON = os.path.join(ASSET_DIR, "test_sentences.json")

class TestEpubModification(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="epub_modifier_test_")
        self.sentences_to_remove = []
        if os.path.exists(TEST_SENTENCES_JSON):
            with open(TEST_SENTENCES_JSON, 'r') as f:
                self.sentences_to_remove = json.load(f)
        else:
            # This case should ideally not happen if assets are correctly generated/present
            print(f"WARNING: Sentence file {TEST_SENTENCES_JSON} not found in setUp.")
            self.sentences_to_remove = [
                "This is a sentence to be removed.",
                "Another sentence for deletion.",
                "Sentence with special chars & entities."
            ]


    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _assert_epub_content(self, epub_path, removed_check_list, kept_check_list):
        """Helper to check content of an EPUB."""
        book = epub.read_epub(epub_path)
        full_text_content = ""
        for item in book.get_items_of_type(epub.ITEM_DOCUMENT):
            full_text_content += item.get_content().decode('utf-8', errors='ignore')

        for sentence in removed_check_list:
            self.assertNotIn(sentence, full_text_content, f"Sentence '{sentence}' should have been removed.")
        
        for sentence in kept_check_list:
            self.assertIn(sentence, full_text_content, f"Sentence '{sentence}' should have been preserved.")
        return book # Return book for further specific checks if needed

    def test_modify_epub_removes_sentences(self):
        # Ensure the original test EPUB exists
        self.assertTrue(os.path.exists(TEST_EPUB_ORIGINAL), f"Test asset not found: {TEST_EPUB_ORIGINAL}")

        temp_epub_path = os.path.join(self.test_dir, "test_epub_modified.epub")
        shutil.copy2(TEST_EPUB_ORIGINAL, temp_epub_path)

        modify_epub_content(temp_epub_path, self.sentences_to_remove)

        # Sentences from test_sentences.json
        removed_sentences = [
            "This is a sentence to be removed.",
            "Another sentence for deletion.",
            "Sentence with special chars & entities." # Note: In EPUB it's "Sentence with special chars &amp; entities."
        ] 
        # The processor handles HTML entities, so we search for the plain text version.
        # The `remove_sentences_from_html_content` works on text nodes after parsing.

        kept_sentences = [
            "Keep this sentence intact.",
            "The quick brown fox jumps over the lazy dog.",
            "This sentence also stays."
        ]
        
        book = self._assert_epub_content(temp_epub_path, removed_sentences, kept_sentences)
        
        # Also check that the EPUB is still valid and has expected structure (e.g., number of items)
        original_book = epub.read_epub(TEST_EPUB_ORIGINAL)
        self.assertEqual(len(list(book.get_items())), len(list(original_book.get_items())), "Number of items in EPUB changed.")


    def test_modify_epub_no_matching_sentences(self):
        self.assertTrue(os.path.exists(TEST_EPUB_ORIGINAL), f"Test asset not found: {TEST_EPUB_ORIGINAL}")
        
        temp_epub_path = os.path.join(self.test_dir, "test_epub_no_change.epub")
        shutil.copy2(TEST_EPUB_ORIGINAL, temp_epub_path)

        non_matching_sentences = ["This sentence does not exist in the test EPUB at all.", "Nor does this one."]
        
        # To verify no changes, we can compare file hashes or modification times before and after.
        # For simplicity, we'll call modify_epub_content and then check if key content is still there.
        # The function itself prints "No changes made to EPUB" which could be captured if using subprocess.
        
        modify_epub_content(temp_epub_path, non_matching_sentences)

        # All original sentences should still be there
        original_sentences_to_check = [
            "This is a sentence to be removed.",
            "Keep this sentence intact.",
            "The quick brown fox jumps over the lazy dog.",
            "Another sentence for deletion.",
            "This sentence also stays.",
            # "Sentence with special chars & entities." # This will be &amp; in raw HTML
        ]
        # Check raw text content, so use the version as it appears in the text nodes
        
        book = epub.read_epub(temp_epub_path)
        full_text_content = ""
        for item in book.get_items_of_type(epub.ITEM_DOCUMENT):
            full_text_content += item.get_content().decode('utf-8', errors='ignore')
        
        for sentence in original_sentences_to_check:
            self.assertIn(sentence, full_text_content)
        # Check the one with entity specifically
        self.assertIn("Sentence with special chars &amp; entities.", full_text_content)


    def test_load_epub_for_modification_file_not_found(self):
        book = load_epub_for_modification("non_existent_epub_file.epub")
        self.assertIsNone(book)
        # We could also check that an error was printed to stderr, but that requires more setup.

    def test_load_epub_for_modification_corrupted_epub(self):
        # Create a dummy corrupted file
        corrupted_epub_path = os.path.join(self.test_dir, "corrupted.epub")
        with open(corrupted_epub_path, "w") as f:
            f.write("This is not a valid EPUB file.")
        
        book = load_epub_for_modification(corrupted_epub_path)
        self.assertIsNone(book)

if __name__ == '__main__':
    unittest.main()
