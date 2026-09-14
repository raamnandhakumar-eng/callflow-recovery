import json
import os
import time
import urllib.error
import urllib.request
import uuid

BASE_URL = os.getenv("PUBLIC_SMOKE_URL", "https://callflow-recovery.onrender.com").rstrip("/")
ATTEMPTS = int(os.getenv("PUBLIC_SMOKE_ATTEMPTS", "24"))
DELAY_SECONDS = int(os.getenv("PUBLIC_SMOKE_DELAY_SECONDS", "15"))


def request(path: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, str]:
    data = None
    headers = {"User-Agent": "callflow-public-smoke/1.0"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.status, response.read().decode("utf-8")


def wait_for_current_deploy() -> None:
    last_error = "unknown"
    for attempt in range(1, ATTEMPTS + 1):
        try:
            status, body = request("/")
            ready_status, ready_body = request("/ready")
            ready = json.loads(ready_body)
            if (
                status == 200
                and ready_status == 200
                and "Recruiter demo" in body
                and ready.get("status") == "ready_for_recruiter_demo"
                and ready.get("mode") == "demo"
                and "crm_live" in ready.get("integrations", {})
            ):
                print(f"Current recruiter deployment detected on attempt {attempt}.")
                return
            last_error = f"deployment not current: landing={status}, ready={ready}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = repr(exc)
        print(f"Attempt {attempt}/{ATTEMPTS}: {last_error}")
        if attempt < ATTEMPTS:
            time.sleep(DELAY_SECONDS)
    raise SystemExit(f"Public deployment did not become ready: {last_error}")


def run_smoke() -> None:
    status, dashboard = request("/dashboard/northstar-hvac")
    assert status == 200
    assert "AI Workflow Operations" in dashboard
    assert "Run end-to-end call" in dashboard
    assert "demo adapter" in dashboard.lower()

    call_id = f"smoke-{uuid.uuid4().hex[:12]}"
    payload = {
        "tenant_slug": "northstar-hvac",
        "external_call_id": call_id,
        "caller_phone": "+12125550123",
        "customer_name": "Public Smoke Test",
        "transcript": "I need to book an appointment for an AC diagnostic.",
        "requested_time": "Thursday at 2 PM",
        "service": "AC diagnostic",
    }
    status, body = request("/v1/calls/simulate", method="POST", payload=payload)
    assert status == 200
    result = json.loads(body)
    assert result["status"] == "booked"
    assert result["appointment_id"]
    assert result["crm_contact_id"].startswith("demo-")
    assert result["sms_message_id"].startswith("demo-")
    assert "simulated" in result["answer"].lower()

    replay_status, replay_body = request("/v1/calls/simulate", method="POST", payload=payload)
    assert replay_status == 200
    replay = json.loads(replay_body)
    assert replay["replayed"] is True
    assert replay["appointment_id"] == result["appointment_id"]

    print("Public recruiter demo smoke test passed.")
    print(
        json.dumps(
            {
                "base_url": BASE_URL,
                "call_id": call_id,
                "status": result["status"],
                "crm": result["crm_contact_id"],
                "sms": result["sms_message_id"],
                "replayed": replay["replayed"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    wait_for_current_deploy()
    run_smoke()
