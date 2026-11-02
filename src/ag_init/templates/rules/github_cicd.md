---
id: github-cicd
name: GitHub CI/CD & Releases
category: devops
default: true
description: Standard git conventions, Conventional Commits, SemVer, and documentation rules
---
## GitHub CI/CD & Release Management

### Repository Setup
- Initialize a Git repository named after the project.
- Configure the appropriate remote repository URL.
- Follow Git best practices and maintain a clean, consistent commit history.

### CI/CD Automation
Implement production-ready GitHub Actions workflows that:

- Automate linting, formatting checks, tests, and production builds.
- Run validation checks on pull requests and pushes.
- Include relevant security and dependency vulnerability checks.
- Use caching to optimize workflow execution.
- Apply least-privilege permissions and secure secret management.
- Fail fast when critical checks fail.
- Publish tagged releases with changelogs and build artifacts.

**Requirements:**
- Never commit secrets, credentials, or sensitive configuration.
- Never bypass CI checks or ignore failing validation.
- Never publish releases containing broken builds.
- Document the CI/CD pipeline and release process in `README.md`.

### Git & Versioning Policy

Follow **Conventional Commits** and **Semantic Versioning** (`MAJOR.MINOR.PATCH`).

Apply version increments according to the following rules:

| Change Type | Version Bump | Examples |
|---|---|---|
| Breaking changes | **MAJOR** | Incompatible API or architecture changes |
| New features | **MINOR** | New functionality or capabilities |
| Fixes and other changes | **PATCH** | Bug fixes, refactoring, documentation, and minor edits |

For every release:
- Update the project version appropriately.
- Update the changelog with relevant changes.
- Ensure all required CI checks pass before creating a release.
- Use meaningful, descriptive Conventional Commits.

### Remote Operations & Authorization

- Commit changes locally when appropriate.
- **Never push, publish, or synchronize changes to any remote repository without explicit user authorization.**
- Never create or publish a remote release without explicit user authorization.
- Local commits and local repository maintenance are permitted without additional approval.
