
from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List
from datetime import datetime
import os
import uuid
import shutil
import pandas as pd
import subprocess

# Konfiguracja
UPLOAD_DIR = "uploaded_files"
REPORT_DIR = "generated_reports"
TACHOPARSER_PATH = "tachoparser"
CERTS_DIR = "certs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# HTML interfejs
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Obsługa uploadu
@app.post("/upload")
async def upload_files(
    request: Request,
    files: List[UploadFile],
    start_date: str = Form(...),
    end_date: str = Form(...)
):
    report_id = uuid.uuid4().hex
    upload_path = os.path.join(UPLOAD_DIR, report_id)
    os.makedirs(upload_path, exist_ok=True)

    filepaths = []
    for file in files:
        dest = os.path.join(upload_path, file.filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        filepaths.append(dest)

    # Przetwarzanie plików przez tachoparser
    parsed_data = []
    for path in filepaths:
        try:
            result = subprocess.run([
                "python3", os.path.join(TACHOPARSER_PATH, "tachoparser.py"),
                path,
                "--certificates-dir", CERTS_DIR,
                "--format", "json"
            ], capture_output=True, text=True)
            parsed_data.append(result.stdout)
        except Exception as e:
            print(f"Błąd przetwarzania: {e}")

    # Filtrowanie i raport (mock - przykładowa tabela)
    df = pd.DataFrame({
        "Plik": [os.path.basename(p) for p in filepaths],
        "Data start": start_date,
        "Data koniec": end_date,
        "Czas jazdy": ["4:32"] * len(filepaths),
        "Czas odpoczynku": ["1:45"] * len(filepaths)
    })

    report_file = os.path.join(REPORT_DIR, f"report_{report_id}.xlsx")
    df.to_excel(report_file, index=False)

    return templates.TemplateResponse("result.html", {
        "request": request,
        "report_url": f"/download/{os.path.basename(report_file)}"
    })

@app.get("/download/{filename}")
def download_file(filename: str):
    path = os.path.join(REPORT_DIR, filename)
    return FileResponse(path, filename=filename, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Uruchomienie serwera: ustal port 30319
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=30319, reload=True)
