import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
import qrcode
from io import BytesIO
from fpdf import FPDF

# --- 1. CONFIGURAZIONE E GRAFICA ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

def set_bg(png_file):
    try:
        with open(png_file, 'rb') as f:
            bin_str = base64.b64encode(f.read()).decode()
        st.markdown(f'''<style>
        .stApp {{ 
            background-image: url("data:image/png;base64,{bin_str}"); 
            background-size: 100% 100%; 
            background-attachment: fixed; 
        }}
        [data-testid="stVerticalBlock"] {{ padding-top: 100px; padding-bottom: 150px; }}
        header {{ visibility: hidden; }}
        </style>''', unsafe_allow_html=True)
    except: pass

set_bg('sfondo_eft.png')

# --- 2. MODALITÀ OSPITE (QR-CODE) ---
if "report" in st.query_params:
    st.title("📄 Il Tuo Report Personale")
    try:
        testo = base64.b64decode(st.query_params["report"]).decode('utf-8')
        st.info("Ecco i corsi selezionati per te.")
        st.markdown(testo)
        st.stop()
    except: st.error("Errore caricamento report")

# --- 3. ACCESSO ADMIN ---
if "auth" not in st.session_state:
    st.title("🎓 Accesso Stand Didacta")
    pwd = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else: st.error("Errata")
    st.stop()

# --- 4. CARICAMENTO DATI (CORREZIONE EMPTYDATAERROR) ---
@st.cache_data
def load_data():
    try:
        data = pd.read_csv("Catalogo_Corsi_EFT_2026.csv")
        if data.empty: return pd.DataFrame(columns=["Titolo", "Link", "Livello"])
        return data
    except Exception:
        # Se il file non esiste o è vuoto, non crashare
        return pd.DataFrame(columns=["Titolo", "Link", "Livello"])

df = load_data()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 5. LOGICA CHAT ---
if "msgs" not in st.session_state: st.session_state.msgs = []
if "finito" not in st.session_state: st.session_state.finito = False

st.title("🔍 Consulente Formativo EFT")

for m in st.session_state.msgs:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if not st.session_state.finito:
    if p := st.chat_input("Cerca..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        # Prompt per forzare solo link da CSV
        context = f"Dati corsi disponibili: {df.to_string()}. REGOLA: Usa SOLO i link della colonna Link. Non inventare URL."
        r = model.generate_content(f"{context}\nDomanda: {p}")
        
        st.session_state.msgs.append({"role": "assistant", "content": r.text})
        with st.chat_message("assistant"): st.markdown(r.text)

    if len(st.session_state.msgs) > 0:
        if st.button("🏁 Genera QR per il Docente"):
            st.session_state.finito = True
            st.rerun()
else:
    # --- 6. SCHERMATA QR ---
    report_completo = "\n\n".join([m["content"] for m in st.session_state.msgs if m["role"] == "assistant"])
    payload = base64.b64encode(report_completo.encode('utf-8')).decode('utf-8')
    qr_url = f"https://mimmo-consulente-didacta.streamlit.app/?report={payload[:1500]}"
    
    img = qrcode.make(qr_url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.image(buf.getvalue(), width=250, caption="Fai scansionare al docente")
    
    if st.button("🔄 Nuova Ricerca"):
        st.session_state.msgs = []
        st.session_state.finito = False
        st.rerun()
