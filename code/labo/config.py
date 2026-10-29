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

# Engin qui porte chaque camera (« la camera X de ... »), donne a l'IA pour qu'elle n'en invente pas.
HUBBLE = "du télescope spatial Hubble (en orbite autour de la Terre depuis 1990)"
PROBES = {"Galileo SSI": "de la sonde Galileo (en orbite autour de Jupiter de 1995 à 2003)",
          "Voyager ISS": "des sondes Voyager 1 et 2 (survols de 1979 à 1989)",
          "Cassini ISS": "de la sonde Cassini (en orbite autour de Saturne de 2004 à 2017)",
          "New Horizons LORRI": "de la sonde New Horizons (Pluton en 2015, Arrokoth en 2019)",
          "New Horizons MVIC": "de la sonde New Horizons (Pluton en 2015, Arrokoth en 2019)",
          "Hubble ACS": HUBBLE, "Hubble WFPC2": HUBBLE, "Hubble WFC3": HUBBLE, "Hubble NICMOS": HUBBLE}

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
# de ces cameras (environ 560 000 images au total), puis aux photos des planetes prises par Hubble
# (environ 20 000 de plus). Les spectrometres (VIMS, UVIS...) ne donnent pas de vraies photos : pas fouilles.
IMAGING_INSTRUMENTS = [
    "Galileo SSI",
    "Voyager ISS",
    "New Horizons LORRI",
    "New Horizons MVIC",
    "Cassini ISS",
    "Hubble WFPC2",
    "Hubble ACS",
    "Hubble WFC3",
    "Hubble NICMOS",
]

# Mission 2 : facons de signaler a la culture qu'elle a rate la balle.
FEEDBACK_MODES = {
    "fep": "retour prévisible / imprévisible (DishBrain)",
    "silent": "silence après une balle ratée",
    "none": "aucun retour",
}
# Taille de la culture (20 000 = ce que le processeur tient encore un peu plus vite que le temps reel).
# Chaque recette garde la taille sur laquelle elle a ete jouee : seules celles de la taille actuelle
# se comparent entre elles, les anciennes restent en archive.
CULTURE_SIZE = 20000

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
