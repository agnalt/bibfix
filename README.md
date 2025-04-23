# BibFix

Bibfix is a simple project that simplifies the cleaning of bibliography files before submission of a paper. 

## Features

- Clean and standardize bibliographic data.
- Shorten the lists of authors using "et. al.".
- Remove unnessecary bib entries.

## Usage

1. Clone the repository or navigate to the directory.
2. Use your reference manager to create a .bib-file.
3. Run `bibfix.py path/to/bibfile.bib --max-authors 4` 

Now, you will find a cleaned copy of your .bib-file at `path/to/bibfile_cleaned.bib`.
## Requirements
- Python 3.x
- Required dependencies (install using `pip install -r requirements.txt`)

