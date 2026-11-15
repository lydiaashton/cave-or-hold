# Pilot report (harness numbers; judge costs are in judging/judge_report.md)

| model | world | condition | runs | reached turn 4 | reached turn 8 | mean own tokens / run | mean output tokens / run | mean cost / run |
|---|---|---|---:|---:|---:|---:|---:|---:|
| openai-api/adaption/qwen3.5-397b | confounded | after_B | 60 | 60 | 60 | 94,771 | 4,664 | 0.0659 Adaption credits |
| openai-api/adaption/qwen3.5-397b | confounded | after_D | 60 | 60 | 60 | 91,902 | 4,401 | 0.0635 Adaption credits |
| openai-api/adaption/qwen3.5-397b | confounded | before_B | 60 | 60 | 60 | 185,490 | 12,307 | 0.1383 Adaption credits |
| openai-api/adaption/qwen3.5-397b | confounded | before_D | 60 | 60 | 60 | 195,364 | 12,823 | 0.1453 Adaption credits |
| openai-api/adaption/qwen3.5-397b | confounded | never | 60 | 60 | 60 | 203,231 | 12,163 | 0.1477 Adaption credits |
| openai-api/adaption/qwen3.5-397b | strong | after_B | 60 | 60 | 60 | 74,131 | 4,354 | 0.0536 Adaption credits |
| openai-api/adaption/qwen3.5-397b | strong | after_D | 60 | 60 | 60 | 75,743 | 4,299 | 0.0543 Adaption credits |
| openai-api/adaption/qwen3.5-397b | strong | before_B | 60 | 60 | 60 | 155,782 | 9,864 | 0.1148 Adaption credits |
| openai-api/adaption/qwen3.5-397b | strong | before_D | 60 | 60 | 60 | 155,079 | 9,982 | 0.1147 Adaption credits |
| openai-api/adaption/qwen3.5-397b | strong | never | 60 | 60 | 60 | 163,429 | 10,663 | 0.1213 Adaption credits |
| openai-api/adaption/qwen3.5-397b | underpowered | after_B | 60 | 60 | 60 | 72,100 | 4,225 | 0.0521 Adaption credits |
| openai-api/adaption/qwen3.5-397b | underpowered | after_D | 60 | 60 | 60 | 70,504 | 4,189 | 0.0511 Adaption credits |
| openai-api/adaption/qwen3.5-397b | underpowered | before_B | 60 | 60 | 60 | 146,232 | 10,735 | 0.1121 Adaption credits |
| openai-api/adaption/qwen3.5-397b | underpowered | before_D | 60 | 60 | 60 | 155,856 | 11,310 | 0.1191 Adaption credits |
| openai-api/adaption/qwen3.5-397b | underpowered | never | 60 | 60 | 60 | 154,467 | 11,033 | 0.1175 Adaption credits |

Own tokens exclude an After run's shared turns 1-2, which are counted once, on its Never run. Prices come from harness/prices.toml.
