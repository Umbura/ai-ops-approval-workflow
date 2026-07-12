# Security Policy

## Supported Version

Security updates are applied to the latest release on `main`.

## Reporting A Vulnerability

Do not open a public issue for a suspected vulnerability. Use the repository's private security-advisory channel:

https://github.com/Umbura/ai-ops-approval-workflow/security/advisories/new

Include the affected component, reproduction steps, impact, and any proposed mitigation. Do not include real API keys, personal data, or production credentials.

## Deployment Scope

The default Compose configuration is intended for local evaluation. Before external deployment:

- replace all development secrets;
- terminate TLS at a trusted reverse proxy;
- restrict n8n editor access;
- use managed identity and role-based authorization;
- move persistence to a managed database with backups;
- configure centralized logs, metrics, and alerting.
