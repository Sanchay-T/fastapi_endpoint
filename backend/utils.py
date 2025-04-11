import tempfile
import sys
import os

# Determine the project root directory (assuming utils.py is 2 levels down from root)
# fastapi_endpoint/backend/utils.py -> fastapi_endpoint/
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def get_saved_pdf_dir():
    """Returns the path to the directory for saving temporary PDF files."""
    # Keep PDFs in the system temp dir for now, or change as needed
    TEMP_SAVED_PDF_DIR = os.path.join(tempfile.gettempdir(), "saved_pdfs")
    os.makedirs(TEMP_SAVED_PDF_DIR, exist_ok=True)
    return TEMP_SAVED_PDF_DIR


def get_saved_excel_dir():
    """Returns the path to the directory for saving generated Excel files within the project."""
    # Use the determined project root + 'oupt' folder
    OUTPUT_EXCEL_DIR = os.path.join(PROJECT_ROOT_DIR, "oupt")
    # The directory creation will happen in save_to_excel, no need to create it here
    # os.makedirs(OUTPUT_EXCEL_DIR, exist_ok=True)
    return OUTPUT_EXCEL_DIR


def get_base_dir():
    """
    Determine the base directory of the application.
    - Use sys.executable if running as an executable
    - Use __file__ if running as a script

    """
    if hasattr(sys, "_MEIPASS"):
        print("MEIPASS : ", sys._MEIPASS)
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))
