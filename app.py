import streamlit as st
import google.generativeai as genai
import pandas as pd
import base64
import qrcode
import re
import os
from io import BytesIO

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

# --- 2. FUNZIONE SFONDO OTTIMIZZATO ---
def set_bg_hack(png_file):
    if os.path.exists(png_file):
        with open(png_file, "rb") as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/png;base64,{bin_str}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            /* Effetto "Vetro" per rendere leggibile il testo sopra lo sfondo */
            .stMain .block-container {{
                background-color: rgba(255, 255, 255, 0.90);
                padding: 3rem;
                border-radius: 20px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                margin-top: 2rem;
            }}
            /* Nasconde header e footer standard di Streamlit */
            header {{visibility: hidden;}}
            footer {{visibility: hidden;}}
            </style>
            """,
            unsafe_allow_html=True
        )

# Carica lo sfondo se presente
set_bg_hack('sfondo_eft.png')

# --- 3. LOGIN / PASSWORD ---
# Se non c'è la password nei secrets, usa una di default per evitare blocchi
PASSWORD_SEGRETA = st.secrets.get("APP_PASSWORD", "didacta2026")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Area Riservata EFT")
    pwd = st.text_input("Inserisci la password per accedere", type="password")
    if st.button("Accedi"):
        if pwd == PASSWORD_SEGRETA:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Password errata. Riprova.")
    st.stop() # Ferma l'esecuzione qui se non loggato

# --- 4. CARICAMENTO DATI ---
@st.cache_data
def load_data():
    file_path = "Catalogo_Corsi_EFT_2026.csv"
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        # Carica il CSV forzando tutto a testo per evitare errori
        df = pd.read_csv(file_path, dtype=str).fillna("")
        return df.apply(lambda x: x.str.strip())
    except Exception as e:
        st.error(f"Errore nella lettura del file: {e}")
        return pd.DataFrame()

df = load_data()

# --- 5. INTERFACCIA UTENTE ---
st.title("🎓 Consulente Formativo EFT")
st.markdown("Compila i campi per trovare il percorso su **Scuola Futura** più adatto.")

# Verifica silenziosa: se il DF è vuoto, avvisa
if df.empty:
    st.error("⚠️ Attenzione: Il catalogo corsi non è stato caricato correttamente o è vuoto.")
    st.stop()

# Filtri
col1, col2 = st.columns(2)

with col1:
    # Ordine scuola (Non presente nel CSV, ma usato per il prompt IA)
    ordine = st.selectbox(
        "Ordine di Scuola",
        ["Tutti", "Infanzia", "Primaria", "Secondaria I grado", "Secondaria II grado", "CPIA"]
    )

with col2:
    # Regione (Presente nel CSV)
    regioni_disponibili = ["Tutte"] + sorted(df['Regione'].unique().tolist())
    regione = st.selectbox("Regione", regioni_disponibili)

# Area Tematica (Presente nel CSV)
temi_disponibili = ["Tutte"] + sorted(df['Tematica'].unique().tolist())
tema = st.selectbox("Area Tematica Preferita", temi_disponibili)

# Campo libero
query_libera = st.text_input("Interessi specifici (es: podcast, inclusione, AI, robotica)")

# --- 6. LOGICA IA E GENERAZIONE ---
if st.button("🔎 Cerca Corsi", use_container_width=True):
    
    with st.spinner("L'intelligenza artificiale sta analizzando il catalogo..."):
        # Configurazione API Key
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        else:
            st.error("Manca la GEMINI_API_KEY nei secrets.")
            st.stop()

        # Modello specificato dall'utente
        model = genai.GenerativeModel('gemini-flash-latest')

        # Preparazione contesto dati
        # Convertiamo il DF in CSV stringa per passarlo al prompt
        dati_csv = df.to_csv(index=False)

        prompt = f"""
        Sei un esperto orientatore per la formazione docenti.
        Analizza il seguente catalogo corsi (CSV):
        {dati_csv}

        LA TUA MISSIONE:
        Trova i 3 corsi migliori per un docente con queste caratteristiche:
        - Ordine Scuola: {ordine} (Cerca indizi nel Titolo o Abstract se il corso è adatto)
        - Regione: {regione} (Se 'Tutte', ignora la regione. Se la regione scelta non ha corsi, cerca corsi 'Nazionale' o 'Tutte le regioni')
        - Area Tematica: {tema}
        - Richiesta specifica: {query_libera}

        REGOLE FONDAMENTALI:
        1. Usa SOLO i corsi presenti nel CSV fornito.
        2. Non inventare link. Copia esattamente il link dalla colonna 'Link'.
        3. Se non trovi nulla di perfetto, proponi l'alternativa più vicina (es. corsi Nazionali).

        FORMATO RISPOSTA (Usa Markdown):
        Per ogni corso trovato (massimo 3):
        ### [Titolo del Corso]
        **ID:** [ID Corso]
        **Perché è adatto:** Spiega in una frase basandoti sull'Abstract e sul target {ordine}.
        **Competenze DigCompEdu:** [Cita la colonna Competenze]
        🔗 [VAI AL CORSO]([Link])
        
        ---
        """

        try:
            response = model.generate_content(prompt)
            st.session_state.risposta_ia = response.text
        except Exception as e:
            st.error(f"Errore di connessione con Gemini: {e}")

# --- 7. VISUALIZZAZIONE RISULTATI E QR CODE ---
if "risposta_ia" in st.session_state:
    st.markdown("---")
    st.markdown(st.session_state.risposta_ia)

    # Estrazione dei link per il QR Code
    # Cerca stringhe che iniziano con http e finiscono prima di uno spazio o parentesi
    links_trovati = re.findall(r'(https?://scuolafutura[^\s\)]+)', st.session_state.risposta_ia)
    
    # Rimuove eventuali duplicati mantenendo l'ordine
    links_unici = list(dict.fromkeys(links_trovati))

    if links_unici:
        st.markdown("---")
        st.subheader("📱 Scansiona per iscriverti")
        st.write("Inquadra il QR Code per aprire direttamente i link ai corsi trovati.")
        
        # Crea il contenuto del QR: solo i link separati da "a capo"
        qr_content = "\n".join(links_unici)
        
        # Generazione QR Code
        qr_img = qrcode.make(qr_content)
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        
        # Mostra l'immagine
        st.image(buf.getvalue(), width=250)
    else:
        st.warning("Nessun link diretto trovato nella risposta.")
