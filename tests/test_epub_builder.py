import unittest
import os
import tempfile
import shutil
import zipfile # Added for creating EPUB file structure
import html # Added for html.unescape
from unittest.mock import patch, MagicMock
from ebooklib import epub, ITEM_IMAGE, ITEM_DOCUMENT # Corrected import, Added ITEM_DOCUMENT
import requests # For mocking requests.Response
from bs4 import BeautifulSoup # Added for parsing HTML/XML content in tests
from core.epub_builder import build_epubs_for_story, fix_xhtml_titles_in_epub # Added fix_xhtml_titles_in_epub

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

        expected_epub_filename = "Ch001-Ch002_my-awesome-test-story.epub" 
        epub_filepath = os.path.join(self.output_folder, expected_epub_filename)
        self.assertTrue(os.path.exists(epub_filepath), f"EPUB file was not created at {epub_filepath}")

        book = epub.read_epub(epub_filepath)

        self.assertEqual(book.get_metadata('DC', 'title')[0][0], f"{test_story_title} (Ch 1-2)")
        self.assertEqual(book.get_metadata('DC', 'creator')[0][0], test_author_name)
        self.assertEqual(book.get_metadata('DC', 'description')[0][0], test_description)
        
        dc_subjects = book.get_metadata('DC', 'subject')
        retrieved_tags = [s[0] for s in dc_subjects]
        self.assertCountEqual(retrieved_tags, test_tags)

        self.assertEqual(book.get_metadata('DC', 'publisher')[0][0], test_publisher)
        
        cover_image_item = book.get_item_with_id('cover-img')
        
        self.assertIsNotNone(cover_image_item, "Cover image item with ID 'cover-img' not found.")
        self.assertEqual(cover_image_item.get_name(), "cover.jpg", "Cover image filename mismatch.")
        self.assertEqual(cover_image_item.get_content(), b'fake_image_bytes_jpeg', "Cover image content does not match mocked content.")
        self.assertEqual(cover_image_item.media_type, "image/jpeg", "Cover image media type is incorrect.")
        
        mock_requests_get.assert_called_once_with(test_cover_url, stream=True, timeout=15)

    # Replaced previous test_fix_xhtml_head_and_titles
    def test_fix_xhtml_head_and_titles_from_raw_epub(self):
        """
        Tests fix_xhtml_titles_in_epub by creating a raw EPUB file with problematic
        XHTML content, then reading it and processing it.
        """
        with tempfile.TemporaryDirectory() as temp_dir_path:
            # 1. Define content for XHTML files
            # Changed cover.xhtml to start with <head></head> instead of <head/>
            cover_xhtml_content_str = "<?xml version='1.0' encoding='utf-8'?><!DOCTYPE html><html xmlns='http://www.w3.org/1999/xhtml'><head></head><body><p>Cover Page</p></body></html>"
            xhtml1_content_str = "<?xml version='1.0' encoding='utf-8'?><!DOCTYPE html><html xmlns='http://www.w3.org/1999/xhtml'><head/><body><p>Chapter 1 content.</p></body></html>"
            xhtml2_content_str = "<?xml version='1.0' encoding='utf-8'?><!DOCTYPE html><html xmlns='http://www.w3.org/1999/xhtml'><head></head><body><p>Chapter 2 content.</p></body></html>"

            # 2. Define OPF content (content.opf) - now includes cover
            opf_content_str = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:identifier id="bookid">urn:uuid:12345</dc:identifier>
    <dc:title>Test Book for Title Fixes</dc:title>
    <dc:language>en</dc:language>
    <meta name="cover" content="cover-item"/>
  </metadata>
  <manifest>
    <item id="cover-item" href="cover.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap1" href="chap1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap2" href="chap2.xhtml" media-type="application/xhtml+xml"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="cover-item"/>
    <itemref idref="chap1"/>
    <itemref idref="chap2"/>
  </spine>
</package>
"""
            toc_ncx_content_str = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:12345"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>Test Book for Title Fixes</text></docTitle>
  <navMap>
    <navPoint id="nav-cover" playOrder="0"><navLabel><text>Cover</text></navLabel><content src="cover.xhtml"/></navPoint>
    <navPoint id="nav-chap1" playOrder="1"><navLabel><text>Chapter 1</text></navLabel><content src="chap1.xhtml"/></navPoint>
    <navPoint id="nav-chap2" playOrder="2"><navLabel><text>Chapter 2</text></navLabel><content src="chap2.xhtml"/></navPoint>
  </navMap>
</ncx>
"""
            container_xml_content_str = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
            with open(os.path.join(temp_dir_path, "cover.xhtml"), "w", encoding="utf-8") as f: f.write(cover_xhtml_content_str)
            with open(os.path.join(temp_dir_path, "chap1.xhtml"), "w", encoding="utf-8") as f: f.write(xhtml1_content_str)
            with open(os.path.join(temp_dir_path, "chap2.xhtml"), "w", encoding="utf-8") as f: f.write(xhtml2_content_str)
            with open(os.path.join(temp_dir_path, "content.opf"), "w", encoding="utf-8") as f: f.write(opf_content_str)
            with open(os.path.join(temp_dir_path, "toc.ncx"), "w", encoding="utf-8") as f: f.write(toc_ncx_content_str)

            meta_inf_dir = os.path.join(temp_dir_path, "META-INF")
            os.makedirs(meta_inf_dir, exist_ok=True)
            with open(os.path.join(meta_inf_dir, "container.xml"), "w", encoding="utf-8") as f: f.write(container_xml_content_str)

            mimetype_content = "application/epub+zip"
            with open(os.path.join(temp_dir_path, "mimetype"), "w", encoding="utf-8") as f: f.write(mimetype_content)

            epub_file_path = os.path.join(temp_dir_path, 'test_book.epub')
            with zipfile.ZipFile(epub_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(os.path.join(temp_dir_path, "mimetype"), "mimetype", compress_type=zipfile.ZIP_STORED)
                zf.write(os.path.join(meta_inf_dir, "container.xml"), "META-INF/container.xml")
                zf.write(os.path.join(temp_dir_path, "content.opf"), "content.opf")
                zf.write(os.path.join(temp_dir_path, "toc.ncx"), "toc.ncx")
                zf.write(os.path.join(temp_dir_path, "cover.xhtml"), "cover.xhtml")
                zf.write(os.path.join(temp_dir_path, "chap1.xhtml"), "chap1.xhtml")
                zf.write(os.path.join(temp_dir_path, "chap2.xhtml"), "chap2.xhtml")

            book = epub.read_epub(epub_file_path)

            # Unconditionally set item.title to ensure correct desired_title_text.
            # fix_xhtml_titles_in_epub is now expected to process cover.xhtml as well.
            test_manifest_titles = {
                "cover.xhtml": "Cover", # NCX provides "Cover", but item.title was empty from read_epub
                "chap1.xhtml": "Chapter 1",
                "chap2.xhtml": "Chapter 2",
            }
            for item in book.get_items():
                if item.get_name() in test_manifest_titles:
                    item.title = test_manifest_titles[item.get_name()]
                    print(f"DEBUG_TEST: Manually set item.title for {item.get_name()} to '{item.title}'")

            modified = fix_xhtml_titles_in_epub(book)
            print(f"DEBUG_TEST: 'modified' flag from fix_xhtml_titles_in_epub (cover processed): {modified}")
            self.assertTrue(modified, "fix_xhtml_titles_in_epub should report MODIFICATIONS with string logic")

            # Assertions will now apply to cover, chap1, and chap2
            expected_html_titles_to_check = {
                "cover.xhtml": "Cover",
                "chap1.xhtml": "Chapter 1",
                "chap2.xhtml": "Chapter 2",
            }

            found_items_count = 0
            processed_item_names = []
            for item in book.get_items_of_type(ITEM_DOCUMENT):
                item_name = item.get_name()

                if item_name not in expected_html_titles_to_check:
                    continue # Skip any other items like NCX if they are ITEM_DOCUMENT
                processed_item_names.append(item_name)

                found_items_count +=1
                decoded_content = item.get_content().decode('utf-8')
                # Using 'html.parser' for test assertions as it's more lenient if there are minor XHTML issues
                # not critical to title presence. String manipulation might not produce perfect XHTML.
                soup = BeautifulSoup(decoded_content, 'html.parser')

                head = soup.find('head')
                self.assertIsNotNone(head, f"Item {item_name}: <head> tag should exist.")

                title_tag = head.find('title')
                self.assertIsNotNone(title_tag, f"Item {item_name}: <title> tag should exist in <head> (fixed by string logic).")

                expected_title = expected_html_titles_to_check[item_name]
                # html.unescape because desired_title_text was escaped before inserting into placeholder
                self.assertEqual(html.unescape(title_tag.string), expected_title, f"Item {item_name}: Title should be '{expected_title}' (fixed by string logic).")

            self.assertEqual(found_items_count, len(expected_html_titles_to_check), f"Should have found and tested all expected items. Processed: {processed_item_names}")

if __name__ == '__main__':
    unittest.main()
