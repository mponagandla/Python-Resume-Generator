#!/usr/bin/env python3
"""
Tailor resume content to a job description using an LLM.

Uses the user's base resume content only; the LLM rephrases and emphasizes
to match the job description without adding any new facts (no fabrication).
Supports Ollama (local, default) and optional OpenAI. Falls back to base
content on LLM or parse failure.

Copyright (C) 2025  Manoj Ponagandla

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at your option)
any later version. See LICENSE for details.
"""

import os
import re
import sys
import logging
from pathlib import Path
from typing import Optional, TypedDict

import yaml
import requests

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a resume tailor. Your output must contain ONLY information that appears in the user's profile/content below. Do not invent job titles, companies, dates, technologies, projects, or achievements. You may rephrase, reorder, and emphasize to match the job description; you may not add new facts. Output valid YAML only, with keys: summary, skills, experience, projects. Use the same structure as the input (e.g. skills as list of {category, items}, experience/projects as list of {position, organization, date, location, bullets}). Preserve raw_position: true for project entries that need LaTeX in the position field. For skills, keep each category's items string to one line in the PDF (about 50–60 characters); use abbreviations or fewer items per category to avoid wrapping."""

USER_PROMPT_TEMPLATE = """Base resume content (YAML):
```yaml
{base_yaml}
```

Job description:
```
{job_description}
```

Produce tailored resume YAML that matches the job description while using ONLY the facts above. Output nothing but the YAML (you may wrap it in a ```yaml ... ``` code block)."""

USER_PROMPT_NO_JD_TEMPLATE = """Base resume content (YAML):
```yaml
{base_yaml}
```

Produce a polished version of this resume YAML. Use ONLY the facts above; do not add any new information. Output nothing but the YAML (you may wrap it in a ```yaml ... ``` code block)."""

# Profile-based tailoring: user's freeform profile is the single source of truth.
SYSTEM_PROMPT_PROFILE = """You are a resume generator. Your output must contain ONLY information that appears in the user's profile below. Do not invent job titles, companies, dates, technologies, projects, or achievements. You may rephrase, reorder, and emphasize to match the job description; you may not add new facts. Output valid YAML only, with keys: summary, skills, experience, projects. Use the structure: skills as list of {category, items}; experience and projects as list of {position, organization, date, location, bullets}. Preserve raw_position: true for project entries that need LaTeX in the position field. For skills, keep each category's items string to one line in the PDF (about 50–60 characters); use abbreviations or fewer items per category to avoid wrapping."""

USER_PROMPT_PROFILE_TEMPLATE = """User profile (everything the user has provided about themselves):
```
{profile_text}
```

Job description:
```
{job_description}
```

Produce tailored resume YAML that matches the job description while using ONLY the facts from the user profile above. Output nothing but the YAML (you may wrap it in a ```yaml ... ``` code block)."""

USER_PROMPT_PROFILE_NO_JD_TEMPLATE = """User profile (everything the user has provided about themselves):
```
{profile_text}
```

Produce resume YAML from this profile. Use ONLY the facts above; do not add any new information. Output nothing but the YAML (you may wrap it in a ```yaml ... ``` code block)."""

# Rewrite-only prompt: fix specific experience/project entries that contain facts not in the source.
SYSTEM_PROMPT_REWRITE = """You are a resume editor. Your task is to rewrite only the given experience or project entries so they use ONLY facts from the source of truth below. Do not add new companies, job titles, or projects. Output valid YAML with keys "experience" and/or "projects" containing only the corrected entries in the same order as given. Preserve raw_position: true for project entries that need LaTeX in the position field."""

USER_PROMPT_REWRITE_TEMPLATE = """Source of truth (only these facts may appear):
```
{source}
```

Entries to correct (these contain facts not in the source; rewrite them to use only the source):
```yaml
{entries_yaml}
```

Output valid YAML with keys "experience" and/or "projects" containing only the corrected entries in the same order. Nothing else."""


def load_user_profile(path: Path) -> str:
    """Load user profile text from file. Returns full file content."""
    with open(path, encoding="utf-8") as f:
        return f.read()


def _get_ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def _get_model() -> str:
    return os.environ.get("RESUME_LLM_MODEL", "llama3")


def _call_ollama(prompt: str, system: str, verbose: bool = False) -> str:
    """Call Ollama generate API. Returns full response text."""
    host = _get_ollama_host().rstrip("/")
    model = _get_model()
    print(f"Calling Ollama at {host} (model: {model})...", flush=True, file=sys.stderr)
    url = f"{host}/api/generate"
    # Ollama accepts system prompt in the request
    full_prompt = f"{system}\n\n{prompt}"
    payload = {"model": model, "prompt": full_prompt, "stream": False}
    if verbose:
        logger.info("Calling Ollama at %s with model %s", host, model)
    resp = requests.post(url, json=payload, timeout=120)
    if resp.status_code == 404:
        print(
            f"Ollama returned 404. The model '{model}' may not be pulled. Try: ollama pull {model}",
            file=sys.stderr,
            flush=True,
        )
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "")


def _get_openai_model() -> str:
    """Model for OpenAI API; separate from RESUME_LLM_MODEL (Ollama)."""
    return os.environ.get("RESUME_OPENAI_MODEL", "gpt-4o-mini")


def _call_openai(prompt: str, system: str, verbose: bool = False) -> str:
    """Call OpenAI chat API. Returns assistant message content."""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("OpenAI backend requires: pip install openai")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY must be set for OpenAI backend")
    client = OpenAI(api_key=api_key)
    model = _get_openai_model()
    print(f"Calling OpenAI (model: {model})...", flush=True, file=sys.stderr)
    if verbose:
        logger.info("Calling OpenAI with model %s", model)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""


def _extract_yaml_from_response(text: str) -> str:
    """Extract YAML from markdown code block if present, else return whole text."""
    text = (text or "").strip()
    # Find all ```...``` blocks; prefer one that looks like resume YAML (has summary: or skills:)
    blocks = list(re.finditer(r"```(?:\w+)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE))
    for m in blocks:
        candidate = m.group(1).strip()
        if re.search(r"^(summary|skills)\s*:", candidate, re.MULTILINE | re.IGNORECASE):
            return candidate
    if blocks:
        return blocks[0].group(1).strip()
    # No code block: try to find start of YAML (summary: or skills: at line start)
    for pattern in (r"^summary\s*:", r"^skills\s*:"):
        m = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if m:
            return text[m.start() :].strip()
    return text


def _normalize_llm_yaml(raw: str) -> str:
    """Fix common LLM YAML mistakes before parsing. E.g. 'position: raw_position: X' -> valid."""
    # LLM sometimes outputs invalid 'position: raw_position: "X"' or 'position: raw_position: X' (mapping values not allowed).
    # Normalize to separate keys with correct indentation for list items.

    lines = []
    for line in raw.split("\n"):
        if "position:" in line and "raw_position:" in line and "position: raw_position:" in line:
            # Match "position: raw_position: value" or "position: raw_position: "value""
            quoted = re.match(r"^(\s*)(.*?\bposition:\s*)raw_position:\s*\"([^\"]*)\"(.*)$", line)
            unquoted = re.match(r"^(\s*)(.*?\bposition:\s*)raw_position:\s+(.+)$", line)
            if quoted:
                prefix, before, value, suffix = quoted.group(1, 2, 3, 4)
                indent = prefix + "  "  # key indent for list item
                lines.append(f"{prefix}{before}\"{value}\"{suffix}")
                lines.append(f"{indent}raw_position: true")
                continue
            if unquoted:
                prefix, before, value = unquoted.group(1, 2, 3)
                value = value.strip()
                if '"' in value:
                    value = value.replace("\\", "\\\\").replace('"', '\\"')
                indent = prefix + "  "
                lines.append(f'{prefix}{before}"{value}"')
                lines.append(f"{indent}raw_position: true")
                continue
        lines.append(line)
    return "\n".join(lines)


def _parse_tailored_yaml(raw: str) -> Optional[dict]:
    """Parse tailored YAML string into dict. Returns None on parse error."""
    raw = _normalize_llm_yaml(raw)
    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError as e:
        logger.debug("YAML parse error: %s", e)
        return None


def _normalize_for_compare(s: str) -> str:
    """Normalize string for fuzzy entity comparison."""
    if not s:
        return ""
    return " ".join(s.lower().split())


def _normalize_project_position(pos: str) -> str:
    """Normalize project position for comparison: strip LaTeX, backslashes, URL-like parentheses."""
    if not pos:
        return ""
    # Strip LaTeX commands and braces
    plain = re.sub(r"\\[a-z]+\{[^}]*\}|\\[a-z]+|[\{\}]", "", pos)
    # Strip any remaining backslashes (e.g. from LLM output)
    plain = plain.replace("\\", "")
    # Remove parenthesized URL-like fragments e.g. (desiroomy.app) so they match "DesiRoomy"
    plain = re.sub(r"\([a-z0-9.-]+\)", "", plain, flags=re.IGNORECASE)
    return _normalize_for_compare(plain)


def _extract_entities(data: dict) -> dict:
    """Extract companies, positions, project names from resume data for validation."""
    entities = {"organizations": set(), "positions": set(), "projects": set()}
    if not data:
        return entities
    for entry in data.get("experience", []) or []:
        org = entry.get("organization", "").strip()
        pos = entry.get("position", "").strip()
        if org:
            entities["organizations"].add(_normalize_for_compare(org))
        if pos:
            entities["positions"].add(_normalize_for_compare(pos))
    for entry in data.get("projects", []) or []:
        pos = entry.get("position", "").strip()
        if pos:
            entities["projects"].add(_normalize_project_position(pos))
    return entities


def validate_no_new_facts(base_data: dict, tailored_data: dict) -> tuple[bool, list[str]]:
    """
    Check that tailored content does not introduce new companies, job titles, or projects.
    Returns (is_valid, list of violation messages).
    """
    base_entities = _extract_entities(base_data)
    tailored_entities = _extract_entities(tailored_data)
    violations = []

    def check_set(name: str, base_set: set, tailored_set: set) -> None:
        extra = tailored_set - base_set
        if extra:
            violations.append(f"Tailored content adds new {name}: {extra}")

    check_set("organizations", base_entities["organizations"], tailored_entities["organizations"])
    check_set("positions", base_entities["positions"], tailored_entities["positions"])
    check_set("projects", base_entities["projects"], tailored_entities["projects"])

    # Also require same number of experience and project entries (no new roles)
    base_exp = (base_data.get("experience") or [])
    base_proj = (base_data.get("projects") or [])
    tail_exp = (tailored_data.get("experience") or [])
    tail_proj = (tailored_data.get("projects") or [])
    if len(tail_exp) > len(base_exp):
        violations.append("Tailored content has more experience entries than base.")
    if len(tail_proj) > len(base_proj):
        violations.append("Tailored content has more project entries than base.")

    return (len(violations) == 0, violations)


class ValidationDetail(TypedDict):
    is_valid: bool
    violations: list
    total_entities: int
    violating_entities: int
    entries_to_rewrite: list  # list of tuple[str, int]: (section, entry_index)


def _count_entities(tailored_data: dict) -> int:
    """Count total entities (org + position in experience, position in projects) in tailored data."""
    total = 0
    for entry in (tailored_data.get("experience") or []):
        if (entry.get("organization") or "").strip():
            total += 1
        if (entry.get("position") or "").strip():
            total += 1
    for entry in (tailored_data.get("projects") or []):
        if (entry.get("position") or "").strip():
            total += 1
    return total


def validate_no_new_facts_detailed(
    base_data: dict, tailored_data: dict
) -> ValidationDetail:
    """
    Like validate_no_new_facts but returns structured data for error rate and entries to rewrite.
    """
    base_entities = _extract_entities(base_data)
    tailored_entities = _extract_entities(tailored_data)
    violations = []
    entries_to_rewrite_set: set[tuple[str, int]] = set()

    new_orgs = tailored_entities["organizations"] - base_entities["organizations"]
    new_positions = tailored_entities["positions"] - base_entities["positions"]
    new_projects = tailored_entities["projects"] - base_entities["projects"]
    if new_orgs:
        violations.append(f"Tailored content adds new organizations: {new_orgs}")
    if new_positions:
        violations.append(f"Tailored content adds new positions: {new_positions}")
    if new_projects:
        violations.append(f"Tailored content adds new projects: {new_projects}")

    base_exp = (base_data.get("experience") or [])
    base_proj = (base_data.get("projects") or [])
    tail_exp = (tailored_data.get("experience") or [])
    tail_proj = (tailored_data.get("projects") or [])

    for i, entry in enumerate(tail_exp):
        org = (entry.get("organization") or "").strip()
        pos = (entry.get("position") or "").strip()
        org_norm = _normalize_for_compare(org) if org else ""
        pos_norm = _normalize_for_compare(pos) if pos else ""
        if org_norm and org_norm in new_orgs:
            entries_to_rewrite_set.add(("experience", i))
        if pos_norm and pos_norm in new_positions:
            entries_to_rewrite_set.add(("experience", i))
        if i >= len(base_exp):
            entries_to_rewrite_set.add(("experience", i))
    if len(tail_exp) > len(base_exp):
        violations.append("Tailored content has more experience entries than base.")

    for j, entry in enumerate(tail_proj):
        pos = (entry.get("position") or "").strip()
        pos_norm = _normalize_project_position(pos) if pos else ""
        if pos_norm and pos_norm in new_projects:
            entries_to_rewrite_set.add(("projects", j))
        if j >= len(base_proj):
            entries_to_rewrite_set.add(("projects", j))
    if len(tail_proj) > len(base_proj):
        violations.append("Tailored content has more project entries than base.")

    total_entities = _count_entities(tailored_data)
    violating_entities = len(new_orgs) + len(new_positions) + len(new_projects)
    if len(tail_exp) > len(base_exp):
        violating_entities += len(tail_exp) - len(base_exp)
    if len(tail_proj) > len(base_proj):
        violating_entities += len(tail_proj) - len(base_proj)

    return ValidationDetail(
        is_valid=len(violations) == 0,
        violations=violations,
        total_entities=total_entities,
        violating_entities=violating_entities,
        entries_to_rewrite=sorted(entries_to_rewrite_set, key=lambda x: (0 if x[0] == "experience" else 1, x[1])),
    )


def validate_tailored_against_profile(profile_text: str, tailored_data: dict) -> tuple[bool, list[str]]:
    """
    Check that tailored YAML does not introduce entities absent from the profile text.
    Each organization, position, and project in tailored_data must appear (normalized, as substring) in profile_text.
    Returns (is_valid, list of violation messages).
    """
    if not profile_text or not tailored_data:
        return (True, [])
    profile_normalized = _normalize_for_compare(profile_text)
    violations = []

    def check_in_profile(name: str, value: str, kind: str) -> None:
        if not value or not value.strip():
            return
        norm = _normalize_for_compare(value)
        if norm not in profile_normalized:
            violations.append(f"Tailored {kind} not found in profile: {name!r}")

    for entry in (tailored_data.get("experience") or []):
        org = (entry.get("organization") or "").strip()
        pos = (entry.get("position") or "").strip()
        if org:
            check_in_profile(org, org, "organization")
        if pos:
            check_in_profile(pos, pos, "position")

    for entry in (tailored_data.get("projects") or []):
        pos = (entry.get("position") or "").strip()
        if pos:
            plain = _normalize_project_position(pos)
            if plain and plain not in profile_normalized:
                violations.append(f"Tailored project not found in profile: {pos!r}")

    return (len(violations) == 0, violations)


def validate_tailored_against_profile_detailed(
    profile_text: str, tailored_data: dict
) -> ValidationDetail:
    """
    Like validate_tailored_against_profile but returns structured data for error rate and entries to rewrite.
    """
    if not profile_text or not tailored_data:
        return ValidationDetail(
            is_valid=True,
            violations=[],
            total_entities=_count_entities(tailored_data),
            violating_entities=0,
            entries_to_rewrite=[],
        )
    profile_normalized = _normalize_for_compare(profile_text)
    violations = []
    entries_to_rewrite_set: set[tuple[str, int]] = set()
    violating_entities = 0

    for i, entry in enumerate(tailored_data.get("experience") or []):
        org = (entry.get("organization") or "").strip()
        pos = (entry.get("position") or "").strip()
        if org:
            norm = _normalize_for_compare(org)
            if norm not in profile_normalized:
                violations.append(f"Tailored organization not found in profile: {org!r}")
                entries_to_rewrite_set.add(("experience", i))
                violating_entities += 1
        if pos:
            norm = _normalize_for_compare(pos)
            if norm not in profile_normalized:
                violations.append(f"Tailored position not found in profile: {pos!r}")
                entries_to_rewrite_set.add(("experience", i))
                violating_entities += 1

    for j, entry in enumerate(tailored_data.get("projects") or []):
        pos = (entry.get("position") or "").strip()
        if pos:
            plain = _normalize_project_position(pos)
            if plain and plain not in profile_normalized:
                violations.append(f"Tailored project not found in profile: {pos!r}")
                entries_to_rewrite_set.add(("projects", j))
                violating_entities += 1

    total_entities = _count_entities(tailored_data)
    return ValidationDetail(
        is_valid=len(violations) == 0,
        violations=violations,
        total_entities=total_entities,
        violating_entities=violating_entities,
        entries_to_rewrite=sorted(entries_to_rewrite_set, key=lambda x: (0 if x[0] == "experience" else 1, x[1])),
    )


def _rewrite_entries_with_facts(
    source: str,
    entries_to_rewrite: list[tuple[str, int]],
    tailored_data: dict,
    use_openai: bool,
    verbose: bool = False,
) -> Optional[dict]:
    """
    Second LLM call: rewrite only the offending experience/project entries to use only facts from source.
    Returns updated tailored_data with those entries replaced, or None on failure.
    """
    if not entries_to_rewrite:
        return tailored_data
    exp_entries = [tailored_data["experience"][i] for (sec, i) in entries_to_rewrite if sec == "experience"]
    proj_entries = [tailored_data["projects"][j] for (sec, j) in entries_to_rewrite if sec == "projects"]
    entries_block = {}
    if exp_entries:
        entries_block["experience"] = exp_entries
    if proj_entries:
        entries_block["projects"] = proj_entries
    entries_yaml = yaml.dump(entries_block, default_flow_style=False, allow_unicode=True, sort_keys=False)
    user_prompt = USER_PROMPT_REWRITE_TEMPLATE.format(source=source, entries_yaml=entries_yaml)
    try:
        if use_openai:
            response_text = _call_openai(user_prompt, SYSTEM_PROMPT_REWRITE, verbose=verbose)
        else:
            response_text = _call_ollama(user_prompt, SYSTEM_PROMPT_REWRITE, verbose=verbose)
    except Exception as e:
        logger.warning("Rewrite LLM call failed: %s", e)
        return None
    raw = _extract_yaml_from_response(response_text)
    raw = _normalize_llm_yaml(raw)
    try:
        corrected = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        logger.warning("Rewrite response YAML parse failed: %s", e)
        return None
    if not isinstance(corrected, dict):
        return None
    corrected_exp = corrected.get("experience") or []
    corrected_proj = corrected.get("projects") or []
    if len(corrected_exp) != len(exp_entries) or len(corrected_proj) != len(proj_entries):
        logger.warning(
            "Rewrite response entry count mismatch: expected experience=%s projects=%s, got experience=%s projects=%s",
            len(exp_entries), len(proj_entries), len(corrected_exp), len(corrected_proj),
        )
    # Merge back: replace entries at (section, index) with corrected ones in order
    result = dict(tailored_data)
    result["experience"] = list((result.get("experience") or []))
    result["projects"] = list((result.get("projects") or []))
    exp_i = 0
    proj_j = 0
    for section, idx in entries_to_rewrite:
        if section == "experience":
            if exp_i < len(corrected_exp):
                result["experience"][idx] = corrected_exp[exp_i]
            exp_i += 1
        else:
            if proj_j < len(corrected_proj):
                result["projects"][idx] = corrected_proj[proj_j]
            proj_j += 1
    return result


def _get_max_fact_error_rate(max_fact_error_rate: Optional[float]) -> float:
    """Resolve max fact error rate from env or argument (default 0.20)."""
    if max_fact_error_rate is not None:
        return max(0.0, min(1.0, float(max_fact_error_rate)))
    try:
        return max(0.0, min(1.0, float(os.environ.get("RESUME_TAILOR_MAX_FACT_ERROR_RATE", "0.2"))))
    except (TypeError, ValueError):
        return 0.2


def fetch_job_description(url: str, verbose: bool = False) -> str:
    """Fetch job description text from URL. Returns raw text (no parsing)."""
    if verbose:
        logger.info("Fetching job description from %s", url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def load_job_description_from_file(path: Path) -> str:
    """Load job description from file. If YAML with 'description' key, use that; else full file text."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    try:
        data = yaml.safe_load(content)
        if isinstance(data, dict) and "description" in data:
            desc = data["description"]
            return desc if isinstance(desc, str) else yaml.dump(desc, default_flow_style=False)
    except yaml.YAMLError:
        pass
    return content


def tailor_from_profile(
    profile_path: Path,
    job_description_source: Optional[str] = None,
    *,
    use_openai: bool = False,
    verbose: bool = False,
    max_fact_error_rate: Optional[float] = None,
) -> Optional[str]:
    """
    Produce tailored resume YAML from user profile text and optional job description.
    Profile is the single source of truth; the LLM may only use facts from the profile.

    When the LLM introduces facts not in the profile, if the error rate is within
    max_fact_error_rate (default from RESUME_TAILOR_MAX_FACT_ERROR_RATE, e.g. 0.2),
    the tailored content is accepted with a warning. If over the threshold, a second
    LLM call rewrites only the offending entries; if that fails, returns None.

    Returns YAML string on success, or None on LLM/parse/validation failure (caller should fall back).
    """
    profile_text = load_user_profile(profile_path)
    if not profile_text.strip():
        logger.warning("User profile is empty.")
        return None

    if job_description_source:
        jd_source = job_description_source.strip()
        if jd_source.startswith("http://") or jd_source.startswith("https://"):
            job_description = fetch_job_description(jd_source, verbose=verbose)
        else:
            job_description = load_job_description_from_file(Path(jd_source))
        user_prompt = USER_PROMPT_PROFILE_TEMPLATE.format(
            profile_text=profile_text, job_description=job_description
        )
    else:
        user_prompt = USER_PROMPT_PROFILE_NO_JD_TEMPLATE.format(profile_text=profile_text)

    try:
        if use_openai:
            response_text = _call_openai(user_prompt, SYSTEM_PROMPT_PROFILE, verbose=verbose)
        else:
            response_text = _call_ollama(user_prompt, SYSTEM_PROMPT_PROFILE, verbose=verbose)
    except Exception as e:
        print(f"Warning: LLM call failed ({e}); profile tailoring aborted.", file=sys.stderr, flush=True)
        logger.warning("LLM call failed (%s); profile tailoring aborted.", e)
        return None

    raw_yaml = _extract_yaml_from_response(response_text)
    tailored_data = _parse_tailored_yaml(raw_yaml)
    if tailored_data is None:
        print("Warning: Could not parse LLM output as YAML; profile tailoring aborted.", file=sys.stderr, flush=True)
        logger.warning("Could not parse LLM output as YAML; profile tailoring aborted.")
        if verbose:
            try:
                yaml.safe_load(raw_yaml)
            except yaml.YAMLError as e:
                print(f"YAML error: {e}", file=sys.stderr, flush=True)
            preview = response_text[:1200] + ("..." if len(response_text) > 1200 else "")
            print(f"LLM response (first 1200 chars):\n{preview}", file=sys.stderr, flush=True)
            print(f"Extracted YAML (first 800 chars):\n{raw_yaml[:800]}{'...' if len(raw_yaml) > 800 else ''}", file=sys.stderr, flush=True)
        return None

    detail = validate_tailored_against_profile_detailed(profile_text, tailored_data)
    total_entities = detail["total_entities"]
    violating_entities = detail["violating_entities"]
    error_rate = (violating_entities / total_entities) if total_entities else 0.0
    threshold = _get_max_fact_error_rate(max_fact_error_rate)

    if error_rate <= threshold:
        if error_rate > 0:
            print(
                f"Warning: Tailored content has {violating_entities}/{total_entities} introduced facts ({error_rate:.0%}); within tolerance ({threshold:.0%}), accepting.",
                file=sys.stderr,
                flush=True,
            )
            logger.warning(
                "Tailored content has %s/%s introduced facts (within tolerance); accepting.",
                violating_entities, total_entities,
            )
        print("Using tailored content from LLM (profile-based).", file=sys.stderr, flush=True)
        return yaml.dump(tailored_data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Over threshold: rewrite only the offending entries
    print(
        f"Tailored content has {violating_entities}/{total_entities} introduced facts ({error_rate:.0%}); over tolerance ({threshold:.0%}). Rewriting offending entries...",
        file=sys.stderr,
        flush=True,
    )
    merged = _rewrite_entries_with_facts(
        profile_text,
        detail["entries_to_rewrite"],
        tailored_data,
        use_openai,
        verbose=verbose,
    )
    if merged is None:
        print("Warning: Rewrite failed; profile tailoring aborted.", file=sys.stderr, flush=True)
        logger.warning("Rewrite failed; profile tailoring aborted.")
        return None
    detail2 = validate_tailored_against_profile_detailed(profile_text, merged)
    total2 = detail2["total_entities"]
    err2 = (detail2["violating_entities"] / total2) if total2 else 0.0
    if err2 > threshold:
        print(
            f"Warning: After rewrite, fact error rate still {err2:.0%}; profile tailoring aborted.",
            file=sys.stderr,
            flush=True,
        )
        logger.warning("After rewrite, fact error rate still over threshold; aborting.")
        return None
    if detail2["violating_entities"] > 0:
        print(
            f"Warning: After rewrite, {detail2['violating_entities']}/{total2} introduced facts remain; within tolerance, accepting.",
            file=sys.stderr,
            flush=True,
        )
    print("Using tailored content from LLM (profile-based, after rewrite).", file=sys.stderr, flush=True)
    return yaml.dump(merged, default_flow_style=False, allow_unicode=True, sort_keys=False)


def tailor(
    base_content_path: Path,
    job_description_source: Optional[str] = None,
    *,
    use_openai: bool = False,
    verbose: bool = False,
    max_fact_error_rate: Optional[float] = None,
) -> str:
    """
    Produce tailored resume YAML from base content and optional job description.

    job_description_source: path to a file, or URL (must start with http:// or https://).
    If None, only polish the base content (no JD).

    When the LLM introduces facts not in the base, if the error rate is within
    max_fact_error_rate, the tailored content is accepted with a warning. If over
    the threshold, a second LLM call rewrites only the offending entries; if that
    fails, returns base content YAML.

    Returns YAML string. On LLM/parse/validation failure, returns base content YAML and logs warning.
    """
    with open(base_content_path, encoding="utf-8") as f:
        base_yaml_str = f.read()
    base_data = yaml.safe_load(base_yaml_str)
    if not base_data:
        logger.warning("Base content is empty; returning as-is.")
        return base_yaml_str

    if job_description_source:
        jd_source = job_description_source.strip()
        if jd_source.startswith("http://") or jd_source.startswith("https://"):
            job_description = fetch_job_description(jd_source, verbose=verbose)
        else:
            job_description = load_job_description_from_file(Path(jd_source))
        user_prompt = USER_PROMPT_TEMPLATE.format(
            base_yaml=base_yaml_str, job_description=job_description
        )
    else:
        job_description = "(none)"
        user_prompt = USER_PROMPT_NO_JD_TEMPLATE.format(base_yaml=base_yaml_str)

    try:
        if use_openai:
            response_text = _call_openai(user_prompt, SYSTEM_PROMPT, verbose=verbose)
        else:
            response_text = _call_ollama(user_prompt, SYSTEM_PROMPT, verbose=verbose)
    except Exception as e:
        print(f"Warning: LLM call failed ({e}); using base content.", file=sys.stderr, flush=True)
        logger.warning("LLM call failed (%s); using base content.", e)
        return base_yaml_str

    raw_yaml = _extract_yaml_from_response(response_text)
    tailored_data = _parse_tailored_yaml(raw_yaml)
    if tailored_data is None:
        print("Warning: Could not parse LLM output as YAML; using base content.", file=sys.stderr, flush=True)
        logger.warning("Could not parse LLM output as YAML; using base content.")
        return base_yaml_str

    detail = validate_no_new_facts_detailed(base_data, tailored_data)
    total_entities = detail["total_entities"]
    violating_entities = detail["violating_entities"]
    error_rate = (violating_entities / total_entities) if total_entities else 0.0
    threshold = _get_max_fact_error_rate(max_fact_error_rate)

    if error_rate <= threshold:
        if error_rate > 0:
            print(
                f"Warning: Tailored content has {violating_entities}/{total_entities} new facts ({error_rate:.0%}); within tolerance ({threshold:.0%}), accepting.",
                file=sys.stderr,
                flush=True,
            )
            logger.warning(
                "Tailored content has %s/%s new facts (within tolerance); accepting.",
                violating_entities, total_entities,
            )
        print("Using tailored content from LLM.", file=sys.stderr, flush=True)
        return yaml.dump(tailored_data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Over threshold: rewrite only the offending entries
    print(
        f"Tailored content has {violating_entities}/{total_entities} new facts ({error_rate:.0%}); over tolerance ({threshold:.0%}). Rewriting offending entries...",
        file=sys.stderr,
        flush=True,
    )
    merged = _rewrite_entries_with_facts(
        base_yaml_str,
        detail["entries_to_rewrite"],
        tailored_data,
        use_openai,
        verbose=verbose,
    )
    if merged is None:
        print("Warning: Rewrite failed; using base content.", file=sys.stderr, flush=True)
        logger.warning("Rewrite failed; using base content.")
        return base_yaml_str
    detail2 = validate_no_new_facts_detailed(base_data, merged)
    total2 = detail2["total_entities"]
    err2 = (detail2["violating_entities"] / total2) if total2 else 0.0
    if err2 > threshold:
        print(
            f"Warning: After rewrite, fact error rate still {err2:.0%}; using base content.",
            file=sys.stderr,
            flush=True,
        )
        logger.warning("After rewrite, fact error rate still over threshold; using base content.")
        return base_yaml_str
    if detail2["violating_entities"] > 0:
        print(
            f"Warning: After rewrite, {detail2['violating_entities']}/{total2} new facts remain; within tolerance, accepting.",
            file=sys.stderr,
            flush=True,
        )
    print("Using tailored content from LLM (after rewrite).", file=sys.stderr, flush=True)
    return yaml.dump(merged, default_flow_style=False, allow_unicode=True, sort_keys=False)
