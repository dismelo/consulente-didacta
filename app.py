import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
import qrcode
import re
import os
from io import BytesIO
from datetime import datetime

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
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
        }}
        [data-testid="stVerticalBlock"] {{ padding-top: 80px; padding-bottom: 100px; }}
        header {{ visibility: hidden; }}
        </style>''', unsafe_allow_html=True)
    except: pass

set_bg('sfondo_eft.png')

# --- 2. CARICAMENTO E PULIZIA DATI ---
@st.cache_data
def load_data():
    try:
        # Legge il file ignorando spazi iniziali
        df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv", skipinitialspace=True)
        
        # PULIZIA AGGRESSIVA: Rimuove virgolette e spazi che rompono i link
        for col in df.columns:
            df[col] = df[col].astype(str).str.replace('"', '').str.strip()
        
        return df
    except Exception as e:
        st.error(f"Errore caricamento database: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. MODALITÀ OSPITE (QR SCANSIONATO) ---
if "qrlite" in st.query_params:
    st.title("📱 I Tuoi Corsi Selezionati")
    try:
        dati_raw = base64.b64decode(st.query_params["qrlite"]).decode('utf-8')
        for riga in dati_raw.split('\n'):
            if "|" in riga:
                parti = riga.split('|')
                if len(parti) >= 3:
                    st.markdown(f"**ID: {parti[0]}** - {parti[1]}")
                    st.link_button(f"Vai alla scheda 🔗", parti[2])
                    st.divider()
        st.stop()
    except:
        st.error("Errore lettura QR.")
        st.stop()

# --- 4. ACCESSO STAFF E STATO DATI ---
if "auth" not in st.session_state:
    st.title("🎓 Accesso Stand Didacta")

    # Controllo data aggiornamento file
    if os.path.exists("Catalogo_Corsi_EFT_2026.csv"):
        mtime = os.path.getmtime("Catalogo_Corsi_EFT_2026.csv")
        last_upd = datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M')
        is_fresh = (datetime.now() - datetime.fromtimestamp(mtime)).days < 1
        
        if is_fresh:
            st.success(f"✅ Il file dati dei corsi è stato aggiornato con successo ({last_upd}).")
            with open("Catalogo_Corsi_EFT_2026.csv", "rb") as f:
                st.download_button("📥 Scarica Catalogo Aggiornato (CSV)", f, "Catalogo_EFT.csv", "text/csv")
        else:
            st.warning(f"⚠️ L'elenco non è stato aggiornato oggi. Ultimo aggiornamento: ({last_upd}).")

    st.write("---")
    pwd = st.text_input("Password Staff", type="password")
    if st.button("Accedi"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Password errata")
    st.stop()

# --- 5. INTERFACCIA PRINCIPALE (Dopo il Login) ---

# DEBUG TOOL: Verifica se i link sono puliti
with st.expander("🛠️ STRUMENTO DEBUG (Verifica Link)"):
    if not df.empty:
        st.write("Dati estratti dal CSV (senza virgolette):")
        st.dataframe(df[["ID", "Titolo", "Link"]].head(3))
        test_url = df['Link'].iloc[0]
        st.write(f"Saggio URL: `{test_url}`")
        st.link_button("PROVA QUESTO LINK", test_url)
    else:
        st.error("Il file CSV sembra vuoto o non leggibile.")

st.title("🔍 Consulente Formativo")

# Configurazione AI
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Errore configurazione AI")
    st.stop()

col_scuola, col_tema = st.columns(2)
with col_scuola:
    scuola = st.selectbox("Livello Scuola", ["Infanzia", "Primaria", "Secondaria I grado", "Secondaria II grado", "Tutti"])
with col_tema:
    tema = st.selectbox("Tematica", ["Intelligenza Artificiale", "STEM e Robotica", "Metodologie", "Inclusione", "Tutti"])

if "risultato_ia" not in st.session_state: st.session_state.risultato_ia = None

if st.button("🔎 Cerca nel Catalogo", use_container_width=True):
    with st.spinner("Analisi database..."):
        # Passiamo i dati puliti all'IA
        context = df[["ID", "Titolo", "Link"]].to_string(index=False)
        prompt = f"""
        Usa esclusivamente questo catalogo: {context}
        Cerca corsi per: {scuola}, Tema: {tema}.
        
        FORMATO RISPOSTA OBBLIGATORIO:
        1. **[ID: numero] Titolo Corso**
        - Abstract: Breve descrizione di 2 righe.
        - Link: [Apri Scheda Corso](INSERISCI_LINK_ESATTO)
        
        Nota: Il link deve essere puro, senza virgolette.
        """
        try:
            res = model.generate_content(prompt)
            st.session_state.risultato_ia = res.text
        except Exception as e:
            st.error(f"Errore AI: {e}")

# --- 6. GENERAZIONE QR CODE ---
if st.session_state.risultato_ia:
    st.markdown("---")
    st.markdown(st.session_state.risultato_ia)
    
    # Estrazione dati per QR
    qr_payload = ""
    for line in st.session_state.risultato_ia.split('\n'):
        if "http" in line:
            # Estrae ID e Link puliti
            m_id = re.search(r'ID:\s*(\d+)', line) or re.search(r'\[ID:\s*(\d+)\]', line)
            m_url = re.search(r'(https?://[^\s\)]+)', line)
            if m_id and m_url:
                qr_payload += f"{m_id.group(1)}|Corso|{m_url.group(1)}\n"

    if qr_payload:
        b64 = base64.b64encode(qr_payload.encode()).decode()
        qr_url = f"https://{st.secrets.get('APP_URL', 'mimmo-consulente-didacta.streamlit.app')}/?qrlite={b64}"
        
        qr = qrcode.
