import os
import re
from bs4 import BeautifulSoup, Comment

def _load_and_parse_html(file_path: str) -> BeautifulSoup | None:
    """
    Loads an HTML file and parses it using BeautifulSoup.

    Args:
        file_path: Path to the HTML file.

    Returns:
        A BeautifulSoup object or None if an error occurs.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        if not html_content.strip():
            print(f"   WARNING: File {file_path} is empty.")
            return None
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup
    except FileNotFoundError:
        print(f"   ERROR: File not found: {file_path}")
        return None
    except IOError as e:
        print(f"   ERROR: Could not read file {file_path}: {e}")
        return None
    except Exception as e:
        print(f"   ERROR: An unexpected error occurred while parsing {file_path}: {e}")
        return None

def _clean_and_extract_text(soup_object: BeautifulSoup, file_path: str) -> str:
    """
    Cleans the HTML content from a BeautifulSoup object, focusing on the chapter content.
    It removes scripts, styles, comments, and specific unwanted elements.

    Args:
        soup_object: The BeautifulSoup object of the chapter's HTML page.
        file_path: Original file path, for logging purposes.

    Returns:
        A string containing the cleaned HTML of the chapter content,
        or an empty string if content is not found or an error occurs.
    """
    if not soup_object:
        return "<p>Error: BeautifulSoup object was None.</p>"

    # Locate the main content div
    # The crawler saves the content within a div that was originally 'chapter-content' from RoyalRoad.
    # In the saved file, this div is directly under body, after the h1.
    # Example: <body><h1>Title</h1><div class="chapter-content">...</div></body>
    content_div = soup_object.find('div', class_='chapter-content')

    if not content_div:
        # Fallback: try to find by class 'chapter-inner chapter-content' as per example
        content_div = soup_object.find('div', class_='chapter-inner chapter-content')
        if not content_div:
            print(f"   WARNING: Could not find 'div.chapter-content' or 'div.chapter-inner.chapter-content' in {file_path}.")
            # As a last resort, if the structure is very minimal (e.g. only <p> tags directly in body)
            # and we know the crawler might put content directly, we might take soup_object.body
            # However, for now, let's stick to the known structure.
            return "<p>Conteúdo principal não encontrado no arquivo processado.</p>"

    # Remove unwanted elements from within the content_div
    # 1. Scripts
    for script_tag in content_div.find_all('script'):
        script_tag.decompose()

    # 2. Styles
    for style_tag in content_div.find_all('style'):
        style_tag.decompose()

    # 3. HTML Comments
    for comment in content_div.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # 4. Specific unwanted spans (e.g., "Unauthorized tale usage")
    #    The class name in the example "cmYx..." seems dynamic. Searching by text is more robust.
    #    The structure is: <span class="..."><br/>TEXT<br/></span>
    unauthorized_text_pattern = re.compile(r'Unauthorized tale usage', re.IGNORECASE)
    # Find all text nodes containing the pattern
    text_nodes_to_check = content_div.find_all(string=unauthorized_text_pattern)
    for text_node in text_nodes_to_check:
        # Check if the parent is a span, or a <br> whose parent is a span, etc.
        # We want to remove the encompassing <span> tag.
        span_parent = text_node.find_parent('span')
        if span_parent:
            # Additional check to be more specific, if the span only contains this and <br> tags
            # For now, if the text is found within a span, assume it's the target span.
            is_target_span = True # Simple assumption
            # A more complex check could be:
            # child_tags = [child.name for child in span_parent.children if child.name is not None]
            # is_target_span = all(tag == 'br' for tag in child_tags) and unauthorized_text_pattern.search(span_parent.get_text(separator=' '))

            if is_target_span:
                print(f"   INFO: Removing 'Unauthorized tale usage' span from {file_path}")
                span_parent.decompose()


    # Return the HTML string of the cleaned content_div
    return str(content_div)

def process_story_chapters(input_story_folder: str, output_base_folder: str):
    """
    Processes all HTML chapter files in a given story folder, cleans them,
    and saves the cleaned HTML to a corresponding folder in the output_base_folder.

    Args:
        input_story_folder: Path to the folder containing raw HTML chapters of a single story
                            (e.g., "downloaded_stories/story-slug").
        output_base_folder: Path to the base folder where processed stories will be saved
                           (e.g., "processed_stories").
    """
    story_name = os.path.basename(os.path.normpath(input_story_folder))
    processed_story_output_folder = os.path.join(output_base_folder, story_name)

    if not os.path.isdir(input_story_folder):
        print(f"ERROR: Input story folder '{input_story_folder}' not found or is not a directory.")
        return

    if not os.path.exists(processed_story_output_folder):
        print(f"Creating output folder for processed story: {processed_story_output_folder}")
        os.makedirs(processed_story_output_folder, exist_ok=True)
    else:
        print(f"Using existing output folder for processed story: {processed_story_output_folder}")

    print(f"\nProcessing story: {story_name}")
    print(f"Input folder: {input_story_folder}")
    print(f"Outputting to: {processed_story_output_folder}")

    processed_files_count = 0
    for filename in sorted(os.listdir(input_story_folder)): # Sorted to maintain chapter order
        if filename.lower().endswith((".html", ".htm")):
            raw_file_path = os.path.join(input_story_folder, filename)
            print(f"\nProcessing chapter file: {filename}")

            soup = _load_and_parse_html(raw_file_path)
            if not soup:
                print(f"   Skipping file {filename} due to loading/parsing error.")
                continue

            # Try to get original title from <h1> or <title> for logging
            page_title_tag = soup.find('title')
            h1_title_tag = soup.find('h1')
            chapter_display_title = filename
            if h1_title_tag and h1_title_tag.string:
                chapter_display_title = h1_title_tag.string.strip()
            elif page_title_tag and page_title_tag.string:
                chapter_display_title = page_title_tag.string.strip().split(' - ')[0]


            print(f"   Original Title (from HTML): {chapter_display_title}")

            cleaned_html_content = _clean_and_extract_text(soup, raw_file_path)

            if not cleaned_html_content or cleaned_html_content.strip() == "<p>Conteúdo principal não encontrado no arquivo processado.</p>" or cleaned_html_content.strip() == "<p>Error: BeautifulSoup object was None.</p>":
                print(f"   WARNING: No content extracted or error processing for {filename}. Output might be empty or contain error message.")


            # Construct output filename
            base, ext = os.path.splitext(filename)
            cleaned_filename = f"{base}_clean{ext}"
            cleaned_filepath = os.path.join(processed_story_output_folder, cleaned_filename)

            try:
                # Save the cleaned HTML (which is the content of the .chapter-content div)
                # For better direct viewing, we can wrap it in a minimal HTML structure,
                # or save as a fragment. EbookLib might prefer a full HTML doc per chapter.
                # Let's create a minimal valid HTML5 document for each cleaned chapter.
                final_html_to_save = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{chapter_display_title}</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; }}
        .chapter-content {{ max-width: 800px; margin: 0 auto; padding: 1em; border: 1px solid #ddd; }}
        /* Add any other minimal styles you want for the processed files */
    </style>
</head>
<body>
    <h1>{chapter_display_title}</h1>
    {cleaned_html_content}
</body>
</html>"""
                with open(cleaned_filepath, 'w', encoding='utf-8') as f:
                    f.write(final_html_to_save)
                print(f"   Cleaned content saved to: {cleaned_filepath}")
                processed_files_count += 1
            except IOError as e:
                print(f"   ERROR: Could not write cleaned file {cleaned_filepath}: {e}")
            except Exception as e:
                print(f"   ERROR: An unexpected error occurred while saving {cleaned_filepath}: {e}")

    if processed_files_count > 0:
        print(f"\nSuccessfully processed {processed_files_count} chapter(s) for story '{story_name}'.")
    else:
        print(f"\nNo chapter files were processed for story '{story_name}'. Check input folder and file types.")

    print("Processing complete.")

if __name__ == '__main__':
    # Example usage for testing processor.py directly
    # Create dummy files similar to what the crawler would produce for this test.
    print("Running direct test for processor.py...")

    # Dummy data paths
    test_input_base = "test_raw_story_data"
    test_story_slug = "my-sample-story"
    test_input_story_folder = os.path.join(test_input_base, test_story_slug)
    test_output_base = "test_processed_story_data"

    # Create dummy raw chapter file
    if not os.path.exists(test_input_story_folder):
        os.makedirs(test_input_story_folder)

    dummy_chapter_content_from_rr = """
    <div class="chapter-content">
        <p>This is the first paragraph of the story.</p>
        <script>console.log("This should be removed.");</script>
        <p>This is 文本 with some  моделей non-ASCII characters.</p>
        <style>.secret { display: none; }</style>
        <p>Another paragraph here.</p>
        <span class="cmYxNDIxMTliM2RlYzRlNTViNjQ0MWYyZTk4ZGVmODYz">
            <br/>Unauthorized tale usage: if you spot this story on Amazon, report the violation.<br/>
        </span>
        <p>Final paragraph.</p>
        <div class="hidden-for-some-reason-we-want-to-keep">This div should remain if it's part of content.</div>
    </div>
    """
    # This is how crawler.py saves it:
    dummy_html_file_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Chapter 1: Test Title</title>
  <style>body {{ font-family: sans-serif; }}</style>
</head>
<body>
<h1>Chapter 1: Test Title</h1>
{dummy_chapter_content_from_rr}
</body>
</html>"""

    dummy_file_path = os.path.join(test_input_story_folder, "capitulo_001_test_chapter.html")
    with open(dummy_file_path, 'w', encoding='utf-8') as f:
        f.write(dummy_html_file_content)
    print(f"Created dummy chapter: {dummy_file_path}")

    # Run the processor
    process_story_chapters(test_input_story_folder, test_output_base)

    # You would then inspect the files in "test_processed_story_data/my-sample-story/"
    print("\nProcessor test run finished. Check the output folder.")
    print(f"Expected output in: {os.path.join(test_output_base, test_story_slug)}")