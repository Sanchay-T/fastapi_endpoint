import requests
import json

url = "http://localhost:7500/analyze-statements/"

payload = {
    "bank_names": ["HDFC"],
    "pdf_paths": ["/Users/sanchaythalnerkar/CypherSol/accountant/banks/hdfc.pdf"],
    "passwords": [
        "",
    ],
    "start_date": ["26-01-2024"],
    "end_date": ["26-02-2024"],
    "ca_id": "HDFC",
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
