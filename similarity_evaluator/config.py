"""Central configuration for every independently testable evaluator module."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
# The repository's single source of truth for the 55 descriptions and references.
DATASET_PATH = ROOT.parent / "bpmn_generator_catalogue" / "dataset.json"
OUTPUT_DIR = ROOT / "test_outputs"

EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
SIMILARITY_THRESHOLD = 0.75
ROUND_DIGITS = 6

# Semantic-contextual node identity. Named activities must still satisfy
# SIMILARITY_THRESHOLD; context refines the ranking but cannot rescue a
# semantically incompatible task.
NODE_MATCH_INITIAL_SEMANTIC_WEIGHT = 0.90
NODE_MATCH_INITIAL_CONTEXT_WEIGHT = 0.10
NODE_MATCH_BASE_WEIGHT = 0.90
NODE_MATCH_PREDECESSOR_WEIGHT = 0.05
NODE_MATCH_SUCCESSOR_WEIGHT = 0.05
NODE_MATCH_CONTEXT_FALLBACK_THRESHOLD = 0.50
NODE_MATCH_MAX_ITERATIONS = 3

FLOW_NODE_TAGS = {
    "task", "userTask", "serviceTask", "scriptTask", "manualTask",
    "businessRuleTask", "sendTask", "receiveTask", "subProcess",
    "callActivity", "startEvent", "endEvent", "intermediateCatchEvent",
    "intermediateThrowEvent", "boundaryEvent", "exclusiveGateway",
    "parallelGateway", "inclusiveGateway", "eventBasedGateway",
    "complexGateway",
}

TASK_LIKE_TAGS = {
    "task", "userTask", "serviceTask", "scriptTask", "manualTask",
    "businessRuleTask", "sendTask", "receiveTask",
}
GATEWAY_TAGS = {
    "exclusiveGateway", "parallelGateway", "inclusiveGateway",
    "eventBasedGateway", "complexGateway",
}
EVENT_TAGS = {
    "startEvent", "endEvent", "intermediateCatchEvent",
    "intermediateThrowEvent", "boundaryEvent",
}
