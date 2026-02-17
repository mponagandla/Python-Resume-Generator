# Python Resume Generator

Generate PDF resumes from YAML content using LaTeX (Awesome-CV). A **content → render → compile** pipeline: you edit structured YAML, a Python script renders it to LaTeX, and XeLaTeX produces the PDF.

---

## Architecture

### Overview

Content lives in YAML. A Python script converts it to LaTeX, which is compiled to PDF using XeLaTeX and the Awesome-CV document class.

### Project Structure

```
Python Resume Generator/
├── generate_resume.py          # Main generator script
├── Makefile                    # Build orchestration
├── Pipfile / Pipfile.lock      # Python dependencies
├── .env.example                # Optional env config (LLM/job-tailoring)
└── resources/
    ├── resume.tex              # LaTeX document (layout, header, Education, Certifications, etc.)
    ├── resume_content.yaml     # Source content (Summary, Skills, Experience, Projects)
    ├── resume_sections.tex     # Generated LaTeX (replaced on each run)
    ├── job-descriptions/       # Job-specific YAML variants
    │   ├── github_compute_foundation_software_engineer_iii.yaml
    │   ├── github_software_engineer_iii.yaml
    │   └── ...
    └── awesome-cv.cls          # LaTeX class
```

### Data Flow

1. **Input**: `resume_content.yaml` (or a job-specific YAML in `job-descriptions/`)
2. **Generation**: `generate_resume.py` parses the YAML, escapes LaTeX characters, and writes `resume_sections.tex`
3. **Compilation**: `xelatex` compiles `resume.tex` (which includes `resume_sections.tex`) to PDF

### Components

#### 1. Content Layer (`resume_content.yaml`)

YAML with four main sections:

- **summary** — Plain paragraph
- **skills** — List of `{category, items}` entries
- **experience** — List of `{position, organization, date, location, bullets}`
- **projects** — Same structure as experience (optional `raw_position: true` for LaTeX in title)

#### 2. Generator (`generate_resume.py`)

- Reads YAML
- Escapes LaTeX special characters (`\`, `&`, `%`, `#`, `_`, `{`, `}`, `$`, `~`, `^`)
- Renders Summary, Skills, Experience, Projects into Awesome-CV LaTeX (`\cvsection`, `\cventry`, `\cvskill`, etc.)
- Writes `resume_sections.tex`

#### 3. LaTeX Layer (`resume.tex`)

- Uses `awesome-cv` document class
- Page geometry, fonts, colors
- Fixed personal info (name, contact)
- Includes generated content via `\input{resume_sections}`
- Static sections: Education, Certifications, Achievements

#### 4. Build System (`Makefile`)

| Target    | Action                                               |
|----------|------------------------------------------------------|
| `generate` | Runs the Python generator                            |
| `build`    | Runs `generate` then compiles with `xelatex`         |
| `clean`    | Removes generated PDF and auxiliary build artifacts  |

### Job-Specific Variants

`resources/job-descriptions/` contains YAML variants tailored to different roles. Each follows the same schema as `resume_content.yaml`. To target a job, copy the desired file to `resume_content.yaml`, or modify `generate_resume.py` to accept a content file path. The `.env.example` references optional LLM-based tailoring (Ollama/OpenAI), which is not yet implemented.

### Dependencies

| Type   | Tool / Package | Purpose                  |
|--------|----------------|--------------------------|
| Python | PyYAML ≥ 6.0   | Parsing YAML content     |
| LaTeX  | XeLaTeX        | PDF compilation          |
| LaTeX  | awesome-cv     | Resume layout & macros   |

### Output

- **`resources/resume_sections.tex`** — Generated LaTeX (gitignored)
- **`resources/resume.pdf`** — Final PDF (gitignored)
