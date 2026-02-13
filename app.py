import streamlit as st
import google.generativeai as genai
import pandas as pd
import qrcode
import re
import os
from io import BytesIO

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

# --- 2. GESTIONE DATABASE ---
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "Catalogo_Corsi_EFT_2026.csv")

@st.cache_data
def load_data():
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    try:
        # Caricamento con separatore punto e virgola come nel file B
        df = pd.read_csv(csv_path, sep=';', dtype=str).fillna("")
        return df.apply(lambda x: x.str.strip())
    except Exception as e:
        st.error(f"Errore nella lettura del file: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. ACCESSO (PASSWORD) ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Accesso Riservato")
    with st.form("login"):
        user_pwd = st.text_input("Inserisci la password", type="password")
        if st.form_submit_button("Sblocca"):
            if user_pwd == st.secrets.get("APP_PASSWORD", "didacta2026"):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Password errata.")
    st.stop()

# --- 4. INTERFACCIA UTENTE ---
st.title("🎓 Consulente Formativo EFT")

if df.empty:
    st.warning("⚠️ Database corsi non trovato o vuoto. Carica il file CSV su GitHub.")
    st.stop()

st.info("Benvenuto! Seleziona i tuoi interessi per trovare i corsi più adatti su Scuola Futura.")

# --- 5. FILTRI ---
col1, col2 = st.columns(2)

with col1:
    # Mappatura su colonna 'Ordine_scuola' del file B
    opzioni_scuola = ["Tutti"] + sorted(list(set([opt.strip() for val in df['Ordine_scuola'].unique() for opt in val.split(',')])))
    ordine = st.selectbox("Ordine Scuola", opzioni_scuola)

with col2:
    regione = st.selectbox("Regione", ["Tutte"] + sorted(df['Regione'].unique().tolist()))

tema = st.selectbox("Area Tematica", ["Tutte"] + sorted(df['Tematica'].unique().tolist()))
query = st.text_input("Cosa stai cercando? (es. intelligenza artificiale, inclusione...)")

# --- 6. LOGICA DI RICERCA CON GEMINI ---
if st.button("🔎 Trova i miei corsi", use_container_width=True):
    # Filtraggio preliminare per non mandare troppi dati all'IA
    df_filtrato = df.copy()
    if ordine != "Tutti":
        df_filtrato = df_filtrato[df_filtrato['Ordine_scuola'].str.contains(ordine, case=False)]
    if regione != "Tutte":
        df_filtrato = df_filtrato[df_filtrato['Regione'] == regione]
    if tema != "Tutte":
        df_filtrato = df_filtrato[df_filtrato['Tematica'] == tema]

    if df_filtrato.empty:
        st.error("Nessun corso trovato con questi filtri. Prova a cercarne altri!")
    else:
        with st.spinner("L'intelligenza artificiale sta analizzando i corsi per te..."):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-flash-latest')
                
                # Prepariamo i dati per il prompt (prime 15 righe filtrate per brevità)
                context_csv = df_filtrato.head(15).to_csv(index=False)
                
                prompt = f"""
                Agisci come un consulente esperto di Scuola Futura. 
                In base a questa richiesta: '{query}' per la scuola '{ordine}',
                analizza i seguenti corsi:
                {context_csv}
                
                Seleziona i 3 corsi migliori e scrivi un breve report.
                Per ogni corso DEVI includere il link esatto che trovi nella colonna 'Link_scheda'.
                Alla fine, elenca solo i link nudi (uno per riga) per il QR code.
                """
                
                res = model.generate_content(prompt)
                st.session_state.risposta_ia = res.text
            except Exception as e:
                st.error(f"Errore durante l'analisi: {e}")

# --- 7. RISULTATI E QR CODE ---
if "risposta_ia" in st.session_state:
    st.markdown("---")
    st.markdown(st.session_state.risposta_ia)
    
    # Estrazione link per il QR Code (usa la colonna Link_scheda del file B)
    links = re.findall(r'(https?://scuolafutura[^\s\)\],]+)', st.session_state.risposta_ia)
    links_unici = list(dict.fromkeys(links))
    
    if links_unici:
        st.subheader("📱 Porta i link sul tuo smartphone")
        qr_content = "\n".join(links_unici)
        
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(qr_content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buf = BytesIO()
        img.save(buf, format="PNG")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(buf.getvalue(), width=250)
        with c2:
            st.success("Scansiona il QR code per aprire le schede dei corsi selezionati!")

    if st.button("🗑️ Nuova Ricerca"):
        del st.session_state.risposta_ia
        st.rerun()
