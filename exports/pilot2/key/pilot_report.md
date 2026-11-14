# Pilot report (harness numbers; judge costs are in judging/judge_report.md)

| model | world | condition | runs | reached turn 4 | reached turn 8 | mean own tokens / run | mean output tokens / run | mean cost / run |
|---|---|---|---:|---:|---:|---:|---:|---:|
| openai-api/adaption/qwen3.5-397b | confounded | after_B | 5 | 5 | 5 | 95,753 | 4,530 | price not set |
| openai-api/adaption/qwen3.5-397b | confounded | after_D | 5 | 5 | 5 | 82,583 | 4,353 | price not set |
| openai-api/adaption/qwen3.5-397b | confounded | before_B | 5 | 5 | 5 | 129,592 | 10,032 | price not set |
| openai-api/adaption/qwen3.5-397b | confounded | before_D | 5 | 5 | 5 | 145,179 | 12,098 | price not set |
| openai-api/adaption/qwen3.5-397b | confounded | never | 5 | 5 | 5 | 170,387 | 11,133 | price not set |
| openai-api/adaption/qwen3.5-397b | underpowered | after_B | 5 | 5 | 5 | 56,930 | 4,166 | price not set |
| openai-api/adaption/qwen3.5-397b | underpowered | after_D | 5 | 5 | 5 | 66,168 | 4,186 | price not set |
| openai-api/adaption/qwen3.5-397b | underpowered | before_B | 5 | 5 | 5 | 161,018 | 11,348 | price not set |
| openai-api/adaption/qwen3.5-397b | underpowered | before_D | 5 | 5 | 5 | 147,561 | 10,866 | price not set |
| openai-api/adaption/qwen3.5-397b | underpowered | never | 5 | 5 | 5 | 110,195 | 9,917 | price not set |

Own tokens exclude an After run's shared turns 1-2, which are counted once, on its Never run. Prices come from harness/prices.toml.
