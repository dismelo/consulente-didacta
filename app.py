import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
import qrcode
from io import BytesIO
from fpdf import FPDF

# --- 1. CONFIGURAZIONE E GRAFICA (Sfondo e distanze dai loghi) ---
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
        /* Spazio extra sopra e sotto per non coprire i loghi */
        [data-testid="stVerticalBlock"] {{ padding-top: 100px; padding-bottom: 150px; }}
        .stChatFloatingInputContainer {{ bottom: 120px; }}
        header {{ visibility: hidden; }}
        </style>''', unsafe_allow_html=True)
    except: pass

set_bg('sfondo_eft.png')

# --- 2. MODALITÀ OSPITE (Per chi scansiona il QR) ---
query_params = st.query_params
if "report" in query_params:
    st.title("📄 Il Tuo Report Personale")
    try:
        # Decodifica il testo dal link del QR
        testo_report = base64.b64decode(query_params["report"]).decode('utf-8')
        st.info("Ecco i risultati della tua consulenza allo stand EFT.")
        st.markdown(testo_report)
        
        def download_ospite(t):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 10, txt=t.encode('latin-1', 'ignore').decode('latin-1'))
            return pdf.output(dest='S').encode('latin-1')

        st.download_button("📥 Scarica Report PDF sul telefono", data=download_ospite(testo_report), file_name="mio_report_EFT.pdf")
        st.stop()
    except:
        st.error("Link non valido o scaduto.")

# --- 3. CONTROLLO PASSWORD (Admin) ---
if "auth" not in st.session_state:
    st.title("🔐 Accesso Riservato Stand")
    pwd = st.text_input("Inserisci password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else: st.error("Password errata")
    st.stop()

# --- 4. CARICAMENTO DATI (Risolve l'EmptyDataError) ---
@st.cache_data
def get_data():
    try:
        data = pd.read_csv("Catalogo_Corsi_EFT_2026.csv")
        if data.empty: raise ValueError
        return data
    except:
        # Se il file è vuoto o manca, creiamo una riga di esempio per non far crashare l'app
        return pd.DataFrame([{"Titolo": "Esempio", "Link": "https://scuolafutura.pubblica.istruzione.it/", "Livello": "A1"}])

df = get_data()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 5. CHAT E LOGICA ---
if "msgs" not in st.session_state: st.session_state.msgs = []
if "finito" not in st.session_state: st.session_state.finito = False

st.title("🎓 Consulente Didacta 2026")

for m in st.session_state.msgs:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if not st.session_state.finito:
    if p := st.chat_input("Cerca corsi..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        # ORDINI RIGIDI ALL'IA: Solo link dal CSV
        istruzioni = f"Dati: {df.to_string()}. REGOLA: Usa SOLO i link della colonna Link. Non citare siti esterni."
        r = model.generate_content(f"{istruzioni}\nDomanda: {p}")
        
        st.session_state.msgs.append({"role": "assistant", "content": r.text})
        with st.chat_message("assistant"): st.markdown(r.text)

    if len(st.session_state.msgs) > 0:
        if st.button("🏁 Genera QR per il Docente"):
            st.session_state.finito = True
            st.rerun()
else:
    # --- 6. SCHERMATA FINALE CON QR E PDF ---
    report_completo = ""
    for m in st.session_state.msgs:
        if m["role"] == "assistant": report_completo += m["content"] + "\n\n"

    st.success("### Consulenza Terminata")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("Fai inquadrare il QR al docente per fargli scaricare il report sul suo telefono.")
        if st.button("🔄 Nuova Ricerca"):
            st.session_state.msgs = []
            st.session_state.finito = False
            st.rerun()

    with col2:
        # Creiamo il link magico per l'ospite
        app_url = "https://mimmo-consulente-didacta.streamlit.app/" 
        payload = base64.b64encode(report_completo.encode('utf-8')).decode('utf-8')
        qr_url = f"{app_url}?report={payload[:1500]}" # Limite caratteri QR
        
        qr_img = qrcode.make(qr_url)
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        st.image(buf.getvalue(), width=230, caption="Scansiona il tuo Report")
