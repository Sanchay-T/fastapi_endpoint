#!/bin/bash

# Get the directory where the script is located (project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Define the path to the activation script (env is in root)
ACTIVATE_SCRIPT="${SCRIPT_DIR}/env/bin/activate"

# Check if activation script exists
if [ ! -f "${ACTIVATE_SCRIPT}" ]; then
    echo "Error: Activation script not found at ${ACTIVATE_SCRIPT}"
    echo "Ensure the virtual environment exists in the project root directory ('${SCRIPT_DIR}/env')."
    exit 1
fi

echo "Virtual environment found at: ${ACTIVATE_SCRIPT}"
echo "Run 'deactivate' to exit the virtual environment when done."

# Instruct the user how to source it.
echo "To activate, run this command in your terminal:"
echo "source ${ACTIVATE_SCRIPT}" 