# Hermes Nosso — Provider Registry

This registry describes external providers and how Hermes Nosso must decide whether they are directly executable from the runtime.

## Provider activation contract

A provider is DIRECT only when its required runtime credential/tool is actually present.
A provider is EXTERNAL when it is connected outside the Hermes container (for example through a host/MCP integration) but not exposed to the container.
A provider is UNAVAILABLE when neither direct credentials nor an external execution path exist.

Never claim DIRECT execution merely because the user's account is connected somewhere else.

## Runway

Purpose:
- text-to-video
- image-to-video
- video editing
- multishot video
- image generation/editing
- music / sound effects / speech

Runtime activation:
- DIRECT when `RUNWAY_API_KEY` (or a future registered Runway runtime tool) is available.
- EXTERNAL when a Runway MCP/tool is available to the host orchestrator but no runtime credential is present.
- otherwise UNAVAILABLE.

Routing:
- ordinary AI video -> Runway first when DIRECT/EXTERNAL executor is actually callable.
- technical/math explainer -> `manim-video` remains the local fallback.
- never substitute image output for requested video.

## Vercel

Purpose:
- preview and production web deployment
- project/deployment inspection
- runtime/build logs

Runtime activation:
- DIRECT when `VERCEL_TOKEN` is available together with the relevant project/team context.
- EXTERNAL when a Vercel MCP/tool is available to the host orchestrator.
- otherwise UNAVAILABLE.

Environment variables recognized:
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID` or `VERCEL_TEAM_ID`
- `VERCEL_PROJECT_ID` when a single project is intentionally pinned

Routing:
- website implementation happens locally/repository-first.
- use Vercel only for deployment/inspection when callable.
- never default every website request to one unrelated existing Vercel project.

## Supabase

Purpose:
- Auth
- Data API
- Storage
- Realtime
- database/schema/backend workflows

Runtime activation:
- FRONTEND/DATA API access when `SUPABASE_URL` + `SUPABASE_PUBLISHABLE_KEY` are present.
- privileged backend/admin access only when a proper backend secret/integration exists.
- EXTERNAL management when a Supabase MCP/tool is exposed by the host orchestrator.

Recognized variables:
- `SUPABASE_URL` or `HERMES_SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY` or `HERMES_SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_PROJECT_REF` or `HERMES_SUPABASE_PROJECT_REF`

Security:
- publishable key may be used for client/Data API workflows protected by RLS.
- never expose or embed `service_role` / secret keys in generated frontend code.
- privileged operations must use a secure backend/MCP path.

## GitHub

DIRECT when authenticated GitHub CLI/tool is present.
EXTERNAL when host GitHub integration is available.
Use the specific GitHub skill selected by the router.

## OpenAI / Hermes model providers

Current Hermes runtime model access remains configured through the existing OpenAI-compatible / Matrix / Hermes bridge configuration.
Do not alter the working chat-model path merely to add creative/deployment providers.

## Detection pseudocode

At task time:

1. inspect available tools/providers;
2. inspect relevant environment variable *presence*, never print secret values;
3. classify provider as DIRECT / EXTERNAL / UNAVAILABLE;
4. execute only through a callable path;
5. if unavailable, use same-artifact fallback if one exists;
6. otherwise explain the missing provider succinctly.

## Current orchestration observations

The host environment has authenticated integrations available for Runway, Vercel and Supabase.
This does not automatically grant those credentials to the Hermes Cloud container.
Hermes Cloud should treat them as EXTERNAL unless the host exposes the integration during that request or runtime credentials are later provisioned.
