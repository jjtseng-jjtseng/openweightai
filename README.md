# OpenWeightAI

OpenWeightAI is a small Cloud Run API for asking profile-grounded questions against an open-weight Gemma model. It is designed for a Raspberry Pi 5 client: the Pi sends HTTPS requests, while Cloud Run runs the GPU-backed inference service.

The deployed Cloud Run service has two containers:

- `api`: a lightweight FastAPI gateway that exposes `/v1/profile/answer`, optional API-key auth, `/readyz`, `/warmup`, and an OpenAI-compatible pass-through at `/v1/chat/completions`.
- `vllm`: a Gemma 4 vLLM sidecar using an NVIDIA L4 GPU.

## Model Weights

This project uses the Hugging Face model ID:

```text
google/gemma-4-E2B-it
```

Before deploying:

1. Create or sign in to a Hugging Face account.
2. Open `https://huggingface.co/google/gemma-4-E2B-it`.
3. Accept the Gemma model terms if Hugging Face asks for approval.
4. Create a read token at `https://huggingface.co/settings/tokens`.
5. Paste that token into the Colab notebook when prompted.

The weights are not committed to GitHub. The vLLM container downloads them on Cloud Run startup. With `minScale: 0`, the first request after scale-to-zero can be slow because the model has to download or load again. Warm requests on an already-running instance are much faster.

Google also publishes Gemma weights through Kaggle, but this deployment path uses Hugging Face because vLLM can pull the Hugging Face model ID directly.

## Cloud Run Settings

The included template uses cost-capped L4 settings:

- GPU: `nvidia-l4`
- GPU count: `1`
- vLLM resources: `8 CPU`, `32Gi` memory
- API resources: `1 CPU`, `1Gi` memory
- minimum instances: `0`
- maximum instances: configurable, default `1`
- concurrency: configurable, default `8`
- startup CPU boost: enabled
- CPU throttling: disabled, required for GPU services
- GPU zonal redundancy: disabled for lower GPU-second cost

Use `max instances = 1` while testing so a bad loop cannot fan out multiple L4 instances.

## Deploy From Colab

Open `notebooks/deploy_cloud_run_colab.ipynb` in Google Colab and run the cells from top to bottom. The notebook will:

1. Authenticate you to Google Cloud.
2. Enable required APIs.
3. Clone this GitHub repo.
4. Build the FastAPI gateway image with Cloud Build.
5. Render `cloudrun/service.template.yaml`.
6. Deploy the multi-container Cloud Run service with the Gemma vLLM sidecar.
7. Optionally make the service public while still requiring your API key.
8. Send a test request.

## API Example

```bash
export OPENWEIGHTAI_URL="https://YOUR_SERVICE_URL"
export OPENWEIGHTAI_API_KEY="YOUR_API_KEY"

curl -sS "$OPENWEIGHTAI_URL/v1/profile/answer" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $OPENWEIGHTAI_API_KEY" \
  -d '{
    "profile": {
      "name": "Maya",
      "age": 34,
      "likes": ["coffee", "gardening"],
      "income": "$72,000 per year",
      "state": "California"
    },
    "question": "What is your salary?",
    "max_tokens": 120,
    "temperature": 0.1
  }'
```

Example response:

```json
{
  "answer": "$72,000 per year",
  "source": "profile",
  "confidence": 1.0,
  "used_profile_fields": ["income"],
  "model": "google/gemma-4-E2B-it",
  "latency_ms": 842,
  "raw_text": null,
  "usage": {
    "prompt_tokens": 200,
    "completion_tokens": 30,
    "total_tokens": 230
  }
}
```

## Raspberry Pi Client

Install the only client dependency:

```bash
python3 -m pip install requests
```

Run:

```bash
export OPENWEIGHTAI_URL="https://YOUR_SERVICE_URL"
export OPENWEIGHTAI_API_KEY="YOUR_API_KEY"
python3 examples/raspberry_pi_client.py "To show you are paying attention, please select B."
```

## Notes On Cost And Cold Starts

Minimum instances set to `0` keeps idle cost down, but it does not keep a warm GPU. If Cloud Run scales to zero, the next request must start a new GPU instance and load the model. The Cloud Run GPU itself becomes available quickly, but model loading is still the slow part.

For a cheap personal setup:

- Keep `MAX_INSTANCES=1` until you trust the service.
- Use short prompts and `max_tokens` values.
- Call `/warmup` only when you are about to use the model. Scheduled warmups reduce latency but also create billable GPU uptime.
- Delete the service when you are done testing:

```bash
gcloud run services delete openweightai --region us-central1
```

## References

- Gemma 4 model overview: `https://ai.google.dev/gemma/docs/core`
- Gemma 4 Hugging Face inference guide: `https://ai.google.dev/gemma/docs/core/huggingface_inference`
- Cloud Run GPU configuration: `https://docs.cloud.google.com/run/docs/configuring/services/gpu`
- Cloud Run GPU inference best practices: `https://docs.cloud.google.com/run/docs/configuring/services/gpu-best-practices`
