#!/usr/bin/env python
"""
Script de test d'authentification Google Sheets en mode standalone.
Utiliser ce script pour vérifier si l'authentification fonctionne correctement
indépendamment du serveur Flask.
"""

import os
import sys
import json
import socket
from dotenv import load_dotenv
from google.oauth2 import service_account
import gspread

def main():
    print("=== Test d'authentification Google Sheets ===\n")
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Augmenter le timeout des sockets
    socket.setdefaulttimeout(30)
    
    # Vérifier si le fichier de service account existe
    service_account_file = os.environ.get("SERVICE_ACCOUNT_FILE", "service_account.json")
    print(f"Fichier de compte de service: {service_account_file}")
    
    if not os.path.exists(service_account_file):
        print(f"ERREUR: Le fichier {service_account_file} n'existe pas!")
        sys.exit(1)
    
    # Vérifier le contenu du fichier service account
    try:
        with open(service_account_file, 'r') as f:
            content = json.load(f)
            print(f"✓ Lecture du fichier JSON réussie")
            print(f"  Type de compte: {content.get('type', 'non spécifié')}")
            print(f"  Client email: {content.get('client_email', 'non spécifié')}")
            print(f"  Projet: {content.get('project_id', 'non spécifié')}")
    except json.JSONDecodeError as e:
        print(f"ERREUR: Le fichier {service_account_file} n'est pas un JSON valide!")
        print(f"Détail: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"ERREUR lors de la lecture du fichier: {str(e)}")
        sys.exit(1)
    
    # Tenter l'authentification
    try:
        print("\nTentative d'authentification...")
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=scope
        )
        
        print("✓ Credentials créées avec succès")
        
        # Tenter de créer un client gspread
        client = gspread.authorize(credentials)
        print("✓ Client gspread autorisé avec succès")
        
        # Tenter d'ouvrir le sheet
        sheet_id = os.environ.get("SHEET_ID")
        if not sheet_id:
            print("AVERTISSEMENT: SHEET_ID non défini dans les variables d'environnement")
            print("Tentative de lister les sheets disponibles...")
            try:
                sheets = client.openall()
                print(f"Sheets disponibles ({len(sheets)}):")
                for s in sheets:
                    print(f"  - {s.title} (ID: {s.id})")
            except Exception as e:
                print(f"ERREUR lors de la liste des sheets: {str(e)}")
        else:
            print(f"Tentative d'ouverture du sheet ID: {sheet_id}")
            try:
                spreadsheet = client.open_by_key(sheet_id)
                print(f"✓ Ouverture réussie du sheet: {spreadsheet.title}")
                
                # Lister les worksheets
                worksheets = spreadsheet.worksheets()
                print(f"Worksheets disponibles ({len(worksheets)}):")
                for ws in worksheets:
                    print(f"  - {ws.title}")
                
                # Lire quelques données
                if worksheets:
                    first_sheet = worksheets[0]
                    print(f"\nLecture des premières données de {first_sheet.title}...")
                    try:
                        values = first_sheet.get_all_values()
                        if values:
                            print(f"Premières lignes:")
                            for i, row in enumerate(values[:3]):  # Afficher les 3 premières lignes
                                print(f"  Ligne {i+1}: {row}")
                        else:
                            print("La feuille est vide")
                    except Exception as e:
                        print(f"ERREUR lors de la lecture des données: {str(e)}")
            except Exception as e:
                print(f"ERREUR lors de l'ouverture du sheet: {str(e)}")
                print("Vérifiez que l'ID est correct et que le compte de service a accès à ce document.")
        
        print("\n✓ Test d'authentification réussi!")
        return True
    
    except Exception as e:
        import traceback
        print(f"\n✗ ERREUR d'authentification: {str(e)}")
        print(f"Détail de l'erreur: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    # Si SSL bypass est disponible, l'importer
    try:
        if os.path.exists(os.path.join(os.path.dirname(__file__), 'ssl_bypass.py')):
            print("Chargement du bypass SSL...")
            import ssl_bypass
    except Exception:
        pass
    
    # Si proxy_config est disponible, l'importer
    try:
        if os.path.exists(os.path.join(os.path.dirname(__file__), 'proxy_config.py')):
            print("Chargement de la configuration proxy...")
            import proxy_config
    except Exception:
        pass
    
    success = main()
    sys.exit(0 if success else 1)