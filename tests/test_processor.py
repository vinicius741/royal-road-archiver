import unittest
from bs4 import BeautifulSoup
from core.processor import remove_sentences_from_html_content

class TestSentenceRemoval(unittest.TestCase):

    def test_remove_basic_sentences(self):
        html_content = """<html><body>
<p>This is a sentence to be removed.</p>
<p>Keep this sentence intact.</p>
<div>Another sentence for deletion. It is here.</div>
</body></html>"""
        sentences_to_remove = [
            "This is a sentence to be removed.",
            "Another sentence for deletion."
        ]
        expected_html = """<html><body>
<p></p>
<p>Keep this sentence intact.</p>
<div> It is here.</div>
</body></html>"""
        # Note: BeautifulSoup might self-close <p></p> to <p/> or format slightly differently.
        # The key is the textual content and preservation of other tags.
        
        modified_html = remove_sentences_from_html_content(html_content, sentences_to_remove)
        
        # Parse both to allow for minor formatting differences by BeautifulSoup
        soup_modified = BeautifulSoup(modified_html, 'html.parser')
        soup_expected = BeautifulSoup(expected_html, 'html.parser')

        self.assertEqual(str(soup_modified), str(soup_expected))
        # More robust check: Check text content of specific tags
        self.assertEqual(soup_modified.find_all('p')[0].get_text(), "")
        self.assertEqual(soup_modified.find_all('p')[1].get_text(), "Keep this sentence intact.")
        self.assertIn("It is here.", soup_modified.find('div').get_text())
        self.assertNotIn("Another sentence for deletion.", soup_modified.find('div').get_text())


    def test_html_structure_preserved(self):
        html_content = """<html><head><title>Test</title></head><body>
<div class="main">
  <p style="color: red;">This is a sentence to be removed. <span>Nested sentence.</span></p>
  <p>Keep this sentence intact.</p>
</div>
<script>console.log("script content");</script>
</body></html>"""
        sentences_to_remove = ["This is a sentence to be removed."]
        # Expected: The sentence is removed, span might become empty or its content also removed if part of sentence.
        # For current implementation, " Nested sentence." would remain if "This is a sentence to be removed." is removed.
        # If the sentence was "This is a sentence to be removed. Nested sentence.", then span would be affected.
        
        modified_html = remove_sentences_from_html_content(html_content, sentences_to_remove)
        soup = BeautifulSoup(modified_html, 'html.parser')
        
        self.assertIsNotNone(soup.find('head'))
        self.assertIsNotNone(soup.find('title'))
        self.assertIsNotNone(soup.find('div', class_='main'))
        self.assertIsNotNone(soup.find('script'))
        self.assertEqual(soup.find('p', style='color: red;').get_text(), " Nested sentence.") # Current behavior
        self.assertEqual(soup.find_all('p')[1].get_text(), "Keep this sentence intact.")

    def test_no_change_if_sentences_not_found(self):
        html_content = "<p>A sentence that stays.</p><p>Another one here.</p>"
        sentences_to_remove = ["Non-existent sentence."]
        modified_html = remove_sentences_from_html_content(html_content, sentences_to_remove)
        self.assertEqual(modified_html, html_content)

    def test_empty_html_input(self):
        html_content = ""
        sentences_to_remove = ["Remove this."]
        modified_html = remove_sentences_from_html_content(html_content, sentences_to_remove)
        self.assertEqual(modified_html, "")

    def test_empty_sentences_list(self):
        html_content = "<p>Some important text.</p>"
        sentences_to_remove = []
        modified_html = remove_sentences_from_html_content(html_content, sentences_to_remove)
        self.assertEqual(modified_html, html_content)

    def test_sentences_with_special_html_chars(self):
        # Using the sentence from our test_sentences.json
        html_content = """<html><body>
<p>Sentence with special chars &amp; entities.</p>
<p>Another sentence &lt;tag&gt; example.</p>
</body></html>"""
        sentences_to_remove = ["Sentence with special chars & entities."]
        expected_html = """<html><body>
<p></p>
<p>Another sentence &lt;tag&gt; example.</p>
</body></html>"""
        
        modified_html = remove_sentences_from_html_content(html_content, sentences_to_remove)
        soup_modified = BeautifulSoup(modified_html, 'html.parser')
        soup_expected = BeautifulSoup(expected_html, 'html.parser')
        
        self.assertEqual(str(soup_modified), str(soup_expected))
        self.assertEqual(soup_modified.find_all('p')[0].get_text(), "")
        self.assertEqual(soup_modified.find_all('p')[1].get_text(), "Another sentence <tag> example.")

    def test_script_and_style_content_ignored(self):
        html_content = """<html><body>
<style>.text { font-size: 10px; /* This is a sentence to be removed. */ }</style>
<script>var x = "This is a sentence to be removed.";</script>
<p>This is a sentence to be removed.</p>
</body></html>"""
        sentences_to_remove = ["This is a sentence to be removed."]
        modified_html = remove_sentences_from_html_content(html_content, sentences_to_remove)
        soup = BeautifulSoup(modified_html, 'html.parser')

        self.assertIn("This is a sentence to be removed.", soup.find('style').string)
        self.assertIn("This is a sentence to be removed.", soup.find('script').string)
        self.assertEqual(soup.find('p').get_text(), "")

if __name__ == '__main__':
    unittest.main()
