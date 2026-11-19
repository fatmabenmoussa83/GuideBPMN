# GuideBPMN — replication package

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24362598.svg)](https://doi.org/10.5281/zenodo.24362598)

Website: https://fatmabenmoussa83.github.io/GuideBPMN/ · Archived version: https://doi.org/10.5281/zenodo.24362598

GuideBPMN generates BPMN 2.0 models from textual process descriptions with LLMs and
learns modeling guidelines from the mistakes it verifies. An orchestrator agent
(LLM + LangGraph) calls the components as tools:

    generate -> validate -> evaluate -> detect failures -> learn -> revise (next iteration) ... -> stop

This package holds the implementation evaluated in the paper (the three settings
First, Revised and Reuse, with GPT-6 Luna and Claude Haiku 5.5), the data, the runs
of the study and the scripts that produce its tables.

| Step | Component | Where | LLM |
|---|---|---|---|
| 1 | Inputs: task prompt, process description, documentation guidelines | `bpmn_generator_catalogue/prompts/`, `bpmn_generator_catalogue/dataset.json`, `guidelines/bpmn_documentation_guidelines.json` | – |
| 2 | Generator | `bpmn_generator_catalogue/generator.py`, `bpmn_pipeline/generation.py` | yes |
| 3 | Structural validator (L1 syntax & schema, L2 gateways, L3 sequence flows, L4 collaboration) | `validator.py`, `soundness.py`, `xsd/`, `bpmn_pipeline/validation.py` | no |
| 4 | Similarity evaluator (flow order, participants, connections, label meaning, element coverage) | `similarity_evaluator/`, `bpmn_pipeline/evaluation.py` | no (sentence embeddings, BAAI/bge-base-en-v1.5) |
| 5 | Failure detector (T1–T7) | `bpmn_pipeline/diagnosis.py` | no |
| 6 | Guideline agents: Retriever and Expert (ReAct loops with tools) | `bpmn_pipeline/guideline_agents_tools.py` (the agents), `bpmn_pipeline/guideline_agents.py` (evidence records, code guards, catalogue update) | yes |
| 7 | Guideline catalogue (documentation, generic and example-specific error-driven guidelines) | `bpmn_pipeline/guideline_store.py`, `guidelines/learned/<model>/agents/` | – |
| – | Orchestrator agent | `bpmn_pipeline/orchestrator_agent.py`, `bpmn_pipeline/orchestrator_tools.py` | yes |
| – | Study: runs, folds, reports | `bpmn_pipeline/run_batch.py`, `folds.py`, `study_report.py`, `fold_report.py`, `rescore.py`, `utility.py`, `run_kfold.ps1` | – |
| – | Website and its API | `docs/`, `webapi/` | – |

Dataset: 55 descriptions with their reference models (PMo), `bpmn_generator_catalogue/dataset.json`.
Documentation guidelines: 82 rules paraphrased from the OMG BPMN 2.0.2 specification.

## Install

Python 3.10 or later. Windows (PowerShell):

```
python -m venv env
env\Scripts\python -m pip install -r requirements.txt -r webapi\requirements-web.txt
```

Linux / macOS: `python3 -m venv env && env/bin/pip install -r requirements.txt -r webapi/requirements-web.txt`.
The first run downloads the sentence-embedding model BAAI/bge-base-en-v1.5 (about 0.4 GB).

Set the key of the LLM you use in the terminal, e.g. `$env:OPENAI_API_KEY = "..."` (PowerShell) or
`export ANTHROPIC_API_KEY=...` (bash): `OPENAI_API_KEY` for GPT-6 Luna,
`ANTHROPIC_API_KEY` for Claude Haiku 5.5. Keys are read from the terminal only; they are never written to a file. Any other model of these two providers can be
named as `provider:model`. Without a key, dry runs (no LLM call) still work.

## Try it: one description from zero

From the website: `.\start_webapi.ps1`, open `docs\run.html`, card "Test one description
from zero", then download the zip of everything the tool did. From the command line
(in `bpmn_pipeline/`):

```
python run_batch.py --arm documentation --ids 07 --next-iterations 3 --force-iterations --promote-confirmed --trial ^
    --generator openai:gpt-6-luna --orchestrator openai:gpt-6-luna --retriever openai:gpt-6-luna --expert openai:gpt-6-luna
```

A trial learns into a catalogue of its own (`guidelines/learned/<model>/agents/trials/`),
never into the catalogues of the study.

## The study (from the repository root, PowerShell)

```
.\run_kfold.ps1 -Phase first       # First: 3 runs, documentation guidelines only, 55 descriptions
.\run_kfold.ps1 -Phase revised     # Revised: 3 runs, learning with 3 forced next iterations
.\run_kfold.ps1 -Phase train       # Reuse: training of the 5 rounds (44 descriptions each)
.\run_kfold.ps1 -Phase watch       # unattended: starts each round's test when its training is complete, resumes lost steps
python bpmn_pipeline\study_report.py --generator openai:gpt-6-luna          # the tables of the paper
python bpmn_pipeline\study_report.py --generator anthropic:claude-haiku-5-5
```

Each run is saved in `bpmn_pipeline/runs/<run>/` with its settings (`models.json`), every
draft, the validator and similarity results, the orchestrator's decisions and, for every
learn call, the full trace of the Retriever and Expert agents
(`id_NN/guideline_learning_history.json`). `study_report.py` rebuilds the tables from the
saved runs without any LLM call.

## Layout

```
bpmn_generator_catalogue/   dataset, prompts, generator
bpmn_pipeline/              orchestrator, tools, agents, failure detector, study scripts, runs/ (the 32 runs of the study)
similarity_evaluator/       the similarity evaluator
guidelines/                 documentation guidelines; learned/ holds the catalogues of the study
xsd/                        the official BPMN 2.0 schemas (structural validator L1)
validator.py, soundness.py  the structural validator (L1–L4, deadlock check)
webapi/                     the API behind the website
docs/                       the website (static pages; docs/_build/build.py regenerates them)
```

## Where to find the results of the paper

| What | Where |
|---|---|
| Tables of the paper (mean, SD, Wilcoxon tests) | `bpmn_pipeline/runs/_study_reports/<model>_agents_<date>/study.md` and `study.json` |
| The 32 runs (3 First, 3 Revised, 5 Reuse trainings, 5 Reuse tests, per model) | `bpmn_pipeline/runs/batch_<date>_<model>_<setting>/` |
| One description of a run: drafts, validator and similarity results, decisions, agents' trace | `bpmn_pipeline/runs/<run>/id_NN/` |
| The learned guidelines, readable | `guidelines/learned/<model>/agents/{replicates/rN,folds/fold_N}/learned_guidelines.md` (also `.csv`; full records in `.json`); index in `guidelines/learned/README.md` |
| The guidelines given to each Reuse test | `bpmn_pipeline/runs/<Reuse test run>/learned_guidelines_used.json` |
| The 82 documentation guidelines | `guidelines/bpmn_documentation_guidelines.json` |
| Dataset (55 descriptions and reference models) | `bpmn_generator_catalogue/dataset.json` |

## The website

The website is the `docs/` folder. Published with GitHub Pages (source: `main`, folder `/docs`), its
pages can be read online. To run GuideBPMN from it (page "Run GuideBPMN", card "Test one description
from zero"), start the API on your own computer with your key (`.\start_webapi.ps1`, it listens on
`http://127.0.0.1:8765`) and open the page, online or `docs\run.html` locally: the page calls the API
on your computer; your key never leaves it. Your browser may ask once to allow the site to reach
your local network: accept.

## Results of the study

The tables of the paper are in `bpmn_pipeline/runs/_study_reports/<model>_agents_<date>/study.md`
(`study.json` holds the per-run values and the Wilcoxon tests). Distribution of the similarity
scores over the 55 descriptions (each description: its mean over the 3 runs of First and Learned;
its single Reuse test), mean / SD / min / max:

| Model | Setting | Stat | Act. P | Act. R | Act. F1 | Conn. P | Conn. R | Conn. F1 | Flow order | Coverage |
|---|---|---|---|---|---|---|---|---|---|---|
| GPT-6 Luna | First | Mean | 0.76 | 0.70 | 0.71 | 0.31 | 0.26 | 0.28 | 0.43 | 0.55 |
| | | SD | 0.21 | 0.21 | 0.19 | 0.20 | 0.19 | 0.19 | 0.21 | 0.19 |
| | | Min | 0.23 | 0.13 | 0.16 | 0.01 | 0.01 | 0.01 | 0.03 | 0.14 |
| | | Max | 1.00 | 1.00 | 0.99 | 0.94 | 0.92 | 0.93 | 0.97 | 0.97 |
| | Learned | Mean | 0.80 | 0.74 | 0.76 | 0.39 | 0.34 | 0.36 | 0.50 | 0.59 |
| | | SD | 0.19 | 0.23 | 0.20 | 0.23 | 0.24 | 0.23 | 0.23 | 0.20 |
| | | Min | 0.23 | 0.18 | 0.20 | 0.00 | 0.00 | 0.00 | 0.11 | 0.18 |
| | | Max | 1.00 | 1.00 | 1.00 | 0.96 | 0.95 | 0.96 | 0.98 | 0.98 |
| | Reuse | Mean | 0.79 | 0.70 | 0.73 | 0.33 | 0.28 | 0.29 | 0.46 | 0.56 |
| | | SD | 0.21 | 0.22 | 0.20 | 0.22 | 0.21 | 0.21 | 0.21 | 0.20 |
| | | Min | 0.14 | 0.05 | 0.07 | 0.00 | 0.00 | 0.00 | 0.06 | 0.09 |
| | | Max | 1.00 | 1.00 | 1.00 | 0.89 | 0.86 | 0.87 | 0.95 | 0.95 |
| Claude Haiku 5.5 | First | Mean | 0.77 | 0.63 | 0.68 | 0.32 | 0.25 | 0.27 | 0.43 | 0.53 |
| | | SD | 0.20 | 0.21 | 0.20 | 0.19 | 0.19 | 0.19 | 0.20 | 0.18 |
| | | Min | 0.26 | 0.19 | 0.22 | 0.05 | 0.03 | 0.04 | 0.08 | 0.26 |
| | | Max | 1.00 | 1.00 | 0.98 | 0.91 | 0.87 | 0.89 | 0.95 | 0.95 |
| | Learned | Mean | 0.80 | 0.75 | 0.76 | 0.46 | 0.41 | 0.43 | 0.54 | 0.64 |
| | | SD | 0.18 | 0.23 | 0.20 | 0.23 | 0.25 | 0.24 | 0.23 | 0.20 |
| | | Min | 0.27 | 0.19 | 0.22 | 0.06 | 0.05 | 0.06 | 0.10 | 0.24 |
| | | Max | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| | Reuse | Mean | 0.75 | 0.64 | 0.68 | 0.33 | 0.26 | 0.28 | 0.44 | 0.54 |
| | | SD | 0.23 | 0.24 | 0.23 | 0.23 | 0.22 | 0.22 | 0.23 | 0.21 |
| | | Min | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.10 |
| | | Max | 1.00 | 1.00 | 1.00 | 0.93 | 0.93 | 0.93 | 0.98 | 1.00 |

The scores vary widely between descriptions (minima near 0, maxima at 1): the difficulty of the
descriptions is far from uniform. Learned has the strongest results, as expected when the
feedback of the description's own reference is available; Reuse improves the flow order and the
number of errors over First without that reference.

## Main technologies

| Technology | Purpose |
|---|---|
| LangGraph | State graph of the orchestrator agent and its tools |
| OpenAI, Anthropic SDKs | Access to the configured LLMs |
| Pydantic | Validation of the agents' structured outputs |
| lxml and the BPMN 2.0 XSD | XML parsing and schema validation (L1) |
| NetworkX | Process graphs, reachability, flow order |
| Sentence Transformers (BAAI/bge-base-en-v1.5) | Label and guideline embeddings |
| SciPy | Hungarian matching, Wilcoxon tests |
| FastAPI | Local API behind the website |
| HTML/JavaScript, bpmn-js | Website; drawing of the generated and reference models |
