import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
from fpdf import FPDF
from datetime import datetime

# 1. CONFIGURAZIONE PAGINA E SFONDO
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_png_as_page_bg(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    page_bg_img = '''
    <style>
    .stApp {
        background-image: url("data:image/png;base64,%s");
        background-size: 100%% 100%%;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    [data-testid="stVerticalBlock"] > div:first-child { margin-top: 150px; }
    [data-testid="stChatMessageContainer"] { padding-bottom: 180px; max-width: 800px; margin: auto; }
    [data-testid="stChatInput"] { bottom: 110px !important; max-width: 800px; margin: auto; }
    header { visibility: hidden; }
    </style>
    ''' % bin_str
    st.markdown(page_bg_img, unsafe_allow_html=True)

set_png_as_page_bg('sfondo_eft.png')

# 2. INIZIALIZZAZIONE STATO (RESET)
if "messages" not in st.session_state:
    st.session_state.messages = []

def reset_chat():
    st.session_state.messages = []
    st.rerun()

# 3. CARICAMENTO DATI (DAL CSV AGGIORNATO DALLO SCRAPER)
@st.cache_data
def load_data():
    try:
        return pd.read_csv("Catalogo_Corsi_EFT_2026.csv")
    except:
        return pd.DataFrame(columns=["Titolo", "Sintesi", "Obiettivi", "DigCompEdu_Competenze", "Livello", "Link"])

df_corsi = load_data()

# 4. CONFIGURAZIONE AI
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('models/gemini-flash-latest')

# 5. LOGICA PDF
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Report Orientamento Corsi EFT 2026', 0, 1, 'C')
        self.ln(5)

def create_pdf(text):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 10, txt=text)
    pdf.ln(10)
    pdf.set_text_color(0, 0, 255)
    pdf.cell(0, 10, "Consulta i corsi su Scuola Futura", link="https://scuolafutura.pubblica.istruzione.it/", ln=1)
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 6. INTERFACCIA CHAT
st.title("🎓 Orientatore EFT 2026")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Chiedimi dei corsi..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Preparazione contesto per l'IA
    context = f"Dati corsi disponibili: {df_corsi.to_string()}\n\nRispondi includendo Titolo, Sintesi, Obiettivi, Competenze DigCompEdu, Livello e Link cliccabile."
    
    with st.chat_message("assistant"):
        response = model.generate_content(f"{context}\n\nUtente chiede: {prompt}")
        full_response = response.text
        st.markdown(full_response)
        
        # Pulsanti Azione
        col1, col2 = st.columns(2)
        with col1:
            pdf_bytes = create_pdf(full_response)
            st.download_button("📥 Scarica Report PDF", data=pdf_bytes, file_name="consigli_corsi_eft.pdf", mime="application/pdf")
        with col2:
            if st.button("🔄 Nuova Ricerca"):
                reset_chat()

    st.session_state.messages.append({"role": "assistant", "content": full_response})

# 7. CHIUSURA CORDIALE
if len(st.session_state.messages) > 1:
    st.info("Grazie per avermi consultato. Arrivederci e tieniti aggiornato sui corsi delle EFT su [Scuola Futura](https://scuolafutura.pubblica.istruzione.it/).")
