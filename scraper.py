import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

def scrape_scuola_futura():
    # URL target: Usiamo la pagina di ricerca pubblica o l'home page dei percorsi
    # Nota: Se il sito cambia, questo URL potrebbe richiedere aggiornamenti
    base_domain = "https://scuolafutura.pubblica.istruzione.it"
    url = f"{base_domain}/poli-formativi" 
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    corsi_data = []
    print(f"Scansione di: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cerca tutti i link nella pagina
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href']
            titolo = link.get_text(strip=True)
            
            # FILTRO INTELLIGENTE: Cerchiamo link che sembrano corsi
            # Solitamente contengono parole chiave come 'corso', 'percorso', 'id'
            if len(titolo) > 10 and ("percorso" in href or "id=" in href or "scheda" in href):
                
                # 1. CORREZIONE LINK (Da Relativo ad Assoluto)
                full_link = href if href.startswith("http") else f"{base_domain}{href}"
                
                # 2. ESTRAZIONE ID (Cerca numeri nel link)
                # Esempio: .../percorso-12345 -> ID: 12345
                match_id = re.search(r'(\d{4,})', full_link)
                id_corso = match_id.group(1) if match_id else "N/D"
                
                # Evitiamo duplicati e link di sistema
                if id_corso != "N/D":
                    corsi_data.append({
                        "ID": id_corso,
                        "Titolo": titolo,
                        "Link": full_link,
                        # Questi campi verranno poi arricchiti o inferiti dall'IA se mancanti
                        "Livello": "Misto", 
                        "Tematica": "Didattica Digitale"
                    })

    except Exception as e:
        print(f"Errore durante lo scraping: {e}")

    # SALVATAGGIO CSV
    if not corsi_data:
        print("⚠️ Attenzione: Nessun corso trovato dallo scraper automatico.")
        # Dati di fallback per garantire che l'app parta
        corsi_data.append({
            "ID": "99999", 
            "Titolo": "Corso Demo: Intelligenza Artificiale in Classe", 
            "Link": "https://scuolafutura.pubblica.istruzione.it/", 
            "Livello": "A1", 
            "Tematica": "IA"
        })

    df = pd.DataFrame(corsi_data)
    # Rimuove duplicati basati sull'ID
    df = df.drop_duplicates(subset=['ID'])
    
    print(f"Trovati {len(df)} corsi.")
    df.to_csv("Catalogo_Corsi_EFT_2026.csv", index=False)

if __name__ == "__main__":
    scrape_scuola_futura()
