# Hermes worldwide expansion — operational prerequisites

Existing Hermes is deployed to Railway region sfo. Existing memory volume and backup buckets are not globally replicated. The Supabase project in us-east-2 is a separate fault domain but not a global replica.

New provider endpoints must be explicitly authorized, reachable over HTTPS, and configured by environment variables. Never discover, consume, or self-provision unrelated nodes. Do not bypass resource or account limits. Cap cost, concurrency and retry attempts.

The memory database has a private encrypted-record schema. Automatic synchronization is disabled until the backend integration can authenticate and encrypt records safely. Prompt-sourced text and retrieved memory must be treated as untrusted content.

Use mTLS only where both endpoints explicitly support client certificates. TLS-only APIs must not be labeled mTLS.
