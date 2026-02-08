import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
import qrcode
import re
import os
from io import BytesIO

# --- 1. CONFIGURAZIONE E GRAFICA ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

def set_bg(png_file):
    try:
        with open(png_file, 'rb') as f:
            bin_str = base64.b64encode(f.read()).decode()
        st.markdown(f'''<style>
        .stApp {{ 
            background-image: url("data:image/png;base64,{bin_str}"); 
            background-size: cover; 
            background-position: center;
            background-attachment: fixed;
        }}
        /* Rendiamo i box leggermente trasparenti per leggere il testo sullo sfondo */
        .st-emotion-cache-1y4p8pa, .st-emotion-cache-10trblm {{
            background-color: rgba(255, 255, 255, 0.9) !important;
            border-radius: 15px;
            padding: 20px;
        }}
        header {{ visibility: hidden; }}
        </style>''', unsafe_allow_html=True)
    except: pass

set_bg('sfondo_eft.png')

# --- 2. CARICAMENTO DATI SICURO ---
@st.cache_data
def load_data():
    if not os.path.exists("Catalogo_Corsi_EFT_2026.csv"): return pd.DataFrame()
    try:
        # Legge tutto come testo per non perdere zeri iniziali o link strani
        df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv", dtype=str).fillna("")
        # Pulizia di sicurezza
        df = df.apply(lambda x: x.str.strip())
        return df
    except: return pd.DataFrame()

df = load_data()

# --- 3. LOGIN STAFF ---
if "auth" not in st.session_state:
    st.title("🎓 Accesso Stand Didacta")
    pwd = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else: st.error("Errore")
    st.stop()

# --- 4. INTERFACCIA PRINCIPALE ---
st.title("🔍 Consulente Formativo EFT")

# DEBUG BOX RIPRISTINATO
with st.expander("🛠️ Verifica Link CSV (Prova prima di cercare)"):
    if not df.empty:
        test_link = df.iloc[0]['Link']
        st.write(f"Primo link nel database: `{test_link}`")
        st.link_button("👉 CLICCA QUI PER TESTARE IL PRIMO LINK", test_link)
    else:
        st.error("Database vuoto.")

col1, col2 = st.columns(2)
with col1: scuola = st.selectbox("Ordine Scuola", ["Infanzia", "Primaria", "Secondaria I grado", "Secondaria II grado", "Tutti"])
with col2: tema = st.selectbox("Area Tematica", ["Intelligenza Artificiale", "STEM e Robotica", "Metodologie", "Inclusione", "Tutti"])

if st.button("🔎 Trova Corsi Reali", use_container_width=True):
    if df.empty: st.error("Nessun dato disponibile.")
    else:
        with st.spinner("Consultazione catalogo in corso..."):
            # USIAMO IL MODELLO ESATTO RICHIESTO
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-flash-latest')
            
            # Prompt blindato anti-allucinazioni
            csv_data = df.to_csv(index=False)
            prompt = f"""
            Sei un assistente che deve suggerire corsi SOLO dal catalogo fornito.
            
            CATALOGO REALE:
            {csv_data}
            
            COMPITO:
            Trova fino a 3 corsi adatti per: Scuola {scuola}, Tema {tema}.
            
            REGOLE ASSOLUTE:
            1. NON INVENTARE CORSI O LINK. Se non trovi nulla, scrivilo.
            2. Copia il 'Titolo' e il 'Link' ESATTAMENTE come sono nel CSV.
            3. Usa questo formato per la risposta:
               ## [ID] Titolo del Corso
               *Descrizione sintetica basata su titolo e tema.*
               [VAI ALLA SCHEDA DEL CORSO](Link_esatto_dal_csv)
            """
            try:
                res = model.generate_content(prompt)
                st.session_state.risultato = res.text
            except Exception as e: st.error(f"Errore AI: {e}")

# --- 5. RISULTATI E QR CODE FUNZIONANTE ---
if "risultato" in st.session_state:
    st.markdown("---")
    st.markdown(st.session_state.risultato)
    
    # Estrae i link reali trovati dall'IA
    links_trovati = re.findall(r'(https://scuolafutura[^\s\)]+)', st.session_state.risultato)
    
   if links_trovati:
        st.subheader("📱 Scarica i link sul telefono")
        # Crea un QR code che contiene la lista dei link uno per riga
        qr_content = "\n".join(links_trovati)
        img = qrcode.make(qr_content) # <--- ASSICURATI CHE CI SIA .make(qr_content)
        buf = BytesIO()
        img.save(buf, format="PNG")
        st.image(buf.getvalue(), width=250, caption="Inquadra per aprire l'elenco dei link")

if st.button("🔄 Ricomincia"):
    st.session_state.risultato = ""
    st.rerun()
