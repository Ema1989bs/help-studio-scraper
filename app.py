import streamlit as st
import pandas as pd
import asyncio
from crawl4ai import AsyncWebCrawler
import anthropic
import json
import io
import os
import uuid
from datetime import datetime

# ── Page Config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mr. Wine · Gestione Catalogo",
    page_icon="🍷",
    layout="wide"
)

# ── Data Persistence ──────────────────────────────────────────────────────
WINES_FILE = "wines.json"

def load_wines():
    if os.path.exists(WINES_FILE):
        with open(WINES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_wines(wines):
    with open(WINES_FILE, "w", encoding="utf-8") as f:
        json.dump(wines, f, ensure_ascii=False, indent=2)

if "wines" not in st.session_state:
    st.session_state.wines = load_wines()
if "ai_loaded" not in st.session_state:
    st.session_state.ai_loaded = {}
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

# ── API Client ────────────────────────────────────────────────────────────
if "ANTHROPIC_API_KEY" in st.secrets:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
else:
    st.error("⚠️ Inserisci la chiave 'ANTHROPIC_API_KEY' nei Secrets di Streamlit Cloud.")
    st.stop()

# ── AI Helpers ────────────────────────────────────────────────────────────
async def _scrape(url: str) -> str:
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        return result.markdown

def scrape_url(url: str) -> str:
    return asyncio.run(_scrape(url))

def ai_extract_wine(content: str) -> dict:
    prompt = f"""Analizza il contenuto di questa pagina web su un vino e restituisci SOLO un JSON valido
(senza markdown, senza backtick) con questa struttura esatta (usa null per i campi non trovati):

{{
  "nome": "nome del vino",
  "produttore": "nome produttore/cantina",
  "categoria": "Champagne|Rosso|Bianco|Rosé|Spumante|Altro",
  "regione": "regione e paese (es. Toscana, Italia)",
  "vitigni": "vitigni separati da virgola",
  "annata": "anno come stringa o null",
  "descrizione": "descrizione sintetica del vino (max 200 caratteri)",
  "badge": "etichetta breve promozionale (es. CLASSICO, TOP, RISERVA, VIGNERON D'ÉLITE) o null",
  "prezzo_bottiglia": numero decimale o null,
  "prezzo_cassa": numero decimale o null,
  "immagine_url": "URL immagine principale o null"
}}

Contenuto pagina:
{content[:12000]}"""

    msg = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=2000,
        system="Sei un esperto sommelier e catalogatore di vini. Rispondi SOLO con JSON valido.",
        messages=[{"role": "user", "content": prompt}]
    )
    text = msg.content[0].text.strip()
    # Strip markdown fences if present
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)

# ── Styles ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="metric-container"] { background: #1a0a0a; padding: 8px 12px; border-radius: 6px; }
    .wine-name { font-size: 1.05rem; font-weight: 700; margin: 0; }
    .wine-producer { font-size: 0.8rem; color: #888; margin: 0 0 6px 0; }
    .badge-pill {
        display: inline-block;
        background: #7a1a1a;
        color: #f5e6c8;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 1px;
        padding: 2px 8px;
        border-radius: 20px;
        margin-bottom: 6px;
    }
    .price-row { margin-top: 6px; }
    .price-original { text-decoration: line-through; color: #777; font-size: 0.85rem; }
    .price-sale { color: #e8c87a; font-size: 1.1rem; font-weight: 700; }
    .status-pill-esaurito {
        background: #3a0000; color: #ff6b6b;
        padding: 2px 10px; border-radius: 20px;
        font-size: 0.75rem; font-weight: 700;
    }
    .status-pill-prossimamente {
        background: #1a1a00; color: #e8c87a;
        padding: 2px 10px; border-radius: 20px;
        font-size: 0.75rem; font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
with c1:
    st.title("🍷 Mr. Wine · Gestione Catalogo")
wines = st.session_state.wines
disp = sum(1 for w in wines if w.get("stato","disponibile") == "disponibile")
esau = sum(1 for w in wines if w.get("stato") == "esaurito")
pros = sum(1 for w in wines if w.get("stato") == "prossimamente")
with c2:
    st.metric("Totale vini", len(wines))
with c3:
    st.metric("Disponibili", disp)
with c4:
    st.metric("Esauriti", esau)

# ── Tabs ──────────────────────────────────────────────────────────────────
tab_cat, tab_add, tab_manage, tab_io = st.tabs([
    "📖 Catalogo",
    "✨ Aggiungi Vino",
    "⚙️ Gestisci",
    "📥 Import / Export"
])

# ═════════════════════════════════════════════════════════════════════════
# TAB 1 · CATALOGO
# ═════════════════════════════════════════════════════════════════════════
with tab_cat:
    if not wines:
        st.info("Nessun vino in catalogo. Aggiungine uno dalla tab **✨ Aggiungi Vino**.")
    else:
        fc1, fc2, fc3 = st.columns([2, 2, 3])
        with fc1:
            categorie = ["Tutte"] + sorted({w.get("categoria","Altro") for w in wines})
            cat_f = st.selectbox("Categoria", categorie, key="cat_f")
        with fc2:
            stato_f = st.selectbox("Stato", ["Tutti", "Disponibile", "Esaurito", "Prossimamente"], key="stato_f")
        with fc3:
            search_f = st.text_input("🔍 Cerca nome / produttore", "", key="search_f")

        filt = wines[:]
        if cat_f != "Tutte":
            filt = [w for w in filt if w.get("categoria") == cat_f]
        stato_map = {"Disponibile":"disponibile", "Esaurito":"esaurito", "Prossimamente":"prossimamente"}
        if stato_f != "Tutti":
            filt = [w for w in filt if w.get("stato","disponibile") == stato_map[stato_f]]
        if search_f:
            s = search_f.lower()
            filt = [w for w in filt if s in w.get("nome","").lower() or s in w.get("produttore","").lower()]

        st.caption(f"**{len(filt)}** vini trovati")

        cols = st.columns(3)
        for i, w in enumerate(filt):
            with cols[i % 3]:
                with st.container(border=True):
                    if w.get("badge"):
                        st.markdown(f'<span class="badge-pill">{w["badge"]}</span>', unsafe_allow_html=True)

                    st.markdown(f'<p class="wine-name">{w.get("nome","—")}</p>', unsafe_allow_html=True)
                    st.markdown(f'<p class="wine-producer">{w.get("produttore","")}</p>', unsafe_allow_html=True)

                    info_parts = []
                    if w.get("regione"):
                        info_parts.append(f"📍 {w['regione']}")
                    if w.get("vitigni"):
                        info_parts.append(f"🍇 {w['vitigni']}")
                    if w.get("annata"):
                        info_parts.append(f"📅 {w['annata']}")
                    if info_parts:
                        st.caption(" · ".join(info_parts))

                    if w.get("descrizione"):
                        desc = w["descrizione"]
                        st.caption(desc[:120] + "…" if len(desc) > 120 else desc)

                    stato = w.get("stato", "disponibile")
                    if stato == "esaurito":
                        st.markdown('<span class="status-pill-esaurito">ESAURITO</span>', unsafe_allow_html=True)
                    elif stato == "prossimamente":
                        st.markdown('<span class="status-pill-prossimamente">PROSSIMAMENTE</span>', unsafe_allow_html=True)
                    else:
                        pb  = w.get("prezzo_bottiglia")
                        pbs = w.get("prezzo_scontato_bottiglia")
                        pc  = w.get("prezzo_scontato_cassa") or w.get("prezzo_cassa")

                        if pb:
                            if pbs and float(pbs) < float(pb):
                                st.markdown(
                                    f'<div class="price-row">'
                                    f'<span class="price-original">pt {float(pb):.0f}</span> '
                                    f'<span class="price-sale">pt {float(pbs):.0f}</span>'
                                    f' <span style="font-size:0.75rem;color:#888">/ bott.</span></div>',
                                    unsafe_allow_html=True
                                )
                            else:
                                st.markdown(
                                    f'<div class="price-row"><span class="price-sale">pt {float(pb):.0f}</span>'
                                    f' <span style="font-size:0.75rem;color:#888">/ bott.</span></div>',
                                    unsafe_allow_html=True
                                )
                        if pc:
                            st.caption(f"pt {float(pc):.0f} / cassa")

# ═════════════════════════════════════════════════════════════════════════
# TAB 2 · AGGIUNGI VINO
# ═════════════════════════════════════════════════════════════════════════
with tab_add:
    st.subheader("Aggiungi Nuovo Vino")

    # ── AI URL Loader (il punto centrale) ─────────────────────────────
    with st.container(border=True):
        st.markdown("### 🤖 Caricamento Automatico da URL")
        st.caption(
            "Incolla l'URL di una pagina vino (Vivino, sito cantina, enoteca online…) "
            "e l'AI compilerà **tutti i campi automaticamente** in pochi secondi."
        )
        url_ai = st.text_input(
            "URL del vino",
            placeholder="https://www.vivino.com/wines/1234  oppure  https://www.cantina.it/vino",
            key="url_ai"
        )
        if st.button("🚀 Carica con AI", type="primary", key="ai_load_btn"):
            if not url_ai.strip():
                st.warning("Inserisci un URL valido.")
            else:
                with st.spinner("Sto leggendo la pagina e compilando i campi…"):
                    try:
                        content = scrape_url(url_ai.strip())
                        data = ai_extract_wine(content)
                        st.session_state.ai_loaded = data
                        st.success("✅ Dati estratti! Controlla i campi qui sotto e clicca **Salva Vino**.")
                    except Exception as e:
                        st.error(f"Errore durante il caricamento: {e}")

    st.divider()

    # ── Modulo (pre-compilato dall'AI o manuale) ───────────────────────
    ai = st.session_state.ai_loaded

    def _str(v):
        return str(v) if v not in (None, "null", "None") else ""

    def _float(v):
        try:
            return float(v) if v not in (None, "null", "None", "") else 0.0
        except Exception:
            return 0.0

    CATEGORIE = ["Champagne", "Rosso", "Bianco", "Rosé", "Spumante", "Altro"]
    STATI = ["disponibile", "esaurito", "prossimamente"]

    if ai:
        st.info("Campi pre-compilati dall'AI — modifica se necessario prima di salvare.")

    with st.form("add_wine_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            nome       = st.text_input("Nome vino *",         value=_str(ai.get("nome")))
            produttore = st.text_input("Produttore *",        value=_str(ai.get("produttore")))
            cat_val    = ai.get("categoria", "Rosso")
            cat_idx    = CATEGORIE.index(cat_val) if cat_val in CATEGORIE else 1
            categoria  = st.selectbox("Categoria *",          CATEGORIE, index=cat_idx)
            regione    = st.text_input("Regione / Paese",     value=_str(ai.get("regione")))
            vitigni    = st.text_input("Vitigni",             value=_str(ai.get("vitigni")))
            annata     = st.text_input("Annata",              value=_str(ai.get("annata")))

        with c2:
            badge      = st.text_input("Badge (es. CLASSICO, TOP, RISERVA)", value=_str(ai.get("badge")))
            stato_val  = ai.get("stato", "disponibile") if ai.get("stato") in STATI else "disponibile"
            stato      = st.selectbox("Stato",                STATI, index=STATI.index(stato_val))
            prezzo_b   = st.number_input("Prezzo bottiglia (pt)",         min_value=0.0, value=_float(ai.get("prezzo_bottiglia")),  step=5.0)
            prezzo_bs  = st.number_input("Prezzo scontato bottiglia (pt)", min_value=0.0, value=_float(ai.get("prezzo_bottiglia")),  step=5.0)
            prezzo_c   = st.number_input("Prezzo cassa (pt)",             min_value=0.0, value=_float(ai.get("prezzo_cassa")),      step=10.0)
            prezzo_cs  = st.number_input("Prezzo scontato cassa (pt)",    min_value=0.0, value=_float(ai.get("prezzo_cassa")),      step=10.0)

        descrizione  = st.text_area("Descrizione",  value=_str(ai.get("descrizione")), height=80)
        immagine_url = st.text_input("URL Immagine", value=_str(ai.get("immagine_url")))

        sb1, sb2 = st.columns([1, 4])
        with sb1:
            save_btn = st.form_submit_button("💾 Salva Vino", type="primary")
        with sb2:
            clear_btn = st.form_submit_button("🗑️ Pulisci campi")

        if save_btn:
            if not nome.strip() or not produttore.strip():
                st.error("Nome e Produttore sono obbligatori.")
            else:
                new_wine = {
                    "id":           str(uuid.uuid4())[:8],
                    "nome":         nome.strip(),
                    "produttore":   produttore.strip(),
                    "categoria":    categoria,
                    "regione":      regione.strip() or None,
                    "vitigni":      vitigni.strip() or None,
                    "annata":       annata.strip() or None,
                    "badge":        badge.strip() or None,
                    "stato":        stato,
                    "prezzo_bottiglia":          prezzo_b  if prezzo_b  > 0 else None,
                    "prezzo_scontato_bottiglia": prezzo_bs if prezzo_bs > 0 else None,
                    "prezzo_cassa":              prezzo_c  if prezzo_c  > 0 else None,
                    "prezzo_scontato_cassa":     prezzo_cs if prezzo_cs > 0 else None,
                    "descrizione":  descrizione.strip() or None,
                    "immagine_url": immagine_url.strip() or None,
                    "data_aggiunta": datetime.now().isoformat()
                }
                st.session_state.wines.append(new_wine)
                save_wines(st.session_state.wines)
                st.session_state.ai_loaded = {}
                st.success(f"✅ **{nome}** aggiunto al catalogo!")
                st.rerun()

        if clear_btn:
            st.session_state.ai_loaded = {}
            st.rerun()

# ═════════════════════════════════════════════════════════════════════════
# TAB 3 · GESTISCI
# ═════════════════════════════════════════════════════════════════════════
with tab_manage:
    st.subheader("Gestisci Vini in Catalogo")

    if not wines:
        st.info("Nessun vino nel catalogo.")
    else:
        # Quick bulk-status editor
        st.markdown("#### Modifica rapida stato")
        df_stato = pd.DataFrame([
            {"#": i, "Nome": w.get("nome",""), "Produttore": w.get("produttore",""),
             "Categoria": w.get("categoria",""), "Stato": w.get("stato","disponibile")}
            for i, w in enumerate(wines)
        ])
        edited = st.data_editor(
            df_stato,
            column_config={
                "Stato": st.column_config.SelectboxColumn(
                    "Stato", options=["disponibile","esaurito","prossimamente"]
                ),
                "#": st.column_config.NumberColumn("#", disabled=True),
                "Nome": st.column_config.TextColumn("Nome", disabled=True),
                "Produttore": st.column_config.TextColumn("Produttore", disabled=True),
                "Categoria": st.column_config.TextColumn("Categoria", disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            key="stato_editor"
        )
        if st.button("💾 Salva modifiche stato", type="primary"):
            for _, row in edited.iterrows():
                st.session_state.wines[int(row["#"])]["stato"] = row["Stato"]
            save_wines(st.session_state.wines)
            st.success("Stati aggiornati.")
            st.rerun()

        st.divider()
        st.markdown("#### Elimina vini")
        for i, w in enumerate(wines):
            col_n, col_d = st.columns([5, 1])
            with col_n:
                icon = {"disponibile":"🟢","esaurito":"🔴","prossimamente":"🟡"}.get(w.get("stato","disponibile"),"⚪")
                st.write(f"{icon} **{w.get('nome','?')}** — *{w.get('produttore','')}* · {w.get('categoria','')}")
            with col_d:
                if st.button("🗑️", key=f"del_{i}", help="Elimina questo vino"):
                    st.session_state.wines.pop(i)
                    save_wines(st.session_state.wines)
                    st.rerun()

# ═════════════════════════════════════════════════════════════════════════
# TAB 4 · IMPORT / EXPORT
# ═════════════════════════════════════════════════════════════════════════
with tab_io:
    col_exp, col_imp = st.columns(2)

    # ── Export ────────────────────────────────────────────────────────
    with col_exp:
        st.subheader("📤 Export")
        if wines:
            df_exp = pd.DataFrame(wines)

            buf_xl = io.BytesIO()
            df_exp.to_excel(buf_xl, index=False, engine="openpyxl")
            st.download_button(
                "⬇️ Excel (.xlsx)", buf_xl.getvalue(),
                "mr_wine_catalogo.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            buf_csv = io.BytesIO()
            buf_csv.write(df_exp.to_csv(index=False).encode("utf-8"))
            st.download_button("⬇️ CSV (.csv)", buf_csv.getvalue(), "mr_wine_catalogo.csv", "text/csv")

            buf_json = json.dumps(wines, ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button("⬇️ JSON (.json)", buf_json, "mr_wine_catalogo.json", "application/json")
        else:
            st.info("Nessun vino da esportare.")

    # ── Import ────────────────────────────────────────────────────────
    with col_imp:
        st.subheader("📥 Import")
        st.caption("Importa da Excel o CSV. Le colonne devono corrispondere ai campi del catalogo.")
        uploaded = st.file_uploader("Carica file", type=["csv", "xlsx"], key="import_file")

        if uploaded:
            try:
                df_imp = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
                st.dataframe(df_imp.head(5), use_container_width=True)
                st.caption(f"Trovati **{len(df_imp)}** vini nel file")

                if st.button("✅ Importa tutti", type="primary"):
                    count = 0
                    for rec in df_imp.to_dict("records"):
                        # Replace NaN with None
                        rec = {k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in rec.items()}
                        if not rec.get("id"):
                            rec["id"] = str(uuid.uuid4())[:8]
                        st.session_state.wines.append(rec)
                        count += 1
                    save_wines(st.session_state.wines)
                    st.success(f"✅ {count} vini importati!")
                    st.rerun()
            except Exception as e:
                st.error(f"Errore import: {e}")

    st.divider()
    with st.expander("⚠️ Zona Pericolosa — Svuota catalogo"):
        st.warning("Questa operazione elimina **tutti** i vini dal catalogo. Non può essere annullata.")
        confirm = st.text_input("Scrivi CONFERMA per procedere", key="confirm_delete_txt")
        if st.button("🗑️ Svuota catalogo", type="secondary"):
            if confirm == "CONFERMA":
                st.session_state.wines = []
                save_wines([])
                st.success("Catalogo svuotato.")
                st.rerun()
            else:
                st.error("Scrivi esattamente CONFERMA per procedere.")
