# ReAct vs fixed pipeline: test split (52 answerable, 4 unanswerable), run once, frozen_react_v1

Judge gpt-5.6-luna high, validator N7, retrieval variant B for the agent, prompt p2, no human check (silver).

| system | correctness | faithfulness | hit@5 | citation ok | abstained (of 4) | tokens/question |
|---|---|---|---|---|---|---|
| A dense | 0.798 | 0.803 | 43/52 | 36/49 | 3 | 4.8k |
| B hybrid (convex a=0.6) | 0.885 | 0.827 | 46/52 | 38/50 | 3 | 4.8k |
| C B + rerank | 0.904 | 0.886 | 48/52 | 39/51 | 4 | 4.8k |
| D BM25 only | 0.808 | 0.768 | 42/52 | 39/46 | 2 | 4.8k |
| ReAct, plain Python (seed_search, 3 rounds) | 0.827 | 0.833 | 47/52 | 38/48 | 3 | 26.5k |
| ReAct, LangGraph (same settings) | 0.827 | 0.833 | 47/52 | 38/48 | 3 | 26.5k |

- Python and LangGraph agents: 56/56 identical answers and statuses (same cache, same tools).
- Paired bootstrap, ReAct minus B, correctness: -0.058, 95% CI [-0.154, +0.038] (n=52). Faithfulness: +0.011, CI [-0.096, +0.121] (n=47). Neither separates from 0.
- By type (correctness, ReAct vs B): number_unit 0.82 vs 0.91, condition 0.72 vs 0.94, fact 0.91 vs 0.97, table 0.71 vs 0.64, multi_page 1.00 vs 0.67 (n=3). Small n per type.
- Conclusion: ReAct does not beat the fixed pipeline B or C in this domain, at about 5.5x the tokens. Retrieval hit@5 is slightly higher (47 vs 46) because of the seed search.
