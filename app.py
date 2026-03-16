import streamlit as st
import pandas as pd
import asyncio
from crawl4ai import AsyncWebCrawler
import anthropic
import json
import io
import os

# Configurazione Pagina
st.set_page_config(page_title="Help-Studio AI Scraper", layout="wide")
st.title("🤖 Help-Studio: Universal AI Web Scraper")

# Gestione API Key dai Secrets di Streamlit
if "ANTHROPIC_API_KEY" in st.secrets:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
else:
    st.error("Inserisci la chiave 'ANTHROPIC_API_KEY' nei Secrets di Streamlit Cloud.")
    st.stop()

# Interfaccia Sidebar
with st.sidebar:
    st.header("Configurazione")
    output_format = st.selectbox("Formato Output", ["Excel", "CSV"])

url_to_scrape = st.text_input("URL del sito da analizzare:", placeholder="https://esempio.it")
instruction = st.text_area("Cosa vuoi estrarre?", "Estrai i dati in una tabella.")

async def get_web_content(url):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        return result.markdown

if st.button("Avvia Analisi"):
    if not url_to_scrape:
        st.error("Per favore, inserisci un URL.")
    else:
        with st.spinner("L'AI sta leggendo il sito..."):
            try:
                # 1. Scraping Asincrono
                markdown_content = asyncio.run(get_web_content(url_to_scrape))

                # 2. Elaborazione con Claude
                message = client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=4000,
                    system="Rispondi SOLO in JSON. Struttura: {'dati': [...]}.",
                    messages=[{"role": "user", "content": f"{instruction}\n\nContenuto:\n{markdown_content[:15000]}"}]
                )
                
                raw_json = json.loads(message.content[0].text)
                data = raw_json.get('dati', [])

                if data:
                    df = pd.DataFrame(data)
                    st.success("Dati estratti!")
                    st.dataframe(df)

                    # 3. Download
                    buffer = io.BytesIO()
                    if output_format == "Excel":
                        df.to_excel(buffer, index=False, engine='openpyxl')
                        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        fn = "estrazione.xlsx"
                    else:
                        buffer.write(df.to_csv(index=False).encode('utf-8'))
                        mime = "text/csv"
                        fn = "estrazione.csv"

                    st.download_button("Scarica File", buffer.getvalue(), file_name=fn, mime=mime)
                
            except Exception as e:
                st.error(f"Errore: {e}")
