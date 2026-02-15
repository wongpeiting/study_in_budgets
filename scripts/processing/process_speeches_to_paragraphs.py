#!/usr/bin/env python3
"""
Process budget speeches into individual paragraphs for analysis.

This script:
1. Merges short lines (< 80 chars) with adjacent text
2. Splits long paragraphs (> 800 chars) at sentence boundaries
3. Merges lines that don't end with proper punctuation
4. Preserves all metadata for each paragraph
"""

import csv
import re
from pathlib import Path
from typing import List, Dict, Tuple


def load_metadata(metadata_path: str) -> Dict[str, Dict]:
    """Load metadata from CSV file and index by filename."""
    metadata = {}
    with open(metadata_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            metadata[row['file_name']] = row
    return metadata


def ends_with_sentence_terminator(text: str) -> bool:
    """Check if text ends with proper punctuation."""
    text = text.rstrip()
    if not text:
        return False
    # Check for sentence endings
    return text[-1] in '.!?;:' or text.endswith('...')


def find_sentence_break(text: str, target_pos: int) -> int:
    """
    Find a good sentence break near the target position.
    Returns position after the sentence terminator.
    """
    # Look for sentence terminators near the target position
    # Search within +/- 200 chars of target
    search_start = max(0, target_pos - 200)
    search_end = min(len(text), target_pos + 200)
    search_region = text[search_start:search_end]

    # Find all sentence terminators in the region
    terminators = []
    for match in re.finditer(r'[.!?]+\s', search_region):
        pos = search_start + match.end()
        terminators.append(pos)

    if not terminators:
        # No good break found, return target
        return target_pos

    # Find the terminator closest to target
    closest = min(terminators, key=lambda x: abs(x - target_pos))
    return closest


def process_lines_to_paragraphs(lines: List[str]) -> List[str]:
    """
    Process lines into paragraphs according to the rules:
    1. Merge short lines (< 80 chars) with adjacent text
    2. Merge lines that don't end with proper punctuation
    3. Split long paragraphs (> 800 chars) at sentence boundaries
    """
    # First, merge lines into initial paragraphs
    paragraphs = []
    current_para = []

    for line in lines:
        line = line.strip()

        # Skip empty lines - they mark paragraph boundaries
        if not line:
            if current_para:
                paragraphs.append(' '.join(current_para))
                current_para = []
            continue

        # Add line to current paragraph
        current_para.append(line)

        # Check if we should end the paragraph
        # End if line is long enough AND ends with proper punctuation
        if len(line) >= 80 and ends_with_sentence_terminator(line):
            paragraphs.append(' '.join(current_para))
            current_para = []

    # Don't forget the last paragraph
    if current_para:
        paragraphs.append(' '.join(current_para))

    # Now split long paragraphs
    final_paragraphs = []
    for para in paragraphs:
        if len(para) <= 800:
            final_paragraphs.append(para)
        else:
            # Split at sentence boundaries
            remaining = para
            while len(remaining) > 800:
                # Find a good break point around position 800
                break_pos = find_sentence_break(remaining, 800)

                # Extract the chunk
                chunk = remaining[:break_pos].strip()
                if chunk:
                    final_paragraphs.append(chunk)

                # Continue with the rest
                remaining = remaining[break_pos:].strip()

            # Add the final chunk
            if remaining:
                final_paragraphs.append(remaining)

    # Filter out very short paragraphs (likely artifacts)
    final_paragraphs = [p for p in final_paragraphs if len(p) > 10]

    return final_paragraphs


def process_speech_file(file_path: Path, metadata: Dict) -> List[Dict]:
    """Process a single speech file into paragraphs with metadata."""
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Process into paragraphs
    paragraphs = process_lines_to_paragraphs(lines)

    # Create result with metadata
    results = []
    for i, para in enumerate(paragraphs, 1):
        result = {
            'paragraph_id': f"{metadata['speech_id']}_{i}",
            'speech_id': metadata['speech_id'],
            'paragraph_num': i,
            'paragraph_text': para,
            'paragraph_length': len(para),
            'year': metadata['year'],
            'date': metadata['date'],
            'fm_name': metadata['fm_name'],
            'pm_name': metadata['pm_name'],
            'parliament_term': metadata['parliament_term'],
            'election_budget': metadata['election_budget'],
            'file_name': metadata['file_name']
        }
        results.append(result)

    return results


def main():
    """Main processing function."""
    # Paths
    corpus_dir = Path('/Users/wongpeiting/Desktop/CU/python-work/budget-strict/corpus')
    metadata_path = Path('/Users/wongpeiting/Desktop/CU/python-work/budget-strict/metadata.csv')
    output_path = Path('/Users/wongpeiting/Desktop/CU/python-work/budget_in_one_chart/budget_speeches_paragraphs.csv')

    # Load metadata
    print("Loading metadata...")
    metadata = load_metadata(metadata_path)
    print(f"Loaded metadata for {len(metadata)} speeches")

    # Process all speeches
    all_paragraphs = []

    speech_files = sorted(corpus_dir.glob('*.txt'))
    print(f"\nProcessing {len(speech_files)} speech files...")

    for i, file_path in enumerate(speech_files, 1):
        file_name = file_path.name

        if file_name not in metadata:
            print(f"Warning: No metadata found for {file_name}")
            continue

        print(f"[{i}/{len(speech_files)}] Processing {file_name}...")

        # Process the speech
        paragraphs = process_speech_file(file_path, metadata[file_name])
        all_paragraphs.extend(paragraphs)

        print(f"  -> Generated {len(paragraphs)} paragraphs")

    # Write output CSV
    print(f"\nWriting {len(all_paragraphs)} paragraphs to {output_path}...")

    fieldnames = [
        'paragraph_id',
        'speech_id',
        'paragraph_num',
        'paragraph_text',
        'paragraph_length',
        'year',
        'date',
        'fm_name',
        'pm_name',
        'parliament_term',
        'election_budget',
        'file_name'
    ]

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_paragraphs)

    print(f"\nProcessing complete!")
    print(f"Total speeches processed: {len(speech_files)}")
    print(f"Total paragraphs generated: {len(all_paragraphs)}")
    print(f"Average paragraphs per speech: {len(all_paragraphs) / len(speech_files):.1f}")

    # Print some statistics
    lengths = [p['paragraph_length'] for p in all_paragraphs]
    print(f"\nParagraph length statistics:")
    print(f"  Min: {min(lengths)} characters")
    print(f"  Max: {max(lengths)} characters")
    print(f"  Average: {sum(lengths) / len(lengths):.1f} characters")
    print(f"  Median: {sorted(lengths)[len(lengths) // 2]} characters")


if __name__ == '__main__':
    main()
