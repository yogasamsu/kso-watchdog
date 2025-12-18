import requests
from bs4 import BeautifulSoup
import pdfplumber
import io
import time
import csv
import json
import os
from datetime import datetime
from groq import Groq

# --- CONFIGURATION ---
# ⚠️ REPLACE WITH YOUR ACTUAL GROQ API KEY

BASE_URL = "https://jdih.kemendag.go.id"
TARGET_URL_TEMPLATE = "https://jdih.kemendag.go.id/peraturan?page={}" 
PAGES_TO_SCAN = 1  
CSV_FILENAME = "vpti_regulatory_log.csv"

# Initialize Groq
client = Groq(api_key=GROQ_API_KEY)

# --- MODULE 1: THE ANALYST (JSON OUTPUT) ---
def analyze_regulation_with_groq(text_content):
    """
    Sends text to Groq and requests a JSON response for easy CSV saving.
    """
    print("   ⚡ Analyst: Blasting text to Groq (Requesting JSON)...")
    
    system_prompt = """
    You are a Trade Compliance AI. Analyze the Indonesian regulation text.
    You MUST output ONLY valid JSON. Do not add markdown formatting like ```json.
    
    Required JSON Structure:
    {
        "english_title": "Translated Title",
        "status": "New/Amendment/Revocation",
        "commodity": "Commodity Name or 'General'",
        "effective_date": "YYYY-MM-DD or 'Immediately'",
        "vpti_impact": "High/Medium/Low",
        "key_changes": "Brief summary of changes",
        "action_required": "What must the surveyor do?"
    }
    """

    user_prompt = f"""
    Analyze this text (first 3 pages):
    {text_content[:15000]}
    """

    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0, # Zero temp for strict JSON adherence
            response_format={"type": "json_object"} # Forces JSON mode
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"❌ Groq/JSON Error: {e}")
        return None

# --- MODULE 2: THE CSV SAVER ---
def save_to_csv(data_dict):
    """
    Appends the analyzed data to a CSV file.
    """
    file_exists = os.path.isfile(CSV_FILENAME)
    
    # Define Column Headers
    fieldnames = [
        "scan_date", "original_url", "english_title", "status", 
        "commodity", "effective_date", "vpti_impact", 
        "key_changes", "action_required"
    ]

    try:
        with open(CSV_FILENAME, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            # Write header only if file didn't exist
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(data_dict)
            print(f"   💾 Saved to {CSV_FILENAME}")
            
    except Exception as e:
        print(f"❌ CSV Write Error: {e}")

# --- MODULE 3: CRAWLER & EXTRACTOR ---
def scan_website_pages():
    all_links = []
    print(f"🐶 Watchdog: Scanning first {PAGES_TO_SCAN} pages...")
    for page_num in range(1, PAGES_TO_SCAN + 1):
        url = TARGET_URL_TEMPLATE.format(page_num)
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(resp.content, 'html.parser')
            for link in soup.find_all('a', href=True):
                if "/peraturan/" in link['href'] or "/dokumen-hukum/" in link['href']:
                    full = link['href'] if link['href'].startswith("http") else BASE_URL + link['href']
                    if full not in all_links: all_links.append(full)
        except Exception: pass
    return all_links

def extract_text_from_url(url):
    print(f"   🔎 Visiting: {url}")
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        pdf_url = None
        for a in soup.find_all('a', href=True):
            if a['href'].lower().endswith('.pdf') or "unduh" in a.get_text().lower():
                pdf_url = a['href']
                break
        
        if not pdf_url: return None
        if not pdf_url.startswith("http"): pdf_url = BASE_URL + "/" + pdf_url.lstrip("/")

        pdf_resp = requests.get(pdf_url, stream=True)
        text = ""
        with pdfplumber.open(io.BytesIO(pdf_resp.content)) as pdf:
            for i in range(min(3, len(pdf.pages))):
                extracted = pdf.pages[i].extract_text()
                if extracted: text += extracted + "\n"
        return text
    except Exception: return None

# --- MAIN ORCHESTRATOR ---
if __name__ == "__main__":
    links = scan_website_pages()
    print(f"\n📦 Found {len(links)} regulations. Processing top 3...\n")
    
    count = 0
    for link in links:
        if count >= 3: break
        
        print(f"--- Document {count + 1} ---")
        raw_text = extract_text_from_url(link)
        
        if raw_text:
            # 1. Analyze
            analysis_json = analyze_regulation_with_groq(raw_text)
            
            if analysis_json:
                # 2. Add Metadata
                analysis_json['scan_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                analysis_json['original_url'] = link
                
                # 3. Save to CSV
                save_to_csv(analysis_json)
                
                print(f"      ✅ Title: {analysis_json.get('english_title', 'N/A')}")
                count += 1
        else:
            print("      ❌ Text extraction failed.")
        print("-" * 50)