.PHONY: generate build clean

generate:
	pipenv run python generate_resume.py

build: generate
	cd resources && xelatex -interaction=nonstopmode resume.tex

clean:
	cd resources && rm -f resume.pdf resume.aux resume.log resume.out resume.fls resume.fdb_latexmk
	rm -f resources/resume_sections.tex
