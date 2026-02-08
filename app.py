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

# Funzione per lo sfondo (Ripristinata)
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
        [data-testid="stVerticalBlock"] {{ 
            background: rgba(255, 255, 255, 0.9); 
            padding: 30px; 
            border-radius: 20px; 
            margin-top: 50px;
        }}
        header {{ visibility: hidden; }}
        </style>''', unsafe_allow_html=True)
    except:
        pass

set_bg('sfondo_eft.png')

# --- 2. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    if not os.path.exists("Catalogo_Corsi_EFT_2026.csv"):
        return pd.DataFrame()
    try:
        # Pulizia totale per evitare allucinazioni o errori di link
        df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv", dtype=str).fillna("")
        df = df.apply(lambda x: x.str.replace('"', '').str.strip())
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 3. ACCESSO ---
if "auth" not in st.session_state:
    st.title("🎓 Accesso Stand Didacta")
    pwd = st.text_input("Password Staff", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Password errata")
    st.stop()

# --- 4. INTERFACCIA DI RICERCA ---
st.title("🔍 Consulente Formativo EFT")

# Debug per sicurezza (lo vedi solo tu)
with st.expander("🛠️ Verifica Database"):
    st.write(f"Corsi caricati nel sistema: {len(df)}")
    st.dataframe(df.head(5))

col1, col2 = st.columns(2)
with col1:
    scuola = st.selectbox("Ordine Scuola", ["Infanzia", "Primaria", "Secondaria I grado", "Secondaria II grado", "Tutti"])
with col2:
    tema = st.selectbox("Area Tematica", ["Intelligenza Artificiale", "STEM e Robotica", "Metodologie", "Inclusione", "Tutti"])

if st.button("🔎 Genera Proposta Personalizzata", use_container_width=True):
    if df.empty:
        st.error("Database non trovato!")
    else:
        with st.spinner("L'IA sta analizzando il catalogo reale..."):
            # Configuriamo il modello che hai confermato funzionante
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-flash-latest')
            
            # PROMPT BLINDATO: Ordiniamo all'IA di non inventare nulla
            contesto_csv = df.to_csv(index=False)
            prompt = f"""
            ISTRUZIONI RIGIDE: 
            1. Usa SOLO i corsi elencati qui sotto. 
            2. Se non trovi corsi per {scuola} e {tema}, dillo chiaramente, NON inventare nomi.
            3. Per ogni corso trovato scrivi:
               - **[ID] Titolo**
               - Link: Copia esattamente il link della colonna Link.
            
            DATASET CORSI:
            {contesto_csv}
            
            RICHIESTA UTENTE: Corsi per {scuola} su {tema}.
            """
            
            try:
                res = model.generate_content(prompt)
                st.session_state.risposta = res.text
            except Exception as e:
                st.error(f"Errore AI: {e}")

# --- 5. RISULTATI E QR CODE ---
if "risposta" in st.session_state:
    st.markdown("---")
    st.markdown(st.session_state.risposta)
    
    # Estrazione link per QR Code
    links = re.findall(r'(https?://[^\s\)]+)', st.session_state.risposta)
    if links:
        st.subheader("📲 Porta i link sul tuo smartphone")
        # Creiamo un payload per il QR che contiene i link trovati
        qr_payload = "I TUOI CORSI SELEZIONATI:\n\n" + "\n".join(links)
        
        qr = qrcode.make(qr_payload)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        st.image(buf.getvalue(), width=250)
        st.caption("Scansiona per aprire l'elenco dei link direttamente sul telefono.")

if st.button("🗑️ Nuova Ricerca"):
    st.session_state.risposta = ""
    st.rerun()
