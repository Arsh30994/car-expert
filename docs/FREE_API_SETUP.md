# Free AI API key for local testing

You must create your own key in your own account. There is no safe universal/shared API key that I can issue or put into your repository. Never commit a real key to GitHub or paste it into chat.

## Recommended quick option: OpenRouter free models

1. Create an account at https://openrouter.ai/
2. Open https://openrouter.ai/settings/keys and create an API key.
3. Copy it once and keep it private.
4. The current Car Expert AI code uses the OpenAI-compatible client, so configure the existing legacy AIMLAPI environment variable names like this in your local, untracked `.env` file:

```dotenv
AIMLAPI_API_KEY=your_openrouter_key_here
AIMLAPI_BASE_URL=https://openrouter.ai/api/v1
AIMLAPI_MODEL=google/gemma-4-26b-a4b-it:free
AIMLAPI_VISION_MODEL=google/gemma-4-26b-a4b-it:free
```

The model above is currently listed as a free multimodal model supporting text, images and video input. Free model capacity and availability can change. OpenRouter currently documents free-model limits of 20 requests/minute and 50 requests/day; failed requests may count toward the daily allowance. Check current limits before a demo:
- https://openrouter.ai/collections/free-models
- https://openrouter.ai/docs/limits

5. Restart Django after changing `.env`.
6. Sign in and test a text prompt first, then test an image. The current repository's upload endpoint only supports JPG, JPEG, PNG, WebP and GIF. PDF, audio and video extraction pipelines are not implemented yet, so an API key will not make those upload types work.

## Alternative: Google AI Studio / Gemini API

Create a key at https://aistudio.google.com/app/apikey. Google offers a free tier for selected models with model-specific quotas and limits. Check the current pricing and rate-limit pages:
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/rate-limits

The current repository uses an OpenAI-compatible client and does not directly call Gemini's native API. Use OpenRouter for the fastest setup with the existing code, or implement a dedicated Gemini provider adapter before using a Gemini key.

## Security checklist

- Keep `.env` local; verify it is in `.gitignore`.
- Do not add keys to frontend JavaScript, React environment variables exposed to browsers, screenshots, README files or test fixtures.
- Use separate keys for local development and deployment.
- Set provider spend/rate limits where available.
- Revoke a key immediately if it is exposed.
- Do not upload real customer registration, insurance or identity documents to free-tier services without reviewing their data-use terms.
