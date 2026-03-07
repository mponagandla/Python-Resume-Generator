.PHONY: generate build build-docx build-tailored clean init-profile

generate:
	pipenv run python generate_resume.py

build: generate
	cd resources && xelatex -interaction=batchmode resume.tex
	@timestamp=$$(date +%Y%m%d-%H%M%S); \
	mkdir -p output; \
	cp resources/resume.pdf output/resume-$$timestamp.pdf; \
	echo "Saved output/resume-$$timestamp.pdf"

# Generate Word document only (no LaTeX/PDF).
build-docx:
	pipenv run python generate_resume.py --format docx
	@echo "Saved output/resume-*.docx"

# Tailor resume to a job description then build.
# Usage: make build-tailored JOB_DESC=path/to/jd.txt
# Word output: make build-tailored JOB_DESC=jd.txt FORMAT=docx
# Use OpenAI: make build-tailored JOB_DESC=misc/job-descriptions/jd.txt OPENAI=1
build-tailored:
	@if [ -z "$(JOB_DESC)" ]; then echo "Error: JOB_DESC required. Example: make build-tailored JOB_DESC=misc/job-descriptions/jd.txt"; exit 1; fi
	pipenv run python generate_resume.py --tailor "$(JOB_DESC)" $(if $(OPENAI),--openai,) $(if $(FORMAT),--format $(FORMAT),)
	@if [ "$(FORMAT)" != "docx" ]; then \
		cd resources && xelatex -interaction=batchmode resume.tex; \
		timestamp=$$(date +%Y%m%d-%H%M%S); \
		mkdir -p output; \
		cp resources/resume.pdf output/resume-$$timestamp.pdf; \
		echo "Saved output/resume-$$timestamp.pdf"; \
	else \
		echo "Saved output/resume-*.docx"; \
	fi

# Copy example user profile to my-content so you can fill it once and use it for tailoring.
init-profile:
	@mkdir -p my-content
	cp resources/example_user_profile.md my-content/user_profile.md
	@echo "Created my-content/user_profile.md — edit it with your details, then use --tailor for profile-based resume generation."

clean:
	cd resources && rm -f resume.pdf resume.aux resume.log resume.out resume.fls resume.fdb_latexmk
	rm -f resources/resume_sections.tex
