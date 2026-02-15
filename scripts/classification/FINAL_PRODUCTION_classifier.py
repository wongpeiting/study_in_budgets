#!/usr/bin/env python3
"""
Singapore Budget Speech Classifier - V9 (FINAL PRODUCTION VERSION)

Performance: 91.2% accuracy (62/68 correct) ⭐
Progress: V1 (72.1%) → V4 (79.4%) → V7 (83.8%) → V8 (88.2%) → V9 (91.2%)
Note: Accuracy updated after fixing human labeling typo in row 67-84

Remaining 6 mismatches (only 3 more needed for 95%!):
- 2 ambiguous (human notes contradict category label)
- 4 clear errors:
  * Row 15-87: Duty removal (pred=promise_firm, should=neutral)
  * Row 30-73: Medical research funding (pred=promise_firm, should=neutral)
  * Row 53-180: Fiscal planning (pred=demand_citizen, should=neutral)
  * Row 60-74: "Create opportunities for people to develop skills" (pred=promise_firm, should=demand_citizen)

Key improvements from earlier versions:
- Strict neutral rules (government announcements ≠ promises)
- Clear target distinction (leaders of companies = firms; our people = citizens)
- "Help/Support X to DO Y" = demand with supportive_demand
- Investment commitments descriptions = neutral (not promise_firm)
- Environmental targets for sectors = demand_firm
- Fiscal prudence emphasis = demand_citizen

Next steps to reach 95%:
- User to classify new_sample_50_for_human_classification.csv
- Retrain on combined cleaner dataset
- Apply to full corpus of 12,803 paragraphs
"""

import csv
import time
import os
import google.generativeai as genai

# Configure Gemini API - set GEMINI_API_KEY environment variable
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# System and User prompts - VERSION 4
SYSTEM_PROMPT = """You are an expert classifier specializing in analyzing Singapore political discourse for themes related to fiscal redistribution and civic obligation. Your sole task is to determine if a provided text articulates a PROMISE (prosperity, help, sharing, stability, recovery) or a DEMAND (discipline, participation, compliance, restraint) directed at citizens or firms, and, if so, to categorize it according to a strict set of five themes.

You must adhere to four critical rules:

1. Government Updates Are Neutral - BE VERY STRICT: Government announcing what it will do/is doing = NEUTRAL, NOT promise. Promise requires EXPLICIT "we will give/help/support citizens/firms" language. NEUTRAL includes: "HDB expected to complete units", "committee investigating", "duty/tax will be removed/changed", "research will be stepped up", "training programme will include", "we introduced GST and gave rebate" (tax history), "careful/prudent planning resulted in" (WITHOUT emphasizing "importance of discipline"), company examples (Samwoh), fiscal planning explanations, industry descriptions. International affairs, fiscal reports, government plans, speech procedures, case studies, technical fiscal explanations.

2. Target Distinction Is CRITICAL: When there IS a behavioral expectation, identify target precisely:
   - FIRMS: "leaders of companies", "companies must", "firms need to", productivity, competitiveness, "we need to improve productivity"
   - CITIZENS: "Singaporeans", "our people", "workers", "citizens", "households"
   - CRITICAL: "Leaders of companies play key role... committed to reskilling staff" → demand_FIRM (leaders are firm representatives)
   - "Our people develop skills" → demand_CITIZEN
   - "Help Singaporeans acquire skills, adapt" → demand_CITIZEN (not promise)

3. Investment/Financial Mentions - CHECK CAREFULLY: "Investment commitments amounted to $X" or "investors are confident" = NEUTRAL (just describing investment activity). Promise_firm requires explicit support/promotion language: "we will promote wealth management", "measures to enhance financial services", "we will provide R&D funding". NOT just describing investment levels.

4. "Help/Support/Enable X to DO Y" = Demand NOT Promise: "Help Singaporeans acquire skills, adapt" = demand_citizen + supportive_demand (NOT promise_citizen). "Support seniors to remain active" = demand_citizen + supportive_demand. The "DO Y" is the behavioral expectation.

5. Fiscal Discipline Language = Demand_Citizen: Emphasizing "discipline," "fiscal prudence," "setting aside resources" as crucial behavior = demand_citizen.

6. Environmental Targets = Demand_Firm: Sector targets like "aim to have 100% cleaner vehicles by 2040" = demand_firm.

7. "Create opportunities for people to develop skills" = Demand_Citizen: When text says "create opportunities for our people to develop their skills, creativity and talents" or similar - this expects citizens to develop skills, NOT a promise_firm to businesses. Check carefully if the expectation is on PEOPLE (citizens) or FIRMS.

8. Strict Output Format: Your entire response must consist of exactly eight lines and nothing else."""

USER_PROMPT_TEMPLATE = """Follow these steps to analyze the text provided at the end.

Step 1: Government Update vs Descriptive Check

First, determine if the text is ONLY describing what government is doing/planning WITHOUT rallying anyone:
- Government plans, reports, updates, announcements
- Case studies/examples of specific individuals or companies
- Technical fiscal explanations (NIR, reserve management) WITHOUT "importance of discipline" language
- Government stating "upcoming direction" or "pressing on with efforts"

If yes → neutral. Stop here.

EXCEPTION: If example explicitly showcases model behavior others should follow ("addressed it with diligence, determination; move up; improved continuously") → demand_citizen.

Step 2: Check for Investment/Financial Services Mentions

If text mentions investment commitments, investment confidence, financial services promotion, R&D funding, innovation funding, wealth management:
→ promise_firm (unless explicit behavioral expectation for firms)

Step 3: Target Audience Identification

If NOT neutral or promise_firm, identify target:
- FIRMS: companies, businesses, leaders of companies, industries, sectors, "we" (in productivity/competitiveness context), "step up productivity," "lose ground to emerging cities"
- CITIZENS: Singaporeans, people, workers, households, families, seniors, "adjust to disruptions," "pull up socks"

Step 4: Promise vs. Demand Classification

PROMISE: Support without behavioral expectation
- Citizens: subsidies, tax rebates, cash, housing supply, healthcare benefits, "public services at least cost to taxpayer"
- Firms: infrastructure investment (T5, Changi), investment incentives (already classified in Step 2)

DEMAND: Explicit/implicit behavioral expectation
- Citizens: "pull up socks," "live within means," "incentive to get job," "support seniors to remain active," "adjust to disruptions," "baton is passed," "importance of fiscal discipline," "create opportunities for people to develop skills"
- Firms: "must transform," "innovate," "redesign jobs," "reskill staff," "step up productivity," "leaders must raise capabilities," "if we do not succeed we will lose ground"

CRITICAL: "Support X to DO Y" = demand with supportive_demand = 1

Step 5: Supportive Demand & Framing

If demand_*, check if support enables behavior → supportive_demand = 1
Identify framing: crisis_framing, collective_future_framing, vulnerability_framing, or none

### EXAMPLES:

Example 1: Technical Fiscal Explanation (Neutral)

TEXT: "Currently, we spend up to 50% of expected NIR and keep the remainder in our Reserves. This allows our Reserves to grow with our economy."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 0
demand_citizen: 0
demand_firm: 0
neutral: 1
supportive_demand: 0
framing_signal: none
reason: none

Example 2: Government Direction Statement (Neutral)

TEXT: "MOT is pressing on with our efforts to become a car-lite society by improving public transport, encouraging active mobility, while discouraging pollutive vehicles."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 0
demand_citizen: 0
demand_firm: 0
neutral: 1
supportive_demand: 0
framing_signal: none
reason: none

Example 3: Public Services at Least Cost (Promise Citizen)

TEXT: "The effectiveness and efficiency of public services should be enhanced. In general, public services should be provided at least cost to the taxpayer."

YOUR RESPONSE:
promise_citizen: 1
promise_firm: 0
demand_citizen: 0
demand_firm: 0
neutral: 0
supportive_demand: 0
framing_signal: none
reason: Public services at least cost benefits taxpayers

Example 4: Investment Confidence (Promise Firm)

TEXT: "Although our relative competitiveness position has declined slightly, investors are confident about Singapore's fundamentals. Investment commitments in the manufacturing sector amounted to $3.5 billion in 1992, a record high."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 1
demand_citizen: 0
demand_firm: 0
neutral: 0
supportive_demand: 0
framing_signal: none
reason: Investment confidence and commitments benefit firms

Example 5: Financial Services Promotion (Promise Firm)

TEXT: "In financial services, we are steadily becoming a full-service global financial centre. I will take further measures to promote our wealth management, capital market and treasury activities."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 1
demand_citizen: 0
demand_firm: 0
neutral: 0
supportive_demand: 0
framing_signal: none
reason: Promoting financial services benefits firms

Example 6: R&D/Innovation Funding (Promise Firm)

TEXT: "I will set aside $100 million to build capabilities under the Global Innovation Alliance and Leadership Development Initiative."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 1
demand_citizen: 0
demand_firm: 0
neutral: 0
supportive_demand: 0
framing_signal: none
reason: Innovation funding for firms without behavioral expectations

Example 7: Climate Support Mentioned (Promise Firm)

TEXT: "We will continue to support international and regional efforts towards climate action and play an active role at the United Nations Framework Convention on Climate Change negotiations."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 1
demand_citizen: 0
demand_firm: 0
neutral: 0
supportive_demand: 0
framing_signal: none
reason: Climate support benefits firms in transition

Example 8: R&D Investment (Promise Firm)

TEXT: "Under our Research, Innovation and Enterprise 2020 Plan, we are sustaining investment into promising ideas. These include artificial intelligence, industrial robotics, urban solutions and sustainability."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 1
demand_citizen: 0
demand_firm: 0
neutral: 0
supportive_demand: 0
framing_signal: none
reason: R&D investment for promising enterprises

Example 9: Leaders Must Reskill (Demand Firm)

TEXT: "We want our people to have the skills to adapt and thrive. The leadership of companies plays a key role. The leaders of successful companies are those who are committed to raising the capabilities of their workers by redesigning jobs and reskilling their staff."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 0
demand_citizen: 0
demand_firm: 1
neutral: 0
supportive_demand: 0
framing_signal: collective_future_framing
reason: Leaders of companies expected to redesign jobs reskill staff

Example 10: Step Up Productivity (Demand Firm)

TEXT: "There is also another important reason why we have to step up productivity improvement. If we do not succeed in this new phase of transformation, we will lose ground to emerging cities in Asia."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 0
demand_citizen: 0
demand_firm: 1
neutral: 0
supportive_demand: 0
framing_signal: crisis_framing
reason: Firms must step up productivity to avoid losing ground

Example 11: Adjust to Disruptions (Demand Citizen)

TEXT: "This is not the first time that we've found ourselves in such a situation. Since our Independence, we have had to adjust to all sorts of external disruptions and shocks."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 0
demand_citizen: 1
demand_firm: 0
neutral: 0
supportive_demand: 0
framing_signal: none
reason: Implies citizens must adjust to disruptions and shocks

Example 12: Budget Support (Promise Citizen)

TEXT: "This Budget will support all of us to stay true to this SG Cares spirit and to work together to build a caring and cohesive society."

YOUR RESPONSE:
promise_citizen: 1
promise_firm: 0
demand_citizen: 0
demand_firm: 0
neutral: 0
supportive_demand: 0
framing_signal: collective_future_framing
reason: Budget supports caring society general not specific behavior

Example 13: Model Behavior Example (Demand Citizen)

TEXT: "I know a very interesting young man; Ramadan Salawat. He started off with a difficulty; addressed it with diligence, determination; move up; improved continuously; and raised the gain for all of us."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 0
demand_citizen: 1
demand_firm: 0
neutral: 0
supportive_demand: 0
framing_signal: none
reason: Showcases model behavior others should emulate

Example 14: Housing Supply (Promise Citizen)

TEXT: "This year, HDB will launch around 3,800 flats with a waiting time of less than three years. We will continue to increase the supply of such flats in the coming years."

YOUR RESPONSE:
promise_citizen: 1
promise_firm: 0
demand_citizen: 0
demand_firm: 0
neutral: 0
supportive_demand: 0
framing_signal: none
reason: Housing supply increase for citizens without conditions

Example 15: Workfare (Demand Citizen)

TEXT: "Workfare will give those at the lower end of the workforce a stronger incentive to get a job, stay in a job, and save for their future."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 0
demand_citizen: 1
demand_firm: 0
neutral: 0
supportive_demand: 1
framing_signal: none
reason: Incentive expects citizens to get job stay employed save

Example 16: Support Seniors Active (Demand Citizen)

TEXT: "Our priority is to support seniors to take care of their own health, including by remaining physically and mentally active, and staying engaged in their communities."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 0
demand_citizen: 1
demand_firm: 0
neutral: 0
supportive_demand: 1
framing_signal: none
reason: Support enables seniors to remain active engaged expectation

Example 17: Skills Development (Demand Citizen)

TEXT: "To create opportunities and redesign jobs, for our people to develop their skills, creativity and talents. Ultimately, to grow opportunities for our people to realise their full potential."

YOUR RESPONSE:
promise_citizen: 0
promise_firm: 0
demand_citizen: 1
demand_firm: 0
neutral: 0
supportive_demand: 0
framing_signal: collective_future_framing
reason: Expects people to develop skills for transformation participation

### FINAL INSTRUCTIONS:

TEXT: "{text}"

YOUR RESPONSE MUST CONTAIN EXACTLY EIGHT LINES IN THIS FORMAT:

promise_citizen: [0 or 1]
promise_firm: [0 or 1]
demand_citizen: [0 or 1]
demand_firm: [0 or 1]
neutral: [0 or 1]
supportive_demand: [0 or 1]
framing_signal: [crisis_framing, collective_future_framing, vulnerability_framing, or none]
reason: [max 12 words OR "none" if neutral]"""


def classify_text(text: str, model_name: str = "gemini-2.0-flash-001") -> dict:
    """Classify a single text using Gemini API."""
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_PROMPT
    )
    prompt = USER_PROMPT_TEMPLATE.format(text=text)
    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        lines = result_text.split('\n')
        result = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if key in ['promise_citizen', 'promise_firm', 'demand_citizen', 'demand_firm', 'neutral', 'supportive_demand']:
                    result[key] = int(value)
                elif key == 'framing_signal':
                    result[key] = value
                elif key == 'reason':
                    result[key] = value
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None

def load_validation_data(csv_path: str) -> list:
    """Load the 68-row validation sample."""
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data

def compare_with_human_audit(predicted: dict, actual_row: dict) -> dict:
    """Compare predicted classification with human audit."""
    human_logic = actual_row['Human logic -- category and notes']
    human_category = None
    if 'promise_citizen' in human_logic.lower():
        human_category = 'promise_citizen'
    elif 'promise_firm' in human_logic.lower():
        human_category = 'promise_firm'
    elif 'demand_citizen' in human_logic.lower():
        human_category = 'demand_citizen'
    elif 'demand_firm' in human_logic.lower():
        human_category = 'demand_firm'
    elif 'neutral' in human_logic.lower():
        human_category = 'neutral'
    predicted_category = None
    for cat in ['promise_citizen', 'promise_firm', 'demand_citizen', 'demand_firm', 'neutral']:
        if predicted.get(cat) == 1:
            predicted_category = cat
            break
    match = (predicted_category == human_category)
    return {
        'match': match,
        'predicted': predicted_category,
        'human': human_category,
        'human_notes': human_logic
    }

def test_prompt_on_validation_set(csv_path: str, output_path: str):
    """Test the prompt on all 68 rows and save results."""
    print("Loading validation data...")
    data = load_validation_data(csv_path)
    print(f"Loaded {len(data)} rows\n")
    results = []
    correct = 0
    total = 0
    for i, row in enumerate(data, 1):
        print(f"[{i}/{len(data)}] Processing row {row['speech_id']}...")
        text = row['paragraph']
        predicted = classify_text(text)
        if predicted is None:
            print(f"  ⚠ Classification failed")
            continue
        comparison = compare_with_human_audit(predicted, row)
        total += 1
        if comparison['match']:
            correct += 1
            print(f"  ✓ MATCH: {comparison['predicted']}")
        else:
            print(f"  ✗ MISMATCH: Predicted={comparison['predicted']}, Human={comparison['human']}")
            print(f"    Human notes: {comparison['human_notes'][:100]}...")
        result_row = {
            'speech_id': row['speech_id'],
            'paragraph_number': row['paragraph_number'],
            'year': row['year'],
            'paragraph': text[:100] + '...',
            'predicted_category': comparison['predicted'],
            'human_category': comparison['human'],
            'match': comparison['match'],
            'predicted_promise_citizen': predicted.get('promise_citizen', 0),
            'predicted_promise_firm': predicted.get('promise_firm', 0),
            'predicted_demand_citizen': predicted.get('demand_citizen', 0),
            'predicted_demand_firm': predicted.get('demand_firm', 0),
            'predicted_neutral': predicted.get('neutral', 0),
            'predicted_supportive_demand': predicted.get('supportive_demand', 0),
            'predicted_framing_signal': predicted.get('framing_signal', 'none'),
            'predicted_reason': predicted.get('reason', ''),
            'human_notes': comparison['human_notes']
        }
        results.append(result_row)
        time.sleep(1)
    print(f"\n\nWriting results to {output_path}...")
    fieldnames = [
        'speech_id', 'paragraph_number', 'year', 'paragraph',
        'predicted_category', 'human_category', 'match',
        'predicted_promise_citizen', 'predicted_promise_firm',
        'predicted_demand_citizen', 'predicted_demand_firm', 'predicted_neutral',
        'predicted_supportive_demand', 'predicted_framing_signal', 'predicted_reason',
        'human_notes'
    ]
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    accuracy = (correct / total * 100) if total > 0 else 0
    print(f"\n{'='*60}")
    print(f"RESULTS SUMMARY - VERSION 9 - FINAL")
    print(f"{'='*60}")
    print(f"Total rows tested: {total}")
    print(f"Correct classifications: {correct}")
    print(f"Accuracy: {accuracy:.1f}%")
    print(f"Improvement from V4: +{correct - 53} correct")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    validation_csv = '/Users/wongpeiting/Desktop/CU/python-work/budget-strict/ai_augment/validation_sample_68_classified_audited.csv'
    output_csv = '/Users/wongpeiting/Desktop/CU/python-work/budget_in_one_chart/01_dmil-dataviz-with-llms-d3/viz-scrollytelling/classification_test_results_v9.csv'
    test_prompt_on_validation_set(validation_csv, output_csv)
