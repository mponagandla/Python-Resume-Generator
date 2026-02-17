# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately. **Do not open a public issue.**

- **Email:** [INSERT MAINTAINER EMAIL]
- **Preferred:** Contact the maintainers through the repository’s security contact (if configured).

Include:

- A clear description of the vulnerability
- Steps to reproduce
- Affected components and versions
- Potential impact
- Suggested fix (if any)

We will respond within a reasonable timeframe and keep you updated on status and resolution. Credit will be given to reporters when the issue is disclosed, unless you prefer to remain anonymous.

---

## Areas of Particular Concern

### LaTeX Injection

YAML content is rendered into LaTeX and compiled to PDF. Malicious `\input{}`, `\write{}`, shell escape sequences, or other LaTeX macros in user-controlled YAML could lead to:

- Arbitrary file read/write
- Command execution during compilation
- Information disclosure

The current `escape_latex()` function escapes common special characters but may not cover all injection vectors. Reports of bypasses or edge cases are especially valuable.

### YAML Parsing

Content is loaded via `yaml.safe_load()`, which should mitigate deserialization attacks (e.g. `!!python/object`). Potential risks include:

- Unexpected types or structures causing crashes or unexpected behavior
- Resource exhaustion from deeply nested or oversized YAML
- Parser bugs or `safe_load` misconfiguration

Report any concerns about YAML loading, especially with untrusted or third-party content files.

### LLM Integration (Future)

Planned AI tailoring will send resume and job-description content to LLM providers (Ollama, OpenAI). Potential risks:

- **Prompt injection** — Malicious job descriptions affecting LLM output or instructions
- **Data exfiltration** — User content leaking to third parties or training data
- **API key exposure** — Misuse of credentials in logs, env, or error messages

Report issues in LLM integration design or implementation as they become relevant.

---

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| Latest  | Yes                |
| Older   | Best-effort fixes  |

---

## Acknowledgments

Security researchers who responsibly disclose vulnerabilities will be acknowledged here (with permission) when fixes are released.
