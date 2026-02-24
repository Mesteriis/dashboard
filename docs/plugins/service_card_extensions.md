# Service Card Extensions (v1)

`ServiceItemCard` uses a fixed core contract:

- `id`
- `title`
- `url`
- `check_url` (optional in YAML, defaults to `url`)
- `tags`
- `open`
- `type`

Plugin UI is attached through `plugin_blocks` (declarative, versioned):

```yaml
groups:
  - id: core
    subgroups:
      - id: main
        items:
          - id: grafana
            title: Grafana
            type: link
            url: https://grafana.local
            check_url: https://grafana.internal/health
            open: new_tab
            tags: [observability]
            plugin_blocks:
              - plugin_id: metrics
                version: v1
                title: Metrics
                elements:
                  - id: uptime
                    kind: text
                    label: Uptime
                    value: "99.98%"
                  - id: slo
                    kind: badge
                    value: SLO met
                    tone: success
                  - id: runbook
                    kind: link
                    label: Runbook
                    url: https://wiki.local/runbook/grafana
                    open: new_tab
```

Supported element kinds:

- `text`
- `badge`
- `link`
- `html`

Security defaults:

- Plugin code is never executed in browser.
- `html` is rendered only when `trust=server_sanitized_v1`; otherwise it is denied.
- Unknown element kinds are ignored.
