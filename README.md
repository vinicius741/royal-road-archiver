# README.md (Relevant parts updated)

## Commands

The program is run using `python main.py`. If you run `python main.py` without any commands, it will display the help message.

Here are the available commands:

### `crawl`

Downloads a story from Royal Road chapter by chapter as raw HTML files.

-   **Arguments:**
    -   `STORY_URL`: (Required) The full URL of the story's overview page OR a chapter URL. This URL is used for metadata fetching (if overview) and default chapter discovery.
-   **Options:**
    -   `--out TEXT` or `-o TEXT`: Base folder where the raw HTML chapters will be saved. A subfolder with the story name will be created here. (Default: `downloaded_stories`)
    -   `--start-chapter-url TEXT` or `-scu TEXT`: (Optional) The specific URL of the chapter from which to start downloading. If provided, this overrides any chapter found via the main `STORY_URL`.
-   **Usage Examples:**
    ```bash
    # Start from the beginning of a story (overview URL)
    python main.py crawl "[https://www.royalroad.com/fiction/12345/some-story](https://www.royalroad.com/fiction/12345/some-story)" -o my_raw_stories
    ```
    ```bash
    # Start from a specific chapter (using main argument)
    python main.py crawl "[https://www.royalroad.com/fiction/12345/some-story/chapter/123456/chapter-one](https://www.royalroad.com/fiction/12345/some-story/chapter/123456/chapter-one)" -o my_raw_stories
    ```
    ```bash
    # Start from a specific chapter using the dedicated option (useful if STORY_URL is an overview)
    python main.py crawl "[https://www.royalroad.com/fiction/12345/some-story](https://www.royalroad.com/fiction/12345/some-story)" --start-chapter-url "[https://www.royalroad.com/fiction/12345/some-story/chapter/654321/chapter-ten](https://www.royalroad.com/fiction/12345/some-story/chapter/654321/chapter-ten)" -o my_raw_stories
    ```

### `process`

Processes raw HTML chapters of a story: cleans HTML, removes unwanted tags, and saves the processed chapters.

-   **Arguments:**
    -   `INPUT_STORY_FOLDER`: (Required) Path to the folder containing the raw HTML chapters of a single story (e.g., `downloaded_stories/some-story`).
-   **Options:**
    -   `--out TEXT` or `-o TEXT`: Base folder where the cleaned HTML chapters will be saved. A subfolder with the story name will be created here. (Default: `processed_stories`)
-   **Usage Example:**
    ```bash
    python main.py process "downloaded_stories/some-story" -o my_cleaned_stories
    ```

### `build-epub`

Generates EPUB files from cleaned HTML chapters.

-   **Arguments:**
    -   `INPUT_PROCESSED_FOLDER`: (Required) Path to the folder containing the CLEANED HTML chapters of a single story (e.g., `processed_stories/some-story`).
-   **Options:**
    -   `--out TEXT` or `-o TEXT`: Base folder where the generated EPUB files will be saved. (Default: `epubs`)
    -   `--chapters-per-epub INTEGER` or `-c INTEGER`: Number of chapters to include in each EPUB file. Set to 0 or a very large number for a single EPUB. (Default: `50`)
    -   `--author TEXT` or `-a TEXT`: Author name to be used in the EPUB metadata. (Default: `Royal Road Archiver`)
    -   `--title TEXT` or `-t TEXT`: Story title to be used in the EPUB metadata. If not provided, it will attempt to extract from the first chapter file. (Default: `Archived Royal Road Story`)
-   **Usage Example:**
    ```bash
    python main.py build-epub "processed_stories/some-story" -o my_epubs -c 100 -a "Story Author" -t "My Awesome Story"
    ```

### `full-process`

Performs the full sequence: downloads the story, processes its chapters, and builds EPUB file(s). This is the recommended command for most users.

-   **Arguments:**
    -   `STORY_URL`: (Required) The full URL of the story's overview page OR a chapter URL. This URL is primarily used for metadata (if overview) and for deriving the story's slug (for folder naming).
-   **Options:**
    -   `--start-chapter-url TEXT` or `-scu TEXT`: (Optional) The specific URL of the chapter from which to start downloading. If provided, this overrides any chapter found via the main `STORY_URL` for the crawling process.
    -   `--chapters-per-epub INTEGER` or `-c INTEGER`: Number of chapters to include in each EPUB file. (Default: `50`)
    -   `--author TEXT` or `-a TEXT`: Author name for EPUB metadata. If not provided, the tool will attempt to infer it from the overview page. (Default: `Royal Road Archiver`)
    -   `--title TEXT` or `-t TEXT`: Story title for EPUB metadata. If not provided, the tool will attempt to infer it from the overview page or slug. (Default: `Archived Royal Road Story`)
-   **Usage Example:**
    ```bash
    # Download the whole story starting from the beginning
    python main.py full-process "[https://www.royalroad.com/fiction/12345/some-story-name](https://www.royalroad.com/fiction/12345/some-story-name)"
    ```
    ```bash
    # Download starting from a specific chapter (e.g., if you stopped midway)
    # The main story URL is still useful for metadata if it's an overview page.
    python main.py full-process "[https://www.royalroad.com/fiction/12345/some-story-name](https://www.royalroad.com/fiction/12345/some-story-name)" --start-chapter-url "[https://www.royalroad.com/fiction/12345/some-story-name/chapter/654321/chapter-ten](https://www.royalroad.com/fiction/12345/some-story-name/chapter/654321/chapter-ten)" --title "Some Story Name" --author "Author Name"
    ```
    ```bash
    # If story_url itself is a chapter, and you don't provide --start-chapter-url, it will start from that chapter.
    python main.py full-process "[https://www.royalroad.com/fiction/12345/some-story-name/chapter/1234567/some-chapter-name](https://www.royalroad.com/fiction/12345/some-story-name/chapter/1234567/some-chapter-name)"
    ```

### `test`

A simple test command to ensure the CLI is working. It just prints a success message.

-   **Usage Example:**
    ```bash
    python main.py test
    ```

## Basic Workflow

For most users, the `full-process` command is the easiest way to go from a story URL to an EPUB file.

1.  **Find the URL of the story.** This can be the story's main overview page or a specific chapter.

    -   Story Overview Example: `https://www.royalroad.com/fiction/12345/my-epic-novel`
    -   Chapter Example: `https://www.royalroad.com/fiction/12345/my-epic-novel/chapter/000001/the-beginning`

2.  **Run the `full-process` command:**
    ```bash
    python main.py full-process "YOUR_STORY_URL" --title "My Epic Novel" --author "Author Name" --chapters-per-epub 100
    ```
    -   Replace `YOUR_STORY_URL` with the actual URL.
    -   If you want to start downloading from a specific chapter (e.g., to resume a download or skip initial chapters), use the `--start-chapter-url` option:
    ```bash
    python main.py full-process "STORY_OVERVIEW_URL" --start-chapter-url "URL_OF_CHAPTER_TO_START_FROM" --title "My Epic Novel" --author "Author Name"
    ```
    -   Customize the `--title`, `--author`, and `--chapters-per-epub` as needed.
    -   The tool will create three base folders if they don't exist:
        -   `downloaded_stories/`: For raw HTML.
        -   `processed_stories/`: For cleaned HTML.
        -   `epubs/`: For the final EPUB files.
            A subfolder named after the story (e.g., `my-epic-novel`) will be created within `downloaded_stories` and `processed_stories`. The EPUB files will be placed directly in the `epubs` folder.

## Advanced Workflow

If you need more control over the process, you can use the commands individually:

1.  **`crawl`**: Download the raw HTML chapters.
    ```bash
    python main.py crawl "YOUR_STORY_URL_OR_FIRST_CHAPTER" --start-chapter-url "OPTIONAL_SPECIFIC_START_CHAPTER" -o custom_raw_output
    ```
2.  **`process`**: Clean the downloaded HTML.
    ```bash
    python main.py process "custom_raw_output/story-slug" -o custom_processed_output
    ```
3.  **`build-epub`**: Create EPUB files from the cleaned HTML.
    ```bash
    python main.py build-epub "custom_processed_output/story-slug" -o custom_epub_output --title "My Custom Title"
    ```
