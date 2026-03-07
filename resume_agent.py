#!/usr/bin/env python3
"""
Resume generation chat agent.

Provides a terminal REPL where users can chat with an agent that plans and triggers
resume generation. The agent has tools to load profile, load job description, and
generate tailored resumes with optional skills to highlight and extra instructions.

Copyright (C) 2025  Manoj Ponagandla
"""

import os
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PROFILE = PROJECT_ROOT / "my-content" / "user_profile.md"
DEFAULT_OUTPUT = PROJECT_ROOT / "resources" / "resume_sections.tex"


def _get_tools(default_profile_path: Path, use_openai: bool = False):
    """Build LangChain tools that close over default_profile_path and use_openai."""
    import tailor
    from generate_resume import compile_latex_to_pdf, render_yaml_to_docx, render_yaml_to_latex

    from langchain_core.tools import tool

    @tool
    def load_profile(path: str) -> str:
        """Load the user profile from a file path. Use this to read the user's profile content
        (summary, skills, experience, projects) before generating a resume. Path can be relative
        to the project root or absolute."""
        try:
            p = Path(path)
            if not p.is_absolute():
                p = PROJECT_ROOT / path
            p = p.resolve()
            if not p.exists():
                return f"Error: Profile file not found: {p}"
            return tailor.load_user_profile(p)
        except Exception as e:
            return f"Error loading profile: {e}"

    @tool
    def load_jd(path_or_url: str) -> str:
        """Load a job description from a file path or URL. Use this to read the job description
        before generating a tailored resume. Path can be relative to project root or absolute.
        URL must start with http:// or https://."""
        try:
            s = path_or_url.strip()
            if s.startswith("http://") or s.startswith("https://"):
                return tailor.fetch_job_description(s)
            p = Path(s)
            if not p.is_absolute():
                p = PROJECT_ROOT / s
            p = p.resolve()
            if not p.exists():
                return f"Error: Job description file not found: {p}"
            return tailor.load_job_description_from_file(p)
        except Exception as e:
            return f"Error loading job description: {e}"

    @tool
    def generate_resume(
        profile_path: str,
        jd_path: Optional[str] = None,
        skills_to_highlight: Optional[str] = None,
        extra_instructions: Optional[str] = None,
        output_path: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> str:
        """Generate a tailored resume from the user profile and optionally a job description.
        Writes LaTeX to the output path, then compiles to PDF (unless output_format is docx).
        Use this when the user wants to generate or regenerate their resume. profile_path is required.
        jd_path is optional (file or URL). skills_to_highlight can be a comma-separated list of skills
        to emphasize (e.g. 'AWS, Kubernetes, leadership'). extra_instructions can be any additional guidance
        (e.g. 'emphasize backend and scalability'). output_path defaults to resources/resume_sections.tex
        if not provided. output_format: 'pdf' (default), 'docx' (Word document), or 'both'. Use 'docx' when
        the user asks for an editable document, Word document, or .docx format."""
        try:
            p_path = Path(profile_path)
            if not p_path.is_absolute():
                p_path = PROJECT_ROOT / profile_path
            p_path = p_path.resolve()
            if not p_path.exists():
                return f"Error: Profile file not found: {p_path}"

            jd_source = None
            if jd_path and jd_path.strip():
                jd_source = jd_path.strip()

            skills_list = None
            if skills_to_highlight and skills_to_highlight.strip():
                skills_list = [s.strip() for s in skills_to_highlight.split(",") if s.strip()]

            fmt = (output_format or "pdf").strip().lower()
            if fmt not in ("pdf", "docx", "both"):
                fmt = "pdf"

            out_path = Path(output_path) if output_path and output_path.strip() else DEFAULT_OUTPUT
            if not out_path.is_absolute():
                out_path = PROJECT_ROOT / out_path
            out_path = out_path.resolve()

            yaml_str = tailor.tailor_from_profile(
                p_path,
                jd_source,
                skills_to_highlight=skills_list,
                extra_instructions=extra_instructions.strip() if extra_instructions else None,
                use_openai=use_openai,
                verbose=False,
            )
            if yaml_str is None:
                return "Error: Resume tailoring failed (LLM or validation error). Try again or check the profile."

            results = []
            if fmt in ("pdf", "both"):
                render_yaml_to_latex(yaml_str, out_path)
                pdf_path = compile_latex_to_pdf()
                if pdf_path:
                    results.append(f"Generated resume PDF at {pdf_path}")
                elif fmt == "pdf":
                    return f"Generated LaTeX at {out_path}. (PDF compilation failed—ensure XeLaTeX is installed. Run 'make build' to compile manually.)"
                else:
                    results.append(f"LaTeX at {out_path} (PDF compilation failed).")

            if fmt in ("docx", "both"):
                from datetime import datetime, timezone
                output_dir = PROJECT_ROOT / "output"
                output_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                docx_path = output_dir / f"resume-{timestamp}.docx"
                render_yaml_to_docx(yaml_str, docx_path)
                results.append(f"Generated Word document at {docx_path}")

            return " ".join(results) if results else "No output generated."
        except Exception as e:
            return f"Error generating resume: {e}"

    return [load_profile, load_jd, generate_resume]


def _create_agent(use_openai: bool, default_profile: Path):
    """Create the LangChain agent with tools."""
    from langchain.agents import create_agent
    from langchain_core.messages import SystemMessage

    if use_openai:
        from langchain_openai import ChatOpenAI
        model = ChatOpenAI(
            model=os.environ.get("RESUME_OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.1,
        )
    else:
        from langchain_ollama import ChatOllama
        model = ChatOllama(
            model=os.environ.get("RESUME_LLM_MODEL", "llama3"),
            base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
            temperature=0.1,
        )

    tools = _get_tools(default_profile, use_openai)
    system_prompt = """You are a helpful resume assistant. You help users generate tailored resumes from their profile and job descriptions.

You have access to these tools:
- load_profile(path): Load the user's profile from a file path
- load_jd(path_or_url): Load a job description from a file path or URL
- generate_resume(profile_path, jd_path=None, skills_to_highlight=None, extra_instructions=None, output_path=None, output_format=None): Generate a tailored resume. output_format can be "pdf", "docx", or "both".

When the user wants to generate a resume:
1. Use their profile (default: my-content/user_profile.md unless they specify another path)
2. Optionally use a job description if they provide one (file path or URL)
3. If they mention specific skills to emphasize (e.g. "highlight AWS and Kubernetes"), pass them as skills_to_highlight (comma-separated)
4. If they give other instructions (e.g. "emphasize backend", "focus on leadership"), pass them as extra_instructions

When the user asks for an editable document, Word document, .docx format, or format they can edit, call generate_resume with output_format="docx". When they want both PDF and Word, use output_format="both". Default is output_format="pdf".

IMPORTANT: When the user confirms they want to proceed (e.g. "yes", "proceed", "generate", "go ahead") and you have already loaded their profile and job description in this conversation, call generate_resume immediately. Do not ask for the same information again."""
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=SystemMessage(content=system_prompt),
    )
    return agent


def _extract_final_response(result: dict) -> str:
    """Extract the final assistant message from the agent result."""
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content and hasattr(msg, "type"):
            if getattr(msg, "type", "") == "ai" or "AI" in str(type(msg).__name__):
                return str(msg.content).strip()
        if isinstance(msg, dict):
            role = msg.get("role", msg.get("type", ""))
            content = msg.get("content", "")
            if role in ("ai", "assistant") and content:
                return str(content).strip()
    return "No response."


def run_chat(use_openai: bool = False, default_profile: Optional[Path] = None) -> None:
    """Run the chat REPL."""
    profile = default_profile or DEFAULT_PROFILE
    agent = _create_agent(use_openai, profile)
    print("Resume Assistant — type your message (or 'exit'/'quit' to leave)", flush=True)
    print(f"Default profile: {profile}", flush=True)
    print("-" * 50, flush=True)
    messages: list = []
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.", flush=True)
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.", flush=True)
            break
        try:
            messages.append({"role": "user", "content": user_input})
            result = agent.invoke({"messages": messages})
            messages = result.get("messages", messages)
            response = _extract_final_response(result)
            print(f"\nAssistant: {response}\n", flush=True)
        except Exception as e:
            print(f"\nError: {e}\n", flush=True, file=sys.stderr)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Chat with the resume generation agent.")
    parser.add_argument("--openai", action="store_true", help="Use OpenAI instead of Ollama")
    parser.add_argument("--profile", type=Path, default=None, help="Default profile path")
    args = parser.parse_args()
    run_chat(use_openai=args.openai, default_profile=args.profile)


if __name__ == "__main__":
    main()
