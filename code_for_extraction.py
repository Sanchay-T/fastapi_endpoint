import pandas as pd
import numpy as np
import io
from django.utils import timezone
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2 import PdfReader, PdfWriter, Transformation
from PyPDF2.generic import NameObject, NumberObject, RectangleObject
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import black
from datetime import datetime, timedelta
import torch
from PIL import Image
import pdfplumber
from torchvision import transforms
from huggingface_hub import hf_hub_download
from matplotlib.patches import Patch
from PIL import ImageDraw
from transformers import TableTransformerForObjectDetection
from tqdm.auto import tqdm
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import fitz  # PyMuPDF
from io import BytesIO
from old_bank_extractions import CustomStatement
import re
import uuid


class ExtractionOnly:
    def __init__(
        self, bank_name, pdf_path, pdf_password, CA_ID, saved_pdf_file_code="CA8104E"
    ):
        self.writer = None
        self.bank_names = bank_name
        self.pdf_paths = pdf_path
        self.pdf_passwords = pdf_password
        self.account_number = ""
        self.file_name = None
        self.CA_ID = CA_ID
        self.saved_pdf_file_code = saved_pdf_file_code
        self.customer = CustomStatement(bank_name, pdf_path, pdf_password, CA_ID)

    # def unlock_and_add_margins_to_pdf(self, pdf_path, pdf_password, timestamp, CA_ID):
    #     margin = 0.3
    #     os.makedirs("saved_pdf", exist_ok=True)
    #
    #     # Open the PDF using fitz (PyMuPDF)
    #     pdf_document = fitz.open(pdf_path)
    #
    #     # If the PDF is encrypted, try to unlock it
    #     if pdf_document.is_encrypted:
    #         if not pdf_document.authenticate(pdf_password):
    #             raise ValueError("Incorrect password. Unable to unlock the PDF.")
    #
    #     # Define the output path for the unlocked PDF
    #     unlocked_pdf_filename = f"{timestamp}-{CA_ID}.pdf"
    #     unlocked_pdf_path = os.path.join("saved_pdf", unlocked_pdf_filename)
    #
    #     # MARGIN CODE STARTS NOW: Convert margin from inches to points (1 inch = 72 points)
    #     margin_pts = margin * 72
    #
    #     # Iterate through each page, applying the margin adjustment
    #     for page_num in range(len(pdf_document)):
    #         page = pdf_document.load_page(page_num)
    #         rect = page.rect  # Get the original page size
    #
    #         # Expand the page size by adding margin around all sides
    #         new_rect = fitz.Rect(
    #             rect.x0 - margin_pts,  # Left
    #             # rect.y0 - margin_pts,  # Top
    #             rect.y0,  # Top
    #             rect.x1 + margin_pts,  # Right
    #             # rect.y1 + margin_pts  # Bottom
    #             rect.y1  # Bottom
    #         )
    #
    #         # Set the new page size (media box) to the expanded dimensions
    #         page.set_mediabox(new_rect)
    #
    #     # Save the modified PDF (unlocked and with margins)
    #     pdf_document.save(unlocked_pdf_path)
    #     pdf_document.close()
    #
    #     # Verify that the PDF contains text
    #     pdf_document = fitz.open(unlocked_pdf_path)
    #     first_page = pdf_document[0]
    #     try:
    #         text = first_page.get_text("text").strip()
    #         if not text:
    #             raise ValueError("The PDF is of image-only (non-text) format. Please upload a text PDF.")
    #     except Exception as e:
    #         raise ValueError("Error extracting text from the first page of the PDF.")
    #
    #     pdf_document.close()
    #     return unlocked_pdf_path

    def load_new_first_page_function(self, pdf_document):
        """
        Trims the first page of the PDF from the point where 'date' and 'balance' keywords
        are found together downwards. If not found on the first page, checks the second and third pages,
        then terminates if not found. Keeps some distance above the line containing the keywords.
        """
        date_pattern = re.compile(r"\b(date|value date|value)\b", re.IGNORECASE)
        balance_pattern = re.compile(r"\b(balance|total amount)\b", re.IGNORECASE)

        for page_num in range(
            min(4, len(pdf_document))
        ):  # Check up to the first three pages
            page = pdf_document[page_num]  # Load the page
            text_blocks = page.get_text("blocks")  # Extract text blocks

        date_coords = []
        balance_coords = []

        # Collect coordinates for 'date' and 'balance' keywords
        for block in text_blocks:
            y0 = block[1]
            text = block[4].strip()

            if date_pattern.search(text):
                date_coords.append((y0, block))
            if balance_pattern.search(text):
                balance_coords.append((y0, block))

        crop_y = None

        # Find the y-coordinate where both 'date' and 'balance' keywords are on the same row
        for date_y, date_block in date_coords:
            for balance_y, balance_block in balance_coords:
                if abs(date_y - balance_y) < 11:  # Small tolerance for alignment
                    crop_y = min(date_y, balance_y)
                    break
            if crop_y is not None:
                break

        if crop_y is not None:
            # Adjust crop_y to include some distance above the keywords
            buffer_distance = 30  # Points to keep above the line
            crop_y = max(page.mediabox.y0, crop_y - buffer_distance)

                # Define the cropping rectangle
                crop_rect = fitz.Rect(
                    page.mediabox.x0,  # Left boundary
                    crop_y,  # Top boundary (crop above this point with buffer)
                    page.mediabox.x1,  # Right boundary
                    page.mediabox.y1,  # Bottom boundary
                )

                # Create a new document for the cropped page
                cropped_doc = fitz.open()
                cropped_doc.insert_pdf(
                    pdf_document, from_page=page_num, to_page=page_num
                )
                cropped_page = cropped_doc[0]
                cropped_page.set_cropbox(crop_rect)

            return cropped_doc

    return None  # Terminate if keywords are not found on the first three pages

def load_first_page_into_memory(pdf_path):
    ca_id = "1234_temp"
    # Compile regex patterns for date and balance keywords for fast searching
    # date_pattern = re.compile(r'\b(date|value date|value)\b', re.IGNORECASE)
    # balance_pattern = re.compile(r'\b(balance|total amount)\b', re.IGNORECASE)

    try:
        # Open the PDF and determine which pages to check
        with fitz.open(pdf_path) as pdf_doc:
            # pages_to_check = [1, 0] if pdf_doc.page_count > 1 else [0]

            # Initialize variables for cropping decision
            crop_y = None
            # selected_page_num = 0  # Default to the first page
            #
            # # Iterate over the pages to check for keywords
            # for page_num in pages_to_check:
            #     page = pdf_doc[page_num]
            #     text_blocks = page.get_text("blocks")
            #
            #     # Collect coordinates of text blocks containing date or balance keywords
            #     date_coords = []
            #     balance_coords = []
            #     for block in text_blocks:
            #         y0 = block[1]
            #         text = block[4].strip()
            #
            #         if date_pattern.search(text):
            #             date_coords.append((y0, block))
            #         if balance_pattern.search(text):
            #             balance_coords.append((y0, block))
            #
            #     # Find the block that contains both date and balance keywords on the same x-axis
            #     for date_y, date_block in date_coords:
            #         for balance_y, balance_block in balance_coords:
            #             if abs(date_y - balance_y) < 5:  # Assuming a small tolerance to consider same row
            #                 crop_y = min(date_y, balance_y)
            #                 selected_page_num = page_num
            #                 break
            #         if crop_y is not None:
            #             break
            #
            #     # If no row with both date and balance keywords found, check for balance keywords first
            #     # if crop_y is None and balance_coords:
            #     #     crop_y = min(balance_coords, key=lambda x: x[0])[0]
            #     #     selected_page_num = page_num
            #
            #     # If a suitable crop_y is found, stop checking further pages
            #     if crop_y is not None:
            #         break

            # If no keywords were found, use the full height of the first page
            if crop_y is None:
                selected_page_num = 0
                page = pdf_doc[selected_page_num]
                crop_y = page.mediabox.y0  # Use the entire page without cropping

            # Define the cropping rectangle (or use the full page if no cropping is needed)
            crop_rect = fitz.Rect(
                page.mediabox.x0,  # Left boundary
                max(page.mediabox.y0, crop_y),  # Crop above this Y
                page.mediabox.x1,  # Right boundary
                page.mediabox.y1  # Top boundary
            )

            # Define output path for the cropped page
            output_page_path = os.path.join(
                os.path.dirname(pdf_path),
                f"{ca_id}_{selected_page_num + 1}_crop_{uuid.uuid4().hex}.pdf"
            )

            # Save only the selected page as a new PDF
            with fitz.open() as single_page_pdf:
                single_page_pdf.insert_pdf(pdf_doc, from_page=selected_page_num, to_page=selected_page_num)
                cropped_page = single_page_pdf[0]
                # Apply the crop to the saved page using the defined crop rectangle
                cropped_page.set_cropbox(crop_rect)
                single_page_pdf.save(output_page_path)

            return output_page_path

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def flatten_page_rotation(page):
    """
    - Read /Rotate from the page (90, 180, or 270).
    - Physically re-rotate (flatten) the page's content stream so
      we can set /Rotate=0 without changing the visual appearance.
    - Update page.mediabox so the rotated content is fully visible.
    """
    # Safely fetch the /Rotate entry (as a PdfObject).
    rotate_obj = page.get(NameObject("/Rotate"), NumberObject(0))
    rotation = int(rotate_obj)  # Convert to plain int

    if rotation == 0:
        return  # No rotation to flatten

    # Current page width/height
    w = float(page.mediabox.width)
    h = float(page.mediabox.height)

    transform = None

    if rotation == 90:
        # Flatten +90 by applying +270
        transform = Transformation().rotate(270).translate(tx=0, ty=w)
        # After rotation by +270°, the "width" and "height" swap
        # So the new page width should be old 'h', new page height old 'w'
        new_box = RectangleObject([0, 0, h, w])

    elif rotation == 180:
        # Flatten +180 by applying +180
        transform = Transformation().rotate(180).translate(tx=w, ty=h)
        # Rotating 180 doesn't swap width/height
        new_box = RectangleObject([0, 0, w, h])

    elif rotation == 270:
        # Flatten +270 by applying +90
        transform = Transformation().rotate(90).translate(tx=0, ty=h)
        # Rotation by +90 also swaps width/height
        new_box = RectangleObject([0, 0, h, w])

    # 1) Physically transform the page content
    page.add_transformation(transform)

    # 2) Update the MediaBox so the reoriented content isn't clipped
    page.mediabox = new_box

    # 3) Finally, set /Rotate to 0 so the viewer doesn't rotate the page
    page[NameObject("/Rotate")] = NumberObject(0)

def flatten_pdf_rotation(input_pdf_path, output_pdf_path):

    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        flatten_page_rotation(page)
        writer.add_page(page)

    with open(output_pdf_path, "wb") as f:
        writer.write(f)

    return output_pdf_path

def unlock_and_add_margins_to_pdf(pdf_path, pdf_password, timestamp, CA_ID):
    margin = 0.3
    os.makedirs(f"saved_pdf", exist_ok=True)

    try:
        # Open the PDF using fitz (PyMuPDF)
        pdf_document = fitz.open(pdf_path)

        # If the PDF is encrypted, try to unlock it
        if pdf_document.is_encrypted:
            if not pdf_document.authenticate(pdf_password):
                raise ValueError("Incorrect password. Unable to unlock the PDF.")

            # Define the output path for the unlocked PDF
            unlocked_pdf_filename = f"{timestamp}-{CA_ID}.pdf"
            unlocked_pdf_path = os.path.join(
                f"saved_pdf/pdf_{self.saved_pdf_file_code}", unlocked_pdf_filename
            )

        # MARGIN CODE STARTS NOW: Convert margin from inches to points (1 inch = 72 points)
        margin_pts = margin * 72

        # Process the first page for trimming if needed
        cropped_doc = load_new_first_page_function(pdf_document)

        if cropped_doc:
            # Create a new document combining the cropped first page and the remaining pages
            combined_doc = fitz.open()
            combined_doc.insert_pdf(cropped_doc)
            combined_doc.insert_pdf(pdf_document, from_page=1)

            # Save the combined document back to the original reference
            combined_path = "combined_temp.pdf"
            combined_doc.save(combined_path)
            pdf_document = fitz.open(combined_path)

        # Iterate through each page, applying the margin adjustment
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            rect = page.rect  # Get the original page size

                # Expand the page size by adding margin around all sides
                new_rect = fitz.Rect(
                    rect.x0 - margin_pts,  # Left
                    rect.y0,  # Top (unchanged for now)
                    rect.x1 + margin_pts,  # Right
                    rect.y1,  # Bottom (unchanged for now)
                )

            # Set the new page size (media box) to the expanded dimensions
            page.set_mediabox(new_rect)

        # Save the modified PDF (unlocked and with margins)
        pdf_document.save(unlocked_pdf_path)
        pdf_document.close()

            # Verify that the PDF contains text
            pdf_document = fitz.open(unlocked_pdf_path)
            first_page = pdf_document[0]
            text = first_page.get_text("text").strip()
            if not text:
                raise ValueError(
                    "The PDF is of image-only (non-text) format. Please upload a text PDF."
                )

        pdf_document.close()
        return unlocked_pdf_path

    except Exception as e:
        raise ValueError(f"An error occurred while processing the PDF: {e}")

        finally:
            # Ensure all temporary documents are closed and cleaned up
            if "cropped_doc" in locals() and cropped_doc is not None:
                cropped_doc.close()
            if "combined_doc" in locals() and combined_doc is not None:
                combined_doc.close()
            if os.path.exists("combined_temp.pdf"):
                os.remove("combined_temp.pdf")

##____________AFTER EXTRACTION (cleaning)_________________
def parse_date(date_string):
    formats_to_try = [
        "%d-%m-%Y",
        "%d %b %Y",
        "%Y-%m-%d",
        "%y-%m-%d",
        "%d %B %Y",
        "%d/%m/%Y",
        "%d-%b-%Y",
        "%d-%b-%y",
        "%B %d, %Y",
        "%d-%B-%Y",
        "%m/%d/%Y",
        "%d %b %y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d-%b- %Y",
        "%d/%b/%Y",
        "%d %b, %Y",
        "%d %b, %Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%d %b %Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%y-%m-%d %H:%M:%S",
        "%d %B %Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d-%b-%Y %H:%M:%S",
        "%d-%b-%y %H:%M:%S",
        "%B %d, %Y %H:%M:%S",
        "%d-%B-%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%d %b %y %H:%M:%S",
        "%d/%m/%y %H:%M:%S",
        "%d-%m-%y %H:%M:%S",
        "%d-%b- %Y %H:%M:%S",
        "%d/%b/%Y %H:%M:%S",
    ]

    for date_format in formats_to_try:
        try:
            return datetime.strptime(date_string, date_format).date()
        except ValueError:
            pass
    return None

def extract_date_col_from_df(df):
    date_col = []
    for column in df.columns:
        for index, value in df[column].head(60).items():
            parsed_date = parse_date(str(value))
            if parsed_date:
                date_col.append(column)
    d_col = list(set(date_col))
    if not d_col:
        df = df.applymap(lambda x: str(x).lower())
        # Iterate over each column number
        for column in df.columns:
            if any(df.iloc[:, column].str.contains("value date")):
                d_col.append(column)
    return d_col

    def find_desc_column(self, df, date_cols):
        # Convert all entries in the DataFrame to lowercase strings
        df = df.applymap(lambda x: str(x).lower())
        desc = []
        keywords = [
            "description",
            "escription",
            "scription",
            "descr",
            "descrip",
            "narration",
            "arration",
            "rration",
            "narrati",
            "narrat",
            "particular",
            "articular",
            "rticular",
            "particul",
            "detail",
            "remark",
        ]

    # Iterate over each row
    for index, row in df.head(60).iterrows():
        # Iterate over each column in the row
        for column_number, cell in enumerate(row):
            if column_number in date_cols:
                continue
            if any(keyword in cell for keyword in keywords):
                desc.append(column_number)
                break  # Move to the next row after finding a match

    return list(set(desc))

def find_debit_column(df, desc_col, date_col, bal_column):
    # Convert all entries in the DataFrame to lowercase strings
    df = df.applymap(lambda x: str(x).lower())
    deb = []
    keywords = ["withdraw", "debit", "dr amount", "withdr", "dr", "withdrawal"]

        # Iterate over each row
        for index, row in df.head(60).iterrows():
            # Iterate over each column in the row
            for column_number, cell in enumerate(row):
                if (
                    column_number in desc_col
                    or column_number in date_col
                    or column_number in bal_column
                ):
                    continue
                if any(keyword in cell for keyword in keywords):
                    deb.append(column_number)
                    break  # Move to the next row after finding a match

    # Return unique column indices
    return deb

def find_credit_column(df, desc_col, date_col, bal_column):
    # Convert all entries in the DataFrame to lowercase strings
    df = df.applymap(lambda x: str(x).lower())
    cred = []
    keywords = ["deposit", "credit", "cr amount", "depo", "cr"]

        # Iterate over each row
        for index, row in df.head(60).iterrows():
            # Iterate over each column in the row
            for column_number, cell in enumerate(row):
                if (
                    column_number in desc_col
                    or column_number in date_col
                    or column_number in bal_column
                ):
                    continue
                if any(keyword in cell for keyword in keywords):
                    cred.append(column_number)
                    break  # Move to the next row after finding a match

    # Return unique column indices
    return cred

def find_balance_column(df, desc_col, date_col):
    # Convert all entries in the DataFrame to lowercase strings
    desc_col = [desc_col[0]]
    df = df.applymap(lambda x: str(x).lower())
    bal = []
    keywords = ["balance", "total amount", "ance", "bal", "bala"]

    # Iterate over each row
    for index, row in df.head(60).iterrows():
        # Iterate over each column in the row
        for column_number, cell in enumerate(row):
            if column_number in desc_col or column_number in date_col:
                continue
            if any(keyword in cell for keyword in keywords):
                bal.append(column_number)
                break  # Move to the next row after finding a match

    # Return unique column indices
    return bal

    def check_date(self, df):
        df.dropna(subset=["Value Date"], inplace=True)
        if pd.to_datetime(df["Value Date"].iloc[-1], dayfirst=True) < pd.to_datetime(
            df["Value Date"].iloc[0], dayfirst=True
        ):
            new_df = df[::-1].reset_index(drop=True)
            print("found in reverse")
        else:
            new_df = df.copy()  # No reversal required
        return new_df

def cleaning(new_df):

    def try_parsing_date(text):
        formats_to_try = [
            "%d-%m-%Y",
            "%d %b %Y",
            "%Y-%m-%d",
            "%y-%m-%d",
            "%d %B %Y",
            "%d/%m/%Y",
            "%d-%b-%Y",
            "%d-%b-%y",
            "%B %d, %Y",
            "%d-%B-%Y",
            "%m/%d/%Y",
            "%d %b %y",
            "%d/%m/%y",
            "%d-%m-%y",
            "%d-%b- %Y",
            "%d/%b/%Y",
            "%d %b, %Y",
            "%d %b, %Y %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%d %b %Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%y-%m-%d %H:%M:%S",
            "%d %B %Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%d-%b-%Y %H:%M:%S",
            "%d-%b-%y %H:%M:%S",
            "%B %d, %Y %H:%M:%S",
            "%d-%B-%Y %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d %b %y %H:%M:%S",
            "%d/%m/%y %H:%M:%S",
            "%d-%m-%y %H:%M:%S",
            "%d-%b- %Y %H:%M:%S",
            "%d/%b/%Y %H:%M:%S",
        ]

        for fmt in formats_to_try:
            try:
                return pd.to_datetime(text, format=fmt)
            except ValueError:
                continue
        # try:
        #     return parser.parse(text)
        # except Exception as e:
        #     return pd.NaT

    df = new_df.drop_duplicates()
    df = df.reset_index(drop=True)
    # if 2 value dates eg : 02-Apr-23 (02-Apr-2023)
    df["Value Date"] = df["Value Date"].apply(
        lambda x: x.split("(")[0].strip() if isinstance(x, str) and "(" in x else x
    )
    df["Debit"] = df["Debit"].astype(str)
    df["Credit"] = df["Credit"].astype(str)
    df["Balance"] = df["Balance"].astype(str)

    df["Value Date"] = df["Value Date"].apply(try_parsing_date)
    df["Value Date"] = df["Value Date"].dt.strftime("%d-%m-%Y")
    df["Balance"] = df["Balance"].str.replace(r"Cr.|Dr.", "", regex=True)

    df["Balance"] = df["Balance"].str.replace(r"[^\d.-]+", "", regex=True)
    df["Debit"] = df["Debit"].str.replace(r"[^\d.-]+", "", regex=True)
    df["Credit"] = df["Credit"].str.replace(r"[^\d.-]+", "", regex=True)

        df["Debit"] = pd.to_numeric(df["Debit"], errors="coerce")
        df["Credit"] = pd.to_numeric(df["Credit"], errors="coerce")
        df["Balance"] = pd.to_numeric(df["Balance"], errors="coerce")
        # this is the code to merge lines that have been cut by separators
        # Iterate through the DataFrame and combine descriptions
        for i in range(1, len(df)):
            if pd.isna(df.loc[i, "Value Date"]):
                # Check if the description in the current row is NaN, replace it with an empty string if it is
                current_description = (
                    df.loc[i, "Description"]
                    if pd.notna(df.loc[i, "Description"])
                    else ""
                )
                # Also, ensure the previous row's description is a string
                df.at[i - 1, "Description"] = (
                    str(df.loc[i - 1, "Description"]) + " " + current_description
                )

        # Drop the rows where 'Value Date' is NaN (these rows are now redundant)
        df_cleaned = df.dropna(subset=["Value Date"]).reset_index(drop=True)
        # df = df_cleaned.drop_duplicates(subset="new_column").reset_index(drop=True)

        df = self.check_date(df)
        df = df[df["Balance"].notna() & (df["Balance"] != "")]
        df.dropna(subset=["Debit", "Credit"], how="all", inplace=True)
        idf = df[["Value Date", "Description", "Debit", "Credit", "Balance"]]

    return idf

    def credit_debit(
        self, df, description_column, date_column, bal_column, same_column
    ):
        def classify_column(column):
            case1_count = 0
            case2_count = 0

        # Vectorized processing: Convert entire column to uppercase and check for patterns
        values = df[column][2:].str.strip().str.upper()

        # Case 1: Count occurrences where the value is only "CR", "DR", "CR.", or "DR."
        case1_count = values.isin(
            ["CR", "DR", "CR.", "DR.", "Credit", "Debit", "cr", "dr", "Cr", "Dr", "C", "D", "C.", "D.", "credit",
             "debit"]).sum()

            # Case 2: Count occurrences where the value contains both a number and "CR" or "DR"
            case2_count = values.str.contains(r"\d+.*CR|DR", regex=True).sum()

        # Return the case based on counts
        if case1_count >= 5:
            return "case1"
        elif case2_count >= 5:
            return "case2"
        else:
            return "no_case"

    # Function to find the column with the keyword 'amount' (case-insensitive)
    def find_amount_column(df, desc_col, date_col, bal_column):
        df = df.applymap(lambda x: str(x).lower())
        amount_col = []
        keywords = ["amount"]

            # Iterate over each row
            for index, row in df.head(30).iterrows():
                # Iterate over each column in the row
                for column_number, cell in enumerate(row):
                    if (
                        column_number in desc_col
                        or column_number in date_col
                        or column_number in bal_column
                    ):
                        continue
                    if any(keyword in cell for keyword in keywords):
                        amount_col.append(column_number)
                        break
                        # Efficient search with list comprehension
            amount_columns = amount_col[0]
            return amount_columns

    # Since cred_column and deb_column are the same, we only need to classify the single column
    column_case = classify_column(same_column)

    if column_case == "case1":
        print("5 or more occurrences of case 1 found")

            # Find the column containing the keyword 'amount'
            amount_column = find_amount_column(
                df, description_column, date_column, bal_column
            )

            if amount_column:
                print(f"Found 'amount' column: {amount_column}")
                # Call the crdr_to_credit_debit_columns function with the found amount column
                new_df = self.crdr_to_credit_debit_columns(
                    df,
                    description_column,
                    date_column,
                    bal_column,
                    amount_column,
                    same_column,
                )
                return new_df
            else:
                print("No 'amount' column found")
                return None

    elif column_case == "case2":
        print("5 or more occurrences of case 2 found")

            # Vectorized split of numeric part and "CR/DR" part using regex
            df["A"] = (
                df[same_column]
                .str.extract(r"([\d,]+\.?\d*)")[0]
                .str.replace(",", "")
                .astype(float)
            )
            df["B"] = (
                df[same_column]
                .str.extract(r"(CR|DR)", flags=re.IGNORECASE)[0]
                .str.upper()
            )
            # Now call the crdr_to_credit_debit_columns function with new columns 'A' and 'B'
            new_df = self.crdr_to_credit_debit_columns(
                df, description_column, date_column, bal_column, "A", "B"
            )
            return new_df

    else:
        print("Fewer than 5 occurrences of either case")
        return None

    def crdr_to_credit_debit_columns(
        self,
        df,
        description_column,
        date_column,
        bal_column,
        amount_column,
        keyword_column,
    ):
        # Vectorized assignment of Debit and Credit columns
        df["Debit"] = np.where(
            df[keyword_column].str.contains(r"(?i)^DR\.?$", regex=True),
            df[amount_column],
            0,
        )
        df["Credit"] = np.where(
            df[keyword_column].str.contains(r"(?i)^CR\.?$", regex=True),
            df[amount_column],
            0,
        )

        # Construct the final DataFrame efficiently
        final_df = df[
            [date_column[0], description_column[0], "Debit", "Credit", bal_column[0]]
        ].copy()
        # Rename all columns in order
        final_df.columns = ["Value Date", "Description", "Debit", "Credit", "Balance"]

    return final_df

    def extract_text_from_pdf(self, unlocked_file_path):
        with fitz.open(unlocked_file_path) as pdf_doc:
            # Use a list comprehension for faster text concatenation
            text = "".join(
                [
                    pdf_doc.load_page(i).get_text("text")
                    for i in range(pdf_doc.page_count)
                ]
            )
        return text

    ##____________AFTER EXTRACTION (cleaning)_________________

##____________COLUMN SEPARATORS_______________________
def pdf_to_images(pdf_path):
    pdf_document = fitz.open(pdf_path)
    images = []

    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)

    return images

    def outputs_to_objects(self, outputs, img_size, id2label):
        m = outputs.logits.softmax(-1).max(-1)
        pred_labels = list(m.indices.detach().cpu().numpy())[0]
        pred_scores = list(m.values.detach().cpu().numpy())[0]
        pred_bboxes = outputs["pred_boxes"].detach().cpu()[0]

        # Convert bounding boxes from cxcywh to xyxy
        x_c, y_c, w, h = pred_bboxes.unbind(-1)
        pred_bboxes = torch.stack(
            [x_c - 0.5 * w, y_c - 0.5 * h, x_c + 0.5 * w, y_c + 0.5 * h], dim=-1
        )

        # Rescale bounding boxes to the image size
        scale_factors = torch.tensor(
            [img_size[0], img_size[1], img_size[0], img_size[1]], dtype=torch.float32
        )
        pred_bboxes = pred_bboxes * scale_factors

        objects = []
        for label, score, bbox in zip(pred_labels, pred_scores, pred_bboxes):
            class_label = id2label[int(label)]
            if class_label != "no object":
                objects.append(
                    {"label": class_label, "score": float(score), "bbox": bbox.tolist()}
                )

    return objects

    def detect_table_columns(self, image):
        structure_model = TableTransformerForObjectDetection.from_pretrained(
            "./local_model"
        )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    structure_model.to(device)

        structure_transform = transforms.Compose(
            [
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ]
        )

    img_size = image.size
    pixel_values = structure_transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = structure_model(pixel_values)

    structure_id2label = structure_model.config.id2label
    structure_id2label[len(structure_id2label)] = "no object"

        objects = self.outputs_to_objects(outputs, img_size, structure_id2label)
        columns = [obj for obj in objects if obj["label"] == "table column"]

    return columns

def plot_results(image, columns):
    plt.figure(figsize=(16, 10))
    plt.imshow(image)
    ax = plt.gca()

    for column in columns:
        score = column["score"]
        bbox = column["bbox"]
        label = column["label"]

            xmin, ymin, xmax, ymax = tuple(bbox)
            ax.add_patch(
                plt.Rectangle(
                    (xmin, ymin),
                    xmax - xmin,
                    ymax - ymin,
                    fill=False,
                    color="red",
                    linewidth=2,
                )
            )

            text = f"{label}: {score:0.2f}"
            ax.text(
                xmin,
                ymin,
                text,
                fontsize=12,
                color="white",
                bbox=dict(facecolor="red", alpha=0.5),
            )

        plt.axis("off")
        plt.show()

    def annotate_pdf(self, pdf_document, columns):
        rightmost_column = None
        rightmost_xmax = float("-inf")

        # First pass: Identify the rightmost column in one go
        for column in columns:
            bbox = column["bbox"]
            xmax = bbox[2]  # Extract xmax

        # Identify the rightmost column
        if xmax > rightmost_xmax:
            rightmost_xmax = xmax
            rightmost_column = column  # Update the rightmost column

        # Cache the coordinates for the rightmost column
        if rightmost_column:
            rightmost_bbox = rightmost_column["bbox"]
            xmin_rightmost = rightmost_bbox[0]  # xmin of the rightmost column
            xmax_rightmost = rightmost_bbox[2]  # xmax of the rightmost column

    # Process all pages
    list_of = []
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        page_height = page.rect.height  # Cache the page height

            # Second pass: Draw the lines for all columns
            for column in columns:
                bbox = column["bbox"]
                xmin = bbox[0]  # Extract xmin

            # Draw the left side line (xmin) for each column
            list_of.append(xmin)
            page.draw_line((xmin, 0), (xmin, page_height), color=(1, 0, 0), width=1)

            # Draw the bounding box for the rightmost column
            if rightmost_column:
                # Draw the left side (xmin) of the rightmost column
                page.draw_line(
                    (xmin_rightmost, 0),
                    (xmin_rightmost, page_height),
                    color=(1, 0, 0),
                    width=1,
                )
                # Draw the right side (xmax) of the rightmost column in blue
                page.draw_line(
                    (xmax_rightmost, 0),
                    (xmax_rightmost, page_height),
                    color=(0, 0, 1),
                    width=1,
                )

    lines = [x - 20 for x in list_of]
    return lines

def process_pdf_and_annotate(pdf_path, output_pdf):
    images = pdf_to_images(pdf_path)
    pdf_document = fitz.open(pdf_path)

    # Detect table columns only on the first page
    first_page_columns = detect_table_columns(images[0])

    # Display the first page with detected table columns
    # plot_results(images[0], first_page_columns)

    # Annotate all pages with the same table column coordinates
    llama = annotate_pdf(pdf_document, first_page_columns)
    print("llama", llama)

    # Save the annotated PDF
    pdf_document.save(output_pdf)

        return output_pdf, first_page_columns

    ##____________COLUMN SEPARATORS_______________________

    def clean_table(self, table):
        # Find the first row containing both 'date' and 'balance'/'total amount' or just 'balance'/'total amount'
        start_index = table.apply(
            lambda row: (
                row.astype(str).str.contains("date", case=False).any()
                and row.astype(str)
                .str.contains("balance|total amount", case=False)
                .any()
            )
            or row.astype(str).str.contains("balance|total amount", case=False).any(),
            axis=1,
        ).idxmax()

        df = table.loc[start_index:] if start_index is not None else pd.DataFrame()
        # Remove columns where all values are empty strings or whitespace
        cleaned_table = df.loc[
            :, ~(df.iloc[1:].apply(lambda col: (col.astype(str) == "None").all()))
        ]
        cleaned_table.columns = range(cleaned_table.shape[1])
        return cleaned_table

    # Functions for handling test cases and transformations
    def extract_dataframe_from_pdf(self, page_path, table_settings):
        pdf = pdfplumber.open(page_path)
        df_total = pd.DataFrame()
        # text = self.extract_text_from_pdf(unlocked_pdf_path)

    for i in range(len(pdf.pages)):
        p0 = pdf.pages[i]
        table = p0.extract_table(table_settings)
        # new_table = clean_table(pd.DataFrame(table))
        df_total = df_total._append(table, ignore_index=True)
        df_total.replace({r"\n": " "}, regex=True, inplace=True)
        print(f"on page:{i}")
    w = df_total.drop_duplicates()
    # rage_path = pdf_path.split(".")[0]
    # w.to_excel(f"raw_dataframe_{rage_path}.xlsx")
    return w

def extract_dataframe_from_full_pdf(pdf_path):
    pdf = pdfplumber.open(pdf_path)
    df_total = pd.DataFrame()
    # text = extract_text_from_pdf(unlocked_pdf_path)

    for i in range(len(pdf.pages)):
        p0 = pdf.pages[i]
        table = p0.extract_table()
        df_total = df_total._append(table, ignore_index=True)
        df_total.replace({r"\n": " "}, regex=True, inplace=True)
    w = df_total.drop_duplicates()

    return w

    def cut_the_datframe_from_headers(self, df):
        date_pattern = re.compile(r"\b(date|value date|value)\b", re.IGNORECASE)
        balance_pattern = re.compile(r"\b(balance|total amount)\b", re.IGNORECASE)

    crop_index = None

    # Iterate over the rows to check for keywords
    for index, row in df.iterrows():
        text = str(row).strip()
        if date_pattern.search(text) and balance_pattern.search(text):
            crop_index = index
            break

    # If no row with both date and balance keywords found, check for balance keywords first
    # if crop_index is None:
    #     for index, row in df.iterrows():
    #         text = str(row).strip()
    #         if balance_pattern.search(text):
    #             crop_index = index
    #             break

    # If a suitable crop_index is found, remove rows above it
    if crop_index is not None:
        df = df.loc[crop_index:].reset_index(drop=True)

    return df

def model_for_pdf(df):
    # Simulate cleaning or processing the dataframe
    # print(f"Modeling dataframe: {df}")
    print(df.head(10))
    df = cut_the_datframe_from_headers(df)
    date_column = [extract_date_col_from_df(df)[0]]

    print("Date Column is:", date_column)
    # numeric_columns_list = extract_numeric_col_from_df(df)
    # print(numeric_columns_list)
    description_column = find_desc_column(df, [f"{date_column}"])
    # description_column = [3]
    print("Description Column is:", description_column)

        bal_column = self.find_balance_column(df, description_column, date_column)
        bal_column = [bal_column[0]]
        # bal_column = [7]
        print("Balance Column is:", bal_column)

        deb_column = self.find_debit_column(
            df, description_column, date_column, bal_column
        )
        # deb_column = [4]
        print("Debit Column is:", deb_column)
        cred_column = self.find_credit_column(
            df, description_column, date_column, bal_column
        )
        # cred_column = [6]
        print("Credit Column is:", cred_column)

    lists = [date_column, description_column, deb_column, cred_column, bal_column]

    # Check and remove common element from "Credit Column" and "Debit Column"
    if len(lists[2]) == 2 and len(lists[3]) == 2:
        common_element = set(lists[2]).intersection(lists[3])
        if common_element:
            common_element = common_element.pop()
            lists[2].remove(common_element)
            lists[3].remove(common_element)

    new_lists = [
        list(dict.fromkeys(col)) if isinstance(col, list) else col for col in lists
    ]

    # Column names
    new_columns = ["Value Date", "Description", "Debit", "Credit", "Balance"]
    # Create new_df from new_lists
    selected_columns = [df.iloc[:, col[0]] for col in new_lists]
    new_df = pd.DataFrame(
        {new_columns[i]: selected_columns[i] for i in range(len(new_columns))}
    )

        if deb_column[0] == cred_column[0]:
            print("Credit and Debit are in the same column.")
            result = self.credit_debit(
                df, description_column, date_column, bal_column, deb_column[0]
            )
            final_df = self.cleaning(result)
        else:
            final_df = self.cleaning(new_df)

    print(final_df.head(10))
    return final_df, lists

def new_mode_for_pdf(df, lists):
    print(df.head(20))
    # Check and remove common element from "Credit Column" and "Debit Column"
    if len(lists[2]) == 2 and len(lists[3]) == 2:
        common_element = set(lists[2]).intersection(lists[3])
        if common_element:
            common_element = common_element.pop()
            lists[2].remove(common_element)
            lists[3].remove(common_element)

    new_lists = [
        list(dict.fromkeys(col)) if isinstance(col, list) else col for col in lists
    ]

    # Column names
    new_columns = ["Value Date", "Description", "Debit", "Credit", "Balance"]
    # Create new_df from new_lists
    selected_columns = [df.iloc[:, col[0]] for col in new_lists]
    new_df = pd.DataFrame(
        {new_columns[i]: selected_columns[i] for i in range(len(new_columns))}
    )

    if lists[2][0] == lists[3][0]:
        print("Credit and Debit are in the same column.")
        result = credit_debit(df, lists[1], lists[0], lists[4], lists[2][0])
        final_df = cleaning(result)
    else:
        final_df = cleaning(new_df)
    print("Extraction is Over !!!!!!!!!!!")
    return final_df

def old_bank_extraction(page_path):
    # Simulate old bank extraction process with the PDF page path
    print(f"Performing old bank extraction on {page_path}")
    pass

    def load_first_page_into_memory(self, pdf_path):
        ca_id = self.CA_ID
        # Compile regex patterns for date and balance keywords for fast searching
        # date_pattern = re.compile(r'\b(date|value date|value)\b', re.IGNORECASE)
        # balance_pattern = re.compile(r'\b(balance|total amount)\b', re.IGNORECASE)

        try:
            # Open the PDF and determine which pages to check
            with fitz.open(pdf_path) as pdf_doc:
                # pages_to_check = [1, 0] if pdf_doc.page_count > 1 else [0]

                # Initialize variables for cropping decision
                crop_y = None
                # selected_page_num = 0  # Default to the first page
                #
                # # Iterate over the pages to check for keywords
                # for page_num in pages_to_check:
                #     page = pdf_doc[page_num]
                #     text_blocks = page.get_text("blocks")
                #
                #     # Collect coordinates of text blocks containing date or balance keywords
                #     date_coords = []
                #     balance_coords = []
                #     for block in text_blocks:
                #         y0 = block[1]
                #         text = block[4].strip()
                #
                #         if date_pattern.search(text):
                #             date_coords.append((y0, block))
                #         if balance_pattern.search(text):
                #             balance_coords.append((y0, block))
                #
                #     # Find the block that contains both date and balance keywords on the same x-axis
                #     for date_y, date_block in date_coords:
                #         for balance_y, balance_block in balance_coords:
                #             if abs(date_y - balance_y) < 5:  # Assuming a small tolerance to consider same row
                #                 crop_y = min(date_y, balance_y)
                #                 selected_page_num = page_num
                #                 break
                #         if crop_y is not None:
                #             break
                #
                #     # If no row with both date and balance keywords found, check for balance keywords first
                #     # if crop_y is None and balance_coords:
                #     #     crop_y = min(balance_coords, key=lambda x: x[0])[0]
                #     #     selected_page_num = page_num
                #
                #     # If a suitable crop_y is found, stop checking further pages
                #     if crop_y is not None:
                #         break

                # If no keywords were found, use the full height of the first page
                if crop_y is None:
                    selected_page_num = 0
                    page = pdf_doc[selected_page_num]
                    crop_y = page.mediabox.y0  # Use the entire page without cropping

                # Define the cropping rectangle (or use the full page if no cropping is needed)
                crop_rect = fitz.Rect(
                    page.mediabox.x0,  # Left boundary
                    max(page.mediabox.y0, crop_y),  # Crop above this Y
                    page.mediabox.x1,  # Right boundary
                    page.mediabox.y1,  # Top boundary
                )

                # Define output path for the cropped page
                output_page_path = os.path.join(
                    os.path.dirname(pdf_path),
                    f"{self.CA_ID}_page{selected_page_num+1}_{uuid.uuid4().hex}_crop.pdf",
                )

                # Save only the selected page as a new PDF
                with fitz.open() as single_page_pdf:
                    single_page_pdf.insert_pdf(
                        pdf_doc, from_page=selected_page_num, to_page=selected_page_num
                    )
                    cropped_page = single_page_pdf[0]
                    # Apply the crop to the saved page using the defined crop rectangle
                    cropped_page.set_cropbox(crop_rect)
                    single_page_pdf.save(output_page_path)

                return output_page_path

        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def add_row_separators_in_memory(self, input_pdf_path):
        line_threshold = 5
        output_pdf_path = os.path.join(
            f"saved_pdf/pdf_{self.saved_pdf_file_code}",
            f"{self.CA_ID}_with_rows_added_{uuid.uuid4().hex}.pdf",
        )
        doc = fitz.open(input_pdf_path)
        for page in doc:
            words = page.get_text("words")
            # Ensure words are sorted by their top coordinate (y0)
            words.sort(key=lambda w: w[1])

            if not words:
                # No words on this page, just continue
                continue

            lines = []
            current_line = []
            current_line_y = None

            # Group words into lines
            for w in words:
                x0, y0, x1, y1, text, bno, lno, wno = w
                if current_line_y is None:
                    current_line = [w]
                    current_line_y = y0
                else:
                    # Check if the word belongs to the same line
                    if abs(y0 - current_line_y) < line_threshold:
                        current_line.append(w)
                    else:
                        lines.append(current_line)
                        current_line = [w]
                        current_line_y = y0
            if current_line:
                lines.append(current_line)

            # Draw lines
            shape = page.new_shape()
            # Set line properties before drawing
            shape.line_width = 1  # Increase if you need a thicker line
            shape.stroke_color = (0, 0, 0)  # Black color

            page_width = page.rect.width
            for line in lines:
                line_top = min(word[1] for word in line)
                # Draw a horizontal line at line_top
                shape.draw_line((0, line_top), (page_width, line_top))

            # Optional: Draw a line near the bottom of the page
            shape.draw_line((0, 2.83), (page_width, 2.83))

            # Finish and commit the drawing
            shape.finish()
            shape.commit()

        # Save the modified PDF
        print(output_pdf_path)
        doc.save(output_pdf_path)
        # doc.close()
        return output_pdf_path

    # Function to add column separators (optimized to avoid file I/O)
    def add_column_separators_in_memory(self, page):
        # timestamp, CA_ID = "1234", "1234"
        # Simulate adding column separators to the in-memory page
        output_pdf, coordinates = self.process_pdf_and_annotate(
            page,
            os.path.join(
                f"saved_pdf/pdf_{self.saved_pdf_file_code}",
                f"{self.CA_ID}_{uuid.uuid4().hex}_only_columns_add.pdf",
            ),
        )
        return output_pdf, coordinates  # Return the modified page and coordinates

    def add_column_separators_with_coordinates(self, pdf_path, coordinates):
        pdf_document = fitz.open(pdf_path)
        self.annotate_pdf(pdf_document, coordinates)
        processed_pdf_path = os.path.join(
            f"saved_pdf/pdf_{self.saved_pdf_file_code}",
            f"{self.CA_ID}_{uuid.uuid4().hex}_columns_adding_with_coordinates.pdf",
        )
        pdf_document.save(processed_pdf_path)
        return processed_pdf_path

    # Optimized test case A
    def run_test_case_A(self, page):
        try:
            df = self.extract_dataframe_from_pdf(
                page,
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "edge_min_length": 20,
                },
            )
            model_df, lists = self.model_for_pdf(df)  # Process the DataFrame
            return model_df, lists  # No coordinates for Test Case A
        except Exception as e:
            print(f"Test Case A failed: {e}")
            return None, None

    # Optimized test case B
    def run_test_case_B(self, page_with_rows_added):
        try:
            df = self.extract_dataframe_from_pdf(
                page_with_rows_added,
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "text",
                    "edge_min_length": 40,
                    "intersection_x_tolerance": 120,
                },
            )
            model_df, lists = self.model_for_pdf(df)
            return model_df, lists  # No coordinates for Test Case B
        except Exception as e:
            print(f"Test Case B failed: {e}")
            return None, None

    # Optimized test case C
    def run_test_case_C(self, page_with_columns_added):
        try:
            df = self.extract_dataframe_from_pdf(
                page_with_columns_added,
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "edge_min_length": 40,
                },
            )
            model_df, lists = self.model_for_pdf(df)
            return model_df, lists  # Return coordinates for Test Case C
        except Exception as e:
            print(f"Test Case C failed: {e}")
            return None, None

    # Optimized test case D
    def run_test_case_D(self, page_with_rows_n_columns_added):
        try:
            # final_page = add_column_separators_with_coordinates(page_with_rows, coordinates)  # Use the coordinates from Test Case C
            df = self.extract_dataframe_from_pdf(
                page_with_rows_n_columns_added,
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "text",
                    "edge_min_length": 40,
                    "intersection_x_tolerance": 120,
                },
            )
            model_df, lists = self.model_for_pdf(df)
            return model_df, lists  # Use coordinates from Test Case C
        except Exception as e:
            print(f"Test Case D failed: {e}")
            return None, None

def run_test_case_E(bank, pdf_path, timestamp, CA_ID):
    lists = 0
    df = pd.DataFrame()
    # df = customer.custom_extraction(bank, pdf_path, 0, timestamp)
    return df, lists

def process_pdf_with_test_cases(pdf_path):
    print("Starting Test Case Processing...")

    # Load the first page of the PDF into memory once
    page = load_first_page_into_memory(pdf_path)

    # Test Case A
    model_df_A, lists = run_test_case_A(page)
    if model_df_A is not None:
        print("Test Case A passed")
        return ["A", 0, lists, 0]  # Test Case A passed

    # Test Case B
    # page_with_rows = add_row_separators_in_memory(page)
    model_df_B, lists = run_test_case_B(page)
    if model_df_B is not None:
        print("Test Case B passed")
        return ["B", 0, lists, 0]  # Test Case B passed

    # Test Case C
    page_with_columns, coordinates_C, explicit_lines = add_column_separators_in_memory(page)
    model_df_C, lists = run_test_case_C(page_with_columns, explicit_lines)
    if model_df_C is not None:
        print("Test Case C passed")
        return ["C", coordinates_C, lists, explicit_lines]  # Test Case C passed

        # Test Case D
        # page_with_rows = self.add_row_separators_in_memory(page)
        page_with_columns_n_rows = self.add_column_separators_with_coordinates(
            page, coordinates_C
        )
        model_df_D, lists = self.run_test_case_D(page_with_columns_n_rows)
        if model_df_D is not None:
            print("Test Case D passed")
            return ["D", coordinates_C, lists]  # Test Case D passed
        else:
            # Test Case E
            lists = 0
            print("Test Case E begins : MOVING TOWARDS CUSTOM EXTRACTION")
            return ["E", 0, lists]

    def run_test_output_on_whole_pdf(
        self, list_a, pdf_in_saved_pdf, bank_name, timestamp, CA_ID
    ):
        test_case = list_a[0]
        coordinates_C = list_a[1]
        lists_of_columns = list_a[2]

        if test_case == "A":
            # Run `extract_dataframe_from_pdf()` for Test Case A
            print("Running extract_dataframe_from_pdf() for Test Case A")
            df = self.extract_dataframe_from_pdf(
                pdf_in_saved_pdf,
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "edge_min_length": 30,
                },
            )
            model_df = self.new_mode_for_pdf(df, lists_of_columns)

        return model_df, None

        elif test_case == "B":
            # Run `row_separators_addition()` for Test Case B
            print("Running row_separators_addition() for Test Case B")
            # pdf_in_rows_saved_pdf = self.add_row_separators_in_memory(pdf_in_saved_pdf)
            df = self.extract_dataframe_from_pdf(
                pdf_in_saved_pdf,
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "text",
                    "edge_min_length": 40,
                    "intersection_x_tolerance": 120,
                },
            )
            model_df = self.new_mode_for_pdf(df, lists_of_columns)
            return model_df

        elif test_case == "C":
            # Run `add_column_separators_with_coordinates()` for Test Case C
            print(
                f"Running add_column_separators_with_coordinates() for Test Case C with coordinates {coordinates_C}"
            )
            pdf_in_columns_saved_pdf = self.add_column_separators_with_coordinates(
                pdf_in_saved_pdf, coordinates_C
            )
            df = self.extract_dataframe_from_pdf(
                pdf_in_columns_saved_pdf,
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "edge_min_length": 40,
                },
            )
            model_df = self.new_mode_for_pdf(df, lists_of_columns)
            return model_df

        elif test_case == "D":
            # First add row separators, then column separators with coordinates for Test Case D
            print(
                "Running add_row_separators and add_column_separators_with_coordinates() for Test Case D"
            )
            # pdf_in_rows_saved_pdf = self.add_row_separators_in_memory(pdf_in_saved_pdf)
            pdf_in_columns_saved_pdf = self.add_column_separators_with_coordinates(
                pdf_in_saved_pdf, coordinates_C
            )
            df = self.extract_dataframe_from_pdf(
                pdf_in_columns_saved_pdf,
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "text",
                    "edge_min_length": 40,
                    "intersection_x_tolerance": 120,
                },
            )
            model_df = self.new_mode_for_pdf(df, lists_of_columns)
            return model_df

    else:
        # Handle Test Case E
        print("Running specific handling for Test Case E with extracted dataframe")
        df = pd.DataFrame()
        return df, explicit_lines


    # Main function to run test cases with optimizations
    def extract_with_test_cases(self, bank_name, pdf_path, pdf_password, CA_ID):
        timestamp = int("1234567")
        pdf_in_saved_pdf = self.unlock_and_add_margins_to_pdf(
            pdf_path, pdf_password, timestamp, CA_ID
        )
        list_test = self.process_pdf_with_test_cases(pdf_in_saved_pdf)
        text = self.extract_text_from_pdf(pdf_in_saved_pdf)
        idf = self.run_test_output_on_whole_pdf(
            list_test, pdf_in_saved_pdf, bank_name, timestamp, CA_ID
        )
        return idf, text
