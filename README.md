# Royal Road Archiver 📚

A command-line tool to download stories from Royal Road, process them into clean HTML, and build EPUB files for offline reading.

---

## Features ✨

-   **Crawl Stories**: Download entire stories or specific chapters from Royal Road.
-   **Process HTML**: Clean the downloaded HTML, removing unnecessary scripts, styles, and unwanted elements.
-   **Build EPUBs**: Convert the cleaned HTML chapters into well-formatted EPUB files, with options to split into multiple volumes.
-   **Metadata Handling**: Fetch and utilize story metadata like title, author, and slug for organizing files and EPUBs.
-   **Flexible Workflow**: Use individual commands for crawling, processing, and building EPUBs, or run a full end-to-end process with a single command.
-   **Graphical User Interface**: An optional GUI to manage the full archiving process.

---

## Setup ⚙️

Follow these steps to set up your Python environment and install the necessary dependencies.

### Prerequisites

-   **Python 3.x**: This project is written in Python. It's recommended to use Python 3.7 or newer. You can download Python from [python.org](https://www.python.org/).
-   **Tkinter (for GUI)**: For the GUI, Tkinter is required. It's usually included with standard Python installations on Windows and macOS. On Linux, it might need to be installed separately (e.g., `sudo apt-get install python3-tk`).

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

    **On Windows:**
   
    ```bash
    .\.venv\Scripts\activate
    ```
    **On macOS and Linux:**
    
    ```bash
    source .venv/bin/activate
    ```
    
    Your terminal prompt should change to indicate that the virtual environment is active (e.g.,`(.venv) your-prompt$`).

5.  **Install dependencies:**

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
    -   `-o <OUTPUT_EPUB_FOLDER>`: (Optional) Base folder for EPUB files. Default: `epubs`. EPUBs for a story will be saved in a subfolder named after the story slug (e.g., `epubs/story-slug/`).
    -   `-c <CHAPTERS_PER_EPUB>`: (Optional) Number of chapters per EPUB file (0 for a single EPUB). Default: 50.
    -   `--author "<AUTHOR_NAME>"`: (Optional) Author name for EPUB metadata. Default: "Royal Road Archiver".
    -   `--title "<STORY_TITLE>"`: (Optional) Story title for EPUB metadata. Default: "Archived Royal Road Story".

-   **`full-process`**: Performs the entire sequence: download, process, and build EPUB.
    ```bash
    python main.py full-process <STORY_URL_OR_CHAPTER_URL> --start-chapter-url <SPECIFIC_CHAPTER_URL_TO_START_FROM> -c <CHAPTERS_PER_EPUB> --author "<AUTHOR_NAME>" --title "<STORY_TITLE>" --keep-intermediate-files
    ```
    -   This command combines the functionality of `crawl`, `process`, and `build-epub`.
    -   It uses default base folders: `downloaded_stories`, `processed_stories`, and `epubs`. EPUBs for a story will be saved in a subfolder named after the story slug within the `epubs` directory (e.g., `epubs/story-slug/`).
    -   **Cleanup**: By default, after successfully generating the EPUB(s), the intermediate folders (`downloaded_stories/story-slug` and `processed_stories/story-slug`) are automatically deleted to save space.
    -   `--keep-intermediate-files`: (Optional) Add this flag if you want to preserve the downloaded (raw HTML) and processed (cleaned HTML) chapter folders. This can be useful for debugging or if you want to re-process or re-build EPUBs with different settings without re-downloading.

-   **`gui`**: Launches a Graphical User Interface (GUI) to run the full process.
    ```bash
    python main.py gui
    ```
    See the "Graphical User Interface (GUI)" section below for more details.

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

### Graphical User Interface (GUI) 🖼️

For users who prefer a graphical interface, the archiver provides a GUI to run the full download and EPUB generation process.

**How to Launch:**

Ensure you have completed the setup steps (including Tkinter for GUI) and activated your virtual environment. Then, run:

```bash
python main.py gui
```

This will open a window where you can input the story details.

**Features:**

-   **Story URL**: The mandatory URL for the story's main page or a specific chapter.
-   **Start Chapter URL**: (Optional) If you want to begin downloading from a specific chapter different from the story's first chapter.
-   **Chapters per EPUB**: (Optional) Number of chapters to include in each EPUB file (e.g., 50). Use 0 to create a single EPUB for the entire story. Defaults to 50.
-   **Author Name**: (Optional) Specify the author's name for the EPUB metadata. If left blank, the tool will attempt to fetch it from the story page.
-   **Story Title**: (Optional) Specify the story's title for the EPUB metadata. If left blank, the tool will attempt to fetch it.
-   **Keep Intermediate Files**: (Checkbox, optional) If checked, the raw downloaded chapters and cleaned HTML chapters will be kept after the EPUB is generated. By default, these are deleted.
-   **Run Full Process Button**: Starts the archiving process.
-   **Feedback Area**: Displays progress messages and any errors encountered during the process.

**Note:** The GUI requires a desktop environment with Tkinter support (which is usually included with standard Python installations on Windows, macOS, and many Linux distributions). If Tkinter is not available, the command will print an error message.

---

## Folder Structure 📂

-   **`core/`**: Contains the core logic for crawling, processing, and EPUB building.
-   **`gui.py`**: The script for the Tkinter Graphical User Interface.
-   **`tests/`**: Contains unit and integration tests for the application.
-   **`main.py`**: The main script for the command-line interface.
-   **`.vscode/`**: (Optional) Contains VS Code specific settings, like `python.analysis.extraPaths` which can help with intellisense for the `core` module.
-   **`downloaded_stories/`**: Default output directory for raw HTML files downloaded by the `crawl` command. Stories are saved in subfolders named after their slug.
-   **`processed_stories/`**: Default output directory for cleaned HTML files generated by the `process` command. Organized similarly to `downloaded_stories`.
-   **`epubs/`**: Default output directory for the final EPUB files. Within this directory, EPUBs for each story are saved in a subfolder named after the story's slug (e.g., `epubs/my-awesome-story/`).
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
