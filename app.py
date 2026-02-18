import streamlit as st
import google.generativeai as genai
import pandas as pd
import qrcode
import re
import os
from io import BytesIO

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

# --- 2. CARICAMENTO E PULIZIA PROFONDA DATI ---
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "Catalogo_Corsi_EFT_2026.csv")

@st.cache_data
def load_data():
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(csv_path, sep=';', dtype=str).fillna("")
        # PULIZIA: Rimuove spazi vuoti e ritorni a capo da tutte le colonne
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        return pd.DataFrame()

df = load_data()

# --- 3. PASSWORD (FIX AUTOCOMPLETAMENTO) ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Accesso Riservato")
    with st.form("login"):
        # Cambiato il parametro 'key' per forzare il browser a dimenticare la cronologia
        user_pwd = st.text_input("Inserisci la Password di sblocco", type="password", key="pwd_segreta_26")
        if st.form_submit_button("Sblocca"):
            if user_pwd == st.secrets.get("APP_PASSWORD", "didacta2026"):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Password errata.")
    st.stop()

# --- 4. INTERFACCIA E FILTRI ---
st.title("🎓 Consulente Formativo EFT")

if df.empty:
    st.warning("⚠️ Database non trovato o vuoto.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
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
    
    # FILTRO ELASTICO (Risolve il problema Campania e spazi vuoti)
    mask = pd.Series([True] * len(df))
    if ordine != "Tutti":
        mask &= df['Ordine_scuola'].str.contains(ordine, case=False, regex=False)
    if regione != "Tutte":
        mask &= df['Regione'].str.contains(regione, case=False, regex=False)
    if tema != "Tutte":
        mask &= df['Tematica'].str.contains(tema, case=False, regex=False)
    
    df_preview = df[mask].head(15)
    
    if df_preview.empty:
        st.error("Nessun corso trovato con questi filtri. Prova a cercarne altri!")
    else:
        with st.spinner(f"Analizzando {len(df_preview)} corsi trovati..."):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-flash-latest')
                
                prompt = f"""
                Analizza questi corsi e seleziona i 3 migliori per: {query}.
                DATI: {df_preview[['Titolo_corso', 'Link_scheda', 'Abstract']].to_csv(index=False)}
                
                REGOLE:
                1. Scrivi un report descrivendo brevemente perché hai scelto ciascun corso.
                2. Alla fine, vai a capo e scrivi ESATTAMENTE questa stringa: 'TAG_SEGRETO_LINK:'
                3. Sotto la stringa, elenca i link esatti dei 3 corsi scelti, uno per riga, senza aggiungere altro testo, punti o virgole.
                """
                
                res = model.generate_content(prompt)
                st.session_state.risposta_ia = res.text
            except Exception as e:
                st.error(f"Errore IA: {e}")

# --- 6. RISULTATI: DISPLAY E MULTI-QR CODE ---
if "risposta_ia" in st.session_state:
    st.markdown("---")
    
    # Separiamo il testo descrittivo dalla zona dei link (così l'utente non vede i link spiattellati)
    parti_risposta = st.session_state.risposta_ia.split("TAG_SEGRETO_LINK:")
    testo_descrittivo = parti_risposta[0]
    st.markdown(testo_descrittivo)
    
    # Se la IA ha generato correttamente la seconda parte (i link)
    if len(parti_risposta) > 1:
        testo_link = parti_risposta[1]
        
        # Estrazione pulita
        raw_links = re.findall(r'(https?://scuolafutura[^\s\)\>\]\'\"]+)', testo_link)
        clean_links = []
        for l in raw_links:
            pulito = l.strip(".,;!*()[]{}'\"")
            if pulito not in clean_links:
                clean_links.append(pulito)

        # Generazione di UN QR CODE PER OGNI CORSO
        if clean_links:
            st.subheader("📱 Accedi alle schede dei corsi")
            
            # Creiamo tante colonne quanti sono i link trovati (massimo 3)
            colonne_qr = st.columns(len(clean_links))
            
            for i, link in enumerate(clean_links):
                with colonne_qr[i]:
                    # Mostra un link cliccabile pulito
                    st.markdown(f"**[🔗 Apri Corso {i+1}]({link})**")
                    
                    # Genera e mostra il QR Code singolo
                    qr = qrcode.QRCode(box_size=6, border=2)
                    qr.add_data(link)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    st.image(buf.getvalue(), use_container_width=True)

    if st.button("🗑️ Nuova Ricerca"):
        del st.session_state.risposta_ia
        st.rerun()
