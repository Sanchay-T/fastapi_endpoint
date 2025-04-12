import requests
import json
import os
import re
import math
import sys

# --- Configuration ---
BASE_URL = "https://127.0.0.1:8000/api/v1"  # Django API URL

# --- Placeholder Credentials ---
# NOTE: Replace with actual test user credentials or use environment variables
TEST_USERNAME = "sanchay"
TEST_PASSWORD = "sanchay"

# Statement details (Update these as needed)
PDF_PATH = "/Users/sanchaythalnerkar/fastapi_endpoint/api/statement_analyzer/statements/AXIS BANK PASSWORD - SHAK895229130.pdf"
BANK_NAME = "AXIS BANK"
PASSWORD = "SHAK895229130"  # Assumed from filename
START_DATE = "01-04-2021"
END_DATE = "15-03-2022"
CA_ID = "django_script_run_1"  # Example Client/Case ID
CASE_NAME_FOR_EXCEL = (
    "axis_statement_analysis_from_django_script"  # Desired Excel filename base
)

# --- Helper Functions ---


def get_auth_token(base_url, username, password):
    """Authenticates with the Django API and returns an access token."""
    token_url = f"{base_url}/auth/token/"
    print(f"[*] Attempting authentication at {token_url}...")
    try:
        response = requests.post(
            token_url,
            data={"username": username, "password": password},
            verify=False,  # Added for self-signed certs
            timeout=30,
        )
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access")
            if access_token:
                print("[+] Authentication successful. Received access token.")
                return access_token
            else:
                print(
                    "[!] Authentication succeeded but no access token found in response."
                )
                return None
        else:
            print(
                f"[!] Authentication failed. Status: {response.status_code}, Response: {response.text}"
            )
            return None
    except requests.exceptions.RequestException as e:
        print(f"[!] Connection error during authentication: {e}")
        return None


def check_health(base_url):
    """Checks the /health endpoint of the server."""
    # Adjust health check URL if necessary (Django health check might be different)
    health_url = (
        f"{base_url}/health/"  # Assuming Django health check is at /api/v1/health/
    )
    print(f"[*] Checking server health at {health_url}...")
    try:
        response = requests.get(
            health_url, timeout=10, verify=False
        )  # Added verify=False for HTTPS
        if response.status_code == 200:
            print(f"[+] Server is healthy: {response.json()}")
            return True
        else:
            print(
                f"[!] Server health check failed. Status: {response.status_code}, Response: {response.text}"
            )
            return False
    except requests.exceptions.RequestException as e:
        print(f"[!] Connection error during health check: {e}")
        return False


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
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "bank_names": bank_names,
        "pdf_paths": pdf_paths,
        "passwords": passwords,
        "start_date": start_dates,
        "end_date": end_dates,
        "ca_id": ca_id,
    }
    print(f"[*] Sending analysis request to {analyze_url}...")
    try:
        response = requests.post(
            analyze_url, headers=headers, json=payload, timeout=300, verify=False
        )
        print(f"[*] Analysis response status code: {response.status_code}")

        if response.status_code == 200:
            print("[+] Analysis request successful.")
            return response.json()
        elif response.status_code == 401 or response.status_code == 403:
            print(
                f"[!] Authorization Error ({response.status_code}). Check token or permissions."
            )
            print(f"Server Response: {response.text}")
            return None
        elif response.status_code == 422:
            print(f"[!] Validation Error (422) from server. Check payload structure.")
            print(f"Server Response:\n{json.dumps(response.json(), indent=2)}")
            return None
        elif response.status_code == 500:
            print(f"[!] Internal Server Error (500).")
            try:
                error_detail = response.json().get("detail", response.text)
                print(f"Server Error Detail: {error_detail}")
            except json.JSONDecodeError:
                print(f"Server Response Text: {response.text}")
            return None
        else:
            print(f"[!] Analysis request failed. Status: {response.status_code}")
            print(f"Server Response: {response.text}")
            return None
    except requests.exceptions.Timeout:
        print(
            "[!] Analysis request timed out. The process might be running in the background on the server."
        )
        return None
    except requests.exceptions.RequestException as e:
        print(f"[!] Connection error during analysis request: {e}")
        return None


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
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "transaction_data": transaction_data,
        "name_n_num": name_n_num_data,
        "case_name": case_name,
    }
    print(f"[*] Sending Excel download request to {excel_url}...")
    try:
        response = requests.post(
            excel_url, headers=headers, json=payload, timeout=120, verify=False
        )
        print(f"[*] Excel download response status code: {response.status_code}")

        if (
            response.status_code == 200
            and response.headers.get("Content-Type")
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ):
            print("[+] Excel download request successful.")
            content_disposition = response.headers.get("Content-Disposition")
            filename = "downloaded_statement_analysis.xlsx"
            if content_disposition:
                filename_match = re.search(
                    r'filename="?([^"\n]+)"?', content_disposition
                )
                if filename_match:
                    filename = filename_match.group(1)
            local_filepath = os.path.join(".", filename)
            with open(local_filepath, "wb") as f:
                f.write(response.content)
            print(f"[+] Excel file saved locally as: {local_filepath}")
            return local_filepath
        elif response.status_code == 401 or response.status_code == 403:
            print(
                f"[!] Authorization Error ({response.status_code}). Check token or permissions."
            )
            print(f"Server Response: {response.text}")
            return None
        elif response.status_code == 422:
            print(f"[!] Validation Error (422) from server. Check payload structure.")
            try:
                print(f"Server Response:\n{json.dumps(response.json(), indent=2)}")
            except json.JSONDecodeError:
                print(f"Server Response (non-JSON): {response.text}")
            return None
        elif response.status_code == 500:
            print(f"[!] Internal Server Error (500) during Excel generation.")
            try:
                error_detail = response.json().get("detail", response.text)
                print(f"Server Error Detail: {error_detail}")
            except json.JSONDecodeError:
                print(f"Server Response Text: {response.text}")
            return None
        else:
            print(f"[!] Excel download request failed. Status: {response.status_code}")
            print(f"Server Response: {response.text}")
            return None
    except requests.exceptions.Timeout:
        print("[!] Excel download request timed out.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[!] Connection error during Excel download request: {e}")
        return None


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


# --- Main Execution Flow ---
if __name__ == "__main__":
    print("--- Starting Bank Statement Analysis Workflow ---")

    access_token = get_auth_token(BASE_URL, TEST_USERNAME, TEST_PASSWORD)

    if not access_token:
        print("[!] Failed to authenticate. Exiting.")
        sys.exit(1)

    # Optional: Check health (might require auth depending on Django settings)
    # check_health(BASE_URL)

    # Prepare data for analysis request
    bank_names_list = [BANK_NAME]
    pdf_paths_list = [PDF_PATH]
    passwords_list = [PASSWORD] if PASSWORD else []
    start_dates_list = [START_DATE]
    end_dates_list = [END_DATE]

    analysis_result = analyze_statements(
        BASE_URL,
        access_token,  # Pass the token
        bank_names_list,
        pdf_paths_list,
        passwords_list,
        start_dates_list,
        end_dates_list,
        CA_ID,
    )

    if analysis_result and analysis_result.get("status") == "success":
        print("[*] Extracting data for Excel generation...")
        processed_data_sheets_raw = analysis_result.get("data", {})
        ner_data_dict = analysis_result.get("ner_results", {})
        processed_data_sheets = (
            processed_data_sheets_raw
            if isinstance(processed_data_sheets_raw, dict)
            else {}
        )

        transaction_list = []
        if "Transactions" in processed_data_sheets:
            transaction_list = processed_data_sheets["Transactions"]
            print("[i] Found 'Transactions' sheet.")
        elif (
            "Payment Voucher" in processed_data_sheets
            and "Receipt Voucher" in processed_data_sheets
        ):
            print("[i] Combining 'Payment Voucher' and 'Receipt Voucher'.")
            transaction_list.extend(processed_data_sheets.get("Payment Voucher", []))
            transaction_list.extend(processed_data_sheets.get("Receipt Voucher", []))
        else:
            print(
                "[!] Could not find a suitable transaction sheet ('Transactions', or Payment/Receipt Vouchers) in the analysis response."
            )
            # Print available keys for debugging
            available_keys = (
                list(processed_data_sheets.keys()) if processed_data_sheets else "None"
            )
            print(
                f"[DEBUG] Available keys in analysis_result['data']: {available_keys}"
            )

        name_n_num_list = format_ner_results(ner_data_dict)

        if not transaction_list:
            print(
                "[!] Extracted transaction list is empty. Cannot proceed to Excel download."
            )
        elif not name_n_num_list:
            print("[!] Extracted Name/Number list is empty, but proceeding anyway.")

        if transaction_list:
            print("[*] Sanitizing transaction data for JSON compatibility...")
            sanitized_transactions = sanitize_data_for_json(transaction_list)
            sanitized_name_num = sanitize_data_for_json(name_n_num_list)

            excel_file_path = download_excel(
                BASE_URL,
                access_token,  # Pass the token
                sanitized_transactions,
                sanitized_name_num,
                CASE_NAME_FOR_EXCEL,
            )

            if excel_file_path:
                print(f"\n[*** SUCCESS ***]")
                print(f"[>] Excel file download simulated successfully.")
                print(f"[>] File saved locally at: {excel_file_path}")
            else:
                print(
                    "\n[!] Failed to generate or download Excel file."
                )  # Modified message
        else:
            print("\n[!] Skipping Excel generation due to missing transaction data.")

    elif analysis_result:
        print(
            f"\n[!] Analysis completed but status was not 'success'. Status: {analysis_result.get('status')}, Message: {analysis_result.get('message')}"
        )
        if analysis_result.get("pdf_paths_not_extracted"):
            print(
                f"[!] PDFs not extracted: {analysis_result['pdf_paths_not_extracted']}"
            )
    else:
        print("\n[!] Analysis request failed or returned no result.")

    print("\n--- Workflow Finished ---")
