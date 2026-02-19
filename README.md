# Python Resume Generator

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A YAML-driven resume generator CLI that compiles LaTeX (Awesome-CV) to PDF. Edit structured YAML content, run the tool, and get a professionally formatted resume.

---

## What It Does

The tool reads resume content from YAML (summary, skills, experience, projects), renders it to LaTeX with proper escaping, and compiles it to PDF using the [Awesome-CV](https://github.com/posquit0/Awesome-CV) document class. The pipeline is: **YAML → LaTeX → PDF**.

---

## Key Features

- **YAML-based content** — Edit resume content in YAML instead of LaTeX
- **LaTeX escaping** — Automatically escapes special characters (`\`, `&`, `%`, `#`, etc.)
- **Awesome-CV layout** — Professional, ATS-friendly resume format
- **Job-specific variants** — Maintain multiple YAML versions for different roles
- **Simple build** — One command to generate and compile

---

## Installation

**Prerequisites**

- Python 3.10+
- [Pipenv](https://pipenv.pypa.io/) (or `pip`)
- A LaTeX distribution with XeLaTeX ([TeX Live](https://www.tug.org/texlive/), [MiKTeX](https://miktex.org/), or [MacTeX](https://www.tug.org/mactex/))

**Steps**

```bash
git clone <repository-url>
cd python-resume-generator
pipenv install
```

---

## Quick Start

1. Edit `resources/resume_content.yaml` with your summary, skills, experience, and projects.
2. Run:

```bash
make build
```

3. Open the newest `output/resume-YYYYMMDD-HHMMSS.pdf`.

---

## CLI Usage

**Full build** (generate LaTeX + compile to PDF):

```bash
make build
```

**Generate LaTeX only** (writes `resources/resume_sections.tex`):

```bash
make generate
```

Or directly:

```bash
pipenv run python generate_resume.py
```

**Clean build artifacts**:

```bash
make clean
```

**Using a job-specific YAML** — Copy the desired variant to the default content path, then build:

```bash
cp resources/job-descriptions/github_software_engineer_iii.yaml resources/resume_content.yaml
make build
```

---

## Project Structure

```
├── generate_resume.py          # CLI entry point
├── Makefile                    # Build targets
├── Pipfile                     # Python dependencies
└── resources/
    ├── resume.tex              # LaTeX document (layout, static sections)
    ├── resume_content.yaml     # Primary content source
    ├── resume_sections.tex     # Generated (gitignored)
    ├── job-descriptions/       # Job-tailored YAML variants
    └── awesome-cv.cls          # Awesome-CV document class
```

---

## Contributing

Contributions are welcome. Please open an issue or pull request on the project repository.

---

## License

This project is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html). See [LICENSE](LICENSE) for the full text.
