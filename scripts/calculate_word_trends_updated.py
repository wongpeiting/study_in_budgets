#!/usr/bin/env python3
"""
Recalculate word frequency trends with 2026 data.
Compare 1965-1975 vs 2016-2026, normalized per 10,000 words.
"""

import csv
import json
from collections import Counter
import re

def normalize_word(word):
    """Normalize word for counting."""
    return word.lower().strip()

def count_words_by_period(corpus, start_year, end_year):
    """Count word frequencies in a period, return counts and total words."""
    all_text = []

    for row in corpus:
        year = int(row['year'])
        if start_year <= year <= end_year:
            all_text.append(row['paragraph_text'])

    # Combine all text
    combined = ' '.join(all_text)

    # Tokenize (simple word splitting)
    words = re.findall(r'\b[a-z]+\b', combined.lower())

    total_words = len(words)
    word_counts = Counter(words)

    return word_counts, total_words

def calculate_per_10k(count, total_words):
    """Calculate mentions per 10,000 words."""
    return (count / total_words) * 10000 if total_words > 0 else 0

def get_yearly_frequencies(corpus, word, start_year=1965, end_year=2026):
    """Calculate word frequency for each year."""
    yearly_data = []

    for year in range(start_year, end_year + 1):
        # Get all text for this year
        year_text = []
        for row in corpus:
            if int(row['year']) == year:
                year_text.append(row['paragraph_text'])

        if not year_text:
            yearly_data.append({'year': year, 'per_10k': 0})
            continue

        # Combine and count
        combined = ' '.join(year_text)
        words = re.findall(r'\b[a-z]+\b', combined.lower())
        total = len(words)
        count = words.count(word.lower())

        per_10k = calculate_per_10k(count, total)
        yearly_data.append({'year': year, 'per_10k': round(per_10k, 1)})

    return yearly_data

def main():
    corpus_path = 'data/budget_speeches_paragraphs_v3_clean.csv'
    output_path = 'word_trends.json'

    print("Loading corpus...")
    with open(corpus_path, 'r') as f:
        corpus = list(csv.DictReader(f))

    print(f"Loaded {len(corpus)} paragraphs")

    # Define periods
    early_start, early_end = 1965, 1975
    recent_start, recent_end = 2016, 2026

    print(f"\nCalculating word frequencies...")
    print(f"Early period: {early_start}-{early_end}")
    print(f"Recent period: {recent_start}-{recent_end}")

    # Count words in each period
    early_counts, early_total = count_words_by_period(corpus, early_start, early_end)
    recent_counts, recent_total = count_words_by_period(corpus, recent_start, recent_end)

    print(f"\nEarly period: {early_total:,} total words")
    print(f"Recent period: {recent_total:,} total words")

    # Words to track (from the image shown)
    rising_words = [
        'support', 'singaporeans', 'help', 'workers', 'provide', 'global',
        'continue', 'businesses', 'seniors', 'innovation', 'together', 'community',
        'families', 'opportunities'
    ]

    declining_words = [
        'expenditure', 'development', 'trade', 'industrial', 'manufacturing',
        'export', 'revenue', 'fiscal', 'budget', 'investment', 'economic', 'sector'
    ]

    # Calculate statistics
    rising_stats = []
    declining_stats = []

    print("\n" + "="*80)
    print("RISING WORDS (1965-1975 vs 2016-2026)")
    print("="*80)

    for word in rising_words:
        early_per_10k = calculate_per_10k(early_counts[word], early_total)
        recent_per_10k = calculate_per_10k(recent_counts[word], recent_total)
        multiplier = recent_per_10k / early_per_10k if early_per_10k > 0 else float('inf')

        # Handle infinity cases
        if multiplier == float('inf'):
            mult_value = 999  # Use large number instead of infinity
            change_str = '+999'
        else:
            mult_value = round(multiplier, 1)
            change_str = '+' + str(mult_value)

        rising_stats.append({
            'word': word,
            'early_per_10k': round(early_per_10k, 1),
            'recent_per_10k': round(recent_per_10k, 1),
            'multiplier': mult_value,
            'change': change_str
        })

        print(f"{word:15s}: {early_per_10k:6.1f} → {recent_per_10k:6.1f} (×{multiplier:.1f})")

    print("\n" + "="*80)
    print("DECLINING WORDS (1965-1975 vs 2016-2026)")
    print("="*80)

    for word in declining_words:
        early_per_10k = calculate_per_10k(early_counts[word], early_total)
        recent_per_10k = calculate_per_10k(recent_counts[word], recent_total)
        multiplier = recent_per_10k / early_per_10k if early_per_10k > 0 else 0

        declining_stats.append({
            'word': word,
            'early_per_10k': round(early_per_10k, 1),
            'recent_per_10k': round(recent_per_10k, 1),
            'multiplier': round(multiplier, 2),
            'change': str(round((multiplier - 1) * 100, 1)) + '%'
        })

        print(f"{word:15s}: {early_per_10k:6.1f} → {recent_per_10k:6.1f} (×{multiplier:.2f})")

    # Sort by multiplier
    rising_stats.sort(key=lambda x: x['multiplier'] if x['multiplier'] != float('inf') else 999, reverse=True)
    declining_stats.sort(key=lambda x: x['multiplier'])

    # Generate timeseries data for visualization (year by year)
    print("\nCalculating yearly timeseries for each word...")
    for stat in rising_stats:
        yearly = get_yearly_frequencies(corpus, stat['word'])
        stat['timeseries'] = yearly

    for stat in declining_stats:
        yearly = get_yearly_frequencies(corpus, stat['word'])
        stat['timeseries'] = yearly

    # Create output
    output = {
        'periods': {
            'early': f'{early_start}-{early_end}',
            'recent': f'{recent_start}-{recent_end}'
        },
        'rising': rising_stats[:12],  # Top 12
        'declining': declining_stats[:12]
    }

    # Write to file
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n" + "="*80)
    print(f"Word trends saved to: {output_path}")
    print("="*80)

    # Print top changes
    print("\nTOP RISING WORDS:")
    for i, stat in enumerate(rising_stats[:5], 1):
        mult = stat['multiplier']
        if mult == float('inf'):
            print(f"{i}. {stat['word']}: 0 → {stat['recent_per_10k']:.1f} (new word)")
        else:
            print(f"{i}. {stat['word']}: {stat['early_per_10k']:.1f} → {stat['recent_per_10k']:.1f} (×{mult:.1f})")

    print("\nTOP DECLINING WORDS:")
    for i, stat in enumerate(declining_stats[:5], 1):
        print(f"{i}. {stat['word']}: {stat['early_per_10k']:.1f} → {stat['recent_per_10k']:.1f} (×{stat['multiplier']:.2f})")


if __name__ == '__main__':
    main()
