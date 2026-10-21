# HCSStest-events-trade

# Economic Exposure: reading GENOME through trade and dependency

## The idea
GENOME captures how countries and organisations interact through events: who
cooperates with whom, and who is in conflict. What it does not show is a second layer
of interaction: **economic dependency through trade**. Countries depend on each other
for goods such as gas, oil and chips, and this may shape how they behave. A country may
react less fiercely towards a partner it depends on.

This project adds that layer as a new domain angle: **economic exposure**. It looks at
**pairs of countries** and places their political relationship (GENOME events) next to
their trade relationship (Eurostat).

A second question behind this angle: **does an aggressor reduce its own dependencies
before a conflict, while the dependency of the other side remains or grows?** If so,
shifts in trade could become an early signal of political tension.

## What the analysis shows
The notebook compares trade between EU countries, and between EU and non-EU countries
(Saudi Arabia, China, Russia, Algeria), with their relationship in GENOME. It can show
two things:

1. **Risky relationships.** Pairs that are politically in conflict but economically
   dependent on each other. If such a relationship escalates, this imbalance can be
   used as leverage.
2. **The effect of conflict on trade.** Whether a deteriorating relationship goes
   together with changes in trade. In the current data there is **little correlation**,
   but this may change with a delay of several months, which requires further research.

## Relevance for policy
For countries that combine a strong dependency with a conflictual relationship, the
analysis points to where it is worth **diversifying suppliers or broadening trade
partners**, before an escalation makes that dependency costly.

## Design choices and trade-offs
- **Eurostat Comext** (DS-059341) was chosen because it is easily accessible, updated
  monthly and contains detail per product, so specific commodities such as gas
  (HS 2711) can be analysed.
- **Trade-off:** Eurostat only covers trade reported by **EU member states**. Trade
  between two non-EU countries (e.g. China–Russia) is not available.
- The EU has a **common trade policy**, so individual member states have limited
  control over trade measures, and EU countries may be more cautious in their reactions
  than other states.
- **Unit of analysis:** country pairs per month. GENOME intensity is averaged per event
  over both directions; trade balances are computed from totals over the period.

## Limitations
- **Few events can distort the picture.** With a small number of events, a single
  event strongly affects the average relationship between two countries.
- **Trade data is published with a delay** of a few months, so Eurostat cannot be used
  to anticipate conflicts in real time.
- **No history before the start date.** The relationship is measured from the start
  of the chosen period, so earlier relations are not taken into account.
- **Trade values in euro also reflect prices**, which matters especially for energy.

## Challenges
- **Interpreting events.** When a natural disaster occurs and countries send aid,
  this shows up as cooperation, while the underlying relationship may not have
  improved. The measured relationship therefore also depends on whether such events
  happen at all.


## Follow-up research
- Look at **historical conflicts** and test whether trade balances shifted
  **before** the conflict. This only makes sense for countries with a real dependency,
  so the first step is to identify the right countries and cases.
- Test whether political changes **precede** trade changes, with a delay of 1–6 months.
- Extend the commodity lens to oil (HS 2709/2710), chips (HS 8542) and critical raw
  materials.
- Use global trade data to include relationships between non-EU countries.

## How to run
1. Install the dependencies (listed in `requirements.txt`):
```bash
   pip install -r requirements.txt
```
2. Add your GENOME API key: copy `.env.example` to `.env` and fill in your key:
```
   GENOME_API_KEY=genome_your_key_here
```
   Without a `.env` file the notebook asks for the key when it starts. Press Enter to
   skip it; the notebook then retrieves at most 250 events per request.
   
3. Open the notebook and run all cells:
```bash
   jupyter notebook analysis.ipynb
```
   The notebook imports `data_events.py` and `data_trading.py` from the same folder,
   so keep all files together and run the notebook from the repository root.
   
4. Change the period, countries or product in the **Settings** cell.



    
## Repository structure
| File | Contents |
|---|---|
| `analysis.ipynb` | Main notebook: settings, data retrieval, charts |
| `data_events.py` | Retrieves GENOME events and aggregates them per country pair per month |
| `data_trading.py` | Retrieves Eurostat trade data and computes flows, balances and totals |
| `README.md` | Python dependencies |
