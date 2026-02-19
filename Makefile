.PHONY: generate build clean

generate:
	pipenv run python generate_resume.py

build: generate
	cd resources && xelatex -interaction=nonstopmode resume.tex
	@timestamp=$$(date +%Y%m%d-%H%M%S); \
	mkdir -p output; \
	cp resources/resume.pdf output/resume-$$timestamp.pdf; \
	echo "Saved output/resume-$$timestamp.pdf"

clean:
	cd resources && rm -f resume.pdf resume.aux resume.log resume.out resume.fls resume.fdb_latexmk
	rm -f resources/resume_sections.tex
