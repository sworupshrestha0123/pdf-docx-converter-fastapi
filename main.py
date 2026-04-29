import os
import subprocess
import tempfile
import shutil
import platform
from tempfile import NamedTemporaryFile, TemporaryDirectory

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pdf2docx import Converter

app = FastAPI(title="PDF ↔ DOCX Converter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Smart soffice locator
# ------------------------------------------------------------------
def get_soffice_path():
    if platform.system() == "Windows":
        possible = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for p in possible:
            if os.path.isfile(p):
                return p
    return "soffice"

# ------------------------------------------------------------------
# Endpoint 1: PDF -> DOCX
# ------------------------------------------------------------------
@app.post("/pdf-to-docx")
async def pdf_to_docx(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files accepted")

    pdf_bytes = await file.read()
    with NamedTemporaryFile(delete=False, suffix=".pdf") as pdf_tmp:
        pdf_tmp.write(pdf_bytes)
        pdf_path = pdf_tmp.name

    docx_path = pdf_path.replace(".pdf", ".docx")

    try:
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)
        cv.close()

        return FileResponse(
            path=docx_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="converted.docx",
            background=True
        )
    except Exception as e:
        if os.path.exists(docx_path):
            os.unlink(docx_path)
        raise HTTPException(500, f"PDF to DOCX conversion failed: {str(e)}")
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)

# ------------------------------------------------------------------
# Endpoint 2: DOCX -> PDF (FIXED)
# ------------------------------------------------------------------
@app.post("/docx-to-pdf")
async def docx_to_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".docx"):
        raise HTTPException(400, "Only DOCX files accepted")

    docx_bytes = await file.read()
    with NamedTemporaryFile(delete=False, suffix=".docx") as docx_tmp:
        docx_tmp.write(docx_bytes)
        docx_path = docx_tmp.name

    # We'll create a permanent temp PDF file that FileResponse can safely serve
    output_pdf_file = NamedTemporaryFile(delete=False, suffix=".pdf")
    output_pdf_path = output_pdf_file.name
    output_pdf_file.close()  # we only need the path

    with TemporaryDirectory() as workdir:
        try:
            # Copy the DOCX into the workdir (soffice works on a directory)
            shutil.copy(docx_path, workdir)
            base_name = os.path.basename(docx_path)

            soffice_exe = get_soffice_path()
            subprocess.run(
                [
                    soffice_exe,
                    "--headless",
                    "--norestore",
                    "--convert-to", "pdf",
                    "--outdir", workdir,
                    os.path.join(workdir, base_name)
                ],
                check=True,
                timeout=120,
                env={**os.environ, "HOME": tempfile.gettempdir()},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # LibreOffice created the PDF inside workdir
            pdf_name = base_name.replace(".docx", ".pdf")
            generated_pdf = os.path.join(workdir, pdf_name)

            if not os.path.exists(generated_pdf):
                raise HTTPException(500, "PDF was not created")

            # Copy the PDF out of the temporary directory to the permanent one
            shutil.copy2(generated_pdf, output_pdf_path)

            # Now the PDF at output_pdf_path will survive after workdir is deleted
            return FileResponse(
                path=output_pdf_path,
                media_type="application/pdf",
                filename="translated.pdf",
                background=True   # FileResponse will delete this file after sending
            )
        except subprocess.CalledProcessError as e:
            # Clean up the permanent file if conversion failed
            if os.path.exists(output_pdf_path):
                os.unlink(output_pdf_path)
            raise HTTPException(500, f"LibreOffice conversion failed: {e.stderr.decode()}")
        except Exception as e:
            if os.path.exists(output_pdf_path):
                os.unlink(output_pdf_path)
            raise HTTPException(500, f"DOCX to PDF conversion failed: {str(e)}")
        finally:
            if os.path.exists(docx_path):
                os.unlink(docx_path)

# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}