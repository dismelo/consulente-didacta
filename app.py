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
        /* Spazio extra in alto e in basso per proteggere i loghi */
        [data-testid="stVerticalBlock"] {{ padding-top: 100px; padding-bottom: 120px; }}
        header {{ visibility: hidden; }}
        </style>''', unsafe_allow_html=True)
    except: pass # Se non trova lo sfondo, pazienza, va avanti lo stesso

set_bg('sfondo_eft.png')

# --- 2. MODALITÀ OSPITE (Per chi scansiona il QR) ---
if "report" in st.query_params:
    st.title("📄 Il Tuo Report Personale")
    try:
        # Recupera il testo dal link
        testo_report = base64.b64decode(st.query_params["report"]).decode('utf-8')
        st.info("Ecco il riepilogo dei corsi suggeriti per te.")
        st.markdown(testo_report)
        
        # Generatore PDF al volo per l'ospite
        def pdf_ospite(txt):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 10, txt=txt.encode('latin-1', 'ignore').decode('latin-1'))
            return pdf.output(dest='S').encode('latin-1')

        st.download_button("📥 Scarica Report PDF", data=pdf_ospite(testo_report), file_name="Mio_Report_EFT.pdf")
        st.stop() # Ferma qui l'app per l'ospite
    except:
        st.error("Errore: Impossibile visualizzare il report.")
        st.stop()

# --- 3. ACCESSO ADMIN (Solo per lo Staff allo stand) ---
if "auth" not in st.session_state:
    st.title("🎓 Accesso Stand Didacta")
    pwd = st.text_input("Inserisci Password Staff", type="password")
    if st.button("Accedi"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else: st.error("Password errata")
    st.stop()

# --- 4. CARICAMENTO DATI (Senza crashare se vuoto) ---
@st.cache_data
def get_data():
    try:
        df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv")
        if df.empty: return pd.DataFrame() # Ritorna vuoto ma non crasha
        return df
    except:
        return pd.DataFrame() # Ritorna vuoto se il file manca

df = get_data()

# Configurazione AI
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Errore configurazione AI. Controlla l'API Key.")
    st.stop()

# --- 5. INTERFACCIA DI RICERCA ---
if "msgs" not in st.session_state: st.session_state.msgs = []
if "finito" not in st.session_state: st.session_state.finito = False

st.title("🔍 Consulente Formativo")

# Se il file CSV è vuoto, mostriamo un avviso ma l'app resta viva
if df.empty:
    st.warning("⚠️ Attenzione: Il catalogo corsi sembra vuoto. Verifica l'aggiornamento dati su GitHub.")
else:
    # Mostra chat
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if not st.session_state.finito:
        if p := st.chat_input("Es: Cerco un corso sull'IA per la primaria..."):
            st.session_state.msgs.append({"role": "user", "content": p})
            with st.chat_message("user"): st.markdown(p)
            
            # Istruzioni blindate per i link
            context = f"Dati corsi: {df.to_string()}. REGOLA: Usa SOLO i link presenti nella colonna 'Link'. Non inventare URL."
            try:
                r = model.generate_content(f"{context}\nRichiesta utente: {p}")
                st.session_state.msgs.append({"role": "assistant", "content": r.text})
                with st.chat_message("assistant"): st.markdown(r.text)
            except Exception as e:
                st.error(f"Errore nella risposta dell'AI: {e}")

        if len(st.session_state.msgs) > 0:
            if st.button("🏁 Genera QR per il Docente"):
                st.session_state.finito = True
                st.rerun()

    else:
        # --- 6. FASE DI CONSEGNA (QR) ---
        st.success("✅ Consulenza completata")
        
        # Creiamo il testo completo per il QR
        full_text = "\n\n".join([m["content"] for m in st.session_state.msgs if m["role"] == "assistant"])
        
        # Link per l'ospite
        base_url = "https://mimmo-consulente-didacta.streamlit.app/" # Assicurati che sia giusto
        encoded_text = base64.b64encode(full_text.encode('utf-8')).decode('utf-8')
        # Limitiamo a 1500 caratteri per evitare QR troppo densi
        qr_url = f"{base_url}?report={encoded_text[:1500]}"
        
        img = qrcode.make(qr_url)
        buf = BytesIO()
        img.save(buf, format="PNG")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(buf.getvalue(), caption="Fai scansionare questo QR al docente")
        with col2:
            st.info("Il docente vedrà il report sul suo telefono e potrà scaricare il PDF, senza bisogno di password.")
            if st.button("🔄 Nuova Ricerca"):
                st.session_state.msgs = []
                st.session_state.finito = False
                st.rerun()
