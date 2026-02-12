import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import random

# Nome del file
FILENAME = "Catalogo_Corsi_EFT_2026.csv"

# Configurazione Browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}

def scrape_courses():
    print("Tentativo di scraping nuovi corsi...")
    lista_corsi = []
    url = "https://scuolafutura.pubblica.istruzione.it/didattica-digitale" 
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # ESEMPIO: Adatta questi selettori al sito reale quando possibile
            cards = soup.find_all('div', class_='card') 
            
            for card in cards:
                # Logica fittizia di estrazione
                titolo = card.find('h3').text.strip() if card.find('h3') else "Corso Scuola Futura"
                link = card.find('a')['href'] if card.find('a') else "https://scuolafutura.pubblica.istruzione.it/"
                
                lista_corsi.append({
                    "Titolo": titolo,
                    "Regione": "Tutte", 
                    "Tematica": "Innovazione",
                    "Link": link if link.startswith('http') else f"https://scuolafutura.pubblica.istruzione.it{link}",
                    "Abstract": "Corso di formazione."
                })
        else:
            print(f"Errore connessione: {response.status_code}")
    except Exception as e:
        print(f"Eccezione scraping: {e}")

    return lista_corsi

def generate_emergency_data():
    """Genera dati finti SOLO se non c'è altra scelta."""
    print("⚠️ Generazione dati di EMERGENZA...")
    dati = []
    temi = ["AI", "Inclusione", "Metodologie", "STEM"]
    regioni = ["Lombardia", "Sicilia", "Lazio", "Tutte"]
    for i in range(10):
        t = random.choice(temi)
        dati.append({
            "Titolo": f"Corso {t} per docenti",
            "Regione": random.choice(regioni),
            "Tematica": t,
            "Link": "https://scuolafutura.pubblica.istruzione.it/",
            "Abstract": "Descrizione corso di prova."
        })
    return dati

if __name__ == "__main__":
    # 1. Tenta lo scraping
    nuovi_dati = scrape_courses()
    
    # 2. Logica decisionale intelligente
    if len(nuovi_dati) > 0:
        # SUCCESSO: Abbiamo nuovi dati, aggiorniamo il file
        print(f"✅ Trovati {len(nuovi_dati)} nuovi corsi. Aggiorno il database.")
        df = pd.DataFrame(nuovi_dati)
        df.to_csv(FILENAME, index=False)
        
    else:
        # FALLIMENTO: Niente dati nuovi
        print("⚠️ Scraping vuoto o fallito.")
        
        # Controlliamo se esiste già un file valido
        if os.path.exists(FILENAME) and os.path.getsize(FILENAME) > 50:
            print("ℹ️ Mantengo il file CSV esistente (nessuna sovrascrittura).")
            # NON facciamo nulla, il file vecchio rimane lì intatto.
        else:
            # Caso disperato: Non c'è file vecchio E lo scraping è fallito.
            # Dobbiamo creare qualcosa altrimenti l'app muore.
            print("🚨 Nessun file precedente trovato. Creo dati di emergenza.")
            df = pd.DataFrame(generate_emergency_data())
            df.to_csv(FILENAME, index=False)
