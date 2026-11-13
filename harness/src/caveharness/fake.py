"""Offline stand-in models for testing the harness: "cavefake/analyst" (the
tested model) and "cavefake/judge" (a judge, see _judge_output).

It behaves like a tool-using analyst: on the first request it calls the code
tool with a real two-way fixed effects regression and saves a chart into a
subfolder; on "finalize" it writes a uniquely named file into another subfolder
and lists every file (so a missing or partial sandbox restore on the After
branch would show); otherwise it writes a summary quoting the latest tool
output. Every reply carries a reasoning block, so the thinking-placeholder path
in the export is exercised. No API key, no cost.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re

from inspect_ai.model import (ChatCompletionChoice, ChatMessageAssistant,
                              ChatMessageTool, ChatMessageUser, ContentReasoning,
                              ContentText, GenerateConfig, ModelAPI, ModelOutput,
                              ModelUsage, modelapi)
from inspect_ai.tool import ToolCall

ANALYSIS = """import pandas as pd, statsmodels.formula.api as smf
import matplotlib.pyplot as plt
df = pd.read_csv("branches.csv")
df["D"] = df["switched_branch"] * df["after_switch"]
m = smf.ols("service_score ~ D + C(branch_id) + C(week)", data=df).fit(
    cov_type="cluster", cov_kwds={"groups": df["branch_id"]})
lo, hi = m.conf_int().loc["D"]
print(f"estimate={m.params['D']:.3f} ci=[{lo:.3f}, {hi:.3f}] p={m.pvalues['D']:.4f} n={len(df)}")
df.groupby(["week", "switched_branch"])["service_score"].mean().unstack().plot()
import os
os.makedirs("figs", exist_ok=True)
plt.savefig("figs/trend.png")
"""

# Writes a uniquely named file into a subfolder, then lists every file. The
# After branch must see the Never run's figs/trend.png (made before the branch
# point) but never the Never run's note (made after it). The 25,000 x's exceed
# the 20,000-character cap shown to the model, exercising full-output logging.
FINALIZE = """import os, uuid
os.makedirs("notes", exist_ok=True)
open("notes/note_" + uuid.uuid4().hex[:6] + ".txt", "w").write("x")
print(sorted(os.path.join(r, f) for r, _, fs in os.walk(".") for f in fs))
print("x" * 25000)
"""

_ids = itertools.count(1)

# "cavefake/judge": a stand-in judge. It reads the reply-format lines the judge
# runner appends to every prompt ('- "key": one of "a", "b"') and answers with
# one of the allowed values, picked from a hash of the prompt so different
# items get different (but reproducible) answers.
_FIELD = re.compile(r'^- "(\w+)": (.*)$', re.M)


def _judge_output(prompt: str) -> ModelOutput:
    out: dict = {}
    for key, what in _FIELD.findall(prompt):
        options = re.findall(r'"([^"]*)"', what) if what.startswith("one of ") else []
        pick = int(hashlib.sha256(f"{key}|{prompt}".encode()).hexdigest(), 16)
        out[key] = (options[pick % len(options)] if options
                    else [1.5, 2.0] if what == "a JSON list" else "(fake)")
    msg = ChatMessageAssistant(content=[ContentReasoning(reasoning="(fake judge reasoning)"),
                                        ContentText(text=f"```json\n{json.dumps(out)}\n```")],
                               model="judge", source="generate")
    return ModelOutput(model="judge", choices=[ChatCompletionChoice(message=msg, stop_reason="stop")],
                       usage=ModelUsage(input_tokens=len(prompt) // 4, output_tokens=60,
                                        total_tokens=len(prompt) // 4 + 60))


def _call(model: str, thinking, text: str, code: str) -> tuple[ChatMessageAssistant, str]:
    msg = ChatMessageAssistant(
        content=[thinking, ContentText(text=text)],
        tool_calls=[ToolCall(id=f"call_{next(_ids)}", function="python",
                             arguments={"code": code})],
        model=model, source="generate")
    return msg, "tool_calls"


@modelapi(name="cavefake")
class CaveFake(ModelAPI):
    def __init__(self, model_name, base_url=None, api_key=None, api_key_vars=[],
                 config=GenerateConfig(), **kwargs):
        super().__init__(model_name, base_url, api_key, api_key_vars, config)

    async def generate(self, input, tools, tool_choice, config):
        if self.model_name == "judge":
            return _judge_output(input[-1].text or "")
        last = input[-1]
        said = (last.text or "").lower() if isinstance(last, ChatMessageUser) else ""
        thinking = ContentReasoning(reasoning="(fake private reasoning)")
        first = not any(isinstance(m, ChatMessageTool) for m in input)
        if tools and "summary for the board. include" in said and first:
            msg, stop = _call(self.model_name, thinking, "Let me run the analysis.", ANALYSIS)
        elif tools and "finalize" in said:
            msg, stop = _call(self.model_name, thinking, "Re-checking the files.", FINALIZE)
        else:
            results = [m.text for m in input if isinstance(m, ChatMessageTool)]
            ask = said or "(tool result)"
            body = ("Title: Shelving change and service scores. "
                    f"Bottom line: (fake) based on {results[-1].strip() if results else 'no analysis'}. "
                    f"Replying to: {ask[:60]}")
            msg = ChatMessageAssistant(content=[thinking, ContentText(text=body)],
                                       model=self.model_name, source="generate")
            stop = "stop"
        return ModelOutput(model=self.model_name,
                           choices=[ChatCompletionChoice(message=msg, stop_reason=stop)],
                           usage=ModelUsage(input_tokens=100 * len(input), output_tokens=50,
                                            total_tokens=100 * len(input) + 50))
