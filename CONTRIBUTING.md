# Contributing to Aternos Discord Bot

First off, thank you for considering contributing to the **Aternos Discord Bot**! It's people like you that make this tool great for Minecraft communities worldwide.

---

## 🧭 Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to project maintainers.

---

## 🛠️ How Can I Contribute?

### Reporting Bugs
Before creating bug reports, please check the existing issue tracker to make sure the problem hasn't been reported. When creating a bug report, include:
- A clear and descriptive title.
- Steps to reproduce the problem.
- Expected behavior vs. actual behavior.
- Relevant logs (sanitize your credentials and tokens first!).
- Your environment details (OS, Python version, Docker vs. native).

### Suggesting Enhancements
Feature requests are always welcome! Please explain:
- The problem your idea solves.
- How you envision the feature working.
- Alternatives you've considered.

### Pull Requests
1. Fork the repo and create your branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Follow the project coding standards:
   - PEP 8 compliance.
   - Comprehensive type hints (`mypy` compliant).
   - Descriptive function and class docstrings.
4. Run tests and linting before submitting:
   ```bash
   pytest
   ruff check .
   ```
5. Commit using Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `ci:`).
6. Push to your fork and submit a Pull Request!

---

## 🏗️ Project Architecture Overview

- `bot/`
  - `cogs/`: Discord slash commands organized by feature domain (automation, management, multi-server, ai, etc.).
  - `services/`: Core logic decoupled from Discord UI (Aternos client wrapper, web dashboard, AI service, Prometheus metrics).
  - `utils/`: Reusable helpers (paginator views, modals, security sanitizers, structured logging).
- `tests/`: Comprehensive unit and integration test suite using `pytest` and `pytest-asyncio`.
- `docs/`: In-depth guides for self-hosting, reverse proxies, and configuration.
