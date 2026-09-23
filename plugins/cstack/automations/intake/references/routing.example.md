# Routing map example

Copy this file to <code>.github/cstack/intake/routing.md</code> and replace every placeholder. Point `routing.map_path` at the copy. Pack refreshes must not overwrite it.

The triage run treats this as data. A route needs evidence from the report or cause trace. A keyword match alone is not enough.

Follow [the Codex runtime contract](../../../skills/cstack/references/codex-runtime.md).

```yaml
routes:
  - name: "billing-example"
    match:
      product_areas:
        - "billing-area-placeholder"
      code_paths:
        - "billing-code-path-placeholder"
      error_signatures:
        - "billing-error-placeholder"
    destination:
      source_channel: ""
      tracker_team: "billing-team-placeholder"
    owners:
      - "billing-owner-placeholder"
    allow_feature_owner_ping: false

  - name: "desktop-example"
    match:
      product_areas:
        - "desktop-area-placeholder"
      code_paths:
        - "desktop-code-path-placeholder"
      error_signatures:
        - "desktop-error-placeholder"
    destination:
      source_channel: ""
      tracker_team: "desktop-team-placeholder"
    owners:
      - "desktop-owner-placeholder"
    allow_feature_owner_ping: false

fallback:
  destination: ""
  owners: []
  allow_feature_owner_ping: false

ping_policy:
  default: "off"
  allow:
    - "configured-feature-owner"
    - "confirmed-regression-author"
  deny:
    - "broad-on-call-group"
    - "unverified-owner"
```

## Rules

- Leave `fallback.destination` empty unless one team accepts all unmatched reports.
- Use stable product areas, code paths, and error signatures.
- Do not include private data in a public copy.
- Do not paste raw user or channel IDs into an example that will be published.
- Keep feature-owner pings off until the target team agrees to them.
- A reroute tells the reporter where to go. The automation never cross-posts.
