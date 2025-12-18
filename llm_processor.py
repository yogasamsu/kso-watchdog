import json
import streamlit as st
from groq import Groq

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def analyze_regulation(text_content):
    """
    Analyzes the extracted PDF text using the specific VPTI Compliance Prompt.
    """
    system_prompt = """
    You are a Trade Compliance AI. Analyze the Indonesian regulation text.
    You MUST output ONLY valid JSON. Do not add markdown formatting like ```json.
    
    Required JSON Structure:
    {
        "english_title": "Translated Title",
        "status": "New/Amendment/Revocation",
        "commodity": "Commodity Name or 'General'",
        "vpti_impact": "High/Medium/Low",
        "key_changes": "Brief summary of changes (1-2 sentences)",
        "action_required": "What must the surveyor/importer do?"
    }
    """
    
    # Safety: If no PDF text was found, handle it gracefully
    if not text_content or len(text_content) < 50:
        return {
            "english_title": "PDF Read Failed",
            "status": "Unknown",
            "commodity": "Unknown",
            "vpti_impact": "Unknown",
            "key_changes": "Could not extract text from PDF.",
            "action_required": "Check manually."
        }

    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this text:\n{text_content[:15000]}"}
            ],
            model="llama-3.1-8b-instant",
            temperature=0,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        return {
            "english_title": "Error",
            "key_changes": str(e)
        }