#!/usr/bin/env python3
"""
Generate resume_sections.tex from resume_content.yaml.

Reads Summary, Skills, Experience, and Projects from the YAML content file,
escapes LaTeX special characters, and renders the four sections in Awesome-CV format.
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


RESOURCES_DIR = Path(__file__).resolve().parent / "resources"
CONTENT_FILE = RESOURCES_DIR / "resume_content.yaml"
OUTPUT_FILE = RESOURCES_DIR / "resume_sections.tex"


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


def render_skills(skills: list[dict]) -> str:
    """Render the Skills section."""
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
        items = escape_latex(skill["items"])
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


def main() -> None:
    content_path = CONTENT_FILE
    if not content_path.exists():
        print(f"Error: Content file not found: {content_path}", file=sys.stderr)
        sys.exit(1)

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

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"Generated {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
