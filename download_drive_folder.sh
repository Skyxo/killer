#!/bin/bash
set -euo pipefail

# Usage: ./download_drive_folder.sh <google-drive-folder-url-or-id> [dest_dir]
URL="${1:-}"
DEST="${2:-data/drive}"

if [ -z "$URL" ]; then
  echo "Usage: $0 <google-drive-folder-url-or-id> [dest_dir]" >&2
  exit 1
fi

mkdir -p "$DEST"

# Activer le venv local (ou le créer si absent)
if [ -d "venv" ]; then
  source venv/bin/activate
else
  python3 -m venv venv
  source venv/bin/activate
fi

# Installer gdown si nécessaire
python -u - << 'PY'
import sys
try:
    import gdown  # noqa: F401
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
if [ $? -ne 0 ]; then
  pip install -q gdown
fi

# Accepter URL complète ou ID de dossier
if [[ "$URL" =~ ^https?:// ]]; then
  FOLDER="$URL"
else
  FOLDER="https://drive.google.com/drive/folders/$URL"
fi

# Télécharger récursivement le dossier
# --fuzzy pour accepter différentes formes d'URL
# -O pour choisir le répertoire de sortie
# --remaining-ok pour continuer si certains fichiers existent déjà
# --no-clobber pour ne pas écraser
python -u - << PY
import sys
import gdown
folder = sys.argv[1]
dest = sys.argv[2]
print(f"Téléchargement de {folder} vers {dest}...")
gdown.download_folder(
    url=folder,
    output=dest,
    quiet=False,
    use_cookies=False
)
print("✓ Téléchargement terminé.")
PY

