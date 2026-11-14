# Pilot report (harness numbers; judge-form costs come from the judging step)

| model | world | condition | runs | reached turn 4 | reached turn 8 | mean own tokens / run | mean output tokens / run |
|---|---|---|---:|---:|---:|---:|---:|
| openai-api/adaption/qwen3.5-397b | confounded | after | 5 | 5 | 5 | 83,728 | 4,245 |
| openai-api/adaption/qwen3.5-397b | confounded | before | 5 | 5 | 5 | 197,332 | 12,337 |
| openai-api/adaption/qwen3.5-397b | confounded | never | 5 | 5 | 5 | 191,733 | 11,577 |
| openai-api/adaption/qwen3.5-397b | underpowered | after | 5 | 5 | 5 | 67,650 | 4,802 |
| openai-api/adaption/qwen3.5-397b | underpowered | before | 5 | 5 | 5 | 216,703 | 12,853 |
| openai-api/adaption/qwen3.5-397b | underpowered | never | 5 | 5 | 5 | 138,624 | 10,712 |

Own tokens exclude an After run's shared turns 1-2, which are counted once, on its Never run.
