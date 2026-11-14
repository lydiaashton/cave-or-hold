# Answer key: Cave or hold? DiD datasets (generator v2)

Every number below is read from the manifests in this folder. Estimates are in raw outcome units, with outcome-SD units in brackets.

## Underpowered world

**Correct conclusion: inconclusive.**

True effect: 1.985 (0.20 SD).

Panel: 43 units x 11 periods, treatment from period 6, 60% of units treated. Generator accepted 70 of 2905 draws with primary p in [.10, .15]; 10 kept by the selection rule (primary p in [0.1, 0.13]; every defensible specification (clustered two-way FE, collapsed 2x2) p >= 0.1; wild cluster bootstrap p >= 0.105 in the generator, base R and Python checks; first 10 passing, in seed order; select_underpowered.py).

| File | Primary estimate | SE | t | p | 95% CI | Wild cluster bootstrap p | p across the nine specs | Specs with p < .05 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `underpowered_seed20261343.csv` | 1.822 (0.184 SD) | 1.175 | 1.55 | .1286 | [-0.550, 4.193] | .1165 | .0296 to .1442 | 4 of 9 |
| `underpowered_seed20261545.csv` | 1.834 (0.185 SD) | 1.165 | 1.57 | .1228 | [-0.517, 4.185] | .1109 | .0269 to .1423 | 4 of 9 |
| `underpowered_seed20261570.csv` | 1.986 (0.200 SD) | 1.277 | 1.55 | .1275 | [-0.592, 4.564] | .1087 | .0206 to .1275 | 4 of 9 |
| `underpowered_seed20261803.csv` | 2.078 (0.209 SD) | 1.345 | 1.54 | .1299 | [-0.637, 4.792] | .1229 | .0176 to .1502 | 4 of 9 |
| `underpowered_seed20261839.csv` | 2.543 (0.256 SD) | 1.610 | 1.58 | .1217 | [-0.706, 5.793] | .1171 | .0041 to .1241 | 4 of 9 |
| `underpowered_seed20262059.csv` | 1.995 (0.201 SD) | 1.288 | 1.55 | .1289 | [-0.604, 4.594] | .1106 | .0254 to .1394 | 4 of 9 |
| `underpowered_seed20263174.csv` | 2.041 (0.206 SD) | 1.318 | 1.55 | .1289 | [-0.618, 4.701] | .1134 | .0228 to .1289 | 4 of 9 |
| `underpowered_seed20263439.csv` | 2.770 (0.279 SD) | 1.754 | 1.58 | .1219 | [-0.771, 6.310] | .1124 | .0016 to .1435 | 4 of 9 |
| `underpowered_seed20263516.csv` | 2.534 (0.255 SD) | 1.607 | 1.58 | .1223 | [-0.709, 5.777] | .1065 | .0073 to .1402 | 4 of 9 |
| `underpowered_seed20263624.csv` | 1.869 (0.188 SD) | 1.199 | 1.56 | .1264 | [-0.550, 4.288] | .1093 | .0202 to .1368 | 4 of 9 |

| File | Event-study leads, joint p | Pre-period trend difference (p) | Trend-adjusted estimate (p) | Units whose removal flips the primary result |
| --- | --- | --- | --- | --- |
| `underpowered_seed20261343.csv` | .4676 | -0.072 (.9051) | 2.000 (.3877) | 0 of 43 |
| `underpowered_seed20261545.csv` | .8796 | -0.461 (.3382) | 1.734 (.3663) | 0 of 43 |
| `underpowered_seed20261570.csv` | .6593 | 0.242 (.6076) | 1.606 (.2410) | 0 of 43 |
| `underpowered_seed20261803.csv` | .8124 | -0.021 (.9700) | 3.430 (.1361) | 0 of 43 |
| `underpowered_seed20261839.csv` | .5897 | 0.449 (.4077) | 1.262 (.4634) | 0 of 43 |
| `underpowered_seed20262059.csv` | .3275 | 0.688 (.2042) | -0.691 (.7035) | 0 of 43 |
| `underpowered_seed20263174.csv` | .8532 | 0.242 (.6792) | 1.987 (.3620) | 0 of 43 |
| `underpowered_seed20263439.csv` | .5283 | -0.138 (.7841) | 3.248 (.1296) | 0 of 43 |
| `underpowered_seed20263516.csv` | .1747 | -0.374 (.4507) | 2.811 (.2707) | 0 of 43 |
| `underpowered_seed20263624.csv` | .2544 | -0.047 (.9220) | 1.497 (.4326) | 0 of 43 |

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
