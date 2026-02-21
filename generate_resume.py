#!/usr/bin/env python3
"""
Generate resume_sections.tex from resume_content.yaml.

Reads Summary, Skills, Experience, and Projects from the YAML content file,
escapes LaTeX special characters, and renders the four sections in Awesome-CV format.
Supports optional AI tailoring (--tailor) to adapt content to a job description.

Copyright (C) 2025  Manoj Ponagandla

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import argparse
import logging
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

__version__ = "1.0.0"

PROJECT_ROOT = Path(__file__).resolve().parent
RESOURCES_DIR = PROJECT_ROOT / "resources"
CONTENT_FILE = PROJECT_ROOT / "my-content" / "resume_content.yaml"
PROFILE_FILE = PROJECT_ROOT / "my-content" / "user_profile.md"
OUTPUT_FILE = RESOURCES_DIR / "resume_sections.tex"

# Max characters per skill items line so PDF stays one line (Awesome-CV ~70% text width).
SKILL_ITEMS_MAX_CHARS = 58


def escape_latex(text: str) -> str:
    """Escape LaTeX special characters in plain text."""
    if not text:
        return ""
    replacements = [
        ("\\", r"\textbackslash "),
        ("&", r"\&"),
        ("%", r"\%"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("$", r"\$"),
        ("~", r"\textasciitilde "),
        ("^", r"\textasciicircum "),
    ]
    result = str(text)
    for old, new in replacements:
        result = result.replace(old, new)
    return result


def render_summary(summary: str) -> str:
    """Render the Summary section."""
    escaped = escape_latex(summary.strip())
    return f"""%--------------------------------------------------
% Summary
%--------------------------------------------------
\\cvsection{{Summary}}

\\begin{{cvparagraph}}
{escaped}
\\end{{cvparagraph}}
"""


def _truncate_skill_items(items_str: str, max_chars: int) -> str:
    """Limit items string to max_chars so it fits on one line; truncate at last comma if over."""
    if not items_str or len(items_str) <= max_chars:
        return items_str
    candidate = items_str[: max_chars + 1]
    last_comma = candidate.rfind(",")
    if last_comma > 0:
        return items_str[:last_comma].strip()
    return items_str[:max_chars].strip()


def render_skills(skills: list[dict]) -> str:
    """Render the Skills section. One row per category; items truncated to fit one line."""
    lines = [
        "%--------------------------------------------------",
        "% Skills (condensed, Awesome-CV style)",
        "%--------------------------------------------------",
        "\\cvsection{Skills}",
        "",
        "\\begin{cvskills}",
    ]
    for skill in skills:
        category = escape_latex(skill["category"])
        raw_items = skill.get("items", "")
        # Schema expects items as string; LLM may output a list — normalize to one string.
        if isinstance(raw_items, (list, tuple)):
            items_str = ", ".join(str(x).strip() for x in raw_items)
        else:
            items_str = str(raw_items).strip() if raw_items else ""
        items_str = _truncate_skill_items(items_str, SKILL_ITEMS_MAX_CHARS)
        items = escape_latex(items_str)
        items = items.replace(", ", ", \\allowbreak ")
        lines.append(f"\\cvskill{{{category}}}{{{items}}}")
    lines.extend(["\\end{cvskills}", ""])
    return "\n".join(lines)


def render_entry(
    position: str,
    organization: str,
    date: str,
    location: str,
    bullets: list[str],
    *,
    raw_position: bool = False,
) -> str:
    """Render a single cventry (experience or project)."""
    pos_text = position if raw_position else escape_latex(position)
    org_text = escape_latex(organization)
    date_text = escape_latex(date)
    loc_text = escape_latex(location)

    # cventry: position, title, location, date, description
    bullet_lines = [f"\\item {escape_latex(b)}" for b in bullets]
    items_block = "\\begin{cvitems}\n" + "\n".join(bullet_lines) + "\n\\end{cvitems}"
    return f"""\\cventry
{{{pos_text}}}
{{{org_text}}}
{{{date_text}}}
{{{loc_text}}}
{{
{items_block}
}}
"""


def render_experience(experience: list[dict]) -> str:
    """Render the Experience section."""
    lines = [
        "%--------------------------------------------------",
        "% Experience",
        "%--------------------------------------------------",
        "\\cvsection{Experience}",
        "",
    ]
    for entry in experience:
        lines.append(
            render_entry(
                position=entry["position"],
                organization=entry.get("organization", ""),
                date=entry.get("date", ""),
                location=entry.get("location", ""),
                bullets=entry.get("bullets", []),
                raw_position=entry.get("raw_position", False),
            )
        )
    return "\n".join(lines)


def render_projects(projects: list[dict]) -> str:
    """Render the Projects section."""
    lines = [
        "%--------------------------------------------------",
        "% Projects",
        "%--------------------------------------------------",
        "\\cvsection{Projects}",
        "",
    ]
    for entry in projects:
        # LLM may output "name" instead of "position" for projects; accept both.
        position = entry.get("position") or entry.get("name") or ""
        bullets = entry.get("bullets")
        if bullets is None and "description" in entry:
            d = entry["description"]
            bullets = [d] if isinstance(d, str) else list(d) if isinstance(d, (list, tuple)) else []
        if bullets is None:
            bullets = []
        lines.append(
            render_entry(
                position=position,
                organization=entry.get("organization", ""),
                date=entry.get("date", ""),
                location=entry.get("location", ""),
                bullets=bullets,
                raw_position=entry.get("raw_position", False),
            )
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate resume_sections.tex from resume content YAML. Optionally tailor content to a job description using an LLM."
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=CONTENT_FILE,
        help="Path to content YAML (default: my-content/resume_content.yaml)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=OUTPUT_FILE,
        help="Path for generated LaTeX sections (default: resources/resume_sections.tex)",
    )
    parser.add_argument(
        "--tailor",
        metavar="PATH",
        help="Path to job description file (text or YAML with 'description' key). Tailors content via LLM.",
    )
    parser.add_argument(
        "--tailor-url",
        metavar="URL",
        help="URL of job description to fetch and tailor content to.",
    )
    parser.add_argument(
        "--no-tailor",
        action="store_true",
        help="Disable LLM tailoring even if --tailor/--tailor-url would be inferred.",
    )
    parser.add_argument(
        "--openai",
        action="store_true",
        help="Use OpenAI API for tailoring (default: Ollama). Requires OPENAI_API_KEY.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (debug) output.",
    )
    parser.add_argument(
        "--max-fact-error-rate",
        type=float,
        default=None,
        metavar="RATE",
        help="Max allowed share of LLM-introduced facts (0.0-1.0). Default from RESUME_TAILOR_MAX_FACT_ERROR_RATE (e.g. 0.2). Within limit, tailored content is accepted; over limit triggers a targeted rewrite of offending entries.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    content_path = args.input.resolve()
    if not content_path.exists():
        print(f"Error: Content file not found: {content_path}", file=sys.stderr)
        sys.exit(1)

    tailor_source = None
    if not args.no_tailor and (args.tailor or args.tailor_url):
        tailor_source = args.tailor or args.tailor_url
        if args.tailor:
            jd_path = Path(args.tailor).resolve()
            if not jd_path.exists():
                print(f"Error: Job description file not found: {jd_path}", file=sys.stderr)
                sys.exit(1)
            tailor_source = str(jd_path)

    if tailor_source:
        import tailor as tailor_mod
        profile_path = PROFILE_FILE.resolve()
        if profile_path.exists():
            print("Tailoring resume from user profile + job description via LLM...", flush=True)
            yaml_str = tailor_mod.tailor_from_profile(
                profile_path,
                tailor_source,
                use_openai=args.openai,
                verbose=args.verbose,
                max_fact_error_rate=args.max_fact_error_rate,
            )
            if yaml_str is not None:
                data = yaml.safe_load(yaml_str)
            else:
                # Fall back to resume_content.yaml and YAML-based tailoring
                print("Falling back to resume_content.yaml for tailoring.", flush=True)
                yaml_str = tailor_mod.tailor(
                    content_path,
                    tailor_source,
                    use_openai=args.openai,
                    verbose=args.verbose,
                    max_fact_error_rate=args.max_fact_error_rate,
                )
                data = yaml.safe_load(yaml_str)
        else:
            print("Tailoring resume to job description via LLM (Ollama)...", flush=True)
            yaml_str = tailor_mod.tailor(
                content_path,
                tailor_source,
                use_openai=args.openai,
                verbose=args.verbose,
                max_fact_error_rate=args.max_fact_error_rate,
            )
            data = yaml.safe_load(yaml_str)
    else:
        with open(content_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

    if not data:
        print("Error: Content file is empty.", file=sys.stderr)
        sys.exit(1)

    sections = []
    if "summary" in data:
        sections.append(render_summary(data["summary"]))
    if "skills" in data:
        sections.append(render_skills(data["skills"]))
    if "experience" in data:
        sections.append(render_experience(data["experience"]))
    if "projects" in data:
        sections.append(render_projects(data["projects"]))

    output = "\n".join(sections)
    out_path = args.output.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"Generated {out_path}")


if __name__ == "__main__":
    main()
