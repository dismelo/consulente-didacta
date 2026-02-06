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

# --- 2. MODALITÀ OSPITE (SCANSIONE QR) ---
if "report" in st.query_params:
    st.title("📄 Il Tuo Report Personale")
    try:
        testo = base64.b64decode(st.query_params["report"]).decode('utf-8')
        st.info("Ecco il riepilogo dei corsi suggeriti per te.")
        st.markdown(testo)
        
        def genera_pdf(txt):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 10, txt=txt.encode('latin-1', 'ignore').decode('latin-1'))
            return pdf.output(dest='S').encode('latin-1')

        st.download_button("📥 Scarica Report PDF", data=genera_pdf(testo), file_name="Mio_Report_EFT.pdf")
        st.stop()
    except:
        st.error("Errore nel caricamento del report.")
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

# --- 4. CARICAMENTO DATI (SICUREZZA ANTICRASH) ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv").dropna(how='all')
        if df.empty: raise ValueError
        return df
    except:
        # Se il CSV è vuoto o mancante, carica dati demo per non bloccare l'app
        return pd.DataFrame([
            {"Titolo": "Corso IA e Didattica", "Link": "https://scuolafutura.pubblica.istruzione.it/", "Livello": "A1"},
            {"Titolo": "Robotica Educativa", "Link": "https://scuolafutura.pubblica.istruzione.it/", "Livello": "B1"}
        ])

df = load_data()

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # MODELLO FUNZIONANTE VERIFICATO DA DIAGNOSTICA
    model = genai.GenerativeModel('gemini-flash-latest')
except Exception as e:
    st.error(f"Errore API Key: {e}")
    st.stop()

# --- 5. INTERFACCIA CHAT ---
if "msgs" not in st.session_state: st.session_state.msgs = []
if "finito" not in st.session_state: st.session_state.finito = False

st.title("🔍 Consulente Formativo")

# Avviso se siamo in modalità demo
try:
    pd.read_csv("Catalogo_Corsi_EFT_2026.csv")
except:
    st.warning("⚠️ Modalità DEMO (Dati reali non trovati nel CSV).")

for m in st.session_state.msgs:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if not st.session_state.finito:
    if p := st.chat_input("Cerca corsi (es. STEM, IA, Primaria)..."):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        context = f"Catalogo: {df.to_string(index=False)}. Istruzioni: Suggerisci i corsi e fornisci i link cliccabili."
        try:
            r = model.generate_content(f"{context}\n\nDomanda: {p}")
            st.session_state.msgs.append({"role": "assistant", "content": r.text})
            with st.chat_message("assistant"): st.markdown(r.text)
        except Exception as e:
            st.error(f"Errore AI: {e}")

    if len(st.session_state.msgs) > 0:
        if st.button("🏁 Genera QR per il Docente"):
            st.session_state.finito = True
            st.rerun()

else:
    # --- 6. FASE DI CONSEGNA QR ---
    st.success("✅ Consulenza completata")
    
    # Filtriamo solo le risposte dell'assistente
    responses = [m["content"] for m in st.session_state.msgs if m["role"] == "assistant"]
    full_text = "\n\n".join(responses)
    
    # Per rendere il QR leggibile, inviamo solo gli ultimi suggerimenti (max 800 caratteri)
    # e ottimizziamo i parametri del QR
    short_text = full_text[-800:] if len(full_text) > 800 else full_text
    
    base_url = "https://mimmo-consulente-didacta.streamlit.app/"
    encoded_text = base64.b64encode(short_text.encode('utf-8')).decode('utf-8')
    qr_url = f"{base_url}?report={encoded_text}"
    
    # Configurazione QR per massima leggibilità
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L, # Riduce la ridondanza per pixel più grandi
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    
    col1, col2 = st.columns([1, 1]) # Distanza maggiore tra le colonne
    with col1:
        st.image(buf.getvalue(), caption="Punta la fotocamera qui", width=300)
    with col2:
        st.write("### 📲 Istruzioni per il docente")
        st.info("Inquadra il QR per aprire il report sul tuo smartphone. Potrai scaricare l'elenco dei corsi in formato PDF.")
        if st.button("🔄 Nuova Ricerca"):
            st.session_state.msgs = []
            st.session_state.finito = False
            st.rerun()
