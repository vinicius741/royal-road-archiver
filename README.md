# Royal Road Story Archiver

This is a command-line interface (CLI) tool for downloading stories from Royal Road (royalroad.com), processing their content, and converting them into EPUB format for offline reading.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_folder>
    ```
    *(Replace `<repository_url>` with the actual URL of this repository and `<repository_folder>` with the name of the cloned directory.)*

2.  **Install Python:**
    Make sure you have Python 3.7+ installed. You can download it from [python.org](https://www.python.org/).

3.  **Install dependencies:**
    This project uses [Typer](https://typer.tiangolo.com/) for its command-line interface. You'll also need `beautifulsoup4` for HTML processing and `ebooklib` for EPUB creation. You can install them using pip:
    ```bash
    pip install typer beautifulsoup4 ebooklib requests
    ```
    *(Note: `requests` is used by the crawler, and `lxml` is a good parser for `beautifulsoup4`, so it's good to include them. If there are other specific dependencies revealed by `core` files, they should be added here.)*

    If you encounter any `ModuleNotFoundError` for other packages when running the program, please install them using pip as well.

## Commands

The program is run using `python main.py`. If you run `python main.py` without any commands, it will display the help message.

Here are the available commands:

### `crawl`

Downloads a story from Royal Road chapter by chapter as raw HTML files.

*   **Arguments:**
    *   `FIRST_CHAPTER_URL`: (Required) The full URL of the first chapter of the story.
*   **Options:**
    *   `--out TEXT` or `-o TEXT`: Base folder where the raw HTML chapters will be saved. A subfolder with the story name will be created here. (Default: `downloaded_stories`)

*   **Usage Example:**
    ```bash
    python main.py crawl "https://www.royalroad.com/fiction/12345/some-story/chapter/123456/chapter-one" -o my_raw_stories
    ```

### `process`

Processes raw HTML chapters of a story: cleans HTML, removes unwanted tags, and saves the processed chapters.

*   **Arguments:**
    *   `INPUT_STORY_FOLDER`: (Required) Path to the folder containing the raw HTML chapters of a single story (e.g., `downloaded_stories/some-story`).
*   **Options:**
    *   `--out TEXT` or `-o TEXT`: Base folder where the cleaned HTML chapters will be saved. A subfolder with the story name will be created here. (Default: `processed_stories`)

*   **Usage Example:**
    ```bash
    python main.py process "downloaded_stories/some-story" -o my_cleaned_stories
    ```

### `build-epub`

Generates EPUB files from cleaned HTML chapters.

*   **Arguments:**
    *   `INPUT_PROCESSED_FOLDER`: (Required) Path to the folder containing the CLEANED HTML chapters of a single story (e.g., `processed_stories/some-story`).
*   **Options:**
    *   `--out TEXT` or `-o TEXT`: Base folder where the generated EPUB files will be saved. (Default: `epubs`)
    *   `--chapters-per-epub INTEGER` or `-c INTEGER`: Number of chapters to include in each EPUB file. Set to 0 or a very large number for a single EPUB. (Default: `50`)
    *   `--author TEXT` or `-a TEXT`: Author name to be used in the EPUB metadata. (Default: `Royal Road Archiver`)
    *   `--title TEXT` or `-t TEXT`: Story title to be used in the EPUB metadata. If not provided, it will attempt to extract from the first chapter file. (Default: `Archived Royal Road Story`)

*   **Usage Example:**
    ```bash
    python main.py build-epub "processed_stories/some-story" -o my_epubs -c 100 -a "Story Author" -t "My Awesome Story"
    ```

### `full-process`

Performs the full sequence: downloads the story, processes its chapters, and builds EPUB file(s). This is the recommended command for most users.

*   **Arguments:**
    *   `FIRST_CHAPTER_URL`: (Required) The full URL of the first chapter of the story.
*   **Options:**
    *   `--chapters-per-epub INTEGER` or `-c INTEGER`: Number of chapters to include in each EPUB file. (Default: `50`)
    *   `--author TEXT` or `-a TEXT`: Author name for EPUB metadata. (Default: `Royal Road Archiver`)
    *   `--title TEXT` or `-t TEXT`: Story title for EPUB metadata. If not provided, the tool will attempt to infer it. (Default: `Archived Royal Road Story`)

*   **Usage Example:**
    ```bash
    python main.py full-process "https://www.royalroad.com/fiction/12345/some-story/chapter/123456/chapter-one" -c 75 -a "Cool Author" -t "An Epic Tale"
    ```

### `test`

A simple test command to ensure the CLI is working. It just prints a success message.

*   **Usage Example:**
    ```bash
    python main.py test
    ```

## Basic Workflow

For most users, the `full-process` command is the easiest way to go from a story URL to an EPUB file.

1.  **Find the URL of the first chapter** of the story you want to download from Royal Road.
    *   Example: `https://www.royalroad.com/fiction/12345/my-epic-novel/chapter/000001/the-beginning`

2.  **Run the `full-process` command:**
    ```bash
    python main.py full-process "YOUR_STORY_FIRST_CHAPTER_URL" --title "My Epic Novel" --author "Author Name" --chapters-per-epub 100
    ```
    *   Replace `YOUR_STORY_FIRST_CHAPTER_URL` with the actual URL.
    *   Customize the `--title`, `--author`, and `--chapters-per-epub` as needed.
    *   The tool will create three base folders if they don't exist:
        *   `downloaded_stories/`: For raw HTML.
        *   `processed_stories/`: For cleaned HTML.
        *   `epubs/`: For the final EPUB files.
        A subfolder named after the story (e.g., `my-epic-novel`) will be created within `downloaded_stories` and `processed_stories`. The EPUB files will be placed directly in the `epubs` folder (or the folder specified with `--out` in the `build-epub` command if used individually).

### Advanced Workflow

If you need more control over the process, you can use the commands individually:

1.  **`crawl`**: Download the raw HTML chapters.
    ```bash
    python main.py crawl "YOUR_STORY_FIRST_CHAPTER_URL" -o custom_raw_output
    ```
2.  **`process`**: Clean the downloaded HTML.
    ```bash
    python main.py process "custom_raw_output/story-slug" -o custom_processed_output
    ```
    *(Replace `story-slug` with the actual folder name created by the crawl command)*
3.  **`build-epub`**: Create EPUB files from the cleaned HTML.
    ```bash
    python main.py build-epub "custom_processed_output/story-slug" -o custom_epub_output --title "My Custom Title"
    ```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
