import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Consulente Scuola Futura", page_icon="🎓")

# --- SICUREZZA ---
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

# --- CONFIGURAZIONE AI ---
try:
    # Questa riga forza la compatibilità corretta
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Proviamo gemini-1.5-flash ma con un approccio più semplice
    model = genai.GenerativeModel('gemini-1.5-flash') 
except Exception as e:
    st.error(f"Errore configurazione API: {e}")

# --- CARICAMENTO DATI ---
@st.cache_data
def load_data():
    return pd.read_csv("Catalogo_Corsi_EFT_2026.csv")

df = load_data()

# --- INTERFACCIA CHAT ---
st.title("🎓 Orientatore EFT 2026")
st.write("Ciao! Chiedimi pure consiglio sui corsi del catalogo.")

if st.button("🔄 Nuova Sessione"):
    st.session_state.messages = []
    st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Scrivi qui la tua domanda..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Preparazione contesto (solo le prime 50 righe per sicurezza di spazio)
    catalogo_testo = df[['ID Percorso', 'Titolo', 'Livello', 'Descrizione']].head(50).to_string(index=False)
    
    full_prompt = f"Sei un orientatore. Catalogo: {catalogo_testo}\n\nDomanda utente: {prompt}"

    with st.chat_message("assistant"):
        try:
            # Chiamata diretta (più stabile per le API Key gratuite)
            response = model.generate_content(full_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error("Ops! C'è un piccolo problema di connessione con Google AI.")
            st.info(f"Dettaglio tecnico: {e}")
