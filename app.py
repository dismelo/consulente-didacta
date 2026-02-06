import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
import qrcode
from io import BytesIO
from fpdf import FPDF

# 1. CONFIGURAZIONE E PASSWORD
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

def check_password():
    if "password_correct" not in st.session_state:
        st.text_input("Accesso Riservato - Inserisci Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password errata", type="password", on_change=password_entered, key="password")
        return False
    return True

def password_entered():
    if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
    else:
        st.session_state["password_correct"] = False

if not check_password():
    st.stop()

# 2. SFONDO E STILE (Come richiesto)
def get_base64(bin_file):
    with open(bin_file, 'rb') as f: return base64.b64encode(f.read()).decode()

def set_bg(png_file):
    bin_str = get_base64(png_file)
    st.markdown(f'''<style>
    .stApp {{ background-image: url("data:image/png;base64,{bin_str}"); background-size: 100%% 100%%; background-attachment: fixed; }}
    [data-testid="stVerticalBlock"] > div:first-child {{ margin-top: 150px; }}
    [data-testid="stChatMessageContainer"] {{ padding-bottom: 180px; max-width: 800px; margin: auto; }}
    [data-testid="stChatInput"] {{ bottom: 110px !important; max-width: 800px; margin: auto; }}
    header {{ visibility: hidden; }}
    </style>''', unsafe_allow_html=True)

set_bg('sfondo_eft.png')

# 3. STATO DELLA SESSIONE
if "messages" not in st.session_state: st.session_state.messages = []
if "concluso" not in st.session_state: st.session_state.concluso = False

# 4. FUNZIONI PDF E QR
def generate_qr(url):
    qr = qrcode.make(url)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=text.encode('latin-1', 'ignore').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

# 5. CARICAMENTO DATI E AI
@st.cache_data
def load_data():
    try: return pd.read_csv("Catalogo_Corsi_EFT_2026.csv")
    except: return pd.DataFrame(columns=["Titolo", "Sintesi", "Obiettivi", "DigCompEdu_Competenze", "Livello", "Link"])

df = load_data()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('models/gemini-flash-latest')

# 6. INTERFACCIA
st.title("🎓 Orientatore EFT 2026")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if not st.session_state.concluso:
    if prompt := st.chat_input("Chiedimi dei corsi..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        context = f"Dati: {df.to_string()}\nRispondi con Titolo, Sintesi, Obiettivi, Competenze DigCompEdu, Livello e Link."
        response = model.generate_content(f"{context}\nDomanda: {prompt}")
        
        with st.chat_message("assistant"):
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            if st.button("🏁 Ricerca conclusa"):
                st.session_state.concluso = True
                st.rerun()

# 7. SCHERMATA FINALE (Solo se concluso)
if st.session_state.concluso:
    st.success("✅ Grazie per avermi consultato. Arrivederci e tieniti aggiornato sui corsi delle EFT su [Scuola Futura](https://scuolafutura.pubblica.istruzione.it/).")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        full_text = "\n".join([m["content"] for m in st.session_state.messages if m["role"]=="assistant"])
        st.download_button("📥 Scarica Report PDF", data=create_pdf(full_text), file_name="report_eft.pdf")
        
    with col2:
        if st.button("🔄 Nuova Ricerca"):
            st.session_state.messages = []
            st.session_state.concluso = False
            st.rerun()
            
    with col3:
        st.write("📱 Porta il report con te:")
        qr_img = generate_qr("https://scuolafutura.pubblica.istruzione.it/") # Qui puoi mettere il link dell'app
        st.image(qr_img, width=100)
