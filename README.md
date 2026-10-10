# ClaimBridge — Intelligent Insurance Claim Verification and Readiness Assessment System

ClaimBridge is an AI-assisted health insurance claim verification system designed to help hospitals, insurance coordinators, and claims officers review medical documents, validate claim information, evaluate policy coverage, and assess claim readiness before submission.

The system combines document processing, Optical Character Recognition (OCR), document classification, information extraction, medical intelligence, policy-based analysis, and rule-based validation to produce structured, traceable claim assessments.

**Project Type:** Final-Year BE Computer Engineering Project

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Objectives](#objectives)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Claim Processing Workflow](#claim-processing-workflow)
- [Technology Stack](#technology-stack)
- [Supported Documents](#supported-documents)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Environment Configuration](#environment-configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Security and Reliability](#security-and-reliability)
- [Current Limitations](#current-limitations)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)
- [License](#license)

## Overview

Health insurance claims frequently involve multiple documents, including hospital bills, discharge summaries, prescriptions, laboratory reports, medical reports, and insurance policies. Manually reviewing these documents can be time-consuming and may lead to missing information, inconsistent records, and delayed claim processing.

ClaimBridge aims to streamline this workflow by extracting information from uploaded documents, identifying document types, checking consistency, evaluating available policy evidence, and generating a claim-readiness assessment.

The system is designed to support human reviewers rather than replace final professional claim decisions.

## Problem Statement

Traditional insurance claim verification relies heavily on manual document examination and cross-checking. This can result in:

- Time-consuming document verification.
- Inconsistent or incomplete claim information.
- Difficulty identifying discrepancies across multiple documents.
- Delayed identification of missing documentation.
- Manual comparison of medical expenses against available policy information.
- Limited visibility into why a claim requires additional review.

ClaimBridge addresses these challenges through automated document understanding, structured extraction, validation, and explainable review assistance.

## Objectives

1. Automate the intake and processing of medical claim documents.
2. Extract text from searchable and scanned PDF documents using OCR and native-text extraction.
3. Automatically classify documents into relevant categories.
4. Extract structured medical, financial, and policy information.
5. Identify missing fields and inconsistencies across claim documents.
6. Evaluate available policy evidence using policy intelligence and retrieval-based analysis.
7. Calculate claim-readiness and confidence indicators using the existing assessment engines.
8. Route uncertain or inconsistent claims for human review.
9. Maintain claim records, processing results, and decision history in PostgreSQL.
10. Provide a web-based interface for uploading documents and reviewing claim information.

## Key Features

### 1. Secure Document Intake

- Upload supported PDF and image documents.
- Associate uploaded documents with claim records.
- Validate file types, file signatures, and file size.
- Track document-processing status.
- Handle invalid and unreadable documents without generating fabricated results.

### 2. Automatic PDF Understanding

- Extract native text from searchable PDFs.
- Render scanned PDF pages into images for OCR.
- Process multi-page PDFs while preserving page boundaries.
- Support documents containing both searchable and scanned pages.
- Preserve extraction metadata, including page numbers and extraction method where available.

### 3. OCR and Document Classification

- Use OCR to recognize text in scanned documents.
- Automatically identify likely document categories from extracted content.
- Handle hospital bills, discharge summaries, prescriptions, laboratory reports, medical reports, and insurance policies.
- Identify ambiguous or unsupported document types for further review.

### 4. Structured Information Extraction

Extract relevant information according to document type, where available:

- Patient and provider details.
- Admission, discharge, and invoice dates.
- Medical diagnoses and procedures.
- Itemized hospital charges and total amounts.
- Prescription medication details.
- Laboratory test results and reference ranges.
- Insurance policy identifiers, coverage limits, and relevant clauses.

Extracted values are subject to validation and may require human confirmation.

### 5. Medical and Policy Intelligence

- Analyze available medical information.
- Retrieve relevant policy content where available.
- Compare extracted claim details against available policy evidence.
- Identify missing evidence, possible inconsistencies, and unresolved coverage questions.
- Avoid treating unsupported AI-generated findings as verified facts.

### 6. Validation and Claim Readiness

- Check required fields and data consistency.
- Identify possible discrepancies between documents.
- Assess the availability and quality of supporting information.
- Generate claim-readiness and confidence indicators.
- Route uncertain cases for human review rather than automatically treating them as approved.

### 7. Claim Management and Review Dashboard

- Create and view claim records.
- Upload and review associated documents.
- Display processing results and validation findings.
- Track claim status and review outcomes.
- Maintain claim history through the backend workflow.

## System Architecture

```text
                 CLAIMBRIDGE
                      |
                      v
             React + TypeScript
                 Web Frontend
                      |
                      v
                FastAPI Backend
                      |
                      v
            Secure Document Intake
                      |
                      v
             Image Preprocessing
                      |
                      v
            PDF Text Extraction / OCR
                      |
                      v
            Document Classification
                      |
                      v
            Information Extraction
                      |
                      v
              Medical Intelligence
                      |
                      v
           Policy Intelligence (RAG)
                      |
                      v
              Validation Engine
                      |
                      v
           Claim Readiness Engine
                      |
                      v
              Confidence Engine
                      |
              +-------+-------+
              |               |
              v               v
       Human Review     Eligible Automated
                           Processing
              |               |
              +-------+-------+
                      |
                      v
             Final Claim Decision
                      |
                      v
               Claim History
                      |
                      v
              PostgreSQL Database
```

The architecture represents the intended processing flow. The availability and behavior of individual modules depend on their implementation and configured data sources.

## Claim Processing Workflow

1. **Document Upload:** The user uploads a claim document through the web interface.
2. **File Validation:** The backend validates the file and associates it with the relevant claim.
3. **PDF Processing:** Searchable text is extracted directly; scanned pages are rendered for OCR.
4. **Document Classification:** The system predicts the document category from its contents.
5. **Information Extraction:** Relevant medical, financial, and policy fields are extracted.
6. **Medical Intelligence:** Available medical details are analyzed.
7. **Policy Intelligence:** Relevant policy information is retrieved and evaluated.
8. **Validation:** The system checks required information, consistency, and possible discrepancies.
9. **Readiness Assessment:** The readiness and confidence engines evaluate the available evidence.
10. **Review Routing:** Claims with uncertainty or unresolved issues can be routed for human review.
11. **Final Decision and History:** The existing workflow records the decision and relevant claim history.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| Routing and Data Fetching | TanStack Router, React Query |
| UI and Styling | Tailwind CSS, Radix UI-based components |
| Backend | Python, FastAPI |
| API Validation | Pydantic |
| Database | Neon PostgreSQL |
| ORM and Migrations | SQLAlchemy, Alembic |
| PDF Processing | PyMuPDF |
| OCR | Tesseract through PyTesseract; PaddleOCR where installed and configured |
| Image Processing | Pillow, OpenCV |
| Authentication | Existing authentication API and configured backend mechanisms |
| Version Control | Git and GitHub |

## Supported Documents

| Document Type | Examples of Information Extracted |
|---|---|
| Hospital Bill | Itemized charges, invoice date, total amount, hospital details |
| Discharge Summary | Diagnosis, admission and discharge dates, treatment details |
| Prescription | Medication names, dosage, frequency, duration |
| Laboratory Report | Test names, results, units, reference ranges |
| Medical Report | Findings, diagnosis, recommendations |
| Insurance Policy | Policy period, coverage limits, exclusions, relevant clauses |

Extraction depends on document quality, layout, language, and the availability of readable content. Unsupported or ambiguous documents should be flagged rather than assigned fabricated information.

## Project Structure

The repository contains the React frontend, FastAPI backend, document-processing modules, and test files.

```text
ClaimBridgde-/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── auth.py
│   │   ├── claims.py
│   │   ├── documents.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── ocr.py
│   │   ├── pipeline.py
│   │   ├── document_classifier.py
│   │   ├── information_extractor.py
│   │   ├── medical_intelligence.py
│   │   ├── policy_intelligence.py
│   │   ├── validation_engine.py
│   │   ├── claim_readiness_engine.py
│   │   ├── confidence_engine.py
│   │   ├── final_claim_decision.py
│   │   ├── claim_history.py
│   │   └── claim_processor.py
│   ├── policies/
│   ├── requirements.txt
│   ├── test_pdf_ocr.py
│   └── test_complete_pdf_pipeline.py
├── src/
│   ├── api/
│   ├── components/
│   ├── lib/
│   └── routes/
├── public/
├── package.json
├── server.ts
└── README.md
```

This is a representative structure; additional configuration files, UI components, and modules may exist in the repository.

## Prerequisites

Install the following before running the application:

- Python compatible with the backend dependencies.
- Node.js and npm.
- Access to the configured Neon PostgreSQL database.
- Git.
- Tesseract OCR installed and available to PyTesseract for scanned-document OCR.
- The Python packages specified in `backend/requirements.txt`.

PaddleOCR may also be used where its dependencies and runtime are installed and configured. Verify the OCR engine in the environment where the application will run.

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/hiteshmorye-afk/ClaimBridgde-.git
cd ClaimBridgde-
```

### 2. Configure the Backend

Create and activate a virtual environment from the repository root:

```powershell
python -m venv backend/.venv
backend\.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```powershell
python -m pip install -r backend/requirements.txt
```

If PowerShell does not permit activation, use the environment's interpreter directly:

```powershell
backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Install Tesseract OCR separately on Windows if it is not already installed. Confirm that the executable is accessible to the application.

### 3. Configure Environment Variables

Create `backend/.env` using the project's existing environment configuration. Set the database connection variable expected by `backend/app/database.py`, using your own Neon PostgreSQL connection string.

Example:

```env
DATABASE_URL=your_neon_postgresql_connection_string
```

This is an illustrative placeholder. Check the existing application configuration for any additional required environment variables.

**Security:** Never commit `.env` files, database passwords, API keys, authentication secrets, or private medical documents to GitHub.

### 4. Configure the Frontend

From the repository root:

```bash
npm install
```

If the frontend requires an API base URL, configure it using the environment variable expected by the existing API client. Do not expose private backend credentials in frontend variables.

## Running the Application

Run the backend and frontend in separate terminals.

### Backend — FastAPI

From the repository root, with the backend virtual environment activated:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Backend URL:

`http://127.0.0.1:8000`

Interactive API documentation:

`http://127.0.0.1:8000/docs`

Health endpoint, if enabled:

`http://127.0.0.1:8000/health`

### Frontend — React and Vite

From the repository root:

```bash
npm run dev
```

Open the local URL printed by Vite in the terminal. The port may vary if the default port is already in use.

Ensure that the frontend API configuration and backend CORS settings permit communication between the two local services.

## API Documentation

FastAPI provides interactive API documentation at:

`http://127.0.0.1:8000/docs`

The existing backend includes endpoints for authentication, claims, and document operations. Depending on the current implementation, document workflows include upload and processing through routes such as:

- `POST /documents/upload`
- `POST /documents/{document_id}/process`
- `GET /claims`
- `GET /claims/{claim_id}`

Use the interactive documentation to inspect the actual request formats, response schemas, and currently registered endpoints.

## Testing

Run the focused PDF and OCR tests:

```powershell
python backend/test_pdf_ocr.py
```

Run the complete automated pipeline test suite:

```powershell
python backend/test_complete_pdf_pipeline.py
```

Check Python syntax:

```powershell
python -m compileall -q backend/app
```

Build the frontend for production:

```bash
npm run build
```

These tests cover PDF processing, extraction behavior, classification, validation, and relevant integration workflows. Test results depend on the installed OCR runtime, environment configuration, database availability, and test implementation.

Scanned-PDF tests should verify actual recognized text, not merely confirm that an OCR error was handled safely.

## Security and Reliability

- Validate uploaded file types, signatures, and size.
- Handle corrupted, empty, and unreadable documents safely.
- Do not fabricate OCR output or medical information when processing fails.
- Preserve document-to-claim associations.
- Protect database credentials and authentication secrets.
- Validate extracted amounts, dates, and cross-document consistency.
- Distinguish missing evidence from verified information.
- Route uncertain results to human review.
- Treat AI-generated findings as decision support, not definitive medical or insurance advice.

## Current Limitations

- OCR accuracy depends on image resolution, scan quality, fonts, layout, and language.
- Similar-looking characters can cause errors in dates, patient identifiers, and financial amounts.
- Document classification and field extraction may be uncertain for unfamiliar layouts.
- Policy analysis depends on the availability and quality of the relevant policy content.
- The presence of a policy clause does not automatically establish that a claim is covered.
- OCR, extraction, and automated validation do not replace human review or the insurer's final decision.
- OCR runtime availability must be verified separately in each deployment environment.

## Future Enhancements

Potential future improvements include:

- Better handling of rotated, low-resolution, and handwritten documents.
- Multilingual OCR support.
- Stronger field-level extraction confidence and evidence tracking.
- Improved policy retrieval and source-grounded explanations.
- More comprehensive fraud and anomaly detection.
- Advanced cross-document reconciliation.
- Role-based claimant and claims-officer workflows.
- TPA integrations and claim-status synchronization.
- More extensive automated integration and security testing.
- Deployment monitoring, auditability, and production hardening.

These are planned or potential enhancements; their inclusion here does not imply that they are already implemented.

## Contributing

1. Create a dedicated feature branch.
2. Make changes within the existing architecture.
3. Run the relevant backend tests and frontend build.
4. Review the staged changes before committing.
5. Submit changes through a pull request for review.

Avoid committing secrets, environment files, test patient records, uploaded documents, or generated build artifacts.

## License

No license is specified in this README. Add an appropriate `LICENSE` file before distributing the project under an open-source license.