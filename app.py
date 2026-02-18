import streamlit as st
import google.generativeai as genai
import pandas as pd
import qrcode
import re
import os
from io import BytesIO

# --- 1. CONFIGURAZIONE (Layout Centrato e Titolo) ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

# --- 2. CARICAMENTO DATI "RESILIENTE" ---
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "Catalogo_Corsi_EFT_2026.csv")

@st.cache_data
def load_data():
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    try:
        # Legge con encoding 'utf-8-sig' per ignorare la "scritta in giallo" (BOM di Excel)
        df = pd.read_csv(csv_path, sep=';', dtype=str, encoding='utf-8-sig', on_bad_lines='skip')
        
        # Pulizia totale: rimuove NaN e trasforma tutto in testo pulito
        df = df.fillna("")
        for col in df.columns:
            # Rimuove spazi doppi, ritorni a capo e caratteri invisibili
            df[col] = df[col].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
            # Elimina la scritta 'nan' se presente come testo
            df[col] = df[col].apply(lambda x: "" if x.lower() == "nan" else x)
        
        return df
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. PASSWORD ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Accesso Riservato")
    with st.form("login"):
        user_pwd = st.text_input("Inserisci Password", type="password")
        if st.form_submit_button("Sblocca"):
            if user_pwd == st.secrets.get("APP_PASSWORD", "didacta2026"):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Password errata.")
    st.stop()

# --- 4. INTERFACCIA ---
st.title("🎓 Consulente Formativo EFT 2026")

# Ordini richiesti (Menu fisso come da tua indicazione)
opzioni_scuola = [
    "Tutti", "Scuola dell'infanzia", "Scuola primaria", 
    "Scuola secondaria I grado", "Scuola secondaria II grado", "CPIA"
]

col1, col2 = st.columns(2)
with col1:
    ordine = st.selectbox("Ordine Scuola", opzioni_scuola)
with col2:
    # Filtro regioni: solo nomi validi, niente nan
    regioni_disponibili = sorted([r for r in df['Regione'].unique() if r])
    regione = st.selectbox("Regione", ["Tutte"] + regioni_disponibili)

temi_disponibili = sorted([t for t in df['Tematica'].unique() if t])
tema = st.selectbox("Area Tematica", ["Tutte"] + temi_disponibili)

query = st.text_input("Di cosa vorresti occuparti? (es: storytelling, AI, STEAM...)")

# --- 5. LOGICA DI RICERCA ---
if st.button("🔎 Trova Corsi", use_container_width=True):
    
    # Filtro geografico e scolastico
    mask = pd.Series([True] * len(df))
    if regione != "Tutte":
        mask &= df['Regione'] == regione
    if tema != "Tutte":
        mask &= df['Tematica'] == tema
    if ordine != "Tutti":
        mask &= df['Ordine_scuola'].str.contains(ordine, case=False, na=False)
    
    df_filtrato = df[mask].copy()

    if df_filtrato.empty:
        st.warning("Nessun corso trovato. Prova a cambiare i filtri.")
    else:
        # Punteggio Equilibrato (Titolo + Abstract)
        if query.strip():
            parole = query.lower().split()
            def calculate_score(row):
                testo_completo = (row['Titolo_corso'] + " " + row['Abstract']).lower()
                return sum(testo_completo.count(p) for p in parole)
            df_filtrato['score'] = df_filtrato.apply(calculate_score, axis=1)
            df_top = df_filtrato.sort_values(by='score', ascending=False).head(10)
        else:
            df_top = df_filtrato.head(10)

        # --- 6. IA E RISULTATI ---
        with st.spinner("L'IA sta selezionando i corsi migliori..."):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-flash-latest')
                prompt = f"""
                Analizza questi corsi per un docente che cerca: {query}.
                Filtro ordine scuola: {ordine}.
                CORSI: {df_top[['Titolo_corso', 'Link_scheda', 'Abstract']].to_csv(index=False)}
                Scegli i 3 migliori. Spiega perché in 2 righe. 
                Dopo il testo scrivi 'LISTA_LINK:' e i link sotto uno per riga.
                """
                res = model.generate_content(prompt)
                st.session_state.risposta_ia = res.text
            except Exception as e:
                st.error(f"Errore IA: {e}")

# --- 7. DISPLAY RISULTATI (QR Code ridimensionati) ---
if "risposta_ia" in st.session_state:
    st.markdown("---")
    parti = st.session_state.risposta_ia.split("LISTA_LINK:")
    st.markdown(parti[0])
    
    if len(parti) > 1:
        links = re.findall(r'(https?://scuolafutura[^\s\)\>\]]+)', parti[1])
        if links:
            st.subheader("📱 Schede per l'iscrizione")
            cols_qr = st.columns(len(links[:3]))
            for i, l in enumerate(links[:3]):
                with cols_qr[i]:
                    l_pulito = l.strip(".,;!")
                    st.markdown(f"**[LINK CORSO {i+1}]({l_pulito})**")
                    qr = qrcode.make(l_pulito)
                    buf = BytesIO()
                    qr.save(buf, format="PNG")
                    # QR Code con larghezza fissa per evitare l'effetto "gigante"
                    st.image(buf.getvalue(), width=180)

    if st.button("🗑️ Nuova Ricerca"):
        del st.session_state.risposta_ia
        st.rerun()
