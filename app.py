import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
import qrcode
import re
import os
from io import BytesIO

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

# --- 2. FUNZIONE SFONDO E STILE ---
def set_bg_hack(png_file):
    # Carica lo sfondo se esiste
    if os.path.exists(png_file):
        with open(png_file, "rb") as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/png;base64,{bin_str}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

    # Stile CSS per rendere leggibile il testo (Effetto vetro bianco)
    st.markdown(
        """
        <style>
        /* Contenitore principale semitrasparente */
        .stMain .block-container {
            background-color: rgba(255, 255, 255, 0.92);
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            max-width: 800px;
        }
        /* Nasconde menu e footer di Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True
    )

set_bg_hack('sfondo_eft.png')

# --- 3. GESTIONE PASSWORD ---
# Se non impostata nei secrets, usa quella di default
PASSWORD_SEGRETA = st.secrets.get("APP_PASSWORD", "didacta2026")

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Accesso Staff EFT")
    pwd = st.text_input("Inserisci Password", type="password")
    if st.button("Entra"):
        if pwd == PASSWORD_SEGRETA:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Password errata")
    st.stop()

# --- 4. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    if not os.path.exists("Catalogo_Corsi_EFT_2026.csv"):
        return pd.DataFrame()
    try:
        # Carica tutto come testo
        df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv", dtype=str).fillna("")
        return df.apply(lambda x: x.str.strip())
    except:
        return pd.DataFrame()

df = load_data()

# --- 5. INTERFACCIA RICERCA ---
st.title("🎓 Consulente Formativo EFT")

if df.empty:
    st.error("⚠️ Il file CSV dei corsi non è stato trovato o è vuoto.")
    st.stop()

# Filtri
col1, col2 = st.columns(2)
with col1:
    ordine = st.selectbox("Ordine Scuola", ["Tutti", "Infanzia", "Primaria", "Secondaria I grado", "Secondaria II grado", "CPIA"])
with col2:
    # Ordina le regioni alfabeticamente
    regioni = ["Tutte"] + sorted(df['Regione'].unique().tolist()) if 'Regione' in df.columns else ["Tutte"]
    regione = st.selectbox("Regione", regioni)

# Tematica
temi = ["Tutte"] + sorted(df['Tematica'].unique().tolist()) if 'Tematica' in df.columns else ["Tutte"]
tema = st.selectbox("Area Tematica", temi)

# Input libero
query = st.text_input("Interessi specifici (es. Podcast, AI, Inclusione)")

# --- 6. PULSANTE CERCA E LOGICA IA ---
if st.button("🔎 Cerca Corsi", use_container_width=True):
    with st.spinner("Analisi del catalogo in corso..."):
        # Configura Gemini
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-flash-latest')
            
            dati = df.to_csv(index=False)
            
            prompt = f"""
            Sei un consulente esperto. Analizza questo catalogo CSV:
            {dati}
            
            TROVA 3 CORSI PER:
            - Scuola: {ordine} (Deduci dal titolo/abstract)
            - Regione: {regione} (Se non trovi, cerca 'Nazionale')
            - Tema: {tema}
            - Extra: {query}
            
            FORMATO RISPOSTA (Markdown):
            ### [Titolo]
            **ID:** [ID]
            **Perché:** Breve spiegazione.
            **Competenze:** [Competenze_DigCompEdu]
            🔗 [VAI AL CORSO]([Link])
            
            REGOLE:
            1. Usa SOLO i corsi del CSV.
            2. Copia i LINK esattamente.
            """
            
            res = model.generate_content(prompt)
            st.session_state.risposta_ia = res.text
            
        except Exception as e:
            st.error(f"Errore IA: {e}")

# --- 7. RISULTATI, QR CODE E RESET ---
if "risposta_ia" in st.session_state:
    st.markdown("---")
    st.markdown(st.session_state.risposta_ia)
    
    # Estrazione Link per QR Code
    links = re.findall(r'(https?://scuolafutura[^\s\)]+)', st.session_state.risposta_ia)
    links_unici = list(dict.fromkeys(links)) # Rimuove duplicati
    
    if links_unici:
        st.markdown("---")
        st.subheader("📱 Scansiona per iscriverti")
        
        # QR Code leggero (solo link)
        qr_content = "\n".join(links_unici)
        img = qrcode.make(qr_content)
        
        buf = BytesIO()
        img.save(buf, format="PNG")
        st.image(buf.getvalue(), width=200, caption="I link dei corsi sul tuo telefono")
    
    st.markdown("---")
    # PULSANTE RESET
    if st.button("🗑️ Nuova Ricerca (Resetta)", use_container_width=True):
        # Cancella la risposta dalla memoria
        del st.session_state.risposta_ia
        # Ricarica la pagina
        st.rerun()
