import requests
from bs4 import BeautifulSoup
import pdfplumber
import io
import datetime
import re
import time

# --- CORRECTED CONFIGURATION ---
BASE_URL = "https://jdih.kemendag.go.id"
# RESTORED TO THE PATTERN THAT WORKS:
TARGET_URL_TEMPLATE = "https://jdih.kemendag.go.id/peraturan?page={}" 

def parse_indonesian_date(text):
    """Extracts date like '20 Januari 2024' -> '2024-01-20'"""
    month_map = {
        "Januari": "01", "Februari": "02", "Maret": "03", "April": "04",
        "Mei": "05", "Juni": "06", "Juli": "07", "Agustus": "08",
        "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
    }
    match = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if match:
        day, month_name, year = match.groups()
        month = month_map.get(month_name, "01")
        return f"{year}-{month}-{day.zfill(2)}"
    return datetime.datetime.now().strftime("%Y-%m-%d")

def fetch_links_from_page(page_number):
    """
    Step 1: Get the list of regulations from the index page.
    """
    url = TARGET_URL_TEMPLATE.format(page_number)
    print(f"DEBUG: Scanning Index {url}...")
    
    try:
        # Added headers to look like a real browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        items = []
        found_links = set()
        
        # Robust "Scan All Links" strategy
        all_link_tags = soup.find_all('a', href=True)
        print(f"   -> Found {len(all_link_tags)} raw links on page. Filtering...") # DEBUG PRINT

        for link_tag in all_link_tags:
            href = link_tag['href']
            
            # Filter: Must be a regulation link
            if "/peraturan/" not in href and "/dokumen-hukum/" not in href: continue
            if href in found_links or "download" in href.lower(): continue
            
            full_link = href if href.startswith("http") else BASE_URL + href
            title = link_tag.get_text(" ", strip=True)
            
            # Skip tiny titles (usually navigation buttons)
            if len(title) < 10: continue
            
            # Find date in parent container
            iso_date = parse_indonesian_date(link_tag.parent.get_text(" ", strip=True))
            
            found_links.add(href)
            items.append({
                "original_title": title,
                "date": iso_date,
                "link": full_link
            })
            
        print(f"   -> ✅ Valid Regulations Found: {len(items)}")
        return items
    except Exception as e:
        print(f"❌ Error scanning page {page_number}: {e}")
        return []

def extract_text_from_pdf(url):
    """
    Step 2: Go to the detail page, find the PDF, and extract text.
    """
    print(f"   🔎 Extracting PDF text from: {url}")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        pdf_url = None
        for a in soup.find_all('a', href=True):
            if a['href'].lower().endswith('.pdf') or "unduh" in a.get_text().lower():
                pdf_url = a['href']
                break
        
        if not pdf_url: 
            print("      ⚠️ No PDF link found on page.")
            return None
            
        if not pdf_url.startswith("http"): 
            pdf_url = BASE_URL + "/" + pdf_url.lstrip("/")

        # Download PDF to Memory
        pdf_resp = requests.get(pdf_url, headers=headers, stream=True)
        
        # Extract Text (First 3 pages)
        text_content = ""
        with pdfplumber.open(io.BytesIO(pdf_resp.content)) as pdf:
            max_pages = min(3, len(pdf.pages))
            for i in range(max_pages):
                extracted = pdf.pages[i].extract_text()
                if extracted: 
                    text_content += extracted + "\n"
        
        print(f"      📄 Extracted {len(text_content)} chars.")
        return text_content
    except Exception as e:
        print(f"      ⚠️ PDF Extraction Failed: {e}")
        return None