import streamlit as st
import pandas as pd
import google.generativeai as genai

# Configurazione Pagina
st.set_page_config(page_title="Orientatore EFT 2026", page_icon="🎓")

# --- INIZIO BLOCCO CSS PER SFONDO ---
import base64

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
        background-size: cover;
        background-position: center top;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    
    /* Stile per il contenitore principale della chat */
    [data-testid="stChatMessageContainer"] {
        padding-top: 180px; /* Spazio per l'intestazione dorata */
        padding-bottom: 100px; /* Spazio per i loghi in basso */
        max-width: 900px; /* Larghezza massima per non toccare i bordi */
        margin: auto; /* Centra la chat orizzontalmente */
    }

    /* Stile per il box di input della chat in basso */
    [data-testid="stChatInput"] {
        max-width: 900px;
        margin: auto;
        padding-bottom: 120px; /* Solleva il box di input sopra i loghi */
    }
    
    /* Nasconde l'header standard di Streamlit e il menu hamburger per pulizia */
    header[data-testid="stHeader"] {
        visibility: hidden;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    </style>
    ''' % bin_str
    st.markdown(page_bg_img, unsafe_allow_html=True)

# Richiama la funzione con il nome del tuo file immagine
# Assicurati che il file 'sfondo_eft.png' sia caricato su GitHub!
try:
    set_png_as_page_bg('sfondo_eft.png')
except FileNotFoundError:
    st.warning("⚠️ Immagine di sfondo 'sfondo_eft.png' non trovata. Caricala su GitHub per vederla.")

# --- FINE BLOCCO CSS ---

# Gestione Password
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔒 Accesso Riservato")
    pwd = st.text_input("Inserisci il codice:", type="password")
    if st.button("Accedi"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Codice errato")
    st.stop()

# Configurazione AI (Usiamo il modello che abbiamo trovato nella lista!)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Usiamo il nome esatto trovato nella tua lista
    model = genai.GenerativeModel('models/gemini-flash-latest')
except Exception as e:
    st.error(f"Errore configurazione: {e}")

# Caricamento Dati
@st.cache_data
def load_data():
    # Assicurati che il nome del file CSV su GitHub sia identico a questo:
    return pd.read_csv("Catalogo_Corsi_EFT_2026.csv")

try:
    df = load_data()
except Exception as e:
    st.error(f"Errore nel caricamento del file CSV: {e}")
    st.stop()

st.title("🎓 Orientatore EFT 2026")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Chiedimi dei corsi..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Preparazione contesto
    catalogo_testo = df[['ID Percorso', 'Titolo', 'Livello', 'Descrizione']].to_string(index=False)
    full_prompt = f"Sei un esperto orientatore per docenti. Usa SOLO questo catalogo per rispondere: {catalogo_testo}\n\nDomanda utente: {prompt}"
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(full_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Errore generazione: {e}")
