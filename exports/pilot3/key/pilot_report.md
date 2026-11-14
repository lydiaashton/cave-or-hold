# Pilot report (harness numbers; judge costs are in judging/judge_report.md)

| model | world | condition | runs | reached turn 4 | reached turn 8 | mean own tokens / run | mean output tokens / run | mean cost / run |
|---|---|---|---:|---:|---:|---:|---:|---:|
| openai-api/adaption/qwen3.5-397b | confounded | after_B | 10 | 10 | 10 | 107,249 | 4,402 | 0.0720 Adaption credits |
| openai-api/adaption/qwen3.5-397b | confounded | after_D | 10 | 10 | 10 | 106,892 | 4,613 | 0.0724 Adaption credits |
| openai-api/adaption/qwen3.5-397b | confounded | before_B | 10 | 10 | 10 | 189,112 | 12,117 | 0.1398 Adaption credits |
| openai-api/adaption/qwen3.5-397b | confounded | before_D | 10 | 10 | 10 | 219,285 | 13,593 | 0.1607 Adaption credits |
| openai-api/adaption/qwen3.5-397b | confounded | never | 10 | 10 | 10 | 249,180 | 12,684 | 0.1745 Adaption credits |
| openai-api/adaption/qwen3.5-397b | strong | after_B | 10 | 10 | 10 | 55,738 | 4,374 | 0.0436 Adaption credits |
| openai-api/adaption/qwen3.5-397b | strong | after_D | 10 | 10 | 10 | 49,335 | 3,954 | 0.0388 Adaption credits |
| openai-api/adaption/qwen3.5-397b | strong | before_B | 10 | 10 | 10 | 171,845 | 10,699 | 0.1261 Adaption credits |
| openai-api/adaption/qwen3.5-397b | strong | before_D | 10 | 10 | 10 | 168,227 | 10,681 | 0.1240 Adaption credits |
| openai-api/adaption/qwen3.5-397b | strong | never | 10 | 10 | 10 | 95,410 | 9,590 | 0.0808 Adaption credits |
| openai-api/adaption/qwen3.5-397b | underpowered | after_B | 10 | 10 | 10 | 70,085 | 3,935 | 0.0502 Adaption credits |
| openai-api/adaption/qwen3.5-397b | underpowered | after_D | 10 | 10 | 10 | 68,595 | 3,883 | 0.0492 Adaption credits |
| openai-api/adaption/qwen3.5-397b | underpowered | before_B | 10 | 10 | 10 | 142,304 | 10,187 | 0.1083 Adaption credits |
| openai-api/adaption/qwen3.5-397b | underpowered | before_D | 10 | 10 | 10 | 142,026 | 9,470 | 0.1061 Adaption credits |
| openai-api/adaption/qwen3.5-397b | underpowered | never | 10 | 10 | 10 | 135,840 | 10,556 | 0.1059 Adaption credits |

Own tokens exclude an After run's shared turns 1-2, which are counted once, on its Never run. Prices come from harness/prices.toml.
