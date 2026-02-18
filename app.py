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
        df = pd.read_csv(csv_path, sep=';', dtype=str, on_bad_lines='skip')
        # Pulizia standard colonne
        cols_to_fix = ['Ordine_scuola', 'Regione', 'Tematica', 'Titolo_corso', 'Abstract', 'Link_scheda']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'[\r\n\t]+', ' ', regex=True).str.strip().fillna("")
        return df
    except Exception as e:
        return pd.DataFrame()

df = load_data()

# --- 3. PASSWORD ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Accesso Riservato")
    with st.form("login"):
        user_pwd = st.text_input("Password", type="password", key="pwd_search_fix")
        if st.form_submit_button("Sblocca"):
            if user_pwd == st.secrets.get("APP_PASSWORD", "didacta2026"):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Password errata.")
    st.stop()

# --- 4. INTERFACCIA E FILTRI ---
st.title("🎓 Consulente Formativo EFT")

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
query_utente = st.text_input("Di cosa vorresti occuparti? (es: storytelling, coding, inclusione)")

# --- 5. MOTORE DI RICERCA TESTUALE + IA ---
if st.button("🔎 Trova i corsi migliori", use_container_width=True):
    
    # A. Filtro geografico/scolastico (Base)
    mask = pd.Series([True] * len(df))
    if ordine != "Tutti":
        mask &= df['Ordine_scuola'].str.contains(ordine, case=False, regex=False)
    if regione != "Tutte":
        mask &= df['Regione'] == regione
    if tema != "Tutte":
        mask &= df['Tematica'] == tema
    
    df_filtrato = df[mask].copy()

    # B. Ricerca Rilevanza (Il "cuore" della tua richiesta)
    if query_utente.strip() != "":
        # Creiamo un punteggio: +2 se la parola è nel titolo, +1 se è nell'abstract
        parole_chiave = query_utente.lower().split()
        
        def calcola_punteggio(row):
            punti = 0
            testo_completo = (row['Titolo_corso'] + " " + row['Abstract']).lower()
            for parola in parole_chiave:
                if parola in row['Titolo_corso'].lower(): punti += 5 # Molto importante nel titolo
                if parola in row['Abstract'].lower(): punti += 2     # Importante nell'abstract
            return punti

        df_filtrato['score'] = df_filtrato.apply(calcola_punteggio, axis=1)
        # Ordiniamo per punteggio e prendiamo i migliori 10
        df_per_ia = df_filtrato.sort_values(by='score', ascending=False).head(10)
    else:
        df_per_ia = df_filtrato.head(10)

    # C. Analisi con Gemini
    if df_per_ia.empty or (query_utente != "" and df_per_ia['score'].max() == 0):
        st.error("Non ho trovato corsi che corrispondano specificamente alla tua ricerca. Prova a usare parole diverse.")
    else:
        with st.spinner("Sto selezionando i corsi più pertinenti dal catalogo..."):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-flash-latest')
                
                contesto = df_per_ia[['Titolo_corso', 'Link_scheda', 'Abstract']].to_csv(index=False)
                
                prompt = f"""
                L'utente cerca corsi su: "{query_utente}".
                Analizza questi dati (già filtrati per pertinenza):
                {contesto}
                
                Scegli i 3 migliori in assoluto per soddisfare la richiesta dell'utente.
                REGOLE:
                1. Spiega in 2 righe perché il corso è perfetto per la sua richiesta.
                2. Alla fine scrivi 'TAG_SEGRETO_LINK:' e sotto i link esatti, uno per riga.
                """
                
                res = model.generate_content(prompt)
                st.session_state.risposta_ia = res.text
            except Exception as e:
                st.error(f"Errore: {e}")

# --- 6. RISULTATI E QR CODE (MULTI-QR FIX) ---
if "risposta_ia" in st.session_state:
    st.markdown("---")
    parti = st.session_state.risposta_ia.split("TAG_SEGRETO_LINK:")
    st.markdown(parti[0])
    
    if len(parti) > 1:
        links = re.findall(r'(https?://scuolafutura[^\s\)\>\]\'\"]+)', parti[1])
        if links:
            st.subheader("📱 Schede dei Corsi")
            cols = st.columns(len(links))
            for i, l in enumerate(links[:3]): # Max 3 QR
                with cols[i]:
                    clean_l = l.strip(".,;!*")
                    st.markdown(f"**[Corso {i+1}]({clean_l})**")
                    qr = qrcode.make(clean_l)
                    buf = BytesIO()
                    qr.save(buf, format="PNG")
                    st.image(buf.getvalue(), use_container_width=True)

    if st.button("Nuova Ricerca"):
        del st.session_state.risposta_ia
        st.rerun()
