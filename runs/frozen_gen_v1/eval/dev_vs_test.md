# Dev vs test (answer quality)

dev: dev_p2_N7 (answerable 97), test: test_luna_N7 (answerable 52); validator N7 / N7

| metric | A dev | A test | B dev | B test | C dev | C test | order dev | order test |
|---|---|---|---|---|---|---|---|---|
| correctness score (0-1) | 0.856 | 0.798 | 0.876 | 0.885 | 0.902 | 0.904 | C > B > A | C > B > A |
| faithfulness | 0.867 | 0.803 | 0.910 | 0.827 | 0.888 | 0.886 | B > C > A | C > B > A |
| BERTScore F1 | 0.824 | 0.821 | 0.827 | 0.821 | 0.828 | 0.821 | C > B > A | A > B > C |
| BERTScore Recall | 0.908 | 0.903 | 0.911 | 0.905 | 0.913 | 0.902 | C > B > A | B > A > C |
| retrieval hit@5 | 0.876 | 0.827 | 0.928 | 0.885 | 0.928 | 0.923 | B > C > A | C > B > A |
| citation correct | answered | 0.753 | 0.735 | 0.809 | 0.760 | 0.804 | 0.765 | B > C > A | C > B > A |
| answerable refused (share) | 0.041 | 0.058 | 0.031 | 0.038 | 0.000 | 0.019 | A > B > C | A > B > C |
| unanswerable abstained (share) | 0.889 | 0.750 | 0.889 | 0.750 | 0.778 | 1.000 | A > B > C | C > A > B |

Paired differences (mean [95% CI]):

| comparison | dev | test |
|---|---|---|
| B - A: correctness_score | +0.021 [-0.026, +0.072] (n=97) | +0.086 [+0.010, +0.173] (n=52) |
| B - A: bert_f1 | +0.002 [-0.004, +0.009] (n=92) | -0.003 [-0.008, +0.004] (n=47) |
| B - A: faithfulness | +0.034 [-0.015, +0.085] (n=92) | +0.004 [-0.064, +0.078] (n=47) |
| C - A: correctness_score | +0.046 [-0.010, +0.103] (n=97) | +0.106 [+0.029, +0.192] (n=52) |
| C - A: bert_f1 | +0.003 [-0.003, +0.010] (n=93) | -0.003 [-0.013, +0.006] (n=48) |
| C - A: faithfulness | +0.023 [-0.034, +0.081] (n=93) | +0.069 [-0.004, +0.146] (n=48) |
| C - B: correctness_score | +0.026 [-0.021, +0.077] (n=97) | +0.019 [-0.048, +0.096] (n=52) |
| C - B: bert_f1 | +0.001 [-0.004, +0.006] (n=94) | +0.002 [-0.006, +0.010] (n=50) |
| C - B: faithfulness | -0.014 [-0.062, +0.030] (n=94) | +0.067 [-0.013, +0.153] (n=50) |

Read with care: the dev and test questions differ, test has only 52 answerable questions, and the judge is one model. An interval that contains 0 means the difference cannot be told from noise, not that there is none.
