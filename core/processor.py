import os
import re
from typing import List # Added this line
from bs4 import BeautifulSoup, Comment
import traceback # For more detailed error logging if needed

def _load_and_parse_html(file_path: str) -> BeautifulSoup | None:
    """
    Loads an HTML file and parses it using BeautifulSoup.
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
        # print(traceback.format_exc()) # Uncomment for full traceback if needed
        return None

def _clean_and_extract_text(soup_object: BeautifulSoup, file_path: str) -> str:
    """
    Cleans the HTML content from a BeautifulSoup object, focusing on the chapter content.
    """
    if not soup_object:
        return "<p>Error: BeautifulSoup object was None.</p>"

    content_div = soup_object.find('div', class_='chapter-content')
    if not content_div:
        content_div = soup_object.find('div', class_='prose') # Another common class
        if not content_div:
            # If specific content div isn't found, consider taking the whole body
            # or a significant portion, but this might include unwanted elements.
            # For now, stick to known patterns.
            print(f"   WARNING: Could not find 'div.chapter-content' or 'div.prose' in {file_path}.")
            # Fallback: use the body if no other main content div is found.
            # This is a guess and might need adjustment based on raw HTML structure.
            # body_tag = soup_object.find('body')
            # if body_tag:
            #    content_div = body_tag
            # else:
            return "<p>Main content not found in the processed file.</p>"


    for script_tag in content_div.find_all('script'):
        script_tag.decompose()
    for style_tag in content_div.find_all('style'):
        style_tag.decompose()
    for comment in content_div.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    unauthorized_text_pattern = re.compile(r'Unauthorized tale usage', re.IGNORECASE)
    text_nodes_to_check = content_div.find_all(string=unauthorized_text_pattern)
    for text_node in text_nodes_to_check:
        span_parent = text_node.find_parent('span')
        if span_parent:
            print(f"   INFO: Removing 'Unauthorized tale usage' span from {file_path}")
            span_parent.decompose()
            
    # Remove empty tags that might have been left after decomposition, e.g. empty <p></p>
    for p_tag in content_div.find_all('p'):
        if not p_tag.get_text(strip=True) and not p_tag.find_all(True, recursive=False): # No text and no child elements
            p_tag.decompose()

    return str(content_div)

def process_story_chapters(input_story_folder: str, target_output_folder_for_story: str): # PARAMETER RENAMED FOR CLARITY
    """
    Processes all HTML chapter files in a given story folder, cleans them,
    and saves the cleaned HTML to the target_output_folder_for_story.

    Args:
        input_story_folder: Path to the folder containing raw HTML chapters of a single story.
        target_output_folder_for_story: Path to the specific folder where processed chapters for this story will be saved.
    """
    # The target_output_folder_for_story is now the exact directory where files should be saved,
    # NOT a base folder to create a subdirectory in.
    processed_story_output_folder = target_output_folder_for_story

    if not os.path.isdir(input_story_folder):
        print(f"ERROR: Input story folder '{input_story_folder}' not found or is not a directory.")
        return

    # Ensure the direct target output folder exists
    if not os.path.exists(processed_story_output_folder):
        print(f"Creating output folder for processed story: {processed_story_output_folder}")
        os.makedirs(processed_story_output_folder, exist_ok=True)
    else:
        print(f"Using existing output folder for processed story: {processed_story_output_folder}")

    story_name_for_log = os.path.basename(os.path.normpath(input_story_folder)) # Used for logging
    print(f"\nProcessing story: {story_name_for_log}")
    print(f"Input folder: {input_story_folder}")
    print(f"Outputting processed files to: {processed_story_output_folder}") # This should be the correct path

    processed_files_count = 0
    raw_chapter_files = sorted([f for f in os.listdir(input_story_folder) if f.lower().endswith((".html", ".htm"))])

    if not raw_chapter_files:
        print(f"No HTML files found in input folder: {input_story_folder}")
        print("Processing complete (no files to process).")
        return

    print(f"Found {len(raw_chapter_files)} HTML files to process in {input_story_folder}")

    for filename in raw_chapter_files:
        raw_file_path = os.path.join(input_story_folder, filename)
        print(f"\nProcessing chapter file: {filename}")

        soup = _load_and_parse_html(raw_file_path)
        if not soup:
            print(f"   Skipping file {filename} due to loading/parsing error or empty content.")
            continue

        page_title_tag = soup.find('title')
        h1_title_tag = soup.find('h1') # Processor should aim to have one H1 for chapter title
        chapter_display_title = filename # Fallback
        
        # Prefer H1 from the body content as the chapter title
        # The crawler saves H1 for the chapter title.
        body_h1 = None
        body_content_div = soup.find('div', class_='chapter-content') # As saved by crawler
        if body_content_div:
            body_h1 = body_content_div.find('h1')
        
        if not body_h1: # Fallback to any H1 in the doc
            body_h1 = soup.find('h1')

        if body_h1 and body_h1.string:
            chapter_display_title = body_h1.string.strip()
        elif h1_title_tag and h1_title_tag.string: # H1 outside chapter-content, or from original <head><h1>
             chapter_display_title = h1_title_tag.string.strip()
        elif page_title_tag and page_title_tag.string:
            # Extract from <title>Tag Content - Story Name</title>
            chapter_display_title = page_title_tag.string.strip().split(' - ')[0]
        
        print(f"   Chapter Title (for processed file): {chapter_display_title}")

        cleaned_html_content = _clean_and_extract_text(soup, raw_file_path)

        if not cleaned_html_content or cleaned_html_content.strip() == "<p>Main content not found in the processed file.</p>" or cleaned_html_content.strip() == "<p>Error: BeautifulSoup object was None.</p>":
            print(f"   WARNING: No valid content extracted for {filename}. Output might be minimal or contain error message.")
            # Optionally, skip saving this file if content is just an error message
            if "Main content not found" in cleaned_html_content or "Error: BeautifulSoup object was None" in cleaned_html_content: # Updated to check for English error
                print(f"   Skipping save for {filename} due to critical content extraction error.")
                continue

        base, ext = os.path.splitext(filename)
        cleaned_filename = f"{base}_clean{ext}" # e.g. capitulo_001_title_clean.html
        cleaned_filepath = os.path.join(processed_story_output_folder, cleaned_filename)

        try:
            # Create a minimal valid HTML5 document for each cleaned chapter.
            final_html_to_save = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{chapter_display_title}</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; line-height: 1.6; }}
        .chapter-content {{ max-width: 800px; margin: 0 auto; padding: 1em; }}
        h1 {{ font-size: 1.8em; text-align: center; margin-bottom: 1em; }}
        p {{ margin-bottom: 1em; text-align: justify; }}
        img, svg {{ max-width: 100%; height: auto; display: block; margin: 1em auto; }}
    </style>
</head>
<body>
    <h1>{chapter_display_title}</h1>
    <div class="chapter-content">
    {cleaned_html_content}
    </div>
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
            # print(traceback.format_exc()) # Uncomment for full traceback

    if processed_files_count > 0:
        print(f"\nSuccessfully processed {processed_files_count} chapter(s) for story '{story_name_for_log}'.")
    else:
        print(f"\nNo chapter files were actually processed and saved for story '{story_name_for_log}'. Check input folder and file content quality.")

    print("Processing complete.")


def remove_sentences_from_html_content(html_content: str, sentences_to_remove: List[str]) -> str:
    """
    Removes specified sentences from HTML content.

    Args:
        html_content: The HTML content string.
        sentences_to_remove: A list of sentences to remove.

    Returns:
        The modified HTML content string.
    """
    if not html_content or not sentences_to_remove:
        return html_content

    soup = BeautifulSoup(html_content, 'html.parser')

    for text_node in soup.find_all(string=True):
        # Skip text nodes within <script> or <style> tags
        if text_node.parent.name in ['script', 'style']:
            continue

        original_text = str(text_node)
        modified_text = original_text
        for sentence in sentences_to_remove:
            if sentence in modified_text:
                modified_text = modified_text.replace(sentence, "")
        
        if modified_text != original_text:
            # If the text becomes empty, and it's not just whitespace,
            # it's better to replace it with empty string to avoid issues.
            # If the node becomes empty, it might be removed or handled by BS4.
            if modified_text.strip() == "":
                text_node.string.replace_with("")
            else:
                text_node.string.replace_with(modified_text)

    return str(soup)


if __name__ == '__main__':
    print("Running direct test for processor.py...")
    # Ensure dummy paths are relative to where this script might be run or use absolute paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir) # Assuming core is one level down from project root

    test_input_base = os.path.join(project_root, "test_raw_story_data_proc")
    test_story_slug = "my-sample-story-proc"
    test_input_story_folder = os.path.join(test_input_base, test_story_slug)

    # The second argument should be the *exact* folder where processed files go
    test_output_specific_folder = os.path.join(project_root, "test_processed_story_data_proc", test_story_slug)


    if not os.path.exists(test_input_story_folder):
        os.makedirs(test_input_story_folder)
    # Create dummy output base if it doesn't exist, so test_output_specific_folder can be created by the function
    if not os.path.exists(os.path.dirname(test_output_specific_folder)):
         os.makedirs(os.path.dirname(test_output_specific_folder))


    dummy_chapter_content_from_rr = """
    <div class="chapter-content">
        <h1>Chapter 1: Test Title from Content</h1>
        <p>This is the first paragraph of the story.</p>
        <script>console.log("This should be removed.");</script>
        <p>This is 文本 with some  моделей non-ASCII characters.</p>
        <style>.secret { display: none; }</style>
        <p>Another paragraph here.</p>
        <span class="cmYxNDIxMTliM2RlYzRlNTViNjQ0MWYyZTk4ZGVmODYz">
            <br/>Unauthorized tale usage: if you spot this story on Amazon, report the violation.<br/>
        </span>
        <p>Final paragraph.</p>
    </div>
    """
    dummy_html_file_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Chapter 1: Test Title in Head</title>
</head>
<body>
{dummy_chapter_content_from_rr}
</body>
</html>"""

    dummy_file_path = os.path.join(test_input_story_folder, "chapter_001_test_chapter.html") # Changed "capitulo" to "chapter"
    with open(dummy_file_path, 'w', encoding='utf-8') as f:
        f.write(dummy_html_file_content)
    print(f"Created dummy chapter: {dummy_file_path}")

    # Call with the specific output folder
    process_story_chapters(test_input_story_folder, test_output_specific_folder)

    print("\nProcessor test run finished. Check the output folder.")
    print(f"Expected output in: {test_output_specific_folder}")