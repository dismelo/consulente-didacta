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
        [data-testid="stVerticalBlock"] {{ padding-top: 100px; padding-bottom: 120px; }}
        header {{ visibility: hidden; }}
        </style>''', unsafe_allow_html=True)
    except: pass

set_bg('sfondo_eft.png')

# --- 2. MODALITÀ OSPITE (QR-CODE) ---
if "report" in st.query_params:
    st.title("📄 Il Tuo Report Personale")
    try:
        testo = base64.b64decode(st.query_params["report"]).decode('utf-8')
        st.info("Ecco il riepilogo dei corsi suggeriti per te.")
        st.markdown(testo)
        
        def pdf_ospite(txt):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 10, txt=txt.encode('latin-1', 'ignore').decode('latin-1'))
            return pdf.output(dest='S').encode('latin-1')

        st.download_button("📥 Scarica Report PDF", data=pdf_ospite(testo), file_name="Mio_Report_EFT.pdf")
        st.stop()
    except:
        st.error("Errore report.")
        st.stop()

# --- 3. ACCESSO ADMIN ---
if "auth" not in st.session_state:
    st.title("🎓 Accesso Stand Didacta")
    pwd = st.text_input("Password Staff", type="password")
    if st.button("Accedi"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else: st.error("Password errata")
    st.stop()

# --- 4. CARICAMENTO DATI (CON DATI DI PROVA SE VUOTO) ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv")
        if df.empty: raise ValueError
        return df
    except:
        # DATI DI EMERGENZA (DEMO)
        return pd.DataFrame([
            {"Titolo": "Corso Demo IA", "Link": "https://scuolafutura.pubblica.istruzione.it/", "Livello": "A1"},
            {"Titolo": "Corso Demo Robotica", "Link": "https://scuolafutura.pubblica.istruzione.it/", "Livello": "B1"},
            {"Titolo": "Corso Demo STEAM", "Link": "https://scuolafutura.pubblica.istruzione.it/", "Livello": "A2"}
        ])

df = load_data()

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # MODIFICA QUI: Usiamo il modello "pro" che è più compatibile
    model = genai.GenerativeModel('gemini-pro')
except:
    st.error("Errore API Key Gemini.")
    st.stop()

# --- 5. INTERFACCIA CHAT (SEMPRE VISIBILE) ---
if "msgs" not in st.session_state: st.session_state.msgs = []
if "finito" not in st.session_state: st.session_state.finito = False

st.title("🔍 Consulente Formativo")

try:
    pd.read_csv("Catalogo_Corsi_EFT_2026.csv")
except:
    st.warning("⚠️ Modalità DEMO (Dati reali non disponibili).")

for m in st.session_state.msgs:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if not st.session_state.finito:
    if p := st.chat_input("Cerca..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        context = f"Dati corsi: {df.to_string()}. REGOLA: Usa SOLO i link della colonna Link."
        try:
            r = model.generate_content(f"{context}\nDomanda: {p}")
            st.session_state.msgs.append({"role": "assistant", "content": r.text})
            with st.chat_message("assistant"): st.markdown(r.text)
        except Exception as e:
            # Mostra l'errore in modo più gentile
            st.error(f"Errore di comunicazione con l'AI: {e}")

    if len(st.session_state.msgs) > 0:
        if st.button("🏁 Genera QR per il Docente"):
            st.session_state.finito = True
            st.rerun()

else:
    # --- 6. FASE DI CONSEGNA ---
    st.success("✅ Consulenza completata")
    
    full_text = "\n\n".join([m["content"] for m in st.session_state.msgs if m["role"] == "assistant"])
    base_url = "https://mimmo-consulente-didacta.streamlit.app/"
    encoded_text = base64.b64encode(full_text.encode('utf-8')).decode('utf-8')
    qr_url = f"{base_url}?report={encoded_text[:1500]}"
    
    img = qrcode.make(qr_url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(buf.getvalue(), caption="Fai scansionare questo QR")
    with col2:
        st.info("Il docente può scaricare il PDF sul suo telefono.")
        if st.button("🔄 Nuova Ricerca"):
            st.session_state.msgs = []
            st.session_state.finito = False
            st.rerun()
