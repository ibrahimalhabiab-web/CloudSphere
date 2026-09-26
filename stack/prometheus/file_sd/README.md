# Generated GitLab scrape targets

The repository contains empty `gitlab-metrics.yml`, `gitlab-node.yml`, and `gitlab-health.yml` target lists so Prometheus starts cleanly before Azure addresses exist. `scripts/deploy-azure.sh` replaces the remote copies with Terraform's private GitLab address. Do not commit live target addresses.

For a local presentation, copy the examples below and replace the address:

```yaml
# gitlab-metrics.yml
- targets: ["10.42.2.4:80"]
  labels:
    role: gitlab-application
```

```yaml
# gitlab-node.yml
- targets: ["10.42.2.4:9100"]
  labels:
    role: gitlab-host
```

```yaml
# gitlab-health.yml
- targets: ["http://10.42.2.4/-/health"]
  labels:
    role: gitlab-application
```
