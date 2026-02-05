import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Consulente Scuola Futura", page_icon="🎓", layout="centered")

# --- GESTIONE PASSWORD ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    st.title("🔒 Accesso Riservato Didacta")
    st.write("Inserisci il codice per consultare il catalogo EFT 2026")
    pwd_input = st.text_input("Codice di accesso", type="password")
    if st.button("Entra"):
        if pwd_input == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Codice non valido")
    return False

if not check_password():
    st.stop()

# --- CONFIGURAZIONE AI ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- CARICAMENTO DATI ---
@st.cache_data
def load_data():
    # Carichiamo il tuo file specifico
    df = pd.read_csv("Catalogo_Corsi_EFT_2026.csv")
    return df

df = load_data()

# --- INTERFACCIA ---
st.image("https://scuolafutura.pubblica.istruzione.it/os-scuolafutura-theme/images/logo-scuola-futura.png", width=200) # Logo di esempio
st.title("Orientatore Formazione EFT")
st.markdown("Scansiono il catalogo **Scuola Futura 2026** per trovare i percorsi più adatti a te.")

if st.button("🔄 Nuova ricerca"):
    st.session_state.messages = []
    st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- LOGICA CHAT ---
if prompt := st.chat_input("Es: Sono un docente di primaria, cerco corsi sull'AI livello base..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Preparazione contesto dai dati del CSV
    # Prendiamo le info principali per non appesantire il prompt
    catalogo_testo = df[['ID Percorso', 'Titolo', 'Livello', 'Area DigCompEdu', 'Descrizione']].to_string(index=False)

    system_message = f"""
    Sei l'orientatore esperto di Scuola Futura presente allo stand Didacta. 
    Il tuo compito è aiutare i docenti a orientarsi nel catalogo EFT 2026.

    REGOLE D'ORO:
    1. Se l'utente non specifica il suo LIVELLO (A1, A2, B1, B2, C1, C2), chiedilo sempre prima di proporre corsi.
    2. Proponi ESATTAMENTE i 3 corsi più pertinenti presenti nel catalogo sotto.
    3. Per ogni corso indica: Titolo, ID Percorso (fondamentale per trovarlo su Scuola Futura), Livello e una breve motivazione del perché lo consigli.
    4. Sii professionale, accogliente e sintetico.

    CATALOGO DATI:
    {catalogo_testo}
    """

    with st.chat_message("assistant"):
        with st.spinner("Consulto il catalogo..."):
            model = genai.GenerativeModel('gemini-1.5-flash')
            # Inviamo tutta la storia della conversazione per mantenere il contesto
            chat = model.start_chat(history=[])
            response = chat.send_message(system_message + "\n\nDOMANDA UTENTE: " + prompt)
            
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
