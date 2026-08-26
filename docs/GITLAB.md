# GitLab Integration

The root `.gitlab-ci.yml` validates every push and merge request without connecting to Azure or changing infrastructure.

## Pipeline checks

- `terraform_validate`: checks Terraform formatting, initializes providers without a backend, and validates the configuration.
- `shellcheck`: checks all Bash automation scripts.
- `python_and_dashboard`: checks the Python demo application and Grafana dashboard JSON syntax.
- `compose_validate`: validates the Docker Compose model using a temporary CI-only password file.
- `secret_detection`: uses GitLab's maintained analyzer to detect committed secrets.

## Create and connect a GitLab project

1. In GitLab, create a blank project without initializing it with a README.
2. Copy the project's HTTPS or SSH clone URL.
3. From this project directory, run:

   ```bash
   git init -b main
   git add .
   git status
   git commit -m "Add monitoring platform and GitLab CI"
   git remote add origin GITLAB_REPOSITORY_URL
   git push -u origin main
   ```

4. In GitLab, open **Build > Pipelines** and confirm all jobs pass.

## Secret handling

Never commit any of the following:

- `terraform/terraform.tfvars`
- Terraform state or plan files
- `.env`
- `stack/secrets/grafana_admin_password.txt`
- SSH private keys
- Azure credentials or GitLab access tokens

The `.gitignore` excludes these files. If deployment is added later, store Azure credentials and SSH material as protected, masked GitLab CI/CD variables. Keep deployment manual and limited to protected branches or environments.
