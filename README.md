# Royal Road Archiver 📚

A command-line tool to download stories from Royal Road, process them into clean HTML, and build EPUB files for offline reading.

---

## Features ✨

-   **Crawl Stories**: Download entire stories or specific chapters from Royal Road.
-   **Process HTML**: Clean the downloaded HTML, removing unnecessary scripts, styles, and unwanted elements.
-   **Build EPUBs**: Convert the cleaned HTML chapters into well-formatted EPUB files, with options to split into multiple volumes.
-   **Metadata Handling**: Fetch and utilize story metadata like title, author, and slug for organizing files and EPUBs.
-   **Flexible Workflow**: Use individual commands for crawling, processing, and building EPUBs, or run a full end-to-end process with a single command.

---

## Setup ⚙️

Follow these steps to set up your Python environment and install the necessary dependencies.

### Prerequisites

-   **Python 3.x**: This project is written in Python. It's recommended to use Python 3.7 or newer. You can download Python from [python.org](https://www.python.org/).

### Environment Setup & Dependencies

It's highly recommended to use a virtual environment to manage project dependencies.

1.  **Clone the repository (if you haven't already):**

    ```bash
    git clone https://github.com/vinicius741/royal-road-archiver
    cd royal-road-archiver
    ```

2.  **Create a virtual environment:**
    Navigate to the project's root directory in your terminal and run:

    ```bash
    python -m venv .venv
    ```

    This command creates a directory named `.venv` (or any name you prefer, like `env` or `venv`) which will contain the Python interpreter and libraries specific to this project.

3.  **Activate the virtual environment:**

        -   **On Windows:**
            ```bash
            .\.venv\Scripts\activate
            ```
        -   **On macOS and Linux:**
            `bash

    source .venv/bin/activate
    `        Your terminal prompt should change to indicate that the virtual environment is active (e.g.,`(.venv) your-prompt$`).

4.  **Install dependencies:**

    Install these dependencies by running:

    ```bash
    pip install -r requirements.txt
    ```

    This will install `typer` (for the CLI), `requests` (for HTTP requests), `beautifulsoup4` (for HTML parsing), and `EbookLib` (for EPUB creation).

---

## Usage 🚀

All commands are run from the project's root directory with the virtual environment activated. The main script is `main.py`.

The script uses `typer` for its command-line interface. You can get help for any command by running:

```bash
python main.py <command> --help
```

### Available Commands:

-   **`crawl`**: Downloads raw HTML chapters from a story URL.

    ```bash
    python main.py crawl <STORY_URL_OR_CHAPTER_URL> -o <OUTPUT_DOWNLOAD_FOLDER> --start-chapter-url <SPECIFIC_CHAPTER_URL_TO_START_FROM>
    ```

    -   `<STORY_URL_OR_CHAPTER_URL>`: Full URL of the story's overview page or a specific chapter.
    -   `-o <OUTPUT_DOWNLOAD_FOLDER>`: (Optional) Base folder for raw HTML files. Default: `downloaded_stories`.
    -   `--start-chapter-url <SPECIFIC_CHAPTER_URL_TO_START_FROM>`: (Optional) Specify a chapter URL to begin downloading from, overriding the first chapter found from an overview page.

-   **`process`**: Cleans and processes raw HTML chapter files.

    ```bash
    python main.py process <INPUT_RAW_STORY_FOLDER> -o <OUTPUT_PROCESSED_FOLDER>
    ```

    -   `<INPUT_RAW_STORY_FOLDER>`: Path to the folder containing raw HTML chapters (e.g., `downloaded_stories/story-slug`).
    -   `-o <OUTPUT_PROCESSED_FOLDER>`: (Optional) Base folder for cleaned HTML files. Default: `processed_stories`.

-   **`build-epub`**: Generates EPUB files from cleaned HTML chapters.

    ```bash
    python main.py build-epub <INPUT_PROCESSED_FOLDER> -o <OUTPUT_EPUB_FOLDER> -c <CHAPTERS_PER_EPUB> --author "<AUTHOR_NAME>" --title "<STORY_TITLE>"
    ```

    -   `<INPUT_PROCESSED_FOLDER>`: Path to the folder containing cleaned HTML chapters (e.g., `processed_stories/story-slug`).
    -   `-o <OUTPUT_EPUB_FOLDER>`: (Optional) Base folder for EPUB files. Default: `epubs`.
    -   `-c <CHAPTERS_PER_EPUB>`: (Optional) Number of chapters per EPUB file (0 for a single EPUB). Default: 50.
    -   `--author "<AUTHOR_NAME>"`: (Optional) Author name for EPUB metadata. Default: "Royal Road Archiver".
    -   `--title "<STORY_TITLE>"`: (Optional) Story title for EPUB metadata. Default: "Archived Royal Road Story".

-   **`full-process`**: Performs the entire sequence: download, process, and build EPUB.
    ```bash
    python main.py full-process <STORY_URL_OR_CHAPTER_URL> --start-chapter-url <SPECIFIC_CHAPTER_URL_TO_START_FROM> -c <CHAPTERS_PER_EPUB> --author "<AUTHOR_NAME>" --title "<STORY_TITLE>"
    ```
    -   This command combines the functionality of `crawl`, `process`, and `build-epub`.
    -   It uses default base folders: `downloaded_stories`, `processed_stories`, and `epubs`.

### Examples:

1.  **Full process for a story from its overview page:**

    ```bash
    python main.py full-process "[https://www.royalroad.com/fiction/12345/my-awesome-story](https://www.royalroad.com/fiction/12345/my-awesome-story)" --title "My Awesome Story" --author "Story Author"
    ```

2.  **Crawl a story starting from a specific chapter:**

    ```bash
    python main.py crawl "[https://www.royalroad.com/fiction/12345/my-awesome-story](https://www.royalroad.com/fiction/12345/my-awesome-story)" --start-chapter-url "[https://www.royalroad.com/fiction/12345/my-awesome-story/chapter/67890/chapter-5-the-adventure-begins](https://www.royalroad.com/fiction/12345/my-awesome-story/chapter/67890/chapter-5-the-adventure-begins)"
    ```

3.  **Process previously downloaded chapters:**

    ```bash
    python main.py process downloaded_stories/my-awesome-story
    ```

4.  **Build an EPUB from processed chapters (all chapters in one file):**
    ```bash
    python main.py build-epub processed_stories/my-awesome-story -c 0 --title "My Awesome Story - Full"
    ```

---

## Folder Structure 📂

-   **`core/`**: Contains the core logic for crawling, processing, and EPUB building.
-   **`tests/`**: Contains unit and integration tests for the application.
-   **`main.py`**: The main script for the command-line interface.
-   **`.vscode/`**: (Optional) Contains VS Code specific settings, like `python.analysis.extraPaths` which can help with intellisense for the `core` module.
-   **`downloaded_stories/`**: Default output directory for raw HTML files downloaded by the `crawl` command. Stories are saved in subfolders named after their slug.
-   **`processed_stories/`**: Default output directory for cleaned HTML files generated by the `process` command. Organized similarly to `downloaded_stories`.
-   **`epubs/`**: Default output directory for the final EPUB files generated by the `build-epub` command.
-   **`.venv/`** (or your chosen name): Directory for the Python virtual environment (should be added to `.gitignore`).

---

## Running Tests 🧪 (Optional)

If you want to run the tests:

1.  Make sure you have the test dependencies installed (if any additional ones are specified, e.g., `unittest` is built-in).
2.  Navigate to the project root directory.
3.  Run the tests. For example, if using `unittest`:
    ```bash
    python -m unittest discover -s tests
    ```
    Or directly run the test file:
    ```bash
    python tests/test_main.py
    ```
