# User profile (one-time input for resume tailoring)

Copy this file to `my-content/user_profile.md` and fill in each section with your own information. Use freeform text, bullets, or paragraphs. When you run tailoring (e.g. `--tailor jd.txt`), the LLM will use only facts from this profile to generate resume content—nothing will be invented.

---

## Summary / About

One or two sentences about who you are professionally. This is used for the resume summary.

Example: Senior software engineer with 8 years building backend systems. Focus on reliability and developer experience.

---

## Skills

Languages, tools, platforms, and domains. Use a list or short paragraphs.

Example:
- Languages: Python, Java, JavaScript, SQL
- Tools & platforms: Git, Docker, AWS, Kubernetes, CI/CD
- Domains: distributed systems, APIs, data pipelines

---

## Experience

For each role: job title, company, dates, location, and what you did (bullets or paragraphs). Include outcomes and technologies where relevant.

Example:

**Senior Software Engineer at Acme Corp** (2020 – Present, Remote)
- Led migration of legacy monolith to microservices; reduced deploy time by 60%.
- Owned payment integration; improved error handling and observability.
- Tech: Python, Go, PostgreSQL, Kafka.

**Software Engineer at Startup Inc** (2018 – 2020, NYC)
- Built and maintained core API and background jobs.
- Python, Django, Redis, AWS.

---

## Projects

Project names, context, what you built, tech used, and outcomes. Include side projects, open source, or internal tools.

Example:

**DesiRoomy** (desiroomy.app) — Roommate-matching web app. Built with React and Node; deployed on Vercel. 500+ signups in first quarter.

**Internal CLI** — Tool for engineers to run one-off data fixes safely. Python, argparse, read-only by default.

---

## Achievements

Awards, metrics, and impact (e.g. “Reduced latency by 40%”, “Won hackathon”, “Mentored 3 junior engineers”).

---

## Certifications

Certifications, courses, and credentials (e.g. AWS Certified Solutions Architect, Coursera ML).
