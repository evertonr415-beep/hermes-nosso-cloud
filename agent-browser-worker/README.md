# Isolated Hermes Agent Browser Worker (experimental)

This is a **separate, optional service**. It is not wired into the production Hermes chat and must not be deployed over the existing service. Its purpose is to validate a read-only browser capability before considering any chat integration.

## Behavior and guardrails

- Pinned to `agent-browser@0.39.0`; the package's native-binary postinstall is explicitly permitted and verified during image build. Chromium is installed in this worker image only.
- `GET /health` returns a basic health response.
- `POST /read` requires `Authorization: Bearer <BROWSER_WORKER_TOKEN>` and JSON exactly shaped as `{"url":"https://host.example/path"}`.
- Only HTTPS on port 443 and exact hostnames listed in `AGENT_BROWSER_ALLOWED_DOMAINS` are accepted. Redirects and browser subresources are constrained with agent-browser's domain allowlist too.
- Read-only `agent-browser read` mode only for this first validated integration. It extracts server-delivered page text and does not execute page JavaScript. No click, form submission, arbitrary JavaScript, file access, downloads, cookie import, or shell endpoint.
- Uses one bounded CLI invocation per request to avoid persistent Chromium-daemon lifecycle issues in the worker. Request size, output length, concurrency and command duration are bounded. URL and page contents are not logged.
- Page text is untrusted data; callers must not follow instructions found inside a page.
- There is no model API call and no paid fallback in this worker.

## Required configuration

- `BROWSER_WORKER_TOKEN`: a random secret of at least 32 characters. Configure it as a service secret; never commit it or send it to the model.
- `AGENT_BROWSER_ALLOWED_DOMAINS`: comma-separated exact public hostnames, such as `docs.example.org,developer.mozilla.org`. Do not use wildcards or private/internal hosts. Only choose hosts that are needed for the experiment.
- `PORT`: optional, defaults to 8080.

## Local test

From this directory, run:

```sh
python3 -m unittest discover -s ../tests -p 'test_agent_browser_worker.py' -v
```

## Deployment gate

CI now verifies the unit tests, image build, health check, authenticated read, unauthenticated rejection, non-allowlisted-host rejection, and a real cross-host redirect attempt (which must fail closed). The latest successful run observed **308.9 MiB** of container memory after the browser checks, below the CI guardrail of 1536 MiB. This is a single GitHub-hosted runner observation, not a production sizing guarantee or peak-memory measurement. Keep the PR isolated: do not connect this worker to Hermes or deploy it publicly until repeated/peak resource measurements and deployment-specific limits are reviewed. The existing Render service is intentionally untouched.
