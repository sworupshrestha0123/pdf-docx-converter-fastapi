<h1 align="center">PDF ↔ DOCX Converter Microservice</h1>

<p align="center">
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"></a>
</p>

<p align="center">
  A high-performance, containerized REST API for bi-directional document conversion. 
</p>

<div align="center">
  <h3>
    <strong><a href="https://github.com/sworupshrestha0123/Google_TMT_HACKATHON">Part of the Google TMT Hackathon Project</a></strong>
  </h3>
</div>

<hr>

## Table of Contents

1. [Project Context](#project-context)
2. [Architecture & Stack](#architecture--stack)
3. [Docker Installation (Recommended)](#docker-installation-recommended)
4. [Local Installation](#local-installation)
5. [API Documentation](#api-documentation)
6. [Usage Examples](#usage-examples)

---

## Project Context

This microservice was developed specifically to support the **[Google TMT Hackathon](https://github.com/sworupshrestha0123/Google_TMT_HACKATHON)** repository. 

Document conversion requires system-level dependencies that are often difficult to bundle within a standard serverless function or lightweight web application. By isolating this functionality into its own dedicated, Dockerized FastAPI microservice, the main hackathon application can remain lightweight while delegating heavy CPU-bound document rendering tasks via standard HTTP calls.

---

## Architecture & Stack

*   **Framework:** FastAPI (Python) for asynchronous, high-throughput request handling.
*   **PDF to DOCX:** Utilizes the `pdf2docx` Python library for direct parsing and conversion.
*   **DOCX to PDF:** Invokes **LibreOffice Headless** via system subprocesses. This guarantees highly accurate rendering of Microsoft Word documents, including precise formatting and font mapping.
*   **Font Support:** Pre-configured with Liberation, FreeFont, and Devanagari (`fonts-deva`) fonts to ensure multilingual documents and translations render accurately in the final PDF without missing characters or layout shifts.

---

## Docker Installation (Recommended)

Because LibreOffice is a system-level dependency, deploying via Docker is the intended and most stable method for this repository. 

### 1. The Dockerfile
The repository includes a production-ready `Dockerfile` optimized for minimal size and robust font support:

```dockerfile
FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libreoffice-writer \
        libreoffice-calc \
        fonts-deva \
        fonts-liberation \
        fonts-freefont-ttf \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 2. Build and Run

**Build the image:**
```bash
docker build -t pdf-docx-converter .
```

**Run the container:**
*Note: The Dockerfile utilizes the `$PORT` environment variable, making it immediately compatible with PaaS providers like Google Cloud Run, Heroku, or Render. For local testing, you must pass this variable.*

```bash
docker run -e PORT=8000 -p 8000:8000 pdf-docx-converter
```

The API will now be available at `http://localhost:8000`.

---

## Local Installation

If you prefer to run the service directly on your host machine without Docker:

**1. Install System Dependencies (Debian/Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install libreoffice-core libreoffice-writer fonts-deva fonts-liberation fonts-freefont-ttf
```

**2. Setup Python Environment:**
```bash
git clone https://github.com/sworupshrestha0123/pdf-docx-converter-fastapi.git
cd pdf-docx-converter-fastapi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Run the Server:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## API Documentation

FastAPI provides an automatic, interactive OpenAPI interface. Once the server is running, navigate to:
*   **Swagger UI:** `http://localhost:8000/docs`

### Endpoints

#### `GET /health`
Validates that the service is running.
*   **Response:** `200 OK` `{"status": "ok"}`

#### `POST /pdf-to-docx`
Converts a PDF document into an editable DOCX file.
*   **Payload:** `multipart/form-data` containing the `file` key with the `.pdf` payload.
*   **Response:** `200 OK` Returns the binary `.docx` file.

#### `POST /docx-to-pdf`
Converts a DOCX document into a fixed-layout PDF file using the LibreOffice engine.
*   **Payload:** `multipart/form-data` containing the `file` key with the `.docx` payload.
*   **Response:** `200 OK` Returns the binary `.pdf` file.

---

## Usage Examples

### Consuming the API via Python (For the Main Hackathon App)

To integrate this within the main `Google_TMT_HACKATHON` project, use the `requests` library:

```python
import requests

def convert_document(file_path: str, target_format: str):
    """
    Utility function to call the microservice.
    target_format should be 'pdf' or 'docx'
    """
    # Adjust URL to match your deployed microservice endpoint
    base_url = "https://your-deployed-service-url.com" 
    
    if target_format == 'pdf':
        endpoint = f"{base_url}/docx-to-pdf"
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        endpoint = f"{base_url}/pdf-to-docx"
        content_type = "application/pdf"

    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, content_type)}
        response = requests.post(endpoint, files=files)

    if response.status_code == 200:
        output_name = f"output.{target_format}"
        with open(output_name, "wb") as f:
            f.write(response.content)
        return output_name
    else:
        raise Exception(f"Conversion failed: {response.text}")

# Example Usage:
# convert_document("translated_output.docx", "pdf")
```
