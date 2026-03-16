import streamlit as st
import pandas as pd
import asyncio
from crawl4ai import AsyncWebCrawler
import anthropic
import json
import io

# Configurazione Pagina
st.set_page_config(page_title="Help-Studio AI Scraper", layout="wide")
st.title("🤖 Help-Studio: Universal AI Web Scraper")

# Recupero API Key dai Secrets di Streamlit
try:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
except Exception:
    st.error("Configura la ANTHROPIC_API_KEY nei Secrets di Streamlit Cloud.")
    st.stop()

# Interfaccia
with st.sidebar:
    st.header("📊 Area Clienti")
    st.write("Servizio gestito da **Help-Studio**")
    output_format = st.selectbox("Formato file", ["Excel", "CSV"])

url_to_scrape = st.text_input("Inserisci l'URL da analizzare:", placeholder="https://www.esempio.it")
instruction = st.text_area("Cosa deve fare l'AI?", "Estrai i dati principali in una tabella con colonne chiare.")

async def get_web_content(url):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        return result.markdown

if st.button("🚀 Avvia Elaborazione"):
    if not url_to_scrape:
        st.warning("Per favore, inserisci un URL.")
    else:
        with st.spinner("L'AI sta scansionando il sito... attendi..."):
            try:
                # Esecuzione scraping
                markdown_content = asyncio.run(get_web_content(url_to_scrape))
                
                # Chiamata a Claude 3.5 Sonnet
                response = client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=4000,
                    system="Estrai i dati e rispondi SOLO con un JSON. Il JSON deve contenere una lista di oggetti sotto la chiave 'dati'.",
                    messages=[{"role": "user", "content": f"Istruzione: {instruction}\n\nTesto:\n{markdown_content[:18000]}"}]
                )
                
                data_json = json.loads(response.content[0].text)
                df = pd.DataFrame(data_json['dati'])
                
                st.success("Estrazione completata!")
                st.dataframe(df)

                # Gestione Download
                buffer = io.BytesIO()
                if output_format == "Excel":
                    df.to_excel(buffer, index=False, engine='openpyxl')
                    file_ext, mime = "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                else:
                    buffer.write(df.to_csv(index=False).encode('utf-8'))
                    file_ext, mime = "csv", "text/csv"

                st.download_button(f"📥 Scarica {output_format}", buffer.getvalue(), f"estrazione_helpstudio.{file_ext}", mime)

            except Exception as e:
                st.error(f"Errore durante l'elaborazione: {e}")