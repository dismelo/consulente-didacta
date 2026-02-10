import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
import qrcode
import re
import os
from io import BytesIO

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

# --- 2. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    if not os.path.exists("Catalogo_Corsi_EFT_2026.csv"): return pd.DataFrame()
    try:
        # Carica il nuovo CSV con la struttura: ID, titolo, Abstract, Competenze_DigCompEdu, Tematica, Regione, Link
        df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv", dtype=str).fillna("")
        return df.apply(lambda x: x.str.strip())
    except: return pd.DataFrame()

df = load_data()

# --- 3. LOGIN (Oltrepassiamo per brevità, tieni il tuo se vuoi) ---
if "auth" not in st.session_state:
    st.session_state.auth = True # Impostato a True per test immediato

# --- 4. INTERFACCIA ---
st.title("🔍 Consulente Formativo EFT")

with st.expander("🛠️ Verifica Database Reale"):
    if not df.empty:
        st.write(f"Corsi totali nel file: {len(df)}")
        st.dataframe(df.head(5))
    else:
        st.error("File CSV non trovato!")

# FILTRI (Qui rimediamo alla mancanza della colonna)
col1, col2, col3 = st.columns(3)
with col1:
    # Aggiungiamo manualmente l'ordine di scuola che l'IA dovrà cercare nel testo
    ordine = st.selectbox("Ordine Scuola", ["Tutti", "Infanzia", "Primaria", "Secondaria I grado", "Secondaria II grado"])
with col2:
    regione = st.selectbox("Regione", ["Tutte"] + sorted(df['Regione'].unique().tolist()))
with col3:
    tema = st.selectbox("Area Tematica", ["Tutte"] + sorted(df['Tematica'].unique().tolist()))

query_libera = st.text_input("Ricerca per parole chiave (es: coding, inclusione, podcast)")

if st.button("🔎 Trova i corsi adatti", use_container_width=True):
    with st.spinner("L'IA sta leggendo i titoli e gli abstract per te..."):
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        contesto = df.to_csv(index=False)
        
        prompt = f"""
        Sei un orientatore esperto. Devi trovare corsi per un docente di: {ordine}.
        Filtra anche per Regione: {regione} e Tema: {tema}.
        Altre info: {query_libera}

        DATI DISPONIBILI:
        {contesto}

        ISTRUZIONI:
        1. Analizza 'titolo' e 'Abstract' per capire se il corso è adatto a: {ordine}.
        2. Se non trovi nulla per {regione}, proponi corsi Nazionali (dove Regione è vuoto o 'Nazionale').
        3. Formato risposta:
           ### [ID] titolo
           **Target:** (Indica a chi è rivolto deducendolo dal testo)
           **Abstract:** (Breve sintesi)
           **Competenze:** (Cita le Competenze_DigCompEdu)
           [VAI ALLA SCHEDA](Link)
        """
        
        try:
            res = model.generate_content(prompt)
            st.session_state.report = res.text
        except Exception as e:
            st.error(f"Errore: {e}")

# --- 5. RISULTATI E QR CODE (SISTEMATO) ---
if "report" in st.session_state:
    st.markdown("---")
    st.markdown(st.session_state.report)
    
    links = re.findall(r'(https?://scuolafutura[^\s\)]+)', st.session_state.report)
    if links:
        st.subheader("📱 Porta i link con te")
        qr_data = "\n".join(links)
        img = qrcode.make(qr_data) # <--- CORRETTO (niente più errore Syntax)
        buf = BytesIO()
        img.save(buf, format="PNG")
        st.image(buf.getvalue(), width=200)
