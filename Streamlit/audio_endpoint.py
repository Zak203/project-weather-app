"""
/audio endpoint — Google Cloud Text-to-Speech
=============================================
À ajouter à ton service Cloud Run existant (functions_framework).

Entrée  POST /audio  → {"query": "indoor_temp", "value": 22.5, "room": "Salon"}
Sortie  JSON          → {"text": "...", "audio_b64": "...base64 mp3..."}
"""

import base64
import functions_framework
from flask import Request, jsonify
from google.cloud import texttospeech

# ── Mapping des clés capteur → phrases françaises ─────────────────────────────
TEMPLATES = {
    "indoor_temp":     "La température intérieure du {room} est de {value} degrés.",
    "indoor_humidity": "L'humidité intérieure du {room} est de {value} pourcent.",
    "eco2":            "Le taux de CO2 du {room} est de {value} parties par million.",
    "tvoc":            "Le taux de composés organiques volatils du {room} est de {value} parties par milliard.",
    "outdoor_temp":    "La température extérieure à {room} est de {value} degrés.",
    "weather_main":    "La météo actuelle à {room} est : {value}.",
    "motion_detected": "Un mouvement a été détecté dans le {room}." if "{value}" == "true"
                       else "Aucun mouvement détecté dans le {room}.",
}

DEFAULT_TEMPLATE = "La valeur de {query} dans le {room} est de {value}."


def build_sentence(query: str, value, room: str) -> str:
    """Génère une phrase française naturelle à partir des données capteur."""
    template = TEMPLATES.get(query, DEFAULT_TEMPLATE)
    # Arrondi à 1 décimale si float
    if isinstance(value, float):
        value = round(value, 1)
    return template.format(query=query, value=value, room=room)


def synthesize_french(text: str) -> bytes:
    """
    Synthétise le texte en MP3 via Google Cloud Text-to-Speech.
    Voix : fr-FR-Neural2-A (voix féminine française Neural2)
    """
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="fr-FR",
        name="fr-FR-Neural2-A",
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0,   # vitesse normale
        pitch=0.0,           # tonalité neutre
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )

    return response.audio_content  # bytes MP3


@functions_framework.http
def audio(request: Request):
    """
    Endpoint HTTP : POST /audio
    Body JSON : {"query": "indoor_temp", "value": 22.5, "room": "Salon"}
    Retourne   : {"text": "...", "audio_b64": "...base64 MP3..."}
    """
    # ── CORS headers (si appelé depuis le dashboard Streamlit) ───────────────
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    if request.method == "OPTIONS":
        return ("", 204, headers)

    if request.method != "POST":
        return (jsonify({"error": "Méthode non autorisée. Utilise POST."}), 405, headers)

    # ── Parsing du body ───────────────────────────────────────────────────────
    body = request.get_json(silent=True)
    if not body:
        return (jsonify({"error": "Corps JSON manquant ou invalide."}), 400, headers)

    query = body.get("query", "")
    value = body.get("value", "")
    room  = body.get("room", "la pièce")

    if not query:
        return (jsonify({"error": "Le champ 'query' est requis."}), 400, headers)

    # ── Génération de la phrase ───────────────────────────────────────────────
    text = build_sentence(query, value, room)

    # ── Synthèse vocale ──────────────────────────────────────────────────────
    try:
        mp3_bytes = synthesize_french(text)
    except Exception as e:
        return (jsonify({"error": f"Erreur TTS : {str(e)}"}), 500, headers)

    # ── Encodage base64 et réponse ───────────────────────────────────────────
    audio_b64 = base64.b64encode(mp3_bytes).decode("utf-8")

    return (jsonify({"text": text, "audio_b64": audio_b64}), 200, headers)
