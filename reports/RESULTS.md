# Results (generated)

This file is written by `make run`. Do not edit by hand.

Cohort: 5,998 leads first contacted 2018-01-01 to 2018-05-31; 678 won within 90 days (11.3%).

## 1. Conversion by source

| origin | leads | wins | rate | ci low | ci high | share of leads | share of wins | rankable |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| organic search | 1736 | 213 | 12.3% | 10.8% | 13.9% | 28.9% | 31.4% | yes |
| paid search | 1182 | 147 | 12.4% | 10.7% | 14.4% | 19.7% | 21.7% | yes |
| social | 1051 | 55 | 5.2% | 4.0% | 6.7% | 17.5% | 8.1% | yes |
| unknown | 813 | 157 | 19.3% | 16.7% | 22.2% | 13.6% | 23.2% | yes |
| direct traffic | 380 | 49 | 12.9% | 9.9% | 16.6% | 6.3% | 7.2% | yes |
| email | 347 | 12 | 3.5% | 2.0% | 5.9% | 5.8% | 1.8% | yes |
| referral | 211 | 21 | 10.0% | 6.6% | 14.7% | 3.5% | 3.1% | yes |
| other | 114 | 4 | 3.5% | 1.4% | 8.7% | 1.9% | 0.6% | yes |
| display | 75 | 5 | 6.7% | 2.9% | 14.7% | 1.3% | 0.7% | no |
| missing | 48 | 12 | 25.0% | 14.9% | 38.8% | 0.8% | 1.8% | no |
| other publicities | 41 | 3 | 7.3% | 2.5% | 19.4% | 0.7% | 0.4% | no |

Chi-square test of independence: chi2 = 134.5, dof = 10, p = 5.5e-24.

### Odds ratios vs organic search, adjusted for contact month

| origin | odds ratio | or low | or high | p value | p holm | significant after holm |
|---|---:|---:|---:|---:|---:|---:|
| missing | 2.43 | 1.24 | 4.75 | 0.0097 | 0.0579 | no |
| unknown | 1.70 | 1.36 | 2.14 | 0.0000 | 0.0000 | yes |
| direct traffic | 1.06 | 0.76 | 1.48 | 0.7291 | 1.0000 | no |
| paid search | 1.02 | 0.81 | 1.27 | 0.8949 | 1.0000 | no |
| referral | 0.80 | 0.50 | 1.28 | 0.3560 | 1.0000 | no |
| other publicities | 0.56 | 0.17 | 1.83 | 0.3375 | 1.0000 | no |
| display | 0.49 | 0.20 | 1.24 | 0.1334 | 0.6669 | no |
| social | 0.39 | 0.29 | 0.54 | 0.0000 | 0.0000 | yes |
| email | 0.26 | 0.14 | 0.48 | 0.0000 | 0.0001 | yes |
| other | 0.25 | 0.09 | 0.69 | 0.0074 | 0.0521 | no |

## 2. Speed to close (won within 90 days)

| origin | wins | median days | p75 days | within 14d |
|---|---:|---:|---:|---:|
| organic search | 213 | 10 | 22 | 64% |
| unknown | 157 | 9 | 21 | 67% |
| paid search | 147 | 9 | 19 | 63% |
| social | 55 | 18 | 36 | 40% |
| direct traffic | 49 | 8 | 15 | 73% |
| referral | 21 | 11 | 31 | 57% |
| email | 12 | 14 | 28 | 50% |
| missing | 12 | 6 | 9 | 83% |
| display | 5 | 10 | 16 | 60% |
| other | 4 | 9 | 20 | 75% |
| other publicities | 3 | 35 | 42 | 0% |

## 3. Landing pages

Pooled page prior: Beta(1.78, 18.42), mean 8.8%. 407 pages in the cohort.

Top 5 by raw rate (what a naive ranking would show):

| page | leads | wins | raw rate | shrunk rate |
|---|---:|---:|---:|---:|
| 6b6c0934 | 2 | 2 | 100.0% | 17.0% |
| 8515f4df | 2 | 2 | 100.0% | 17.0% |
| b3346ddd | 2 | 2 | 100.0% | 17.0% |
| 3c3d58fa | 1 | 1 | 100.0% | 13.1% |
| 5963a9ba | 1 | 1 | 100.0% | 13.1% |

Pages with 100+ leads (the ones a decision can rest on):

| page | leads | wins | raw rate | shrunk rate |
|---|---:|---:|---:|---:|
| b76ef374 | 751 | 152 | 20.2% | 19.9% |
| 22c29808 | 726 | 149 | 20.5% | 20.2% |
| 58326e62 | 495 | 22 | 4.4% | 4.6% |
| ce1a65ab | 346 | 47 | 13.6% | 13.3% |
| 88740e65 | 306 | 21 | 6.9% | 7.0% |
| 40dec9f3 | 297 | 58 | 19.5% | 18.8% |
| f017be4d | 224 | 16 | 7.1% | 7.3% |
| e492ee5e | 214 | 8 | 3.7% | 4.2% |
| a7982125 | 132 | 11 | 8.3% | 8.4% |
| 73f31a40 | 113 | 4 | 3.5% | 4.3% |

Top 10 by shrunk rate:

| page | leads | wins | raw rate | shrunk rate | cred low | cred high |
|---|---:|---:|---:|---:|---:|---:|
| 22c29808 | 726 | 149 | 20.5% | 20.2% | 17.8% | 22.7% |
| b76ef374 | 751 | 152 | 20.2% | 19.9% | 17.6% | 22.3% |
| 40dec9f3 | 297 | 58 | 19.5% | 18.8% | 15.4% | 22.6% |
| 6b6c0934 | 2 | 2 | 100.0% | 17.0% | 6.1% | 31.4% |
| 8515f4df | 2 | 2 | 100.0% | 17.0% | 6.1% | 31.4% |
| b3346ddd | 2 | 2 | 100.0% | 17.0% | 6.1% | 31.4% |
| 358adb2f | 20 | 5 | 25.0% | 16.9% | 8.3% | 27.3% |
| 30077c17 | 39 | 8 | 20.5% | 16.5% | 9.3% | 25.0% |
| c35447dc | 15 | 4 | 26.7% | 16.4% | 7.5% | 27.6% |
| fa5a0151 | 15 | 4 | 26.7% | 16.4% | 7.5% | 27.6% |

## 4. Lead scoring (train Jan-Mar, test Apr-May)

Train: 3,343 leads, 11.9% won. Test: 2,655 leads, 10.5% won; 23% of test leads came from landing pages not seen in training.

| model | roc auc | pr auc | brier | log loss | top 10pct | top 20pct | top 30pct | top 50pct |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| channel only | 0.624 | 0.148 | 0.092 | 0.326 | 0.164 | 0.311 | 0.421 | 0.657 |
| logistic without page | 0.640 | 0.155 | 0.092 | 0.326 | 0.179 | 0.339 | 0.457 | 0.675 |
| logistic | 0.696 | 0.192 | 0.090 | 0.316 | 0.214 | 0.425 | 0.554 | 0.754 |
| gradient boosting | 0.677 | 0.188 | 0.091 | 0.319 | 0.214 | 0.382 | 0.539 | 0.746 |

Bootstrap 95% intervals (1,000 resamples of the test set):

- ROC AUC channel_only: 0.593 to 0.659
- ROC AUC logistic_without_page: 0.608 to 0.673
- ROC AUC logistic: 0.664 to 0.729
- ROC AUC gradient_boosting: 0.646 to 0.711
- AUC gain of logistic_without_page over source-only: -0.002 to +0.033
- AUC gain of logistic over source-only: +0.045 to +0.098
- AUC gain of gradient_boosting over source-only: +0.022 to +0.085

Calibration of the logistic score on the test set (deciles of predicted probability):

| bin | leads | mean predicted | observed |
|---:|---:|---:|---:|
| 1.0 | 266.0 | 0.042 | 0.041 |
| 2.0 | 265.0 | 0.056 | 0.030 |
| 3.0 | 266.0 | 0.066 | 0.049 |
| 4.0 | 265.0 | 0.078 | 0.072 |
| 5.0 | 266.0 | 0.088 | 0.068 |
| 6.0 | 265.0 | 0.100 | 0.072 |
| 7.0 | 265.0 | 0.119 | 0.140 |
| 8.0 | 266.0 | 0.151 | 0.135 |
| 9.0 | 265.0 | 0.182 | 0.219 |
| 10.0 | 266.0 | 0.235 | 0.229 |

## 5. After the deal: did the seller start selling?

621 deals won by 2018-06-01 with a full 90-day window; 43.6% made at least one sale in that window in the public order data (a lower bound, see DQ08).

| origin | deals | active | activation rate | ci low | ci high | gmv per deal | share of gmv |
|---|---:|---:|---:|---:|---:|---:|---:|
| organic search | 195 | 79 | 40.5% | 33.9% | 47.5% | 450 | 26.5% |
| unknown | 148 | 60 | 40.5% | 33.0% | 48.6% | 853 | 38.1% |
| paid search | 131 | 71 | 54.2% | 45.7% | 62.5% | 549 | 21.7% |
| social | 48 | 22 | 45.8% | 32.6% | 59.7% | 261 | 3.8% |
| direct traffic | 46 | 21 | 45.7% | 32.2% | 59.8% | 188 | 2.6% |
| referral | 18 | 8 | 44.4% | 24.6% | 66.3% | 638 | 3.5% |
| email | 12 | 5 | 41.7% | 19.3% | 68.0% | 511 | 1.9% |
| missing | 11 | 3 | 27.3% | 9.7% | 56.6% | 53 | 0.2% |
| display | 5 | 1 | 20.0% | 3.6% | 62.4% | 55 | 0.1% |
| other | 4 | 1 | 25.0% | 4.6% | 69.9% | 1,321 | 1.6% |
| other publicities | 3 | 0 | 0.0% | 0.0% | 56.2% | 0 | 0.0% |

By lead type:

| lead type | deals | active | activation rate | gmv per deal | share of gmv |
|---|---:|---:|---:|---:|---:|
| online medium | 255 | 122 | 47.8% | 352 | 29.7% |
| online big | 94 | 59 | 62.8% | 1,690 | 52.5% |
| industry | 88 | 30 | 34.1% | 176 | 5.1% |
| offline | 77 | 20 | 26.0% | 94 | 2.4% |
| online small | 56 | 20 | 35.7% | 349 | 6.5% |
| online beginner | 37 | 13 | 35.1% | 239 | 2.9% |
| online top | 11 | 5 | 45.5% | 244 | 0.9% |
