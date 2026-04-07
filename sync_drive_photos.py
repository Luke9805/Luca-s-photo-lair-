#!/usr/bin/env python3
"""
Script per sincronizzare foto da Google Drive e generare gallery-config.json

Uso:
    python3 sync_drive_photos.py "https://drive.google.com/drive/folders/FOLDER_ID"

O esegui senza parametri e ti chiede il link interattivamente.
"""

import re
import sys
import requests
import json
from pathlib import Path
from typing import Dict, List, Tuple

class DrivePhotoSync:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_folder_id(self, url: str) -> str:
        """Estrae il Folder ID da un URL di Google Drive."""
        match = re.search(r'/folders/([^/?]+)', url)
        if match:
            return match.group(1)
        raise ValueError(f"URL non valido: {url}")
    
    def get_folder_name(self, folder_id: str) -> str:
        """Ottiene il nome della cartella."""
        try:
            url = f"https://drive.google.com/drive/folders/{folder_id}"
            response = self.session.get(url)
            match = re.search(r'"title":"([^"]+)"', response.text)
            if match:
                return match.group(1)
        except Exception as e:
            print(f"⚠️  Non potuto leggere nome cartella: {e}")
        return "Foto"
    
    def extract_file_ids_from_html(self, html: str) -> List[Tuple[str, str]]:
        """Estrae file ID e nomi dal HTML di Google Drive."""
        files = []
        
        # Pattern per find file entries nell'HTML
        pattern = r'"[a-zA-Z0-9_-]{20,}"[^}]*?"displayName":"([^"]+)"'
        
        for match in re.finditer(pattern, html):
            try:
                name = match.group(1)
                # Controlla se è un'immagine
                if name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    # Estrai l'ID (il primo elemento che è un ID lungo)
                    id_match = re.search(r'"([a-zA-Z0-9_-]{20,})"', match.group(0))
                    if id_match:
                        file_id = id_match.group(1)
                        files.append((file_id, name))
            except:
                continue
        
        return files
    
    def get_files_from_folder(self, folder_id: str) -> Dict[str, List[Tuple[str, str]]]:
        """Ottiene tutti i file organizzati per sottocartella."""
        files_by_subfolder = {}
        
        try:
            url = f"https://drive.google.com/drive/folders/{folder_id}"
            response = self.session.get(url)
            
            # Cerca le sottocartelle e i file
            # Pattern per sottocartelle
            subfolder_pattern = r'"([a-zA-Z0-9_-]{20,})"[^}]*?"displayName":"(Compleanni|Ritratti|Varie|Esibizioni)"'
            
            for match in re.finditer(subfolder_pattern, response.text):
                subfolder_id = match.group(1)
                subfolder_name = match.group(2)
                
                print(f"📁 Lettura cartella: {subfolder_name}...")
                
                try:
                    subfolder_url = f"https://drive.google.com/drive/folders/{subfolder_id}"
                    subfolder_response = self.session.get(subfolder_url)
                    
                    files = self.extract_file_ids_from_html(subfolder_response.text)
                    files_by_subfolder[subfolder_name] = files
                    print(f"   ✅ {len(files)} foto trovate")
                except Exception as e:
                    print(f"   ❌ Errore: {e}")
                    files_by_subfolder[subfolder_name] = []
            
            # Se non trova sottocartelle, prova a leggere i file dalla cartella principale
            if not files_by_subfolder:
                print("⚠️  Nessuna sottocartella trovata. Leggo file dalla cartella principale...")
                files = self.extract_file_ids_from_html(response.text)
                
                # Distribuisci i file tra le categorie (per primo carattere o lunghezza)
                categories = ["Compleanni", "Ritratti", "Varie", "Esibizioni"]
                n = len(files)
                
                for i, category in enumerate(categories):
                    start = (i * n) // len(categories)
                    end = ((i + 1) * n) // len(categories)
                    files_by_subfolder[category] = files[start:end]
                    print(f"   ✅ {len(files_by_subfolder[category])} foto in {category}")
        
        except Exception as e:
            print(f"❌ Errore nel lettura folder: {e}")
        
        return files_by_subfolder
    
    def generate_config(self, files_by_subfolder: Dict[str, List[Tuple[str, str]]]) -> Dict:
        """Genera la configurazione gallery-config.json."""
        config = {}
        
        for category in ["Compleanni", "Ritratti", "Varie", "Esibizioni"]:
            files = files_by_subfolder.get(category, [])
            config[category] = [
                {"fileId": file_id, "name": name}
                for file_id, name in files
            ]
        
        # Aggiungi i video (rimangono locali)
        config["Video"] = [
            {"title": "Finale per mattia", "url": "Immagini/Legacy/Finale per mattia.mov"},
            {"title": "Il vero video del banco", "url": "Immagini/Legacy/Il vero video del banco final cut.mp4"},
            {"title": "Pretendiamo legalità", "url": "Immagini/Legacy/Pretendiamo legalità logo.mp4"}
        ]
        
        return config
    
    def save_config(self, config: Dict, filename: str = "gallery-config.json") -> bool:
        """Salva la configurazione in JSON."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"\n✨ Salvato: {filename}")
            return True
        except Exception as e:
            print(f"\n❌ Errore nel salvataggio: {e}")
            return False
    
    def sync(self, folder_url: str):
        """Sincronizza tutto."""
        try:
            print("🔗 Estrazione Folder ID...")
            folder_id = self.extract_folder_id(folder_url)
            print(f"✅ Folder ID: {folder_id}\n")
            
            print("📸 Lettura foto da Google Drive...")
            files_by_subfolder = self.get_files_from_folder(folder_id)
            
            total_files = sum(len(files) for files in files_by_subfolder.values())
            print(f"\n📊 Totale foto trovate: {total_files}\n")
            
            if total_files == 0:
                print("⚠️  Nessuna foto trovata. Controlla:")
                print("   1. Il link della cartella è corretto")
                print("   2. La cartella è pubblica (Condividi → Chiunque abbia il link)")
                print("   3. Le sottocartelle si chiamano: Compleanni, Ritratti, Varie, Esibizioni")
                return False
            
            print("🔧 Generazione configurazione...")
            config = self.generate_config(files_by_subfolder)
            
            # Mostra preview
            print("\n📋 Anteprima configurazione:")
            print("=" * 50)
            for category in ["Compleanni", "Ritratti", "Varie", "Esibizioni"]:
                count = len(config[category])
                print(f"   {category}: {count} foto")
            print("=" * 50 + "\n")
            
            if self.save_config(config):
                print("🎉 Sincronizzazione completata!")
                print("\n📝 Prossimi step:")
                print("   1. Controlla il file gallery-config.json")
                print("   2. Aggiorna index.html se necessario")
                print("   3. git add gallery-config.json")
                print("   4. git commit -m 'Sincronizzazione foto da Google Drive'")
                print("   5. git push")
                return True
            return False
        
        except Exception as e:
            print(f"\n❌ Errore: {e}")
            return False

def main():
    print("📸 Google Drive Photo Sync")
    print("=" * 50 + "\n")
    
    # Leggi l'URL da parametro o da input
    folder_url = None
    
    if len(sys.argv) > 1:
        folder_url = sys.argv[1]
    else:
        print("Incolla il link della cartella Google Drive:")
        print("(Es: https://drive.google.com/drive/folders/ABC123...)\n")
        folder_url = input("🔗 Link: ").strip()
    
    if not folder_url:
        print("❌ Nessun link fornito.")
        sys.exit(1)
    
    sync = DrivePhotoSync()
    success = sync.sync(folder_url)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
