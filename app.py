import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
import qrcode
import re
import os
from io import BytesIO
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

# Funzione Caricamento Dati con Pulizia Automatica
@st.cache_data
def load_data():
    try:
        if os.path.exists("Catalogo_Corsi_EFT_2026.csv"):
            # Legge il file ignorando le virgolette sporche
            df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv", quotechar='"', skipinitialspace=True)
            # Pulisce ogni cella da eventuali residui di virgolette
            df = df.apply(lambda x: x.astype(str).str.replace('"', '').str.strip())
            return df
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

df_corsi = load_data()

# --- LOGIN E STATO AGGIORNAMENTO ---
if "auth" not in st.session_state:
    st.title("🎓 Accesso Orientatore")
    
    # Visualizza info file se esiste
    if os.path.exists("Catalogo_Corsi_EFT_2026.csv"):
        mtime = os.path.getmtime("Catalogo_Corsi_EFT_2026.csv")
        data_str = datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M')
        st.info(f"Database corsi aggiornato al: {data_str}")
    
    pwd = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Password errata")
    st.stop()

# --- INTERFACCIA PRINCIPALE ---
st.title("🔍 Ricerca Percorsi Formativi")

# Strumento Debug per te (visibile solo dopo login)
with st.expander("🛠️ Controllo Integrità Link"):
    if not df_corsi.empty:
        st.write("Esempio Link pulito:", df_corsi['Link'].iloc[0])
        st.link_button("Test Link 1", df_corsi['Link'].iloc[0])
    else:
        st.error("Database non caricato correttamente.")

# Selezione filtri
scuola = st.selectbox("Ordine di Scuola", ["Infanzia", "Primaria", "Secondaria I grado", "Secondaria II grado", "Tutti"])
tema = st.selectbox("Area Tematica", ["Intelligenza Artificiale", "STEM e Robotica", "Metodologie", "Tutti"])

if st.button("🔎 Genera Proposta"):
    if df_corsi.empty:
        st.error("Catalogo non disponibile.")
    else:
        with st.spinner("Analisi in corso..."):
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            contesto = df_corsi[['ID', 'Titolo', 'Link']].to_string(index=False)
            prompt = f"Basandoti su questo catalogo: {contesto}. Trova corsi per {scuola} su {tema}. Per ogni corso scrivi: 1. **[ID: numero] Titolo** - Link: [Vai al corso](URL_CORRETTO)"
            
            try:
                response = model.generate_content(prompt)
                st.session_state.risultato = response.text
            except Exception as e:
                st.error("Errore AI")

if "risultato" in st.session_state and st.session_state.risultato:
    st.markdown(st.session_state.risultato)
    
    # Generazione QR semplice
    qr_data = ""
    urls = re.findall(r'(https?://[^\s\)]+)', st.session_state.risultato)
    if urls:
        # Prende il primo link trovato per il QR
        qr_url = f"https://mimmo-consulente-didacta.streamlit.app/?link={urls[0]}"
        img_qr = qrcode.make(qr_url)
        buf = BytesIO()
        img_qr.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="QR Code del primo corso suggerito", width=200)

    if st.button("Pulisci"):
        st.session_state.risultato = None
        st.rerun()
