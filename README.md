# Royal Road Archiver 📚

A command-line tool to download stories from Royal Road, process them into clean HTML, and build EPUB files for offline reading.

---

## Features ✨

-   **Crawl Stories**: Download entire stories or specific chapters from Royal Road.
-   **Process HTML**: Clean the downloaded HTML, removing unnecessary scripts, styles, and unwanted elements.
-   **Build EPUBs**: Convert the cleaned HTML chapters into well-formatted EPUB files, with options to split into multiple volumes.
-   **Metadata Handling**: Fetch and utilize story metadata like title, author, slug, cover image, description, tags, and publisher for organizing files and EPUBs.
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
    The `requirements.txt` also includes Google API client libraries for the optional Google Drive upload feature.

---

## Google Drive Integration (Optional) 📤

This tool allows you to back up your generated EPUB files and story metadata to Google Drive. To use this feature, you need to set up Google Cloud Platform credentials.

### Setup Steps:

1.  **Google Cloud Console**:
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a new project or select an existing one.

2.  **Enable Google Drive API**:
    *   In the console, navigate to "APIs & Services" > "Library".
    *   Search for "Google Drive API" and enable it for your project.

3.  **Create OAuth 2.0 Credentials**:
    *   Go to "APIs & Services" > "Credentials".
    *   Click on "+ CREATE CREDENTIALS" and select "OAuth client ID".
    *   For "Application type", choose "Desktop app".
    *   Give your client a name (e.g., "RoyalRoad Archiver Desktop Client").
    *   Click "Create".

4.  **Download Credentials File**:
    *   After the OAuth client ID is created, a dialog will show your Client ID and Client Secret. You can close this, and on the Credentials page, find your newly created Desktop client.
    *   Click the download icon (⬇️) next to your OAuth 2.0 client ID.
    *   This will download a JSON file (e.g., `client_secret_XXXX.json`).
    *   **Rename this downloaded file to `credentials.json` and place it in the root directory of this `royal-road-archiver` project.**

5.  **Important Security Note**:
    *   The `credentials.json` file contains sensitive information. **Do NOT commit this file to version control (e.g., Git).** It should be listed in your `.gitignore` file.
    *   The first time you run the `upload-to-gdrive` command, your web browser will open, asking you to authorize the application to access your Google Drive.
    *   Upon successful authorization, a file named `token.json` will be created in the project's root directory. This file stores your access and refresh tokens, so the application doesn't need to ask for authorization every time.
    *   The `token.json` file should also **NOT be committed to version control** and should be added to `.gitignore`.

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
    python main.py build-epub <INPUT_PROCESSED_FOLDER> -o <OUTPUT_EPUB_FOLDER> -c <CHAPTERS_PER_EPUB> --author "<AUTHOR_NAME>" --title "<STORY_TITLE>" --cover-url "<URL>" --description "<TEXT>" --tags "<TAG1,TAG2>" --publisher "<NAME>"
    ```

    -   `<INPUT_PROCESSED_FOLDER>`: Path to the folder containing cleaned HTML chapters (e.g., `processed_stories/story-slug`).
    -   `-o <OUTPUT_EPUB_FOLDER>`: (Optional) Base folder for EPUB files. Default: `epubs`. EPUBs for a story will be saved in a subfolder named after the story slug (e.g., `epubs/story-slug/`).
    -   `-c <CHAPTERS_PER_EPUB>`: (Optional) Number of chapters per EPUB file (0 for a single EPUB). Default: 50.
    -   `--author "<AUTHOR_NAME>"`: (Optional) Author name for EPUB metadata. Default: "Royal Road Archiver".
    -   `--title "<STORY_TITLE>"`: (Optional) Story title for EPUB metadata. Default: "Archived Royal Road Story".
    -   `--cover-url <URL>` / `-cu <URL>`: (Optional) URL of the cover image for the EPUB.
    -   `--description "<TEXT>"` / `-d "<TEXT>"`: (Optional) Description for the EPUB metadata.
    -   `--tags "<TAG1,TAG2>"` / `-tg "<TAG1,TAG2>"`: (Optional) Comma-separated list of tags/genres for the EPUB metadata.
    -   `--publisher "<NAME>"` / `-p "<NAME>"`: (Optional) Publisher name for the EPUB metadata.

-   **`full-process`**: Performs the entire sequence: download, process, and build EPUB.
    ```bash
    python main.py full-process <STORY_URL_OR_CHAPTER_URL> --start-chapter-url <SPECIFIC_CHAPTER_URL_TO_START_FROM> -c <CHAPTERS_PER_EPUB> --author "<AUTHOR_NAME>" --title "<STORY_TITLE>" --keep-intermediate-files --output-base-dir <BASE_OUTPUT_DIRECTORY>
    ```
    -   This command combines the functionality of `crawl`, `process`, and `build-epub`.
    -   `--output-base-dir <BASE_OUTPUT_DIRECTORY>`: (Optional) Specify a base directory where `downloaded_stories`, `processed_stories`, and `epubs` subdirectories will be created. If not provided, these folders are created in the current working directory.
    -   **Cleanup**: By default, after successfully generating the EPUB(s), the intermediate folders (`downloaded_stories/story-slug` and `processed_stories/story-slug`) are automatically deleted to save space.
    -   `--keep-intermediate-files`: (Optional) Add this flag if you want to preserve the downloaded (raw HTML) and processed (cleaned HTML) chapter folders. This can be useful for debugging or if you want to re-process or re-build EPUBs with different settings without re-downloading.
    -   Other options like `--author`, `--title`, `-c` are passed through to the respective steps. Metadata like cover, description, tags, and publisher are automatically fetched if an overview URL is provided. If you provide specific CLI options for author/title, they will override any fetched values.

-   **`upload-to-gdrive`**: Uploads EPUB files and metadata for a story (or all stories) to your Google Drive.

    ```bash
    python main.py upload-to-gdrive <STORY_SLUG_OR_ALL>
    ```

    -   `<STORY_SLUG_OR_ALL>`: The slug of the story to upload (e.g., `my-awesome-story`). Alternatively, use `ALL` to upload all stories found in your local `epubs/` and `metadata_store/` directories.
    -   **Prerequisites**: Requires `credentials.json` to be set up as described in the "Google Drive Integration" section.
    -   The command will create a root folder named "RoyalRoad Archiver Backups" in your Google Drive, and then subfolders for each story slug.

-   **`remove-sentences`**: Removes specified sentences from EPUB files.
    ```bash
    python main.py remove-sentences <JSON_SENTENCES_PATH> --dir <EPUB_DIRECTORY> --out <OUTPUT_DIRECTORY>
    ```
    -   `<JSON_SENTENCES_PATH>`: (Required) Path to a JSON file containing a list of sentences to remove.
    -   `--dir <EPUB_DIRECTORY>` / `-d <EPUB_DIRECTORY>`: (Optional) Directory containing EPUB files to process. EPUBs are expected to be in story-specific subfolders (e.g., `epubs/story-slug/file.epub`). Default: `epubs`.
    -   `--out <OUTPUT_DIRECTORY>` / `-o <OUTPUT_DIRECTORY>`: (Optional) Directory where modified EPUBs will be saved. If not provided, the original EPUB files are overwritten. The output directory will mirror the structure of the input directory (e.g., `modified_epubs/story-slug/file.epub`).
    -   **JSON File Format:** The JSON file should contain a single list of strings. Each string is a sentence that will be removed from the text content of the EPUB files.
        ```json
        [
            "This is an example sentence to be removed.",
            "Another sentence that will be deleted from the EPUBs."
        ]
        ```

-   **`fix-epub-titles`**: Scans and fixes `<title>` tags in EPUBs.
    ```bash
    python main.py fix-epub-titles <FOLDER_PATH>
    ```
    -   `<FOLDER_PATH>`: Path to a folder containing EPUB files. The command searches recursively through subdirectories.
    -   **Functionality**: For each `.epub` file found, this command inspects its internal XHTML components (like chapters, cover pages, etc.). It ensures that each XHTML file has a valid `<title>` tag within its `<head>` section.
        -   For `cover.xhtml`, the title is set to "Cover".
        -   For other XHTML files, it attempts to use the title from the EPUB's manifest for that item. If that's not suitable (e.g., "None", "Untitled"), it generates a title from the XHTML filename.
    -   **Important**: This command directly modifies and overwrites the original EPUB files in place.
    -   **Example Usages**:
        -   To fix EPUBs within a specific story's output folder:
            ```bash
            python main.py fix-epub-titles epubs/my-story-slug/
            ```
        -   To fix all EPUBs located anywhere under the general `epubs/` directory:
            ```bash
            python main.py fix-epub-titles epubs/
            ```

### Examples:

1.  **Full process for a story from its overview page, using fetched metadata for EPUB:**

    ```bash
    python main.py full-process "https://www.royalroad.com/fiction/12345/my-awesome-story"
    ```
    *(This will attempt to use the title, author, cover, etc., fetched from the story's page for the EPUB metadata.)*

2.  **Full process, overriding title and author, and keeping intermediate files:**
    ```bash
    python main.py full-process "https://www.royalroad.com/fiction/12345/my-awesome-story" --title "My Custom Title For EPUB" --author "Custom Author" --keep-intermediate-files
    ```

3.  **Crawl a story starting from a specific chapter:**

    ```bash
    python main.py crawl "https://www.royalroad.com/fiction/12345/my-awesome-story" --start-chapter-url "https://www.royalroad.com/fiction/12345/my-awesome-story/chapter/67890/chapter-5-the-adventure-begins"
    ```

4.  **Process previously downloaded chapters:**

    ```bash
    python main.py process downloaded_stories/my-awesome-story
    ```

5.  **Build an EPUB from processed chapters with specific metadata overrides:**
    ```bash
    python main.py build-epub processed_stories/my-awesome-story -c 0 --title "My Awesome Story - Full" --author "Story Author" --cover-url "http://example.com/cover.jpg" --description "A really cool story." --tags "Fantasy,Adventure,LitRPG" --publisher "My Self-Publishing"
    ```

6.  **Remove specific sentences from all EPUBs in the `epubs` directory, saving modified versions to `epubs_modified`:**
    ```bash
    python main.py remove-sentences path/to/sentences_to_remove.json --dir epubs --out epubs_modified
    ```

7.  **Remove specific sentences from EPUBs, overwriting the original files:**
    ```bash
    python main.py remove-sentences path/to/sentences_to_remove.json --dir my_collection_of_epubs
    ```

---

## Folder Structure 📂

-   **`core/`**: Contains the core logic for crawling, processing, and EPUB building.
-   **`tests/`**: Contains unit and integration tests for the application.
-   **`main.py`**: The main script for the command-line interface.
-   **`.vscode/`**: (Optional) Contains VS Code specific settings, like `python.analysis.extraPaths` which can help with intellisense for the `core` module.
-   **`downloaded_stories/`**: Default output directory for raw HTML files downloaded by the `crawl` command. Stories are saved in subfolders named after their slug.
-   **`processed_stories/`**: Default output directory for cleaned HTML files generated by the `process` command. Organized similarly to `downloaded_stories`.
-   **`epubs/`**: Default output directory for the final EPUB files. Within this directory, EPUBs for each story are saved in a subfolder named after the story's slug (e.g., `epubs/my-awesome-story/`).
-   **`metadata_store/`**: Holds metadata for downloaded stories.
    -   **`download_status.json`**: Tracks download progress (e.g., last chapter downloaded, next chapter to download), stores chapter details (URL, title, filename, timestamp), and enables resumable downloads. Located at `metadata_store/<story-slug>/download_status.json`.
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

---

## .gitignore recommendation

Ensure your `.gitignore` file includes at least the following to protect sensitive information and avoid committing unnecessary files:

```gitignore
# Python virtual environment
.venv/
venv/
env/
*.pyc
__pycache__/

# Credentials and tokens
credentials.json
token.json

# Downloaded and processed data (optional, if you don't want to commit them)
# downloaded_stories/
# processed_stories/
# epubs/

# IDE specific
.vscode/
.idea/
```

---
*Disclaimer: This tool is for personal use only to archive stories for offline reading. Please support the authors on Royal Road by reading their work on the platform and through any monetization options they provide.*
