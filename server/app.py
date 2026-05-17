"""
Brajawali WhatsApp webhook — Twilio + Flask.

When a user sends a WhatsApp message to your Twilio sandbox number, Twilio
hits this webhook. We parse the body, run translate_v2, and respond with
TwiML that Twilio sends back as a WhatsApp reply.

Endpoints:
    POST /whatsapp   — Twilio webhook
    GET  /           — health check (returns "ok")
    GET  /test?text=... — browser test (returns plain JSON)

Environment:
    PORT (default 8000)
    BRAJAWALI_TIMEOUT_SECONDS (default 10)
"""
from __future__ import annotations
import os
import sys
import json
import time
from pathlib import Path
from flask import Flask, request, Response

# Make `lib/translate_v2` importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

# Lazy-load the translator on first request to keep cold-start fast
_translator = None


def get_translator():
    global _translator
    if _translator is None:
        try:
            from translate_v2 import TranslatorV2
            _translator = TranslatorV2()
        except Exception:
            # NLP layer not available — fall back to v1
            from translate import Translator
            _translator = Translator()
    return _translator


app = Flask(__name__)


@app.get("/")
def health():
    return "Brajawali bot — alive\n"


@app.get("/test")
def test():
    text = request.args.get("text", "মই তোমাক ভাল পাওঁ")
    t = get_translator()
    r = t.translate(text)
    return Response(json.dumps(r, ensure_ascii=False, indent=2),
                    mimetype="application/json")


def _twiml(message: str) -> Response:
    """Build a minimal TwiML reply."""
    safe = (message
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response><Message>' + safe + '</Message></Response>'
    )
    return Response(body, mimetype="application/xml")


def _format_reply(translation: dict) -> str:
    """Make a tidy WhatsApp-friendly response."""
    lines = []
    lines.append(f"*{translation['brajawali']}*")
    lines.append("")
    lines.append(f"_(input: {translation['normalised_assamese']})_")
    lines.append("")
    lines.append("Word-by-word:")
    for tok in translation["alignment"]:
        src_tag = tok["source"]
        tag = "✓" if src_tag in ("core", "dictionary") else (
              "≈" if src_tag == "fuzzy" else (
              "*" if "morph" in src_tag else (
              "?" if src_tag == "unknown" else "·")))
        lines.append(f"  {tag} {tok['asm']} → {tok['braja']}")
    meta = translation["metadata"]
    if meta.get("unknown_count", 0):
        lines.append("")
        lines.append(f"_{meta['unknown_count']} unknown of {meta['token_count']}_")
    return "\n".join(lines)


@app.post("/whatsapp")
def whatsapp():
    body = request.values.get("Body", "").strip()
    if not body:
        return _twiml(
            "👋 Send any Assamese (or Roman-Assamese) text and I'll "
            "translate to Brajawali — Sankaradeva's literary language.\n\n"
            "Example: মই তোমাক ভাল পাওঁ\n"
            "Example: moi tumar logot ahisilo")

    if body.lower() in ("help", "/help", "?"):
        return _twiml(
            "🪷 *Brajawali Bot*\n\n"
            "Send any Assamese sentence — get the Brajawali rendering "
            "from Sankaradeva-Madhavadeva's literary language.\n\n"
            "Examples:\n"
            "• মই তোমাক ভাল পাওঁ\n"
            "• তেওঁ ঘৰলৈ গ'ল\n"
            "• moi tumar logot ahisilo  (Roman input also works)\n\n"
            "Source: Sri Sri Narayan Chandra Goswami's "
            "ব্ৰজাৱলী ভাষাৰ ব্যাকৰণ আৰু অভিধান (1990)")

    try:
        t = get_translator()
        result = t.translate(body)
        return _twiml(_format_reply(result))
    except Exception as exc:
        return _twiml(f"❌ error: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
