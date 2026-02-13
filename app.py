import streamlit as st
import google.generativeai as genai
import pandas as pd
import qrcode
import re
import os
from io import BytesIO

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

# --- 2. CARICAMENTO DATI (FILE B) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "Catalogo_Corsi_EFT_2026.csv")

@st.cache_data
def load_data():
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    try:
        # File B usa il punto e virgola come separatore
        df = pd.read_csv(csv_path, sep=';', dtype=str).fillna("")
        return df.apply(lambda x: x.str.strip())
    except Exception as e:
        return pd.DataFrame()

df = load_data()

# --- 3. PASSWORD ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Accesso Riservato")
    with st.form("login"):
        user_pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Sblocca"):
            if user_pwd == st.secrets.get("APP_PASSWORD", "didacta2026"):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Password errata.")
    st.stop()

# --- 4. INTERFACCIA ---
st.title("🎓 Consulente Formativo EFT")

if df.empty:
    st.warning("⚠️ Database non trovato. Carica il file B rinominato su GitHub.")
    st.stop()

# Filtri basati sulle colonne del File B
col1, col2 = st.columns(2)
with col1:
    # Gestione ordini multipli (es. "Infanzia, Primaria")
    set_ordini = set()
    for val in df['Ordine_scuola'].unique():
        for s in val.split(','):
            set_ordini.add(s.strip())
    ordine = st.selectbox("Ordine Scuola", ["Tutti"] + sorted(list(set_ordini)))

with col2:
    regione = st.selectbox("Regione", ["Tutte"] + sorted(df['Regione'].unique().tolist()))

tema = st.selectbox("Area Tematica", ["Tutte"] + sorted(df['Tematica'].unique().tolist()))
query = st.text_input("Di cosa vorresti occuparti?")

# --- 5. RICERCA E PROMPT ---
if st.button("🔎 Cerca Corsi", use_container_width=True):
    # Filtro rapido per passare all'IA solo i dati pertinenti
    mask = pd.Series([True] * len(df))
    if ordine != "Tutti":
        mask &= df['Ordine_scuola'].str.contains(ordine, case=False)
    if regione != "Tutte":
        mask &= df['Regione'] == regione
    if tema != "Tutte":
        mask &= df['Tematica'] == tema
    
    df_preview = df[mask].head(10)
    
    if df_preview.empty:
        st.error("Nessun corso trovato. Prova a cambiare filtri.")
    else:
        with st.spinner("L'IA sta preparando il tuo percorso..."):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-flash-latest')
                
                # Prompt ultra-stretto per evitare errori nei link
                prompt = f"""
                Analizza questi corsi e seleziona i 3 migliori per: {query}.
                DATI: {df_preview[['Titolo_corso', 'Link_scheda', 'Abstract']].to_csv(index=False)}
                
                REGOLE:
                1. Descrivi brevemente perché hai scelto il corso.
                2. Alla fine scrivi 'LINK_PER_QR:' e sotto elenca i link esatti senza aggiungere punti o testo dopo il link.
                3. NON abbreviare mai i link con '...'.
                """
                
                res = model.generate_content(prompt)
                st.session_state.risposta_ia = res.text
            except Exception as e:
                st.error(f"Errore IA: {e}")

# --- 6. RISULTATI E PULIZIA QR CODE ---
if "risposta_ia" in st.session_state:
    st.markdown("---")
    st.markdown(st.session_state.risposta_ia)
    
    # ESTRAZIONE E PULIZIA MANUALE DEI LINK
    # Cerchiamo tutto ciò che inizia con http e finisce prima di uno spazio o invio
    raw_links = re.findall(r'https?://scuolafutura[^\s]+', st.session_state.risposta_ia)
    
    clean_links = []
    for link in raw_links:
        # Rimuove punteggiatura finale che l'IA potrebbe aver aggiunto (punti, virgole, parentesi)
        l = link.strip().rstrip('.,;)]!#')
        if l not in clean_links:
            clean_links.append(l)

    if clean_links:
        st.subheader("📱 Link pronti per il tuo smartphone")
        qr_text = "\n".join(clean_links)
        
        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(qr_text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buf = BytesIO()
        img.save(buf, format="PNG")
        
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.image(buf.getvalue(), width=250)
        with c2:
            st.info("Scansiona per aprire i corsi. Se vedi una pagina vuota, assicurati che il telefono abbia preso il link completo.")

    if st.button("🗑️ Reset"):
        del st.session_state.risposta_ia
        st.rerun()
