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

# IA locale optionnelle (Ollama). Sans elle, les missions tournent quand meme.
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "gemma3:4b"
