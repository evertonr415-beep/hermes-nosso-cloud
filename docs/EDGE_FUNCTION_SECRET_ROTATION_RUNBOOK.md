# Hermes Edge Function Secret Rotation Runbook

Status: prepared for a coordinated maintenance window; **not executed in production**.

## Why this is required

The deployed source of `hermes-auth` and `hermes-profile` contains hardcoded shared authentication material. Treat those values as compromised. The `hermes-auth` function also has a separate hardcoded bootstrap credential. Do not copy the old values into issues, logs, Git, or chat.

## Preconditions

- Identify every caller of the two functions, including any frontend or repository outside this repo. The current repository search did not establish all callers.
- Confirm access to the Supabase project dashboard and the deployed app's secret/configuration controls.
- Prepare a maintenance window and a rollback plan. Do not rotate just one side of the shared header check.
- Generate fresh, independent, high-entropy values for the app-auth secret and bootstrap secret. Never reuse either value for another purpose.

## Coordinated migration

1. Open [Supabase Edge Function Secrets](https://supabase.com/dashboard/project/aufsewqtybpothlrsjij/functions/secrets).
2. Add managed secrets named `HERMES_APP_SECRET` and `HERMES_BOOTSTRAP_SECRET`. Do not paste their values into Git or chat.
3. Prepare a reviewed function version in which both functions read `HERMES_APP_SECRET` from `Deno.env`; `hermes-auth` must also read `HERMES_BOOTSTRAP_SECRET`. Validate that missing/empty secrets fail closed. Do not deploy until all callers are ready to use the new app-auth secret.
4. Update each caller to read the matching secret from its own server-side secret store and continue sending the expected headers. Never put either secret in browser JavaScript or a public client bundle.
5. Deploy the caller and both Edge Functions in a coordinated sequence that avoids an interval where valid users cannot authenticate. If the platform cannot provide an atomic cutover, use a brief maintenance window.
6. Verify, without logging credentials:
   - valid login succeeds;
   - invalid app-auth header is rejected;
   - valid session verification and logout work;
   - profile read and preference/character writes work for the authenticated user only;
   - bootstrap is rejected without the bootstrap secret and remains one-time only;
   - unrelated password-reset and encrypted-memory flows still work.
7. Review function logs for unexpected 401/403/5xx responses. Logs must not include secret values, request passwords, or session tokens.
8. After successful validation, remove the old hardcoded values from all deployed versions and revoke/rotate any other credential that reused them. Record only the rotation timestamp and test outcomes.

## Stop conditions

- Do not deploy a function version that expects managed secrets until those secrets are configured.
- Do not rotate the server-side functions without locating and updating all callers.
- Do not disable authentication checks as a workaround.
- If login/profile tests fail, stop the rollout and restore a known-good coordinated version; do not reintroduce the exposed literals as a long-term fix.

## Separate Auth hardening

Leaked-password protection is a Supabase Auth setting, separate from Edge Function secrets. Enable it through the Auth dashboard only after reviewing the impact on signup/password-change flows, then test both flows. Do not claim it is enabled until the dashboard setting and behavior are verified.
