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
import threading
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PROFILE = PROJECT_ROOT / "my-content" / "user_profile.md"
DEFAULT_OUTPUT = PROJECT_ROOT / "resources" / "resume_sections.tex"


def _get_tools(
    default_profile_path: Path,
    use_openai: bool = False,
    draft: Optional[dict[str, Any]] = None,
):
    """Build LangChain tools that close over default_profile_path, use_openai, and draft."""
    import tailor
    from generate_resume import compile_latex_to_pdf, render_yaml_to_docx, render_yaml_to_latex

    from langchain_core.tools import tool

    if draft is None:
        draft = {}

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

            draft["yaml"] = yaml_str

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

            msg = " ".join(results) if results else "No output generated."
            return f"{msg} Resume content has been saved as the current draft for this session."
        except Exception as e:
            return f"Error generating resume: {e}"

    @tool
    def get_draft_content() -> str:
        """Return the current draft resume content (YAML) for this session. Use when the user
        asks to see the content for approval. Returns a message if no draft exists yet."""
        yaml_str = draft.get("yaml") if draft else None
        if not yaml_str or not yaml_str.strip():
            return "No draft content yet. Generate resume content first (e.g. get_resume_content or generate_resume)."
        return yaml_str

    @tool
    def update_draft_content(yaml_content: str) -> str:
        """Set the current draft resume content to the given YAML. Use this when the user has
        approved or refined content and you have the full YAML (e.g. after you showed refined
        content and the user said 'use this' or 'generate PDF with this'). Keeps the draft in
        sync so generate_pdf_from_draft uses the latest content."""
        if not yaml_content or not yaml_content.strip():
            return "Error: YAML content is empty. Provide the full resume YAML."
        draft["yaml"] = yaml_content.strip()
        return "Draft updated. You can generate the PDF with generate_pdf_from_draft when ready."

    @tool
    def generate_pdf_from_draft(
        output_format: Optional[str] = None,
    ) -> str:
        """Generate PDF (and optionally docx) from the current draft content without calling
        the LLM. Use this when the user is satisfied with the content and asks to generate
        the PDF (or 'generate with this content'). output_format: 'pdf' (default), 'docx',
        or 'both'. If no draft exists, returns an error asking to generate content first."""
        yaml_str = draft.get("yaml") if draft else None
        if not yaml_str or not yaml_str.strip():
            return "No draft content. Generate resume content first or provide YAML, then generate the PDF."
        fmt = (output_format or "pdf").strip().lower()
        if fmt not in ("pdf", "docx", "both"):
            fmt = "pdf"
        out_path = DEFAULT_OUTPUT
        if not out_path.is_absolute():
            out_path = PROJECT_ROOT / out_path
        out_path = out_path.resolve()
        try:
            results = []
            if fmt in ("pdf", "both"):
                render_yaml_to_latex(yaml_str, out_path)
                pdf_path = compile_latex_to_pdf()
                if pdf_path:
                    results.append(f"Generated resume PDF at {pdf_path}")
                else:
                    results.append("LaTeX written; PDF compilation failed (ensure XeLaTeX is installed).")
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
            return f"Error generating from draft: {e}"

    @tool
    def get_resume_content(
        profile_path: str,
        jd_path: Optional[str] = None,
        skills_to_highlight: Optional[str] = None,
        extra_instructions: Optional[str] = None,
    ) -> str:
        """Get tailored resume content from the LLM (profile + optional job description) and
        store it as the current draft. Does NOT render to LaTeX or compile to PDF. Use when
        the user wants to see content for approval before generating PDF. profile_path is
        required. jd_path is optional (file or URL). skills_to_highlight: comma-separated
        list. extra_instructions: additional guidance. Returns the YAML content so you can
        show it to the user."""
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
            draft["yaml"] = yaml_str
            return yaml_str
        except Exception as e:
            return f"Error getting resume content: {e}"

    return [
        load_profile,
        load_jd,
        get_resume_content,
        get_draft_content,
        update_draft_content,
        generate_pdf_from_draft,
        generate_resume,
    ]


def _create_agent(use_openai: bool, default_profile: Path, draft: dict[str, Any]):
    """Create the LangChain agent with tools. draft is the session draft container (mutable)."""
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

    tools = _get_tools(default_profile, use_openai, draft)
    system_prompt = """You are a helpful resume assistant. You help users generate tailored resumes from their profile and job descriptions.

DRAFT: The "current resume content" for this session is the draft. Generating content (via get_resume_content or generate_resume) or updating content (via update_draft_content) sets the draft. When the user asks to generate the PDF after refinements, use generate_pdf_from_draft so the PDF uses the latest content. Only call generate_resume when the user explicitly wants a fresh generation from profile/JD (e.g. new JD, or "regenerate from scratch").

You have access to these tools:
- load_profile(path): Load the user's profile from a file path
- load_jd(path_or_url): Load a job description from a file path or URL
- get_resume_content(profile_path, jd_path=None, skills_to_highlight=None, extra_instructions=None): Get tailored content from the LLM and store as draft; returns YAML for you to show. Does NOT create PDF. Use when the user wants to see content for approval first.
- get_draft_content(): Return the current draft YAML. Use when the user asks to see the content for approval (if draft exists).
- update_draft_content(yaml_content): Set the draft to the given YAML. Whenever you output revised resume YAML for the user's approval (e.g. after refining a section), you MUST call update_draft_content with the full refined YAML so the draft stays in sync.
- generate_pdf_from_draft(output_format=None): Generate PDF (and optionally docx) from the current draft without calling the LLM. Use when the user is satisfied and asks to generate the PDF or "generate with this content". output_format: "pdf", "docx", or "both".
- generate_resume(profile_path, jd_path=None, skills_to_highlight=None, extra_instructions=None, output_path=None, output_format=None): Fresh generation from profile + JD; writes LaTeX and compiles. Also updates the draft. Use only when the user wants a new run from profile (e.g. new job description or "regenerate from scratch").

When the user wants to see content for approval: use get_draft_content() if draft exists; otherwise get_resume_content(...) first. When they refine a section and you produce revised YAML in your reply, call update_draft_content(full_refined_yaml). When they say they are satisfied and want the PDF, call generate_pdf_from_draft(output_format).

When the user wants a fresh resume from profile/JD: use their profile (default: my-content/user_profile.md), optionally load_jd or pass jd_path to get_resume_content or generate_resume. For editable/Word format use output_format="docx" or "both"."""
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


def _patch_shift_enter_for_newline() -> None:
    """Map Shift+Enter to ControlJ (newline) so it inserts newline instead of sending."""
    from prompt_toolkit.input import ansi_escape_sequences
    from prompt_toolkit.keys import Keys

    # xterm modifyOtherKeys format; Kitty protocol uses \x1b[13;2u
    for seq in ("\x1b[27;2;13~", "\x1b[13;2u"):
        ansi_escape_sequences.ANSI_SEQUENCES[seq] = Keys.ControlJ


def _create_chat_key_bindings():
    """Key bindings: Enter=send, Shift+Enter=newline, Ctrl+J=newline (fallback)."""
    from prompt_toolkit.key_binding import KeyBindings

    _patch_shift_enter_for_newline()

    kb = KeyBindings()

    @kb.add("enter")
    def _accept(event):
        event.current_buffer.validate_and_handle()

    @kb.add("c-j")
    def _newline(event):
        event.current_buffer.newline()

    return kb


def _read_multiline_input(prompt: str = "You: ") -> str:
    """Read multi-line input. Enter=send, Shift+Enter or Ctrl+J=newline."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import merge_key_bindings
    from prompt_toolkit.key_binding.defaults import load_key_bindings

    session = PromptSession(
        multiline=True,
        prompt_continuation="    ",
        key_bindings=merge_key_bindings([
            load_key_bindings(),
            _create_chat_key_bindings(),
        ]),
    )
    return session.prompt(prompt)


def _thinking_spinner(stop_event: threading.Event, message: str = "Thinking...") -> None:
    """Run a simple spinner in a loop until stop_event is set. Used from a daemon thread."""
    frames = ["|", "/", "-", "\\"]
    idx = 0
    while not stop_event.is_set():
        frame = frames[idx % len(frames)]
        print(f"\r  {message}  {frame}", end="", flush=True)
        idx += 1
        stop_event.wait(timeout=0.12)


def run_chat(use_openai: bool = False, default_profile: Optional[Path] = None) -> None:
    """Run the chat REPL."""
    profile = default_profile or DEFAULT_PROFILE
    draft: dict[str, Any] = {"yaml": None}
    agent = _create_agent(use_openai, profile, draft)
    print("Resume Assistant — type your message (or 'exit'/'quit' to leave)", flush=True)
    print("Enter=send, Shift+Enter or Ctrl+J=new line.", flush=True)
    print(f"Default profile: {profile}", flush=True)
    print("-" * 50, flush=True)
    messages: list = []
    while True:
        try:
            user_input = _read_multiline_input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.", flush=True)
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.", flush=True)
            break
        stop_event = threading.Event()
        spinner_thread = None
        try:
            messages.append({"role": "user", "content": user_input})
            if sys.stdout.isatty():
                spinner_thread = threading.Thread(
                    target=_thinking_spinner,
                    args=(stop_event,),
                    daemon=True,
                )
                spinner_thread.start()
            try:
                result = agent.invoke({"messages": messages})
                messages = result.get("messages", messages)
                response = _extract_final_response(result)
                print(f"\nAssistant: {response}\n", flush=True)
            finally:
                if spinner_thread is not None:
                    stop_event.set()
                    spinner_thread.join(timeout=0.5)
                    print(f"\r{' ' * (len('  Thinking...  '))}\r", end="", flush=True)
        except Exception as e:
            if spinner_thread is not None:
                stop_event.set()
                spinner_thread.join(timeout=0.5)
                print(f"\r{' ' * (len('  Thinking...  '))}\r", end="", flush=True)
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
