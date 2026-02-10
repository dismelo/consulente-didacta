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

    # Stile CSS "Vetro" e pulizia interfaccia
    st.markdown(
        """
        <style>
        .stMain .block-container {
            background-color: rgba(255, 255, 255, 0.95); /* Più opaco per leggibilità */
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        /* Nasconde elementi standard Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Forza il colore del testo dei link per leggibilità */
        a { color: #0068c9 !important; font-weight: bold; }
        </style>
        """,
        unsafe_allow_html=True
    )

set_bg_hack('sfondo_eft.png')

# --- 3. GESTIONE PASSWORD (FORM PER EVITARE AUTOCOMPLETAMENTO) ---
PASSWORD_SEGRETA = st.secrets.get("APP_PASSWORD", "didacta2026")

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Accesso Staff EFT")
    
    # Usiamo un FORM: evita che il browser riempia automaticamente con la vecchia sessione
    with st.form("login_form"):
        # Cambiamo la label e usiamo un key casuale se necessario, ma il form aiuta già molto
        pwd = st.text_input("Digita il codice di accesso", type="password")
        submit_button = st.form_submit_button("Entra")
        
        if submit_button:
            if pwd == PASSWORD_SEGRETA:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Codice errato.")
    st.stop()

# --- 4. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    if not os.path.exists("Catalogo_Corsi_EFT_2026.csv"):
        return pd.DataFrame()
    try:
        df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv", dtype=str).fillna("")
        return df.apply(lambda x: x.str.strip())
    except:
        return pd.DataFrame()

df = load_data()

# --- 5. INTERFACCIA RICERCA ---
st.title("🎓 Consulente Formativo EFT")

if df.empty:
    st.error("⚠️ Database corsi non trovato.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    ordine = st.selectbox("Ordine Scuola", ["Tutti", "Infanzia", "Primaria", "Secondaria I grado", "Secondaria II grado", "CPIA"])
with col2:
    regioni = ["Tutte"] + sorted(df['Regione'].unique().tolist()) if 'Regione' in df.columns else ["Tutte"]
    regione = st.selectbox("Regione", regioni)

temi = ["Tutte"] + sorted(df['Tematica'].unique().tolist()) if 'Tematica' in df.columns else ["Tutte"]
tema = st.selectbox("Area Tematica", temi)

query = st.text_input("Interessi specifici (es. Podcast, AI, Inclusione)")

# --- 6. LOGICA IA ---
if st.button("🔎 Cerca Corsi", use_container_width=True):
    with st.spinner("Generazione proposta in corso..."):
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            
            # IL MODELLO CHE HAI SCELTO
            model = genai.GenerativeModel('gemini-flash-latest')
            
            dati = df.to_csv(index=False)
            
            prompt = f"""
            Sei un consulente esperto. Analizza questo catalogo CSV:
            {dati}
            
            TROVA 3 CORSI PER:
            - Scuola: {ordine}
            - Regione: {regione}
            - Tema: {tema}
            - Extra: {query}
            
            ISTRUZIONI RIGIDE:
            1. Usa SOLO i corsi del CSV.
            2. Se non trovi nulla per la regione {regione}, cerca corsi Nazionali.
            3. Nella risposta metti ESATTAMENTE i link presenti nella colonna 'Link'.
            
            FORMATO RISPOSTA (Markdown):
            ### [Titolo]
            **Target:** [Target dedotto]
            **Perché:** Breve spiegazione.
            🔗 [VAI AL CORSO]([Link])
            """
            
            res = model.generate_content(prompt)
            st.session_state.risposta_ia = res.text
            
        except Exception as e:
            st.error(f"Errore IA: {e}")

# --- 7. RISULTATI, QR CODE "CLICK-READY" E RESET ---
if "risposta_ia" in st.session_state:
    st.markdown("---")
    st.markdown(st.session_state.risposta_ia)
    
    # Estrazione Link puliti
    links = re.findall(r'(https?://scuolafutura[^\s\)]+)', st.session_state.risposta_ia)
    # Pulizia profonda: rimuove duplicati, spazi e parentesi residue
    links_unici = [l.strip().split(')')[0].split(']')[0] for l in list(dict.fromkeys(links))]
    
    if links_unici:
        st.markdown("---")
        st.subheader("📱 Ricevi i link sul telefono")
        
        # COSTRUZIONE CONTENUTO QR: SOLO URL NUDI
        # Rimuovendo il testo "CORSI SELEZIONATI", il telefono riconosce i link come azioni
        qr_content = "\n".join(links_unici)
        
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L, # Ridotto per diminuire la densità
            box_size=10,
            border=4,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        
        col_qr, col_text = st.columns([1, 1])
        with col_qr:
            st.image(buf.getvalue(), width=250)
        with col_text:
            st.success("✅ **QR Code generato!**")
            st.write("""
            **Istruzioni per l'utente:**
            - Inquadra il codice.
            - Tocca i link che appaiono sullo schermo del telefono per aprire le schede dei corsi.
            """)
    
    st.markdown("---")
    if st.button("🗑️ Nuova Ricerca (Resetta)", use_container_width=True):
        if "risposta_ia" in st.session_state:
            del st.session_state.risposta_ia
        st.rerun()
