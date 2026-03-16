import streamlit as st
import pandas as pd
import asyncio
from crawl4ai import AsyncWebCrawler
import anthropic
import json
import io

# Configurazione
st.set_page_config(page_title="Help-Studio AI Scraper", layout="wide")

# API Key dai Secrets di Streamlit
if "ANTHROPIC_API_KEY" in st.secrets:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
else:
    st.error("Errore: Inserisci la chiave ANTHROPIC_API_KEY nei Secrets di Streamlit.")
    st.stop()

st.title("🤖 Help-Studio: Universal AI Web Scraper")

url_to_scrape = st.text_input("URL da analizzare:")
instruction = st.text_area("Cosa vuoi estrarre?", "Estrai i dati in una tabella.")

async def run_scraping(url):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        return result.markdown

if st.button("🚀 Avvia"):
    if url_to_scrape:
        with st.spinner("Scansione in corso..."):
            try:
                # Esecuzione asincrona compatibile con il cloud
                markdown_content = asyncio.run(run_scraping(url_to_scrape))
                
                # Chiamata a Claude
                response = client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=4000,
                    system="Rispondi SOLO con un JSON. Struttura: {'dati': [...]}",
                    messages=[{"role": "user", "content": f"{instruction}\n\nTesto: {markdown_content[:18000]}"}]
                )
                
                data_json = json.loads(response.content[0].text)
                df = pd.DataFrame(data_json['dati'])
                
                st.dataframe(df)
                
                buffer = io.BytesIO()
                df.to_excel(buffer, index=False, engine='openpyxl')
                st.download_button("📥 Scarica Excel", buffer.getvalue(), "report_helpstudio.xlsx")
                
            except Exception as e:
                st.error(f"Errore: {e}")
