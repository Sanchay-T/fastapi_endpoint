import json

import requests

analyze_url = "http://localhost:7500/analyze-statements/"
excel_url = "http://localhost:7500/excel-download/"

payload = {
    "bank_names": ["AXIS"],
    "pdf_paths": [
        "/Users/sanchaythalnerkar/fastapi_endpoint/backend/statements/axis.pdf"
    ],
    "passwords": [""],
    "start_date": ["04-04-2021"],
    "end_date": ["14-03-2022"],
    "ca_id": "ADFC_1234",
}

try:
    print("Sending request to:", analyze_url)
    response = requests.post(analyze_url, json=payload)
    print(f"Status Code: {response.status_code}")
    print("\nResponse:")
    analyze_result = response.json()
    print(json.dumps(analyze_result, indent=2))

    # Proceed to call Excel download endpoint if analysis succeeded
    if response.status_code == 200 and analyze_result.get("status") == "success":
        transaction_data = analyze_result.get("data") or []

        # Build name-number mapping
        ner_results = analyze_result.get("ner_results", {})
        names = ner_results.get("Name", [])
        acc_nums = ner_results.get("Acc Number", [])
        name_n_num = [
            {"Name": name, "Acc Number": acc} for name, acc in zip(names, acc_nums)
        ]

        excel_payload = {
            "transaction_data": transaction_data,
            "name_n_num": name_n_num,
            "case_name": "Demo_Case_1",
        }

        print("\nCalling excel-download endpoint…")
        excel_resp = requests.post(excel_url, json=excel_payload)
        print(f"Excel endpoint status: {excel_resp.status_code}")
        try:
            print("Response from excel-download:")
            print(json.dumps(excel_resp.json(), indent=2))
        except Exception:
            print(excel_resp.text)

except requests.exceptions.ConnectionError:
    print(
        "Error: Could not connect to the server. Make sure the FastAPI server is running on port 4000"
    )
except Exception as e:
    print(f"Error occurred: {str(e)}")
