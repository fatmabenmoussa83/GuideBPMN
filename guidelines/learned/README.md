# Learned guidelines of the study

One catalogue per learning run. Each folder holds:

- `learned_guidelines.json`: the catalogue as GuideBPMN uses it (every guideline with its evidence records, the descriptions it was learned from, its relation to the documentation guidelines and its confirmation tests);
- `learned_guidelines.md`: the same guidelines to read (situation and instruction);
- `learned_guidelines.csv`: the same guidelines as a table.

`replicates/rN` = the 3 runs of *Revised* (55 descriptions); `folds/fold_N` = the 5 training rounds of *Reuse* (44 descriptions each; the 11 test descriptions of the round received only its confirmed generic guidelines).

| Model | Setting | Guidelines | Folder |
|---|---|---|---|
| Claude Haiku 5.5 | Reuse training, round 1 (44 descriptions) | 159 | `anthropic-claude-haiku-5-5/agents/folds/fold_1/` |
| Claude Haiku 5.5 | Reuse training, round 2 (44 descriptions) | 157 | `anthropic-claude-haiku-5-5/agents/folds/fold_2/` |
| Claude Haiku 5.5 | Reuse training, round 3 (44 descriptions) | 167 | `anthropic-claude-haiku-5-5/agents/folds/fold_3/` |
| Claude Haiku 5.5 | Reuse training, round 4 (44 descriptions) | 162 | `anthropic-claude-haiku-5-5/agents/folds/fold_4/` |
| Claude Haiku 5.5 | Reuse training, round 5 (44 descriptions) | 168 | `anthropic-claude-haiku-5-5/agents/folds/fold_5/` |
| Claude Haiku 5.5 | Revised, run 1 | 189 | `anthropic-claude-haiku-5-5/agents/replicates/r1/` |
| Claude Haiku 5.5 | Revised, run 2 | 179 | `anthropic-claude-haiku-5-5/agents/replicates/r2/` |
| Claude Haiku 5.5 | Revised, run 3 | 189 | `anthropic-claude-haiku-5-5/agents/replicates/r3/` |
| GPT-6 Luna | Reuse training, round 1 (44 descriptions) | 85 | `openai-gpt-6-luna/agents/folds/fold_1/` |
| GPT-6 Luna | Reuse training, round 2 (44 descriptions) | 90 | `openai-gpt-6-luna/agents/folds/fold_2/` |
| GPT-6 Luna | Reuse training, round 3 (44 descriptions) | 90 | `openai-gpt-6-luna/agents/folds/fold_3/` |
| GPT-6 Luna | Reuse training, round 4 (44 descriptions) | 91 | `openai-gpt-6-luna/agents/folds/fold_4/` |
| GPT-6 Luna | Reuse training, round 5 (44 descriptions) | 105 | `openai-gpt-6-luna/agents/folds/fold_5/` |
| GPT-6 Luna | Revised, run 1 | 100 | `openai-gpt-6-luna/agents/replicates/r1/` |
| GPT-6 Luna | Revised, run 2 | 94 | `openai-gpt-6-luna/agents/replicates/r2/` |
| GPT-6 Luna | Revised, run 3 | 103 | `openai-gpt-6-luna/agents/replicates/r3/` |
