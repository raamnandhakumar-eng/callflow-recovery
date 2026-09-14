from dataclasses import dataclass


@dataclass(frozen=True)
class IntentResult:
    name: str
    confidence: float


class IntentRouter:
    """Fast first-pass router intended to stay out of the live-call latency hot path."""

    def classify(self, transcript: str) -> IntentResult:
        text = transcript.lower()
        emergency_terms = ("gas leak", "smoke", "sparking", "no heat", "flood", "emergency")
        booking_terms = ("book", "appointment", "schedule", "come out", "technician")
        reschedule_terms = ("reschedule", "move my appointment", "change my appointment")
        price_terms = ("price", "cost", "how much", "fee")
        hours_terms = ("open", "hours", "close", "weekend")
        service_terms = (
            "ac diagnostic",
            "ac repair",
            "air conditioning",
            "furnace",
            "heat pump",
            "thermostat",
            "hvac",
            "maintenance",
            "tune-up",
            "tune up",
        )
        time_terms = (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "today",
            "tomorrow",
            "tonight",
            "morning",
            "afternoon",
            "evening",
            "next available",
        )

        if any(term in text for term in emergency_terms):
            return IntentResult("emergency", 0.97)
        if any(term in text for term in reschedule_terms):
            return IntentResult("reschedule", 0.94)
        if any(term in text for term in booking_terms):
            return IntentResult("appointment", 0.92)
        if any(term in text for term in service_terms) and any(term in text for term in time_terms):
            return IntentResult("appointment", 0.90)
        if any(term in text for term in price_terms + hours_terms):
            return IntentResult("faq", 0.88)
        if len(text.split()) >= 5:
            return IntentResult("faq", 0.60)
        return IntentResult("unknown", 0.30)
