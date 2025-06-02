import os
from typing import Optional, List, Tuple # Added Tuple for return type hint

from ebooklib import epub
from ebooklib.epub import EpubHtml, EpubNav, read_epub # read_epub is directly available

from core.processor import remove_sentences_from_html_content
from core.logging_utils import log_info, log_error, log_debug, log_success # Added log_success

# Note: No traceback import needed for these specific functions from epub_builder


def load_epub_for_modification(epub_file_path: str) -> Optional[epub.EpubBook]:
    """Loads an EPUB file for modification.

    Args:
        epub_file_path: The path to the EPUB file.

    Returns:
        The EpubBook object if successful, None otherwise.
    """
    log_debug(f"Attempting to load EPUB for modification: {epub_file_path}")
    if not os.path.exists(epub_file_path):
        log_error(f"EPUB file not found at {epub_file_path}")
        return None
    if not os.path.isfile(epub_file_path):
        log_error(f"Path is not a file: {epub_file_path}")
        return None
        
    try:
        book = read_epub(epub_file_path)
        log_success(f"Successfully loaded EPUB: {epub_file_path}")
        return book
    except epub.EpubException as e: # More specific exception
        log_error(f"Error reading EPUB file {epub_file_path}: {e}")
        return None
    except Exception as e: # Catch other potential errors like zip errors
        log_error(f"An unexpected error occurred while loading EPUB {epub_file_path}: {e}")
        return None


def modify_epub_content(
    epub_path: str,
    sentences_to_remove: List[str],
    processed_chapters_count: int = 0, # Kept from original, though not used in current body
    dry_run: bool = False
) -> Tuple[int, int]: # Changed return type to match potential future use if counts are returned
    """
    Modifies the content of an EPUB file by removing specified sentences.
    Args:
        epub_path: The path to the EPUB file.
        sentences_to_remove: A list of sentences to remove.
        processed_chapters_count: Not currently used in this version of the function.
        dry_run: If True, performs a dry run without saving changes.

    Returns:
        A tuple (total_items_processed, total_items_modified).
        Currently, these counts are basic (0 or 1 for the whole book).
    """
    log_info(f"Starting EPUB content modification for: {epub_path}")
    if dry_run:
        log_info("Dry run mode activated. No changes will be saved.")

    book = load_epub_for_modification(epub_path) # Calls local version
    if not book:
        log_error(f"Could not load EPUB for modification: {epub_path}. Aborting modification.")
        return 0, 0 # total_items_processed, total_items_modified

    modified_in_book = False
    items_processed_count = 0
    items_modified_count = 0

    for item in book.get_items():
        if isinstance(item, (EpubHtml, EpubNav)): # Process both HTML content and Nav files
            items_processed_count += 1
            try:
                original_html_content = item.get_content().decode('utf-8', errors='ignore')
                # Use the imported remove_sentences_from_html_content
                modified_html_content, num_sentences_removed_in_item = remove_sentences_from_html_content(
                    original_html_content, 
                    sentences_to_remove
                )

                if original_html_content != modified_html_content:
                    log_debug(f"Content modified in item: {item.get_name()}. Removed {num_sentences_removed_in_item} sentence instances.")
                    if not dry_run:
                        item.set_content(modified_html_content.encode('utf-8'))
                    modified_in_book = True
                    items_modified_count +=1
                else:
                    log_debug(f"No changes made to item: {item.get_name()}")

            except Exception as e:
                log_error(f"Error processing item {item.get_name()} in {epub_path}: {e}", exc_info=True)
    
    log_info(f"EPUB modification scan complete for {epub_path}. Items processed: {items_processed_count}. Items modified (before save): {items_modified_count}.")

    if modified_in_book and not dry_run:
        output_epub_path = epub_path  # Overwrite original file
        
        # Optional: Backup original file (Consider adding as a parameter or config)
        # backup_path = epub_path + ".bak"
        # if os.path.exists(backup_path):
        #     log_debug(f"Removing existing backup file: {backup_path}")
        #     try:
        #         os.remove(backup_path)
        #     except OSError as e_rm_bak:
        #         log_warning(f"Could not remove existing backup {backup_path}: {e_rm_bak}")
        # try:
        #     os.rename(epub_path, backup_path)
        #     log_info(f"Backup of original EPUB created at: {backup_path}")
        # except OSError as e_bak:
        #     log_warning(f"Error creating backup for {epub_path}: {e_bak}. Proceeding without backup.")

        try:
            log_info(f"Attempting to save modified EPUB: {output_epub_path}")
            # Standard options, can be parameterized if needed
            epub.write_epub(output_epub_path, book, {"epub3_pages": False, "toc_depth": 2}) 
            log_success(f"Successfully modified and saved EPUB: {output_epub_path}")
        except Exception as e_write:
            log_error(f"Error saving modified EPUB {output_epub_path}: {e_write}", exc_info=True)
            # Optional: Restore backup if saving failed
            # if os.path.exists(backup_path):
            #     try:
            #         os.rename(backup_path, epub_path) # Attempt to restore
            #         log_info(f"Successfully restored original EPUB from backup: {epub_path}")
            #     except OSError as e_restore:
            #         log_error(f"CRITICAL: Error restoring backup for {epub_path} after failed save: {e_restore}. Original file might be lost or in .bak state.")
            return items_processed_count, 0 # Return 0 for modified if save failed
    elif modified_in_book and dry_run:
        log_info(f"Dry run: EPUB {epub_path} would have been modified and saved.")
    else:
        log_info(f"No content changes were made to EPUB: {epub_path}. File not saved.")

    return items_processed_count, items_modified_count if modified_in_book else 0
