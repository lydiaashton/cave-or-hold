# Manuscript

## Layout

```
paper/
  main.tex            document shell, section inputs, bibliography
  sections/*.tex      one file per section, one owner per file
  refs.bib            citations, DOI or arXiv ID required
  figures/            figures, PDF or PNG
  REFERENCES_CHECK.md citation verification table
  CLAIMS.md           number-to-output trace table
```

## How to work on it

One file per section means two people editing different sections never
collide. `git blame` on `sections/` gives per-section authorship.

1. Branch: `git checkout -b section/<name>`
2. Edit only your section file.
3. Open a PR and name a reviewer.
4. The build action attaches the compiled PDF to the PR, so reviewers do not
   need LaTeX installed.

**You do not need to use git to contribute.** Write in whatever you like and
send it; it will be committed with you credited in the commit message.

## Two rules

1. **No citation without a DOI or arXiv ID and the name of whoever opened it.**
   Recorded in `refs.bib` as a `note` field and in `REFERENCES_CHECK.md`.
2. **No number in the manuscript without a row in `CLAIMS.md`** naming the
   analysis output it came from and a second person who re-ran the trace.

## Building locally

```
cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main
```
