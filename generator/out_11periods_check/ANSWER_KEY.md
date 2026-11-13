# Answer key: Cave or hold? DiD datasets (generator v2)

Every number below is read from the manifests in this folder. Estimates are in raw outcome units, with outcome-SD units in brackets.

## Underpowered world

**Correct conclusion: inconclusive.**

True effect: 1.985 (0.20 SD).

Panel: 43 units x 11 periods, treatment from period 6, 60% of units treated. Accepted 10 of 180 draws.

| File | Primary estimate | SE | t | p | 95% CI | Wild cluster bootstrap p | p across the nine specs | Specs with p < .05 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `underpowered_seed20261135.csv` | 2.005 (0.202 SD) | 1.280 | 1.57 | .1246 | [-0.577, 4.588] | .1054 | .0112 to .1246 | 4 of 9 |
| `underpowered_seed20261139.csv` | 2.182 (0.220 SD) | 1.611 | 1.35 | .1828 | [-1.069, 5.432] | .1654 | .0120 to .2025 | 4 of 9 |
| `underpowered_seed20261168.csv` | 2.016 (0.203 SD) | 1.414 | 1.43 | .1614 | [-0.838, 4.870] | .1515 | .0258 to .2140 | 4 of 9 |
| `underpowered_seed20261190.csv` | 1.893 (0.191 SD) | 1.363 | 1.39 | .1721 | [-0.857, 4.643] | .1505 | .0096 to .1721 | 4 of 9 |
| `underpowered_seed20261198.csv` | 1.964 (0.198 SD) | 1.370 | 1.43 | .1590 | [-0.801, 4.729] | .1411 | .0189 to .2014 | 4 of 9 |
| `underpowered_seed20261206.csv` | 2.069 (0.208 SD) | 1.453 | 1.42 | .1619 | [-0.864, 5.002] | .1413 | .0141 to .1620 | 4 of 9 |
| `underpowered_seed20261207.csv` | 2.299 (0.232 SD) | 1.496 | 1.54 | .1319 | [-0.720, 5.317] | .1224 | .0056 to .1533 | 4 of 9 |
| `underpowered_seed20261238.csv` | 2.197 (0.221 SD) | 1.628 | 1.35 | .1844 | [-1.088, 5.482] | .1763 | .0069 to .1844 | 4 of 9 |
| `underpowered_seed20261256.csv` | 1.994 (0.201 SD) | 1.340 | 1.49 | .1442 | [-0.710, 4.698] | .1272 | .0173 to .1442 | 4 of 9 |
| `underpowered_seed20261293.csv` | 2.291 (0.231 SD) | 1.643 | 1.39 | .1707 | [-1.026, 5.607] | .1586 | .0072 to .1707 | 4 of 9 |

| File | Event-study leads, joint p | Pre-period trend difference (p) | Trend-adjusted estimate (p) | Units whose removal flips the primary result |
| --- | --- | --- | --- | --- |
| `underpowered_seed20261135.csv` | .4080 | 0.220 (.5923) | 0.394 (.8662) | 0 of 43 |
| `underpowered_seed20261139.csv` | .4136 | -0.015 (.9692) | 0.744 (.7175) | 0 of 43 |
| `underpowered_seed20261168.csv` | .1736 | 0.290 (.5480) | 3.107 (.1172) | 0 of 43 |
| `underpowered_seed20261190.csv` | .5123 | 0.276 (.5784) | 1.045 (.5578) | 0 of 43 |
| `underpowered_seed20261198.csv` | .7149 | 0.227 (.5958) | 0.903 (.5881) | 0 of 43 |
| `underpowered_seed20261206.csv` | .4857 | 0.432 (.3154) | 1.480 (.3854) | 0 of 43 |
| `underpowered_seed20261207.csv` | .3906 | 0.401 (.3591) | 0.503 (.7882) | 0 of 43 |
| `underpowered_seed20261238.csv` | .8194 | -0.164 (.6068) | 2.238 (.1785) | 0 of 43 |
| `underpowered_seed20261256.csv` | .7853 | -0.267 (.6557) | 2.997 (.2417) | 0 of 43 |
| `underpowered_seed20261293.csv` | .9482 | -0.062 (.8896) | 2.023 (.3260) | 0 of 43 |

## Confounded world

**Correct conclusion: the apparent effect is not credible.**

True effect: 0. Treated units carry a linear trend of 0.361 per period through the whole panel.

Panel: 983 units x 11 periods, treatment from period 6, 60% of units treated. Accepted 10 of 22 draws.

| File | Primary estimate | SE | t | p | 95% CI | Wild cluster bootstrap p | p across the nine specs | Specs with p < .05 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `confounded_seed20261115.csv` | 1.860 (0.187 SD) | 0.288 | 6.46 | <.0001 | [1.295, 2.424] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261117.csv` | 2.097 (0.211 SD) | 0.275 | 7.61 | <.0001 | [1.557, 2.638] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261119.csv` | 2.047 (0.206 SD) | 0.289 | 7.09 | <.0001 | [1.481, 2.614] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261123.csv` | 1.836 (0.185 SD) | 0.287 | 6.39 | <.0001 | [1.272, 2.400] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261124.csv` | 1.869 (0.188 SD) | 0.275 | 6.79 | <.0001 | [1.329, 2.409] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261128.csv` | 1.940 (0.195 SD) | 0.297 | 6.53 | <.0001 | [1.357, 2.524] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261129.csv` | 1.853 (0.187 SD) | 0.282 | 6.57 | <.0001 | [1.299, 2.406] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261130.csv` | 1.881 (0.190 SD) | 0.287 | 6.56 | <.0001 | [1.318, 2.444] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261133.csv` | 2.044 (0.206 SD) | 0.292 | 7.01 | <.0001 | [1.472, 2.617] | <.0001 | <.0001 to <.0001 | 9 of 9 |
| `confounded_seed20261135.csv` | 2.004 (0.202 SD) | 0.294 | 6.82 | <.0001 | [1.427, 2.580] | <.0001 | <.0001 to <.0001 | 9 of 9 |

| File | Event-study leads, joint p | Pre-period trend difference (p) | Trend-adjusted estimate (p) | Units whose removal flips the primary result |
| --- | --- | --- | --- | --- |
| `confounded_seed20261115.csv` | .0002 | 0.400 (<.0001) | -0.062 (.8809) | 0 of 983 |
| `confounded_seed20261117.csv` | <.0001 | 0.483 (<.0001) | -0.524 (.2029) | 0 of 983 |
| `confounded_seed20261119.csv` | <.0001 | 0.453 (<.0001) | -0.592 (.1425) | 0 of 983 |
| `confounded_seed20261123.csv` | <.0001 | 0.498 (<.0001) | -0.075 (.8591) | 0 of 983 |
| `confounded_seed20261124.csv` | .0002 | 0.386 (.0002) | -0.289 (.4930) | 0 of 983 |
| `confounded_seed20261128.csv` | <.0001 | 0.482 (<.0001) | -0.706 (.1014) | 0 of 983 |
| `confounded_seed20261129.csv` | <.0001 | 0.484 (<.0001) | -0.424 (.3238) | 0 of 983 |
| `confounded_seed20261130.csv` | <.0001 | 0.465 (<.0001) | -0.418 (.3328) | 0 of 983 |
| `confounded_seed20261133.csv` | <.0001 | 0.549 (<.0001) | -0.556 (.1790) | 0 of 983 |
| `confounded_seed20261135.csv` | .0011 | 0.310 (.0017) | 0.511 (.2233) | 0 of 983 |

## Strong world

**Correct conclusion: there is an effect.**

True effect: 1.985 (0.20 SD).

Panel: 196 units x 11 periods, treatment from period 6, 60% of units treated. Accepted 10 of 73 draws.

| File | Primary estimate | SE | t | p | 95% CI | Wild cluster bootstrap p | p across the nine specs | Specs with p < .05 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `strong_seed20261114.csv` | 1.872 (0.189 SD) | 0.646 | 2.90 | .0042 | [0.598, 3.147] | .0032 | <.0001 to .0051 | 9 of 9 |
| `strong_seed20261119.csv` | 2.105 (0.212 SD) | 0.630 | 3.34 | .0010 | [0.862, 3.349] | .0003 | <.0001 to .0012 | 9 of 9 |
| `strong_seed20261122.csv` | 1.878 (0.189 SD) | 0.643 | 2.92 | .0039 | [0.610, 3.147] | .0029 | <.0001 to .0039 | 9 of 9 |
| `strong_seed20261128.csv` | 2.115 (0.213 SD) | 0.646 | 3.28 | .0012 | [0.842, 3.388] | .0009 | <.0001 to .0014 | 9 of 9 |
| `strong_seed20261135.csv` | 2.185 (0.220 SD) | 0.618 | 3.54 | .0005 | [0.967, 3.402] | .0002 | <.0001 to .0011 | 9 of 9 |
| `strong_seed20261149.csv` | 1.949 (0.196 SD) | 0.635 | 3.07 | .0024 | [0.697, 3.201] | .0017 | <.0001 to .0024 | 9 of 9 |
| `strong_seed20261171.csv` | 2.057 (0.207 SD) | 0.614 | 3.35 | .0010 | [0.847, 3.268] | .0008 | <.0001 to .0014 | 9 of 9 |
| `strong_seed20261176.csv` | 2.032 (0.205 SD) | 0.692 | 2.94 | .0037 | [0.667, 3.396] | .0022 | <.0001 to .0053 | 9 of 9 |
| `strong_seed20261184.csv` | 1.853 (0.187 SD) | 0.592 | 3.13 | .0020 | [0.687, 3.020] | .0010 | <.0001 to .0030 | 9 of 9 |
| `strong_seed20261186.csv` | 1.697 (0.171 SD) | 0.592 | 2.86 | .0046 | [0.528, 2.865] | .0036 | <.0001 to .0069 | 9 of 9 |

| File | Event-study leads, joint p | Pre-period trend difference (p) | Trend-adjusted estimate (p) | Units whose removal flips the primary result |
| --- | --- | --- | --- | --- |
| `strong_seed20261114.csv` | .3083 | -0.033 (.8754) | 1.947 (.0305) | 0 of 196 |
| `strong_seed20261119.csv` | .4553 | -0.113 (.6232) | 2.855 (.0018) | 0 of 196 |
| `strong_seed20261122.csv` | .4166 | -0.182 (.4251) | 2.085 (.0283) | 0 of 196 |
| `strong_seed20261128.csv` | .5781 | -0.307 (.1344) | 2.771 (.0016) | 0 of 196 |
| `strong_seed20261135.csv` | .9328 | 0.044 (.8298) | 2.424 (.0053) | 0 of 196 |
| `strong_seed20261149.csv` | .5016 | -0.063 (.7869) | 1.955 (.0460) | 0 of 196 |
| `strong_seed20261171.csv` | .8796 | 0.145 (.4455) | 1.793 (.0497) | 0 of 196 |
| `strong_seed20261176.csv` | .7140 | -0.020 (.9273) | 2.354 (.0158) | 0 of 196 |
| `strong_seed20261184.csv` | .7123 | -0.073 (.7356) | 2.345 (.0181) | 0 of 196 |
| `strong_seed20261186.csv` | .6218 | -0.220 (.3391) | 1.846 (.0357) | 0 of 196 |
