---
id: github-cicd
name: GitHub CI/CD & Releases
category: devops
default: true
description: Standard git conventions, Conventional Commits, SemVer, and documentation rules
---
## GitHub CI/CD & Release Management

### Repository Setup (new projects only)
- Initialize Git with default branch `main`.
- Add a remote only when the user supplies the URL. Never invent one.
- Commit `.agents/` so the toolkit is reproducible. Add `.ag-kit-backups/`, `.env`, and build output to `.gitignore`.

### CI/CD
Create or change workflows only during project setup, when asked, or when the task requires it. Workflows must:
- Run lint, format check, type check, tests, and a production build on pull requests and pushes to `main`.
- Include dependency review and vulnerability scanning.
- Use caching, set least-privilege `permissions:` (default `contents: read`), and keep secrets in GitHub Secrets.
- Pin third-party actions to a full commit SHA.
- Publish releases (changelog plus artifacts) only when a version tag is pushed. Pushing a tag is a remote operation (see below).
- Be documented in `docs/ci-cd.md`, linked from `README.md`.

Never commit secrets. Never bypass, skip, or weaken failing checks. Never release a broken build.

### Commits
- Use Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `ci:`; append `!` for breaking changes).
- Commit locally after a task passes verification. Each commit is one logical change, and no commit has failing checks unless the user asks for a WIP commit.
- Prefer a local branch (`feat/<slug>`, `fix/<slug>`) for multi-step work.
- Never amend, rebase, or squash commits that may already exist on a remote.

### Versioning (SemVer)
Change the version only when the user asks to prepare a release.

| Change since last release | Bump (≥ 1.0.0) | Bump (0.x) |
|---|---|---|
| Breaking change | MAJOR | MINOR |
| New feature | MINOR | MINOR or PATCH |
| Bug fix | PATCH | PATCH |
| Only docs, tests, CI, or refactor | No release needed | No release needed |

Update `CHANGELOG.md` (Keep a Changelog format) as part of the release commit.

### Remote Operations & Authorization
Local commits and local repository maintenance need no approval. These need explicit user authorization **each time**:
- `git push` of any kind, including tags; opening or merging pull requests.
- Creating GitHub releases, publishing packages, deploying.
- Writing MCP configuration outside the repo (for example `node .agents/hooks/sync-mcp.mjs --apply`).