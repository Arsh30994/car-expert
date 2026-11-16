"""Strict, provider-independent contract for saved diagnostic reports."""

DIAGNOSTIC_JSON_SCHEMA = {
    "type": "object",
    "required": [
        "summary", "observations", "possible_causes", "urgency",
        "safety_warnings", "recommended_actions", "follow_up_questions", "data_gaps",
    ],
    "properties": {
        "summary": {"type": "string"},
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source", "finding", "confidence", "evidence"],
                "properties": {
                    "source": {"enum": ["image", "symptom", "obd", "service", "manual"]},
                    "finding": {"type": "string"},
                    "confidence": {"enum": ["low", "medium", "high"]},
                    "evidence": {"type": "string"},
                },
            },
        },
        "possible_causes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["cause", "likelihood", "supporting_evidence", "contradicting_evidence"],
                "properties": {
                    "cause": {"type": "string"},
                    "likelihood": {"enum": ["low", "medium", "high"]},
                    "supporting_evidence": {"type": "array", "items": {"type": "string"}},
                    "contradicting_evidence": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "urgency": {"enum": ["unknown", "low", "medium", "high", "critical"]},
        "safety_warnings": {"type": "array", "items": {"type": "string"}},
        "recommended_actions": {"type": "array", "items": {"type": "string"}},
        "follow_up_questions": {"type": "array", "items": {"type": "string"}},
        "data_gaps": {"type": "array", "items": {"type": "string"}},
    },
}

class DiagnosticPayloadError(ValueError):
    """Raised when a diagnostic report violates the persisted contract."""


def validate_diagnostic_payload(payload):
    if not isinstance(payload, dict):
        raise DiagnosticPayloadError("Diagnostic report must be a JSON object.")

    required = DIAGNOSTIC_JSON_SCHEMA["required"]
    missing = [field for field in required if field not in payload]
    if missing:
        raise DiagnosticPayloadError("Missing required fields: " + ", ".join(missing))

    if not isinstance(payload["summary"], str) or not payload["summary"].strip():
        raise DiagnosticPayloadError("summary must be a non-empty string.")

    allowed_urgency = DIAGNOSTIC_JSON_SCHEMA["properties"]["urgency"]["enum"]
    if payload["urgency"] not in allowed_urgency:
        raise DiagnosticPayloadError("urgency must be one of: " + ", ".join(allowed_urgency))

    for field in ("safety_warnings", "recommended_actions", "follow_up_questions", "data_gaps"):
        if not isinstance(payload[field], list) or not all(isinstance(item, str) for item in payload[field]):
            raise DiagnosticPayloadError(f"{field} must be a list of strings.")

    for field in ("observations", "possible_causes"):
        if not isinstance(payload[field], list):
            raise DiagnosticPayloadError(f"{field} must be a list.")

    for item in payload["observations"]:
        if not isinstance(item, dict):
            raise DiagnosticPayloadError("Each observation must be an object.")
        if not all(key in item for key in ("source", "finding", "confidence", "evidence")):
            raise DiagnosticPayloadError("Each observation needs source, finding, confidence and evidence.")
        if item["source"] not in ("image", "symptom", "obd", "service", "manual"):
            raise DiagnosticPayloadError("Observation source is not supported.")
        if item["confidence"] not in ("low", "medium", "high"):
            raise DiagnosticPayloadError("Observation confidence must be low, medium or high.")
        if not all(isinstance(item[key], str) and item[key].strip() for key in ("finding", "evidence")):
            raise DiagnosticPayloadError("Observation finding and evidence must be strings.")

    for item in payload["possible_causes"]:
        if not isinstance(item, dict):
            raise DiagnosticPayloadError("Each possible cause must be an object.")
        required_cause = ("cause", "likelihood", "supporting_evidence", "contradicting_evidence")
        if not all(key in item for key in required_cause):
            raise DiagnosticPayloadError("Each possible cause must include evidence and likelihood.")
        if not isinstance(item["cause"], str) or not item["cause"].strip():
            raise DiagnosticPayloadError("Cause must be a non-empty string.")
        if item["likelihood"] not in ("low", "medium", "high"):
            raise DiagnosticPayloadError("Cause likelihood must be low, medium or high.")
        if not all(isinstance(item[key], list) and all(isinstance(v, str) for v in item[key])
                   for key in ("supporting_evidence", "contradicting_evidence")):
            raise DiagnosticPayloadError("Cause evidence must be lists of strings.")

    # Return a JSON-safe copy with only the contract fields. Unknown provider
    # keys are intentionally discarded instead of being persisted as trusted facts.
    return {field: payload[field] for field in required}
