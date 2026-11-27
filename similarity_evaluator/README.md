# Similarity evaluator (step 4)

Compares a generated model with its reference: pairing of the elements
(`semantic_contextual_alignment.py`, sentence embeddings BAAI/bge-base-en-v1.5 and the
Hungarian algorithm), activities (`semantic_family_similarity.py`), connections
(`connection_matching.py`), workflow order (`workflow_order_similarity.py`), swimlanes and messages
(`collaboration_similarity.py`), element counts (`type_matching.py`). The pipeline calls
it through `bpmn_pipeline/evaluation.py`; every equation is on the website page
"Similarity evaluator".

Standalone use of one module on a saved draft:
`python workflow_order_similarity.py 24 <run>/id_24/round_0/generated_bpmn_gpt.json`
(the dataset gives the reference of description 24).

## Measures and their provenance

The names are those of the paper (Table I).

| Measure | Definition | Based on |
|---|---|---|
| Activities | precision, recall, F1 of the activities paired by their label embeddings | BAAI/bge-base-en-v1.5 (Xiao et al., SIGIR 2024); Hungarian algorithm (Kuhn, 1955) |
| Connections | precision, recall, F1 of the sequence flows whose paired endpoints match a reference flow | same pairing |
| Coverage | paired elements / max(reference elements, generated elements) | Bunke and Shearer, Pattern Recognition Letters 19(3-4), 1998 (similarity form of their distance; pairing by labels, not an exact common subgraph) |
| Workflow order | Jaccard similarity of the precedence relations between paired elements, multiplied by coverage | Jaccard, New Phytologist 11(2), 1912 |
| Swimlanes and messages | Jaccard similarity of the pool, lane, lane-membership and message-flow relations; applies when the reference has swimlanes (6 of the 55 PMo descriptions) | Jaccard, 1912 |
