import os
import uvicorn
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# If you have other custom imports:
from tax_professional.banks.CA_Statement_Analyzer import start_extraction_add_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Bank Statement Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


class BankStatementRequest(BaseModel):
    bank_names: List[str]
    pdf_paths: List[str]
    passwords: Optional[List[str]] = []  # Optional field, defaults to empty list
    start_date: List[str]
    end_date: List[str]
    ca_id: str


@app.post("/analyze-statements/")
async def analyze_bank_statements(request: BankStatementRequest):
    try:
        logger.info(f"Received request with banks: {request.bank_names}")

        # Create a progress tracking function
        def progress_tracker(current: int, total: int, info: str) -> None:
            logger.info(f"{info} ({current}/{total})")

        progress_data = {
            "progress_func": progress_tracker,
            "current_progress": 10,
            "total_progress": 100,
        }

        # Validate passwords length if provided
        if request.passwords and len(request.passwords) != len(request.pdf_paths):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Number of passwords ({len(request.passwords)}) "
                    f"must match number of PDFs ({len(request.pdf_paths)})"
                ),
            )

        logger.info("Initializing CABankStatement")
        # Pass empty list if no passwords

        bank_names = request.bank_names
        pdf_paths = request.pdf_paths
        passwords =  request.passwords if request.passwords else []
        start_date = request.start_date
        end_date = request.end_date
        CA_ID = request.ca_id
        progress_data = progress_data

        logger.info("Starting extraction")
        result = start_extraction_add_pdf(bank_names, pdf_paths, passwords, start_date, end_date, CA_ID, progress_data)
        print("RESULT GENERATED")
        logger.info("Extraction completed successfully")
        return {
            "status": "success",
            "message": "Bank statements analyzed successfully",
            "data": result["sheets_in_json"],
            "pdf_paths_not_extracted": result["pdf_paths_not_extracted"],
        }

    except Exception as e:
        logger.error(f"Error processing bank statements: {str(e)}")
        print
        raise HTTPException(
            status_code=500, detail=f"Error processing bank statements: {str(e)}"
        )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    # Optionally use environment variables for host/port. Falls back to "0.0.0.0" and 7500 if none provided.
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "7500"))

    # IMPORTANT: reload=False for production usage
    uvicorn.run("main:app", host=host, port=port, reload=False)
