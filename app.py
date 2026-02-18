import streamlit as st
import google.generativeai as genai
import pandas as pd
import qrcode
import re
import os
from io import BytesIO

# --- 1. CONFIGURAZIONE (Layout centrato per una migliore leggibilità) ---
st.set_page_config(page_title="Orientatore EFT 2026", layout="centered")

# --- 2. CARICAMENTO DATI "INTELLIGENTE" (Excel o CSV) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "Catalogo_Corsi_EFT_2026.csv")

@st.cache_data
def load_data():
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    try:
        # Tenta prima come CSV (separatore punto e virgola)
        try:
            df = pd.read_csv(csv_path, sep=';', dtype=str, encoding='utf-8-sig')
            # Se ha letto una sola colonna, forse è un formato Excel vero
            if df.shape[1] <= 1: raise Exception("Formato non riconosciuto")
        except:
            # Se fallisce, tenta come Excel (perché il file potrebbe essere un .xlsx rinominato)
            df = pd.read_excel(csv_path, dtype=str)
        
        # Pulizia rigorosa: rimuove NaN, spazi bianchi e "nan" testuali
        df = df.fillna("")
        for col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[\r\n\t]+', ' ', regex=True).str.strip()
            # Se la cella contiene la parola "nan" (comune in Excel), la svuota
            df[col] = df[col].apply(lambda x: "" if x.lower() == "nan" else x)
        
        return df
    except Exception as e:
        st.error(f"Errore critico: il file non è leggibile. Assicurati che sia un CSV (punto e virgola) o un Excel valido. {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. PASSWORD ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Accesso Riservato")
    with st.form("login"):
        user_pwd = st.text_input("Inserisci la Password", type="password", key="pwd_fixed_v5")
        if st.form_submit_button("Sblocca"):
            if user_pwd == st.secrets.get("APP_PASSWORD", "didacta2026"):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Password errata.")
    st.stop()

# --- 4. INTERFACCIA E FILTRI ---
st.title("🎓 Consulente Formativo EFT 2026")

# Liste personalizzate basate sulla tua richiesta
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
    regioni = sorted([r for r in df['Regione'].unique() if r])
    regione = st.selectbox("Regione", ["Tutte"] + regioni)

tematiche = sorted([t for t in df['Tematica'].unique() if t])
tema = st.selectbox("Area Tematica", ["Tutte"] + tematiche)

query_utente = st.text_input("Cosa cerchi? (es: IA per inclusione, coding, realtà aumentata...)")

# --- 5. RICERCA E RANKING (Titolo e Abstract pari merito) ---
if st.button("🔎 Cerca Corsi", use_container_width=True):
    
    # Filtri di base
    mask = pd.Series([True] * len(df))
    if ordine != "Tutti":
        mask &= df['Ordine_scuola'].str.contains(ordine, case=False, regex=False)
    if regione != "Tutte":
        mask &= df['Regione'] == regione
    if tema != "Tutte":
        mask &= df['Tematica'] == tema
    
    df_filtrato = df[mask].copy()

    if df_filtrato.empty:
        st.warning(f"Nessun corso trovato in {regione} per {ordine}. Prova ad allargare i filtri.")
    else:
        # Calcolo punteggio: titolo e abstract hanno lo stesso valore
        if query_utente.strip():
            parole = query_utente.lower().split()
            def score(row):
                testo = (row['Titolo_corso'] + " " + row['Abstract']).lower()
                return sum(testo.count(p) for p in parole)
            
            df_filtrato['score'] = df_filtrato.apply(score, axis=1)
            df_risultati = df_filtrato.sort_values(by='score', ascending=False).head(10)
        else:
            df_risultati = df_filtrato.head(10)

        # --- 6. INTELLIGENZA ARTIFICIALE ---
        with st.spinner("Analisi in corso..."):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-flash-latest')
                contesto = df_risultati[['Titolo_corso', 'Link_scheda', 'Abstract']].to_csv(index=False)
                
                prompt = f"""
                L'utente cerca: "{query_utente}" per {ordine}.
                Dati corsi: {contesto}
                Scegli i 3 più attinenti e spiega perché in 2 righe.
                Formatta così: scrivi il report, poi 'TAG_LINK:' e i link uno per riga.
                """
                res = model.generate_content(prompt)
                st.session_state.risposta_ia = res.text
            except Exception as e:
                st.error(f"Errore IA: {e}")

# --- 7. RISULTATI E QR CODE (DIMENSIONI CONTROLLATE) ---
if "risposta_ia" in st.session_state:
    st.markdown("---")
    parti = st.session_state.risposta_ia.split("TAG_LINK:")
    st.markdown(parti[0])
    
    if len(parti) > 1:
        links = re.findall(r'(https?://scuolafutura[^\s\)\>\]]+)', parti[1])
        if links:
            st.subheader("📱 QR Code per iscrizione")
            # Usiamo colonne per i QR Code
            q_cols = st.columns(len(links[:3]))
            for i, link in enumerate(links[:3]):
                with q_cols[i]:
                    l_pulito = link.strip(".,;!")
                    st.markdown(f"**[LINK CORSO {i+1}]({l_pulito})**")
                    qr = qrcode.make(l_pulito)
                    buf = BytesIO()
                    qr.save(buf, format="PNG")
                    # Larghezza fissa a 200 per evitare QR code giganti
                    st.image(buf.getvalue(), width=200)

    if st.button("🗑️ Nuova Ricerca"):
        del st.session_state.risposta_ia
        st.rerun()
