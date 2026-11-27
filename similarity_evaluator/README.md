# Similarity evaluator (step 4)

Compares a generated model with its reference: pairing of the elements
(`semantic_contextual_alignment.py`, sentence embeddings BAAI/bge-base-en-v1.5 and the
Hungarian algorithm), label meaning (`semantic_family_similarity.py`), connections
(`connection_matching.py`), workflow order (`workflow_order_similarity.py`), participants
(`collaboration_similarity.py`), element counts (`type_matching.py`). The pipeline calls
it through `bpmn_pipeline/evaluation.py`; every equation is on the website page
"Similarity evaluator".

Standalone use of one module on a saved draft:
`python workflow_order_similarity.py 24 <run>/id_24/round_0/generated_bpmn_gpt.json`
(the dataset gives the reference of description 24).
