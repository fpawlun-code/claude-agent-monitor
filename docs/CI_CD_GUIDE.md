# CI/CD Pipeline Guide - ClaudeAgent

## 🚀 Overview

ClaudeAgent uses GitHub Actions for continuous integration and deployment. All workflows run automatically on push and pull requests.

---

## 📋 Workflows

### 1. CI - Tests (`ci.yml`)

**Triggers:** Push to `main`/`master`, Pull Requests

**Jobs:**
- Runs on: `ubuntu-latest`, `windows-latest`
- Python: 3.12
- Matrix testing for cross-platform compatibility

**Steps:**
1. Checkout code
2. Setup Python 3.12 with pip cache
3. Install dependencies (`requirements.txt`)
4. Install test dependencies (`pytest`, `pytest-cov`, `pytest-mock`)
5. Run tests with coverage
6. Upload coverage reports (Ubuntu only)

**Command:**
```bash
pytest tests/ -v --cov=ai_gateway --cov=rtx_agent --cov-report=xml
```

---

### 2. Code Quality (`lint.yml`)

**Triggers:** Push to `main`/`master`, Pull Requests

**Jobs:**
- Runs on: `ubuntu-latest`
- Python: 3.12

**Checks:**
1. **Black** - Code formatting verification
   ```bash
   black --check ai_gateway.py rtx_agent.py tests/
   ```

2. **Flake8** - Style guide enforcement
   ```bash
   flake8 ai_gateway.py rtx_agent.py tests/
   ```

3. **Pylint** - Code quality (minimum 7.0/10)
   ```bash
   pylint ai_gateway.py --fail-under=7.0
   pylint rtx_agent.py --fail-under=7.0
   ```

4. **Mypy** - Type checking (non-blocking)
   ```bash
   mypy ai_gateway.py rtx_agent.py --ignore-missing-imports
   ```

5. **Bandit** - Security scanning (non-blocking)
   ```bash
   bandit -r ai_gateway.py rtx_agent.py
   ```

---

### 3. Coverage Report (`coverage-report.yml`)

**Triggers:** Push to `main`/`master`, Pull Requests

**Features:**
- Generates HTML coverage reports
- Uploads artifacts for download
- Comments on PRs with coverage summary
- Displays coverage in GitHub job summary

**Artifacts:**
- `coverage-html-report` - HTML visualization
- `coverage.xml` - Machine-readable format

---

## 🔧 Pre-commit Hooks

Local quality checks before commits:

### Installation

```bash
pip install pre-commit
pre-commit install
```

### Hooks Configured

1. **Black** - Auto-formatting (line-length: 120)
2. **Flake8** - Style checking
3. **isort** - Import sorting
4. **Pylint** - Code quality (score >= 7.0)
5. **Trailing whitespace** - Cleanup
6. **YAML/JSON** - Syntax validation
7. **Large files** - Prevent commits >1MB
8. **Mypy** - Type checking (optional)

### Manual Run

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

### Bypass (Emergency Only)

```bash
git commit --no-verify -m "emergency fix"
```

---

## 📊 Status Badges

Add to README.md:

```markdown
[![CI Tests](https://github.com/USERNAME/ClaudeAgent/workflows/CI%20-%20Tests/badge.svg)](https://github.com/USERNAME/ClaudeAgent/actions)
[![Code Quality](https://github.com/USERNAME/ClaudeAgent/workflows/Code%20Quality/badge.svg)](https://github.com/USERNAME/ClaudeAgent/actions)
[![Coverage](https://img.shields.io/badge/coverage-22%25-orange)](htmlcov/index.html)
```

---

## 🧪 Testing Locally

### Run Full CI Pipeline Locally

```bash
# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock pylint flake8 black mypy bandit

# Run tests
pytest tests/ -v --cov=ai_gateway --cov=rtx_agent --cov-report=html

# Run linting
black --check ai_gateway.py rtx_agent.py
flake8 ai_gateway.py rtx_agent.py
pylint ai_gateway.py --fail-under=7.0
pylint rtx_agent.py --fail-under=7.0

# Security scan
bandit -r ai_gateway.py rtx_agent.py
```

---

## 🔄 Workflow Diagram

```
┌─────────────┐
│   Push/PR   │
└──────┬──────┘
       │
       ├────────────────┬──────────────┬─────────────────┐
       │                │              │                 │
       ▼                ▼              ▼                 ▼
┌──────────┐    ┌──────────┐   ┌──────────┐    ┌──────────┐
│ CI Tests │    │  Linting │   │ Coverage │    │Pre-commit│
└─────┬────┘    └─────┬────┘   └─────┬────┘    └────┬─────┘
      │               │              │              │
      │  Ubuntu/Win   │   Black      │  HTML        │  Local
      │  Python 3.12  │   Flake8     │  Reports     │  Hooks
      │  Pytest       │   Pylint     │  Artifacts   │  Auto
      │               │   Mypy       │              │
      └───────────────┴──────────────┴──────────────┘
                      │
                      ▼
               ┌──────────────┐
               │ All Checks   │
               │    Pass?     │
               └──────┬───────┘
                      │
              ┌───────┴────────┐
              │                │
              ▼                ▼
         ┌────────┐       ┌────────┐
         │   ✅   │       │   ❌   │
         │ Merge  │       │  Fix   │
         └────────┘       └────────┘
```

---

## 📈 Quality Metrics

Current status (as of 2026-02-18):

| Metric | Value | Status |
|--------|-------|--------|
| Pylint (ai_gateway) | 8.05/10 | ✅ Good |
| Pylint (rtx_agent) | 9.23/10 | ✅ Excellent |
| Flake8 (post-black) | 6-3 issues | ✅ Clean |
| Test Coverage | 22% | ⚠️ Improving |
| Tests Passing | 21/30 (70%) | ⚠️ Improving |
| Security Issues | 0 | ✅ Secure |

**Target Goals:**
- Pylint: >=8.0/10
- Test Coverage: >=50%
- Tests Passing: >=90%

---

## 🤝 Contributing

### Workflow for Contributors

1. **Fork & Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ClaudeAgent.git
   cd ClaudeAgent
   ```

2. **Setup Development Environment**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If exists
   pre-commit install
   ```

3. **Create Feature Branch**
   ```bash
   git checkout -b feature/my-feature
   ```

4. **Make Changes**
   - Write code
   - Add tests
   - Run pre-commit hooks
   - Ensure all tests pass

5. **Commit**
   ```bash
   git add .
   git commit -m "feat: add my feature"
   ```
   *Pre-commit hooks will run automatically*

6. **Push & Create PR**
   ```bash
   git push origin feature/my-feature
   ```
   *GitHub Actions will run automatically on PR*

7. **Review**
   - Check CI status
   - Address feedback
   - Update PR

---

## 🐛 Troubleshooting

### Pre-commit Hook Failures

**Black formatting failed:**
```bash
# Auto-fix
black ai_gateway.py rtx_agent.py tests/
git add .
git commit -m "fix: apply black formatting"
```

**Pylint score too low:**
```bash
# Check issues
pylint ai_gateway.py

# Fix issues, then commit
```

**Flake8 errors:**
```bash
# See errors
flake8 ai_gateway.py

# Fix manually or disable specific rules in .flake8
```

### GitHub Actions Failures

**Tests failing:**
```bash
# Run tests locally
pytest tests/ -v

# Debug specific test
pytest tests/test_ai_gateway.py::TestDelegation::test_delegate_to_rtx_basic -v
```

**Linting failing:**
```bash
# Run same checks locally
black --check ai_gateway.py
flake8 ai_gateway.py
pylint ai_gateway.py
```

---

## 📚 References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [Pylint Documentation](https://pylint.pycqa.org/)

---

**Last Updated:** 2026-02-18
**PHASE 3 Week 3:** CI/CD Pipeline Complete ✅
