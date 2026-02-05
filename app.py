import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Diagnostica Didacta", page_icon="🔧")
st.title("🔧 Strumento di Diagnostica")

# Recupera la chiave
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("❌ Chiave API non trovata nei Secrets!")
    st.stop()

try:
    genai.configure(api_key=api_key)
    st.info("Tentativo di connessione a Google...")
    
    # Chiediamo la lista dei modelli disponibili per QUESTA chiave
    models = list(genai.list_models())
    
    found_models = []
    for m in models:
        # Cerchiamo solo i modelli che sanno generare testo
        if 'generateContent' in m.supported_generation_methods:
            found_models.append(m.name)

    if found_models:
        st.success("✅ Connessione Riuscita! Ecco i nomi esatti dei modelli disponibili per te:")
        # Mostriamo la lista a schermo
        for model_name in found_models:
            st.code(model_name)
        st.write("---")
        st.write("Copia uno di questi nomi (es. `models/gemini-pro`) e inviamelo qui in chat.")
    else:
        st.warning("⚠️ La chiave funziona, ma Google dice che non ci sono modelli disponibili. Il progetto potrebbe essere vuoto o limitato.")

except Exception as e:
    st.error(f"❌ Errore critico di connessione: {e}")
