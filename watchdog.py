import requests
from bs4 import BeautifulSoup
import pdfplumber
import io
import time

# --- CONFIGURATION ---
BASE_URL = "https://jdih.kemendag.go.id"
# Based on standard web pagination, usually it's /peraturan?page=X or /peraturan/index/X
# We will assume a standard structure, but this might need tweaking if the URL pattern is unique.
TARGET_URL_TEMPLATE = "https://jdih.kemendag.go.id/peraturan?page={}" 

PAGES_TO_SCAN = 5  # User requirement: Only scan the latest 5 pages

def scan_website_pages():
    """
    Loops through the first 5 pagination pages of the JDIH website.
    """
    all_regulation_links = []
    
    print(f"🐶 Watchdog: Starting scan of the first {PAGES_TO_SCAN} pages...")

    for page_num in range(1, PAGES_TO_SCAN + 1):
        # specific handling for page 1 usually doesn't need query params, 
        # but most frameworks handle ?page=1 correctly.
        current_url = TARGET_URL_TEMPLATE.format(page_num)
        
        print(f"   -> Scanning Page {page_num}: {current_url}")
        
        try:
            # Add headers to look like a real browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(current_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                print(f"      ❌ Failed to load page {page_num} (Status: {response.status_code})")
                continue

            soup = BeautifulSoup(response.content, 'html.parser')
            
            # --- EXTRACT LINKS FROM THIS PAGE ---
            # We look for "Detail" links or Regulation Titles
            # Based on your screenshot, it's a card layout. 
            # We look for the 'href' in the 'DETAIL ->' buttons or the Titles.
            
            found_on_page = 0
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True).lower()
                
                # Filter logic: 
                # 1. Must be a regulation link (usually contains /peraturan/ or /dokumen/)
                # 2. We skip 'download' links here, we want the DETAIL page first.
                if "/peraturan/" in href or "/dokumen-hukum/" in href:
                    
                    # specific keyword filter to ensure it's relevant (optional but recommended)
                    # For now, we grab everything to ensure we don't miss anything on these 5 pages.
                    
                    full_link = href if href.startswith("http") else BASE_URL + href
                    
                    if full_link not in all_regulation_links:
                        all_regulation_links.append(full_link)
                        found_on_page += 1
            
            print(f"      ✅ Found {found_on_page} regulations on Page {page_num}")
            
            # Be polite to the server
            time.sleep(1) 

        except Exception as e:
            print(f"      ⚠️ Error scanning page {page_num}: {e}")

    return all_regulation_links

def extract_text_from_url(detail_url):
    """
    (Reused from previous step)
    Visits the detail page -> Finds PDF -> Downloads to RAM -> Extracts Pages 1-3
    """
    print(f"   🔎 Processing: {detail_url}")
    try:
        response = requests.get(detail_url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find PDF Link
        pdf_url = None
        for a in soup.find_all('a', href=True):
            if a['href'].lower().endswith('.pdf') or "unduh" in a.get_text().lower():
                pdf_url = a['href']
                break
        
        if not pdf_url: 
            return None # Skip if no PDF found

        if not pdf_url.startswith("http"):
            pdf_url = BASE_URL + "/" + pdf_url.lstrip("/")

        # Download to Memory
        pdf_response = requests.get(pdf_url, stream=True)
        
        # Extract Text
        text_content = ""
        with pdfplumber.open(io.BytesIO(pdf_response.content)) as pdf:
            # LIMIT: First 3 pages only
            max_pages = min(3, len(pdf.pages))
            for i in range(max_pages):
                extracted = pdf.pages[i].extract_text()
                if extracted:
                    text_content += extracted + "\n"
        
        return text_content

    except Exception as e:
        # print(f"Error: {e}") # Silent error to keep console clean
        return None

# --- MAIN ORCHESTRATOR ---
if __name__ == "__main__":
    print("🚀 STARTING MULTI-PAGE CRAWLER (Last 5 Pages)...")
    
    # 1. Get all links from the last 5 pages
    all_links = scan_website_pages()
    print(f"\n📦 Total unique regulations found: {len(all_links)}")
    
    # 2. Process the first 3 (for demo purposes) 
    # In production, you would loop through ALL of them.
    print("\n🧪 Processing the first 3 results as a test...")
    
    for i, link in enumerate(all_links[:3]): 
        print(f"\n--- Document {i+1} ---")
        text = extract_text_from_url(link)
        
        if text:
            print(f"✅ Text Extracted ({len(text)} chars). Ready for AI.")
            print(f"SAMPLE: {text[:200]}...") # Show snippet
        else:
            print("❌ Failed to extract text (No PDF or Error).")