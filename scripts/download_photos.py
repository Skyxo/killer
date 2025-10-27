#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de téléchargement et renommage automatique des photos depuis Google Drive

Usage:
  python download_photos.py --csv ../data/formulaire.csv --output-dir ../data/images

Ce script :
1. Lit le fichier formulaire.csv
2. Extrait les liens Google Drive des photos
3. Télécharge chaque photo
4. Les renomme avec le surnom du joueur ([Surnom].jpg ou [Surnom]_pieds.jpg)
5. Les sauvegarde dans data/images/tetes/ et data/images/pieds/
"""

import os
import csv
import argparse
import requests
import re
from pathlib import Path
from PIL import Image
import io
import unicodedata

def sanitize_filename(name):
    """Nettoie un nom pour l'utiliser comme nom de fichier"""
    # Normaliser les caractères Unicode
    name = unicodedata.normalize('NFKC', name)
    # Remplacer les caractères problématiques
    name = name.replace('/', '_').replace('\\', '_').replace(' ', '_')
    # Garder uniquement les caractères alphanumériques et quelques spéciaux
    name = re.sub(r'[^\w\-.]', '_', name)
    return name

def extract_google_drive_id(url):
    """Extrait l'ID de fichier depuis une URL Google Drive"""
    if not url or not isinstance(url, str):
        return None
    
    url = url.strip()
    
    # Format: https://drive.google.com/file/d/ID/view?usp=sharing
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    
    # Format: https://drive.google.com/open?id=ID
    match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    
    return None

def download_google_drive_file(file_id, output_path):
    """Télécharge un fichier depuis Google Drive"""
    if not file_id:
        return False
    
    # URL de téléchargement direct
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    try:
        # Première tentative avec le lien direct
        response = requests.get(url, timeout=30, allow_redirects=True)
        
        # Vérifier si Google demande une confirmation (fichiers > 100MB)
        if 'confirm' in response.text and 'download_warning' in response.text:
            # Extraire le token de confirmation
            confirm_match = re.search(r'confirm=([^&]+)', response.text)
            if confirm_match:
                confirm_token = confirm_match.group(1)
                url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm_token}"
                response = requests.get(url, timeout=30, allow_redirects=True)
        
        if response.status_code == 200:
            # Vérifier que c'est bien une image
            content_type = response.headers.get('content-type', '').lower()
            if 'image' not in content_type and 'octet-stream' not in content_type:
                print(f"  ⚠️  Le contenu téléchargé n'est pas une image (type: {content_type})")
                return False
            
            # Convertir en JPG avec PIL
            try:
                img = Image.open(io.BytesIO(response.content))
                
                # Convertir en RGB si nécessaire
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if img.mode in ('RGBA', 'LA'):
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                
                # Redimensionner si trop grande (max 1200x1200 pour garder une bonne qualité)
                max_size = 1200
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Sauvegarder en JPG
                img.save(output_path, 'JPEG', quality=90, optimize=True)
                return True
            
            except Exception as e:
                print(f"  ❌ Erreur lors de la conversion de l'image: {e}")
                return False
        
        else:
            print(f"  ❌ Erreur HTTP {response.status_code}")
            return False
    
    except requests.exceptions.Timeout:
        print(f"  ❌ Timeout lors du téléchargement")
        return False
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Erreur de connexion: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Erreur inattendue: {e}")
        return False

def process_csv(csv_path, output_dir, skip_existing=True, dry_run=False):
    """Traite le CSV et télécharge toutes les photos"""
    
    # Créer les dossiers de sortie
    tetes_dir = Path(output_dir) / "tetes"
    pieds_dir = Path(output_dir) / "pieds"
    
    if not dry_run:
        tetes_dir.mkdir(parents=True, exist_ok=True)
        pieds_dir.mkdir(parents=True, exist_ok=True)
    
    # Statistiques
    stats = {
        'total': 0,
        'tetes_downloaded': 0,
        'pieds_downloaded': 0,
        'tetes_skipped': 0,
        'pieds_skipped': 0,
        'tetes_failed': 0,
        'pieds_failed': 0,
        'tetes_no_link': 0,
        'pieds_no_link': 0,
    }
    
    # Lire le CSV
    with open(csv_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            nickname = row.get("Surnom (le VRAI, pour pouvoir vous identifier)", "").strip()
            
            if not nickname:
                continue
            
            stats['total'] += 1
            
            # Nettoyer le surnom pour le nom de fichier
            safe_nickname = sanitize_filename(nickname)
            
            print(f"\n[{stats['total']}] Traitement de {nickname}...")
            
            # Photo de profil
            person_photo_link = row.get("Une photo de vous neuillesque (pour le jeu)", "").strip()
            if person_photo_link:
                output_path = tetes_dir / f"{safe_nickname}.jpg"
                
                if skip_existing and output_path.exists():
                    print(f"  ✓ Photo de profil déjà existante, ignorée")
                    stats['tetes_skipped'] += 1
                else:
                    if dry_run:
                        print(f"  [DRY-RUN] Téléchargerait: {person_photo_link} → {output_path}")
                        stats['tetes_downloaded'] += 1
                    else:
                        file_id = extract_google_drive_id(person_photo_link)
                        if file_id:
                            print(f"  📥 Téléchargement photo de profil (ID: {file_id})...")
                            if download_google_drive_file(file_id, str(output_path)):
                                print(f"  ✅ Photo de profil sauvegardée: {output_path.name}")
                                stats['tetes_downloaded'] += 1
                            else:
                                stats['tetes_failed'] += 1
                        else:
                            print(f"  ⚠️  Impossible d'extraire l'ID du lien: {person_photo_link}")
                            stats['tetes_failed'] += 1
            else:
                print(f"  ⊘ Pas de photo de profil")
                stats['tetes_no_link'] += 1
            
            # Photo de pieds
            feet_photo_link = row.get("une photo de vos pieds (pour le plaisir)", "").strip()
            if feet_photo_link:
                output_path = pieds_dir / f"{safe_nickname}_pieds.jpg"
                
                if skip_existing and output_path.exists():
                    print(f"  ✓ Photo de pieds déjà existante, ignorée")
                    stats['pieds_skipped'] += 1
                else:
                    if dry_run:
                        print(f"  [DRY-RUN] Téléchargerait: {feet_photo_link} → {output_path}")
                        stats['pieds_downloaded'] += 1
                    else:
                        file_id = extract_google_drive_id(feet_photo_link)
                        if file_id:
                            print(f"  📥 Téléchargement photo de pieds (ID: {file_id})...")
                            if download_google_drive_file(file_id, str(output_path)):
                                print(f"  ✅ Photo de pieds sauvegardée: {output_path.name}")
                                stats['pieds_downloaded'] += 1
                            else:
                                stats['pieds_failed'] += 1
                        else:
                            print(f"  ⚠️  Impossible d'extraire l'ID du lien: {feet_photo_link}")
                            stats['pieds_failed'] += 1
            else:
                print(f"  ⊘ Pas de photo de pieds")
                stats['pieds_no_link'] += 1
    
    # Afficher le résumé
    print("\n" + "="*60)
    print("📊 RÉSUMÉ")
    print("="*60)
    print(f"Total de joueurs traités: {stats['total']}")
    print(f"\n📸 Photos de profil:")
    print(f"  ✅ Téléchargées: {stats['tetes_downloaded']}")
    print(f"  ⏭️  Ignorées (déjà existantes): {stats['tetes_skipped']}")
    print(f"  ❌ Échecs: {stats['tetes_failed']}")
    print(f"  ⊘  Pas de lien: {stats['tetes_no_link']}")
    print(f"\n🦶 Photos de pieds:")
    print(f"  ✅ Téléchargées: {stats['pieds_downloaded']}")
    print(f"  ⏭️  Ignorées (déjà existantes): {stats['pieds_skipped']}")
    print(f"  ❌ Échecs: {stats['pieds_failed']}")
    print(f"  ⊘  Pas de lien: {stats['pieds_no_link']}")
    print("="*60)
    
    return stats

def main():
    parser = argparse.ArgumentParser(
        description="Télécharge et renomme automatiquement les photos depuis Google Drive"
    )
    parser.add_argument(
        "--csv",
        default="../data/formulaire.csv",
        help="Chemin du fichier CSV (défaut: ../data/formulaire.csv)"
    )
    parser.add_argument(
        "--output-dir",
        default="../data/images",
        help="Dossier de sortie pour les images (défaut: ../data/images)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Télécharger même si le fichier existe déjà"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulation sans téléchargement réel"
    )
    
    args = parser.parse_args()
    
    # Vérifier que le CSV existe
    if not os.path.exists(args.csv):
        print(f"❌ Erreur: Le fichier {args.csv} n'existe pas")
        return 1
    
    print("🚀 Démarrage du téléchargement des photos...")
    print(f"📁 CSV: {args.csv}")
    print(f"📂 Dossier de sortie: {args.output_dir}")
    if args.force:
        print("⚠️  Mode FORCE: remplacement des fichiers existants")
    if args.dry_run:
        print("🔍 Mode DRY-RUN: simulation sans téléchargement")
    print()
    
    try:
        stats = process_csv(
            args.csv,
            args.output_dir,
            skip_existing=not args.force,
            dry_run=args.dry_run
        )
        
        # Code de sortie basé sur les échecs
        if stats['tetes_failed'] > 0 or stats['pieds_failed'] > 0:
            print("\n⚠️  Certains téléchargements ont échoué")
            return 1
        
        print("\n✅ Tous les téléchargements ont réussi !")
        return 0
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Téléchargement interrompu par l'utilisateur")
        return 130
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

