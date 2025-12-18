import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "regulations.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Updated Schema to match your "Correct" script
    c.execute('''
        CREATE TABLE IF NOT EXISTS regulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            regulation_date TEXT, 
            original_title TEXT,
            english_title TEXT,
            status TEXT,
            commodity TEXT,
            vpti_impact TEXT,
            summary TEXT,
            action_required TEXT,
            raw_link TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_regulation(data):
    """
    Saves a dictionary of data to the DB.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute('''
        INSERT INTO regulations (
            timestamp, regulation_date, original_title, english_title, 
            status, commodity, vpti_impact, summary, action_required, raw_link
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        timestamp, 
        data.get('date', 'Unknown'),
        data.get('original_title', 'Unknown'),
        data.get('english_title', 'N/A'),
        data.get('status', 'New'),
        data.get('commodity', 'General'),
        data.get('vpti_impact', 'Low'),
        data.get('key_changes', 'No summary'), # Mapping 'key_changes' to 'summary'
        data.get('action_required', 'None'),
        data.get('link', '')
    ))
    conn.commit()
    conn.close()

def get_all_regulations():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM regulations ORDER BY regulation_date DESC", conn)
    conn.close()
    return df

def get_latest_date():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT MAX(regulation_date) FROM regulations")
    result = c.fetchone()[0]
    conn.close()
    return result