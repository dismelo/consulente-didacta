import streamlit as st
import pandas as pd
import google.generativeai as genai

# Configurazione Pagina
st.set_page_config(page_title="Orientatore EFT 2026", page_icon="🎓")

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

# Configurazione AI (Usiamo gemini-pro per evitare l'errore 404)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.error(f"Errore API: {e}")

# Caricamento Dati
@st.cache_data
def load_data():
    return pd.read_csv("Catalogo_Corsi_EFT_2026.csv")

df = load_data()
st.title("🎓 Orientatore EFT 2026")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Chiedimi dei corsi..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Prepariamo il catalogo per l'IA
    catalogo_testo = df[['ID Percorso', 'Titolo', 'Livello', 'Descrizione']].to_string(index=False)
    full_prompt = f"Sei un orientatore. Catalogo: {catalogo_testo}\n\nDomanda: {prompt}"
    
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(full_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Errore di connessione: {e}")
