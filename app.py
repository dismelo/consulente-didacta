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
# Proviamo a usare il nome modello più standard
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Cambiato da 'gemini-1.5-flash' a 'models/gemini-1.5-flash' 
    # o 'gemini-pro' che è molto stabile
   model = genai.GenerativeModel('gemini-pro') 
except Exception as e:
    st.error(f"Errore configurazione: {e}")

# --- DATI ---
@st.cache_data
def load_data():
    return pd.read_csv("Catalogo_Corsi_EFT_2026.csv")

df = load_data()

# --- CHAT ---
st.title("🎓 Orientatore EFT 2026")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Come posso aiutarti?"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Preparazione contesto
    catalogo_testo = df[['ID Percorso', 'Titolo', 'Livello', 'Descrizione']].to_string(index=False)
    
    full_prompt = f"Sei un orientatore. Catalogo: {catalogo_testo}\n\nUtente: {prompt}"

    with st.chat_message("assistant"):
        try:
            # Chiamata semplificata senza 'chat_session' per massima compatibilità
            response = model.generate_content(full_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Errore nella risposta: {e}")
            st.info("Controlla che la API Key nei Secrets sia corretta e attiva.")
            
