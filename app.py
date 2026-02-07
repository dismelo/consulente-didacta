import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
import qrcode
import re
from io import BytesIO
from fpdf import FPDF

# --- 1. CONFIGURAZIONE E SFONDO (Caricato per primo) ---
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
        /* Migliora visibilità testi su sfondo */
        .stMarkdown, .stText, h1, h2, h3 {{ 
            text-shadow: 0px 0px 5px rgba(255,255,255,0.8); 
        }}
        /* Spaziatura per non coprire loghi */
        [data-testid="stVerticalBlock"] {{ padding-top: 80px; padding-bottom: 100px; }}
        header {{ visibility: hidden; }}
        </style>''', unsafe_allow_html=True)
    except: pass

set_bg('sfondo_eft.png')

# --- 2. MODALITÀ OSPITE (Visualizzazione da QR) ---
if "qrlite" in st.query_params:
    st.title("📱 I Tuoi Corsi (Versione Mobile)")
    try:
        # Decodifica payload leggero
        dati_raw = base64.b64decode(st.query_params["qrlite"]).decode('utf-8')
        st.info("Ecco i link diretti alle schede dei corsi selezionati.")
        
        # Visualizzazione pulita dei link
        for riga in dati_raw.split('\n'):
            if "|" in riga:
                titolo, link = riga.split('|', 1)
                st.markdown(f"**{titolo}**")
                st.link_button(f"Vai alla scheda 🔗", link)
                st.write("---")
        
        st.stop() # Ferma l'app qui per l'ospite
    except:
        st.error("Link non valido.")
        st.stop()

# --- 3. LOGIN ADMIN ---
if "auth" not in st.session_state:
    st.title("🎓 Accesso Stand Didacta")
    col1, col2 = st.columns([3,1])
    with col1:
        pwd = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Inserisci Password")
    with col2:
        if st.button("Entra"):
            if pwd == st.secrets["APP_PASSWORD"]:
                st.session_state.auth = True
                st.rerun()
            else: st.error("No")
    st.stop()

# --- 4. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv").dropna(how='all')
        if df.empty: raise ValueError
        return df
    except:
        return pd.DataFrame([
            {"Titolo": "Corso IA Generativa Base", "Link": "https://scuolafutura.pubblica.istruzione.it/", "Livello": "A1"},
            {"Titolo": "Robotica e STEM", "Link": "https://scuolafutura.pubblica.istruzione.it/", "Livello": "B1"}
        ])

df = load_data()

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-flash-latest')
except:
    st.error("Errore API Key")
    st.stop()

# --- 5. INTERFACCIA DI RICERCA (DROPDOWN) ---
if "risultato_ia" not in st.session_state: st.session_state.risultato_ia = None

st.title("🔍 Consulente Formativo")

# Menu a tendina
col_scuola, col_tema = st.columns(2)
with col_scuola:
    scuola = st.selectbox("Livello Scuola", 
        ["Infanzia", "Primaria", "Secondaria I grado", "Secondaria II grado", "CPIA", "Tutti"])

with col_tema:
    tema = st.selectbox("Tematica Interesse", 
        ["Intelligenza Artificiale", "STEM e Robotica", "Metodologie Didattiche", "Inclusione", "Realtà Aumentata/Virtuale", "Tutti"])

# Pulsante di Ricerca
if st.button("🔎 Cerca Corsi", use_container_width=True):
    with st.spinner("Analisi catalogo in corso..."):
        # Prompt Strutturato
        context = f"Catalogo Corsi: {df.to_string(index=False)}"
        prompt = f"""
        Agisci come un esperto orientatore scolastico.
        Analizza il catalogo fornito e trova i corsi migliori per:
        - Target: {scuola}
        - Tema: {tema}
        
        REQUISITI RISPOSTA (Obbligatori):
        Per ogni corso trovato devi scrivere ESATTAMENTE questo formato:
        1. **Titolo del corso**
        2. *Abstract*: (breve descrizione accattivante)
        3. *Livelli DigCompEdu*: (es. A1, B2 - inventa se non specificato ma sii coerente)
        4. Link: [clicca qui](url_preso_dal_csv)
        
        Usa SOLO i link presenti nel CSV. Se non trovi nulla, suggerisci corsi affini.
        """
        try:
            res = model.generate_content(prompt)
            st.session_state.risultato_ia = res.text
        except Exception as e:
            st.error(f"Errore: {e}")

# --- 6. VISUALIZZAZIONE REPORT E QR ---
if st.session_state.risultato_ia:
    st.write("---")
    st.subheader("💡 Corsi Suggeriti")
    st.markdown(st.session_state.risultato_ia)
    
    st.success("✅ Ricerca completata")
    
    # --- LOGICA QR CODE LEGGERO (SOLO TITOLO + LINK) ---
    # Usiamo una regex per estrarre solo i link e i titoli dalla risposta dell'IA
    # Formato target per il QR: "Titolo|Link\nTitolo|Link"
    lines = st.session_state.risultato_ia.split('\n')
    qr_payload = ""
    current_title = "Corso suggerito"
    
    for line in lines:
        # Cerca righe che sembrano titoli (grassetto)
        if "**" in line:
            current_title = line.replace("**", "").replace("1.", "").strip()
        # Cerca link
        if "http" in line:
            # Estrae l'url pulito
            match = re.search(r'(https?://[^\s\)]+)', line)
            if match:
                url = match.group(1)
                qr_payload += f"{current_title}|{url}\n"

    # Se non trova nulla, mette un link generico
    if not qr_payload:
        qr_payload = "Vai a Scuola Futura|https://scuolafutura.pubblica.istruzione.it/"

    # Codifica Payload
    b64_payload = base64.b64encode(qr_payload.encode('utf-8')).decode('utf-8')
    base_url = "https://mimmo-consulente-didacta.streamlit.app/"
    qr_url = f"{base_url}?qrlite={b64_payload}"
    
    # Generazione QR
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(buf.getvalue(), caption="Scansiona per salvare i link", width=200)
    with col2:
        st.info("📷 **QR-Code Ottimizzato**: Inquadra per aprire la lista essenziale (Titoli + Link) sul tuo telefono.")
        if st.button("🔄 Nuova Ricerca"):
            st.session_state.risultato_ia = None
            st.rerun()
