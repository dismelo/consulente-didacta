import streamlit as st
import google.generativeai as genai
import pandas as pd
import qrcode
import re
import os
from io import BytesIO

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

# --- 2. CARICAMENTO E PULIZIA DATI ---
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "Catalogo_Corsi_EFT_2026.csv")

@st.cache_data
def load_data():
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    try:
        # Legge il file con separatore ; del file FINALE
        df = pd.read_csv(csv_path, sep=';', dtype=str, on_bad_lines='skip')
        # Pulizia: toglie spazi vuoti e ritorni a capo da ogni cella
        for col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[\r\n\t]+', ' ', regex=True).str.strip().fillna("")
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
        user_pwd = st.text_input("Password di sblocco", type="password", key="pwd_unique_key_2026")
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
    st.warning("⚠️ Carica il file Catalogo_Corsi_EFT_2026.csv su GitHub.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    set_ordini = set()
    for val in df['Ordine_scuola'].unique():
        for s in str(val).split(','):
            if s.strip(): set_ordini.add(s.strip())
    ordine = st.selectbox("Ordine Scuola", ["Tutti"] + sorted(list(set_ordini)))

with col2:
    regione = st.selectbox("Regione", ["Tutte"] + sorted(df['Regione'].unique().tolist()))

tema = st.selectbox("Area Tematica", ["Tutte"] + sorted(df['Tematica'].unique().tolist()))
# La domanda fondamentale dell'utente
query_utente = st.text_input("Di cosa vorresti occuparti? (es: AI, inclusione, STEAM, coding)")

# --- 5. RICERCA SEMANTICA + ANALISI IA ---
if st.button("🔎 Trova il mio percorso formativo", use_container_width=True):
    
    # A. Filtro rigoroso (Regione/Scuola)
    mask = pd.Series([True] * len(df))
    if ordine != "Tutti":
        mask &= df['Ordine_scuola'].str.contains(ordine, case=False, regex=False)
    if regione != "Tutte":
        mask &= df['Regione'] == regione
    if tema != "Tutte":
        mask &= df['Tematica'] == tema
    
    df_filtrato = df[mask].copy()

    # B. Motore di Punteggio (Risolve il tuo dubbio)
    if query_utente.strip() != "":
        parole = query_utente.lower().split()
        def calcola_rilevanza(row):
            punti = 0
            testo = (row['Titolo_corso'] + " " + row['Abstract']).lower()
            for p in parole:
                if p in row['Titolo_corso'].lower(): punti += 10 # Il titolo pesa molto
                if p in row['Abstract'].lower(): punti += 3      # L'abstract pesa medio
            return punti

        df_filtrato['score'] = df_filtrato.apply(calcola_rilevanza, axis=1)
        # Prendiamo i migliori 10 basati sulla ricerca dell'utente
        df_per_ia = df_filtrato.sort_values(by='score', ascending=False).head(10)
    else:
        df_per_ia = df_filtrato.head(10)

    # C. Analisi con Gemini
    if df_per_ia.empty or (query_utente != "" and df_per_ia['score'].max() == 0):
        st.error("Nessun corso trovato. Prova a usare parole meno specifiche.")
    else:
        with st.spinner("L'intelligenza artificiale sta analizzando i corsi più pertinenti..."):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-flash-latest')
                
                contesto_csv = df_per_ia[['Titolo_corso', 'Link_scheda', 'Abstract']].to_csv(index=False)
                
                prompt = f"""
                L'utente desidera: "{query_utente}".
                Analizza questi corsi (ordinati per rilevanza):
                {contesto_csv}
                
                1. Presenta i 3 corsi migliori spiegando BREVEMENTE perché sono adatti alla sua richiesta.
                2. Sii cordiale e professionale.
                3. Alla fine del messaggio scrivi solo 'LINK_LIST:' e sotto elenca i link esatti dei 3 corsi, uno per riga.
                """
                
                res = model.generate_content(prompt)
                st.session_state.risposta_ia = res.text
            except Exception as e:
                st.error(f"Errore tecnico: {e}")

# --- 6. DISPLAY RISULTATI E QR CODE INDIVIDUALI ---
if "risposta_ia" in st.session_state:
    st.markdown("---")
    parti = st.session_state.risposta_ia.split("LINK_LIST:")
    st.markdown(parti[0]) # Mostra la spiegazione
    
    if len(parti) > 1:
        # Estrae i link in modo pulito
        links_trovati = re.findall(r'(https?://scuolafutura[^\s\)\>\]]+)', parti[1])
        
        if links_trovati:
            st.subheader("📱 Inquadra il QR Code per iscriverti")
            cols = st.columns(len(links_trovati))
            
            for i, link in enumerate(links_trovati[:3]):
                with cols[i]:
                    link_pulito = link.strip(".,;!")
                    st.markdown(f"**[Vai al Corso {i+1} 🔗]({link_pulito})**")
                    
                    qr = qrcode.QRCode(box_size=5, border=1)
                    qr.add_data(link_pulito)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    st.image(buf.getvalue(), use_container_width=True)

    if st.button("🗑️ Effettua una nuova ricerca"):
        del st.session_state.risposta_ia
        st.rerun()
