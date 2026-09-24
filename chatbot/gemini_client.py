import json
import logging
import mimetypes
import re
import base64

from django.conf import settings
from groq import Groq

logger = logging.getLogger(__name__)

if settings.GROQ_API_KEY:
    client = Groq(api_key=settings.GROQ_API_KEY)
else:
    client = None
    logger.warning("GROQ_API_KEY is not configured.")

SYSTEM_PROMPT = """You are Car Expert AI — an expert automotive assistant with
deep knowledge of engines, transmissions, brakes, suspension, steering,
electrical systems, diagnostics, maintenance, tires, fuel systems, EVs,
hybrids, and vehicle safety.

SCOPE — you ONLY answer questions about cars, automobiles, and vehicle-related
technical topics. If the question is unrelated, politely refuse:
"I'm a car-focused assistant. I can only help with automobile-related
questions, diagnostics, maintenance, specifications, components, repairs,
and driving-related technical information."

SAFETY — if the user describes fire, smoke, fuel leak, brake failure, severe
overheating, loss of steering, an accident, or an electrical burning smell,
prioritize safety: recommend stopping the vehicle safely, turning off the
engine if appropriate, and contacting roadside assistance or emergency
services before anything else.

ACCURACY — do not invent exact specifications (torque values, fluid
capacities, part numbers) unless certain they apply to this vehicle. Say it
depends on the variant and point to the service manual if unsure.

IMAGES/VIDEO — distinguish observation ("fluid residue near the lower engine
area") from definitive diagnosis ("the oil pan gasket is broken"). Don't
overstate certainty from an image alone.

VEHICLE CONTEXT — if given the user's vehicle make/model/year/engine, tailor
your answer to that specific vehicle rather than giving generic advice.

OUTPUT — always reply with a single JSON object and nothing else:
{
  "text": "full assistant reply in plain language",
  "finding": null or {
    "severity": "advisory" | "warning" | "critical",
    "confidence": 0-100,
    "title": "short title",
    "body": "what you observed or inferred",
    "recommendation": "what the user should do next"
  }
}
Use a finding when there is a diagnostic observation (including from an image).
Otherwise set finding to null.
"""

REPLY_FORMAT = (
    "Respond with JSON only as specified in your instructions: "
    '{"text": "...", "finding": null or an object}.'
)


def is_car_related(user_text, uploaded_file_path=None):
    if not user_text and not uploaded_file_path:
        return True

    if client is None:
        return True

    prompt = (
        "Is this related to cars, vehicles, or automotive topics "
        "(including images/documents of car parts, dashboards, "
        "engines, damage, manuals)? Answer with only one word: YES or NO."
    )

    message_text = f'{prompt}\n\nMessage: "{user_text}"' if user_text else prompt
    if uploaded_file_path:
        image_content = _image_content(uploaded_file_path)
        content = [image_content, {"type": "text", "text": message_text}]
        model = settings.GROQ_VISION_MODEL
        if not model:
            return True
    else:
        content = message_text
        model = settings.GROQ_MODEL

    try:
        result = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            temperature=0,
            max_tokens=128,
            reasoning_effort="low",
        )
        answer = (result.choices[0].message.content or "").strip().upper()
        return not answer or answer.startswith("YES")
    except Exception:
        logger.exception("Groq classifier failed.")
        return True


def _image_content(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type or not mime_type.startswith("image/"):
        return None
    with open(file_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
    }


def _parse_reply(raw_text):
    raw = (raw_text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        text = data.get("text") or raw_text
        finding = data.get("finding")
        if finding and not isinstance(finding, dict):
            finding = None
        return text, finding
    except (json.JSONDecodeError, TypeError, AttributeError):
        return raw_text, None


def get_response(user_text, uploaded_file=None, vehicle_context=None):
    if client is None:
        return (
            "Groq is not configured. Add GROQ_API_KEY to .env and restart the server.",
            None,
        )

    text_parts = []
    image_content = None

    if vehicle_context:
        text_parts.append(f"[User's vehicle: {vehicle_context}]")

    if uploaded_file:
        mime_type, _ = mimetypes.guess_type(uploaded_file)
        if mime_type and mime_type.startswith("image/"):
            image_content = _image_content(uploaded_file)
            text_parts.append(
                "Analyze this image. Structure the text field in two clearly "
                "labeled parts:\n"
                "OBSERVATION: only what is visually present in the image "
                "(parts, damage, fluid, warning lights, wear, etc.) — no "
                "conclusions yet.\n"
                "POSSIBLE CAUSES: what this observation could indicate, "
                "phrased as possibilities, not certainties. If the image "
                "alone can't determine the cause, say so and recommend "
                "what additional info or inspection would help."
            )

    if user_text:
        text_parts.append(user_text)

    text_parts.append(REPLY_FORMAT)

    if not text_parts:
        return "Tell me about the vehicle or attach a photo, and I can help.", None

    if image_content:
        if not settings.GROQ_VISION_MODEL:
            return (
                "Image analysis is not available with the currently configured Groq models. "
                "You can still ask text-based car questions.",
                None,
            )
        content = [image_content, {"type": "text", "text": "\n\n".join(text_parts)}]
        model = settings.GROQ_VISION_MODEL
    else:
        content = "\n\n".join(text_parts)
        model = settings.GROQ_MODEL

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            temperature=0.2,
        )
        return _parse_reply(response.choices[0].message.content)
    except Exception:
        logger.exception("Groq generation failed.")
        return (
            "I couldn't generate a reply right now. Please try again. "
            "If this keeps happening, check the server log for the Groq API error.",
            None,
        )
