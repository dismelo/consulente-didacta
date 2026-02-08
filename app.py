import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
import re
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

# Funzione Caricamento Dati con Pulizia Totale
@st.cache_data
def load_data():
    if not os.path.exists("Catalogo_Corsi_EFT_2026.csv"):
        return pd.DataFrame()
    try:
        # Leggiamo tutto come testo per evitare che Pandas faccia confusione con le virgolette
        df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv", dtype=str, skipinitialspace=True)
        # Rimuoviamo ogni tipo di virgoletta e spazio residuo da ogni singola cella
        df = df.apply(lambda x: x.str.replace('"', '').str.strip())
        return df
    except Exception as e:
        st.error(f"Errore tecnico lettura file: {e}")
        return pd.DataFrame()

df_corsi = load_data()

# --- LOGIN ---
if "auth" not in st.session_state:
    st.title("🎓 Accesso Stand Didacta")
    pwd = st.text_input("Inserisci Password", type="password")
    if st.button("Accedi"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Password errata")
    st.stop()

# --- INTERFACCIA DOPO LOGIN ---
st.title("🔍 Consulente Formativo EFT")

# 1. VERIFICA LINK (DEBUG)
with st.expander("🛠️ VERIFICA LINK (Se questo non va, il CSV è errato)"):
    if not df_corsi.empty:
        # Prendiamo il primo link e puliamolo da eventuali caratteri nascosti
        link_test = df_corsi['Link'].iloc[0].split(' ')[0]
        st.write(f"ID Corso: {df_corsi['ID'].iloc[0]}")
        st.write(f"URL analizzato: `{link_test}`")
        st.link_button("VAI ALLA SCHEDA (Verifica)", link_test)
    else:
        st.error("Database non trovato o vuoto.")

# 2. SELEZIONE FILTRI
scuola = st.selectbox("Ordine di Scuola", ["Infanzia", "Primaria", "Secondaria I grado", "Secondaria II grado", "Tutti"])
tema = st.selectbox("Area Tematica", ["Intelligenza Artificiale", "STEM e Robotica", "Metodologie", "Inclusione", "Tutti"])

# 3. RICERCA E RISPOSTA AI
if st.button("🔎 Trova Corsi", use_container_width=True):
    if df_corsi.empty:
        st.error("Il catalogo corsi è vuoto.")
    else:
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Prepariamo i dati per l'IA in modo super semplice
            elenco_testo = ""
            for i, row in df_corsi.iterrows():
                elenco_testo += f"ID: {row['ID']}, Titolo: {row['Titolo']}, Link: {row['Link']}\n"

            prompt = f"""
            Sei un esperto orientatore. In base a questo elenco di corsi:
            {elenco_testo}
            
            Suggerisci 3 corsi adatti a un docente di {scuola} interessato a {tema}.
            Per ogni corso scrivi:
            - **[ID] Titolo**
            - Link: Inserisci qui il link esatto che trovi nell'elenco.
            """
            
            with st.spinner("L'IA sta consultando il catalogo..."):
                response = model.generate_content(prompt)
                st.markdown("### 🎯 Proposte Formative Selezionate:")
                st.write(response.text)
                
        except Exception as e:
            st.error(f"L'AI ha avuto un problema: {e}")

if st.button("🔄 Pulisci Risultati"):
    st.rerun()
