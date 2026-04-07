#!/usr/bin/env python3
"""
Script per sincronizzare foto da Google Drive usando l'API officiale
Prima volta: ti chiede di fare login via browser
Poi: accede automaticamente al tuo Drive

Installazione:
    pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client

Uso:
    python3 sync_drive_api.py
"""

import os
import json
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import discovery

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'

class DrivePhotoSyncAPI:
    def __init__(self):
        self.service = None
        self.authenticate()
    
    def authenticate(self):
        """Autentica con Google Drive API."""
        creds = None
        
        # Se esiste il token salvato, lo riusa
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
        # Se non hai credenziali valide, richiedi login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Crea un file credentials.json da https://developers.google.com/drive/api/quickstart/python
                if not os.path.exists(CREDENTIALS_FILE):
                    print("❌ File credentials.json non trovato!")
                    print("\n📝 Crea il file seguendo questi step:")
                    print("   1. Vai a: https://developers.google.com/drive/api/quickstart/python")
                    print("   2. Clicca 'Enable the Drive API'")
                    print("   3. Scarica il file JSON")
                    print("   4. Rinominalo a 'credentials.json'")
                    print("   5. Mettilo in questa cartella")
                    print("   6. Esegui di nuovo lo script")
                    sys.exit(1)
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Salva il token per usi futuri
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        self.service = discovery.build('drive', 'v3', credentials=creds)
        print("✅ Autenticazione Drive completata\n")
    
    def get_folder_id_from_url(self, url: str) -> str:
        """Estrae il Folder ID da un URL."""
        import re
        match = re.search(r'/folders/([^/?]+)', url)
        if match:
            return match.group(1)
        return None
    
    def get_files_in_folder(self, folder_id: str, folder_name: str = None) -> list:
        """Ottiene tutti i file immagine in una cartella."""
        try:
            query = f"'{folder_id}' in parents and (mimeType='image/jpeg' or mimeType='image/png' or mimeType='image/gif' or mimeType='image/webp') and trashed=false"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=100
            ).execute()
            
            files = results.get('files', [])
            
            if folder_name:
                print(f"📁 {folder_name}: {len(files)} foto")
            
            return [(f['id'], f['name']) for f in files]
        
        except Exception as e:
            print(f"❌ Errore nella lettura cartella: {e}")
            return []
    
    def get_subfolders(self, folder_id: str) -> dict:
        """Ottiene le sottocartelle 'Compleanni', 'Ritratti', 'Varie', 'Esibizioni'."""
        categories = ["Compleanni", "Ritratti", "Varie", "Esibizioni"]
        subfolders = {}
        
        try:
            for category in categories:
                query = f"'{folder_id}' in parents and name='{category}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
                
                results = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name)',
                    pageSize=1
                ).execute()
                
                files = results.get('files', [])
                if files:
                    subfolder_id = files[0]['id']
                    subfolders[category] = subfolder_id
        
        except Exception as e:
            print(f"❌ Errore nella ricerca sottocartelle: {e}")
        
        return subfolders
    
    def sync(self, folder_url: str):
        """Sincronizza le foto dalla cartella Drive."""
        print("📸 Google Drive Photo Sync (API)")
        print("=" * 50 + "\n")
        
        try:
            # Estrai Folder ID
            print("🔗 Estrazione Folder ID dalla URL...")
            folder_id = self.get_folder_id_from_url(folder_url)
            
            if not folder_id:
                print("❌ URL non valida!")
                return False
            
            print(f"✅ Folder ID: {folder_id}\n")
            
            # Leggi le sottocartelle
            print("📸 Ricerca sottocartelle...")
            subfolders = self.get_subfolders(folder_id)
            
            if not subfolders:
                print("❌ Nessuna sottocartella trovata!")
                print("Assicurati che esistano queste cartelle:")
                print("   - Compleanni")
                print("   - Ritratti")
                print("   - Varie")
                print("   - Esibizioni")
                return False
            
            print(f"✅ {len(subfolders)} sottocartelle trovate\n")
            
            # Leggi i file da ogni sottocartella
            print("📍 Lettura foto...")
            files_by_category = {}
            total_files = 0
            
            for category, subfolder_id in subfolders.items():
                files = self.get_files_in_folder(subfolder_id, category)
                files_by_category[category] = files
                total_files += len(files)
            
            # Aggiungi le altre categorie vuote
            for category in ["Compleanni", "Ritratti", "Varie", "Esibizioni"]:
                if category not in files_by_category:
                    files_by_category[category] = []
            
            print(f"\n📊 Totale foto: {total_files}\n")
            
            if total_files == 0:
                print("⚠️  Nessuna foto trovata!")
                return False
            
            # Genera la configurazione
            print("🔧 Generazione gallery-config.json...")
            config = {}
            
            for category in ["Compleanni", "Ritratti", "Varie", "Esibizioni"]:
                files = files_by_category.get(category, [])
                config[category] = [
                    {"fileId": file_id, "name": name}
                    for file_id, name in files
                ]
            
            # Aggiungi i video
            config["Video"] = [
                {"title": "Finale per mattia", "url": "Immagini/Legacy/Finale per mattia.mov"},
                {"title": "Il vero video del banco", "url": "Immagini/Legacy/Il vero video del banco final cut.mp4"},
                {"title": "Pretendiamo legalità", "url": "Immagini/Legacy/Pretendiamo legalità logo.mp4"}
            ]
            
            # Salva il file
            with open('gallery-config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print("✨ Salvato: gallery-config.json\n")
            
            # Mostra il summary
            print("📋 Riepilogo:")
            print("=" * 50)
            for category in ["Compleanni", "Ritratti", "Varie", "Esibizioni"]:
                count = len(config[category])
                print(f"   {category}: {count} foto")
            print("=" * 50)
            
            print("\n🎉 Sincronizzazione completata!")
            print("\n📝 Prossimi step:")
            print("   1. Controlla il file gallery-config.json")
            print("   2. rm -rf Immagini/  (elimina cartella locale)")
            print("   3. git add gallery-config.json index.html")
            print("   4. git commit -m 'Sincronizzazione foto da Google Drive'")
            print("   5. git push")
            
            return True
        
        except Exception as e:
            print(f"\n❌ Errore: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    # Controlla i requisiti
    try:
        import google.auth
        import google_auth_oauthlib
        from googleapiclient import discovery
    except ImportError:
        print("❌ Librerie non trovate!")
        print("\n📦 Installa con:")
        print("   pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        sys.exit(1)
    
    # Se non hai URL, chiedi
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
    
    sync = DrivePhotoSyncAPI()
    success = sync.sync(folder_url)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
