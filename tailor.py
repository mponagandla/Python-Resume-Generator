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
import logging
from pathlib import Path
from typing import Optional

import yaml
import requests

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a resume tailor. Your output must contain ONLY information that appears in the user's profile/content below. Do not invent job titles, companies, dates, technologies, projects, or achievements. You may rephrase, reorder, and emphasize to match the job description; you may not add new facts. Output valid YAML only, with keys: summary, skills, experience, projects. Use the same structure as the input (e.g. skills as list of {category, items}, experience/projects as list of {position, organization, date, location, bullets}). Preserve raw_position: true for project entries that need LaTeX in the position field."""

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


def _get_ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def _get_model() -> str:
    return os.environ.get("RESUME_LLM_MODEL", "llama3.2")


def _call_ollama(prompt: str, system: str, verbose: bool = False) -> str:
    """Call Ollama generate API. Returns full response text."""
    host = _get_ollama_host().rstrip("/")
    model = _get_model()
    url = f"{host}/api/generate"
    # Ollama accepts system prompt in the request
    full_prompt = f"{system}\n\n{prompt}"
    payload = {"model": model, "prompt": full_prompt, "stream": False}
    if verbose:
        logger.info("Calling Ollama at %s with model %s", host, model)
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "")


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
    model = os.environ.get("RESUME_LLM_MODEL", "gpt-4o-mini")
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
    # Match ```yaml ... ``` or ``` ... ```
    match = re.search(r"```(?:yaml)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _parse_tailored_yaml(raw: str) -> Optional[dict]:
    """Parse tailored YAML string into dict. Returns None on parse error."""
    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError:
        return None


def _normalize_for_compare(s: str) -> str:
    """Normalize string for fuzzy entity comparison."""
    if not s:
        return ""
    return " ".join(s.lower().split())


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
            # Strip LaTeX for comparison
            plain = re.sub(r"\\[a-z]+\{[^}]*\}|\\[a-z]+|[\{\}]", "", pos)
            entities["projects"].add(_normalize_for_compare(plain))
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


def tailor(
    base_content_path: Path,
    job_description_source: Optional[str] = None,
    *,
    use_openai: bool = False,
    verbose: bool = False,
) -> str:
    """
    Produce tailored resume YAML from base content and optional job description.

    job_description_source: path to a file, or URL (must start with http:// or https://).
    If None, only polish the base content (no JD).

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
        logger.warning("LLM call failed (%s); using base content.", e)
        return base_yaml_str

    raw_yaml = _extract_yaml_from_response(response_text)
    tailored_data = _parse_tailored_yaml(raw_yaml)
    if tailored_data is None:
        logger.warning("Could not parse LLM output as YAML; using base content.")
        return base_yaml_str

    valid, violations = validate_no_new_facts(base_data, tailored_data)
    if not valid:
        logger.warning("Tailored content introduced new facts: %s; using base content.", violations)
        return base_yaml_str

    return yaml.dump(tailored_data, default_flow_style=False, allow_unicode=True, sort_keys=False)
