import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_scuola_futura():
    base_url = "https://scuolafutura.pubblica.istruzione.it"
    start_url = f"{base_url}/poli-formativi"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    corsi_data = []

    print("Inizio scansione portale Scuola Futura...")

    try:
        # 1. Accediamo alla pagina dei Poli
        response = requests.get(start_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Nota: Qui lo scraper cercherà i link ai singoli Poli/EFT. 
        # Per ora simuliamo la cattura dei percorsi (andrà raffinato con i selettori CSS esatti del sito)
        
        # ESEMPIO DI LOGICA DI ESTRAZIONE (Andrà adattata ai selettori reali del sito)
        # Cerchiamo tutti i link che portano a schede corso o liste corsi
        percorsi = soup.find_all('a', href=True)
        
        for link in percorsi:
            if "/percorso/" in link['href'] or "scheda-corso" in link['href']:
                url_corso = base_url + link['href'] if not link['href'].startswith('http') else link['href']
                
                # Entriamo nella scheda del corso per i dettagli
                res_corso = requests.get(url_corso, headers=headers)
                s_corso = BeautifulSoup(res_corso.text, 'html.parser')
                
                # Estrazione dati (usiamo dei segnaposti che l'IA poi riempirà o che lo scraper cercherà)
                titolo = s_corso.find('h1').text.strip() if s_corso.find('h1') else "Titolo non trovato"
                
                # Cerchiamo le info DigCompEdu e Obiettivi nel testo
                testo_completo = s_corso.get_text()
                
                # Logica semplificata per trovare il livello DigCompEdu (A1, A2, B1...)
                livelli = ["A1", "A2", "B1", "B2", "C1", "C2"]
                livello_trovato = next((l for l in livelli if l in testo_completo), "N/D")
                
                corsi_data.append({
                    "Titolo": titolo,
                    "Sintesi": "Descrizione estratta dal portale...", # Qui andrebbe il selettore della descrizione
                    "Obiettivi": "Obiettivi formativi del corso...",
                    "DigCompEdu_Competenze": "Area 1, Area 2...", # Da mappare in base ai tag del sito
                    "Livello": livello_trovato,
                    "Link": url_corso
                })
                
                print(f"Estratto: {titolo}")
                time.sleep(1) # Rispettiamo il server per non essere bloccati

        # Salvataggio nel CSV che l'app già usa
        df = pd.DataFrame(corsi_data)
        df.to_csv("Catalogo_Corsi_EFT_2026.csv", index=False, encoding='utf-8')
        print("Scansione completata. File CSV aggiornato!")

    except Exception as e:
        print(f"Errore durante lo scraping: {e}")

if __name__ == "__main__":
    scrape_scuola_futura()
