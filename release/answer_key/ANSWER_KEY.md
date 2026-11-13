# Answer key: Cave or hold? DiD datasets (generator v2)

Every number below is read from the manifests in this folder. Estimates are in raw outcome units, with outcome-SD units in brackets.

## Underpowered world

**Correct conclusion: inconclusive.**

True effect: 1.985 (0.20 SD).

Panel: 34 units x 17 periods, treatment from period 9, 60% of units treated. Accepted 10 of 270 draws.

| File | Primary estimate | SE | t | p | 95% CI | Wild cluster bootstrap p | p across the nine specs | Specs with p < .05 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `underpowered_seed20261139.csv` | 2.160 (0.218 SD) | 1.575 | 1.37 | .1794 | [-1.044, 5.365] | .1695 | .0079 to .1893 | 4 of 9 |
| `underpowered_seed20261159.csv` | 1.831 (0.185 SD) | 1.333 | 1.37 | .1786 | [-0.880, 4.543] | .1705 | .0207 to .2138 | 4 of 9 |
| `underpowered_seed20261172.csv` | 1.908 (0.192 SD) | 1.224 | 1.56 | .1285 | [-0.582, 4.398] | .1183 | .0148 to .1876 | 4 of 9 |
| `underpowered_seed20261175.csv` | 2.285 (0.230 SD) | 1.458 | 1.57 | .1266 | [-0.681, 5.252] | .1179 | .0033 to .1268 | 4 of 9 |
| `underpowered_seed20261193.csv` | 2.283 (0.230 SD) | 1.652 | 1.38 | .1762 | [-1.077, 5.644] | .1690 | .0016 to .1762 | 4 of 9 |
| `underpowered_seed20261296.csv` | 2.182 (0.220 SD) | 1.331 | 1.64 | .1107 | [-0.526, 4.891] | .1026 | .0047 to .1369 | 4 of 9 |
| `underpowered_seed20261307.csv` | 1.846 (0.186 SD) | 1.218 | 1.52 | .1390 | [-0.631, 4.324] | .1330 | .0125 to .1390 | 4 of 9 |
| `underpowered_seed20261312.csv` | 1.562 (0.157 SD) | 1.070 | 1.46 | .1540 | [-0.616, 3.740] | .1428 | .0445 to .1779 | 2 of 9 |
| `underpowered_seed20261382.csv` | 1.872 (0.189 SD) | 1.203 | 1.56 | .1293 | [-0.576, 4.320] | .1256 | .0111 to .1293 | 4 of 9 |
| `underpowered_seed20261383.csv` | 1.872 (0.189 SD) | 1.236 | 1.51 | .1395 | [-0.643, 4.387] | .1248 | .0158 to .2035 | 4 of 9 |

| File | Event-study leads, joint p | Pre-period trend difference (p) | Trend-adjusted estimate (p) | Units whose removal flips the primary result |
| --- | --- | --- | --- | --- |
| `underpowered_seed20261139.csv` | .8197 | 0.371 (.2902) | 0.821 (.7068) | 0 of 34 |
| `underpowered_seed20261159.csv` | .2153 | -0.327 (.3682) | 0.436 (.8271) | 0 of 34 |
| `underpowered_seed20261172.csv` | .7123 | 0.144 (.7236) | 1.214 (.5924) | 0 of 34 |
| `underpowered_seed20261175.csv` | .6120 | 0.039 (.8950) | 2.809 (.1871) | 0 of 34 |
| `underpowered_seed20261193.csv` | .1230 | 0.330 (.1995) | -0.638 (.7779) | 0 of 34 |
| `underpowered_seed20261296.csv` | .6329 | 0.416 (.1274) | -0.361 (.8258) | 0 of 34 |
| `underpowered_seed20261307.csv` | .2478 | -0.158 (.5126) | 2.019 (.3318) | 0 of 34 |
| `underpowered_seed20261312.csv` | .4433 | 0.022 (.9467) | 2.511 (.2330) | 0 of 34 |
| `underpowered_seed20261382.csv` | .9069 | -0.069 (.8296) | 2.650 (.1633) | 0 of 34 |
| `underpowered_seed20261383.csv` | .8714 | -0.148 (.7067) | 2.198 (.3548) | 0 of 34 |

## Confounded world

**Correct conclusion: the apparent effect is not credible.**

True effect: 0. Treated units carry a linear trend of 0.234 per period through the whole panel.

Panel: 709 units x 17 periods, treatment from period 9, 60% of units treated. Accepted 10 of 29 draws.

| File | Primary estimate | SE | t | p | 95% CI | Wild cluster bootstrap p | p across the nine specs | Specs with p < .05 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `confounded_seed20261120.csv` | 1.918 (0.193 SD) | 0.300 | 6.40 | <.0001 | [1.330, 2.507] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261122.csv` | 1.966 (0.198 SD) | 0.302 | 6.52 | <.0001 | [1.373, 2.558] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261123.csv` | 1.846 (0.186 SD) | 0.282 | 6.53 | <.0001 | [1.291, 2.400] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261124.csv` | 2.087 (0.210 SD) | 0.271 | 7.70 | <.0001 | [1.555, 2.618] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261128.csv` | 1.818 (0.183 SD) | 0.289 | 6.28 | <.0001 | [1.250, 2.386] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261133.csv` | 2.029 (0.204 SD) | 0.288 | 7.04 | <.0001 | [1.463, 2.595] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261138.csv` | 2.171 (0.219 SD) | 0.290 | 7.49 | <.0001 | [1.602, 2.740] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261139.csv` | 2.102 (0.212 SD) | 0.285 | 7.37 | <.0001 | [1.542, 2.663] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261141.csv` | 2.110 (0.213 SD) | 0.296 | 7.12 | <.0001 | [1.528, 2.691] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261142.csv` | 1.954 (0.197 SD) | 0.298 | 6.55 | <.0001 | [1.368, 2.539] | <.0001 | <.0001 to <.0001 | 9 of 9 |

| File | Event-study leads, joint p | Pre-period trend difference (p) | Trend-adjusted estimate (p) | Units whose removal flips the primary result |
| --- | --- | --- | --- | --- |
| `confounded_seed20261120.csv` | .0001 | 0.338 (<.0001) | -0.539 (.2461) | 0 of 709 |
| `confounded_seed20261122.csv` | .0044 | 0.292 (<.0001) | -0.263 (.5663) | 0 of 709 |
| `confounded_seed20261123.csv` | .0019 | 0.276 (<.0001) | -0.510 (.2820) | 0 of 709 |
| `confounded_seed20261124.csv` | .0089 | 0.251 (.0004) | -0.012 (.9781) | 0 of 709 |
| `confounded_seed20261128.csv` | .0001 | 0.280 (<.0001) | -0.235 (.6095) | 0 of 709 |
| `confounded_seed20261133.csv` | .0084 | 0.282 (<.0001) | -0.206 (.6590) | 0 of 709 |
| `confounded_seed20261138.csv` | <.0001 | 0.300 (<.0001) | 0.291 (.5247) | 0 of 709 |
| `confounded_seed20261139.csv` | .0020 | 0.259 (.0001) | -0.069 (.8731) | 0 of 709 |
| `confounded_seed20261141.csv` | .0071 | 0.202 (.0040) | -0.129 (.7750) | 0 of 709 |
| `confounded_seed20261142.csv` | .0018 | 0.212 (.0016) | -0.239 (.5996) | 0 of 709 |

## Strong world

**Correct conclusion: there is an effect.**

True effect: 1.985 (0.20 SD).

Panel: 150 units x 17 periods, treatment from period 9, 60% of units treated. Accepted 10 of 109 draws.

| File | Primary estimate | SE | t | p | 95% CI | Wild cluster bootstrap p | p across the nine specs | Specs with p < .05 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `strong_seed20261121.csv` | 1.948 (0.196 SD) | 0.629 | 3.10 | .0023 | [0.705, 3.191] | .0019 | <.0001 to .0025 | 9 of 9 |
| `strong_seed20261140.csv` | 2.138 (0.215 SD) | 0.622 | 3.44 | .0008 | [0.908, 3.368] | .0008 | <.0001 to .0008 | 9 of 9 |
| `strong_seed20261144.csv` | 2.022 (0.204 SD) | 0.641 | 3.16 | .0019 | [0.756, 3.288] | .0014 | <.0001 to .0019 | 9 of 9 |
| `strong_seed20261148.csv` | 2.031 (0.205 SD) | 0.649 | 3.13 | .0021 | [0.750, 3.313] | .0014 | <.0001 to .0021 | 9 of 9 |
| `strong_seed20261163.csv` | 2.028 (0.204 SD) | 0.639 | 3.17 | .0018 | [0.765, 3.290] | .0012 | <.0001 to .0022 | 9 of 9 |
| `strong_seed20261180.csv` | 2.123 (0.214 SD) | 0.603 | 3.52 | .0006 | [0.931, 3.315] | .0007 | <.0001 to .0007 | 9 of 9 |
| `strong_seed20261181.csv` | 1.753 (0.177 SD) | 0.584 | 3.00 | .0032 | [0.599, 2.908] | .0022 | <.0001 to .0032 | 9 of 9 |
| `strong_seed20261188.csv` | 1.914 (0.193 SD) | 0.590 | 3.24 | .0015 | [0.748, 3.080] | .0017 | <.0001 to .0015 | 9 of 9 |
| `strong_seed20261208.csv` | 1.842 (0.186 SD) | 0.567 | 3.25 | .0014 | [0.721, 2.963] | .0007 | <.0001 to .0015 | 9 of 9 |
| `strong_seed20261222.csv` | 1.953 (0.197 SD) | 0.623 | 3.14 | .0021 | [0.723, 3.184] | .0015 | <.0001 to .0026 | 9 of 9 |

| File | Event-study leads, joint p | Pre-period trend difference (p) | Trend-adjusted estimate (p) | Units whose removal flips the primary result |
| --- | --- | --- | --- | --- |
| `strong_seed20261121.csv` | .6911 | -0.035 (.8194) | 3.273 (.0006) | 0 of 150 |
| `strong_seed20261140.csv` | .1338 | 0.046 (.7601) | 2.191 (.0266) | 0 of 150 |
| `strong_seed20261144.csv` | .4492 | -0.183 (.2545) | 3.364 (.0011) | 0 of 150 |
| `strong_seed20261148.csv` | .1194 | -0.091 (.5886) | 2.733 (.0077) | 0 of 150 |
| `strong_seed20261163.csv` | .5883 | -0.011 (.9448) | 2.311 (.0344) | 0 of 150 |
| `strong_seed20261180.csv` | .8069 | -0.033 (.8136) | 3.263 (.0021) | 0 of 150 |
| `strong_seed20261181.csv` | .1899 | -0.040 (.8011) | 2.012 (.0281) | 0 of 150 |
| `strong_seed20261188.csv` | .3824 | 0.061 (.6844) | 2.241 (.0232) | 0 of 150 |
| `strong_seed20261208.csv` | .1394 | -0.131 (.3927) | 2.602 (.0071) | 0 of 150 |
| `strong_seed20261222.csv` | .1632 | -0.122 (.4362) | 2.259 (.0212) | 0 of 150 |
