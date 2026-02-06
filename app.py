import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
import qrcode
import json
from io import BytesIO
from fpdf import FPDF

# --- 1. CONFIGURAZIONE E SFONDO IMMEDIATO ---
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
    [data-testid="stVerticalBlock"] {{ padding-top: 80px; padding-bottom: 100px; }}
    header {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    </style>''', unsafe_allow_html=True)

set_bg('sfondo_eft.png')

# --- 2. GESTIONE MODALITÀ OSPITE (VIA QR-CODE) ---
# Se l'URL contiene dati del report, mostriamo solo quelli senza password
query_params = st.query_params
if "report_data" in query_params:
    st.title("📄 Il tuo Report Orientamento")
    try:
        # Decodifichiamo i dati dal QR
        report_text = base64.b64decode(query_params["report_data"]).decode('utf-8')
        st.info("Ecco i corsi selezionati per te durante la consulenza allo stand EFT.")
        st.markdown(report_text)
        
        # Funzione download PDF per l'ospite
        def guest_pdf(text):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 10, txt=text.encode('latin-1', 'ignore').decode('latin-1'))
            return pdf.output(dest='S').encode('latin-1')
            
        st.download_button("📥 Salva PDF sul tuo smartphone", data=guest_pdf(report_text), file_name="mio_report_EFT.pdf")
        st.stop() # Ferma l'app qui per l'ospite
    except:
        st.error("Errore nel caricamento del report.")

# --- 3. ACCESSO ADMIN (CON PASSWORD) ---
def check_password():
    if "authenticated" not in st.session_state:
        st.title("🎓 Orientatore EFT - Stand Didacta")
        pwd = st.text_input("Password di servizio", type="password")
        if st.button("Accedi"):
            if pwd == st.secrets["APP_PASSWORD"]:
                st.session_state["authenticated"] = True
                st.rerun()
            else: st.error("Accesso negato")
        return False
    return True

if not check_password(): st.stop()

# --- 4. LOGICA CHAT E DATI ---
if "messages" not in st.session_state: st.session_state.messages = []
if "finalizzato" not in st.session_state: st.session_state.finalizzato = False

@st.cache_data
def load_data():
    return pd.read_csv("Catalogo_Corsi_EFT_2026.csv")

df = load_data()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 5. INTERFACCIA DI CONSULENZA ---
st.title("🎓 Consulente Formativo EFT")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if not st.session_state.finalizzato:
    if prompt := st.chat_input("Quali corsi cerchiamo?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        # ISTRUZIONI RIGIDE PER L'IA
        system_instruction = f"""
        Sei un consulente EFT. Usa QUESTI DATI: {df.to_string()}.
        REGOLE TASSATIVE:
        1. Non inventare MAI link. Usa solo l'URL presente nella colonna 'Link' del CSV.
        2. Per ogni corso elenca: Titolo, Livello DigCompEdu e il Link alla scheda ufficiale.
        3. Se non trovi nulla, non suggerire siti esterni, ma di consultare Scuola Futura.
        """
        
        response = model.generate_content(f"{system_instruction}\n\nUtente: {prompt}")
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        with st.chat_message("assistant"): st.markdown(response.text)

    if len(st.session_state.messages) > 0:
        if st.button("🏁 Concludi e consegna al Docente"):
            st.session_state.finalizzato = True
            st.rerun()

# --- 6. SCHERMATA DI CONSEGNA (QR E PDF) ---
else:
    st.success("### Consulenza Terminata")
    report_completo = "\n\n".join([m["content"] for m in st.session_state.messages if m["role"] == "assistant"])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("👋 **Messaggio di saluto:**")
        st.write("Grazie per averci visitato! Tieniti aggiornato sui corsi EFT su Scuola Futura.")
        
        if st.button("🔄 Nuova Consulenza"):
            st.session_state.messages = []
            st.session_state.finalizzato = False
            st.rerun()

    with col2:
        # Generiamo il QR-Code che contiene il link "Ospite" con i dati del report
        base_url = "https://mimmo-consulente-didacta.streamlit.app/" # Assicurati sia corretto
        encoded_report = base64.b64encode(report_completo.encode('utf-8')).decode('utf-8')
        # QR limitato a circa 2000 caratteri per stabilità
        qr_link = f"{base_url}?report_data={encoded_report[:1500]}" 
        
        img_qr = qrcode.make(qr_link)
        buf = BytesIO()
        img_qr.save(buf, format="PNG")
        
        st.write("**📱 Fai scansionare al docente:**")
        st.image(buf.getvalue(), width=200, caption="Scansiona per il tuo Report")
