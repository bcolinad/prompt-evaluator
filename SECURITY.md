# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

Only the latest release on the `main` branch receives security updates.

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it **responsibly** by emailing:

**bcolinad@gmail.com**

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce the issue
- Any relevant logs, screenshots, or proof-of-concept code
- Your suggested fix, if you have one

**Do not open a public GitHub issue for security vulnerabilities.** Public disclosure before a fix is available puts all users at risk.

### Response Timeline

| Action                          | Target       |
|---------------------------------|--------------|
| Acknowledgement of your report  | 72 hours     |
| Initial assessment              | 7 days       |
| Patch release (if confirmed)    | 30 days      |

We will credit reporters in the release notes unless anonymity is requested.

## Scope

This policy covers the code in this repository, including:

- The LangGraph agent pipeline (`src/agent/`)
- The Chainlit application (`src/app.py`)
- Evaluation logic (`src/evaluator/`)
- Database layer and migrations (`src/db/`, `alembic/`)
- Docker and infrastructure configuration (`docker-compose*.yml`, `Dockerfile*`)
- Authentication and session handling (`src/config/settings.py`, auth-related modules)

### Out of Scope

- Third-party dependencies (report upstream to the respective maintainer)
- LangSmith, Anthropic, Google, or Ollama hosted services
- Vulnerabilities that require physical access to the host machine
- Social engineering attacks

## Security Best Practices for Deployers

### Secrets and API Keys

- **Never commit secrets** to version control. Use `.env` files (excluded via `.gitignore`) or a secrets manager.
- Rotate `AUTH_SECRET_KEY` before any production deployment; the `.env.example` value is intentionally insecure.
- Restrict API key permissions to the minimum required scope (LangSmith, Google Cloud, Anthropic).

### Database

- Change the default PostgreSQL credentials (`postgres:postgres`) before exposing the service.
- Use SSL/TLS connections to PostgreSQL in production (`?sslmode=require` in `DATABASE_URL`).
- Apply the principle of least privilege for database roles.

### Network and Deployment

- Run the Chainlit server behind a reverse proxy (e.g., Nginx, Caddy) with TLS termination.
- Do not expose PostgreSQL, pgAdmin, or Ollama ports to the public internet.
- Use Docker network isolation to restrict container-to-container communication to only what is necessary.
- Set `APP_ENV=production` and `LOG_LEVEL=WARNING` in production to avoid leaking sensitive information in logs.

### Authentication

- Enable authentication (`AUTH_ENABLED=true`) in any publicly accessible deployment.
- Use strong, unique passwords for admin accounts.
- Rotate `AUTH_SECRET_KEY` periodically.

### Document Uploads

- Enforce `DOC_MAX_FILE_SIZE` to prevent denial-of-service via large file uploads.
- Validate and sanitize uploaded file content before processing.

## Disclaimer

This project is provided under the **MIT License**, which includes the following relevant clause:

> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

The maintainers make a good-faith effort to address reported vulnerabilities, but **no guarantee of security is provided**. Users are responsible for securing their own deployments, including proper configuration of secrets, network access, and infrastructure.
