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

# --- 2. GESTIONE DATABASE (Percorso Robusto) ---
# Questo comando trova la cartella esatta dove si trova app.py
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "Catalogo_Corsi_EFT_2026.csv")

@st.cache_data
def load_data():
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    try:
        # Carichiamo il file forzando la codifica utf-8
        df = pd.read_csv(csv_path, dtype=str).fillna("")
        return df.apply(lambda x: x.str.strip())
    except:
        return pd.DataFrame()

df = load_data()

# --- 3. PASSWORD (NO AUTOCOMPLETE) ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Accesso Riservato")
    # Usiamo un widget vuoto per 'spezzare' la memoria del browser
    with st.form("login"):
        # Cambiando la label e non mettendo il valore di default, il browser è meno propenso a riempirlo
        user_pwd = st.text_input("Inserisci il codice per questa sessione", type="password", help="Inserisci la password per iniziare")
        if st.form_submit_button("Sblocca Sistema"):
            if user_pwd == st.secrets.get("APP_PASSWORD", "didacta2026"):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Accesso negato.")
    st.stop()

# --- 4. INTERFACCIA ---
st.title("🎓 Consulente Formativo EFT")

# Se il database è vuoto o non trovato, mostriamo un messaggio utile
if df.empty:
    st.warning(f"⚠️ File '{os.path.basename(csv_path)}' non trovato nel repository o vuoto. Verifica il caricamento su GitHub.")
    st.stop()

# --- 5. LOGICA IA (Modello Corretto) ---
# (I filtri rimangono uguali a prima...)
ordine = st.selectbox("Ordine Scuola", ["Tutti", "Infanzia", "Primaria", "Secondaria I grado", "Secondaria II grado", "CPIA"])
regione = st.selectbox("Regione", ["Tutte"] + sorted(df['Regione'].unique().tolist()))
tema = st.selectbox("Area Tematica", ["Tutte"] + sorted(df['Tematica'].unique().tolist()))
query = st.text_input("Interessi specifici")

if st.button("🔎 Cerca Corsi", use_container_width=True):
    with st.spinner("Analisi in corso con Gemini..."):
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            # MODELLO CORRETTO COME RICHIESTO
            model = genai.GenerativeModel('gemini-flash-latest')
            
            prompt = f"Analizza questi corsi CSV: {df.to_csv(index=False)} e trova 3 corsi per {ordine}, regione {regione} e tema {tema}. Inserisci solo i link nudi per il QR code finale."
            
            res = model.generate_content(prompt)
            st.session_state.risposta_ia = res.text
        except Exception as e:
            st.error(f"Errore: {e}")

# --- 6. RISULTATI E QR CODE (CLICKABLE) ---
if "risposta_ia" in st.session_state:
    st.markdown(st.session_state.risposta_ia)
    
    links = re.findall(r'(https?://scuolafutura[^\s\)]+)', st.session_state.risposta_ia)
    links_unici = [l.strip().split(')')[0].split(']')[0] for l in list(dict.fromkeys(links))]
    
    if links_unici:
        qr_content = "\n".join(links_unici)
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(qr_content)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buf = BytesIO()
        img.save(buf, format="PNG")
        st.image(buf.getvalue(), width=250, caption="Scansiona per i link diretti")

    if st.button("🗑️ Nuova Ricerca"):
        del st.session_state.risposta_ia
        st.rerun()
