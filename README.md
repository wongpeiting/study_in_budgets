# 💼 A Study In Budgets 💼

As a reporter who used to follow government speeches closely for [work](https://www.straitstimes.com/authors/wong-pei-ting), I do very so often detect some very slight shifts in messaging that I found interesting. As we can imagine such changes are usually gradual, so it would take an analysis of years-long of speeches before we can really pin down a pivot. This project is born from this place of curiosity, where I question if I could devise a text analysis pipeline that can open up a quantitative way of confirming (or disproving) some of these hunches.

Since Prime Minister Lawrence Wong was set to deliver the 2026 Budget speech on Feb 12, I hopped on a mission to collect all the 67 Budget speeches delivered in Singapore since independence in 1965, so I could begin testing if it was indeed possible for me to find patterns in a corpus of words. The journey was an iterative one fraught with early framing uncertainty, data cleaning challenges (not insurmountable, just tedious) and LLM classification issues. 

After three weeks of mucking around, including testing if I could somehow find patterns with the use of a [semantic map](https://github.com/TowCenter/semantic-map), I got inspired by The Pudding's *[In Pursuit of Democracy](https://pudding.cool/2025/11/democracy/)* project, in which Alvin Chang focused on testing just one thing – how the idea of democracy shifted within a body of congressional speeches.

Keen to replicate his project design, I got down to defining a scope, and the result is [this interactive scrollytelling article](https://wongpeiting.github.io/study_in_budgets/) where I drew on the Singapore Budget speeches to trace how responsibility is framed – what the government promises, what it asks of citizens and firms, and how that balance shifts over time. 

The project analyses speeches at a paragraph level and classifies whether each paragraph articulate a promise, a demand, or neither, as well as whether the message is directed towards citizens or firms. The goal is not to measure sentiment, but to examine how the state describes obligation, support and participation.

In all, 11,559 paragraphs were analysed from 67 Budget speeches between 1965 and 2026, and here are the broad findings:

| Prime Minister | Years | Promise Ratio |
|----------------|-------|---------------|
| Lee Kuan Yew | 1965–1990 | 54.5% |
| Goh Chok Tong | 1991–2004 | 65.4% |
| Lee Hsien Loong | 2005–2024 | 72.3% |
| Lawrence Wong | 2025–present | 74.4% |

Under founding Prime Minister Lee Kuan Yew, Budget speeches balanced promises with demands almost equally. By the current era, promises outweigh demands by more than 2:1.

---

## Data and data cleaning

Data from this project is based off the corpus of Budget speeches found on [Singapore Hansard records](https://sprs.parl.gov.sg/search/), the official repository of parliamentary proceedings. 

After the speeches were collected, they were manually cleaned to remove non-substantive transcript markers, subheadings, footnotes and appendix references that were not part of the spoken text. A Python script was later used to break the speeches into paragraphs, and further clean the dataset by removing headers missed from the first pass of data cleaning, table data, as well as speech procedure text that make up entire paragraphs ('Mr Speaker, I beg to move'). 

By the end of this process, the corpus comprised roughly 700,000 words across 11,559 paragraphs. Metadata for each speech - including the finance minister, date of delivery and presiding prime minister - was appended at the paragraph level in a CSV file prior to AI augmentation.

## LLM classification

Each paragraph was classified using Google's Gemini 2.0 Flash into five categories:

| Category | Description |
|----------|-------------|
| **Promise to citizens** | Government commitments to help individuals (subsidies, cash, housing, healthcare) |
| **Promise to firms** | Government support for businesses (tax relief, incentives, infrastructure) |
| **Demand on citizens** | Expectations on Singaporeans (adapt, upgrade skills, stay competitive) |
| **Demand on firms** | Expectations on businesses (innovate, transform, reskill workers) |
| **Neutral** | Factual information, procedural language, general policy discussion |

Before deploying AI for full classification, more than 100 paragraphs were manually labelled to establish a validation set. These hand-coded examples were used to iteratively refine and test the classification prompt.

After 11 rounds of prompt revision, the framework peaked at an accuracy rate of 91.2% on the audited validation set on the ninth try. I manually checked the rows that were deemed to have classified wrongly in this ninth attempt, and realised that many were not straightforward errors, but borderline cases open to reasonable interpretation. I thus selected the ninth iteration of the prompt for full-corpus classification, knowing that it errs on cases of interpretive ambiguity rather than clear misclassification. In fact, this is to be expected. The residual disagreement rate reflects the limits of categorising political language into discrete buckets: some paragraphs contain both promise and demand, or imply obligation without stating it explicitly.

<details>
<summary><strong>View the classification prompt</strong></summary>

```
SYSTEM_PROMPT = """You are an expert classifier specializing in analyzing Singapore political discourse for themes related to fiscal redistribution and civic obligation. Your sole task is to determine if a provided text articulates a promise (prosperity, help, sharing, stability, recovery) or a demand (discipline, participation, compliance, restraint) directed at citizens or firms, and, if so, to categorize it according to a strict set of five themes.

You must adhere to four critical rules:

1. Government updates are neutral - Be very strict: Government announcing what it will do/is doing = neutral, not promise. Promise requires explicit "we will give/help/support citizens/firms" language. Neutral includes: "HDB expected to complete units", "committee investigating", "duty/tax will be removed/changed", "research will be stepped up", "training programme will include", "we introduced GST and gave rebate" (tax history), "careful/prudent planning resulted in" (without emphasizing "importance of discipline"), company examples (Samwoh), fiscal planning explanations, industry descriptions. International affairs, fiscal reports, government plans, speech procedures, case studies, technical fiscal explanations.

2. Target distinction is critical: When there is a behavioral expectation, identify target precisely:
   - Firms: "leaders of companies", "companies must", "firms need to", productivity, competitiveness, "we need to improve productivity"
   - Citizens: "Singaporeans", "our people", "workers", "citizens", "households"
   - Critical: "Leaders of companies play key role... committed to reskilling staff" → demand_firm (leaders are firm representatives)
   - "Our people develop skills" → demand_citizen
   - "Help Singaporeans acquire skills, adapt" → demand_citizen (not promise)

3. Investment/Financial mentions - Check carefully: "Investment commitments amounted to $X" or "investors are confident" = Neutral (just describing investment activity). Promise_firm requires explicit support/promotion language: "we will promote wealth management", "measures to enhance financial services", "we will provide R&D funding". Not just describing investment levels.

4. "Help/support/enable X to do Y" = Demand not Promise: "Help Singaporeans acquire skills, adapt" = demand_citizen + supportive_demand (not promise_citizen). "Support seniors to remain active" = demand_citizen + supportive_demand. The "do Y" is the behavioral expectation.

5. Fiscal discipline language = Demand_citizen: Emphasizing "discipline," "fiscal prudence," "setting aside resources" as crucial behavior = demand_citizen.

6. Environmental targets = Demand_firm: Sector targets like "aim to have 100% cleaner vehicles by 2040" = demand_firm.

7. "Create opportunities for people to develop skills" = Demand_citizen: When text says "create opportunities for our people to develop their skills, creativity and talents" or similar - this expects citizens to develop skills, not a promise_firm to businesses. Check carefully if the expectation is on people (citizens) or firms.

8. Strict output format: Your entire response must consist of exactly eight lines and nothing else."""

USER_PROMPT_TEMPLATE = """Follow these steps to analyze the text provided at the end.

Step 1: Government update vs descriptive check

First, determine if the text is only describing what government is doing/planning WITHOUT rallying anyone:
- Government plans, reports, updates, announcements
- Case studies/examples of specific individuals or companies
- Technical fiscal explanations (NIR, reserve management) without "importance of discipline" language
- Government stating "upcoming direction" or "pressing on with efforts"

If yes → neutral. Stop here.

Exception: If example explicitly showcases model behavior others should follow ("addressed it with diligence, determination; move up; improved continuously") → demand_citizen.

Step 2: Check for Investment/Financial Services Mentions

If text mentions investment commitments, investment confidence, financial services promotion, R&D funding, innovation funding, wealth management:
→ promise_firm (unless explicit behavioral expectation for firms)

Step 3: Target audience identification

If not neutral or promise_firm, identify target:
- Firms: companies, businesses, leaders of companies, industries, sectors, "we" (in productivity/competitiveness context), "step up productivity," "lose ground to emerging cities"
- Citizens: Singaporeans, people, workers, households, families, seniors, "adjust to disruptions," "pull up socks"

Step 4: Promise vs. demand classification

Promise: Support without behavioral expectation
- Citizens: subsidies, tax rebates, cash, housing supply, healthcare benefits, "public services at least cost to taxpayer"
- Firms: infrastructure investment (T5, Changi), investment incentives (already classified in Step 2)

Demand: Explicit/implicit behavioral expectation
- Citizens: "pull up socks," "live within means," "incentive to get job," "support seniors to remain active," "adjust to disruptions," "baton is passed," "importance of fiscal discipline," "create opportunities for people to develop skills"
- Firms: "must transform," "innovate," "redesign jobs," "reskill staff," "step up productivity," "leaders must raise capabilities," "if we do not succeed we will lose ground"

Critical: "Support X to do Y" = demand with supportive_demand = 1

Step 5: Supportive demand & framing

If demand_*, check if support enables behavior → supportive_demand = 1
Identify framing: crisis_framing, collective_future_framing, vulnerability_framing, or none

### EXAMPLES:

Example 1: Technical fiscal explanation (Neutral)

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

Example 2: Government direction statement (Neutral)

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

Example 3: Public services at least cost (Promise citizen)

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

Example 4: Investment confidence (Promise firm)

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

Example 5: Financial services promotion (Promise firm)

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

Example 6: R&D/Innovation funding (Promise firm)

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

Example 7: Climate support mentioned (Promise firm)

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

Example 8: R&D investment (Promise firm)

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

Example 9: Leaders must reskill (Demand firm)

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

Example 10: Step up productivity (Demand firm)

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

Example 11: Adjust to disruptions (Demand citizen)

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

Example 12: Budget support (Promise citizen)

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

Example 13: Model behavior example (Demand citizen)

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

Example 14: Housing supply (Promise citizen)

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

Example 15: Workfare (Demand citizen)

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

Example 16: Support seniors active (Demand citizen)

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

Example 17: Skills development (Demand citizen)

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
reason: [max 12 words OR "none" if neutral]
```

</details>

---

## Classification Results

| Category | Count | % |
|----------|------:|--:|
| Neutral | 5,675 | 49.1% |
| Promise to citizens | 2,433 | 21.0% |
| Promise to firms | 1,596 | 13.8% |
| Demand on citizens | 1,310 | 11.3% |
| Demand on firms | 540 | 4.7% |

---

## Word frequency analysis

To track how Budget vocabulary evolved, all speeches were tokenised and word frequencies calculated for two periods: 1965–1975 (early era) and 2017–2026 (recent era). Raw counts were normalised to mentions per 10,000 words to account for varying speech lengths across years. UK spellings were also normalised to US variants (e.g. "programme" → "program", "defence" → "defense") to avoid double-counting.

Rising and declining words were identified by comparing the change in mean frequency between periods. For example, "support" increased from 1.9 to 60.3 mentions per 10,000 words — a 32× increase.

In calculating the finance minister "pet words", the corpus was grouped by minister and words were ranked by how distinctively each FM used them compared to others. This surfaced vocabulary fingerprints across all 10 finance ministers: Goh Keng Swee spoke of military and battalions; Tony Tan spoke automation and robots; Lawrence Wong now speaks of assurance and vouchers.

A separate analysis identified words that persisted across all seven decades — effort, skills, training, competitive, improve, productivity — suggesting an enduring expectation of self-improvement that runs through every era, regardless of who delivers the speech.

--- 

## Scrollytelling interface

Claude Code was used to build the interactive scrollytelling site, which is also inspired by the *[In Pursuit of Democracy](https://pudding.cool/2025/11/democracy/)* piece on The Pudding. As readers scroll, narrative cards appear on the left while a sticky chart on the right responds to each section, highlighting relevant years, animating transitions, and updating context.

The chart itself is built with [D3.js](https://d3js.org). Each of the 5,879 classified paragraphs is rendered as a small square, coloured by category (coral for promises, blue for demands) and stacked by year. Scroll-triggered transitions use the Intersection Observer API to detect which story card is in view, then update the chart accordingly.

At the end of the narrative, the chart becomes interactive: readers can hover over any square to read the original paragraph, with coordinate-based hit detection used to bypass browser rendering quirks.

**Key tools:**

- **Visualisation:** [D3.js](https://d3js.org) for SVG rendering and data binding
- **Scrollytelling:** Intersection Observer API with CSS sticky positioning
- **Classification:** [Gemini 2.0 Flash](https://deepmind.google/technologies/gemini/) (Google) for paragraph-level analysis
- **Data processing:** Python for corpus cleaning, tokenisation, and frequency analysis

--- 

## Credits

This project lived many lives during its three production weeks. In one of the earlier explorations, Bhuvan Anantham (LSE '28) helped with data cleaning and metadata generation, contributing greatly to the polish of this final iteration. 

Charmaine Yap (Columbia Law '26), without whom this project would not have materialised, and Elliot Poh contributed extensive editorial inputs, while my professors at Columbia Journalism School. Jonathan Soma and Dhrumil Mehta, oversaw the production of this piece, including attending to my cries for help in the middle of the day/ night.

--- 

Lastly, dear reader, if you noticed an error or have thoughts or suggestions, please feel free to reach out at [pw2635@columbia.edu](pw2635@columbia.edu).