# Python Resume Generator

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A YAML-driven resume generator CLI that compiles LaTeX (Awesome-CV) to PDF. Edit structured YAML content, run the tool, and get a professionally formatted resume.

---

## What It Does

The tool reads resume content from YAML (summary, skills, experience, projects), renders it to LaTeX with proper escaping, and compiles it to PDF using the [Awesome-CV](https://github.com/posquit0/Awesome-CV) document class. The pipeline is: **YAML → LaTeX → PDF**. Optionally, use **AI tailoring** to adapt your content to a job description. You can maintain a **one-time user profile** (`my-content/user_profile.md`) with everything about you (skills, roles, projects, achievements, certifications); when present, the LLM generates tailored resume content from that profile only—no fabrication. Without a profile, tailoring uses your existing `resume_content.yaml` and only rephrases/emphasizes.

---

## Key Features

- **YAML-based content** — Edit resume content in YAML instead of LaTeX
- **LaTeX escaping** — Automatically escapes special characters (`\`, `&`, `%`, `#`, etc.)
- **Awesome-CV layout** — Professional, ATS-friendly resume format
- **Job-specific variants** — Maintain multiple YAML versions for different roles
- **AI tailoring (optional)** — Generate a resume tailored to a job description. With a **user profile** (`my-content/user_profile.md`), the LLM builds resume content from that profile only. Without it, tailoring rephrases/emphasizes your existing YAML; the LLM never adds new experience or skills
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

1. Create `my-content/` and add your resume content there (see `resources/example_resume_content.yaml` for the schema). Default content path is `my-content/resume_content.yaml` (this folder is gitignored so your content stays local). Optional: run `make init-profile` to create `my-content/user_profile.md` and fill it once; then tailoring will use it as the single source of truth for generated bullets.
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

**Initialize user profile** (optional, for profile-based tailoring):

```bash
make init-profile
```

This copies `resources/example_user_profile.md` to `my-content/user_profile.md`. Edit it with your skills, experience, projects, and achievements; when you run `--tailor`, the LLM will use only that profile to generate resume content.

**Using a job-specific YAML** — Copy a variant to your content path, then build:

```bash
cp misc/job-descriptions/github_software_engineer_iii.yaml my-content/resume_content.yaml
make build
```

**AI tailoring** — Tailor your resume to a job description using a local LLM (Ollama) or OpenAI. Requires [Ollama](https://ollama.ai/) running locally (e.g. `ollama serve` and `ollama pull llama3.2`) or set `OPENAI_API_KEY` and use `--openai`:

```bash
# Tailor to a job description file, then build PDF
make build-tailored JOB_DESC=my-content/job-descriptions/jd.txt

# Or run the generator with options
pipenv run python generate_resume.py --tailor my-content/job-descriptions/jd.txt
pipenv run python generate_resume.py --tailor-url "https://example.com/job-posting"
pipenv run python generate_resume.py --tailor jd.txt --openai   # use OpenAI instead of Ollama
```

**CLI options** — `-i/--input` (content YAML path; default `my-content/resume_content.yaml`), `-o/--output` (output LaTeX path), `--tailor <path>`, `--tailor-url <url>`, `--no-tailor`, `--openai`, `--version`, `-v/--verbose`, `--max-fact-error-rate`. See `pipenv run python generate_resume.py --help`.

---

## Configuration

You can control LLM validation thresholds via a central config file at `resume_config.yaml` in the project root:

```yaml
fact_error:
  # Default maximum share of introduced facts allowed (0.0–1.0).
  default: 0.2

  # Optional, more specific thresholds:
  # - profile: used for profile-based tailoring (tailor_from_profile).
  # - base_yaml: used for base YAML tailoring (tailor).
  # If omitted, these fall back to "default".
  # profile: 0.2
  # base_yaml: 0.2
```

**Precedence** when resolving the max fact error rate:

- **CLI flag** `--max-fact-error-rate` (highest precedence)
- Then **config file** (`resume_config.yaml`)
- Then **environment variable** `RESUME_TAILOR_MAX_FACT_ERROR_RATE`
- Finally a hard-coded default of `0.2`

You might want a stricter threshold for **profile-based tailoring** (to prevent adding facts not in your profile) and a slightly more relaxed one for **base YAML tailoring**, depending on how close your base content is to the desired output.

---

## Project Structure

```
├── generate_resume.py          # CLI entry point
├── tailor.py                   # AI tailoring (Ollama / OpenAI)
├── Makefile                    # Build targets (generate, build, build-tailored, init-profile, clean)
├── Pipfile                     # Python dependencies
├── my-content/                 # Your resume & job JDs (gitignored)
│   ├── resume_content.yaml    # Primary content source (default -i)
│   ├── user_profile.md         # Optional one-time profile for tailoring
│   └── job-descriptions/       # Private job description files
├── output/                     # Generated PDFs (resume-YYYYMMDD-HHMMSS.pdf)
└── resources/
    ├── resume.tex              # LaTeX document (layout, static sections)
    ├── example_resume_content.yaml  # Schema example
    ├── example_user_profile.md # User profile template for tailoring
    ├── resume_sections.tex     # Generated (gitignored)
    └── awesome-cv.cls          # Awesome-CV document class
misc/
  └── job-descriptions/        # Example job descriptions & tailored YAML variants
```

---

## Contributing

Contributions are welcome. Please open an issue or pull request on the project repository.

---

## License

This project is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html). See [LICENSE](LICENSE) for the full text.
