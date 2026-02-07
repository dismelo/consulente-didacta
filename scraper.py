import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_scuola_futura():
    # URL target (Poli Formativi)
    url = "https://scuolafutura.pubblica.istruzione.it/poli-formativi"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    corsi_data = []
    print("Avvio scansione...")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cerchiamo i link alle schede corso (adattare i selettori se il sito cambia)
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href']
            # Filtro base per trovare link interni pertinenti
            if "scuolafutura" in href and ("percorso" in href or "corso" in href):
                # Pulizia titolo
                titolo = link.get_text(strip=True)
                if len(titolo) > 10: # Ignora link troppo corti
                    corsi_data.append({
                        "Titolo": titolo,
                        "Link": href,
                        "Livello": "B1/B2", # Placeholder se non rilevato
                        "Tematica": "Innovazione Didattica" # Placeholder
                    })

    except Exception as e:
        print(f"Errore connessione: {e}")

    # SALVATAGGIO SICURO: Anche se vuoto, crea le intestazioni
    if not corsi_data:
        print("Nessun corso trovato, creo file placeholder.")
        # Dati finti per testare l'app se il sito è bloccato
        corsi_data.append({"Titolo": "Corso Esempio IA", "Link": "https://scuolafutura.pubblica.istruzione.it/", "Livello": "A2", "Tematica": "IA"})

    df = pd.DataFrame(corsi_data)
    # Rimuove duplicati basati sul Link
    df = df.drop_duplicates(subset=['Link'])
    df.to_csv("Catalogo_Corsi_EFT_2026.csv", index=False)
    print("File CSV salvato con successo.")

if __name__ == "__main__":
    scrape_scuola_futura()
