import json
import math
import os
import re
import sys
import time  # Import time for benchmarking
import warnings  # To suppress warnings

import requests
import urllib3  # To suppress specific warnings
from rich.box import DOUBLE, ROUNDED
from rich.console import Console  # Import rich for better output
from rich.highlighter import ReprHighlighter
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

try:
    # Try importing PyPDF2 for page counting
    from PyPDF2 import PdfReader

    HAS_PDF_READER = True
except ImportError:
    # If not available, we'll handle gracefully
    HAS_PDF_READER = False

# --- Suppress specific warnings ---
warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)

# --- Initialize Rich Console ---
console = Console(
    highlight=False
)  # Disable syntax highlighting to ensure colors display
highlighter = ReprHighlighter()

# --- Check for color support ---
USE_COLORS = True
try:
    USE_COLORS = console.color_system is not None
except:
    USE_COLORS = False


# --- Helper function for consistent spacing ---
def print_spacer(count=1):
    """Print empty lines for better visual separation"""
    for _ in range(count):
        console.print()


# --- Helper function for section headers ---
def print_section_header(title, style="bold blue on white"):
    """Print a prominent section header"""
    console.print()
    console.rule(characters="=", style="bold white")
    console.print(f"[{style}] {title.upper()} [/{style}]", justify="center")
    console.rule(characters="=", style="bold white")
    console.print()


# --- Helper function for subsection headers ---
def print_subsection(title, style="cyan"):
    """Print a subsection divider"""
    console.print()
    console.rule(f"[bold {style}]{title}[/]", style=style)
    console.print()


# --- Configuration ---
BASE_URL = "https://127.0.0.1:8000/api/v1"  # Django API URL

# --- Placeholder Credentials ---
# NOTE: Replace with actual test user credentials or use environment variables
TEST_USERNAME = "sanchay"
TEST_PASSWORD = "sanchay"

# Base path for statements
BASE_STATEMENTS_PATH = (
    "/Users/sanchaythalnerkar/fastapi_endpoint/api/statement_analyzer/statements"
)

# Statement details (Multiple PDFs with their respective configurations)
PDF_PATHS = [
    f"{BASE_STATEMENTS_PATH}/AXIS BANK PASSWORD - SHAK895229130.pdf",
    f"{BASE_STATEMENTS_PATH}/Narpat.pdf",
]
BANK_NAMES = ["AXIS BANK", "HDFC"]
PASSWORDS = ["SHAK895229130", None]  # None for no password
START_DATES = ["01-04-2021", "02-04-2022"]
END_DATES = ["15-03-2022", "01-04-2023"]
CA_ID = "django_script_run_1"  # Example Client/Case ID
CASE_NAME_FOR_EXCEL = (
    "bank_statement_analysis_from_django_script"  # Desired Excel filename base
)

# --- Helper Functions ---


def get_auth_token(base_url, username, password):
    """Authenticates with the Django API and returns an access token."""
    token_url = f"{base_url}/auth/token/"

    print_subsection("AUTHENTICATION REQUEST")

    # Display request details in a table
    auth_table = Table(show_header=False, box=ROUNDED, border_style="blue")
    auth_table.add_column("Property", style="dim")
    auth_table.add_column("Value", style="cyan")
    auth_table.add_row("Endpoint", token_url)
    auth_table.add_row("Method", "POST")
    auth_table.add_row("Username", username)
    auth_table.add_row("Password", "*" * len(password))
    console.print(auth_table)
    print_spacer()

    # Use progress display during authentication
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Authenticating..."),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Authenticating", total=None)

        # Start timing and make the request
        start_time = time.perf_counter()
        access_token = None
        try:
            response = requests.post(
                token_url,
                data={"username": username, "password": password},
                verify=False,  # Added for self-signed certs
                timeout=30,
            )
            end_time = time.perf_counter()
            duration = end_time - start_time

        except requests.exceptions.RequestException as e:
            end_time = time.perf_counter()
            duration = end_time - start_time

            # Display error in a clear panel
            print_spacer()
            console.print(
                Panel(
                    f"[bold red]CONNECTION ERROR[/bold red]\n\n{str(e)}",
                    title="Authentication Failed",
                    border_style="red",
                    expand=False,
                )
            )
            print_spacer()
            console.print(f"[bold red]Time elapsed:[/] {duration:.2f} seconds")
            return None

    print_spacer()

    # Process and display the authentication result
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get("access")

        if access_token:
            # Display truncated token for security
            display_token = (
                f"{access_token[:8]}...{access_token[-5:]}" if access_token else "N/A"
            )

            # Show success panel with token info
            console.print(
                Panel(
                    f"[bold green]AUTHENTICATION SUCCESSFUL[/]\n\n[dim]Token:[/] {display_token}",
                    title="🔐 Authorization",
                    border_style="green",
                    expand=False,
                )
            )
            print_spacer()
            console.print(f"[bold green]Time elapsed:[/] {duration:.2f} seconds")
        else:
            console.print(
                Panel(
                    "[bold yellow]No access token found in response[/]",
                    title="⚠️ Authentication Issue",
                    border_style="yellow",
                    expand=False,
                )
            )
            print_spacer()
            console.print(f"[bold yellow]Time elapsed:[/] {duration:.2f} seconds")
    else:
        # Display failure panel with status code
        console.print(
            Panel(
                f"[bold red]Authentication failed with status code: {response.status_code}[/]\n\n{response.text}",
                title="❌ Authentication Error",
                border_style="red",
                expand=False,
            )
        )
        print_spacer()
        console.print(f"[bold red]Time elapsed:[/] {duration:.2f} seconds")
        access_token = None

    return access_token


def check_health(base_url):
    """Checks the /health endpoint of the server."""
    health_url = f"{base_url}/health/"

    print_subsection("HEALTH CHECK REQUEST")

    # Show health check details
    table = Table(show_header=False, box=ROUNDED, border_style="blue")
    table.add_column("Property", style="dim")
    table.add_column("Value", style="cyan")
    table.add_row("Endpoint", health_url)
    table.add_row("Method", "GET")
    console.print(table)
    print_spacer()

    # Show progress during health check
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Checking server health..."),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Checking", total=100)

        # Start timing and make the request
        start_time = time.perf_counter()
        is_healthy = False

        try:
            # Update progress
            progress.update(task, completed=30)
            response = requests.get(health_url, timeout=10, verify=False)
            # Update progress
            progress.update(task, completed=90)

            end_time = time.perf_counter()
            duration = end_time - start_time

            # Complete the progress
            progress.update(task, completed=100)

        except requests.exceptions.RequestException as e:
            # Complete the progress but show error
            progress.update(task, completed=100)
            end_time = time.perf_counter()
            duration = end_time - start_time

            print_spacer()
            console.print(
                Panel(
                    f"[bold red]CONNECTION ERROR[/]\n\n{str(e)}",
                    title="Health Check Failed",
                    border_style="red",
                    box=DOUBLE,
                    title_align="center",
                    padding=(2, 5),
                )
            )
            print_spacer()
            console.print(f"[bold red]⏱️ Time elapsed:[/] {duration:.2f} seconds")
            return False

    print_spacer()

    # Display health check results
    if response.status_code == 200:
        # Create a nicely formatted panel for health status
        console.print(
            Panel(
                f"[bold green]SERVER IS HEALTHY[/]\n\n{json.dumps(response.json(), indent=2)}",
                title="✅ Health Status",
                border_style="green",
                box=DOUBLE,
                title_align="center",
                padding=(1, 5),
            )
        )
        print_spacer()
        console.print(f"[bold green]⏱️ Time elapsed:[/] {duration:.2f} seconds")
        is_healthy = True
    else:
        console.print(
            Panel(
                f"[bold yellow]Health check failed with status code: {response.status_code}[/]\n\n{response.text}",
                title="⚠️ Health Warning",
                border_style="yellow",
                box=DOUBLE,
                title_align="center",
                padding=(1, 5),
            )
        )
        print_spacer()
        console.print(f"[bold yellow]⏱️ Time elapsed:[/] {duration:.2f} seconds")

    return is_healthy


def analyze_statements(
    base_url,
    access_token,
    bank_names,
    pdf_paths,
    passwords,
    start_dates,
    end_dates,
    ca_id,
):
    """Sends request to /analyze-statements/ endpoint with authentication."""
    analyze_url = f"{base_url}/analyze-statements/"

    print_subsection("ANALYSIS REQUEST DETAILS")

    # Display detailed API request information
    # Only truncate token for display, not for actual request
    display_token = (
        f"{access_token[:8]}...{access_token[-5:]}" if access_token else "N/A"
    )
    headers = {
        "Authorization": f"Bearer {access_token}"
    }  # Use full token for actual request

    # Handle None passwords - convert to empty string or skip as needed
    processed_passwords = []
    for pwd in passwords:
        if pwd is not None:
            processed_passwords.append(pwd)
        else:
            # Add "NO_PASSWORD" as a placeholder for documents without passwords
            processed_passwords.append("NO_PASSWORD")

    payload = {
        "bank_names": bank_names,
        "pdf_paths": pdf_paths,
        "passwords": processed_passwords,
        "start_date": start_dates,
        "end_date": end_dates,
        "ca_id": ca_id,
    }

    # Create a clean display of the PDF paths and their passwords
    pdf_info = []
    for i, pdf in enumerate(pdf_paths):
        pdf_name = os.path.basename(pdf)
        password_display = (
            "None" if passwords[i] is None else "***" if passwords[i] else "Empty"
        )
        pdf_info.append(f"• {pdf_name} (Password: {password_display})")

    # Show analysis details in a table
    console.print(
        Panel(
            "\n".join(pdf_info),
            title=f"Analyzing {len(pdf_paths)} PDF Statement(s)",
            border_style="blue",
            expand=False,
        )
    )
    # Display token being used (truncated for security)
    console.print(f"[dim]Using Authorization:[/] Bearer {display_token}")
    print_spacer()

    # Use progress display during analysis (potentially long operation)
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Analyzing statements..."),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing", total=None)

        # Start timing and make the request
        start_time = time.perf_counter()
        analysis_result = None
        try:
            response = requests.post(
                analyze_url, headers=headers, json=payload, timeout=300, verify=False
            )
            end_time = time.perf_counter()
            duration = end_time - start_time

        except requests.exceptions.Timeout:
            end_time = time.perf_counter()
            duration = end_time - start_time

            print_spacer()
            console.print(
                Panel(
                    "[bold yellow]The analysis request timed out.\nThe process might still be running in the background.[/]",
                    title="⚠️ Timeout",
                    border_style="yellow",
                    expand=False,
                )
            )
            print_spacer()
            console.print(f"[bold yellow]Time elapsed:[/] {duration:.2f} seconds")
            return None

        except requests.exceptions.RequestException as e:
            end_time = time.perf_counter()
            duration = end_time - start_time

            print_spacer()
            console.print(
                Panel(
                    f"[bold red]CONNECTION ERROR[/]\n\n{str(e)}",
                    title="❌ Analysis Request Failed",
                    border_style="red",
                    expand=False,
                )
            )
            print_spacer()
            console.print(f"[bold red]Time elapsed:[/] {duration:.2f} seconds")
            return None

    print_spacer()

    # Process and display the analysis results based on response status
    console.print(
        f"[dim]Status Code:[/] [bold {'green' if response.status_code == 200 else 'red'}]{response.status_code}[/]"
    )
    print_spacer()

    if response.status_code == 200:
        try:
            analysis_result = response.json()
            status = analysis_result.get("status", "unknown")

            if status == "success":
                # Success panel
                console.print(
                    Panel(
                        "[bold green]ANALYSIS COMPLETED SUCCESSFULLY[/]",
                        title="✅ Bank Statement Analysis",
                        border_style="green",
                        expand=False,
                    )
                )

                # Try to create a summary of what was found
                data = analysis_result.get("data", {})

                # Create summary table for transactions found
                summary_table = Table(
                    box=ROUNDED, title="📊 Analysis Results", border_style="green"
                )
                summary_table.add_column("Category", style="cyan")
                summary_table.add_column("Count", style="green")

                # Add document processing information if available
                if "pdf_stats" in analysis_result:
                    pdf_stats = analysis_result.get("pdf_stats", {})
                    if isinstance(pdf_stats, dict):
                        for pdf_name, stats in pdf_stats.items():
                            if isinstance(stats, dict) and "page_count" in stats:
                                summary_table.add_row(
                                    f"Pages in {os.path.basename(pdf_name)}",
                                    str(stats["page_count"]),
                                )
                        # Add total pages if available
                        total_pages = sum(
                            stats.get("page_count", 0)
                            for stats in pdf_stats.values()
                            if isinstance(stats, dict)
                        )
                        if total_pages > 0:
                            summary_table.add_row(
                                "Total Pages Processed", str(total_pages)
                            )
                    elif isinstance(pdf_stats, list):
                        # Handle alternative format if stats is a list
                        total_pages = sum(
                            item.get("page_count", 0)
                            for item in pdf_stats
                            if isinstance(item, dict)
                        )
                        if total_pages > 0:
                            summary_table.add_row(
                                "Total Pages Processed", str(total_pages)
                            )

                # If no PDF stats available, add PDFs processed count
                if "pdf_stats" not in analysis_result:
                    summary_table.add_row("PDFs Processed", str(len(pdf_paths)))
                    console.print(
                        "[dim]Note: Detailed page count information not available from API[/]"
                    )

                # Add transaction info if available
                if "Transactions" in data and isinstance(data["Transactions"], list):
                    summary_table.add_row(
                        "Transactions Found", str(len(data["Transactions"]))
                    )
                elif "Payment Voucher" in data and "Receipt Voucher" in data:
                    payment_count = len(data.get("Payment Voucher", []))
                    receipt_count = len(data.get("Receipt Voucher", []))
                    summary_table.add_row("Payment Vouchers", str(payment_count))
                    summary_table.add_row("Receipt Vouchers", str(receipt_count))
                    summary_table.add_row(
                        "Total Records", str(payment_count + receipt_count)
                    )

                # Add account details if available
                ner_results = analysis_result.get("ner_results", {})
                if "Name" in ner_results and ner_results["Name"]:
                    summary_table.add_row(
                        "Account Names", str(len(ner_results["Name"]))
                    )
                if "Acc Number" in ner_results and ner_results["Acc Number"]:
                    summary_table.add_row(
                        "Account Numbers", str(len(ner_results["Acc Number"]))
                    )

                console.print(summary_table)

            else:
                # Non-success status
                console.print(
                    Panel(
                        f"[bold yellow]Analysis completed with status: {status}[/]\n\n"
                        f"Message: {analysis_result.get('message', 'No message provided')}",
                        title="⚠️ Analysis Status",
                        border_style="yellow",
                        expand=False,
                    )
                )
        except Exception as e:
            console.print(
                Panel(
                    f"[bold yellow]Error parsing analysis response:[/]\n\n{str(e)}",
                    title="⚠️ Response Parsing Error",
                    border_style="yellow",
                    expand=False,
                )
            )
            analysis_result = None

    elif response.status_code in (401, 403):
        # Authentication/Authorization error
        console.print(
            Panel(
                f"[bold red]AUTHORIZATION ERROR[/]\n\n{response.text}",
                title="🔒 Access Denied",
                border_style="red",
                expand=False,
            )
        )
    elif response.status_code == 422:
        # Validation error
        try:
            validation_details = json.dumps(response.json(), indent=2)
        except:
            validation_details = response.text

        console.print(
            Panel(
                f"[bold red]VALIDATION ERROR[/]\n\n{validation_details}",
                title="⚠️ Invalid Request",
                border_style="red",
                expand=False,
            )
        )
    elif response.status_code == 500:
        # Server error
        console.print(
            Panel(
                f"[bold red]SERVER ERROR[/]\n\n{response.text}",
                title="💥 Internal Server Error",
                border_style="red",
                expand=False,
            )
        )
    else:
        # Unknown error
        console.print(
            Panel(
                f"[bold red]REQUEST FAILED[/]\n\nStatus: {response.status_code}\n\n{response.text}",
                title="❌ Analysis Failed",
                border_style="red",
                expand=False,
            )
        )

    print_spacer()
    console.print(
        f"[bold {'green' if response.status_code == 200 else 'red'}]Time elapsed:[/] {duration:.2f} seconds"
    )

    return analysis_result


def format_ner_results(ner_dict):
    """Formats NER results into the list format required by /excel-download/."""
    formatted_list = []
    # Adjust keys based on what Django view returns, assuming 'Name' and 'Acc Number'
    names = ner_dict.get("Name", [])
    acc_numbers = ner_dict.get("Acc Number", [])

    # Assuming names and acc_numbers lists are parallel
    num_entries = min(len(names), len(acc_numbers))

    for i in range(num_entries):
        formatted_list.append({"Name": names[i], "Acc Number": acc_numbers[i]})
    return formatted_list


def download_excel(
    base_url, access_token, transaction_data, name_n_num_data, case_name
):
    """Sends request to /excel-download/ endpoint with authentication."""
    excel_url = f"{base_url}/excel-download/"

    print_subsection("EXCEL GENERATION REQUEST")

    # Display transaction statistics
    transaction_count = len(transaction_data) if transaction_data else 0

    # Create a summary table of what will be included in the Excel file
    excel_table = Table(show_header=False, box=ROUNDED, border_style="blue")
    excel_table.add_column("Parameter", style="dim")
    excel_table.add_column("Value", style="cyan")
    excel_table.add_row("Endpoint", excel_url)
    excel_table.add_row("Method", "POST")
    excel_table.add_row("Case Name", case_name)
    excel_table.add_row("Transaction Count", str(transaction_count))
    excel_table.add_row(
        "Account Details", str(len(name_n_num_data) if name_n_num_data else 0)
    )

    # Display Excel generation parameters
    console.print(excel_table)
    print_spacer()

    # Use progress display during excel generation
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Generating Excel file..."),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Generating", total=None)

        # Start timing and make the request
        headers = {"Authorization": f"Bearer {access_token}"}
        payload = {
            "transaction_data": transaction_data,
            "name_n_num": name_n_num_data,
            "case_name": case_name,
        }

        start_time = time.perf_counter()
        local_filepath = None
        try:
            response = requests.post(
                excel_url, headers=headers, json=payload, timeout=120, verify=False
            )
            end_time = time.perf_counter()
            duration = end_time - start_time

        except requests.exceptions.Timeout:
            end_time = time.perf_counter()
            duration = end_time - start_time

            print_spacer()
            console.print(
                Panel(
                    "[bold yellow]The Excel generation request timed out.[/]",
                    title="⚠️ Request Timeout",
                    border_style="yellow",
                    expand=False,
                )
            )
            print_spacer()
            console.print(f"[bold yellow]Time elapsed:[/] {duration:.2f} seconds")
            return None

        except requests.exceptions.RequestException as e:
            end_time = time.perf_counter()
            duration = end_time - start_time

            print_spacer()
            console.print(
                Panel(
                    f"[bold red]CONNECTION ERROR[/]\n\n{str(e)}",
                    title="❌ Excel Generation Failed",
                    border_style="red",
                    expand=False,
                )
            )
            print_spacer()
            console.print(f"[bold red]Time elapsed:[/] {duration:.2f} seconds")
            return None

    print_spacer()

    # Process and display the results based on response status
    console.print(
        f"[dim]Status Code:[/] [bold {'green' if response.status_code == 200 else 'red'}]{response.status_code}[/]"
    )
    print_spacer()

    if (
        response.status_code == 200
        and response.headers.get("Content-Type")
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        # Excel file successfully generated - save it
        content_disposition = response.headers.get("Content-Disposition")
        filename = "downloaded_statement_analysis.xlsx"
        if content_disposition:
            filename_match = re.search(r'filename="?([^"\n]+)"?', content_disposition)
            if filename_match:
                filename = filename_match.group(1)

        local_filepath = os.path.join(".", filename)

        # Write the file to disk
        with open(local_filepath, "wb") as f:
            f.write(response.content)

        # Get file size for display
        file_size = os.path.getsize(local_filepath)
        file_size_formatted = (
            f"{file_size / 1024:.1f} KB"
            if file_size < 1024 * 1024
            else f"{file_size / (1024*1024):.1f} MB"
        )

        # Success panel with file details
        console.print(
            Panel(
                f"[bold green]EXCEL FILE GENERATED SUCCESSFULLY[/]\n\n"
                f"[bold]Filename:[/] {filename}\n"
                f"[bold]Size:[/] {file_size_formatted}\n"
                f"[bold]Path:[/] {local_filepath}",
                title="✅ Excel File Generated",
                border_style="green",
                expand=False,
            )
        )
    elif response.status_code in (401, 403):
        # Authentication/Authorization error
        console.print(
            Panel(
                f"[bold red]AUTHORIZATION ERROR[/]\n\n{response.text}",
                title="🔒 Access Denied",
                border_style="red",
                expand=False,
            )
        )
    elif response.status_code == 422:
        # Validation error
        try:
            validation_details = json.dumps(response.json(), indent=2)
        except:
            validation_details = response.text

        console.print(
            Panel(
                f"[bold red]VALIDATION ERROR[/]\n\n{validation_details}",
                title="⚠️ Invalid Request Format",
                border_style="red",
                expand=False,
            )
        )
    elif response.status_code == 500:
        # Server error
        console.print(
            Panel(
                f"[bold red]SERVER ERROR[/]\n\n{response.text}",
                title="💥 Internal Server Error",
                border_style="red",
                expand=False,
            )
        )
    else:
        # Unknown error
        console.print(
            Panel(
                f"[bold red]REQUEST FAILED[/]\n\nStatus: {response.status_code}\n\n{response.text}",
                title="❌ Excel Generation Failed",
                border_style="red",
                expand=False,
            )
        )

    print_spacer()
    console.print(
        f"[bold {'green' if response.status_code == 200 else 'red'}]Time elapsed:[/] {duration:.2f} seconds"
    )

    return local_filepath


def sanitize_data_for_json(data):
    """Recursively replace NaN, Infinity, -Infinity in dicts/lists with None."""
    if isinstance(data, dict):
        return {k: sanitize_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data_for_json(item) for item in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None  # Replace non-compliant floats with None (JSON null)
        return data
    else:
        return data


# --- Function to count PDF pages ---
def count_pdf_pages(pdf_path):
    """Count the number of pages in a PDF file."""
    if not HAS_PDF_READER:
        return "Unknown (PyPDF2 not installed)"

    try:
        with open(pdf_path, "rb") as file:
            pdf = PdfReader(file)
            return len(pdf.pages)
    except Exception as e:
        return f"Error: {str(e)}"


# --- Main Execution Flow ---
if __name__ == "__main__":
    overall_start_time = time.perf_counter()

    # Clear screen for a clean start
    if os.name == "nt":  # For Windows
        os.system("cls")
    else:  # For macOS and Linux
        os.system("clear")

    # Print big header with extra space around it
    print_section_header("BANK STATEMENT ANALYSIS WORKFLOW")

    # Initialize variables
    pdf_page_counts = {}
    total_pages = 0

    # --- PDF Information ---
    print_section_header("PDF INFORMATION", "bold white on green")

    # Check if PyPDF2 is available
    if not HAS_PDF_READER:
        console.print(
            "[yellow]Warning: PyPDF2 library not installed. Cannot count PDF pages.[/]"
        )
        console.print("[dim]To install: pip install PyPDF2[/]")
        print_spacer()

    # Display PDF files with their details
    pdf_details = Table(
        title="📑 PDF Files to Process", box=ROUNDED, border_style="green"
    )
    pdf_details.add_column("File", style="cyan")
    pdf_details.add_column("Bank", style="cyan")
    pdf_details.add_column("Password", style="dim")
    pdf_details.add_column("Date Range", style="cyan")
    pdf_details.add_column("Pages", style="green")

    # Count pages in each PDF file
    for i, pdf in enumerate(PDF_PATHS):
        if pdf and os.path.exists(pdf):
            pdf_name = os.path.basename(pdf)

            # Count pages
            page_count = count_pdf_pages(pdf)
            page_display = str(page_count) if isinstance(page_count, int) else "Unknown"

            if isinstance(page_count, int):
                pdf_page_counts[pdf] = page_count
                total_pages += page_count

            # Password display
            pwd_display = "Protected" if PASSWORDS[i] else "None"

            # Add to table
            pdf_details.add_row(
                pdf_name,
                BANK_NAMES[i],
                pwd_display,
                f"{START_DATES[i]} to {END_DATES[i]}",
                page_display,
            )
        else:
            console.print(f"[red]✗[/] PDF file not found at path: {pdf}")

    console.print(pdf_details)

    if total_pages > 0:
        console.print(
            f"[bold green]Total pages across all PDFs:[/] [cyan]{total_pages}[/]"
        )

    print_spacer(2)

    # --- Step 1: Authentication ---
    print_section_header("STEP 1: AUTHENTICATION", "bold white on blue")
    auth_start = time.perf_counter()
    access_token = get_auth_token(BASE_URL, TEST_USERNAME, TEST_PASSWORD)
    auth_end = time.perf_counter()
    auth_step_duration = auth_end - auth_start

    if not access_token:
        console.print(
            Panel(
                "[bold red]AUTHENTICATION FAILED. THE WORKFLOW CANNOT CONTINUE WITHOUT A VALID TOKEN.[/]",
                title="❌ FATAL ERROR",
                border_style="red",
                expand=False,
            )
        )
        print_spacer(2)
        sys.exit(1)

    print_spacer(2)

    # --- Step 2: Statement Analysis ---
    print_section_header("STEP 2: STATEMENT ANALYSIS", "bold white on blue")

    # Prepare data for analysis request
    bank_names_list = BANK_NAMES
    pdf_paths_list = PDF_PATHS
    passwords_list = PASSWORDS
    start_dates_list = START_DATES
    end_dates_list = END_DATES

    # Display request parameters table
    request_table = Table(show_header=False, box=ROUNDED, border_style="blue")
    request_table.add_column("Parameter", style="dim")
    request_table.add_column("Value", style="cyan")
    request_table.add_row("Bank Name", ", ".join(bank_names_list))
    request_table.add_row(
        "PDF File", ", ".join([os.path.basename(p) for p in pdf_paths_list])
    )
    request_table.add_row(
        "Date Range", f"{', '.join(start_dates_list)} to {', '.join(end_dates_list)}"
    )
    request_table.add_row("CA ID", CA_ID)
    if total_pages > 0:
        request_table.add_row("PDF Pages", str(total_pages))
    console.print(Panel(request_table, title="Request Parameters", border_style="blue"))
    print_spacer()

    analysis_start = time.perf_counter()
    analysis_result = analyze_statements(
        BASE_URL,
        access_token,
        bank_names_list,
        pdf_paths_list,
        passwords_list,
        start_dates_list,
        end_dates_list,
        CA_ID,
    )
    analysis_end = time.perf_counter()
    analysis_step_duration = analysis_end - analysis_start

    print_spacer(2)

    excel_file_path = None
    excel_step_duration = 0.0
    transaction_list = []

    # --- Step 3: Excel Generation (conditional) ---
    if analysis_result and analysis_result.get("status") == "success":
        print_section_header("STEP 3: EXCEL GENERATION", "bold white on blue")

        excel_step_start = time.perf_counter()

        # Extract data for Excel generation
        print_subsection("DATA EXTRACTION")
        processed_data_sheets_raw = analysis_result.get("data", {})
        ner_data_dict = analysis_result.get("ner_results", {})

        processed_data_sheets = (
            processed_data_sheets_raw
            if isinstance(processed_data_sheets_raw, dict)
            else {}
        )

        # Process transactions based on available data
        if "Transactions" in processed_data_sheets:
            transaction_list = processed_data_sheets["Transactions"]
            console.print(
                "[green]✓[/] Found [bold]Transactions[/] sheet with "
                f"[bold cyan]{len(transaction_list)}[/] records"
            )
        elif (
            "Payment Voucher" in processed_data_sheets
            and "Receipt Voucher" in processed_data_sheets
        ):
            payment_list = processed_data_sheets.get("Payment Voucher", [])
            receipt_list = processed_data_sheets.get("Receipt Voucher", [])

            console.print(
                "[green]✓[/] Found [bold]Payment Voucher[/] sheet with "
                f"[bold cyan]{len(payment_list)}[/] records"
            )
            console.print(
                "[green]✓[/] Found [bold]Receipt Voucher[/] sheet with "
                f"[bold cyan]{len(receipt_list)}[/] records"
            )

            transaction_list = payment_list + receipt_list
            console.print(
                f"[green]✓[/] Combined [bold cyan]{len(transaction_list)}[/] total transactions"
            )
        else:
            available_keys = (
                list(processed_data_sheets.keys()) if processed_data_sheets else []
            )

            console.print(
                Panel(
                    "[bold yellow]No transaction data found in the analysis results.[/]\n\n"
                    "Expected to find either:\n"
                    "- 'Transactions' sheet\n"
                    "- Both 'Payment Voucher' and 'Receipt Voucher' sheets\n\n"
                    f"Available sheets: {', '.join(available_keys) if available_keys else 'None'}",
                    title="⚠️ Missing Transaction Data",
                    border_style="yellow",
                    expand=False,
                )
            )

        # Process name and account number data
        name_n_num_list = format_ner_results(ner_data_dict)

        if not transaction_list:
            console.print(
                "[bold yellow]Extracted transaction list is empty. Cannot proceed to Excel download.[/]"
            )
        elif not name_n_num_list:
            console.print(
                "[yellow]Extracted Name/Number list is empty, but proceeding anyway.[/]"
            )

        # Generate Excel if transactions were found
        if transaction_list:
            print_spacer()
            print_subsection("DATA PREPARATION")
            console.print(
                "[blue]→[/] Sanitizing transaction data for JSON compatibility..."
            )
            sanitized_transactions = sanitize_data_for_json(transaction_list)
            sanitized_name_num = sanitize_data_for_json(name_n_num_list)
            console.print(
                f"[green]✓[/] Sanitized [bold cyan]{len(sanitized_transactions)}[/] transactions"
            )

            print_spacer()
            print_subsection("EXCEL DOWNLOAD")
            excel_file_path = download_excel(
                BASE_URL,
                access_token,
                sanitized_transactions,
                sanitized_name_num,
                CASE_NAME_FOR_EXCEL,
            )
        else:
            console.print(
                Panel(
                    "[bold yellow]No transactions found to process. Skipping Excel generation.[/]",
                    title="⚠️ Excel Generation Skipped",
                    border_style="yellow",
                    expand=False,
                )
            )
            excel_file_path = None

        excel_step_end = time.perf_counter()
        excel_step_duration = excel_step_end - excel_step_start

    elif analysis_result:
        console.print(
            Panel(
                f"[bold yellow]Analysis completed but status was not 'success'.[/]\n\n"
                f"Status: {analysis_result.get('status', 'N/A')}\n"
                f"Message: {analysis_result.get('message', 'No message provided')}\n\n"
                f"PDFs not extracted: {analysis_result.get('pdf_paths_not_extracted', 'N/A')}",
                title="⚠️ Analysis Issues",
                border_style="yellow",
                expand=False,
            )
        )
    else:
        console.print(
            Panel(
                "[bold red]Analysis request failed or returned no result.[/]",
                title="❌ Analysis Failed",
                border_style="red",
                expand=False,
            )
        )

    print_spacer(2)

    # --- Final Summary ---
    print_section_header("WORKFLOW SUMMARY", "bold white on magenta")

    overall_end_time = time.perf_counter()
    total_duration = overall_end_time - overall_start_time

    # Create summary table
    summary_table = Table(title="⏱️ Timing Summary", box=ROUNDED, border_style="magenta")
    summary_table.add_column("Step", style="bold white")
    summary_table.add_column("Duration", style="cyan")
    summary_table.add_column("Status", style="bold")

    # Add rows for each step
    summary_table.add_row(
        "Authentication",
        f"{auth_step_duration:.2f}s",
        "[green]✓ Success[/]" if access_token else "[red]✗ Failed[/]",
    )

    summary_table.add_row(
        "Statement Analysis",
        f"{analysis_step_duration:.2f}s",
        "[green]✓ Success[/]"
        if analysis_result and analysis_result.get("status") == "success"
        else "[red]✗ Failed[/]"
        if not analysis_result
        else "[yellow]⚠ Partial[/]",
    )

    # Only include Excel generation step if it was attempted
    if analysis_result and analysis_result.get("status") == "success":
        summary_table.add_row(
            "Excel Generation",
            f"{excel_step_duration:.2f}s",
            "[green]✓ Success[/]"
            if excel_file_path
            else "[yellow]⚠ Skipped[/]"
            if not transaction_list
            else "[red]✗ Failed[/]",
        )

    # Add total row
    summary_table.add_row("[bold]TOTAL TIME[/]", f"[bold]{total_duration:.2f}s[/]", "")

    # Print summary table
    console.print(summary_table)
    print_spacer(2)

    # Display final outcome panel
    if excel_file_path:
        # Full success
        # Get transaction count for summary display
        transaction_count = 0
        if analysis_result and isinstance(analysis_result.get("data"), dict):
            data = analysis_result.get("data", {})
            if "Transactions" in data and isinstance(data["Transactions"], list):
                transaction_count = len(data["Transactions"])
            elif "Payment Voucher" in data and "Receipt Voucher" in data:
                payment_count = len(data.get("Payment Voucher", []))
                receipt_count = len(data.get("Receipt Voucher", []))
                transaction_count = payment_count + receipt_count

        # Create success message with processing stats
        success_message = (
            f"[bold green]WORKFLOW COMPLETED SUCCESSFULLY[/]\n\n"
            f"Bank statements from [bold]{', '.join(BANK_NAMES)}[/] were processed successfully.\n\n"
            f"[bold]Processing Statistics:[/]\n"
            f"• PDFs Processed: [cyan]{len(pdf_paths_list)}[/]\n"
        )

        # Add page count if available
        if total_pages > 0:
            success_message += f"• Total PDF Pages: [cyan]{total_pages}[/]\n"

        # Add transaction count
        success_message += f"• Transactions Found: [cyan]{transaction_count}[/]\n\n"
        success_message += (
            f"The Excel reports have been saved to:\n"
            f"[bold cyan]{excel_file_path}[/]"
        )

        console.print(
            Panel(
                success_message, title="✅ SUCCESS", border_style="green", expand=False
            )
        )
    elif analysis_result and analysis_result.get("status") == "success":
        # Partial success (analysis worked but no Excel)
        console.print(
            Panel(
                f"[bold yellow]WORKFLOW PARTIALLY COMPLETED[/]\n\n"
                f"Bank statements from [bold]{', '.join(BANK_NAMES)}[/] were analyzed successfully, "
                f"but no Excel reports were generated because no transactions were found.",
                title="⚠️ PARTIAL SUCCESS",
                border_style="yellow",
                expand=False,
            )
        )
    else:
        # Failure
        console.print(
            Panel(
                f"[bold red]WORKFLOW FAILED[/]\n\n"
                f"The analysis of bank statements from [bold]{', '.join(BANK_NAMES)}[/] was not successful.",
                title="❌ FAILURE",
                border_style="red",
                expand=False,
            )
        )

    print_spacer(2)
    print_section_header("END OF WORKFLOW")
