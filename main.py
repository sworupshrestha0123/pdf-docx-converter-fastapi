import os
import uuid
import subprocess
import shutil
from tempfile import NamedTemporaryFile, TemporaryDirectory

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pdf2docx import Converter

app = FastAPI(title="PDF ↔ DOCX Converter")

# Allow React app to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your React domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Endpoint 1: PDF -> DOCX (preserving layout)
# ------------------------------------------------------------------
@app.post("/pdf-to-docx")
async def pdf_to_docx(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    # Save uploaded PDF to a temporary file
    pdf_bytes = await file.read()
    with NamedTemporaryFile(delete=False, suffix=".pdf") as pdf_tmp:
        pdf_tmp.write(pdf_bytes)
        pdf_path = pdf_tmp.name

    # Create output DOCX path
    docx_path = pdf_path.replace(".pdf", ".docx")

    try:
        # Convert PDF -> DOCX using pdf2docx (layout preserved)
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)  # all pages
        cv.close()

        # Return the DOCX file as download
        return FileResponse(
            path=docx_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="converted.docx",
            background=True  # file is removed after response is sent
        )
    except Exception as e:
        raise HTTPException(500, f"PDF to DOCX conversion failed: {str(e)}")
    finally:
        # Clean up the temporary PDF (DOCX is handled by FileResponse)
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


# ------------------------------------------------------------------
# Endpoint 2: DOCX -> PDF (translated file)
# ------------------------------------------------------------------
@app.post("/docx-to-pdf")
async def docx_to_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".docx"):
        raise HTTPException(400, "Only DOCX files are accepted")

    # Save uploaded DOCX temporarily
    docx_bytes = await file.read()
    with NamedTemporaryFile(delete=False, suffix=".docx") as docx_tmp:
        docx_tmp.write(docx_bytes)
        docx_path = docx_tmp.name

    # Create a temporary directory for LibreOffice output
    with TemporaryDirectory() as tmpdir:
        try:
            # Copy DOCX into the temp directory (LibreOffice works on a directory)
            shutil.copy(docx_path, tmpdir)
            base_name = os.path.basename(docx_path)
            
            # Run headless LibreOffice conversion
            subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", tmpdir,
                    os.path.join(tmpdir, base_name)
                ],
                check=True,
                timeout=120,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Find the generated PDF
            pdf_name = base_name.replace(".docx", ".pdf")
            pdf_path = os.path.join(tmpdir, pdf_name)
            
            if not os.path.exists(pdf_path):
                raise HTTPException(500, "PDF was not created")
            
            # Return the PDF (FileResponse will clean up the tmpdir after response)
            return FileResponse(
                path=pdf_path,
                media_type="application/pdf",
                filename="translated.pdf",
                background=True
            )
        except subprocess.CalledProcessError as e:
            raise HTTPException(500, f"LibreOffice conversion failed: {e.stderr.decode()}")
        except Exception as e:
            raise HTTPException(500, f"DOCX to PDF conversion failed: {str(e)}")
        finally:
            if os.path.exists(docx_path):
                os.unlink(docx_path)


# Health check (optional)
@app.get("/health")
async def health():
    return {"status": "ok"}