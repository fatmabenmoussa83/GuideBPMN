# Demonstration scenarios

Each scenario follows one process description of the PMo dataset through the three settings of the paper:
**First** (documentation guidelines only), **Revised** (three iterations with the error-driven guidelines learned
from its own errors) and **Reuse** (the confirmed generic guidelines learned on other descriptions). For each stage,
the scenario gives the diagram of the generated model, its open errors and its similarity to the reference model,
and the guidelines GuideBPMN learned.

| Scenario | Description | Reference model | LLM | First | Revised: draft → i1 → i2 → i3 | Reuse |
|---|---|---|---|---|---|---|
| [1](scenario_1_description_19_luna/README.md) | 19 | one process, no pools or lanes | GPT-6 Luna | 12 | 21 → 12 → 11 → 5 | 7 |
| [2](scenario_2_description_02_haiku/README.md) | 02 | one process, no pools or lanes | Claude Haiku 5.5 | 33 | 32 → 18 → 12 → 12 | 19 |
| [3](scenario_3_description_15_haiku/README.md) | 15 | one process, no pools or lanes | Claude Haiku 5.5 | 27 | 41 → 29 → 18 → 6 | 21 |
| [4](scenario_4_description_24_luna/README.md) | 24 | 3 pools, 10 message flows | GPT-6 Luna | 74 | 61 → 31 → 27 → 27 | 95 |
| [5](scenario_5_description_23_haiku/README.md) | 23 | 3 pools, 6 message flows | Claude Haiku 5.5 | 48 | 55 → 42 → 39 → 39 | 46 |

(Numbers: open errors T1–T7 of the generated model; lower is better.)

Scenarios 1–3 are single processes; scenarios 4 and 5 are collaborations with pools, lanes and message flows.
The scenarios were chosen to illustrate the tool: in each, the Revised iterations keep or reduce the errors.
They are not representative of all descriptions (in scenario 4, Reuse has more errors than First): the averages
over the 55 descriptions are in the paper and in `bpmn_pipeline/runs/_study_reports/`. Every number above comes
from the run folders named in each scenario.

To run any description yourself, see "Try it: one description from zero" in the main README.
