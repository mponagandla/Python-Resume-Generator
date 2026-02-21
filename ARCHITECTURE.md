# Architecture: YAML → Python → LaTeX → PDF Pipeline

This document explains the internal architecture of the resume generator for contributors. The pipeline has four main layers plus an optional AI tailoring step before the content layer.

---

## Content Layer (YAML)

Content is stored in YAML files. Your content lives in `my-content/` (gitignored): `my-content/resume_content.yaml` is the default source; job description files for tailoring go in `my-content/job-descriptions/`. Example and job-tailored variants ship in `resources/` (e.g. `resources/example_resume_content.yaml`, `resources/job-descriptions/`). The schema defines four sections:

| Section     | Structure | Purpose |
|------------|-----------|---------|
| `summary`  | Single multi-line string | Professional summary paragraph |
| `skills`   | List of `{category, items}` | Categorized skill groups (e.g. Languages, Cloud) |
| `experience` | List of `{position, organization, date, location, bullets}` | Work history entries |
| `projects` | Same as experience; optional `raw_position: true` | Side projects, open source, etc. |

All sections are optional. The optional `raw_position: true` allows raw LaTeX in the position field (e.g. links, formatting) without escaping.

This layer is the single source of truth for what appears in the dynamic sections of the resume. It separates content from layout and enables multiple job-specific variants without duplicating LaTeX.

---

## Rendering Layer (Python)

`generate_resume.py` transforms YAML into LaTeX:

1. **Load** — `yaml.safe_load()` reads the content file.
2. **Escape** — `escape_latex()` replaces `\`, `&`, `%`, `#`, `_`, `{`, `}`, `$`, `~`, `^` with safe LaTeX equivalents.
3. **Render** — Each section has a dedicated renderer:
   - `render_summary()` → `\cvsection{Summary}` and `\begin{cvparagraph}...`
   - `render_skills()` → `\cvsection{Skills}` and `\cvskill{category}{items}`
   - `render_experience()` / `render_projects()` → `\cventry` blocks with `\begin{cvitems}` bullet lists
4. **Write** — Concatenated output is written to `resume_sections.tex`.

The rendering layer is stateless: it maps content to Awesome-CV LaTeX macros without touching page layout, fonts, or the compilation step.

---

## Template Layer (LaTeX)

`resources/resume.tex` is the main document and defines layout and static content:

- **Document class** — `awesome-cv` provides resume layout (page geometry, fonts, colors).
- **Static content** — Header, personal info, Education, Certifications, Achievements.
- **Dynamic content** — `\input{resume_sections}` pulls in the generated LaTeX.

Flow:

```
resume.tex
├── \documentclass{awesome-cv}
├── geometry, colors, fonts
├── \name{}, \position{} (fixed)
├── \makecvheader
├── \input{resume_sections}   ← rendered Summary, Skills, Experience, Projects
├── \cvsection{Education}     ← static
├── \cvsection{Certifications}
└── \cvsection{Achievements}
```

The template layer owns layout and typography; the rendering layer only produces the section content.

---

## Build Layer

The build layer is orchestrated by the **Makefile**:

| Phase    | Command         | Action |
|----------|-----------------|--------|
| Generate | `make generate` | Runs `generate_resume.py` → writes `resume_sections.tex` |
| Compile  | `make build`    | Runs `generate` then `xelatex resume.tex` → produces `resume.pdf` |
| Clean    | `make clean`    | Removes generated PDF, aux files, and `resume_sections.tex` |

`make build` depends on `generate`, so the LaTeX always compiles with fresh generated content. XeLaTeX is used for Unicode support (names, symbols) and modern fonts.

---

## AI Tailoring (Optional)

The `tailor.py` module implements AI tailoring. There are two modes:

### Profile-based tailoring (preferred when available)

If `my-content/user_profile.md` exists, it is used as the **single source of truth**. The user fills this file once (Summary, Skills, Experience, Projects, Achievements, Certifications) in freeform text; see `resources/example_user_profile.md`. When `--tailor` or `--tailor-url` is used, `generate_resume.py` calls `tailor.tailor_from_profile()`: the LLM receives the profile text plus the job description and produces resume YAML (summary, skills, experience, projects) using **only** facts from the profile. `validate_tailored_against_profile(profile_text, tailored_data)` ensures every organization, position, and project in the output appears in the profile (normalized substring check). On LLM/parse/validation failure, the pipeline falls back to YAML-based tailoring using `resume_content.yaml`.

### YAML-based tailoring (fallback or when no profile)

When no profile file is present, the single source of truth is the user's content (default `my-content/resume_content.yaml`). The LLM only rephrases and emphasizes to match a job description—it does not add new experience, skills, or achievements.

1. **Inputs** — Base content (default `my-content/resume_content.yaml`) or user profile (`my-content/user_profile.md` if present) plus an optional job description (file path or URL).
2. **Integration** — When `--tailor` or `--tailor-url` is passed, `generate_resume.py` checks for `my-content/user_profile.md`. If it exists, it calls `tailor.tailor_from_profile()`; otherwise it calls `tailor.tailor()`. The tailor returns a YAML string that is then loaded and rendered as usual.
3. **LLM role** — Tailor bullets, emphasize relevant skills, adjust summary wording; output remains valid YAML conforming to the existing schema. The system prompt explicitly forbids inventing job titles, companies, dates, technologies, or achievements.
4. **Backends** — Ollama (local, default) via HTTP API; optional OpenAI when `--openai` is used and `OPENAI_API_KEY` is set. Config: `RESUME_LLM_MODEL`, `OLLAMA_HOST`, `OPENAI_API_KEY` (see `.env.example`).
5. **Validation** — For profile mode: `validate_tailored_against_profile()`. For YAML mode: `validate_no_new_facts(base_data, tailored_data)`. If validation fails, base content is used (or profile tailoring is aborted and YAML fallback is used) and a warning is logged.
6. **Fallback** — On LLM failure, parse error, or validation failure, the pipeline uses the original base content (or falls back to YAML-based tailoring when profile-based tailoring fails) and logs a warning.

The pipeline remains: **Content (YAML or AI-tailored) → Render → Template → Build**, with AI as an optional preprocessing step before the content layer.
