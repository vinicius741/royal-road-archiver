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

if __name__ == '__main__':
    unittest.main()
