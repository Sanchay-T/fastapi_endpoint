import requests
import json

url = "http://localhost:7500/analyze-statements/"

payload = {
    "bank_names": ["AXIS", "ABC", "SCB"],
    "pdf_paths": ["Copy of Axis bank AC statement (1).pdf", "V V Mehta (3).pdf", "eStatement241216210303209444230.pdf"],
    "passwords": ["","",""],
    "start_date": ["01-04-2000", "01-04-2000", "01-04-2000"],
    "end_date": ["31-03-2025", "31-03-2025", "31-03-2025"],
    "ca_id": "ADFC_1234",
}

try:
    print("Sending request to:", url)
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print("\nResponse:")
    print(json.dumps(response.json(), indent=2))

except requests.exceptions.ConnectionError:
    print(
        "Error: Could not connect to the server. Make sure the FastAPI server is running on port 4000"
    )
except Exception as e:
    print(f"Error occurred: {str(e)}")
