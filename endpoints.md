# Bank Statement Analysis API Endpoints

This document provides a high-level overview of the key API endpoints for the Bank Statement Analysis service.

---

## Core Endpoints

### 1. Statement Analysis (`/analyze-statements/`)

*   **Method:** `POST`
*   **Purpose:** This is the primary endpoint for processing bank statements. It accepts one or more bank statement PDFs (along with necessary metadata like bank name, date range, and optional passwords) and performs the core analysis. This includes extracting transactions, identifying names/account numbers, and structuring the financial data.
*   **Input:** Requires details like bank names, paths to PDF files (accessible by the server), a date range for analysis, and an identifier for the case.
*   **Output:** Returns a structured JSON response containing the analyzed data, including extracted transactions, identified entities (names/accounts), lists of any PDFs that couldn't be processed, and metadata about the analysis (e.g., missing months).
*   **Access:** Requires user authentication (e.g., via API Key or user login).

### 2. Excel Report Generation (`/excel-download/`)

*   **Method:** `POST`
*   **Purpose:** Generates a downloadable Excel report based on the analyzed statement data. This endpoint takes the structured data (typically obtained from the `/analyze-statements` endpoint) and formats it into a user-friendly `.xlsx` file.
*   **Input:** Requires the processed transaction data and name/account number information, along with a desired filename (`case_name`).
*   **Output:** Directly serves an Excel file (`.xlsx`) for download.
*   **Access:** Requires user authentication.

---

## Management & Utility Endpoints

### 3. API Key Management (`/api-keys/`)

*   **Methods:** `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `POST (regenerate)`
*   **Purpose:** Allows authenticated users to manage their API keys for programmatic access to the service. Users can create, view, update, delete, and regenerate their keys. Administrators have full access to manage all keys.
*   **Access:** Requires user authentication. Standard users manage their own keys; Admins manage all keys.

### 4. User Management (`/users/`)

*   **Methods:** `GET` (Read-Only)
*   **Purpose:** Provides administrators with the ability to view user accounts registered in the system.
*   **Access:** Restricted to Admin users only.

### 5. Task Management (`/tasks/`)

*   **Methods:** `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `POST (cancel)`, `GET (status)`
*   **Purpose:** Manages background processing tasks (likely used for asynchronous operations, though current analysis is synchronous). Allows creating, viewing, updating, deleting, and checking the status or canceling tasks.
*   **Access:** Requires user authentication.

### 6. Health Check (`/health/`)

*   **Method:** `GET`
*   **Purpose:** A public endpoint (no authentication needed) to verify the basic health and connectivity of the API service and its dependencies (like the database and caching layer). Useful for automated monitoring.
*   **Output:** Returns the status of key components (e.g., "ok" or "error").
*   **Access:** Public (`AllowAny`).

--- 