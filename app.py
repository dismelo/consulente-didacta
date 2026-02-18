import streamlit as st
import google.generativeai as genai
import pandas as pd
import qrcode
import re
import os
from io import BytesIO

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="wide")

# --- 2. CARICAMENTO E PULIZIA "TANK-PROOF" ---
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "Catalogo_Corsi_EFT_2026.csv")

@st.cache_data
def load_data():
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    try:
        # Caricamento con gestione encoding per file Excel/CSV
        df = pd.read_csv(csv_path, sep=';', dtype=str, on_bad_lines='skip', encoding='utf-8-sig')
        
        # Sostituisce i valori nulli (NaN) con stringhe vuote PRIMA della pulizia
        df = df.fillna("")
        
        # PULIZIA ESTREMA: Rimuove spazi, tabulazioni e ritorni a capo da OGNI cella
        for col in df.columns:
            df[col] = df[col].astype(str).apply(lambda x: re.sub(r'\s+', ' ', x).strip())
        
        return df
    except Exception as e:
        st.error(f"Errore tecnico nel database: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. PASSWORD ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Accesso Riservato")
    with st.form("login"):
        user_pwd = st.text_input("Inserisci Password", type="password", key="pwd_v4_final")
        if st.form_submit_button("Sblocca"):
            if user_pwd == st.secrets.get("APP_PASSWORD", "didacta2026"):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Password errata.")
    st.stop()

# --- 4. INTERFACCIA E FILTRI ---
st.title("🎓 Consulente Formativo EFT 2026")

# Menu Ordine Scuola richiesto
opzioni_scuola = [
    "Tutti", 
    "Scuola dell'infanzia", 
    "Scuola primaria", 
    "Scuola secondaria I grado", 
    "Scuola secondaria II grado", 
    "CPIA"
]

col1, col2, col3 = st.columns(3)

with col1:
    ordine = st.selectbox("Ordine Scuola", opzioni_scuola)

with col2:
    # Genera lista regioni pulita (senza nan o vuoti)
    lista_regioni = sorted([r for r in df['Regione'].unique() if r and r.lower() != 'nan'])
    regione = st.selectbox("Regione", ["Tutte"] + lista_regioni)

with col3:
    # Genera lista tematiche pulita
    lista_temi = sorted([t for t in df['Tematica'].unique() if t and t.lower() != 'nan'])
    tema = st.selectbox("Area Tematica", ["Tutte"] + lista_temi)

query_utente = st.text_input("Di cosa vorresti occuparti? (Cerca per parole chiave come: AI, inclusione, STEAM, coding...)")

# --- 5. LOGICA DI FILTRAGGIO E RANKING ---
if st.button("🔎 Avvia Ricerca", use_container_width=True):
    
    # A. Filtraggio per Regione e Tema (Case-insensitive per sicurezza)
    mask = pd.Series([True] * len(df))
    
    if regione != "Tutte":
        mask &= df['Regione'].str.lower() == regione.lower()
        
    if tema != "Tutte":
        mask &= df['Tematica'].str.lower() == tema.lower()
    
    # B. Filtraggio per Ordine di Scuola (deve essere CONTENUTO nella scheda)
    if ordine != "Tutti":
        mask &= df['Ordine_scuola'].str.contains(ordine, case=False, regex=False)
    
    df_filtrato = df[mask].copy()

    # C. Motore di Punteggio Equilibrato (Titolo e Abstract pesano uguale)
    if query_utente.strip() != "" and not df_filtrato.empty:
        parole = query_utente.lower().split()
        def calcola_punteggio(row):
            # Uniamo i campi per dare pari dignità alla ricerca
            testo_analisi = (row['Titolo_corso'] + " " + row['Abstract']).lower()
            punti = 0
            for p in parole:
                # Conta le occorrenze totali delle parole chiave
                punti += testo_analisi.count(p)
            return punti

        df_filtrato['score'] = df_filtrato.apply(calcola_punteggio, axis=1)
        df_per_ia = df_filtrato.sort_values(by='score', ascending=False).head(12)
    else:
        df_per_ia = df_filtrato.head(12)

    # --- 6. GENERAZIONE RISPOSTA ---
    if df_per_ia.empty:
        st.error(f"Nessun corso trovato per {regione} - {ordine}. Prova a rimuovere i filtri o a cambiare parole chiave.")
    else:
        with st.spinner("Sto preparando i tuoi consigli personalizzati..."):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-flash-latest')
                
                contesto = df_per_ia[['Titolo_corso', 'Link_scheda', 'Abstract']].to_csv(index=False)
                
                prompt = f"""
                Richiesta: "{query_utente}" per {ordine}.
                Dati disponibili:
                {contesto}
                
                Scegli i 3 corsi migliori. Per ognuno scrivi un breve motivo.
                Alla fine scrivi 'LINK_LIST:' e sotto i link esatti, uno per riga.
                """
                
                res = model.generate_content(prompt)
                st.session_state.risposta_ia = res.text
            except Exception as e:
                st.error(f"Errore nell'analisi IA: {e}")

# --- 7. RISULTATI E QR CODE ---
if "risposta_ia" in st.session_state:
    st.markdown("---")
    parti = st.session_state.risposta_ia.split("LINK_LIST:")
    st.markdown(parti[0])
    
    if len(parti) > 1:
        links = re.findall(r'(https?://scuolafutura[^\s\)\>\]]+)', parti[1])
        if links:
            st.subheader("📱 Inquadra per i dettagli")
            cols = st.columns(len(links[:3]))
            for i, l in enumerate(links[:3]):
                with cols[i]:
                    l_pulito = l.strip(".,;!")
                    st.markdown(f"**[Vai alla Scheda {i+1} 🔗]({l_pulito})**")
                    qr = qrcode.make(l_pulito)
                    buf = BytesIO()
                    qr.save(buf, format="PNG")
                    st.image(buf.getvalue(), use_container_width=True)

    if st.button("🗑️ Reset"):
        del st.session_state.risposta_ia
        st.rerun()
