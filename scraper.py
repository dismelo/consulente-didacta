import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import time

def parse_date(date_str):
    # Cerca date nel formato GG/MM/AAAA
    match = re.search(r'(\d{2})/(\d{2})/(\d{4})', date_str)
    if match:
        return datetime.strptime(match.group(0), '%d/%m/%Y')
    return None

def scrape_catalog():
    # LISTA COMPLETA DI TUTTI I POLI E LE ÉQUIPE
    # Nota: Questi sono gli slug standard di Liferay usati dal Ministero
    urls = [
        {"url": "https://scuolafutura.pubblica.istruzione.it/polo-nazionale", "ambito": "Nazionale"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/abruzzo", "ambito": "EFT Abruzzo"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/basilicata", "ambito": "EFT Basilicata"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/calabria", "ambito": "EFT Calabria"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/campania", "ambito": "EFT Campania"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/emilia-romagna", "ambito": "EFT Emilia-Romagna"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/friuli-venezia-giulia", "ambito": "EFT Friuli VG"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/lazio", "ambito": "EFT Lazio"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/liguria", "ambito": "EFT Liguria"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/lombardia", "ambito": "EFT Lombardia"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/marche", "ambito": "EFT Marche"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/molise", "ambito": "EFT Molise"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/piemonte", "ambito": "EFT Piemonte"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/puglia", "ambito": "EFT Puglia"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/sardegna", "ambito": "EFT Sardegna"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/sicilia", "ambito": "EFT Sicilia"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/toscana", "ambito": "EFT Toscana"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/umbria", "ambito": "EFT Umbria"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/valle-aosta", "ambito": "EFT Valle d'Aosta"},
        {"url": "https://scuolafutura.pubblica.istruzione.it/veneto", "ambito": "EFT Veneto"}
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    corsi_trovati = []
    # Data di riferimento: OGGI. Scartiamo tutto ciò che scade prima.
    today = datetime.now() 

    print(f"--- AVVIO SCANSIONE TOTALE ({len(urls)} portali) ---")

    for fonte in urls:
        print(f"Scansione in corso: {fonte['ambito']}...")
        try:
            response = requests.get(fonte['url'], headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Cerchiamo tutti i link che contengono "percorso"
                # Questo intercetta sia le card che le liste
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link['href']
                    titolo = link.get_text(strip=True)
                    
                    # FILTRO 1: È un link a un corso?
                    if "percorso" in href and "id=" in href and len(titolo) > 5:
                        
                        # Costruzione Link Assoluto
                        full_link = href if href.startswith("http") else f"https://scuolafutura.pubblica.istruzione.it{href}"
                        
                        # Estrazione ID
                        match_id = re.search(r'id=(\d+)', full_link)
                        id_corso = match_id.group(1) if match_id else "N/D"

                        # --- ANALISI CONTENUTO PER DATA E CATEGORIA ---
                        # Qui facciamo un'ipotesi: spesso la data è nel testo vicino al link
                        # Per essere precisi al 100% bisognerebbe aprire ogni link (lento), 
                        # ma proviamo a estrarre dal contesto del genitore HTML
                        parent_text = link.parent.get_text(strip=True) if link.parent else ""
                        scadenza_dt = parse_date(parent_text)
                        
                        # FILTRO 2: Controllo Data (Se trovata)
                        is_active = True
                        data_display = "Verificare Online"
                        
                        if scadenza_dt:
                            if scadenza_dt < today:
                                is_active = False # SCADUTO
                            data_display = scadenza_dt.strftime('%d/%m/%Y')
                        
                        # Categorizzazione basica dal titolo
                        tematica = "Metodologie"
                        if any(x in titolo.lower() for x in ['ai ', 'intelligenza', 'gpt']): tematica = "Intelligenza Artificiale"
                        elif any(x in titolo.lower() for x in ['stem', 'robot', 'coding']): tematica = "STEM e Robotica"
                        elif any(x in titolo.lower() for x in ['inclusi', 'bes', 'dsa']): tematica = "Inclusione"
                        
                        livello = "Tutti"
                        if "infanzia" in titolo.lower(): livello = "Infanzia"
                        elif "primaria" in titolo.lower(): livello = "Primaria"
                        elif "secondaria" in titolo.lower(): livello = "Secondaria"

                        if is_active:
                            corsi_trovati.append({
                                "ID": id_corso,
                                "Titolo": titolo,
                                "Link": full_link,
                                "Ambito": fonte['ambito'],
                                "Ordine Scuola": livello,
                                "Tematica": tematica,
                                "DigCompEdu": "Area Mista",
                                "Data Scadenza": data_display
                            })
            
            # Pausa di cortesia per non bloccare il server
            time.sleep(1) 

        except Exception as e:
            print(f"Errore su {fonte['ambito']}: {e}")

    # SALVATAGGIO
    if corsi_trovati:
        df = pd.DataFrame(corsi_trovati)
        # Rimuove duplicati (stesso ID trovato magari in home e in archivio)
        df.drop_duplicates(subset=['ID'], inplace=True)
        df.to_csv("Catalogo_Corsi_EFT_2026.csv", index=False)
        print(f"✅ COMPLETATO. Trovati {len(df)} corsi attivi.")
    else:
        print("⚠️ Nessun corso trovato. Potrebbe essere necessario un controllo manuale.")

if __name__ == "__main__":
    scrape_catalog()
