#!/usr/bin/env python3
# Script pour mettre en cache les données des joueurs

import os
import json
import gspread
from google.oauth2 import service_account
from dotenv import load_dotenv

def main():
    # Charger les variables d'environnement
    load_dotenv()
    
    print("=== Mise en cache des données joueurs ===")
    
    try:
        # Connexion à Google Sheets
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        service_account_file = os.environ.get("SERVICE_ACCOUNT_FILE", "service_account.json")
        
        if not os.path.exists(service_account_file):
            print(f"Erreur: Le fichier {service_account_file} est introuvable.")
            return 1
            
        print(f"Utilisation du fichier de service: {service_account_file}")
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file, 
            scopes=scope
        )
        
        client = gspread.authorize(credentials)
        sheet_id = os.environ.get("SHEET_ID")
        
        if not sheet_id:
            print("Erreur: SHEET_ID manquant dans les variables d'environnement.")
            return 1
            
        print(f"Ouverture de la feuille avec ID: {sheet_id}")
        sheet = client.open_by_key(sheet_id).sheet1
        
        # Récupération de toutes les données
        print("Récupération des données...")
        data = sheet.get_all_values()
        
        if not data or len(data) <= 1:
            print("Erreur: Feuille vide ou seulement avec l'en-tête.")
            return 1
        
        # Trouver les indices des colonnes importantes
        headers = data[0]
        column_indices = {}
        
        for i, header in enumerate(headers):
            header_lower = header.lower()
            if "surnom" in header_lower or "nickname" in header_lower:
                column_indices["NICKNAME"] = i
            elif "mdp" in header_lower or "password" in header_lower or "mot de passe" in header_lower:
                column_indices["PASSWORD"] = i
            elif "visage" in header_lower or "face" in header_lower or "person" in header_lower:
                column_indices["PERSON_PHOTO"] = i
            elif "pied" in header_lower or "feet" in header_lower:
                column_indices["FEET_PHOTO"] = i
            elif "statut" in header_lower or "status" in header_lower:
                column_indices["STATUS"] = i
            elif "cible" in header_lower and "actuelle" in header_lower or "current" in header_lower and "target" in header_lower:
                column_indices["CURRENT_TARGET"] = i
            elif "action" in header_lower and "actuelle" in header_lower or "current" in header_lower and "action" in header_lower:
                column_indices["CURRENT_ACTION"] = i
        
        required_columns = ["NICKNAME", "PASSWORD"]
        missing_columns = [col for col in required_columns if col not in column_indices]
        
        if missing_columns:
            print(f"Erreur: Colonnes requises manquantes: {', '.join(missing_columns)}")
            return 1
            
        # Créer la structure de données pour le cache
        players = []
        
        # Ignorer la ligne d'en-tête
        for i, row in enumerate(data[1:], 1):
            if len(row) <= column_indices["NICKNAME"] or not row[column_indices["NICKNAME"]]:
                continue  # Ignorer les lignes sans surnom
                
            player = {
                "row": i + 1,  # +1 car on ignore la ligne d'en-tête mais on veut l'index réel
                "nickname": row[column_indices["NICKNAME"]],
                "password": row[column_indices["PASSWORD"]] if "PASSWORD" in column_indices and len(row) > column_indices["PASSWORD"] else "",
                "person_photo": row[column_indices["PERSON_PHOTO"]] if "PERSON_PHOTO" in column_indices and len(row) > column_indices["PERSON_PHOTO"] else "",
                "feet_photo": row[column_indices["FEET_PHOTO"]] if "FEET_PHOTO" in column_indices and len(row) > column_indices["FEET_PHOTO"] else "",
                "status": row[column_indices["STATUS"]] if "STATUS" in column_indices and len(row) > column_indices["STATUS"] else "alive",
                "target": row[column_indices["CURRENT_TARGET"]] if "CURRENT_TARGET" in column_indices and len(row) > column_indices["CURRENT_TARGET"] else "",
                "action": row[column_indices["CURRENT_ACTION"]] if "CURRENT_ACTION" in column_indices and len(row) > column_indices["CURRENT_ACTION"] else ""
            }
            players.append(player)
            
        # Sauvegarder dans un fichier cache
        with open("players_cache.json", "w") as f:
            json.dump(players, f, indent=2)
            
        print(f"✓ {len(players)} joueurs mis en cache dans players_cache.json")
        return 0
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise en cache: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())