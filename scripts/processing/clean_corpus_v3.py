#!/usr/bin/env python3
"""
V3: Clean corpus by removing non-content paragraphs.

Remove:
1. Headers ("Revenue, 1965", "Expenditure, 1965", "Tax Changes", etc.)
2. Table data ("1966 - 51,272", "From     To", etc.)
3. Speech procedure text ("Mr Speaker", "I beg to move", etc.)
4. Very short fragments (< 20 chars)
5. Just numbers/years
6. Connector-only fragments ("And", "But", "Or" at start with < 100 chars)
"""

import csv
import re

def should_remove(para):
    """Return True if paragraph should be removed."""
    text = para['paragraph_text'].strip()
    length = len(text)

    # 1. Very short (< 20 chars) - likely headers or fragments
    if length < 20:
        return True

    # 2. Table data patterns
    # Year-number pairs: "1966 - 51,272"
    if re.match(r'^\d{4}\s*[-–]\s*[\d,]+$', text):
        return True

    # Year with ellipsis: "1964  ...  $2,700 million"
    if re.match(r'^\d{4}\s+\.\.\.\s+', text):
        return True

    # Table headers: "From     To", "Per Kilogram"
    table_headers = ['From', 'To', 'Per Kilogram', 'Consumption', 'Present', 'Proposed']
    if text in table_headers or (length < 50 and any(h in text for h in table_headers)):
        return True

    # 3. Section headers (short text ending without punctuation)
    section_header_patterns = [
        r'^(Revenue|Expenditure|Conclusion|Introduction|Summary),?\s*\d{4}$',
        r'^Tax (Changes|Increases|Measures)$',
        r'^(Budget|Fiscal|Economic)\s+(Policy|Outlook|Measures)$',
        r'^\d+-Room Flats$',
        r'^Duty on ',
    ]
    for pattern in section_header_patterns:
        if re.match(pattern, text):
            return True

    # Generic short header without punctuation
    if length < 50 and not text[-1] in '.!?;"' and text[0].isupper():
        # Could be header if it's all caps or title case and short
        words = text.split()
        if len(words) <= 4 and all(w[0].isupper() or w.lower() in ['the', 'of', 'and', 'or', 'in', 'on', 'to'] for w in words):
            return True

    # 4. Speech procedure markers - ONLY pure procedure text
    # Keep paragraphs that END with "I beg to move" (conclusions with content)
    # Only remove paragraphs that START with procedure and have minimal content
    procedure_start_patterns = [
        r'^(Mr|Madam) (Speaker|Deputy Speaker), Sir, I beg to move,?\s*(That|"That) Parliament approves',
        r'^(Mr|Madam) (Speaker|Deputy Speaker), Sir, I beg to move\.$',
        r'^Sir, I beg to move\.$',
        r'^Question put and agreed to',
        r'^Bill read the (First|Second|Third) time',
    ]
    for pattern in procedure_start_patterns:
        if re.match(pattern, text):
            return True

    # Very short procedure fragments (but NOT conclusions)
    if length < 50 and text.startswith(('Mr Speaker', 'Madam Speaker', 'Mr President')) and not 'beg to move' in text[-30:]:
        return True

    # 5. Just numbers or just a year
    if text.replace(',', '').replace('.', '').replace('$', '').replace('%', '').replace(' ', '').replace('-', '').isdigit():
        return True

    # 6. Connector fragments (starts with And/But/Or and is short)
    connectors = ['And ', 'But ', 'Or ', 'So ']
    if any(text.startswith(conn) for conn in connectors) and length < 100:
        return True

    # 7. Isolated list item that slipped through
    if re.match(r'^\([a-z]\)\s*$', text) or re.match(r'^\([ivxl]+\)\s*$', text):
        return True

    # Keep everything else
    return False


def main():
    input_path = 'budget_speeches_paragraphs_v2.csv'
    output_path = 'budget_speeches_paragraphs_v3_clean.csv'

    with open(input_path, 'r') as f:
        reader = csv.DictReader(f)
        paragraphs = list(reader)

    print(f"Analyzing {len(paragraphs)} paragraphs from V2...")

    # Filter
    removed = []
    kept = []

    for para in paragraphs:
        if should_remove(para):
            removed.append(para)
        else:
            kept.append(para)

    # Renumber paragraphs within each speech
    speech_counters = {}
    for para in kept:
        speech_id = para['speech_id']
        if speech_id not in speech_counters:
            speech_counters[speech_id] = 1
        else:
            speech_counters[speech_id] += 1

        para['paragraph_num'] = speech_counters[speech_id]
        para['paragraph_id'] = f"{speech_id}_{speech_counters[speech_id]}"

    # Write cleaned corpus
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=kept[0].keys())
        writer.writeheader()
        writer.writerows(kept)

    # Write removed paragraphs for review
    removed_path = 'removed_paragraphs_v3.csv'
    if removed:
        with open(removed_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=removed[0].keys())
            writer.writeheader()
            writer.writerows(removed)

    # Statistics
    print(f"\n{'='*60}")
    print(f"CLEANING RESULTS")
    print(f"{'='*60}")
    print(f"Input (V2): {len(paragraphs)} paragraphs")
    print(f"Kept: {len(kept)} paragraphs ({len(kept)/len(paragraphs)*100:.1f}%)")
    print(f"Removed: {len(removed)} paragraphs ({len(removed)/len(paragraphs)*100:.1f}%)")
    print(f"\nSaved to: {output_path}")
    print(f"Removed items saved to: {removed_path}")

    # Show examples of what was removed
    print(f"\n{'='*60}")
    print(f"SAMPLE OF REMOVED PARAGRAPHS")
    print(f"{'='*60}")
    for i, para in enumerate(removed[:30], 1):
        print(f"[{i}] {para['speech_id']}-{para['paragraph_num']} ({para['year']}): {para['paragraph_text'][:80]}")

    # Final corpus statistics
    lengths = [len(p['paragraph_text']) for p in kept]
    print(f"\n{'='*60}")
    print(f"FINAL CORPUS STATISTICS")
    print(f"{'='*60}")
    print(f"Total paragraphs: {len(kept)}")
    print(f"Paragraph length:")
    print(f"  Min: {min(lengths)} chars")
    print(f"  Max: {max(lengths)} chars")
    print(f"  Average: {sum(lengths)/len(lengths):.1f} chars")
    print(f"  Median: {sorted(lengths)[len(lengths)//2]} chars")

    # Comparison
    print(f"\n{'='*60}")
    print(f"VERSION COMPARISON")
    print(f"{'='*60}")
    print(f"V1 (original): 12,803 paragraphs")
    print(f"V2 (lists merged): 11,609 paragraphs (-9.3%)")
    print(f"V3 (cleaned): {len(kept)} paragraphs ({(len(kept)-12803)/12803*100:+.1f}%)")


if __name__ == '__main__':
    main()
