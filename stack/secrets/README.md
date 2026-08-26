# Runtime secrets

`scripts/init-secrets.sh` creates `grafana_admin_password.txt` here with mode `0600`.
The password file is intentionally ignored by Git and must never be committed.

For a production deployment, replace this local file workflow with a managed
secret store such as Azure Key Vault and rotate credentials regularly.
