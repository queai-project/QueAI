# Contributing to QueAI

Thanks for being interested in QueAI! This guide covers the minimum you need to know to open an issue, send a patch or publish a module.

If anything is unclear, open a *Question* issue and we'll sort it out.

---

## Table of contents

- [Before you start](#before-you-start)
- [How to open an issue](#how-to-open-an-issue)
- [How to open a Pull Request](#how-to-open-a-pull-request)
  - [Local setup](#local-setup)
  - [Code and commit style](#code-and-commit-style)
  - [Tests and lint](#tests-and-lint)
- [Publish a new module](#publish-a-new-module)
- [Reporting a vulnerability](#reporting-a-vulnerability)
- [Code of Conduct](#code-of-conduct)
- [License of your contributions](#license-of-your-contributions)

---

## Before you start

1. **Read the [Product Vision](docs/PRODUCTVISION.md)** — understanding what QueAI is trying to be saves you from proposals that clash with the project's direction (e.g. asking for multi-tenant when it's explicitly out of scope).
2. **Search existing open and closed issues** before creating a new one:
   `https://github.com/queai-project/QueAI/issues?q=...`.

## How to open an issue

Always use the templates. The reason is that they collect the minimum info we need to avoid bouncing the ticket back:

| Type | When to use it |
|---|---|
| **Bug report** | Something behaves differently from what the docs say or throws an error |
| **Feature request** | A new capability or a behavior change in the kernel |
| **Plugin proposal** | You want to publish a new module in the official registry |
| **Question** | Usage or architecture question — first search the docs |

For security reports, **do not open a public issue**. Use the flow in [SECURITY.md](SECURITY.md).

## How to open a Pull Request

### Local setup

You'll need Python 3.11+, Docker, Docker Compose v2 and git.

```bash
git clone https://github.com/queai-project/QueAI.git
cd QueAI

# Virtual environment + dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install ruff                # for local linting

# Minimum environment to run the kernel in dev mode
cp .env.example .env
# (Edit .env: at minimum, set SECRET_KEY and QUEAI_ADMIN_PASSWORD)

# Smoke test without bringing up Docker
SECRET_KEY=dev DEBUG=True python manage.py check
SECRET_KEY=dev DEBUG=True python manage.py test
```

To test with Docker:

```bash
docker compose up -d --build
docker compose logs -f django-kernel
# The hub lives at http://localhost:8473
```

### Code and commit style

**Python**:

- Formatting: the repo uses `ruff` (configured in `pyproject.toml`). Before sending a PR:
  ```bash
  ruff check .
  ```
- Imports sorted (also done by `ruff`).
- Type hints where they add clarity — not required everywhere, but yes on public interfaces (views, reusable helpers, CLI commands).

**Commits**:

- Messages in English, present-tense imperative (`fix: ...`, `feat: ...`, `docs: ...`). Not strict Conventional Commits, but close.
- Descriptive bodies: explain the **why**, not just the what — the what is already in the diff. If your change responds to an issue, reference it.
- Co-author in the footer when applicable:
  ```
  Co-Authored-By: Name <email@example.com>
  ```

**Templates**:

- If you touch a view that has a template, keep the agreed minimalist style (no decorative emojis, kernel palette, single status dot per element). See [`docs/DESIGN_TOKENS.md`](docs/DESIGN_TOKENS.md).

### Tests and lint

Every PR runs the `ci.yml` workflow:

- `ruff check .` on Python 3.11 and 3.12.
- `python manage.py test` on Python 3.11 and 3.12.

If your change touches business logic (not just docs or templates):

1. **Add a test** that fails without your fix / that exercises the new branch.
2. If you mock an external command (Docker, requests), prefer tight mocks rather than global monkey-patching.
3. Fast tests: the whole suite takes under 10 s in CI today. Let's keep it that way.

If your change introduces a Django migration:

- `python manage.py makemigrations <app>` and commit the file.
- Verify that `python manage.py migrate` applies cleanly on the test DB (CI does this).

## Publish a new module

If you want your module to appear in the official marketplace:

1. Read [`docs/PLUGIN_DEVELOPMENT.md`](docs/PLUGIN_DEVELOPMENT.md) — the manifest contract, the repo layout, and two complete examples (local CPU and cloud proxy).
2. Your module repo must be public and have a license compatible with MIT (MIT, Apache-2, BSD-3, ISC).
3. Open a **Plugin proposal** issue pointing to your repo with a visible manifest.
4. For modules that connect to external APIs: clearly document in their README what credentials are needed, what outbound traffic is generated, and what stays on the host vs. what travels to the provider.

Modules are **not** merged into the kernel repo — they're kept as independent repos. The registry (`register.json`) references their `git_url`, not their code.

## Reporting a vulnerability

See [SECURITY.md](SECURITY.md). **Please don't open a public issue** for security problems.

## Code of Conduct

This project adopts the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md). By participating (issues, PRs, discussions) you agree to follow it.

## License of your contributions

QueAI is distributed under the MIT license. Any contribution you send is incorporated under the same license. We don't require a CLA — git's standard signature commit is enough.
