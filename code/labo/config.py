"""Reglages communs aux deux missions du labo."""
from pathlib import Path

BASE = Path("/opt/labo")
DATA = BASE / "data"
SONDES_DB = DATA / "sondes.db"
NEURO_DB = DATA / "neurones.db"
IMG_DIR = DATA / "sondes" / "img"

# API publique OPUS (PDS Ring-Moon Systems Node, NASA) : gratuite, sans compte.
OPUS_API = "https://opus.pds-rings.seti.org/opus/api"
OPUS_PREVIEWS = "https://opus.pds-rings.seti.org/holdings/previews/"
OPUS_DETAIL = "https://opus.pds-rings.seti.org/opus/#/view=detail&detail="  # fiche d'une image

# Campagnes de depart. Une image n'est "bizarre" que comparee aux autres images
# de la meme cible prises par le meme instrument.
CAMPAIGNS = [
    ("Galileo SSI", "Io"),
    ("Galileo SSI", "Europa"),
    ("Voyager ISS", "Miranda"),
    ("Voyager ISS", "Triton"),
    ("Cassini ISS", "Hyperion"),
    ("Cassini ISS", "Enceladus"),
    ("New Horizons LORRI", "Pluto"),
    ("New Horizons LORRI", "Arrokoth"),
]

# Nom de la sonde de chaque camera, donne a l'IA pour qu'elle n'en invente pas.
PROBES = {"Galileo SSI": "sonde Galileo (en orbite autour de Jupiter de 1995 a 2003)",
          "Voyager ISS": "sondes Voyager 1 et 2 (survols de 1979 a 1989)",
          "Cassini ISS": "sonde Cassini (en orbite autour de Saturne de 2004 a 2017)",
          "New Horizons LORRI": "sonde New Horizons (Pluton en 2015, Arrokoth en 2019)",
          "New Horizons MVIC": "sonde New Horizons (Pluton en 2015, Arrokoth en 2019)"}

# Ce que disent les photos prises juste avant et apres une piste (voir labo.sondes.sequence).
SEQUENCE_TEXT = {
    "seule": "Aucune autre photo exploitable de cet astre dans les 2 heures autour : impossible de savoir si c'est"
             " un phénomène qui dure ou un accident d'une seule image.",
    "dure": "Les photos prises juste avant et juste après sont elles aussi inhabituelles : ce qu'on voit dure"
            " plusieurs minutes, ce n'est probablement pas un accident d'une seule image.",
    "isolee": "Les photos prises juste avant et juste après sont normales : soit c'est un phénomène très bref, soit"
              " c'est un accident de cette seule image (rayon cosmique, parasite) ou un simple changement de cadrage.",
}

# Une fois les campagnes de depart finies, la fouille s'etend a toutes les cibles
# de ces cameras (environ 560 000 images au total).
IMAGING_INSTRUMENTS = [
    "Galileo SSI",
    "Voyager ISS",
    "New Horizons LORRI",
    "New Horizons MVIC",
    "Cassini ISS",
]

# Mission 2 : facons de signaler a la culture qu'elle a rate la balle.
FEEDBACK_MODES = {
    "fep": "retour prévisible / imprévisible (DishBrain)",
    "silent": "silence après une balle ratée",
    "none": "aucun retour",
}

# Publication des recherches sur GitHub (voir labo.publication).
PUBLICATION_SETTINGS = DATA / "publication.json"
PUBLICATION_STATUS = DATA / "publication-etat.json"
DEPLOY_KEY = DATA / ".ssh" / "github_ed25519"

# Etat en direct des missions (page « En direct » du tableau de bord).
LIVE_DIR = DATA / "direct"

# Surveillance (labo.veille) : erreurs relevees et reglages des notifications.
VEILLE_DB = DATA / "veille.db"
NOTIFY_SETTINGS = DATA / "notifications.json"
NTFY_URL = "https://ntfy.sh"  # service de notifications gratuit, sans compte
SERVICES = {"labo-sondes": "Sondes Fantômes", "labo-neurones": "Labo de neurones", "labo-web": "Tableau de bord",
            "labo-publication": "Publication GitHub", "tailscaled": "Accès par VPN", "ollama": "IA locale"}

# Format commun des journaux : le niveau (WARNING, ERROR...) sert a la surveillance.
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

# IA locale optionnelle (Ollama). Sans elle, les missions tournent quand meme.
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "gemma3:4b"
