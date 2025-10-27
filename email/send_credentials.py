#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
send_credentials.py

Usage:
  python send_credentials.py --csv [nom du csv].csv --rate 1.0 --login-url "http://188.137.182.53:8080/"

Le script lit un CSV avec en-tête (séparateur virgule) contenant au minimum :
- "Surnom (le VRAI, pour pouvoir vous identifier)"   -> identifiant
- "Votre mot de passe (vous devrez vous en SOUVENIR pour jouer, même en BO)"  -> mot de passe
- "Adresse e-mail"                                   -> email

Variables d'environnement requises :
  SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
Optionnelles :
  FROM_NAME (par défaut "Club IA"), FROM_EMAIL (par défaut = SMTP_USER)

Sortie :
  sent_log.csv (identifiant,email,status,error,timestamp)
"""
import os
import csv
import time
import argparse
import smtplib
from email.message import EmailMessage
from typing import Optional
from pathlib import Path

# Charger les variables d'environnement depuis .env
try:
    from dotenv import load_dotenv
    # Chercher le .env dans le dossier parent (racine du projet)
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Variables d'environnement chargées depuis {env_path}")
    else:
        # Essayer dans le dossier courant
        load_dotenv()
except ImportError:
    print("⚠️  Module python-dotenv non installé. Chargez manuellement les variables avec : source ../.env")

# 👇 ajoute/édite cette variable une seule fois
login_url = "http://188.137.182.53:8080/"

HEADER_MAP_DEFAULT = {
    "identifiant": "Surnom (le VRAI, pour pouvoir vous identifier)",
    "mot_de_passe": "Votre mot de passe (vous devrez vous en SOUVENIR pour jouer, même en BO)",
    "email": "Adresse e-mail",
}

DEFAULT_SUBJECT = "Rappel pour le killer idf/mdp"

DEFAULT_BODY_PLAIN = """Yo {identifiant} !

Voilà tes identifiants pour le killer (essaye de pas BO par pitwei)

Identifiant : {identifiant}
Mot de passe : {mot_de_passe}

Si tu veux arrêter de jouer tu peux cliquer sur "abandonner" à tout moment.
Les admins sont là aussi pour t'aider (leur numéro de tel est dans le trombi)

➡ Connexion : {login_url}


Killerment,
{from_name}
"""

DEFAULT_BODY_HTML = """\
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
  </head>
  <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; margin:0; padding:0; background:#f6f7fb;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:24px auto;background:#ffffff;border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,0.06);overflow:hidden;">
      <tr>
        <td style="padding:20px 24px;">
          <h2 style="margin:0 0 12px 0;font-size:20px;font-weight:700;color:#111;">Yo {identifiant} !</h2>
          <p style="margin:0 0 14px 0;font-size:15px;color:#222;">
            Voilà tes identifiants pour le killer <em>(essaye de pas BO par pitwei)</em>
          </p>

          <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;margin:14px 0 18px 0;border-collapse:collapse;">
            <tr>
              <td style="padding:10px 12px;border-radius:6px;background:#f2f4f7;">
                <strong>Identifiant :</strong> <span style="margin-left:8px;">{identifiant}</span><br/>
                <strong>Mot de passe :</strong> <span style="margin-left:8px;">{mot_de_passe}</span>
              </td>
            </tr>
          </table>

          <p style="margin:0 0 8px 0;font-size:14px;color:#333;">
            Si tu veux arrêter de jouer tu peux cliquer sur <strong>"abandonner"</strong> à tout moment.
          </p>
          <p style="margin:6px 0 18px 0;font-size:14px;color:#333;">
            Les admins sont là aussi pour t'aider (leur numéro de tel est dans le trombi).
          </p>

          <p style="margin:0 0 18px 0;font-size:15px;">
            Pour te connecter :
          </p>

          <p style="margin:0 0 22px 0;">
            <a href="{login_url}" target="_blank" rel="noopener noreferrer"
               style="display:inline-block;padding:12px 18px;background:#1d72ff;color:#fff;text-decoration:none;border-radius:8px;font-weight:700;">
              Se connecter
            </a>
          </p>

          <p style="margin:0;font-size:14px;color:#666;">
            Killerment,<br/>
            <strong>{from_name}</strong>
          </p>

          <hr style="border:none;border-top:1px solid #eef0f4;margin:18px 0;" />

          <p style="margin:0;font-size:12px;color:#9aa0ab;">
            gros fyot
          </p>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def send_email(smtp_server: str, smtp_port: int, smtp_user: str, smtp_password: str,
               from_name: str, from_email: str, to_email: str,
               subject: str, body_plain: str, body_html: Optional[str] = None,
               timeout: int = 20):
    msg = EmailMessage()
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body_plain)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    with smtplib.SMTP(smtp_server, smtp_port, timeout=timeout) as smtp:
        smtp.ehlo()
        try:
            smtp.starttls()
            smtp.ehlo()
        except Exception:
            pass
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)

def normalize(s: Optional[str]) -> str:
    return (s or "").strip().replace("\u200b", "")  # enlève ZWSP éventuels

def main():
    parser = argparse.ArgumentParser(description="Envoi d'emails personnalisés (identifiant + mdp) depuis un CSV en-têtes FR.")
    parser.add_argument("--csv", required=True, help="Chemin du fichier CSV")
    parser.add_argument("--rate", type=float, default=1.0, help="Secondes entre envois (défaut: 1.0)")
    parser.add_argument("--dry-run", action="store_true", help="Ne pas envoyer, seulement simuler et logger")
    parser.add_argument("--subject", default=DEFAULT_SUBJECT, help="Objet de l'email")
    parser.add_argument("--body-plain", default=DEFAULT_BODY_PLAIN, help="Corps texte (placeholders {identifiant} {mot_de_passe} {from_name})")
    parser.add_argument("--body-html", default=DEFAULT_BODY_HTML, help="Corps HTML (placeholders {identifiant} {mot_de_passe} {from_name})")
    parser.add_argument(
        "--login-url",
        default=os.environ.get("LOGIN_URL", ""),  # fallback sur la variable globale
        help="URL de connexion à inclure dans l'email (peut aussi venir de LOGIN_URL)"
    )
    # possibilité de surcharger les noms d'en-têtes si besoin
    parser.add_argument("--col-identifiant", default=HEADER_MAP_DEFAULT["identifiant"], help="Nom de colonne pour l'identifiant")
    parser.add_argument("--col-mdp", default=HEADER_MAP_DEFAULT["mot_de_passe"], help="Nom de colonne pour le mot de passe")
    parser.add_argument("--col-email", default=HEADER_MAP_DEFAULT["email"], help="Nom de colonne pour l'email")
    args = parser.parse_args()

    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    from_name = os.environ.get("FROM_NAME", "Club IA")
    from_email = os.environ.get("FROM_EMAIL", smtp_user)

    if not smtp_server or not smtp_user or not smtp_password:
        print("ERROR: définir SMTP_SERVER, SMTP_USER, SMTP_PASSWORD (et éventuellement SMTP_PORT).")
        return

    required_headers = {args.col_identifiant, args.col_mdp, args.col_email}
    sent_log_path = "sent_log.csv"

    with open(args.csv, newline='', encoding="utf-8") as f, \
         open(sent_log_path, "a", newline='', encoding="utf-8") as logf:
        reader = csv.DictReader(f)
        log_writer = csv.writer(logf)
        if logf.tell() == 0:
            log_writer.writerow(["identifiant", "email", "status", "error", "timestamp"])

        # Vérifie présence des colonnes attendues
        headers = set(reader.fieldnames or [])
        missing = [h for h in required_headers if h not in headers]
        if missing:
            print("ERROR: colonnes manquantes dans le CSV :", missing)
            print("Colonnes trouvées :", list(headers))
            return

        for i, row in enumerate(reader, start=2):  # start=2 (ligne 1 = entêtes)
            identifiant = normalize(row.get(args.col_identifiant))
            mot_de_passe = normalize(row.get(args.col_mdp))
            email = normalize(row.get(args.col_email)).lower()

            # Skip si pas d'email
            if not email or "@" not in email:
                log_writer.writerow([identifiant, email, "skipped", "email invalide ou vide", time.time()])
                continue

            # Avertit si mdp manquant (ex. Loom/T.A.C. dans l’exemple)
            if not mot_de_passe:
                print(f"⚠️  Ligne {i}: MDP manquant pour {identifiant} → email envoyé quand même (contiendra MDP vide).")

            body_plain = args.body_plain.format(
                identifiant=identifiant or "—",
                mot_de_passe=mot_de_passe or "—",
                from_name=from_name,
                login_url=args.login_url or ""   # <-- ajouté
            )
            body_html = args.body_html.format(
                identifiant=identifiant or "—",
                mot_de_passe=mot_de_passe or "—",
                from_name=from_name,
                login_url=args.login_url or ""   # <-- ajouté
            )

            try:
                if args.dry_run:
                    print(f"[DRY-RUN] → {email} | id={identifiant!r} | mdp={mot_de_passe!r}")
                    status, error = "dry-run", ""
                else:
                    send_email(smtp_server, smtp_port, smtp_user, smtp_password,
                               from_name, from_email, email,
                               args.subject, body_plain, body_html)
                    print(f"✅ Envoyé → {email} (id={identifiant})")
                    status, error = "sent", ""
            except Exception as e:
                print(f"❌ ERREUR envoi {email} (ligne {i}): {e}")
                status, error = "error", str(e)

            log_writer.writerow([identifiant, email, status, error, time.time()])
            logf.flush()
            time.sleep(args.rate)

if __name__ == "__main__":
    main()
