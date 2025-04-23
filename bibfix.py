#!/usr/bin/env python3
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
import argparse
import os
import sys

# --- Configuration ---

# Maximum number of authors to keep before adding "and others"
DEFAULT_MAX_AUTHORS = 3

# Fields to remove completely
UNNECESSARY_FIELDS = {
    'abstract', 'file', 'keywords', 'mendeley-groups', 'comment',
    'url', 'urldate', 'doi', # Keep DOI if you prefer, but often added by publisher
    'issn', 'isbn', 'note', 'month', 'day',
    'eprint', 'eprinttype', 'arxivId', 'archiveprefix', # For arXiv info
    'timestamp', 'creationdate', 'lastchecked',
    'mrnumber', 'zblnumber', # Mathematical reviews numbers
    'language', 'annotation', 'acknowledgement', 'pdf',
    # Add any other fields you consistently want to remove
}

# Essential fields per entry type (lowercase). Add more types if needed.
# Warnings will be printed for entries missing these fields.
ESSENTIAL_FIELDS = {
    'article': {'author', 'title', 'journal', 'year', 'volume'}, # 'pages', 'number' often good too
    'book': {'title', 'year', 'publisher'}, # Needs 'author' OR 'editor'
    'incollection': {'author', 'title', 'booktitle', 'publisher', 'year', 'pages'}, # 'editor' often good too
    'inproceedings': {'author', 'title', 'booktitle', 'year'}, # 'pages', 'publisher', 'organization', 'editor' often good
    'proceedings': {'title', 'year', 'editor'}, # 'publisher', 'organization' often good
    'booklet': {'title', 'year'}, # 'author', 'howpublished', 'address' often good
    'manual': {'title', 'year'}, # 'author', 'organization', 'edition' often good
    'techreport': {'author', 'title', 'institution', 'year'}, # 'number', 'type' often good
    'mastersthesis': {'author', 'title', 'school', 'year'},
    'phdthesis': {'author', 'title', 'school', 'year'},
    'misc': {'title', 'year'}, # Very flexible, maybe 'author', 'howpublished'
    'unpublished': {'author', 'title', 'note', 'year'},
}
# --- End Configuration ---

def truncate_authors(authors_string, max_authors):
    """Truncates author list string if it exceeds max_authors."""
    if not authors_string:
        return authors_string
    try:
        # Split authors based on ' and '
        authors = authors_string.split(' and ')
        if len(authors) > max_authors:
            # Keep the first max_authors and add "and others"
            truncated_authors = authors[:max_authors]
            return ' and '.join(truncated_authors) + ' and others'
        else:
            # No truncation needed
            return authors_string
    except Exception as e:
        print(f"      Warning: Could not parse/truncate authors: '{authors_string[:50]}...'. Error: {e}", file=sys.stderr)
        return authors_string # Return original on error


def clean_entry(entry, max_authors):
    """Cleans a single BibTeX entry dictionary."""
    entry_type = entry.get('ENTRYTYPE', '').lower()
    entry_id = entry.get('ID', 'UNKNOWN_ID')
    cleaned_entry = {'ENTRYTYPE': entry.get('ENTRYTYPE', 'misc'), 'ID': entry_id} # Start fresh
    missing_essential = []
    has_author_or_editor = False

    print(f"  Processing [{entry_id}] ({entry_type})...")

    # 1. Check for essential fields and copy desired fields
    required = set(ESSENTIAL_FIELDS.get(entry_type, set()))

    for key, value in entry.items():
        key_lower = key.lower()

        # Skip unnecessary fields
        if key_lower in UNNECESSARY_FIELDS:
            # print(f"      Removing field: {key}") # Uncomment for verbose removal log
            continue

        # Keep the field
        cleaned_entry[key] = value

        # Check if required field is present
        if key_lower in required:
            required.remove(key_lower) # Mark as found

        # Special check for book/proceedings needing author OR editor
        if entry_type in ('book', 'proceedings') and key_lower in ('author', 'editor'):
            has_author_or_editor = True

    # 2. Author Truncation
    if 'author' in cleaned_entry:
        original_authors = cleaned_entry['author']
        cleaned_entry['author'] = truncate_authors(original_authors, max_authors)
        if cleaned_entry['author'] != original_authors:
            print(f"      Truncated authors for [{entry_id}]")

    # 3. Final Essential Field Check
    missing_essential = list(required)
    # Special case for book/proceedings: remove 'author' and 'editor' if one was found
    if entry_type in ('book', 'proceedings'):
        if has_author_or_editor:
            if 'author' in missing_essential: missing_essential.remove('author')
            if 'editor' in missing_essential: missing_essential.remove('editor')
        else:
             # If neither found, add a generic requirement back for the warning
             missing_essential.append('author or editor')


    if missing_essential:
        print(f"      Warning: Entry [{entry_id}] might be missing essential fields for type '{entry_type}': {', '.join(missing_essential)}", file=sys.stderr)

    return cleaned_entry


def main():
    parser = argparse.ArgumentParser(
        description="Clean a BibTeX file: remove unnecessary fields, check essentials, truncate authors.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Shows default values in help
    )
    parser.add_argument(
        "--original-references",
        dest="input_file",  # Still store it internally as 'input_file' for consistency
        required=True,
        help="Path to the original input .bib file."
    )
    parser.add_argument(
        "--cleaned-references",
        dest="output_file", # Still store it internally as 'output_file'
        required=True,
        help="Path to write the cleaned output .bib file."
    )
    parser.add_argument(
        "--max-authors",
        type=int,
        default=DEFAULT_MAX_AUTHORS,
        help="Maximum number of authors to list before using 'and others'."
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Encoding of the input/output files."
    )
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Starting BibTeX cleanup...")
    print(f"  Original References: {args.input_file}") # Updated print statement
    print(f"  Cleaned References: {args.output_file}")  # Updated print statement
    print(f"  Max authors: {args.max_authors}")
    print(f"  Encoding: {args.encoding}")
    print("-" * 20)

    # Read the BibTeX file
    try:
        with open(args.input_file, 'r', encoding=args.encoding) as bibfile:
            # Use common_strings=False to avoid issues with undefined @string variables
            # if you don't have them defined in your file.
            bib_database = bibtexparser.load(bibfile, parser=bibtexparser.bparser.BibTexParser(common_strings=False))
    except Exception as e:
        print(f"Error parsing BibTeX file: {e}", file=sys.stderr)
        sys.exit(1)

    # Process entries
    cleaned_entries = []
    print(f"Found {len(bib_database.entries)} entries. Processing...")
    for entry in bib_database.entries:
        cleaned_entry = clean_entry(entry, args.max_authors)
        cleaned_entries.append(cleaned_entry)

    # Create a new database with cleaned entries
    cleaned_db = BibDatabase()
    cleaned_db.entries = cleaned_entries

    # Write the cleaned BibTeX file
    try:
        writer = BibTexWriter()
        writer.indent = '    ' # Use 4 spaces for indentation
        writer.comma_first = False # Put comma at the end of the field
        with open(args.output_file, 'w', encoding=args.encoding) as bibfile:
             bibtexparser.dump(cleaned_db, bibfile, writer=writer)
            # bibfile.write(writer.write(cleaned_db)) # Alternative way using writer directly

    except Exception as e:
        print(f"Error writing cleaned BibTeX file: {e}", file=sys.stderr)
        sys.exit(1)

    print("-" * 20)
    print(f"Successfully cleaned {len(cleaned_entries)} entries.")
    print(f"Cleaned file saved to: {args.output_file}")
    print("Please review the output file and check the warnings printed above.")

if __name__ == "__main__":
    main()