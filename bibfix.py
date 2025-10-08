def extract_citation_keys(tex_path):
    import re
    keys = set()
    cite_pattern = re.compile(r'\\cite[t|p]?\s*\{([^}]*)\}')
    with open(tex_path, 'r', encoding='utf-8') as f:
        # Remove all lines starting with %
        lines = [line for line in f if not line.lstrip().startswith('%')]
        # Join all lines into one string to handle multi-line cite commands
        text = ''.join(lines)
        for match in cite_pattern.finditer(text):
            for key in match.group(1).split(','):
                keys.add(key.strip())
    return keys
import re
# --- End Configuration ---

def normalize_string(s):
    # Remove special characters and lowercase
    return re.sub(r'[^a-zA-Z0-9 ]', '', s).lower().strip() if s else ''
#!/usr/bin/env python3
import bibtexparser
import json
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
import argparse
import os
import sys

# --- Configuration ---
DEFAULT_MAX_AUTHORS = -1  # Maximum authors before 'and others'
UNNECESSARY_FIELDS = {
    'abstract', 'file', 'keywords', 'mendeley-groups', 'comment',
    'url', 'urldate', 'doi', 'issn', 'isbn', 'note', 'month', 'day',
    'eprint', 'eprinttype', 'arxivid', 'archiveprefix',
    'timestamp', 'creationdate', 'lastchecked', 'mrnumber', 'zblnumber',
    'language', 'annotation', 'acknowledgement', 'pdf', 'editor'
}
# ESSENTIAL_FIELDS = {
#     'article': {'author', 'title', 'journal', 'month', 'year', 'volume', 'pages', 'doi'},  # all required fields by ieee
#     'book': {'title', 'year', 'publisher', 'state', 'place'},
#     'incollection': {'author', 'title', 'booktitle', 'publisher', 'year', 'pages'},
#     'inproceedings': {'author', 'title', 'booktitle', 'year', 'doi', 'address', 'pages'},  # all required fields by ieee
#     'proceedings': {'title', 'year', 'editor'},
#     'booklet': {'title', 'year'},
#     'manual': {'title', 'year'},
#     'techreport': {'author', 'title', 'institution', 'year', 'doi'},
#     'mastersthesis': {'author', 'title', 'school', 'year'},
#     'phdthesis': {'author', 'title', 'school', 'year'},
#     'misc': {'title', 'year', 'doi'},
#     'unpublished': {'author', 'title', 'note'},
# }

ESSENTIAL_FIELDS = {
    'article': {'author', 'title', 'journal', 'year', 'volume', 'number', 'pages'},
    'book': {'author', 'title', 'publisher', 'year', 'address'},
    'incollection': {'author', 'title', 'booktitle', 'publisher', 'year', 'pages'},
    'inproceedings': {'author', 'title', 'booktitle', 'month', 'year', 'pages', 'address'},
    'proceedings': {'title', 'year', 'editor', 'address'},
    'booklet': {'title', 'year'},
    'manual': {'title', 'organization', 'year', 'address'},
    'techreport': {'author', 'title', 'institution', 'year', 'number', 'address'},
    'mastersthesis': {'author', 'title', 'school', 'year', 'address'},
    'phdthesis': {'author', 'title', 'school', 'year', 'address'},
    'misc': {'author', 'title', 'note', 'month', 'year', 'doi'},
    'unpublished': {'author', 'title', 'note', 'month', 'year', 'doi'},
}


MONTHS = {
    'january': 'Jan', 
    'february': 'Feb', 
    'march': 'Mar', 
    'april': 'Apr', 
    'may': 'May', 
    'june': 'Jun',
    'july': 'Jul', 
    'august': 'Aug', 
    'september': 'Sep', 
    'october': 'Oct', 
    'november': 'Nov', 
    'december': 'Dec',
    'jan': 'Jan', 
    'feb': 'Feb', 
    'mar': 'Mar', 
    'apr': 'Apr', 
    'jun': 'Jun', 
    'jul': 'Jul', 
    'aug': 'Aug',
    'sep': 'Sep', 
    'oct': 'Oct', 
    'nov': 'Nov', 
    'dec': 'Dec'
}
# --- End Configuration ---

def truncate_authors(authors_string: str, max_authors: int) -> str:
    if not authors_string or max_authors < 0:
        return authors_string
    authors = [a.strip() for a in authors_string.split(' and ')]
    if len(authors) > max_authors:
        return ' and '.join(authors[:max_authors]) + ' and others'
    return authors_string


def build_title_exception_terms(abbreviations):
    exceptions = set()
    if not abbreviations:
        return exceptions

    def add_term(term):
        if not term:
            return
        term_lower = term.lower()
        sanitized = re.sub(r'[^a-z0-9]+', '', term_lower)
        if term_lower:
            exceptions.add(term_lower)
        if sanitized:
            exceptions.add(sanitized)
        for part in re.split(r'[\s\-]+', term):
            part = part.strip()
            if not part:
                continue
            part_lower = part.lower()
            sanitized_part = re.sub(r'[^a-z0-9]+', '', part_lower)
            exceptions.add(part_lower)
            if sanitized_part:
                exceptions.add(sanitized_part)

    for term in abbreviations.get('capitalize', []):
        add_term(term)

    return exceptions


def lowercase_alpha(text):
    return ''.join(char.lower() if char.isalpha() else char for char in text)


def capitalize_alpha(text):
    result = []
    capitalized = False
    for char in text:
        if not capitalized and char.isalpha():
            result.append(char.upper())
            capitalized = True
        elif char.isalpha():
            result.append(char.lower())
        else:
            result.append(char)
    return ''.join(result)



def capitalize_alpha(word: str) -> str:
    """Capitalize first alphabetic character only."""
    for i, c in enumerate(word):
        if c.isalpha():
            return word[:i] + c.upper() + word[i+1:].lower()
    return word

def lowercase_alpha(word: str) -> str:
    """Lowercase all alphabetic characters only."""
    return ''.join(c.lower() if c.isalpha() else c for c in word)

def apply_title_no_cap(title: str, exceptions: set[str]) -> str:
    if not title:
        return title

    # Split keeping whitespace
    chunks = re.split(r'(\s+)', title)
    processed = []
    word_index = 0
    capitalize_next = True  # start with first word

    for chunk in chunks:
        if not chunk:
            continue

        if chunk.isspace():
            processed.append(chunk)
            continue

        sanitized = re.sub(r'[^a-z0-9]+', '', chunk.lower())
        has_word = bool(sanitized)

        if has_word:
            uppercase_count = sum(1 for c in chunk if c.isupper())
            has_digits = any(c.isdigit() for c in chunk)

            preserve = False
            if exceptions and (sanitized in exceptions or chunk.lower() in exceptions):
                preserve = True
            elif uppercase_count >= 2 or chunk.isupper() or has_digits:
                preserve = True

            if preserve:
                processed.append(chunk)
            else:
                if capitalize_next:
                    processed.append(capitalize_alpha(chunk))
                else:
                    processed.append(lowercase_alpha(chunk))

            word_index += 1
            capitalize_next = False
        else:
            processed.append(chunk)
            # If chunk contains punctuation that ends a sentence, reset
            if re.search(r'[.:;!?]\s*$', chunk):
                capitalize_next = True

    return ''.join(processed)

def clean_entry(entry: dict, max_authors: int, minimal=False, abbreviations=None, no_cap=False, title_exceptions=None):

    entry_type = entry.get('ENTRYTYPE', '').lower()
    entry_id = entry.get('ID', '<UNKNOWN>')
    cleaned = {'ENTRYTYPE': entry.get('ENTRYTYPE', 'misc'), 'ID': entry_id}

    required = set(ESSENTIAL_FIELDS.get(entry_type, set()))
    found = set()
    has_either = False

    # Only include essential fields (plus ENTRYTYPE and ID)
    for key, val in entry.items():
        kl = key.lower()
        if kl in required:
            cleaned[key] = val
            found.add(kl)
        if entry_type in ('book', 'proceedings') and kl in ('author', 'editor'):
            has_either = True

    # Standardize month field (after copying essential fields)
    if 'month' in cleaned:
        m = str(cleaned['month']).strip().lower()
        num_map = {
            '1': 'Jan', '01': 'Jan', '2': 'Feb', '02': 'Feb', '3': 'Mar', '03': 'Mar',
            '4': 'Apr', '04': 'Apr', '5': 'May', '05': 'May', '6': 'Jun', '06': 'Jun',
            '7': 'Jul', '07': 'Jul', '8': 'Aug', '08': 'Aug', '9': 'Sep', '09': 'Sep',
            '10': 'Oct', '11': 'Nov', '12': 'Dec'
        }
        if m in MONTHS:
            cleaned['month'] = MONTHS[m]
        elif m in num_map:
            cleaned['month'] = num_map[m]
        else:
            cleaned['month'] = m.capitalize()

    # Decapitalize title if --no-cap and not book (after copying essential fields)
    if no_cap and entry_type != 'book' and 'title' in cleaned:
        cleaned['title'] = apply_title_no_cap(cleaned['title'], title_exceptions or set())

    # Abbreviation logic for minimal mode
    if minimal and abbreviations:
        # For articles and inproceedings
        if entry_type == 'article':
            # Journal abbreviation
            journal = cleaned.get('journal')
            if journal:
                norm_journal = normalize_string(journal)
                for abbr, full in abbreviations.get('journal_abbreviations', {}).items():
                    if norm_journal == normalize_string(full):
                        cleaned['journal'] = abbr
                        break
            # Conference abbreviation (for inproceedings)
            booktitle = cleaned.get('booktitle')
            if booktitle:
                norm_booktitle = normalize_string(booktitle)
                for abbr, fulls in abbreviations.get('conference_abbreviations', {}).items():
                    for full in fulls:
                        if norm_booktitle == normalize_string(full):
                            cleaned['booktitle'] = abbr
                            break
        # For proceedings
        elif entry_type == 'inproceedings':
            title = cleaned.get('booktitle')
            if title:
                norm_title = normalize_string(title)
                for abbr, fulls in abbreviations.get('conference_abbreviations', {}).items():
                    norm_abbr = normalize_string(abbr)
                    for full in fulls:
                        norm_full = normalize_string(full)
                        if norm_abbr in norm_title or norm_full in norm_title:
                            cleaned['booktitle'] = abbr
                            break

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
    parser.add_argument('--minimal', action='store_true',
                        help="Remove url and urldate even if doi is missing")
    parser.add_argument('--no-cap', action='store_true',
                        help="Remove capitalization from the title except for the first word (not for books)")
    parser.add_argument('--only-cited', action='store_true')
    args = parser.parse_args()

    if not os.path.isfile(args.input_bib):
        print(f"Error: file not found: {args.input_bib}", file=sys.stderr)
        sys.exit(1)

    base, ext = os.path.splitext(args.input_bib)
    output_bib = f"{base}_cleaned.bib"

    with open(args.input_bib, 'r', encoding='utf-8') as bibfile:
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        db = bibtexparser.load(bibfile, parser=parser)

    # Load abbreviations.json
    abbreviations = None
    title_exceptions = set()
    abbr_path = os.path.join(os.path.dirname(__file__), 'abbreviations.json')
    if os.path.isfile(abbr_path):
        with open(abbr_path, 'r', encoding='utf-8') as abbr_file:
            abbreviations = json.load(abbr_file)
            title_exceptions = build_title_exception_terms(abbreviations)
            print(abbreviations)
    

    # Extract citation keys from manuscript.tex
    if args.only_cited:
        tex_path = os.path.join(os.path.dirname(__file__), 'manuscript.tex')
    else:
        tex_path = ""

    if os.path.isfile(tex_path):
        used_keys = extract_citation_keys(tex_path)
    else:
        used_keys = None

    all_warnings = []
    cleaned_entries = []
    for entry in db.entries:
        entry_id = entry.get('ID', None)
        if used_keys is not None and entry_id not in used_keys:
            continue
        cleaned, warns = clean_entry(
            entry,
            args.max_authors,
            minimal=args.minimal,
            abbreviations=abbreviations,
            no_cap=args.no_cap,
            title_exceptions=title_exceptions,
        )
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
