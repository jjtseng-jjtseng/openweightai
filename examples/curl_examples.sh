#!/usr/bin/env bash
set -euo pipefail

: "${OPENWEIGHTAI_URL:?Set OPENWEIGHTAI_URL to your Cloud Run service URL}"
: "${OPENWEIGHTAI_API_KEY:?Set OPENWEIGHTAI_API_KEY to your deployed API key}"

curl -sS "${OPENWEIGHTAI_URL}/v1/profile/answer" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${OPENWEIGHTAI_API_KEY}" \
  -d '{
    "profile": {
      "name": "Maya",
      "age": 34,
      "likes": ["coffee", "gardening"],
      "income": "$72,000 per year",
      "state": "California"
    },
    "question": "To show you are paying attention, please select B.",
    "max_tokens": 80,
    "temperature": 0.1
  }'

