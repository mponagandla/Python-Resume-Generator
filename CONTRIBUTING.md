# Contributing to Python Resume Generator

Thank you for your interest in contributing. This guide explains how to set up the project and contribute effectively.

---

## Fork and Clone

1. Fork the repository on GitHub (use the **Fork** button).
2. Clone your fork locally:

```bash
git clone https://github.com/YOUR_USERNAME/python-resume-generator.git
cd python-resume-generator
```

3. Add the upstream remote to stay in sync:

```bash
git remote add upstream https://github.com/ORIGINAL_OWNER/python-resume-generator.git
git fetch upstream
```

4. Before starting new work, sync your branch:

```bash
git checkout main
git pull upstream main
```

---

## Development Environment

**Requirements:** Python 3.10+, Pipenv, XeLaTeX (for full builds)

1. Create and activate the virtual environment:

```bash
pipenv install
pipenv shell
```

2. Verify the generator runs:

```bash
python generate_resume.py
make build
```

3. Confirm `resources/resume.pdf` is produced.

---

## Code Style Expectations

- **PEP 8** — Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines. Use a formatter such as **Black** or **Ruff** if your editor supports it.
- **Type hints** — Use type annotations for function parameters and return values.
- **Docstrings** — Document public functions with a brief description; use Google or NumPy style if adding detailed docs.
- **Imports** — Group stdlib, third‑party, and local imports; sort with `isort` or equivalent.
- **Line length** — Prefer 88–100 characters max for readability.

---

## How to Add New CLI Flags

The entry point is `generate_resume.py`; `main()` reads configuration and invokes the render pipeline. To add flags:

1. Add `argparse` (or `typer`/`click` if introduced) at the top of `main()`:

```python
import argparse

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate resume LaTeX from YAML.")
    parser.add_argument("-i", "--input", default=CONTENT_FILE, type=Path,
                        help="Path to YAML content file")
    parser.add_argument("-o", "--output", default=OUTPUT_FILE, type=Path,
                        help="Path for generated resume_sections.tex")
    args = parser.parse_args()
    # Use args.input, args.output instead of constants
```

2. Replace uses of `CONTENT_FILE` and `OUTPUT_FILE` in `main()` with `args.input` and `args.output`.

3. Update the **Makefile** if you add new targets or change how the script is invoked.

4. Document new flags in the README under **CLI Usage**.

---

## How to Add New YAML Templates

**Adding a new content file (job-specific variant):**

1. Create a new YAML file under `resources/job-descriptions/`, e.g. `my_company_senior_engineer.yaml`.

2. Follow the existing schema:

```yaml
summary: |
  Your professional summary paragraph.

skills:
  - category: "Category Name"
    items: "Item 1, Item 2, Item 3"
  # ... more categories

experience:
  - position: "Job Title"
    organization: "Company Name"
    date: "Start -- End"
    location: "Location"
    bullets:
      - "Achievement or responsibility."
      # ... more bullets

projects:
  - position: "Project Name"
    organization: ""
    date: ""
    location: ""
    bullets:
      - "Description."
    raw_position: true   # Optional: use LaTeX in the position text
```

3. Use `raw_position: true` only when the position field contains LaTeX (e.g. links or formatting).

**Adding a new section type (e.g. Certifications, Publications):**

1. Define the YAML schema for the new section in this guide or in the README.
2. Add a `render_*` function in `generate_resume.py` (model it on `render_experience` or `render_skills`).
3. Wire the new section into `main()`: load the key from `data`, call the renderer, append to `sections`.
4. Ensure `resume.tex` includes the appropriate Awesome-CV command or that the generated LaTeX matches the document structure.

---

## Pull Request Guidelines

1. **Scope** — One logical change per PR. Keep diffs focused and reviewable.
2. **Tests** — Add or update tests if the change affects behavior. Ensure existing behavior still works.
3. **Docs** — Update the README, CONTRIBUTING.md, or inline docs when adding features or changing usage.
4. **Description** — Provide a clear title and description. Reference related issues when applicable.
5. **CI** — Ensure any CI checks pass before requesting review.

---

## Branch Naming Conventions

Use lowercase with hyphens; prefix by change type:

| Prefix   | Example                          | Use for                    |
|----------|-----------------------------------|----------------------------|
| `feature/` | `feature/cli-input-flag`         | New functionality          |
| `fix/`     | `fix/latex-ampersand-escape`    | Bug fixes                  |
| `docs/`    | `docs/contributing-setup`       | Documentation only         |
| `refactor/` | `refactor/render-functions`   | Code structure, no behavior change |

---

## Commit Message Format

Follow a simple Conventional Commits style:

```
<type>: <short description>

[Optional body explaining context or rationale.]
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

**Examples:**

```
feat: add --input and --output CLI flags for custom content paths
```

```
fix: escape ampersands in skill items
```

```
docs: document YAML schema for job-descriptions
```

- Use imperative mood: "add" not "added".
- Keep the subject line under ~72 characters.
- Add a body for non-trivial changes.
