import os
import sys
import time
import re
import traceback
from datetime import datetime
from pydantic import BaseModel
import pdfplumber

os.environ["GOOGLE_CLOUD_PROJECT"] = "odin-v2-495523"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "C:/Users/ASUS/.gemini/antigravity/scratch/Odin-v2")

from google.cloud import bigquery
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

# Pydantic schema for structured Gemini extraction
class RequisitosModel(BaseModel):
    experiencia_unspsc: list[str]
    experiencia_minima_cop: float
    experiencia_minima_contratos: int
    financiero_liquidez: str
    financiero_endeudamiento: str
    personal_requerido: list[str]

def download_and_extract_requirements(notice_uid: str) -> dict:
    """Download pliego documents from SECOP II using Playwright and extract requirements with Gemini."""
    url = f"https://community.secop.gov.co/Public/Tendering/OpportunityDetail/Index?noticeUID={notice_uid}"
    print(f"[{datetime.now()}] Initializing Playwright for URL: {url}")
    
    download_dir = os.path.join("C:/Users/ASUS/.gemini/antigravity/scratch/Odin-v2/temp_downloads", notice_uid)
    os.makedirs(download_dir, exist_ok=True)
    
    downloaded_files = []
    
    with sync_playwright() as p:
        # Launch Chromium headless
        browser = p.chromium.launch(headless=True)
        # Configure context with standard browser headers to avoid detection
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        try:
            print("Navigating to SECOP II Opportunity Detail...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for ReCaptcha check
            if "ReCaptcha" in page.title():
                print("[WARNING] ReCaptcha wall detected! Attempting to wait or bypass...")
                # If we are on residential IP, this shouldn't happen, but let's wait a bit
                page.wait_for_timeout(5000)
            
            # Wait for the document links to load
            print("Looking for document download links...")
            page.wait_for_timeout(3000)  # Wait for AJAX to complete
            
            # Find all links that look like downloads
            links = page.locator('a[href*="DownloadReceiver.ashx"]').all()
            print(f"Found {len(links)} potential download links on the page.")
            
            # Filter and download files that are likely to be Pliegos/Estudios Previos
            count = 0
            for link in links:
                href = link.get_attribute("href")
                text = link.inner_text().strip()
                
                # Check if it's a target document (pliego, estudios, terminos, condiciones)
                name_lower = (text + href).lower()
                is_target = any(k in name_lower for k in ("pliego", "estudio", "termino", "condicion", "referencia", "anexo"))
                
                if is_target and count < 3:  # Limit to top 3 documents to keep parsing fast
                    print(f"Downloading target document: '{text}'")
                    try:
                        # Set up download listener
                        with page.expect_download(timeout=30000) as download_info:
                            link.click()
                        download = download_info.value
                        
                        # Save the downloaded file
                        filename = download.suggested_filename or f"doc_{count}.pdf"
                        # Clean filename
                        filename = re.sub(r'[\\/*?:"<>|]', "", filename)
                        filepath = os.path.join(download_dir, filename)
                        download.save_as(filepath)
                        print(f"Saved: {filepath} ({os.path.getsize(filepath)} bytes)")
                        downloaded_files.append(filepath)
                        count += 1
                    except Exception as ex:
                        print(f"Failed to download '{text}': {ex}")
            
            browser.close()
        except Exception as e:
            print(f"Error during Playwright execution: {e}")
            traceback.print_exc()
            try:
                browser.close()
            except:
                pass
            
    # Process downloaded files and extract text
    combined_text = ""
    for filepath in downloaded_files:
        print(f"Parsing file: {filepath}")
        try:
            if filepath.lower().endswith(".pdf"):
                with pdfplumber.open(filepath) as pdf:
                    for page_num, page_obj in enumerate(pdf.pages[:15]):  # Scan up to 15 pages per document
                        page_text = page_obj.extract_text()
                        if page_text:
                            combined_text += f"\n--- Pagina {page_num+1} ---\n{page_text}"
            else:
                # Text or other formats
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    combined_text += f"\n{f.read()[:5000]}"
        except Exception as ex:
            print(f"Failed to parse '{filepath}': {ex}")
            
    if not combined_text:
        print("[WARNING] No text could be extracted from downloaded files.")
        return None
        
    print(f"Extracted {len(combined_text)} characters of text. Invoking Gemini for requirements parsing...")
    
    # 3. Invoke Gemini structured output
    try:
        client = genai.Client()
        prompt = f"""
        Analiza el siguiente texto de pliego de condiciones de un contrato de SECOP II.
        Extrae de forma precisa y estructurada los siguientes requisitos de participación:
        1. experiencia_unspsc: Una lista de códigos de categoría UNSPSC exigidos para la experiencia (ej: ["43233001", "81111800"]). Si no hay específicos, pon una lista vacía.
        2. experiencia_minima_cop: El valor mínimo de experiencia acumulada exigido en pesos colombianos (COP). Si se expresa en SMMLV, multiplícalo por $1,300,000 COP para convertirlo. Si no está definido, pon 0.
        3. experiencia_minima_contratos: El número mínimo de contratos previos que el proponente debe certificar. Si no se especifica, pon 0.
        4. financiero_liquidez: El indicador de liquidez mínimo exigido (ej: ">= 1.5"). Si no está, pon "No Definido".
        5. financiero_endeudamiento: El indicador de endeudamiento máximo permitido (ej: "<= 0.7"). Si no está, pon "No Definido".
        6. personal_requerido: Una lista de los perfiles de personal clave requeridos en los pliegos (ej: ["Archivista Profesional", "Ingeniero de Sistemas", "Director de Proyecto"]). Si no hay específicos, pon una lista vacía.

        Texto del Pliego:
        {combined_text[:60000]}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RequisitosModel,
                temperature=0.1
            )
        )
        
        # Parse result
        import json
        res_dict = json.loads(response.text)
        print("Gemini successfully extracted requirements:")
        print(res_dict)
        return res_dict
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        traceback.print_exc()
        return None

def save_to_bigquery(process_id: str, reqs: dict):
    """Save the extracted requirements dictionary to BQ secop.procesos_requisitos table."""
    client = bigquery.Client(project="odin-v2-495523")
    table_id = "odin-v2-495523.secop.procesos_requisitos"
    
    row = {
        "id_del_proceso": process_id,
        "experiencia_unspsc": reqs.get("experiencia_unspsc", []),
        "experiencia_minima_cop": reqs.get("experiencia_minima_cop", 0),
        "experiencia_minima_contratos": reqs.get("experiencia_minima_contratos", 0),
        "financiero_liquidez": reqs.get("financiero_liquidez", "No Definido"),
        "financiero_endeudamiento": reqs.get("financiero_endeudamiento", "No Definido"),
        "personal_requerido": reqs.get("personal_requerido", []),
        "ultima_actualizacion": datetime.now().isoformat()
    }
    
    errors = client.insert_rows_json(table_id, [row])
    if not errors:
        print(f"Successfully cached requirements for {process_id} in BigQuery.")
    else:
        print(f"Failed to insert row in BigQuery: {errors}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_requirements.py <notice_uid> <process_id>")
        sys.exit(1)
        
    notice_uid = sys.argv[1]
    process_id = sys.argv[2]
    
    reqs = download_and_extract_requirements(notice_uid)
    if reqs:
        save_to_bigquery(process_id, reqs)
        print("Process completed successfully.")
    else:
        print("Failed to extract requirements.")
