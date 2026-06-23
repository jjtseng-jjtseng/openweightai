import os
import sys
from typing import Any

import requests


SERVICE_URL = os.environ.get("OPENWEIGHTAI_URL", "").rstrip("/")
API_KEY = os.environ.get("OPENWEIGHTAI_API_KEY", "")


def ask(question: str) -> dict[str, Any]:
    if not SERVICE_URL:
        raise RuntimeError("Set OPENWEIGHTAI_URL to your Cloud Run service URL.")
    if not API_KEY:
        raise RuntimeError("Set OPENWEIGHTAI_API_KEY to the API key you deployed.")

    payload = {
        "profile": {
            "name": "Maya",
            "age": 34,
            "likes": ["coffee", "gardening"],
            "income": "$72,000 per year",
            "state": "California",
        },
        "question": question,
        "max_tokens": 120,
        "temperature": 0.1,
    }
    response = requests.post(
        f"{SERVICE_URL}/v1/profile/answer",
        headers={"X-API-Key": API_KEY},
        json=payload,
        timeout=240,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What is your salary?"
    result = ask(question)
    print(result["answer"])
    print(result)

