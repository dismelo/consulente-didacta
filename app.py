import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
import qrcode
import re
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
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
        }}
        [data-testid="stVerticalBlock"] {{ padding-top: 80px; padding-bottom: 100px; }}
        header {{ visibility: hidden; }}
        </style>''', unsafe_allow_html=True)
    except: pass

set_bg('sfondo_eft.png')

# --- 2. MODALITÀ OSPITE (QR SCANSIONATO) ---
if "qrlite" in st.query_params:
    st.title("📱 I Tuoi Corsi Selezionati")
    try:
        dati_raw = base64.b64decode(st.query_params["qrlite"]).decode('utf-8')
        st.info("Ecco i corsi salvati. Clicca per iscriverti.")
        
        # Parsing dei dati ID|Titolo|Link
        for riga in dati_raw.split('\n'):
            if "|" in riga:
                try:
                    # Formato atteso: ID|Titolo|Link
                    parti = riga.split('|')
                    if len(parti) >= 3:
                        id_corso = parti[0]
                        titolo = parti[1]
                        link = parti[2]
                        
                        st.markdown(f"**ID: {id_corso}** - {titolo}")
                        st.link_button(f"Vai al Corso (ID: {id_corso}) 🔗", link)
                        st.divider()
                except: pass
        st.stop()
    except:
        st.error("Errore lettura QR.")
        st.stop()

# --- 3. LOGIN STAFF ---
if "auth" not in st.session_state:
    st.title("🎓 Accesso Staff")
    col1, col2 = st.columns([3,1])
    with col1:
        pwd = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Password")
    with col2:
        if st.button("Entra"):
            if pwd == st.secrets["APP_PASSWORD"]:
                st.session_state.auth = True
                st.rerun()
    st.stop()

# --- 4. CARICAMENTO DATI (Con ID) ---
@st.cache_data
def load_data():
    try:
        # Carica il CSV generato dallo scraper
        df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv").dropna(how='all')
        # Assicuriamoci che la colonna ID sia stringa
        if "ID" in df.columns:
            df["ID"] = df["ID"].astype(str)
        else:
            df["ID"] = "N/D" # Fallback se manca colonna
        return df
    except:
        # Fallback estremo se manca il file
        return pd.DataFrame([
            {"ID": "12345", "Titolo": "Corso Demo IA", "Link": "https://scuolafutura.pubblica.istruzione.it/", "Livello": "A1"}
        ])

df = load_data()

# Configurazione AI
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-flash-latest')
except:
    st.error("Errore Chiave API")
    st.stop()

# --- 5. INTERFACCIA RICERCA (DROPDOWN) ---
if "risultato_ia" not in st.session_state: st.session_state.risultato_ia = None

st.title("🔍 Consulente Formativo")

col_scuola, col_tema = st.columns(2)
with col_scuola:
    scuola = st.selectbox("Livello Scuola", ["Infanzia", "Primaria", "Secondaria I grado", "Secondaria II grado", "CPIA", "Tutti"])
with col_tema:
    tema = st.selectbox("Tematica", ["Intelligenza Artificiale", "STEM e Robotica", "Metodologie", "Inclusione", "Lingue", "Tutti"])

if st.button("🔎 Cerca nel Catalogo", use_container_width=True):
    with st.spinner("Analisi database corsi..."):
        # Prompt che include l'ID
        context = f"Catalogo (Colonne: ID, Titolo, Link): {df.to_string(index=False)}"
        prompt = f"""
        Sei un orientatore esperto. Analizza il catalogo.
        Utente cerca corsi per: {scuola}, Tema: {tema}.
        
        OUTPUT RICHIESTO PER OGNI CORSO (Rispetta rigorosamente questo formato):
        
        1. **[ID: INSERISCI_QUI_ID_DAL_CSV] Titolo del Corso**
        * *Abstract*: (Scrivi una breve descrizione accattivante di 2 righe sul contenuto ipotetico).
        * *Livello DigCompEdu*: (Stima un livello es: A2, B1).
        * Link: [Scheda Corso](LINK_ESATTO_DAL_CSV)
        
        Usa SOLO i corsi presenti nel CSV. Non inventare ID o Link.
        """
        try:
            res = model.generate_content(prompt)
            st.session_state.risultato_ia = res.text
        except Exception as e:
            st.error(f"Errore AI: {e}")

# --- 6. REPORT E QR CODE (Con ID) ---
if st.session_state.risultato_ia:
    st.write("---")
    st.subheader("💡 Risultati Ricerca")
    st.markdown(st.session_state.risultato_ia)
    
    st.success("✅ Generazione completata")
    
    # ESTRAZIONE DATI PER QR (ID | Titolo | Link)
    lines = st.session_state.risultato_ia.split('\n')
    qr_payload = ""
    current_id = "00000"
    current_title = "Corso"
    
    for line in lines:
        # Cerca ID e Titolo nella riga 1. **[ID: 123] Titolo**
        if "**" in line and "ID:" in line:
            # Pulisce la riga
            clean_line = line.replace("*", "").replace("1.", "").strip()
            # Estrae ID tra parentesi quadre
            match_id = re.search(r'ID:\s*(\d+)', clean_line)
            if match_id:
                current_id = match_id.group(1)
                # Il titolo è quello che resta dopo la parentesi chiusa
                parts = clean_line.split(']')
                if len(parts) > 1:
                    current_title = parts[1].strip()
        
        # Cerca Link
        if "http" in line:
            match_link = re.search(r'(https?://[^\s\)]+)', line)
            if match_link:
                url = match_link.group(1)
                # Aggiunge al payload: ID|Titolo|Link
                qr_payload += f"{current_id}|{current_title}|{url}\n"

    if not qr_payload:
        qr_payload = "00000|Vai al sito Scuola Futura|https://scuolafutura.pubblica.istruzione.it/"

    # Codifica Base64 per URL QR
    b64_payload = base64.b64encode(qr_payload.encode('utf-8')).decode('utf-8')
    qr_url = f"https://mimmo-consulente-didacta.streamlit.app/?qrlite={b64_payload}"
    
    # Genera QR
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(buf.getvalue(), caption="QR con ID Corsi", width=200)
    with col2:
        st.info("Inquadra per scaricare la lista con **ID Percorso** e **Link diretti**.")
        if st.button("🔄 Nuova Ricerca"):
            st.session_state.risultato_ia = None
            st.rerun()
