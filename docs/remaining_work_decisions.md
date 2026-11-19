# Remaining Work Decisions

- The CLI is the supported interface; no HTTP API is required.
- Keep the first occurrence of an exact `source + job_id` duplicate for analysis.
- Keep different IDs with the same body as review candidates rather than deleting them.
- Use title-based role classification only as metadata. Explicit backend, frontend, or fullstack titles are classified; all other titles remain `unknown` or `needs_review`.
- Keep missing experience labels as `unknown`; do not infer entry-level status from title or body text.
- Keep unmapped technology names unchanged until a reviewed canonical alias is available.

The source dataset lacks an authoritative job-role column. Consequently, role-segment comparison is limited to explicit title classifications and cannot be presented as an authoritative role-level result. The CLI returns `insufficient_sample` when a filtered request has no evidence.
