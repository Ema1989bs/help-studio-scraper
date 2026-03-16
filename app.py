import streamlit as st
import asyncio
from crawl4ai import AsyncWebCrawler
import anthropic
import pandas as pd
import io
import json
import os
import subprocess
import sys

# Forza l'installazione dei browser se siamo nel cloud
try:
    import playwright
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
# Setup pagina
st.set_page_config(page_title="Help-Studio Scraper", layout="wide")

# Recupero chiave segreta dai Secrets di Streamlit
if "ANTHROPIC_API_KEY" in st.secrets:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
else:
    st.error("Configura 'ANTHROPIC_API_KEY' nei Secrets di Streamlit Cloud.")
    st.stop()

async def scrape_site(url):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        return result.markdown

st.title("🤖 Help-Studio: Universal AI Scraper")

url = st.text_input("Inserisci URL:")
task = st.text_area("Cosa vuoi estrarre?", "Crea una tabella con i dati principali.")

if st.button("Avvia Analisi"):
    if url:
        with st.spinner("L'AI sta lavorando..."):
            try:
                # Esecuzione scraping
                content = asyncio.run(scrape_site(url))
                
                # Chiamata a Claude
                response = client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=4000,
                    system="Rispondi SOLO con un JSON. Struttura: {'dati': [...]}",
                    messages=[{"role": "user", "content": f"{task}\n\nTesto: {content[:15000]}"}]
                )
                
                res_json = json.loads(response.content[0].text)
                df = pd.DataFrame(res_json['dati'])
                st.dataframe(df)
                
                # Export Excel
                output = io.BytesIO()
                df.to_excel(output, index=False, engine='openpyxl')
                st.download_button("📥 Scarica Excel", output.getvalue(), "estrazione.xlsx")
            except Exception as e:
                st.error(f"Errore: {e}")
