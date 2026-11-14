# Answer key: Cave or hold? DiD datasets (generator v2)

Every number below is read from the manifests in this folder. Estimates are in raw outcome units, with outcome-SD units in brackets.

## Underpowered world

**Correct conclusion: inconclusive.**

True effect: 1.985 (0.20 SD).

Panel: 34 units x 17 periods, treatment from period 9, 60% of units treated. Generator accepted 320 of 14364 draws with primary p in [.10, .15]; 60 kept by the selection rule (primary p in [0.1, 0.13]; every defensible specification (clustered two-way FE, collapsed 2x2) p >= 0.1; wild cluster bootstrap p >= 0.105 in the generator, base R and Python checks; first 60 passing, in seed order; select_underpowered.py).

| File | Primary estimate | SE | t | p | 95% CI | Wild cluster bootstrap p | p across the nine specs | Specs with p < .05 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `underpowered_seed20272763.csv` | 2.278 (0.230 SD) | 1.430 | 1.59 | .1206 | [-0.631, 5.187] | .1099 | .0057 to .1697 | 4 of 9 |
| `underpowered_seed20272989.csv` | 2.584 (0.260 SD) | 1.631 | 1.58 | .1227 | [-0.735, 5.904] | .1204 | .0018 to .1403 | 4 of 9 |
| `underpowered_seed20273209.csv` | 2.411 (0.243 SD) | 1.489 | 1.62 | .1150 | [-0.619, 5.440] | .1055 | .0039 to .1219 | 4 of 9 |
| `underpowered_seed20273237.csv` | 2.289 (0.231 SD) | 1.469 | 1.56 | .1286 | [-0.699, 5.277] | .1202 | .0057 to .1543 | 4 of 9 |
| `underpowered_seed20273384.csv` | 1.930 (0.194 SD) | 1.237 | 1.56 | .1282 | [-0.587, 4.446] | .1222 | .0131 to .1398 | 4 of 9 |
| `underpowered_seed20273409.csv` | 1.861 (0.187 SD) | 1.176 | 1.58 | .1232 | [-0.532, 4.254] | .1120 | .0215 to .1438 | 4 of 9 |
| `underpowered_seed20274264.csv` | 1.974 (0.199 SD) | 1.260 | 1.57 | .1266 | [-0.589, 4.538] | .1099 | .0151 to .1476 | 4 of 9 |
| `underpowered_seed20274541.csv` | 2.065 (0.208 SD) | 1.321 | 1.56 | .1276 | [-0.623, 4.752] | .1209 | .0056 to .1276 | 4 of 9 |
| `underpowered_seed20275324.csv` | 1.751 (0.176 SD) | 1.125 | 1.56 | .1290 | [-0.537, 4.040] | .1202 | .0200 to .1380 | 4 of 9 |
| `underpowered_seed20275460.csv` | 1.613 (0.163 SD) | 0.999 | 1.61 | .1158 | [-0.419, 3.646] | .1126 | .0352 to .1592 | 2 of 9 |

| File | Event-study leads, joint p | Pre-period trend difference (p) | Trend-adjusted estimate (p) | Units whose removal flips the primary result |
| --- | --- | --- | --- | --- |
| `underpowered_seed20272763.csv` | .4378 | -0.100 (.7623) | -0.104 (.9551) | 0 of 34 |
| `underpowered_seed20272989.csv` | .5399 | 0.056 (.8501) | 2.271 (.1901) | 0 of 34 |
| `underpowered_seed20273209.csv` | .4706 | 0.021 (.9543) | 1.564 (.5133) | 0 of 34 |
| `underpowered_seed20273237.csv` | .6833 | 0.127 (.6686) | 0.793 (.7129) | 0 of 34 |
| `underpowered_seed20273384.csv` | .8171 | -0.403 (.2503) | 3.022 (.1931) | 0 of 34 |
| `underpowered_seed20273409.csv` | .1829 | -0.217 (.5578) | 1.325 (.4894) | 0 of 34 |
| `underpowered_seed20274264.csv` | .4006 | 0.256 (.4136) | 2.054 (.3524) | 0 of 34 |
| `underpowered_seed20274541.csv` | .5906 | 0.338 (.2235) | 0.780 (.7160) | 0 of 34 |
| `underpowered_seed20275324.csv` | .4821 | 0.103 (.7616) | 1.043 (.5572) | 0 of 34 |
| `underpowered_seed20275460.csv` | .6572 | -0.094 (.7792) | 0.376 (.8370) | 0 of 34 |

## Confounded world

**Correct conclusion: the apparent effect is not credible.**

True effect: 0. Treated units carry a linear trend of 0.234 per period through the whole panel.

Panel: 709 units x 17 periods, treatment from period 9, 60% of units treated. Accepted 70 of 256 draws.

| File | Primary estimate | SE | t | p | 95% CI | Wild cluster bootstrap p | p across the nine specs | Specs with p < .05 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `confounded_seed20261325.csv` | 2.049 (0.206 SD) | 0.299 | 6.85 | <.0001 | [1.462, 2.636] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261329.csv` | 1.891 (0.191 SD) | 0.276 | 6.85 | <.0001 | [1.349, 2.434] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261334.csv` | 1.856 (0.187 SD) | 0.283 | 6.56 | <.0001 | [1.300, 2.412] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261339.csv` | 1.854 (0.187 SD) | 0.292 | 6.34 | <.0001 | [1.280, 2.427] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261342.csv` | 1.806 (0.182 SD) | 0.281 | 6.43 | <.0001 | [1.255, 2.358] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261353.csv` | 1.935 (0.195 SD) | 0.287 | 6.75 | <.0001 | [1.372, 2.498] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261356.csv` | 2.081 (0.210 SD) | 0.284 | 7.34 | <.0001 | [1.524, 2.638] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261359.csv` | 2.092 (0.211 SD) | 0.291 | 7.20 | <.0001 | [1.522, 2.663] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261363.csv` | 1.903 (0.192 SD) | 0.281 | 6.77 | <.0001 | [1.351, 2.455] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261369.csv` | 2.301 (0.232 SD) | 0.313 | 7.35 | <.0001 | [1.687, 2.915] | <.0001 | <.0001 to <.0001 | 9 of 9 |

| File | Event-study leads, joint p | Pre-period trend difference (p) | Trend-adjusted estimate (p) | Units whose removal flips the primary result |
| --- | --- | --- | --- | --- |
| `confounded_seed20261325.csv` | .0032 | 0.260 (.0001) | -0.069 (.8824) | 0 of 709 |
| `confounded_seed20261329.csv` | .0006 | 0.283 (<.0001) | 0.307 (.4944) | 0 of 709 |
| `confounded_seed20261334.csv` | .0002 | 0.358 (<.0001) | -0.408 (.3570) | 0 of 709 |
| `confounded_seed20261339.csv` | .0022 | 0.261 (.0005) | -0.198 (.6630) | 0 of 709 |
| `confounded_seed20261342.csv` | .0016 | 0.239 (.0012) | 0.256 (.5701) | 0 of 709 |
| `confounded_seed20261353.csv` | .0014 | 0.245 (.0006) | 0.119 (.7884) | 0 of 709 |
| `confounded_seed20261356.csv` | .0043 | 0.246 (.0005) | -0.212 (.6357) | 0 of 709 |
| `confounded_seed20261359.csv` | <.0001 | 0.345 (<.0001) | -0.015 (.9748) | 0 of 709 |
| `confounded_seed20261363.csv` | .0073 | 0.240 (.0005) | -0.119 (.7931) | 0 of 709 |
| `confounded_seed20261369.csv` | <.0001 | 0.313 (<.0001) | 0.131 (.7738) | 0 of 709 |

## Strong world

**Correct conclusion: there is an effect.**

True effect: 1.985 (0.20 SD).

Panel: 150 units x 17 periods, treatment from period 9, 60% of units treated. Accepted 70 of 642 draws.

| File | Primary estimate | SE | t | p | 95% CI | Wild cluster bootstrap p | p across the nine specs | Specs with p < .05 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `strong_seed20261639.csv` | 2.193 (0.221 SD) | 0.666 | 3.29 | .0012 | [0.877, 3.509] | .0008 | <.0001 to .0014 | 9 of 9 |
| `strong_seed20261643.csv` | 2.176 (0.219 SD) | 0.655 | 3.32 | .0011 | [0.882, 3.470] | .0004 | <.0001 to .0018 | 9 of 9 |
| `strong_seed20261648.csv` | 2.077 (0.209 SD) | 0.583 | 3.57 | .0005 | [0.926, 3.228] | .0005 | <.0001 to .0005 | 9 of 9 |
| `strong_seed20261678.csv` | 1.748 (0.176 SD) | 0.572 | 3.06 | .0027 | [0.618, 2.878] | .0021 | <.0001 to .0042 | 9 of 9 |
| `strong_seed20261680.csv` | 2.145 (0.216 SD) | 0.673 | 3.19 | .0018 | [0.815, 3.476] | .0022 | <.0001 to .0021 | 9 of 9 |
| `strong_seed20261684.csv` | 2.015 (0.203 SD) | 0.633 | 3.18 | .0018 | [0.765, 3.265] | .0006 | <.0001 to .0018 | 9 of 9 |
| `strong_seed20261707.csv` | 1.855 (0.187 SD) | 0.638 | 2.91 | .0042 | [0.594, 3.116] | .0033 | <.0001 to .0055 | 9 of 9 |
| `strong_seed20261736.csv` | 1.737 (0.175 SD) | 0.584 | 2.97 | .0034 | [0.582, 2.891] | .0021 | <.0001 to .0056 | 9 of 9 |
| `strong_seed20261748.csv` | 1.917 (0.193 SD) | 0.592 | 3.24 | .0015 | [0.747, 3.088] | .0013 | <.0001 to .0015 | 9 of 9 |
| `strong_seed20261755.csv` | 1.759 (0.177 SD) | 0.604 | 2.91 | .0041 | [0.566, 2.951] | .0031 | <.0001 to .0041 | 9 of 9 |

| File | Event-study leads, joint p | Pre-period trend difference (p) | Trend-adjusted estimate (p) | Units whose removal flips the primary result |
| --- | --- | --- | --- | --- |
| `strong_seed20261639.csv` | .8184 | -0.082 (.5676) | 2.697 (.0055) | 0 of 150 |
| `strong_seed20261643.csv` | .4303 | -0.220 (.1520) | 4.544 (<.0001) | 0 of 150 |
| `strong_seed20261648.csv` | .6572 | 0.153 (.3111) | 2.271 (.0133) | 0 of 150 |
| `strong_seed20261678.csv` | .8718 | -0.118 (.4521) | 2.740 (.0077) | 0 of 150 |
| `strong_seed20261680.csv` | .1006 | -0.048 (.7376) | 2.370 (.0165) | 0 of 150 |
| `strong_seed20261684.csv` | .9493 | -0.100 (.4712) | 2.075 (.0447) | 0 of 150 |
| `strong_seed20261707.csv` | .4121 | 0.034 (.8127) | 1.935 (.0434) | 0 of 150 |
| `strong_seed20261736.csv` | .2400 | -0.257 (.1124) | 3.123 (.0021) | 0 of 150 |
| `strong_seed20261748.csv` | .9512 | -0.186 (.2577) | 2.773 (.0020) | 0 of 150 |
| `strong_seed20261755.csv` | .6684 | 0.085 (.5776) | 1.867 (.0471) | 0 of 150 |
