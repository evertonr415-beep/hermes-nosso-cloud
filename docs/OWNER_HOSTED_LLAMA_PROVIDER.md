# Optional owner-hosted Llama provider

This is an opt-in integration path for a model hosted by the project owner. It
is deliberately not enabled by default and must not replace the current Groq
configuration.

## Current prerequisites

- The owner-controlled bridge is reachable at an HTTPS URL.
- The bridge implements the OpenAI-compatible `POST /v1/chat/completions`
  contract and accepts `Authorization: Bearer <key>`.
- The bridge forwards only to the local Ollama API; do not expose port 11434
  directly.
- The owner has configured access controls (prefer Cloudflare Access in
  addition to the bearer token), request limits, and timeouts.
- The computer, Ollama, bridge, and tunnel must be running. This provider is
  not an always-on cloud model.

The current test bridge described during setup exposes `/api/chat`, not
`/v1/chat/completions`. Do not point the Hermes router at it until the
OpenAI-compatible route has been implemented and tested. The router sends a
Chat Completions JSON body and expects `choices[0].message.content` in return.

## Render environment — configure only after the bridge adapter is tested

Keep the existing `HERMES_INFERENCE_MODE=groq` and Groq settings unchanged.
Add the bridge key as a secret environment variable named
`HERMES_LLAMA_BRIDGE_KEY`. Never put its value in GitHub, frontend code, logs,
or this document.

Set these non-secret values only when explicitly enabling the provider:

```text
HERMES_GLOBAL_ROUTER_ENABLED=1
HERMES_GLOBAL_ALLOWED_PROVIDERS=llama-local
HERMES_GLOBAL_PROVIDERS_JSON=[{"id":"llama-local","url":"https://llama.sistemavotoforte.com.br/v1/chat/completions","model":"llama3.2:3b","api_key_env":"HERMES_LLAMA_BRIDGE_KEY","priority":0,"max_tokens":256,"timeout":8}]
```

The router's provider configuration requires HTTPS, a provider ID in the
allowlist, and a non-empty secret named by `api_key_env`. These settings alone
do not make the Llama the default provider: the existing web entry point must
explicitly select `provider_id="llama-local"` or add a separately reviewed
opt-in mode. Do not change `HERMES_INFERENCE_MODE` from `groq` as part of the
first test.

## Safe rollout sequence

1. Implement and test the bridge's OpenAI-compatible route locally.
2. Test HTTPS, authentication, request limits, and a no-auth 401 response.
3. Run `python -m unittest discover -s tests -p 'test_owner_hosted_provider.py' -v`.
4. Review the pull request and all CI results.
5. Only then add Render secrets/configuration and use an explicitly enabled
   test route. Keep Groq as the normal route and fallback.
6. Confirm offline/timeout fallback before enabling for normal chat.

Never send restricted/private prompts to an owner-hosted endpoint unless the
owner has explicitly reviewed and approved that data flow. The owner-hosted
computer may be offline and is not guaranteed to be available.
