# Frozen retrieval stack on public benchmarks (nDCG@10)

## Thai

| task | docs | queries | dense | BM25 | hybrid | hybrid - dense (95% CI) | BM25 - dense |
|---|---|---|---|---|---|---|---|
| NitiBench-CCL (Thai law) | 5127 | 3729 | 0.781 | 0.724 | **0.818** | +0.037 [+0.031, +0.042] | -0.057 |
| belebele_tha_thai_tha_thai | 488 | 200 | 0.959 | 0.949 | **0.983** | +0.024 [+0.010, +0.040] | -0.010 |
| xqu_ad_th | 240 | 200 | 0.966 | 0.980 | **0.986** | +0.020 [+0.008, +0.034] | +0.015 |
| belebele_eng_latn_tha_thai | 488 | 200 | 0.916 | 0.065 | **0.914** | -0.002 [-0.005, +0.000] | -0.851 |
| belebele_tha_thai_eng_latn | 488 | 200 | 0.930 | 0.038 | **0.919** | -0.011 [-0.020, -0.004] | -0.892 |
| mkqa_th | 6652 | 200 | 0.036 | 0.018 | **0.032** | -0.005 [-0.012, +0.002] | -0.018 |
| web_faq_tha | 10000 | 200 | 0.888 | 0.697 | **0.889** | +0.001 [-0.016, +0.020] | -0.191 |
| mr_tidy_thai | 10000 | 200 | 0.966 | 0.850 | **0.970** | +0.004 [-0.006, +0.013] | -0.116 |
| miracl_th | 10000 | 200 | 0.903 | 0.622 | **0.872** | -0.031 [-0.052, -0.010] | -0.281 |
| multi_long_doc_th | 10000 | 200 | 0.174 | 0.313 | **0.279** | +0.105 [+0.076, +0.132] | +0.138 |

hybrid beats dense (interval above 0) on 4 of 10 Thai tasks and is worse (interval below 0) on 2.

## English medical (domain shift)

| task | docs | queries | dense | BM25 | hybrid | hybrid - dense (95% CI) | BM25 - dense |
|---|---|---|---|---|---|---|---|
| SciFact (biomedical claims, EN) | 5183 | 300 | 0.642 | 0.631 | **0.687** | +0.046 [+0.026, +0.067] | -0.010 |
| NFCorpus (nutrition/medicine, EN) | 3633 | 323 | 0.318 | 0.295 | **0.341** | +0.022 [+0.013, +0.033] | -0.024 |
| CURE dermatology (clinician questions, EN) | 15687 | 200 | 0.658 | 0.353 | **0.616** | -0.041 [-0.064, -0.019] | -0.305 |
| CURE pulmonology (clinician questions, EN) | 32317 | 200 | 0.617 | 0.340 | **0.597** | -0.019 [-0.034, -0.005] | -0.276 |

hybrid beats dense on 2 of 4 English medical tasks and is worse on 2. (For English the frozen tokenizer splits Latin text into words and uses character 3-grams only for Thai, so this BM25 is ordinary word-level BM25.)

Pattern: the hybrid gain shrinks as BM25 falls behind dense (Pearson r = 0.93 between 'BM25 - dense' and 'hybrid - dense' over 11 tasks; the two cross-lingual sets, where BM25 cannot match across languages, and mkqa, where every method scores near 0, are left out).

GPU (float16) vs CPU (float32) on 8 Thai tasks: largest nDCG@10 difference 0.0027 (belebele_tha_thai_eng_latn, hybrid).

Settings: bge-m3 (max length 512, no prefix); BM25 k1 2.18, b 0.86; convex fusion alpha 0.6, pool 100 (configs/retrieval/frozen_v1.json). Nothing tuned on these sets. Retrieval only: no generation, and not a measure of clinical correctness. Kaggle T4, float16, torch cu128.
