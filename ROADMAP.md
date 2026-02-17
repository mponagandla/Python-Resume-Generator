# Roadmap

This roadmap outlines planned improvements for the Python Resume Generator. Items are grouped by phase; ordering within a phase may change based on contributor availability and priorities.

---

## Phase 1: Foundation

### CLI Improvements

- Add `argparse` (or `typer`/`click`) for structured CLI
- Support `-i/--input` and `-o/--output` for custom content and output paths
- Add `--version` flag
- Optional `--verbose` for debug output
- Document CLI usage in README and `--help`

### YAML Validation

- Add schema validation (e.g. Cerberus, Pydantic, or JSON Schema) for `resume_content.yaml`
- Emit clear error messages for missing required fields or invalid structure
- Optional `--validate` flag to check content without generating output
- Consider `pyyaml` custom constructors for stricter typing

---

## Phase 2: Templating & Outputs

### Jinja2 Templating

- Introduce Jinja2 templates for LaTeX rendering instead of (or alongside) f-strings
- Separate templates per section (summary, skills, experience, projects)
- Support custom template paths for community variants
- Simplify addition of new section types via new template files
- Preserve `escape_latex` or equivalent in Jinja2 filters

### HTML Output

- Add HTML output format (e.g. via Jinja2 or a dedicated HTML template)
- Minimal, print-friendly CSS for HTML resumes
- CLI flag: `--format pdf|html` or `-f html`
- Optional: single-page layout, dark/light themes

---

## Phase 3: AI & Distribution

### AI Tailoring

- Implement `tailor.py` (or equivalent) as described in [ARCHITECTURE.md](ARCHITECTURE.md)
- Support Ollama (local) as default; optional OpenAI backend
- CLI: `--tailor <job_desc_file>` or `--tailor-url <url>`
- Env config: `RESUME_LLM_MODEL`, `OLLAMA_HOST`, `OPENAI_API_KEY`
- Fallback to base content on LLM failure
- Document prompting strategy and rate limits

### Docker Support

- Add `Dockerfile` for reproducible builds
- Include Python + LaTeX (TeX Live) in image for full PDF generation
- Optional `docker-compose.yml` for local development
- Document `docker run` usage in README
- Consider multi-stage build for smaller image

---

## Phase 4: Future

### Web Interface

- Simple web UI to edit YAML and preview/download PDF
- Options: FastAPI + Jinja2, or static SPA (e.g. React/Vue) with backend API
- Live preview (PDF or HTML) as user edits
- No sign-up required; all processing client-side or on single-run containers
- Deployable via Docker

---

## Out of Scope (for now)

- Multi-page resume support
- Interactive CV builder (drag-and-drop)
- Cloud-hosted resume storage or accounts
- Paid / commercial features

---

## Contributing to the Roadmap

If you want to work on a roadmap item:

1. Open an issue to discuss approach before coding
2. Reference this roadmap (e.g. "Phase 1: CLI improvements")
3. Follow [CONTRIBUTING.md](CONTRIBUTING.md) for PRs and branch naming
