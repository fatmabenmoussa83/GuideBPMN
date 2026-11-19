# Generator (step 2)

`generator.py` turns one process description into BPMN 2.0 XML with one LLM:
provider `gpt` (OpenAI, key `OPENAI_API_KEY`) or `claude` (Anthropic, key
`ANTHROPIC_API_KEY`). The prompt (`prompts/`) carries the task, the description and
the documentation guidelines (`../guidelines/bpmn_documentation_guidelines.json`);
in a next iteration it also carries the previous model, the validator report and
the guidelines sent back by the pipeline (`correction_feedback`). No reference model
is ever sent to the LLM. Each call is audited in `prompt_audit/` next to its output.

The pipeline calls `run()` through `bpmn_pipeline/generation.py`; standalone use:

```
python generator.py --provider gpt --model gpt-6-luna --ids 24
python generator.py --provider claude --model claude-haiku-5-5 --ids 41-55
```

Output: `outputs/generated_bpmn_<provider>.json`. `dataset.json` is the dataset of
the study (55 descriptions with their reference models).
