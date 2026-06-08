# Security Policy

Thanks for helping keep QueAI safe for its users.

## Supported versions

| Version | Security support |
|---|---|
| `1.x` (`main` branch) | ✅ actively maintained |
| `< 1.0` (release candidates) | no retroactive guarantee — please upgrade to the latest tag |

## How to report a vulnerability

**Do not open a public issue** for security vulnerabilities.

Use one of these channels (in order of preference):

1. **GitHub Private Vulnerability Reporting** —
   https://github.com/queai-project/QueAI/security/advisories/new
2. **Email** — `security@queai.dev`

Please include at least:
- Kernel and plugin versions involved (`queai health`,
  `git rev-parse HEAD`).
- Reproduction steps.
- Observed or expected impact (unauthorized read/write, RCE,
  privilege escalation, etc.).
- Your availability to coordinate disclosure.

## What to expect

- **Acknowledgement within 72 h** of submission.
- **Triage within 7 days**: we confirm whether it's an issue, its
  estimated severity and a target fix date.
- **Coordinated disclosure**: we work on a private fix and credit
  you when publishing the security advisory and the patched
  version, unless you prefer to stay anonymous.
- If **30 days pass** without a response from our side, you're
  free to disclose — but that's not the goal; we want to resolve
  it before then.

## What we consider in-scope

- Vulnerabilities in the kernel code (`core/`,
  `module_manager/`, `marketplace/`, `system_monitor/`, `cli/`).
- Vulnerabilities in the REST API `/api/v1/*`.
- Vulnerabilities in the installation chain (`install.sh`).
- Defects in the auth / session / token flow.
- Undocumented risks of the Docker socket integration.

## What we consider out-of-scope

- Vulnerabilities in individual plugins (report to the plugin's
  maintainer; list is in `register.json`).
- Issues requiring physical access to the host.
- Attacks requiring valid kernel operator credentials (DoS via
  legitimate load, intentional abuse).
- Insecure configurations explicitly discouraged in
  [`docs/SECURITY.md`](docs/SECURITY.md) (e.g., `DEBUG=True` in
  production).

## Security model and recommendations

Technical detail (attack surface, applied mitigations and
recommended configuration per environment) lives in
[`docs/SECURITY.md`](docs/SECURITY.md).

## Bug bounty

QueAI does not offer monetary rewards. It does offer public credit
in the changelog and the published security advisory, unless you
prefer to remain anonymous.
