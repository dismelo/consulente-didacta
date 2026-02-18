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
        # Lettura file FINALE (separatore ;)
        df = pd.read_csv(csv_path, sep=';', dtype=str, on_bad_lines='skip').fillna("")
        
        # Pulizia profonda di tutte le celle
        for col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[\r\n\t]+', ' ', regex=True).str.strip()
        
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
        user_pwd = st.text_input("Password", type="password", key="pwd_final_v3")
        if st.form_submit_button("Sblocca"):
            if user_pwd == st.secrets.get("APP_PASSWORD", "didacta2026"):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Password errata.")
    st.stop()

# --- 4. INTERFACCIA E FILTRI ---
st.title("🎓 Consulente Formativo EFT")

# Definizione ordini di scuola richiesti
opzioni_scuola = [
    "Tutti", 
    "Scuola dell'infanzia", 
    "Scuola primaria", 
    "Scuola secondaria I grado", 
    "Scuola secondaria II grado", 
    "CPIA"
]

col1, col2 = st.columns(2)
with col1:
    ordine = st.selectbox("Ordine Scuola", opzioni_scuola)

with col2:
    # Pulizia: Rimuove "nan" o valori vuoti dal menu Regioni
    lista_regioni = sorted([r for r in df['Regione'].unique() if r and r.lower() != 'nan'])
    regione = st.selectbox("Regione", ["Tutte"] + lista_regioni)

# Pulizia: Rimuove "nan" o valori vuoti dal menu Tematiche
lista_temi = sorted([t for t in df['Tematica'].unique() if t and t.lower() != 'nan'])
tema = st.selectbox("Area Tematica", ["Tutte"] + lista_temi)

query_utente = st.text_input("Di cosa vorresti occuparti? (es: AI, STEM, inclusione, arte)")

# --- 5. RICERCA E PUNTEGGIO EQUILIBRATO ---
if st.button("🔎 Cerca i corsi ideali", use_container_width=True):
    
    # Filtro Base (Geografico e Scolastico)
    mask = pd.Series([True] * len(df))
    
    if ordine != "Tutti":
        # Cerca se la parola chiave (es. "primaria") è contenuta nella cella Ordine_scuola
        mask &= df['Ordine_scuola'].str.contains(ordine, case=False, regex=False)
    
    if regione != "Tutte":
        mask &= df['Regione'] == regione
        
    if tema != "Tutte":
        mask &= df['Tematica'] == tema
    
    df_filtrato = df[mask].copy()

    # MOTORE DI PUNTEGGIO (Titolo e Abstract valgono allo stesso modo)
    if query_utente.strip() != "" and not df_filtrato.empty:
        parole = query_utente.lower().split()
        def calcola_rilevanza(row):
            punti = 0
            # Uniamo titolo e abstract per dare lo stesso peso a entrambi
            testo_unito = (row['Titolo_corso'] + " " + row['Abstract']).lower()
            for p in parole:
                if p in testo_unito:
                    # Conta quante volte le parole della ricerca appaiono nel blocco testo
                    punti += testo_unito.count(p)
            return punti

        df_filtrato['score'] = df_filtrato.apply(calcola_rilevanza, axis=1)
        df_per_ia = df_filtrato.sort_values(by='score', ascending=False).head(10)
    else:
        df_per_ia = df_filtrato.head(10)

    # --- 6. ANALISI GEMINI ---
    if df_per_ia.empty:
        st.warning("Nessun corso trovato per i criteri selezionati. Prova a cambiare regione o ordine di scuola.")
    else:
        with st.spinner("L'IA sta selezionando le migliori proposte per te..."):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-flash-latest')
                
                contesto = df_per_ia[['Titolo_corso', 'Link_scheda', 'Abstract']].to_csv(index=False)
                
                prompt = f"""
                Richiesta utente: "{query_utente}"
                Target: {ordine}
                Dati corsi disponibili:
                {contesto}
                
                Compito:
                1. Scegli i 3 corsi più pertinenti.
                2. Spiega brevemente perché sono adatti alla richiesta.
                3. Concludi con la stringa 'LINK_LIST:' e sotto elenca solo i link dei 3 corsi, uno per riga.
                """
                
                res = model.generate_content(prompt)
                st.session_state.risposta_ia = res.text
            except Exception as e:
                st.error(f"Errore nella generazione: {e}")

# --- 7. RISULTATI E QR CODE ---
if "risposta_ia" in st.session_state:
    st.markdown("---")
    parti = st.session_state.risposta_ia.split("LINK_LIST:")
    st.markdown(parti[0])
    
    if len(parti) > 1:
        links = re.findall(r'(https?://scuolafutura[^\s\)\>\]]+)', parti[1])
        if links:
            st.subheader("📱 Schede Corso (QR Code)")
            cols = st.columns(len(links[:3]))
            for i, l in enumerate(links[:3]):
                with cols[i]:
                    l_pulito = l.strip(".,;!")
                    st.markdown(f"**[Link Corso {i+1}]({l_pulito})**")
                    qr = qrcode.make(l_pulito)
                    buf = BytesIO()
                    qr.save(buf, format="PNG")
                    st.image(buf.getvalue(), use_container_width=True)

    if st.button("🔄 Nuova Ricerca"):
        del st.session_state.risposta_ia
        st.rerun()
