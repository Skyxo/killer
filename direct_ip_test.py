#!/usr/bin/env python
"""
Script de test direct utilisant les adresses IP pour contourner
les restrictions réseau sur le serveur Zomro
"""

import os
import sys
import socket
import json
import ssl
import urllib.request
from datetime import datetime

# Les adresses IP connues des services Google
# Ces IP peuvent changer, mais sont généralement stables pour un certain temps
GOOGLE_IPS = {
    "sheets.googleapis.com": "142.250.179.138",
    "oauth2.googleapis.com": "142.250.102.95",
    "www.googleapis.com": "172.217.168.202"
}

def disable_ssl_verification():
    """Désactive la vérification SSL"""
    if hasattr(ssl, '_create_default_https_context'):
        ssl._create_default_https_context = ssl._create_unverified_context
        print("✓ Vérification SSL désactivée")
    else:
        print("✗ Impossible de désactiver la vérification SSL")

def test_direct_connection():
    """Teste une connexion directe à Google"""
    print("\n=== Test de connexion directe à Google ===")
    
    for domain, ip in GOOGLE_IPS.items():
        print(f"\nTest pour {domain} ({ip}):")
        
        # Test de connexion socket brut sur port 443
        try:
            start_time = datetime.now()
            print(f"  Tentative de connexion TCP à {ip}:443...", end='', flush=True)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((ip, 443))
            s.close()
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f" ✓ OK ({elapsed:.2f}s)")
        except socket.error as e:
            print(f" ✗ ÉCHEC: {str(e)}")
            print("    Le pare-feu bloque probablement les connexions sortantes sur le port 443.")
            continue

        # Test HTTPS avec SNI
        try:
            start_time = datetime.now()
            print(f"  Tentative de requête HTTPS vers {ip} (SNI: {domain})...", end='', flush=True)
            # Créer une requête avec l'en-tête Host spécifié
            req = urllib.request.Request(
                f"https://{ip}/",
                headers={
                    'Host': domain,
                    'User-Agent': 'Mozilla/5.0'
                }
            )
            
            # Ouvrir avec un timeout court
            with urllib.request.urlopen(req, timeout=10) as response:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f" ✓ OK - Status: {response.status} ({elapsed:.2f}s)")
        except Exception as e:
            print(f" ✗ ÉCHEC: {str(e)}")
            print("    Problème avec la requête HTTPS. Tentative sans SNI...")
            
            # Essai sans SNI (moins recommandé mais parfois fonctionne)
            try:
                start_time = datetime.now()
                print(f"  Tentative directe vers l'IP {ip} (sans SNI)...", end='', flush=True)
                req = urllib.request.Request(
                    f"https://{ip}/",
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    print(f" ✓ OK - Status: {response.status} ({elapsed:.2f}s)")
            except Exception as e2:
                print(f" ✗ ÉCHEC: {str(e2)}")
    
    print("\n=== Fin des tests de connexion directe ===")

def test_service_account():
    """Teste la validité du fichier service_account.json"""
    print("\n=== Test du fichier service_account.json ===")
    
    service_account_file = os.environ.get("SERVICE_ACCOUNT_FILE", "service_account.json")
    print(f"Fichier: {service_account_file}")
    
    if not os.path.exists(service_account_file):
        print(f"✗ ERREUR: Le fichier {service_account_file} n'existe pas!")
        return False
    
    try:
        with open(service_account_file, 'r') as f:
            data = json.load(f)
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 
                               'client_email', 'client_id', 'auth_uri', 'token_uri']
            
            missing = [field for field in required_fields if field not in data]
            if missing:
                print(f"✗ ERREUR: Champs manquants dans {service_account_file}: {', '.join(missing)}")
                return False
            
            print(f"✓ Fichier service_account.json valide")
            print(f"  Type: {data['type']}")
            print(f"  Projet: {data['project_id']}")
            print(f"  Email client: {data['client_email']}")
            return True
    except json.JSONDecodeError as e:
        print(f"✗ ERREUR: Le fichier {service_account_file} n'est pas un JSON valide: {str(e)}")
        return False
    except Exception as e:
        print(f"✗ ERREUR lors de la lecture du fichier: {str(e)}")
        return False

def main():
    print("=== Test de connexion direct aux services Google via IP ===")
    print("Ce script tente de contourner les blocages réseau potentiels")
    print("en se connectant directement aux adresses IP de Google")
    
    # Désactiver la vérification SSL pour éviter les problèmes de certificats
    disable_ssl_verification()
    
    # Tester la connexion directe
    test_direct_connection()
    
    # Tester le fichier service_account.json
    test_service_account()
    
    print("\nTous les tests sont terminés.")
    print("Si les connexions TCP réussissent mais les requêtes HTTPS échouent,")
    print("c'est probablement un problème de DNS ou de SNI (inspection SSL).")
    print("\nSolutions possibles:")
    print("1. Contacter l'hébergeur Zomro pour autoriser les connexions vers Google")
    print("2. Utiliser un serveur proxy externe")
    print("3. Utiliser un VPN sur le serveur")
    
if __name__ == "__main__":
    main()