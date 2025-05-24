import os
import re
from bs4 import BeautifulSoup, Comment
import traceback # For more detailed error logging if needed
from typing import Optional, Callable # For LoggerCallback

# Define LoggerCallback type alias, similar to main.py
LoggerCallback = Optional[Callable[[str, Optional[str]], None]]


def _load_and_parse_html(file_path: str, logger_callback: LoggerCallback = None) -> BeautifulSoup | None:
    """
    Loads an HTML file and parses it using BeautifulSoup.
    """
    log = lambda msg, style=None: logger_callback(msg, style) if logger_callback else print(msg)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        if not html_content.strip():
            log(f"   WARNING: File {file_path} is empty.", "yellow")
            return None
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup
    except FileNotFoundError:
        log(f"   ERROR: File not found: {file_path}", "red")
        return None
    except IOError as e:
        log(f"   ERROR: Could not read file {file_path}: {e}", "red")
        return None
    except Exception as e:
        log(f"   ERROR: An unexpected error occurred while parsing {file_path}: {e}", "red")
        # log(traceback.format_exc(), "yellow") # Uncomment for full traceback if needed
        return None

def _clean_and_extract_text(soup_object: BeautifulSoup, file_path: str, logger_callback: LoggerCallback = None) -> str:
    """
    Cleans the HTML content from a BeautifulSoup object, focusing on the chapter content.
    """
    log = lambda msg, style=None: logger_callback(msg, style) if logger_callback else print(msg)

    if not soup_object:
        return "<p>Error: BeautifulSoup object was None.</p>"

    content_div = soup_object.find('div', class_='chapter-content')
    if not content_div:
        content_div = soup_object.find('div', class_='prose') # Another common class
        if not content_div:
            log(f"   WARNING: Could not find 'div.chapter-content' or 'div.prose' in {file_path}.", "yellow")
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
            log(f"   INFO: Removing 'Unauthorized tale usage' span from {file_path}")
            span_parent.decompose()
            
    for p_tag in content_div.find_all('p'):
        if not p_tag.get_text(strip=True) and not p_tag.find_all(True, recursive=False):
            p_tag.decompose()

    return str(content_div)

def process_story_chapters(input_story_folder: str, target_output_folder_for_story: str, logger_callback: LoggerCallback = None):
    """
    Processes all HTML chapter files in a given story folder, cleans them,
    and saves the cleaned HTML to the target_output_folder_for_story.

    Args:
        input_story_folder: Path to the folder containing raw HTML chapters of a single story.
        target_output_folder_for_story: Path to the specific folder where processed chapters for this story will be saved.
    """
    log = lambda msg, style=None: logger_callback(msg, style) if logger_callback else print(msg)
    processed_story_output_folder = target_output_folder_for_story

    if not os.path.isdir(input_story_folder):
        log(f"ERROR: Input story folder '{input_story_folder}' not found or is not a directory.", "red")
        return

    if not os.path.exists(processed_story_output_folder):
        log(f"Creating output folder for processed story: {processed_story_output_folder}")
        os.makedirs(processed_story_output_folder, exist_ok=True)
    else:
        log(f"Using existing output folder for processed story: {processed_story_output_folder}")

    story_name_for_log = os.path.basename(os.path.normpath(input_story_folder))
    log(f"\nProcessing story: {story_name_for_log}")
    log(f"Input folder: {input_story_folder}")
    log(f"Outputting processed files to: {processed_story_output_folder}")

    processed_files_count = 0
    raw_chapter_files = sorted([f for f in os.listdir(input_story_folder) if f.lower().endswith((".html", ".htm"))])

    if not raw_chapter_files:
        log(f"No HTML files found in input folder: {input_story_folder}", "yellow")
        log("Processing complete (no files to process).")
        return

    log(f"Found {len(raw_chapter_files)} HTML files to process in {input_story_folder}")

    for filename in raw_chapter_files:
        raw_file_path = os.path.join(input_story_folder, filename)
        log(f"\nProcessing chapter file: {filename}")

        soup = _load_and_parse_html(raw_file_path, logger_callback)
        if not soup:
            log(f"   Skipping file {filename} due to loading/parsing error or empty content.", "yellow")
            continue

        page_title_tag = soup.find('title')
        h1_title_tag = soup.find('h1')
        chapter_display_title = filename
        
        body_h1 = None
        body_content_div = soup.find('div', class_='chapter-content')
        if body_content_div:
            body_h1 = body_content_div.find('h1')
        
        if not body_h1:
            body_h1 = soup.find('h1')

        if body_h1 and body_h1.string:
            chapter_display_title = body_h1.string.strip()
        elif h1_title_tag and h1_title_tag.string:
             chapter_display_title = h1_title_tag.string.strip()
        elif page_title_tag and page_title_tag.string:
            chapter_display_title = page_title_tag.string.strip().split(' - ')[0]
        
        log(f"   Chapter Title (for processed file): {chapter_display_title}")

        cleaned_html_content = _clean_and_extract_text(soup, raw_file_path, logger_callback)

        if not cleaned_html_content or cleaned_html_content.strip() == "<p>Main content not found in the processed file.</p>" or cleaned_html_content.strip() == "<p>Error: BeautifulSoup object was None.</p>":
            log(f"   WARNING: No valid content extracted for {filename}. Output might be minimal or contain error message.", "yellow")
            if "Main content not found" in cleaned_html_content or "Error: BeautifulSoup object was None" in cleaned_html_content:
                log(f"   Skipping save for {filename} due to critical content extraction error.", "yellow")
                continue

        base, ext = os.path.splitext(filename)
        cleaned_filename = f"{base}_clean{ext}"
        cleaned_filepath = os.path.join(processed_story_output_folder, cleaned_filename)

        try:
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
            log(f"   Cleaned content saved to: {cleaned_filepath}")
            processed_files_count += 1
        except IOError as e:
            log(f"   ERROR: Could not write cleaned file {cleaned_filepath}: {e}", "red")
        except Exception as e:
            log(f"   ERROR: An unexpected error occurred while saving {cleaned_filepath}: {e}", "red")
            # log(traceback.format_exc(), "yellow")

    if processed_files_count > 0:
        log(f"\nSuccessfully processed {processed_files_count} chapter(s) for story '{story_name_for_log}'.", "green")
    else:
        log(f"\nNo chapter files were actually processed and saved for story '{story_name_for_log}'. Check input folder and file content quality.", "yellow")

    log("Processing complete.")

if __name__ == '__main__':
    # Define a simple print-based logger for standalone testing
    def test_logger(message: str, style: Optional[str] = None):
        if style:
            print(f"[{style.upper()}] {message}")
        else:
            print(message)

    print("Running direct test for processor.py...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    test_input_base = os.path.join(project_root, "test_raw_story_data_proc")
    test_story_slug = "my-sample-story-proc"
    test_input_story_folder = os.path.join(test_input_base, test_story_slug)
    test_output_specific_folder = os.path.join(project_root, "test_processed_story_data_proc", test_story_slug)

    if not os.path.exists(test_input_story_folder):
        os.makedirs(test_input_story_folder)
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

    dummy_file_path = os.path.join(test_input_story_folder, "chapter_001_test_chapter.html")
    with open(dummy_file_path, 'w', encoding='utf-8') as f:
        f.write(dummy_html_file_content)
    print(f"Created dummy chapter: {dummy_file_path}")

    process_story_chapters(test_input_story_folder, test_output_specific_folder, logger_callback=test_logger)

    print("\nProcessor test run finished. Check the output folder.")
    print(f"Expected output in: {test_output_specific_folder}")