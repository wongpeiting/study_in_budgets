#!/usr/bin/env python3
"""
Full Corpus Classification with V9 (91.2% accuracy)

Classify all 11,560 paragraphs from budget_speeches_paragraphs_v3_clean.csv
Expected runtime: ~3.2 hours (1 second per paragraph)
"""

import csv
import time
import os
import google.generativeai as genai
from datetime import datetime, timedelta

# Configure Gemini API - set GEMINI_API_KEY environment variable
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# V9 PRODUCTION SYSTEM PROMPT (91.2% accuracy)
SYSTEM_PROMPT = """You are an expert classifier specializing in analyzing Singapore political discourse for themes related to fiscal redistribution and civic obligation.

You must adhere to four critical rules:

1. Government Updates Are Neutral - BE VERY STRICT: Government announcing what it will do/is doing = NEUTRAL, NOT promise. Promise requires EXPLICIT "we will give/help/support citizens/firms" language. NEUTRAL includes: "HDB expected to complete units", "committee investigating", "duty/tax will be removed/changed", "research will be stepped up", "training programme will include", "we introduced GST and gave rebate" (tax history), "careful/prudent planning resulted in" (WITHOUT emphasizing "importance of discipline"), company examples (Samwoh), fiscal planning explanations, industry descriptions.

2. Target Distinction Is CRITICAL: When there IS a behavioral expectation, identify target precisely:
   - FIRMS: "leaders of companies", "companies must", "firms need to", productivity, competitiveness, "we need to improve productivity"
   - CITIZENS: "Singaporeans", "our people", "workers", "citizens", "households"
   - CRITICAL: "Leaders of companies play key role... committed to reskilling staff" → demand_FIRM
   - "Our people develop skills" → demand_CITIZEN
   - "Help Singaporeans acquire skills, adapt" → demand_CITIZEN (not promise)

3. Investment/Financial Mentions - CHECK CAREFULLY: "Investment commitments amounted to $X" or "investors are confident" = NEUTRAL (just describing investment activity). Promise_firm requires explicit support/promotion language: "we will promote wealth management", "measures to enhance financial services", "we will provide R&D funding". NOT just describing investment levels.

4. "Help/Support/Enable X to DO Y" = Demand NOT Promise: "Help Singaporeans acquire skills, adapt" = demand_citizen + supportive_demand (NOT promise_citizen). "Support seniors to remain active" = demand_citizen + supportive_demand. The "DO Y" is the behavioral expectation.

5. Fiscal Discipline Language = Demand_Citizen: Emphasizing "discipline," "fiscal prudence," "setting aside resources" as crucial behavior = demand_citizen.

6. Environmental Targets = Demand_Firm: Sector targets like "aim to have 100% cleaner vehicles by 2040" = demand_firm.

7. "Create opportunities for OUR PEOPLE to develop skills" = Demand_Citizen NOT Promise_Firm: CRITICAL: "To create opportunities for OUR PEOPLE to develop their skills, creativity and talents" = demand_CITIZEN (expects citizens to develop skills).

8. Strict Output Format: Your entire response must consist of exactly eight lines and nothing else."""

USER_PROMPT_TEMPLATE = """Classify this paragraph from a Singapore Budget speech:

"{paragraph_text}"

YOUR RESPONSE MUST CONTAIN EXACTLY EIGHT LINES:
promise_citizen: [0 or 1]
promise_firm: [0 or 1]
demand_citizen: [0 or 1]
demand_firm: [0 or 1]
neutral: [0 or 1]
supportive_demand: [0 or 1]
framing_signal: [crisis_framing, collective_future_framing, vulnerability_framing, or none]
reason: [max 12 words OR "none" if neutral]"""


def classify_paragraph(para_text):
    """Classify a single paragraph using V9 prompt."""
    model = genai.GenerativeModel("gemini-2.0-flash-001", system_instruction=SYSTEM_PROMPT)

    prompt = USER_PROMPT_TEMPLATE.format(paragraph_text=para_text)

    try:
        response = model.generate_content(prompt)
        result = {}

        for line in response.text.strip().split('\n'):
            if ':' in line:
                k, v = [x.strip() for x in line.split(':', 1)]
                if k in ['promise_citizen','promise_firm','demand_citizen','demand_firm','neutral','supportive_demand']:
                    # Handle both "0" and "[0]" formats
                    v_clean = v.strip('[]').strip()
                    result[k] = int(v_clean)
                else:
                    result[k] = v

        return result

    except Exception as e:
        print(f"    ERROR: {e}")
        return None


def main():
    input_path = 'budget_speeches_paragraphs_v3_clean.csv'
    output_path = 'classification_results_full_corpus_v9.csv'
    checkpoint_path = 'classification_checkpoint_v9.csv'

    # Load corpus
    with open(input_path, 'r') as f:
        corpus = list(csv.DictReader(f))

    total = len(corpus)
    print("="*80)
    print("FULL CORPUS CLASSIFICATION - V9 (91.2% accuracy)")
    print("="*80)
    print(f"Total paragraphs: {total:,}")
    print(f"Estimated time: ~{total/60:.1f} minutes (~{total/3600:.1f} hours)")
    print(f"Rate limit: 1 second per paragraph")
    print(f"Output: {output_path}")
    print(f"Checkpoints saved to: {checkpoint_path}")
    print("="*80)

    # Check if checkpoint exists
    start_idx = 0
    results = []

    try:
        with open(checkpoint_path, 'r') as f:
            reader = csv.DictReader(f)
            results = list(reader)
            start_idx = len(results)
            print(f"\nResuming from checkpoint: {start_idx:,}/{total:,} completed ({start_idx/total*100:.1f}%)")
    except FileNotFoundError:
        print(f"\nStarting fresh classification...")

    start_time = datetime.now()

    # Process paragraphs
    for i in range(start_idx, total):
        para = corpus[i]

        # Progress update
        if i % 100 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = (i - start_idx) / elapsed if elapsed > 0 else 0
            remaining = (total - i) / rate if rate > 0 else 0
            eta = datetime.now() + timedelta(seconds=remaining)

            print(f"\n[{i}/{total}] {i/total*100:.1f}% | Elapsed: {elapsed/60:.1f}m | ETA: {eta.strftime('%H:%M:%S')}")

        # Classify
        print(f"[{i+1}/{total}] {para['paragraph_id']} ({para['year']})...", end=' ')

        pred = classify_paragraph(para['paragraph_text'])

        if pred:
            # Determine primary category
            primary_category = next((c for c in ['promise_citizen','promise_firm','demand_citizen','demand_firm','neutral']
                                   if pred.get(c)==1), 'unknown')

            result = {
                'paragraph_id': para['paragraph_id'],
                'speech_id': para['speech_id'],
                'paragraph_num': para['paragraph_num'],
                'year': para['year'],
                'date': para['date'],
                'fm_name': para['fm_name'],
                'pm_name': para['pm_name'],
                'paragraph_text': para['paragraph_text'][:200] + '...' if len(para['paragraph_text']) > 200 else para['paragraph_text'],
                'paragraph_length': para['paragraph_length'],
                'category': primary_category,
                'promise_citizen': pred.get('promise_citizen', 0),
                'promise_firm': pred.get('promise_firm', 0),
                'demand_citizen': pred.get('demand_citizen', 0),
                'demand_firm': pred.get('demand_firm', 0),
                'neutral': pred.get('neutral', 0),
                'supportive_demand': pred.get('supportive_demand', 0),
                'framing_signal': pred.get('framing_signal', 'none'),
                'reason': pred.get('reason', '')
            }

            results.append(result)
            print(f"✓ {primary_category}")

            # Save checkpoint every 50 paragraphs
            if (i + 1) % 50 == 0:
                with open(checkpoint_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=result.keys())
                    writer.writeheader()
                    writer.writerows(results)
                print(f"    Checkpoint saved ({len(results)} completed)")
        else:
            print("FAILED")

        # Rate limit
        time.sleep(1)

    # Write final results
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # Statistics
    total_time = (datetime.now() - start_time).total_seconds()

    print("\n" + "="*80)
    print("CLASSIFICATION COMPLETE")
    print("="*80)
    print(f"Total paragraphs: {len(results):,}")
    print(f"Time taken: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)")
    print(f"Average rate: {len(results)/total_time:.2f} paragraphs/second")
    print(f"\nResults saved to: {output_path}")

    # Category breakdown
    categories = {}
    for r in results:
        cat = r['category']
        categories[cat] = categories.get(cat, 0) + 1

    print("\n" + "="*80)
    print("CATEGORY BREAKDOWN")
    print("="*80)
    for cat in sorted(categories.keys()):
        count = categories[cat]
        pct = count / len(results) * 100
        print(f"{cat:20s}: {count:5,} ({pct:5.1f}%)")

    print("\n" + "="*80)


if __name__ == '__main__':
    main()
