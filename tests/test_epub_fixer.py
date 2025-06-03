# tests/test_epub_fixer.py
import pytest
from ebooklib import epub
from bs4 import BeautifulSoup
from core.epub_builder import fix_xhtml_titles_in_epub
import os # Will be needed if we add tests that create temp files/dirs

# Helper to create a basic EpubBook for tests
def create_basic_book():
    book = epub.EpubBook()
    book.set_identifier("test_id_default")
    book.set_title("Test Book Default")
    book.set_language("en")
    # Basic NAV document (NCX is usually added by ebooklib automatically on write)
    nav_doc = epub.EpubNav(uid='nav', file_name='nav.xhtml', title='Navigation')
    book.add_item(nav_doc)
    book.spine = ['nav']
    return book

def test_fix_missing_titles():
    book = create_basic_book()
    book.set_identifier("test_id_missing")
    book.set_title("Test Book Missing Titles")

    # Cover item - uid='cover' and file_name='cover.xhtml' are important for detection
    cover_item = epub.EpubHtml(uid='cover', file_name='cover.xhtml', title='Cover Page Item Should Be Ignored')
    cover_item.content = '<html><head></head><body><p>Cover content here</p></body></html>'
    book.add_item(cover_item)

    # Chapter item with a good item.title
    chap_item1 = epub.EpubHtml(uid='c1', file_name='chap1.xhtml', title='Chapter One Is Great')
    chap_item1.content = '<html><head></head><body><h1>My Chapter 1</h1></body></html>'
    book.add_item(chap_item1)

    # Chapter item with an item.title that should be ignored (e.g., "None")
    chap_item2 = epub.EpubHtml(uid='c2', file_name='chap2.xhtml', title='None') # "None" should be overridden by filename
    chap_item2.content = '<html><head></head><body><h1>My Chapter 2</h1></body></html>'
    book.add_item(chap_item2)

    # Chapter item with no item.title
    chap_item3 = epub.EpubHtml(uid='c3', file_name='chap_three_test.xhtml') # No item.title, should use filename
    chap_item3.content = '<html><head></head><body><h1>My Chapter 3</h1></body></html>'
    book.add_item(chap_item3)

    # Update spine
    book.spine.extend([cover_item, chap_item1, chap_item2, chap_item3])

    result = fix_xhtml_titles_in_epub(book)
    assert result is True, "fix_xhtml_titles_in_epub should return True as titles were modified"

    # Verify cover title
    # The fix_xhtml_titles_in_epub function prioritizes 'cover.xhtml' name for "Cover" title
    retrieved_cover_item = book.get_item_with_id('cover')
    assert retrieved_cover_item is not None, "Cover item should still exist"
    cover_soup = BeautifulSoup(retrieved_cover_item.get_content().decode(), 'html.parser')
    assert cover_soup.head is not None, "Cover item should have a <head> tag"
    assert cover_soup.head.title is not None, "Cover item <head> should have a <title> tag"
    assert cover_soup.head.title.string == 'Cover', "Cover title should be 'Cover'"

    # Verify chapter 1 title (uses item.title)
    retrieved_chap1_item = book.get_item_with_id('c1')
    assert retrieved_chap1_item is not None
    chap1_soup = BeautifulSoup(retrieved_chap1_item.get_content().decode(), 'html.parser')
    assert chap1_soup.head is not None
    assert chap1_soup.head.title is not None
    assert chap1_soup.head.title.string == 'Chapter One Is Great', "Chapter 1 title should be from item.title"

    # Verify chapter 2 title (item.title was 'None', so uses filename)
    retrieved_chap2_item = book.get_item_with_id('c2')
    assert retrieved_chap2_item is not None
    chap2_soup = BeautifulSoup(retrieved_chap2_item.get_content().decode(), 'html.parser')
    assert chap2_soup.head is not None
    assert chap2_soup.head.title is not None
    assert chap2_soup.head.title.string == 'Chap2', "Chapter 2 title should be derived from filename 'chap2.xhtml'"

    # Verify chapter 3 title (no item.title, uses filename)
    retrieved_chap3_item = book.get_item_with_id('c3')
    assert retrieved_chap3_item is not None
    chap3_soup = BeautifulSoup(retrieved_chap3_item.get_content().decode(), 'html.parser')
    assert chap3_soup.head is not None
    assert chap3_soup.head.title is not None
    assert chap3_soup.head.title.string == 'Chap Three Test', "Chapter 3 title should be derived from filename 'chap_three_test.xhtml'"


def test_titles_already_correct_and_some_needing_fix():
    book = create_basic_book()
    book.set_identifier("test_id_mixed")
    book.set_title("Test Book Mixed Titles")

    # Cover item - Correct
    cover_item = epub.EpubHtml(uid='cover', file_name='cover.xhtml', title='Irrelevant Item Title')
    cover_item.content = '<html><head><title>Cover</title></head><body><p>Cover content</p></body></html>'
    book.add_item(cover_item)

    # Chapter item - Correct
    chap_item1 = epub.EpubHtml(uid='c1', file_name='chap1.xhtml', title='Chapter One')
    chap_item1.content = '<html><head><title>Chapter One</title></head><body><h1>My Chapter</h1></body></html>'
    book.add_item(chap_item1)

    # Chapter item - Missing title, but item.title is valid
    chap_item2 = epub.EpubHtml(uid='c2', file_name='chap2.xhtml', title='Chapter Two Needs Fixing')
    chap_item2.content = '<html><head></head><body><h1>My Chapter 2</h1></body></html>' # No <title>
    book.add_item(chap_item2)

    # Chapter item - Existing title is "None", should be fixed from filename
    chap_item3 = epub.EpubHtml(uid='c3', file_name='chap3_filename.xhtml', title='Another Chapter') # item.title is valid
    chap_item3.content = '<html><head><title>None</title></head><body><h1>My Chapter 3</h1></body></html>' # <title>None</title>
    book.add_item(chap_item3)

    book.spine.extend([cover_item, chap_item1, chap_item2, chap_item3])

    result = fix_xhtml_titles_in_epub(book)
    assert result is True, "Should return True as chap2 and chap3 were modified"

    # Verify titles
    cover_soup = BeautifulSoup(book.get_item_with_id('cover').get_content().decode(), 'html.parser')
    assert cover_soup.head.title.string == 'Cover'

    chap1_soup = BeautifulSoup(book.get_item_with_id('c1').get_content().decode(), 'html.parser')
    assert chap1_soup.head.title.string == 'Chapter One'

    chap2_soup = BeautifulSoup(book.get_item_with_id('c2').get_content().decode(), 'html.parser')
    assert chap2_soup.head.title.string == 'Chapter Two Needs Fixing' # Fixed from item.title

    # For chap_item3, the item.title is 'Another Chapter'.
    # The logic in fix_xhtml_titles_in_epub is: if title_tag.string != desired_title_text, it updates.
    # desired_title_text for chap_item3 will be 'Another Chapter' (from item.title).
    # So, <title>None</title> should be changed to <title>Another Chapter</title>.
    chap3_soup = BeautifulSoup(book.get_item_with_id('c3').get_content().decode(), 'html.parser')
    assert chap3_soup.head.title.string == 'Another Chapter'


def test_no_changes_needed_all_correct():
    book = create_basic_book()
    book.set_identifier("test_id_all_correct")
    book.set_title("Test Book All Correct")

    # Cover item
    cover_item = epub.EpubHtml(uid='cover', file_name='cover.xhtml', title='Cover') # item.title is ignored due to filename
    cover_item.content = '<html><head><title>Cover</title></head><body><p>Cover content</p></body></html>'
    book.add_item(cover_item)

    # Chapter item
    chap_item = epub.EpubHtml(uid='c1', file_name='chap1.xhtml', title='Chapter One')
    chap_item.content = '<html><head><title>Chapter One</title></head><body><h1>My Chapter</h1></body></html>'
    book.add_item(chap_item)

    book.spine.extend([cover_item, chap_item])

    result = fix_xhtml_titles_in_epub(book)
    assert result is False, "fix_xhtml_titles_in_epub should return False as no titles needed modification"

    # Verify titles remain unchanged
    cover_soup = BeautifulSoup(book.get_item_with_id('cover').get_content().decode(), 'html.parser')
    assert cover_soup.head.title.string == 'Cover'

    chap_soup = BeautifulSoup(book.get_item_with_id('c1').get_content().decode(), 'html.parser')
    assert chap_soup.head.title.string == 'Chapter One'

def test_fix_item_with_no_head_tag():
    book = create_basic_book()
    book.set_identifier("test_id_no_head")
    book.set_title("Test Book No Head")

    # Chapter item with no <head> at all
    chap_no_head = epub.EpubHtml(uid='c_no_head', file_name='chap_no_head.xhtml', title='No Head Chapter')
    # Content is just an html tag with a body. The fixer should create a head and title.
    chap_no_head.content = '<html><body><h1>Chapter Lacking Head</h1></body></html>'
    book.add_item(chap_no_head)
    book.spine.append(chap_no_head)

    result = fix_xhtml_titles_in_epub(book)
    assert result is True, "Should return True as item was modified to add head and title"

    retrieved_item_soup = BeautifulSoup(book.get_item_with_id('c_no_head').get_content().decode(), 'html.parser')
    assert retrieved_item_soup.html is not None, "HTML tag should exist"
    assert retrieved_item_soup.head is not None, "<head> tag should have been created"
    assert retrieved_item_soup.head.title is not None, "<title> tag should have been created in new head"
    assert retrieved_item_soup.head.title.string == 'No Head Chapter', "Title should be from item.title"

def test_fix_item_with_no_html_or_head_tag_fragment():
    book = create_basic_book()
    # This tests how the fixer handles a content fragment (though EPUB items should ideally be full docs)
    # The fixer has a basic mechanism to wrap content if no <html> tag is found.

    chap_fragment = epub.EpubHtml(uid='c_fragment', file_name='chap_fragment.xhtml', title='Fragment Chapter')
    chap_fragment.content = '<body><h1>Just a body</h1></body>' # Not even an <html> tag
    book.add_item(chap_fragment)
    book.spine.append(chap_fragment)

    result = fix_xhtml_titles_in_epub(book)
    assert result is True

    retrieved_item_soup = BeautifulSoup(book.get_item_with_id('c_fragment').get_content().decode(), 'html.parser')
    # Check the structure that fix_xhtml_titles_in_epub is expected to create
    assert retrieved_item_soup.html is not None, "An <html> tag should have been created by the fixer"
    assert retrieved_item_soup.head is not None, "<head> should have been created"
    assert retrieved_item_soup.head.title is not None, "<title> should be in the created <head>"
    assert retrieved_item_soup.head.title.string == 'Fragment Chapter'
    assert retrieved_item_soup.body is not None, "A <body> tag should exist (either original or created)"
    assert retrieved_item_soup.body.h1 is not None, "Original content (h1) should be within a body"
    assert retrieved_item_soup.body.h1.string == 'Just a body'

# Consider adding tests for XHTML files not ending in .xhtml/.html (should be skipped by the function)
# Consider adding tests for items where item.title is an empty string or whitespace (should use filename)
# Consider a test for when filename generation results in an empty string (should use "Untitled Document")
# (The current implementation of filename processing in fix_xhtml_titles_in_epub seems robust enough for most cases)

# Example of an item that should be skipped by the title fixer (e.g. CSS or image)
def test_non_html_item_is_skipped():
    book = create_basic_book()
    css_item = epub.EpubItem(uid="style_default", file_name="style/default.css", media_type="text/css", content=b"body {color: red;}")
    book.add_item(css_item)
    # fix_xhtml_titles_in_epub filters by ITEM_DOCUMENT, so this might not even be seen.
    # If it did see it, it also filters by .xhtml/.html extension.

    initial_content = css_item.get_content()
    result = fix_xhtml_titles_in_epub(book) # Should only process document items

    # Assert that the function returns False if only non-HTML items or already correct HTML items are present
    # In this case, create_basic_book adds a nav.xhtml which *will* be processed.
    # So, let's check if this specific item was touched or if the result reflects changes elsewhere.

    # To isolate, let's make a book with *only* a CSS item and see if it returns False
    isolated_book = epub.EpubBook()
    isolated_book.add_item(css_item)
    isolated_result = fix_xhtml_titles_in_epub(isolated_book)
    assert isolated_result is False, "Should return False as no applicable items were modified"
    assert css_item.get_content() == initial_content, "Non-HTML/XHTML item content should not be changed"

    # Test with a nav file that needs a title
    book_with_nav_only = epub.EpubBook()
    nav_doc = epub.EpubNav(uid='nav', file_name='nav.xhtml', title='Navigation') # item.title is "Navigation"
    nav_doc.content = "<html><head></head><body><p>Nav content</p></body></html>" # No title tag
    book_with_nav_only.add_item(nav_doc)
    book_with_nav_only.spine = ['nav']

    nav_result = fix_xhtml_titles_in_epub(book_with_nav_only)
    assert nav_result is True, "Should return True as nav.xhtml was modified"
    nav_soup = BeautifulSoup(book_with_nav_only.get_item_with_id('nav').get_content().decode(), 'html.parser')
    assert nav_soup.head.title is not None
    assert nav_soup.head.title.string == 'Navigation'
