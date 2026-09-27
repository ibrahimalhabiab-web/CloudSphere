# CloudSphere Public Access

## Purpose and security boundary

The public site is `https://www.cloudsphere-sda.online/`. It is a read-only CloudSphere status page, not the operations console.

```text
Internet
  -> Namecheap DNS: cloudsphere-sda.online -> 20.74.182.209; www -> apex
  -> Azure monitoring NSG: TCP 80 and 443 only
  -> Caddy: automatic HTTPS and an explicit route allowlist
  -> isolated public-edge Docker network
  -> dedicated CloudSphere public-only process
```

Caddy exposes only the page root, the CloudSphere avatar, `/health`, and `GET` or `HEAD` requests to `/api/public/status`. It returns `404` for the simulation controls, metrics, alerts, every other API route, and unknown paths. The upstream public process independently runs with `PUBLIC_ONLY=true`, denies every private route, and shares no Docker network with Grafana, Prometheus, Alertmanager, exporters, or the operator application. The operator console, monitoring tools, GitLab, and application port `8000` remain private. Do not create public NSG rules or DNS records for those services.

## 1. Preflight

Confirm all of the following before opening Azure ports:

- The monitoring VM owns the static public IP `20.74.182.209`.
- The updated application, `compose.yaml`, and `caddy/Caddyfile` are present in `/opt/monitoring`.
- The existing Terraform state is available before using Terraform. Do not run `terraform apply` from a fresh clone with no state; use the reviewed live NSG procedure instead.
- The private operator console still works through its approved SSH tunnel.
- Nothing else is listening publicly on ports `80` or `443` on the monitoring VM.
- Any legacy monitoring-NSG rule for direct Grafana port `3000` access is removed; Grafana now binds to loopback and is reached through SSH tunneling.

## 2. Create the Namecheap record

In Namecheap, open **Domain List > cloudsphere-sda.online > Manage > Advanced DNS**. Keep **Namecheap BasicDNS** nameservers and replace only the conflicting Namecheap parking records for `@` and `www` with these host records:

| Type | Host | Value | TTL |
|---|---|---|---|
| A Record | `@` | `20.74.182.209` | Automatic |
| CNAME Record | `www` | `cloudsphere-sda.online` | Automatic |

Do not change the nameservers or touch mail-related records. The apex hostname redirects to the canonical `https://www.cloudsphere-sda.online/` URL through Caddy.

Wait until a public resolver returns the expected address:

```bash
dig +short A www.cloudsphere-sda.online
dig +short A cloudsphere-sda.online
```

Expected result:

```text
20.74.182.209
20.74.182.209
```

Do not continue until the expected address is returned. A recently registered domain can remain unavailable while its delegation and new record propagate.

## 3. Allow only public web traffic in Azure

The Terraform opt-in is:

```hcl
public_frontend_enabled = true
public_frontend_domain  = "www.cloudsphere-sda.online"
```

It adds only TCP `80` and `443` to the monitoring NSG. Apply it only from the authoritative Terraform working directory and state. If that state is not available, create the equivalent rule against the verified monitoring NSG with Azure CLI or the Azure portal, then confirm that no application, Grafana, Prometheus, Alertmanager, exporter, SSH, or GitLab port was broadened.

## 4. Enable the public Compose profile

On the monitoring VM, set these exact values in `/opt/monitoring/.env`:

```dotenv
PUBLIC_FRONTEND_ENABLED=true
PUBLIC_DOMAIN=www.cloudsphere-sda.online
PUBLIC_APEX_DOMAIN=cloudsphere-sda.online
```

Then deploy:

```bash
cd /opt/monitoring
chmod +x scripts/*.sh
./scripts/deploy-local.sh
```

The deployment script validates the domain, activates the `public` Compose profile, starts Caddy, and leaves the normal private deployment unchanged when the switch is absent or `false`. Caddy configuration validation does not start a server or request a certificate; certificate issuance begins only when the public profile is actually started.

Check the containers without exposing credentials:

```bash
docker compose --env-file .env --profile public ps cloudsphere-public caddy
docker compose --env-file .env --profile public logs --tail=100 caddy
```

Both containers must remain running. Caddy stores certificates and account data in named volumes; never use `docker compose down -v` during deployment or troubleshooting.

## 5. Verify DNS, HTTPS, and route isolation

Run the checks from a device outside the Azure VNet:

```bash
dig +short A www.cloudsphere-sda.online
curl -fsSI https://www.cloudsphere-sda.online/
curl -fsS https://www.cloudsphere-sda.online/api/public/status
curl -sS -o /dev/null -w '%{http_code}\n' https://www.cloudsphere-sda.online/metrics
curl -sS -o /dev/null -w '%{http_code}\n' https://www.cloudsphere-sda.online/simulate/error
```

Accept only these results:

- Both DNS names resolve to `20.74.182.209`.
- HTTPS succeeds with a trusted certificate and the page returns `200`.
- `https://cloudsphere-sda.online/` redirects to `https://www.cloudsphere-sda.online/`.
- The public status response contains only service, status, uptime, and check-time fields.
- Both private-path checks return `404`.
- Public connections to ports `3000`, `8000`, `9090`, and `9093` fail.

Do not continue promoting the URL if any private route or administrative port is reachable.

## 6. Roll back public access

First disable the proxy on the monitoring VM:

```dotenv
PUBLIC_FRONTEND_ENABLED=false
```

```bash
cd /opt/monitoring
./scripts/deploy-local.sh
```

The script stops and removes both public containers but preserves Caddy's named certificate volumes. Next, remove the Namecheap `@` A record and `www` CNAME record, restore parking only if wanted, and disable the Azure public-frontend NSG rule using the same authoritative Terraform state or a reviewed Azure change. DNS caches can keep the old address visible temporarily, so also verify that HTTPS connections no longer succeed.

## Availability and cost warning

The monitoring VM is currently scheduled for Azure auto-shutdown at **23:00 Asia/Riyadh**. The public site is unavailable while that VM is stopped. A 24-hour public service requires an explicit decision to disable or change that schedule, plus approval of the additional Azure compute cost and a budget alert. Do not disable auto-shutdown as an incidental part of DNS or website deployment.
