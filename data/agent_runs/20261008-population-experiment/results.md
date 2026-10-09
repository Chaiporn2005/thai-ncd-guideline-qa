# Population tags: with vs without (BM25 page-level, 44 silver questions)

asker detected from the question text correctly: 43/44
questions by asker: {'adult': 25, 'pregnancy': 7, 'elderly': 5, 'pediatric': 7}

## all (n=44)

| strategy | Recall@5 | Recall@10 | MRR@10 | lenient R@5 | Δ R@5 vs S0 [95% CI] | wrong-population pages in top 5 (adult questions) |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| S0 no tags | 0.70 | 0.77 | 0.514 | 0.75 | +0.00 [+0.00, +0.00] | 7/125 |
| S1 hard filter (detected asker) | 0.75 | 0.82 | 0.581 | 0.82 | +0.05 [+0.00, +0.11] | 0/125 |
| S1o hard filter (true asker) | 0.75 | 0.82 | 0.593 | 0.82 | +0.05 [+0.00, +0.11] | 0/125 |
| S2 drop other populations (detected) | 0.70 | 0.77 | 0.515 | 0.75 | +0.00 [+0.00, +0.00] | 0/125 |
| S2o drop other populations (true asker) | 0.70 | 0.77 | 0.515 | 0.75 | +0.00 [+0.00, +0.00] | 0/125 |
| S3a soft x0.8 / boost x1.2 (detected) | 0.70 | 0.80 | 0.561 | 0.77 | +0.00 [+0.00, +0.00] | 0/125 |
| S3b soft x0.5 / boost x1.5 (detected) | 0.73 | 0.82 | 0.567 | 0.82 | +0.02 [+0.00, +0.07] | 0/125 |
| S3ao soft x0.8 / boost x1.2 (true asker) | 0.70 | 0.80 | 0.561 | 0.77 | +0.00 [+0.00, +0.00] | 0/125 |

## adult questions (n=25)

| strategy | Recall@5 | Recall@10 | MRR@10 | lenient R@5 | Δ R@5 vs S0 [95% CI] | wrong-population pages in top 5 (adult questions) |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| S0 no tags | 0.64 | 0.76 | 0.516 | 0.68 | +0.00 [+0.00, +0.00] | 7/125 |
| S1 hard filter (detected asker) | 0.64 | 0.76 | 0.516 | 0.68 | +0.00 [+0.00, +0.00] | 0/125 |
| S1o hard filter (true asker) | 0.64 | 0.76 | 0.516 | 0.68 | +0.00 [+0.00, +0.00] | 0/125 |
| S2 drop other populations (detected) | 0.64 | 0.76 | 0.516 | 0.68 | +0.00 [+0.00, +0.00] | 0/125 |
| S2o drop other populations (true asker) | 0.64 | 0.76 | 0.516 | 0.68 | +0.00 [+0.00, +0.00] | 0/125 |
| S3a soft x0.8 / boost x1.2 (detected) | 0.64 | 0.76 | 0.516 | 0.68 | +0.00 [+0.00, +0.00] | 0/125 |
| S3b soft x0.5 / boost x1.5 (detected) | 0.64 | 0.76 | 0.516 | 0.68 | +0.00 [+0.00, +0.00] | 0/125 |
| S3ao soft x0.8 / boost x1.2 (true asker) | 0.64 | 0.76 | 0.516 | 0.68 | +0.00 [+0.00, +0.00] | 0/125 |

## population questions (n=19)

| strategy | Recall@5 | Recall@10 | MRR@10 | lenient R@5 | Δ R@5 vs S0 [95% CI] | wrong-population pages in top 5 (adult questions) |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| S0 no tags | 0.79 | 0.79 | 0.512 | 0.84 | +0.00 [+0.00, +0.00] | 0/- |
| S1 hard filter (detected asker) | 0.89 | 0.89 | 0.667 | 1.00 | +0.11 [+0.00, +0.26] | 0/- |
| S1o hard filter (true asker) | 0.89 | 0.89 | 0.693 | 1.00 | +0.11 [+0.00, +0.26] | 0/- |
| S2 drop other populations (detected) | 0.79 | 0.79 | 0.512 | 0.84 | +0.00 [+0.00, +0.00] | 0/- |
| S2o drop other populations (true asker) | 0.79 | 0.79 | 0.512 | 0.84 | +0.00 [+0.00, +0.00] | 0/- |
| S3a soft x0.8 / boost x1.2 (detected) | 0.79 | 0.84 | 0.620 | 0.89 | +0.00 [+0.00, +0.00] | 0/- |
| S3b soft x0.5 / boost x1.5 (detected) | 0.84 | 0.89 | 0.633 | 1.00 | +0.05 [+0.00, +0.16] | 0/- |
| S3ao soft x0.8 / boost x1.2 (true asker) | 0.79 | 0.84 | 0.620 | 0.89 | +0.00 [+0.00, +0.00] | 0/- |

