# Feature: Migrate FastAPI Bank Statement Analyzer to Django

**Description:** Move the standalone FastAPI statement analysis logic (originally in the root `backend` directory) into the main Django project (`api`), renaming it to `api/statement_analyzer/` to avoid conflicts. This integrates the functionality directly into Django. The initial integration will run analysis synchronously within Django views.

## Completed Tasks

**1. Prepare Directory Structure:**
   - [x] **Move and Rename:** Execute `mv backend api/statement_analyzer` to relocate the FastAPI logic.

**2. Update Import Statements:**
   - [x] **In `api/statement_analyzer/...` files referencing `utils`:**
       - *File Example:* `api/statement_analyzer/main.py`
       - *Original:* `from backend.utils import get_saved_pdf_dir`
       - *New:* `from statement_analyzer.utils import get_saved_pdf_dir`
   - [x] **In `api/statement_analyzer/main.py` referencing `tax_professional`:**
       - *Original:* `from backend.tax_professional.banks.CA_Statement_Analyzer import ...`
       - *New:* `from statement_analyzer.tax_professional.banks.CA_Statement_Analyzer import ...`
   - [x] **In `api/statement_analyzer/tax_professional/banks/CA_Statement_Analyzer.py`:**
       - *Original:* `from ...utils import get_saved_pdf_dir, get_saved_excel_dir`
       - *New:* `from statement_analyzer.utils import get_saved_pdf_dir, get_saved_excel_dir`
       - *Original:* `from ...common_functions import ...` (many functions)
       - *New:* `from statement_analyzer.common_functions import ...` (corresponding functions)
   - [x] **In `api/statement_analyzer/common_functions.py`:**
       - *Original:* `from .utils import get_base_dir`
       - *New:* `from statement_analyzer.utils import get_base_dir`
       - *Original:* `from .code_for_extraction import ...`
       - *New:* `from statement_analyzer.code_for_extraction import ...`
   - [x] **In `api/statement_analyzer/...` files referencing NER/Account Extraction:**
       - *File Example:* `api/statement_analyzer/main.py`
       - *Original:* `from backend.account_number_ifsc_extraction import extract_accno_ifsc`
       - *New:* `from statement_analyzer.account_number_ifsc_extraction import extract_accno_ifsc`
       - *Original:* `from backend.pdf_to_name import extract_entities`
       - *New:* `from statement_analyzer.pdf_to_name import extract_entities`
   - [x] **Verify other relative imports within `api/statement_analyzer/` are correctly updated.**

**3. Create Django Serializers (`endpoints/serializers.py`):**
   - [x] Define `BankStatementAnalysisRequestSerializer` mirroring fields in `BankStatementRequest` Pydantic model (from `api/statement_analyzer/main.py`). Ensure fields like `bank_names`, `pdf_paths`, `passwords`, `start_date`, `end_date`, `ca_id` are included.
   - [x] Define `ExcelDownloadRequestSerializer` mirroring fields in `ExcelDownloadRequest` Pydantic model (from `api/statement_analyzer/main.py`). Ensure fields like `transaction_data`, `name_n_num`, `case_name` are included.

**4. Create Django Views (`endpoints/views.py`):**
   - [x] Add necessary imports: `APIView`, `Response`, `status`, `HttpResponse`, new serializers, analysis functions (`start_extraction_add_pdf`, `save_to_excel`, `extract_entities`, `extract_accno_ifsc` from `statement_analyzer...`).
   - [x] Implement `BankStatementAnalysisView(APIView)`:
       - Define `post` method.
       - Validate request using `BankStatementAnalysisRequestSerializer`.
       - Call `extract_entities`, `extract_accno_ifsc`.
       - Call `start_extraction_add_pdf` synchronously, passing validated data.
       - Sanitize results for JSON compatibility (handle NaN/Infinity).
       - Return `Response` containing analysis results (e.g., `data`, `ner_results`, `pdf_paths_not_extracted`).
   - [x] Implement `BankStatementExcelDownloadView(APIView)`:
       - Define `post` method.
       - Validate request using `ExcelDownloadRequestSerializer`.
       - Call `save_to_excel`, passing validated data.
       - Get the file path returned by `save_to_excel`.
       - Read the content of the file at that path.
       - Create `HttpResponse` with the file content, `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, and `Content-Disposition: attachment; filename=...`.
       - Return the `HttpResponse`.

**5. Create Django URL Patterns (`endpoints/urls.py`):**
   - [x] Import `BankStatementAnalysisView` and `BankStatementExcelDownloadView`.
   - [x] Add `path('analyze-statements/', BankStatementAnalysisView.as_view(), name='analyze_statements')`.
   - [x] Add `path('excel-download/', BankStatementExcelDownloadView.as_view(), name='excel_download')`.
   - [x] Verify `endpoints/urls.py` is included in `api/backend/urls.py` under `/api/v1/` prefix.

**6. Update Test Script (`testt.py`):**
   - [x] **Set `BASE_URL`:** Change to Django server address (`https://127.0.0.1:8000/api/v1`).
   - [x] **Add Auth:** Implement JWT token retrieval and inclusion in request headers.
   - [x] **Check Endpoint Paths:** Ensure calls use `/analyze-statements/` and `/excel-download/` relative to `BASE_URL`.
   - [x] **Modify `download_excel` function:** Handle direct file content (`response.content`) and save locally.
   - [x] **Adjust `analyze_statements` result parsing:** Ensure keys match Django view response.

**7. Verification:**
   - [x] Start the Django development server (`./start_dev.sh`).
   - [x] Run the modified `testt.py` (with valid credentials).
   - [x] Check terminal output for success messages.
   - [x] Verify the downloaded Excel file is created locally and looks correct.

## In Progress Tasks

*(Now empty, moved to Future Tasks)*

## Future Tasks (Immediate Priorities)

**1. Refactor File Path Handling:**
   - [ ] **Analyze:** Investigate `api/statement_analyzer/utils.py` (`get_saved_excel_dir`) and `api/statement_analyzer/tax_professional/banks/CA_Statement_Analyzer.py` (`save_to_excel`) to understand how output paths are currently determined.
   - [ ] **Configure:** Define a reliable storage location using Django settings (e.g., a subdirectory within `settings.MEDIA_ROOT` or a dedicated setting like `ANALYSIS_OUTPUT_DIR`).
   - [ ] **Modify:** Update `get_saved_excel_dir` or `save_to_excel` to use the configured Django setting to construct the output file path.
   - [ ] **Verify:** Ensure `BankStatementExcelDownloadView` can still correctly read the file from the new, configured location.

**2. Implement Asynchronous Processing (Celery):**
   - [ ] **Create Celery Task:** Define a new task in `api/endpoints/tasks.py` (e.g., `process_bank_statement_task`).
       - This task should accept necessary inputs (PDF paths, passwords, dates, user ID, etc.).
       - Inside the task, call the core logic: `extract_entities`, `extract_accno_ifsc`, `start_extraction_add_pdf`, `save_to_excel`.
       - The task should handle errors gracefully.
       - Upon completion, the task should update the corresponding `ScheduledTask` model instance (e.g., set status to 'completed'/'failed', store the output Excel file path or error message in the `result` field).
   - [ ] **Update Analysis View (`BankStatementAnalysisView`):**
       - Remove the synchronous calls to the analysis logic.
       - Create a `ScheduledTask` model instance to represent the job.
       - Trigger the new Celery task (`process_bank_statement_task.delay(...)`), passing the required arguments.
       - Store the Celery task ID in the `ScheduledTask` instance (`task_id` field).
       - Return an immediate `Response` (e.g., `202 Accepted`) including the `ScheduledTask` ID, so the client can poll for status.
   - [ ] **Adapt Download Logic:**
       - Determine how the client will retrieve the finished Excel file. Options:
           - **Option A (Polling):** Client polls the existing `/api/v1/tasks/{id}/status/` endpoint. When status is 'completed', the `result` field (containing the Excel path) is returned. Client then makes a *new* request to a dedicated download endpoint (see below).
           - **Option B (Direct Download Endpoint):** Create a new view (e.g., `DownloadAnalyzedStatementView`) that takes the `ScheduledTask` ID. This view checks if the task is 'completed', retrieves the file path from the `result`, and serves the file directly.
       - Modify or replace `BankStatementExcelDownloadView` according to the chosen option.

**3. Add Automated Tests:**
   - [ ] **Unit Tests:** Write tests for individual functions within `api/statement_analyzer/` (especially complex ones in `common_functions.py`), mocking external dependencies if necessary.
   - [ ] **Integration Tests:** Write Django tests (e.g., using `APITestCase`) for the `BankStatementAnalysisView` and the download view/logic.
       - Test successful analysis submission (check response code, `ScheduledTask` creation).
       - Test retrieval of task status/results (mocking Celery task completion).
       - Test successful file download.
       - Test various error conditions (invalid input, analysis failures).

**4. Code Cleanup & Refinement:**
   - [ ] **Remove Unused Code:** Delete `api/statement_analyzer/main.py` (the old FastAPI app).
   - [ ] **Dependencies:** Review `requirements.txt` and remove `fastapi`, `uvicorn` if they are no longer needed by any part of the Django project.
   - [ ] **Pandas Warnings:** Investigate `FutureWarning` and `SettingWithCopyWarning` messages originating from `common_functions.py` and refactor the pandas usage to follow current best practices.
   - [ ] **Configuration:** Move any hardcoded values (like thresholds, specific strings used for categorization in `common_functions.py`) into Django settings or constants for better maintainability.
   - [ ] **Error Handling:** Improve error handling within the analysis logic and views to provide more specific feedback to the user/API client.

## Implementation Plan

The initial migration is complete. The focus now shifts to making the integration robust and production-ready by addressing the items in the "Future Tasks (Immediate Priorities)" section above. The recommended order is: File Paths -> Asynchronous Processing -> Tests -> Cleanup.

## Relevant Files

*(Reflects current state)*
- `api/statement_analyzer/` (Contains migrated analysis logic)
- `api/statement_analyzer/utils.py` (**Needs path refactoring**)
- `api/statement_analyzer/tax_professional/banks/CA_Statement_Analyzer.py` (**Uses path logic, called by Celery task later**)
- `api/statement_analyzer/common_functions.py` (Contains core logic, potential pandas warnings)
- `api/endpoints/views.py` (**Needs update for Celery task triggering**)
- `api/endpoints/serializers.py` (Likely stable for now)
- `api/endpoints/urls.py` (May need updates for new download view)
- `api/endpoints/tasks.py` (**New Celery task to be created here**)
- `api/endpoints/models.py` (`ScheduledTask` model will be used)
- `testt.py` (Will need modification to interact with async flow)
- `TASKS.md` (This file - updated)
- `requirements.txt` (Check for unused dependencies)