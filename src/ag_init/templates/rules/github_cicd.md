---
id: github-cicd
name: GitHub CI/CD & Releases
category: devops
default: true
description: Standard git conventions, Conventional Commits, SemVer, and documentation rules
---
## GitHub CI/CD & Releases
**Repository Setup:** Initialize a Git repository named after the project and configure its remote repository URL.
Configure production-ready GitHub workflows and version control. Follow Git best practices, use Conventional Commits and Semantic Versioning (`MAJOR.MINOR.PATCH`), automate linting, tests, builds, and security checks on PRs and pushes, and publish tagged releases with changelogs and artifacts. Use GitHub Actions, least-privilege permissions, secure secrets, caching, and fail-fast checks. Never commit secrets, bypass checks, or release broken builds. Document the workflow in `README.md`.
**Git & Release Policy:** Use Conventional Commits and Semantic Versioning (`MAJOR.MINOR.PATCH`). Bump **MINOR** for new features and **PATCH** for bug fixes, refactoring, documentation, and other edits; bump **MAJOR** only for breaking changes. Update the version and changelog accordingly. Commit changes locally; **never push, publish, or sync to any remote** without explicit user authorization.
**Documentation:** Move all Markdown documentation into docs/, except essential root-level files required by tools or platforms (e.g., README.md, AGENTS.md). Preserve required file locations.
**Gitignore:** add .agents/ to .gitignore; keep it untrackable by Git unless explicitly instructed otherwise.
