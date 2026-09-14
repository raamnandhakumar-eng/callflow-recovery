from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptDetails:
    service: str | None
    requested_time: str | None


def extract_transcript_details(transcript: str) -> TranscriptDetails:
    text = " ".join(transcript.strip().split())
    lower = text.lower()

    service = None
    if "ac diagnostic" in lower:
        service = "AC diagnostic"
    elif "ac repair" in lower or "ac stopped working" in lower or "ac is not working" in lower:
        service = "AC repair"
    elif "furnace" in lower:
        service = "Furnace service"
    elif "heat pump" in lower:
        service = "Heat pump service"
    elif "thermostat" in lower:
        service = "Thermostat service"
    elif "maintenance" in lower or "tune-up" in lower or "tune up" in lower:
        service = "HVAC maintenance"

    requested_time = None
    for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
        if day in lower:
            requested_time = day.title()
            marker = lower.find(day) + len(day)
            tail = text[marker:].strip().rstrip(".,!?;")
            if tail.lower().startswith("at "):
                requested_time = f"{day.title()} {tail}"
            break
    if requested_time is None:
        for relative in ("tomorrow morning", "tomorrow afternoon", "tomorrow evening", "tomorrow", "today", "tonight", "next available"):
            if relative in lower:
                requested_time = "next available slot" if relative == "next available" else relative.title()
                break

    return TranscriptDetails(service=service, requested_time=requested_time)
