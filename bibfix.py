#!/usr/bin/env python3
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
import argparse
import os
import sys

# --- Configuration ---
DEFAULT_MAX_AUTHORS = 4  # Maximum authors before 'and others'
UNNECESSARY_FIELDS = {
    'abstract', 'file', 'keywords', 'mendeley-groups', 'comment',
    'url', 'urldate', 'doi', 'issn', 'isbn', 'note', 'month', 'day',
    'eprint', 'eprinttype', 'arxivid', 'archiveprefix',
    'timestamp', 'creationdate', 'lastchecked', 'mrnumber', 'zblnumber',
    'language', 'annotation', 'acknowledgement', 'pdf',
}
ESSENTIAL_FIELDS = {
    'article': {'author', 'title', 'journal', 'year', 'volume', 'doi'},
    'book': {'title', 'year', 'publisher'},
    'incollection': {'author', 'title', 'booktitle', 'publisher', 'year', 'pages'},
    'inproceedings': {'author', 'title', 'booktitle', 'year', 'doi'},
    'proceedings': {'title', 'year', 'editor'},
    'booklet': {'title', 'year'},
    'manual': {'title', 'year'},
    'techreport': {'author', 'title', 'institution', 'year', 'doi'},
    'mastersthesis': {'author', 'title', 'school', 'year'},
    'phdthesis': {'author', 'title', 'school', 'year'},
    'misc': {'title', 'year', 'doi'},
    'unpublished': {'author', 'title', 'note', 'year'},
}
# --- End Configuration ---

def truncate_authors(authors_string: str, max_authors: int) -> str:
    if not authors_string:
        return authors_string
    authors = [a.strip() for a in authors_string.split(' and ')]
    if len(authors) > max_authors:
        return ' and '.join(authors[:max_authors]) + ' and others'
    return authors_string


def clean_entry(entry: dict, max_authors: int):
    entry_type = entry.get('ENTRYTYPE', '').lower()
    entry_id = entry.get('ID', '<UNKNOWN>')
    cleaned = {'ENTRYTYPE': entry.get('ENTRYTYPE', 'misc'), 'ID': entry_id}
    required = set(ESSENTIAL_FIELDS.get(entry_type, set()))
    found = set()
    has_either = False

    for key, val in entry.items():
        kl = key.lower()
        if kl in UNNECESSARY_FIELDS:
            # Keep 'doi' if essential for this entry type
            if kl == 'doi' and 'doi' in required:
                cleaned[key] = val
                found.add(kl)
            else:
                continue
        cleaned[key] = val
        if kl in required:
            found.add(kl)
        if entry_type in ('book', 'proceedings') and kl in ('author', 'editor'):
            has_either = True

    if 'author' in cleaned:
        cleaned['author'] = truncate_authors(cleaned['author'], max_authors)

    missing = required - found
    if entry_type in ('book', 'proceedings'):
        if has_either:
            missing.discard('author')
            missing.discard('editor')
        else:
            missing.add('author or editor')
    warnings = []
    if missing:
        warnings.append(f"Entry '{entry_id}' missing: {', '.join(sorted(missing))}")
    return cleaned, warnings


def main():
    parser = argparse.ArgumentParser(description="Clean a .bib file and summarize missing fields.")
    parser.add_argument('input_bib', help="Path to input .bib file")
    parser.add_argument('--max-authors', type=int, default=DEFAULT_MAX_AUTHORS,
                        help="Max number of authors before 'and others'")
    args = parser.parse_args()

    if not os.path.isfile(args.input_bib):
        print(f"Error: file not found: {args.input_bib}", file=sys.stderr)
        sys.exit(1)

    base, ext = os.path.splitext(args.input_bib)
    output_bib = f"{base}_cleaned.bib"

    with open(args.input_bib, 'r', encoding='utf-8') as bibfile:
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        db = bibtexparser.load(bibfile, parser=parser)

    all_warnings = []
    cleaned_entries = []
    for entry in db.entries:
        cleaned, warns = clean_entry(entry, args.max_authors)
        cleaned_entries.append(cleaned)
        all_warnings.extend(warns)

    cleaned_db = BibDatabase()
    cleaned_db.entries = cleaned_entries
    writer = BibTexWriter()
    writer.indent = '    '
    writer.comma_first = False
    with open(output_bib, 'w', encoding='utf-8') as out:
        bibtexparser.dump(cleaned_db, out, writer)

    print(f"Wrote cleaned bibliography to {output_bib}")
    if all_warnings:
        print("\nSummary of missing fields:")
        for w in all_warnings:
            print(f" - {w}")
    else:
        print("\nNo missing essential fields detected.")

if __name__ == '__main__':
    main()
