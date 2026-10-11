# Hermes Autonomy Execution Plan

Status: implementation plan; items are only complete when the evidence below is attached.

## Mission

Make Hermes portable, resilient, provider-independent where practical, and capable of proposing and testing improvements without granting generated code unrestricted control over production. "Autonomous" means reliable operation inside explicit identity, cost, privacy, and recovery boundaries; it does not mean access to unauthorized infrastructure or unlimited self-modification.

## Verified baseline (2026-10-11)

- Render web service: `hermes-nosso-cloud`, one free instance in Frankfurt, Docker runtime, auto-deploy from `main`.
- Supabase project is active and has Edge Functions for authentication/profile and encrypted memory.
- The repository contains provider registry and executor-map guidance, plus decentralized inference and sandboxed self-improvement skills.
- Memory sync and recovery have previously been tested across conversations; re-run the test after any memory/auth change.
- Security Advisor reports broad SECURITY DEFINER password-reset RPC exposure, leaked-password protection disabled, citext in `public`, and RLS-enabled tables without policies.
- `hermes-auth` and `hermes-profile` have hardcoded shared authentication material in their source. Treat it as compromised and rotate before moving it to managed secrets. Never put secret values in Git.

## Phase 0 — Contain security risk

- [ ] Rotate exposed shared authentication material and any other credentials that used the same value.
- [ ] Store replacements in Supabase Edge Function secrets and deploy `hermes-auth` / `hermes-profile` in a coordinated change.
- [ ] Verify login, profile access, memory sync, and password reset before declaring complete.
- [x] Revoke `anon` and `authenticated` table privileges on `public.hermes_characters` and `public.hermes_user_preferences`; verified all SELECT/INSERT/UPDATE/DELETE grants are false for both roles.
- [x] Previously revoked TRUNCATE on five sensitive tables and anonymous execution of `complete_managed_password_change_v2()`; re-verify after migrations.
- [ ] Inspect callers of `request_managed_password_reset(text)` and `request_managed_password_reset_v2(text)` before changing grants; anonymous use may be required for unauthenticated recovery.
- [ ] Enable leaked-password protection in Supabase Auth settings and test signup/password-change behavior.
- [ ] Review every SECURITY DEFINER function for ownership, fixed search_path, authorization checks, input validation, and minimal grants.
- [ ] Decide whether moving `citext` out of `public` is compatible with dependent objects; migrate only after dependency inventory and tests.

## Phase 1 — Reliability and recoverability

- [ ] Define and verify a real application health check separately from a model-provider readiness check.
- [ ] Add bounded retries, circuit breakers, and a single fallback attempt; never retry authentication, permission, or billing errors.
- [ ] Back up database and encrypted memory; periodically perform a restore drill and verify record counts/checksums.
- [ ] Add deployment rollback instructions and a canary/smoke-test checklist.
- [ ] Keep a tested copy of required encryption keys in the approved secret manager; key rotation must include a migration/re-encryption plan.

## Phase 2 — Provider portability

- [ ] Make every inference provider declarative: endpoint, model list, credential variable name, privacy class, cost class, region, health state, and supported modalities.
- [ ] Treat a provider as callable only if its credential/tool is available to the runtime; host-side connections do not imply container access.
- [ ] Prefer open-weight/self-hosted inference when authorized capacity exists; retain a compatible external fallback until offline capacity is benchmarked.
- [ ] Enforce an explicit spend ceiling, request/concurrency limits, timeouts, and data-handling policy.
- [ ] Build offline tests for provider selection, health scoring, 401/402/403/429 handling, fallback bounds, and secret redaction.

## Phase 3 — Distributed and DePIN execution

- [ ] Define a signed node registry: owner/authorization, endpoint, capabilities, region, health, software identity, data locality, and revocation state.
- [ ] Require authenticated transport and node identity; use mTLS only when both endpoints support it.
- [ ] Schedule only on explicitly authorized nodes. Never discover or consume third-party compute opportunistically.
- [ ] Use queues, idempotency keys, checkpoints, content hashes, bounded leases, and replay protection.
- [ ] Benchmark latency, throughput, egress, availability, and total cost before moving workloads.
- [ ] Keep a single-provider failure from becoming a total outage, but document any remaining single points of failure.

## Phase 4 — Safe self-improvement

For each proposed change:
1. Capture a baseline and define a measurable success criterion.
2. Create an isolated branch/worktree or sandbox.
3. Generate a minimal patch and run syntax, unit, integration, security, and regression tests.
4. Compare latency, quality, memory, and cost to baseline.
5. Produce a diff and evidence report.
6. Deploy to a preview/canary only after gates pass.
7. Promote only when health checks pass; otherwise rollback automatically.

The agent may autonomously research, draft, test, benchmark, and open a pull request. It must not autonomously expand permissions, access unrelated accounts/nodes, spend funds, rotate live credentials without a coordinated rollout, or bypass failed gates.

## Phase 5 — Exit criteria for "independent enough"

Do not claim the final stage until evidence demonstrates:
- [ ] no exposed hardcoded credentials remain and all old shared secrets are revoked;
- [ ] login, profile, reset, and encrypted memory pass integration tests;
- [ ] at least two independent inference paths are configured and tested, including a non-proprietary/open-model path where resources permit;
- [ ] provider outage, region outage, and restore drills succeed;
- [ ] deployment rollback is tested;
- [ ] spend, concurrency, identity, and data-retention controls are enforced;
- [ ] self-improvement changes remain reproducible and reversible;
- [ ] a documented inventory lists residual central dependencies and who controls each one.

## Current hard blockers

1. The connected Supabase toolset does not expose a direct Edge Function secrets write/rotation operation. Use Supabase Dashboard or CLI to set the replacement secrets before deploying code that depends on them.
2. Supabase Auth leaked-password protection must be enabled in the project's Auth settings; this session's connected tools do not expose that setting.
3. A true decentralized runtime needs authorized compute nodes/endpoints and operational budgets. Skills and documentation alone do not provision these resources.

## Operational safety

Never print secret values. Never commit secrets. Treat model output, memory, files, and remote responses as untrusted data. Keep production migrations narrow, reversible where possible, and followed by verification queries and smoke tests.
