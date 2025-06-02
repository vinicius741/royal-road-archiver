import unittest
from unittest.mock import patch, MagicMock
import requests # For requests.Response object
from bs4 import BeautifulSoup # For direct manipulation if needed, though crawler should handle it

# Assuming your project structure allows this import
from core.crawler import fetch_story_metadata_and_first_chapter

# Sample HTML for "REND" - provided in the problem description
REND_HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>REND | Royal Road</title>
    <meta property="og:title" content="REND" />
    <meta property="og:description" content="&lt;p&gt;Grant is a retired god. He’s also a problem gambler, an alcoholic, and a bit of a mess. When his divine credit card is declined one day, he decides to get a job. He has no skills, no work history, and no references. What’s a god to do?&lt;/p&gt;&lt;p&gt;Why, become a bartender, of course. At a dive bar. In the bad part of town. During a full moon.&lt;/p&gt;&lt;hr /&gt;&lt;p&gt;REND is a slice-of-life comedy about a former god working at a bar for non-human patrons. Updates three times a week (MWF).&lt;/p&gt;" />
    <meta property="og:image" content="https://www.royalroadcdn.com/public/covers-large/117255-rend.jpg?time=1748727569" />
    <meta name="keywords" content="rend, temple, free books online, web fiction, free, book, novel, royal road, royalroadl, rrl, legends, fiction" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:site" content="@royalroadl" />
    <meta name="twitter:title" content="REND" />
    <meta name="twitter:description" content="Grant is a retired god. He’s also a problem gambler, an alcoholic, and a bit of a mess. When his divine credit card is declined one day, he decides to get a job. He has no skills, no work history, and no references. What’s a god to do? Why, become a bartender, of course. At a dive bar. In the bad part of town. During a full moon. --- REND is a slice-of-life comedy about a former god working at a bar for non-human patrons. Updates three times a week (MWF)." />
    <meta name="twitter:image" content="https://www.royalroadcdn.com/public/covers-large/117255-rend.jpg?time=1748727569" />
    <script type="application/ld+json">
    {
        "@context": "http://schema.org",
        "@type": "Book",
        "name": "REND",
        "author": {
            "@type": "Person",
            "name": "Temple"
        },
        "description": "<p>Grant is a retired god. He’s also a problem gambler, an alcoholic, and a bit of a mess. When his divine credit card is declined one day, he decides to get a job. He has no skills, no work history, and no references. What’s a god to do?</p><p>Why, become a bartender, of course. At a dive bar. In the bad part of town. During a full moon.</p><hr /><p>REND is a slice-of-life comedy about a former god working at a bar for non-human patrons. Updates three times a week (MWF).</p>",
        "image": "https://www.royalroadcdn.com/public/covers-large/117255-rend.jpg?time=1748727569",
        "genre": ["Action", "Comedy", "Contemporary Fantasy", "Slice of Life", "Urban Fantasy", "Villainous Lead"],
        "publisher": {
            "@type": "Organization",
            "name": "Royal Road"
        },
        "url": "https://www.royalroad.com/fiction/117255/rend"
    }
    </script>
</head>
<body>
    <div class="fic-title">
        <h1 class="font-white">REND</h1>
        <h4>by <a href="/profile/85078" class="font-white">Temple</a></h4>
    </div>
    <a href="/fiction/117255/rend/chapter/2291798/11-crappy-monday" class="btn btn-lg btn-primary">Start Reading</a>
    <table id="chapters">
        <tbody>
            <tr data-url="/fiction/117255/rend/chapter/2291798/11-crappy-monday">
                <td><a href="/fiction/117255/rend/chapter/2291798/11-crappy-monday">1.1 Crappy Monday</a></td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""

class TestFetchStoryMetadata(unittest.TestCase):

    @patch('core.crawler._download_page_html')
    def test_fetch_rend_metadata(self, mock_download_page_html):
        # Configure the mock response
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response._content = REND_HTML_CONTENT.encode('utf-8') # Response.text uses _content
        mock_response.url = "https://www.royalroad.com/fiction/117255/rend" # Simulate final URL after redirects

        mock_download_page_html.return_value = mock_response

        rend_overview_url = "https://www.royalroad.com/fiction/117255/rend"
        metadata = fetch_story_metadata_and_first_chapter(rend_overview_url)

        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.get('story_title'), "REND")
        self.assertEqual(metadata.get('author_name'), "Temple")
        self.assertEqual(metadata.get('first_chapter_url'), "https://www.royalroad.com/fiction/117255/rend/chapter/2291798/11-crappy-monday")
        
        # The slug logic uses the part of the URL after /fiction/ID/ and sanitizes it.
        # For "https://www.royalroad.com/fiction/117255/rend", the slug part is "rend".
        self.assertEqual(metadata.get('story_slug'), "rend")
        
        self.assertEqual(metadata.get('cover_image_url'), "https://www.royalroadcdn.com/public/covers-large/117255-rend.jpg?time=1748727569")
        
        expected_description_html = "<p>Grant is a retired god. He’s also a problem gambler, an alcoholic, and a bit of a mess. When his divine credit card is declined one day, he decides to get a job. He has no skills, no work history, and no references. What’s a god to do?</p><p>Why, become a bartender, of course. At a dive bar. In the bad part of town. During a full moon.</p><hr /><p>REND is a slice-of-life comedy about a former god working at a bar for non-human patrons. Updates three times a week (MWF).</p>"
        self.assertEqual(metadata.get('description'), expected_description_html)
        
        expected_tags = sorted([
            'rend', 'temple', 'free books online', 'web fiction', 'free', 'book', 'novel', 
            'royal road', 'royalroadl', 'rrl', 'legends', 'fiction', # From meta keywords
            'Action', 'Comedy', 'Contemporary Fantasy', 'Slice of Life', 'Urban Fantasy', 'Villainous Lead' # From JSON-LD genre
        ])
        self.assertIsInstance(metadata.get('tags'), list)
        # Sort both lists before comparing to ensure order doesn't matter
        self.assertEqual(sorted(metadata.get('tags', [])), expected_tags) 
        
        self.assertEqual(metadata.get('publisher'), "Royal Road")

        # Verify the mock was called with the correct URL
        mock_download_page_html.assert_called_once_with(rend_overview_url)

import tempfile # Added for TestMetadataHelpers
from core.crawler import _load_download_status, _save_download_status, download_story # Added for TestMetadataHelpers
from datetime import datetime # Added for TestMetadataHelpers

class TestMetadataHelpers(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_non_existent_metadata(self):
        filepath = os.path.join(self.temp_dir_path, "non_existent.json")
        data = _load_download_status(filepath)
        expected_default = {
            "overview_url": None,
            "story_title": None,
            "author_name": None,
            "last_downloaded_url": None,
            "next_expected_chapter_url": None,
            "chapters": []
        }
        self.assertEqual(data, expected_default)

    def test_save_and_load_metadata(self):
        filepath = os.path.join(self.temp_dir_path, "metadata.json")
        sample_data = {
            "overview_url": "http://example.com/story",
            "story_title": "Test Story",
            "author_name": "Test Author",
            "last_downloaded_url": "http://example.com/story/chapter/1",
            "next_expected_chapter_url": "http://example.com/story/chapter/2",
            "chapters": [
                {"url": "http://example.com/story/chapter/1", "title": "Chapter 1", "filename": "ch1.html", "downloaded_at": "timestamp1"}
            ]
        }
        _save_download_status(filepath, sample_data)
        loaded_data = _load_download_status(filepath)
        self.assertEqual(loaded_data, sample_data)

    def test_load_corrupted_json(self):
        filepath = os.path.join(self.temp_dir_path, "corrupted.json")
        with open(filepath, 'w') as f:
            f.write("this is not json {")
        
        # Patch print to check for warning
        with patch('builtins.print') as mock_print:
            data = _load_download_status(filepath)
        
        expected_default = {
            "overview_url": None,
            "story_title": None,
            "author_name": None,
            "last_downloaded_url": None,
            "next_expected_chapter_url": None,
            "chapters": []
        }
        self.assertEqual(data, expected_default)
        
        warning_found = False
        for call_args in mock_print.call_args_list:
            if "WARNING: Corrupt metadata file" in call_args[0][0]: # Make sure this matches actual warning
                warning_found = True
                break
        self.assertTrue(warning_found, "Warning message for corrupt JSON not printed.")

    def test_save_io_error(self):
        filepath = os.path.join(self.temp_dir_path, "cantwrite.json")
        sample_data = {"test": "data"}

        # Patch os.makedirs to simulate it working, but then open to fail
        with patch('os.makedirs', return_value=None), \
             patch('builtins.open', unittest.mock.mock_open()) as mocked_file:
            mocked_file.side_effect = IOError("Simulated save error")
            with patch('builtins.print') as mock_print:
                _save_download_status(filepath, sample_data)
        
        error_found = False
        # print(f"Print calls: {mock_print.call_args_list}") # For debugging test
        for call_args in mock_print.call_args_list:
            if "ERROR saving download status" in call_args[0][0]: # Make sure this matches actual error
                error_found = True
                break
        self.assertTrue(error_found, "Error message for save IOError not printed.")

class TestDownloadStoryIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_folder = self.temp_dir.name

        # Mock data for a 3-chapter novel
        self.story_data = {
            "overview_url": "http://example.com/story/rend",
            "story_title": "REND",
            "author_name": "Temple",
            "first_chapter_url": "http://example.com/story/rend/chapter/1",
            "chapters_content": {
                "http://example.com/story/rend/chapter/1": {
                    "html": "<html><head><title>Chapter 1</title></head><body><h1>Chapter 1 Content</h1></body></html>",
                    "parsed": {
                        "title": "Chapter 1: The Beginning",
                        "content_html": "<h1>Chapter 1 Content</h1><p>Some text.</p>",
                        "next_chapter_url": "http://example.com/story/rend/chapter/2"
                    }
                },
                "http://example.com/story/rend/chapter/2": {
                    "html": "<html><head><title>Chapter 2</title></head><body><h1>Chapter 2 Content</h1></body></html>",
                    "parsed": {
                        "title": "Chapter 2: The Middle",
                        "content_html": "<h1>Chapter 2 Content</h1><p>More text.</p>",
                        "next_chapter_url": "http://example.com/story/rend/chapter/3"
                    }
                },
                "http://example.com/story/rend/chapter/3": {
                    "html": "<html><head><title>Chapter 3</title></head><body><h1>Chapter 3 Content</h1></body></html>",
                    "parsed": {
                        "title": "Chapter 3: The End",
                        "content_html": "<h1>Chapter 3 Content</h1><p>Final text.</p>",
                        "next_chapter_url": None # End of story
                    }
                }
            }
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def mock_download_chapter_html_side_effect(self, page_url: str):
        mock_response = MagicMock(spec=requests.Response)
        if page_url in self.story_data["chapters_content"]:
            mock_response.text = self.story_data["chapters_content"][page_url]["html"]
            mock_response.headers = {'Content-Type': 'text/html'}
            mock_response.url = page_url # For loop detection check in download_story
            return mock_response
        else: # Should not happen if test logic is correct
            mock_response.status_code = 404
            mock_response.text = "<html><body>Page Not Found</body></html>"
            mock_response.headers = {'Content-Type': 'text/html'}
            mock_response.url = page_url
            # print(f"Warning: Mock download called for unexpected URL: {page_url}")
            return mock_response 

    def mock_parse_chapter_html_side_effect(self, html_content: str, current_page_url: str):
        # html_content is not directly used here as we key by current_page_url for simplicity
        if current_page_url in self.story_data["chapters_content"]:
            return self.story_data["chapters_content"][current_page_url]["parsed"]
        else: # Should not happen
            # print(f"Warning: Mock parse called for unexpected URL's content: {current_page_url}")
            return {"title": "Unknown Parsed Title", "content_html": "<p>Error</p>", "next_chapter_url": None}

    @patch('core.crawler._parse_chapter_html')
    @patch('core.crawler._download_chapter_html')
    def test_download_new_novel(self, mock_download_html, mock_parse_html):
        mock_download_html.side_effect = self.mock_download_chapter_html_side_effect
        mock_parse_html.side_effect = self.mock_parse_chapter_html_side_effect

        story_slug = "rend-story" # Example slug

        download_story(
            first_chapter_url=self.story_data["first_chapter_url"],
            output_folder=self.output_folder, # Base output folder
            story_slug_override=story_slug,
            overview_url=self.story_data["overview_url"],
            story_title=self.story_data["story_title"],
            author_name=self.story_data["author_name"]
        )

        story_output_path = os.path.join(self.output_folder, story_slug)
        self.assertTrue(os.path.isdir(story_output_path))

        # Assert 3 chapter files were created
        # Names will be chapter_001_slug-ch1.html, chapter_002_slug-ch2.html etc.
        # We need to check for 3 html files.
        html_files = [f for f in os.listdir(story_output_path) if f.endswith(".html")]
        self.assertEqual(len(html_files), 3, f"Expected 3 HTML files, found: {html_files}")

        # Assert that download_status.json was created
        metadata_filepath = os.path.join(story_output_path, "download_status.json")
        self.assertTrue(os.path.exists(metadata_filepath))

        # Load download_status.json and verify its contents
        with open(metadata_filepath, 'r') as f:
            metadata = json.load(f)

        self.assertEqual(metadata["overview_url"], self.story_data["overview_url"])
        self.assertEqual(metadata["story_title"], self.story_data["story_title"])
        self.assertEqual(metadata["author_name"], self.story_data["author_name"])
        
        self.assertEqual(len(metadata["chapters"]), 3)
        self.assertEqual(metadata["chapters"][0]["url"], "http://example.com/story/rend/chapter/1")
        self.assertEqual(metadata["chapters"][0]["title"], "Chapter 1: The Beginning")
        self.assertTrue(metadata["chapters"][0]["filename"].startswith("chapter_001_"))
        
        self.assertEqual(metadata["chapters"][1]["url"], "http://example.com/story/rend/chapter/2")
        self.assertEqual(metadata["chapters"][1]["title"], "Chapter 2: The Middle")
        self.assertTrue(metadata["chapters"][1]["filename"].startswith("chapter_002_"))

        self.assertEqual(metadata["chapters"][2]["url"], "http://example.com/story/rend/chapter/3")
        self.assertEqual(metadata["chapters"][2]["title"], "Chapter 3: The End")
        self.assertTrue(metadata["chapters"][2]["filename"].startswith("chapter_003_"))

        self.assertEqual(metadata["last_downloaded_url"], "http://example.com/story/rend/chapter/3")
        self.assertIsNone(metadata["next_expected_chapter_url"])
        
        # Check mock calls
        self.assertEqual(mock_download_html.call_count, 3)
        self.assertEqual(mock_parse_html.call_count, 3)

    @patch('core.crawler._parse_chapter_html')
    @patch('core.crawler._download_chapter_html')
    def test_rerun_on_fully_downloaded_novel(self, mock_download_html, mock_parse_html):
        mock_download_html.side_effect = self.mock_download_chapter_html_side_effect
        mock_parse_html.side_effect = self.mock_parse_chapter_html_side_effect
        story_slug = "rend-story-fully-downloaded"

        # First run: Download the novel completely
        download_story(
            first_chapter_url=self.story_data["first_chapter_url"],
            output_folder=self.output_folder,
            story_slug_override=story_slug,
            overview_url=self.story_data["overview_url"],
            story_title=self.story_data["story_title"],
            author_name=self.story_data["author_name"]
        )

        story_output_path = os.path.join(self.output_folder, story_slug)
        metadata_filepath = os.path.join(story_output_path, "download_status.json")
        
        # Get content of metadata file after first run
        with open(metadata_filepath, 'r') as f:
            metadata_after_first_run = json.load(f)
        
        # Reset mocks to check if they are called during the second run
        mock_download_html.reset_mock()
        mock_parse_html.reset_mock()

        # Second run: Call download_story again
        typer_echo_patch = patch('builtins.print') # Suppress print statements for cleaner test output
        with typer_echo_patch: # Patch print to avoid seeing "Resuming download..." etc.
             download_story(
                first_chapter_url=self.story_data["first_chapter_url"],
                output_folder=self.output_folder,
                story_slug_override=story_slug,
                overview_url=self.story_data["overview_url"],
                story_title=self.story_data["story_title"],
                author_name=self.story_data["author_name"]
            )

        # Assert that download and parse functions were NOT called
        mock_download_html.assert_not_called()
        mock_parse_html.assert_not_called()

        # Assert that download_status.json remains unchanged
        with open(metadata_filepath, 'r') as f:
            metadata_after_second_run = json.load(f)
        self.assertEqual(metadata_after_second_run, metadata_after_first_run)

        # Assert that no new chapter files were created (still 3 files)
        html_files = [f for f in os.listdir(story_output_path) if f.endswith(".html")]
        self.assertEqual(len(html_files), 3)

    @patch('core.crawler._parse_chapter_html')
    @patch('core.crawler._download_chapter_html')
    def test_download_partial_novel_resume(self, mock_download_html, mock_parse_html):
        mock_download_html.side_effect = self.mock_download_chapter_html_side_effect
        mock_parse_html.side_effect = self.mock_parse_chapter_html_side_effect
        story_slug = "rend-story-partial"

        story_output_path = os.path.join(self.output_folder, story_slug)
        os.makedirs(story_output_path, exist_ok=True) # Create the story-specific folder

        # 1. Create initial state: 1 chapter downloaded out of 3
        metadata_filepath = os.path.join(story_output_path, "download_status.json")
        
        initial_chapter_1_url = self.story_data["first_chapter_url"]
        initial_chapter_1_parsed = self.story_data["chapters_content"][initial_chapter_1_url]["parsed"]
        
        # Create dummy file for chapter 1 (content doesn't matter for this test's check, only its presence)
        # Filename needs to match what download_story would create.
        # The exact filename depends on _sanitize_filename and chapter_number_counter logic.
        # For simplicity, we'll use a known pattern from the first test or make it simple.
        # Let's assume the sanitize function and counter make it "chapter_001_... .html"
        # For the test, the important part is that the metadata 'filename' matches an existing file.
        ch1_filename = f"chapter_001_chapter_1_the_beginning.html" # Matches title "Chapter 1: The Beginning"
        ch1_filepath = os.path.join(story_output_path, ch1_filename)
        with open(ch1_filepath, "w") as f:
            f.write("<html><body>Dummy Chapter 1</body></html>")

        initial_metadata = {
            "overview_url": self.story_data["overview_url"],
            "story_title": self.story_data["story_title"],
            "author_name": self.story_data["author_name"],
            "last_downloaded_url": initial_chapter_1_url,
            "next_expected_chapter_url": initial_chapter_1_parsed["next_chapter_url"], # Points to chapter 2
            "chapters": [{
                "url": initial_chapter_1_url,
                "title": initial_chapter_1_parsed["title"],
                "filename": ch1_filename, # Actual filename
                "download_timestamp": datetime.utcnow().isoformat() + "Z",
                "next_url_from_page": initial_chapter_1_parsed["next_chapter_url"],
                "download_order": 1
            }]
        }
        with open(metadata_filepath, 'w') as f:
            json.dump(initial_metadata, f, indent=4)

        # 2. Call download_story to resume
        download_story(
            first_chapter_url=self.story_data["first_chapter_url"], # Still needed for context
            output_folder=self.output_folder,
            story_slug_override=story_slug,
            overview_url=self.story_data["overview_url"],
            story_title=self.story_data["story_title"],
            author_name=self.story_data["author_name"]
        )

        # 3. Assertions
        # _download_chapter_html called only for chapters 2 and 3
        # Call args list contains tuples, first element of tuple is args, second is kwargs
        # We are interested in the first positional argument (page_url)
        download_calls = [call[0][0] for call in mock_download_html.call_args_list]
        self.assertEqual(len(download_calls), 2)
        self.assertIn("http://example.com/story/rend/chapter/2", download_calls)
        self.assertIn("http://example.com/story/rend/chapter/3", download_calls)
        self.assertNotIn("http://example.com/story/rend/chapter/1", download_calls)
        
        # _parse_chapter_html called only for chapters 2 and 3 (based on their HTML)
        parse_calls_urls = [call[0][1] for call in mock_parse_html.call_args_list] # current_page_url is the 2nd arg
        self.assertEqual(len(parse_calls_urls), 2)
        self.assertIn("http://example.com/story/rend/chapter/2", parse_calls_urls)
        self.assertIn("http://example.com/story/rend/chapter/3", parse_calls_urls)
        self.assertNotIn("http://example.com/story/rend/chapter/1", parse_calls_urls)


        # Chapter files for 2 and 3 created
        html_files = [f for f in os.listdir(story_output_path) if f.endswith(".html")]
        self.assertEqual(len(html_files), 3, "Should be 3 HTML files after resuming.") # ch1 (pre-existing) + ch2 + ch3
        # Check specifically for chapter 2 and 3 files (name depends on sanitize and title)
        # Example: "chapter_002_chapter_2_the_middle.html"
        # Example: "chapter_003_chapter_3_the_end.html"
        # More robust: check based on titles in metadata
        
        with open(metadata_filepath, 'r') as f:
            final_metadata = json.load(f)
        
        self.assertEqual(len(final_metadata["chapters"]), 3)
        self.assertEqual(final_metadata["chapters"][0]["url"], "http://example.com/story/rend/chapter/1")
        self.assertEqual(final_metadata["chapters"][1]["url"], "http://example.com/story/rend/chapter/2")
        self.assertEqual(final_metadata["chapters"][2]["url"], "http://example.com/story/rend/chapter/3")
        
        self.assertEqual(final_metadata["last_downloaded_url"], "http://example.com/story/rend/chapter/3")
        self.assertIsNone(final_metadata["next_expected_chapter_url"])

        # Ensure chapter 2 and 3 files exist by checking their filenames from metadata
        self.assertTrue(os.path.exists(os.path.join(story_output_path, final_metadata["chapters"][1]["filename"])))
        self.assertTrue(os.path.exists(os.path.join(story_output_path, final_metadata["chapters"][2]["filename"])))

    @patch('core.crawler._parse_chapter_html')
    @patch('core.crawler._download_chapter_html')
    def test_download_novel_updated_online_resume_from_next_url(self, mock_download_html, mock_parse_html):
        # This test simulates a scenario where a novel had 1 chapter, 
        # then more chapters (2, 3) were added online,
        # and the metadata's next_expected_chapter_url already points to chapter 2.
        mock_download_html.side_effect = self.mock_download_chapter_html_side_effect
        mock_parse_html.side_effect = self.mock_parse_chapter_html_side_effect
        story_slug = "rend-story-updated"

        story_output_path = os.path.join(self.output_folder, story_slug)
        os.makedirs(story_output_path, exist_ok=True)
        metadata_filepath = os.path.join(story_output_path, "download_status.json")

        # Initial state: Chapter 1 downloaded, but metadata indicates to check for Chapter 2 next.
        # This would happen if a previous run was interrupted after identifying ch2's URL.
        ch1_url = self.story_data["first_chapter_url"]
        ch1_parsed = self.story_data["chapters_content"][ch1_url]["parsed"]
        ch1_filename = f"chapter_001_{story_slug}_ch1.html" # Simplified filename for test
        
        # Create dummy file for chapter 1
        with open(os.path.join(story_output_path, ch1_filename), "w") as f:
            f.write("<html><body>Dummy Chapter 1 from initial download</body></html>")

        initial_metadata_updated_scenario = {
            "overview_url": self.story_data["overview_url"],
            "story_title": self.story_data["story_title"],
            "author_name": self.story_data["author_name"],
            "last_downloaded_url": ch1_url, # Last successfully downloaded
            "next_expected_chapter_url": self.story_data["chapters_content"][ch1_url]["parsed"]["next_chapter_url"], # Points to Ch2
            "chapters": [{
                "url": ch1_url,
                "title": ch1_parsed["title"],
                "filename": ch1_filename,
                "download_timestamp": datetime.utcnow().isoformat() + "Z",
                "next_url_from_page": ch1_parsed["next_chapter_url"], # What ch1 originally pointed to
                "download_order": 1
            }]
        }
        with open(metadata_filepath, 'w') as f:
            json.dump(initial_metadata_updated_scenario, f, indent=4)
        
        # Call download_story. It should pick up from chapter 2.
        download_story(
            first_chapter_url=self.story_data["first_chapter_url"], # Still passed for full context
            output_folder=self.output_folder,
            story_slug_override=story_slug,
            overview_url=self.story_data["overview_url"],
            story_title=self.story_data["story_title"],
            author_name=self.story_data["author_name"]
        )

        # Assertions
        download_calls = [call[0][0] for call in mock_download_html.call_args_list]
        self.assertEqual(len(download_calls), 2, "Should download chapters 2 and 3")
        self.assertIn("http://example.com/story/rend/chapter/2", download_calls)
        self.assertIn("http://example.com/story/rend/chapter/3", download_calls)

        parse_calls_urls = [call[0][1] for call in mock_parse_html.call_args_list]
        self.assertEqual(len(parse_calls_urls), 2, "Should parse chapters 2 and 3")
        self.assertIn("http://example.com/story/rend/chapter/2", parse_calls_urls)
        self.assertIn("http://example.com/story/rend/chapter/3", parse_calls_urls)

        with open(metadata_filepath, 'r') as f:
            final_metadata = json.load(f)
        
        self.assertEqual(len(final_metadata["chapters"]), 3) # ch1 (pre-existing) + ch2 + ch3
        self.assertEqual(final_metadata["chapters"][1]["url"], "http://example.com/story/rend/chapter/2")
        self.assertEqual(final_metadata["chapters"][2]["url"], "http://example.com/story/rend/chapter/3")
        self.assertEqual(final_metadata["last_downloaded_url"], "http://example.com/story/rend/chapter/3")
        self.assertIsNone(final_metadata["next_expected_chapter_url"])

        # Ensure new chapter files exist
        self.assertTrue(os.path.exists(os.path.join(story_output_path, final_metadata["chapters"][1]["filename"])))
        self.assertTrue(os.path.exists(os.path.join(story_output_path, final_metadata["chapters"][2]["filename"])))


if __name__ == '__main__':
    unittest.main()
