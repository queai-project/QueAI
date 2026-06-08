<!--
Thanks for contributing. Summarize the change in the first block;
the rest of the template is a checklist you confirm before asking
for review.

Things that DON'T belong in a PR (open an issue first):
- Product-direction changes (see docs/PRODUCTVISION.md).
- Massive refactors without prior discussion.
- Adding a module to the official registry (use the "Plugin proposal" template).
-->

## What changes and why

<!--
Explain the why. The what is already in the diff.
If it answers an issue, reference it with "Closes #123" or "Refs #123".
-->

## How to test it

<!--
Concrete steps for the reviewer to reproduce the effect.
If you added automated tests, point out which ones exercise your change.
-->

## Screenshots / output

<!-- Optional. Useful for user-visible changes. -->

## Checklist

- [ ] `ruff check .` passes locally.
- [ ] `python manage.py test` passes locally.
- [ ] If there's a logic change, I added (or adjusted) automated tests.
- [ ] If there's a model change, I generated and committed the migration (`makemigrations`).
- [ ] If I touched a REST endpoint, I updated `docs/API_REFERENCE.md`.
- [ ] If I touched env vars, I updated `.env.example`.
- [ ] I didn't include real secrets or `.env` files in the diff.
- [ ] I read and followed [CONTRIBUTING.md](../CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md).

## Notes for the reviewer

<!-- Any extra context, design decisions you'd like to discuss, doubts. -->
