#!/bin/bash

# Get the directory where the script is located (project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Define the path to the API directory and activation script
API_DIR="${SCRIPT_DIR}/api"
ACTIVATE_SCRIPT="${SCRIPT_DIR}/env/bin/activate" # Corrected path to env in root
MANAGE_PY="${API_DIR}/manage.py"

# Check if activation script exists
if [ ! -f "${ACTIVATE_SCRIPT}" ]; then
    echo "Error: Activation script not found at ${ACTIVATE_SCRIPT}"
    echo "Ensure the virtual environment exists in the project root directory ('${SCRIPT_DIR}/env')."
    exit 1
fi

# Check if manage.py exists
if [ ! -f "${MANAGE_PY}" ]; then
    echo "Error: manage.py not found at ${MANAGE_PY}"
    exit 1
fi

echo "Activating virtual environment from ${SCRIPT_DIR}/env..."
source "${ACTIVATE_SCRIPT}"

echo "Changing directory to ${API_DIR}..."
cd "${API_DIR}" || exit

echo "Starting Django development server with SSL support..."
python manage.py runserver_plus --cert-file local-cert.crt --key-file local-cert.key 0.0.0.0:8000

# Optional: Deactivate environment when server stops
# echo "Deactivating environment..."
# deactivate 