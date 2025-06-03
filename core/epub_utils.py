import os
import zipfile
from core.logging_utils import log_info, log_error, log_warning # Assuming this path is correct

def unzip_epub(epub_path: str, output_dir: str) -> bool:
    """
    Extracts all contents of an EPUB file into the specified output directory.

    Args:
        epub_path: Path to the EPUB file.
        output_dir: Directory where the EPUB contents will be extracted.

    Returns:
        True on success, False on failure.
    """
    if not os.path.exists(epub_path):
        log_error(f"EPUB file not found: {epub_path}")
        return False

    if not zipfile.is_zipfile(epub_path):
        log_error(f"File is not a valid ZIP archive (EPUB): {epub_path}")
        return False

    try:
        os.makedirs(output_dir, exist_ok=True)
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        log_info(f"Successfully unzipped EPUB '{epub_path}' to '{output_dir}'")
        return True
    except Exception as e:
        log_error(f"Failed to unzip EPUB '{epub_path}': {e}")
        return False

def rezip_epub(input_dir: str, output_epub_path: str) -> bool:
    """
    Creates a new EPUB archive from the contents of a directory.

    Args:
        input_dir: Directory containing the extracted EPUB content.
        output_epub_path: Desired path for the output EPUB file.

    Returns:
        True on success, False on failure.
    """
    if not os.path.isdir(input_dir):
        log_error(f"Input directory not found: {input_dir}")
        return False

    mimetype_path = os.path.join(input_dir, "mimetype")
    if not os.path.exists(mimetype_path):
        log_error(f"'mimetype' file not found in input directory: {input_dir}")
        return False

    # Ensure output directory for the EPUB file exists
    output_epub_dir = os.path.dirname(output_epub_path)
    if output_epub_dir and not os.path.exists(output_epub_dir):
        try:
            os.makedirs(output_epub_dir, exist_ok=True)
            log_info(f"Created output directory for EPUB: {output_epub_dir}")
        except Exception as e:
            log_error(f"Could not create output directory {output_epub_dir}: {e}")
            return False

    try:
        with zipfile.ZipFile(output_epub_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add mimetype file first, uncompressed
            zf.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
            log_info(f"Added 'mimetype' to EPUB archive.")

            # Add all other files and directories recursively
            for root, _, files in os.walk(input_dir):
                for file in files:
                    if file == "mimetype":  # Already added
                        continue

                    file_path = os.path.join(root, file)
                    archive_name = os.path.relpath(file_path, input_dir)

                    zf.write(file_path, archive_name)
                    log_debug(f"Added '{archive_name}' to EPUB archive.") # Changed to log_debug for less verbosity

        log_info(f"Successfully rezipped EPUB from '{input_dir}' to '{output_epub_path}'")
        return True
    except Exception as e:
        log_error(f"Failed to rezip EPUB to '{output_epub_path}': {e}")
        return False

# Example usage (can be commented out or removed)
if __name__ == '__main__':
    # This part is for testing the functions directly if needed.
    # It requires a dummy EPUB and directories.

    # Create a dummy logger for direct script execution if logging_utils is not fully available
    # or if you want to avoid its side effects during simple tests.
    try:
        from core.logging_utils import log_debug, log_info, log_error, log_warning
    except ImportError:
        print("NOTE: core.logging_utils not found, using basic print for logs in __main__.")
        def log_debug(msg): print(f"DEBUG: {msg}")
        def log_info(msg): print(f"INFO: {msg}")
        def log_error(msg): print(f"ERROR: {msg}")
        def log_warning(msg): print(f"WARNING: {msg}")

    temp_dir_for_test = "temp_epub_utils_test"
    os.makedirs(temp_dir_for_test, exist_ok=True)

    # Create a dummy EPUB for testing unzip
    dummy_epub_path = os.path.join(temp_dir_for_test, "dummy.epub")
    unzip_output_dir = os.path.join(temp_dir_for_test, "unzipped_dummy")

    with zipfile.ZipFile(dummy_epub_path, 'w') as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("EPUB/content.opf", "<package></package>")
        zf.writestr("EPUB/chapter1.xhtml", "<html><body><h1>Chapter 1</h1></body></html>")

    log_info(f"Created dummy EPUB: {dummy_epub_path}")

    # Test unzip_epub
    if unzip_epub(dummy_epub_path, unzip_output_dir):
        log_info("Unzip test successful.")

        # Test rezip_epub
        rezip_output_path = os.path.join(temp_dir_for_test, "rezipped_dummy.epub")
        if rezip_epub(unzip_output_dir, rezip_output_path):
            log_info("Rezip test successful.")

            # Basic validation of rezipped EPUB
            if os.path.exists(rezip_output_path) and zipfile.is_zipfile(rezip_output_path):
                log_info(f"Rezipped EPUB seems valid: {rezip_output_path}")
                with zipfile.ZipFile(rezip_output_path, 'r') as zf_read:
                    file_list = zf_read.namelist()
                    log_info(f"Files in rezipped EPUB: {file_list}")
                    if "mimetype" in file_list and \
                       "EPUB/content.opf" in file_list and \
                       "EPUB/chapter1.xhtml" in file_list:
                       log_info("Essential files found in rezipped EPUB.")
                    else:
                       log_error("Essential files MISSING in rezipped EPUB.")

                    mimetype_info = zf_read.getinfo("mimetype")
                    if mimetype_info.compress_type == zipfile.ZIP_STORED:
                        log_info("Mimetype file is stored uncompressed.")
                    else:
                        log_error("Mimetype file is NOT stored uncompressed.")

            else:
                log_error(f"Rezipped EPUB is not valid or not found: {rezip_output_path}")
        else:
            log_error("Rezip test failed.")
    else:
        log_error("Unzip test failed.")

    # Clean up (optional, as it's in a temp-like directory)
    # import shutil
    # shutil.rmtree(temp_dir_for_test)
    # log_info(f"Cleaned up test directory: {temp_dir_for_test}")
```
