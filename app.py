import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
import qrcode
from io import BytesIO
from fpdf import FPDF

# --- 1. CONFIGURAZIONE PAGINA E SFONDO (Sempre visibile) ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

def set_bg(png_file):
    with open(png_file, 'rb') as f:
        bin_str = base64.b64encode(f.read()).decode()
    st.markdown(f'''<style>
    .stApp {{ 
        background-image: url("data:image/png;base64,{bin_str}"); 
        background-size: 100% 100%; 
        background-attachment: fixed; 
    }}
    /* Distanza per non coprire i loghi in alto e in basso */
    [data-testid="stVerticalBlock"] {{ padding-top: 120px; padding-bottom: 120px; }}
    .stChatFloatingInputContainer {{ bottom: 100px; }}
    header {{ visibility: hidden; }}
    </style>''', unsafe_allow_html=True)

# Carichiamo lo sfondo SUBITO, prima di ogni altra cosa
try:
    set_bg('sfondo_eft.png')
except:
    st.warning("File sfondo_eft.png non trovato. Caricalo su GitHub.")

# --- 2. GESTIONE PASSWORD ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Accesso Riservato")
        pwd = st.text_input("Inserisci la password per iniziare", type="password")
        if st.button("Entra"):
            if pwd == st.secrets["APP_PASSWORD"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Password errata")
        return False
    return True

if not check_password():
    st.stop()

# --- 3. INIZIALIZZAZIONE STATI ---
if "messages" not in st.session_state: st.session_state.messages = []
if "show_report" not in st.session_state: st.session_state.show_report = False

# --- 4. FUNZIONI TECNICHE (PDF & QR) ---
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Report Orientamento EFT 2026", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=11)
    clean_text = text.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 8, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

def generate_qr(url):
    qr = qrcode.make(url)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

# --- 5. CARICAMENTO DATI E AI ---
@st.cache_data
def load_data():
    try: return pd.read_csv("Catalogo_Corsi_EFT_2026.csv")
    except: return pd.DataFrame(columns=["Titolo", "Sintesi", "Obiettivi", "DigCompEdu_Competenze", "Livello", "Link"])

df = load_data()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('models/gemini-flash-latest')

# --- 6. INTERFACCIA DI RICERCA ---
st.title("🎓 Orientatore EFT 2026")

# Mostriamo lo storico messaggi
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Se la ricerca NON è conclusa, mostriamo l'input
if not st.session_state.show_report:
    if prompt := st.chat_input("Cerca un corso..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        context = f"Dati corsi: {df.to_string()}\nRispondi includendo Titolo, Competenze DigCompEdu e Link."
        response = model.generate_content(f"{context}\nDomanda: {prompt}")
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        with st.chat_message("assistant"):
            st.markdown(response.text)

    # Pulsante per chiudere la ricerca (appare se c'è almeno un messaggio)
    if len(st.session_state.messages) > 0:
        st.write("---")
        if st.button("🏁 Ricerca conclusa: genera report e saluti"):
            st.session_state.show_report = True
            st.rerun()

# --- 7. SCHERMATA FINALE (REPORT, QR, RESET) ---
else:
    st.success("### ✅ Ricerca Ultimata")
    st.info("Grazie per avermi consultato. Arrivederci e tieniti aggiornato sui corsi delle EFT su [Scuola Futura](https://scuolafutura.pubblica.istruzione.it/).")
    
    # Preparazione PDF
    full_text = ""
    for m in st.session_state.messages:
        if m["role"] == "assistant":
            full_text += m["content"] + "\n\n"

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.download_button(
            label="📥 SCARICA IL REPORT PDF",
            data=create_pdf(full_text),
            file_name="Report_EFT_Didacta.pdf",
            mime="application/pdf",
            key="download_btn" # La key fissa impedisce la sparizione
        )
        
        if st.button("🔄 Inizia Nuova Ricerca"):
            st.session_state.messages = []
            st.session_state.show_report = False
            st.rerun()

    with col2:
        st.write("**📱 Scansiona col telefono:**")
        app_url = "https://mimmo-consulente-didacta.streamlit.app/" # Inserisci qui l'URL della tua app
        st.image(generate_qr(app_url), width=150, caption="Porta l'app con te")
