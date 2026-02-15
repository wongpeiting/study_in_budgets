#!/usr/bin/env python3
"""
Generate viz_data.json from V9 classification results.
Maintains exact same format as original viz_data.json.
"""

import csv
import json

def main():
    classification_path = 'data/classification_results_full_corpus_v9.csv'
    corpus_path = 'data/budget_speeches_paragraphs_v3_clean.csv'
    output_path = 'viz_data.json'

    print(f"Reading classification results from: {classification_path}")

    with open(classification_path, 'r') as f:
        reader = csv.DictReader(f)
        results = list(reader)

    print(f"Loaded {len(results)} classified paragraphs")

    # Load full text from corpus
    print(f"Reading full text from: {corpus_path}")
    with open(corpus_path, 'r') as f:
        reader = csv.DictReader(f)
        corpus = {row['paragraph_id']: row for row in reader}

    print(f"Loaded {len(corpus)} paragraphs from corpus")

    # Convert to viz format
    paragraphs = []

    for row in results:
        # Map category to primary_type and primary_value
        category = row['category']

        if category == 'promise_citizen':
            primary_type = 'promise'
            primary_value = 'citizen'
        elif category == 'promise_firm':
            primary_type = 'promise'
            primary_value = 'firm'
        elif category == 'demand_citizen':
            primary_type = 'obligation'
            primary_value = 'citizen'
        elif category == 'demand_firm':
            primary_type = 'obligation'
            primary_value = 'firm'
        elif category == 'neutral':
            primary_type = None
            primary_value = 'none'
        else:  # unknown
            primary_type = None
            primary_value = 'none'

        # Get full text from clean corpus
        para_id = row['paragraph_id']
        if para_id in corpus:
            text = corpus[para_id]['paragraph_text']
        else:
            text = row['paragraph_text']  # Fallback to truncated

        para = {
            'year': int(row['year']),
            'text': text,
            'fm_name': row['fm_name'],
            'primary_type': primary_type,
            'primary_value': primary_value,
            'speech_id': int(row['speech_id'])
        }

        paragraphs.append(para)

    # Create output structure
    output = {
        'paragraphs': paragraphs
    }

    # Write to file
    print(f"Writing {len(paragraphs)} paragraphs to: {output_path}")

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=4)

    # Statistics
    print("\n" + "="*60)
    print("VISUALIZATION DATA GENERATED")
    print("="*60)

    # Count by type
    counts = {}
    for p in paragraphs:
        if p['primary_type']:
            key = f"{p['primary_type']}_{p['primary_value']}"
        else:
            key = 'neutral'
        counts[key] = counts.get(key, 0) + 1

    print("\nCategory counts:")
    for cat in sorted(counts.keys()):
        print(f"  {cat:20s}: {counts[cat]:5,}")

    print(f"\nTotal: {len(paragraphs):,} paragraphs")
    print(f"Output: {output_path}")


if __name__ == '__main__':
    main()
