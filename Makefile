.PHONY: generate build build-tailored clean

generate:
	pipenv run python generate_resume.py

build: generate
	cd resources && xelatex -interaction=nonstopmode resume.tex
	@timestamp=$$(date +%Y%m%d-%H%M%S); \
	mkdir -p output; \
	cp resources/resume.pdf output/resume-$$timestamp.pdf; \
	echo "Saved output/resume-$$timestamp.pdf"

# Tailor resume to a job description then build. Usage: make build-tailored JOB_DESC=path/to/jd.txt
build-tailored:
	@if [ -z "$(JOB_DESC)" ]; then echo "Error: JOB_DESC required. Example: make build-tailored JOB_DESC=job-descriptions/jd.txt"; exit 1; fi
	pipenv run python generate_resume.py --tailor "$(JOB_DESC)"
	cd resources && xelatex -interaction=nonstopmode resume.tex
	@timestamp=$$(date +%Y%m%d-%H%M%S); \
	mkdir -p output; \
	cp resources/resume.pdf output/resume-$$timestamp.pdf; \
	echo "Saved output/resume-$$timestamp.pdf"

clean:
	cd resources && rm -f resume.pdf resume.aux resume.log resume.out resume.fls resume.fdb_latexmk
	rm -f resources/resume_sections.tex
