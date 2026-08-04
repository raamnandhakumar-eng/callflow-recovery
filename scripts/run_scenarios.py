import argparse
import json
import uuid

import httpx

SCENARIOS = [
    {
        "name": "appointment-booking",
        "payload": {
            "tenant_slug": "northstar-hvac",
            "caller_phone": "+12125550101",
            "customer_name": "Jordan Lee",
            "transcript": "I need to book an appointment for my air conditioner this Thursday.",
            "requested_time": "Thursday at 2:00 PM",
            "service": "air-conditioning diagnostic",
        },
    },
    {
        "name": "price-question",
        "payload": {
            "tenant_slug": "northstar-hvac",
            "caller_phone": "+12125550102",
            "customer_name": "Morgan Patel",
            "transcript": "How much does a diagnostic visit cost?",
        },
    },
    {
        "name": "after-hours-emergency",
        "payload": {
            "tenant_slug": "northstar-hvac",
            "caller_phone": "+12125550103",
            "customer_name": "Casey Kim",
            "transcript": "There is smoke and sparking from my furnace. This is an emergency.",
        },
    },
    {
        "name": "knowledge-gap",
        "payload": {
            "tenant_slug": "northstar-hvac",
            "caller_phone": "+12125550104",
            "customer_name": "Taylor Singh",
            "transcript": "Do you service geothermal heat pumps in historic buildings?",
        },
    },
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Replay the first call to prove idempotency",
    )
    args = parser.parse_args()

    results = []
    with httpx.Client(timeout=15) as client:
        for scenario in SCENARIOS:
            payload = dict(scenario["payload"])
            payload["external_call_id"] = (
                f"synthetic-{scenario['name']}-{uuid.uuid4().hex[:8]}"
            )
            response = client.post(f"{args.base_url}/v1/calls/simulate", json=payload)
            response.raise_for_status()
            result = response.json()
            results.append({"scenario": scenario["name"], **result})
            print(json.dumps(results[-1], indent=2))

        if args.replay:
            replay_payload = dict(SCENARIOS[0]["payload"])
            replay_payload["external_call_id"] = results[0]["external_call_id"]
            replay = client.post(
                f"{args.base_url}/v1/calls/simulate",
                json=replay_payload,
            )
            replay.raise_for_status()
            print("\nIDEMPOTENCY REPLAY\n" + json.dumps(replay.json(), indent=2))

    print(f"\nDashboard: {args.base_url}/dashboard/northstar-hvac")


if __name__ == "__main__":
    main()
