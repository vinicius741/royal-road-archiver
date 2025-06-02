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
