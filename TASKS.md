# Feature: Migrate FastAPI Bank Statement Analyzer to Django

**Description:** Move the standalone FastAPI statement analysis logic (originally in the root `backend` directory) into the main Django project (`api`), renaming it to `api/statement_analyzer/` to avoid conflicts. This integrates the functionality directly into Django. The initial integration will run analysis synchronously within Django views.

## Completed Tasks

*(Initially empty)*

## In Progress Tasks

**1. Prepare Directory Structure:**
   - [x] **Move and Rename:** Execute `mv backend api/statement_analyzer` to relocate the FastAPI logic.

**2. Update Import Statements:**
   - [x] **In `api/statement_analyzer/...` files referencing `utils`:**
       - *File Example:* `api/statement_analyzer/main.py`
       - *Original:* `from backend.utils import get_saved_pdf_dir`
       - *New:* `from api.statement_analyzer.utils import get_saved_pdf_dir`
   - [x] **In `api/statement_analyzer/main.py` referencing `tax_professional`:**
       - *Original:* `from backend.tax_professional.banks.CA_Statement_Analyzer import ...`
       - *New:* `from api.statement_analyzer.tax_professional.banks.CA_Statement_Analyzer import ...`
   - [x] **In `api/statement_analyzer/tax_professional/banks/CA_Statement_Analyzer.py`:**
       - *Original:* `from ...utils import get_saved_pdf_dir, get_saved_excel_dir`
       - *New:* `from api.statement_analyzer.utils import get_saved_pdf_dir, get_saved_excel_dir`
       - *Original:* `from ...common_functions import ...` (many functions)
       - *New:* `from api.statement_analyzer.common_functions import ...` (corresponding functions)
   - [x] **In `api/statement_analyzer/...` files referencing NER/Account Extraction:**
       - *File Example:* `api/statement_analyzer/main.py`
       - *Original:* `from backend.account_number_ifsc_extraction import extract_accno_ifsc`
       - *New:* `from api.statement_analyzer.account_number_ifsc_extraction import extract_accno_ifsc`
       - *Original:* `from backend.pdf_to_name import extract_entities`
       - *New:* `from api.statement_analyzer.pdf_to_name import extract_entities`
   - [x] **Verify other relative imports within `api/statement_analyzer/` are correctly updated.**

**3. Create Django Serializers (`endpoints/serializers.py`):**
   - [x] Define `BankStatementAnalysisRequestSerializer` mirroring fields in `BankStatementRequest` Pydantic model (from `api/statement_analyzer/main.py`). Ensure fields like `bank_names`, `pdf_paths`, `passwords`, `start_date`, `end_date`, `ca_id` are included.
   - [x] Define `ExcelDownloadRequestSerializer` mirroring fields in `ExcelDownloadRequest` Pydantic model (from `api/statement_analyzer/main.py`). Ensure fields like `transaction_data`, `name_n_num`, `case_name` are included.

**4. Create Django Views (`endpoints/views.py`):**
   - [x] Add necessary imports: `APIView`, `Response`, `status`, `HttpResponse`, new serializers, analysis functions (`start_extraction_add_pdf`, `save_to_excel`, `extract_entities`, `extract_accno_ifsc` from `api.statement_analyzer...`).
   - [x] Implement `BankStatementAnalysisView(APIView)`:
       - Define `post` method.
       - Validate request using `BankStatementAnalysisRequestSerializer`.
       - Call `extract_entities`, `extract_accno_ifsc`.
       - Call `start_extraction_add_pdf` synchronously, passing validated data.
       - Return `Response` containing analysis results (e.g., `data`, `ner_results`, `pdf_paths_not_extracted`) from `start_extraction_add_pdf`.
   - [x] Implement `BankStatementExcelDownloadView(APIView)`:
       - Define `post` method.
       - Validate request using `ExcelDownloadRequestSerializer`.
       - Call `save_to_excel`, passing validated data.
       - **Important:** Get the file path returned by `save_to_excel`.
       - Read the content of the file at that path.
       - Create `HttpResponse` with the file content, `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, and `Content-Disposition: attachment; filename=...`.
       - Return the `HttpResponse`.

**5. Create Django URL Patterns (`endpoints/urls.py`):**
   - [x] Import `BankStatementAnalysisView` and `BankStatementExcelDownloadView`.
   - [x] Add `path('analyze-statements/', BankStatementAnalysisView.as_view(), name='analyze_statements')`.
   - [x] Add `path('excel-download/', BankStatementExcelDownloadView.as_view(), name='excel_download')`.
   - [x] Verify `endpoints/urls.py` is included in `api/urls.py` (likely under a prefix like `api/v1/`).

**6. Update Test Script (`testt.py`):**
   - [x] **Set `BASE_URL`:** Change to Django server address (e.g., `https://127.0.0.1:8000/api/v1` - confirmed prefix).
   - [x] **Check Endpoint Paths:** Ensure calls use `/analyze-statements/` and `/excel-download/`.
   - [x] **Modify `download_excel` function:**
       - Change it to expect file content in `response.content` instead of a file path in `response.text`.
       - Add logic to save `response.content` to a local file (e.g., `downloaded_statement_analysis.xlsx`) for verification.
   - [x] **Adjust `analyze_statements` result parsing:** Modify the main execution block to directly use the JSON response from the Django view (structure might differ slightly from the FastAPI response).

**7. Verification:**
   - [x] Start the Django development server (`./start_dev.sh`).
   - [x] Run the modified `testt.py`.
   - [x] Check terminal output for success messages from `testt.py`.
   - [x] Verify the downloaded Excel file (`Bank_axis_statement_analysis_from_django_script_Extracted_statements_file.xlsx` or similar) is created locally and looks correct.