import streamlit as st
import pandas as pd
import database
import crawler
import llm_processor

# --- CONFIG & INIT ---
st.set_page_config(page_title="VPTI Regulatory Watch", layout="wide")
database.init_db()

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Controls")
    
    if st.button("🔄 Check New Regulation", type="primary"):
        status = st.empty()
        
        with st.spinner("Initializing Scan..."):
            last_db_date = database.get_latest_date()
            if not last_db_date: last_db_date = "1900-01-01"
            
            status.info(f"Scanning for regulations newer than: **{last_db_date}**")
            
            # 1. SCAN INDEX (Find links)
            new_items = []
            stop = False
            
            # Scan pages 1 to 5 (adjust as needed)
            for page in range(1, 6):
                if stop: break
                
                page_links = crawler.fetch_links_from_page(page)
                if not page_links: break
                
                for item in page_links:
                    if item['date'] <= last_db_date:
                        stop = True
                        break
                    new_items.append(item)
            
            # 2. DEEP PROCESS (Download PDF & Analyze)
            if new_items:
                status.info(f"Found {len(new_items)} new items. Starting Deep Analysis...")
                progress = st.progress(0)
                
                for i, item in enumerate(new_items):
                    # A. Get PDF Text
                    pdf_text = crawler.extract_text_from_pdf(item['link'])
                    
                    # B. LLM Analyze
                    analysis = llm_processor.analyze_regulation(pdf_text if pdf_text else item['original_title'])
                    
                    # C. Merge & Save
                    full_record = {**item, **analysis} # Merge dicts
                    database.save_regulation(full_record)
                    
                    progress.progress((i + 1) / len(new_items))
                
                status.success("✅ Database Updated!")
                st.rerun()
            else:
                status.success("✅ System is up to date.")

# --- MAIN DASHBOARD ---
st.title("🚢 VPTI Regulatory Watch")
st.markdown("Automated compliance monitoring for **Trade Regulations**.")

df = database.get_all_regulations()

if not df.empty:
    # Key Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Regulations", len(df))
    col2.metric("Latest Update", df['regulation_date'].max())
    col3.metric("High Impact", len(df[df['vpti_impact'] == 'High']))

    st.divider()

    # Detailed Table
    df.insert(0, "Select", False)
    
    edited_df = st.data_editor(
        df,
        column_config={
            "Select": st.column_config.CheckboxColumn("Export", default=False),
            "raw_link": st.column_config.LinkColumn("Source PDF"),
            "vpti_impact": st.column_config.TextColumn("Impact"),
            "status": st.column_config.TextColumn("Status"),
            "english_title": "Translated Title",
            "commodity": "Commodity"
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Download Button logic (Same as before)
    # ... (You can copy the download button code from previous versions) ...

else:
    st.info("No data yet. Click the button in the sidebar to scan.")