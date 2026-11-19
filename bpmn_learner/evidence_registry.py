"""Build a complete registry of Validator and Similarity Evaluator outputs.

The registry does not classify failures and does not call an LLM. It only
discovers available evidence files, describes them, and links them to the
failure types (T1--T7) for which they may be useful.

Run this file independently:

    python evidence_registry.py \
        --id 24 \
        --generator openai:gpt-6-luna \
        --validator-dir inputs/validator/id_24 \
        --similarity-dir inputs/similarity/id_24 \
        --output-dir outputs/id_24
"""

from __future__ import annotations

import argparse
import hashlib
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


TEXT_EXTENSIONS = {".json", ".csv", ".txt", ".xml", ".bpmn", ".graphml"}
HUMAN_ONLY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}


@dataclass(frozen=True)
class EvidenceFile:
    """Metadata describing one evidence file without loading all its content."""

    evidence_file_id: str
    example_id: str
    generator: str
    source_component: str
    relative_path: str
    file_name: str
    extension: str
    size_bytes: int
    category: str
    failure_types: list[str]
    description: str
    agent_readable: bool
    human_audit_useful: bool
    stable_file_key: str
    content_sha256: str


# Ordered rules: the first matching rule supplies the main category and
# description. Failure types are deliberately broad here: the registry says
# where relevant evidence can be found; it does not claim that a failure exists.
SIMILARITY_RULES: list[tuple[tuple[str, ...], str, list[str], str]] = [
    (("comparison_evidence", "node_matching", "alignment_review", "alignment_before_agent"), "comparison_assessment", ["T5", "T6", "T7"],
     "Retrievable comparison evidence, stable record identities, candidate policies and uncertainty. Not proof of a generation error."),
    (("type_", "type-"), "type_comparison", ["T5"],
     "BPMN element-type counts and TP/FP/FN comparison."),
    (("ged",), "graph_edit_distance", ["T5"],
     "GED inputs, edit operations, search progress, or normalized GED result."),
    (("structural_node_alignment",), "node_alignment", ["T5", "T6"],
     "Gold-to-generated node alignment and its structural context."),
    (("node_mapping",), "node_alignment", ["T5", "T6"],
     "Accepted node mapping used to compare workflow connections."),
    (("nodes_semantic", "node_semantic"), "node_semantics", ["T6"],
     "Node semantic inputs, cosine scores, assignments, or unmatched elements."),
    (("semantic",), "semantic_similarity", ["T6", "T7"],
     "Semantic similarity evidence for BPMN or collaboration elements."),
    (("connection",), "workflow_connections", ["T5"],
     "Correct, missing, additional, reversed, or summarized sequence-flow relations."),
    (("order",), "workflow_order", ["T5"],
     "Directed reachability and workflow-order comparison by execution scope."),
    (("collaboration",), "collaboration", ["T4", "T7"],
     "Pools, lanes, memberships, message flows, or collaboration comparison."),
    (("pool", "lane", "message_flow", "messageflow"), "collaboration", ["T4", "T7"],
     "Extracted pool, lane, membership, or message-flow evidence."),
    (("graph_loader", "process_nodes", "sequence_flows", "adjacency", "graph_summary"),
     "extracted_graph", ["T2", "T3", "T5"],
     "Extracted graph nodes, directed sequence flows, scopes, or adjacency data."),
    (("subprocess", "processes"), "execution_scopes", ["T3", "T5"],
     "Process/subprocess scopes and node memberships."),
    (("input", "example", "configuration"), "run_input", ["T1", "T2", "T3", "T4", "T5", "T6", "T7"],
     "Input BPMN, example metadata, or evaluation configuration."),
    (("all_metrics",), "metric_summary", ["T5", "T6", "T7"],
     "Consolidated similarity metrics used by the deterministic classifier."),
    (("failure_classifier_signal",), "classifier_signal_map", ["T5", "T6", "T7"],
     "Mapping between evaluator metrics and downstream failure types."),
    (("function_io_manifest", "output_file_inventory"), "audit_manifest", [],
     "Inventory describing functions, inputs, and generated outputs."),
]

VALIDATOR_RULES: list[tuple[tuple[str, ...], str, list[str], str]] = [
    (("l1", "xml", "parse", "syntax"), "validator_l1", ["T1"],
     "XML syntax, parsing, namespace, or BPMN document evidence."),
    (("l2", "gateway"), "validator_l2", ["T2"],
     "Gateway split/join and gateway-type validation evidence."),
    (("l3", "flow", "connection"), "validator_l3", ["T3"],
     "Sequence-flow endpoint, connectivity, and control-flow validation evidence."),
    (("l4", "pool", "lane", "message", "collaboration"), "validator_l4", ["T4"],
     "Pool, lane, participant, and message-flow validation evidence."),
    (("combined", "summary", "result"), "validator_summary", ["T1", "T2", "T3", "T4"],
     "Consolidated L1--L4 validation result."),
]


def _matches(file_name: str, keywords: tuple[str, ...]) -> bool:
    """Return True when at least one keyword occurs in the lower-case name."""

    return any(keyword in file_name for keyword in keywords)


def classify_file(file_path: Path, source_component: str) -> tuple[str, list[str], str]:
    """Infer an evidence category from a file name.

    This operation never decides whether T1--T7 is detected. It only links a
    file to the failure families for which it may provide useful evidence.
    """

    name = file_path.name.lower()
    rules = VALIDATOR_RULES if source_component == "validator" else SIMILARITY_RULES

    # Specific rules should win over generic ones. For example,
    # collaboration_semantic belongs to T7, not to the generic T6 family.
    if source_component == "similarity_evaluator" and "collaboration" in name:
        return (
            "collaboration",
            ["T4", "T7"],
            "Pool, lane, membership, message-flow, or collaboration evidence.",
        )

    for keywords, category, failure_types, description in rules:
        if _matches(name, keywords):
            return category, failure_types, description

    default_failures = ["T1", "T2", "T3", "T4"] if source_component == "validator" else ["T5", "T6", "T7"]
    return (
        "uncategorized",
        default_failures,
        "Uncategorized output retained in the registry so that no evidence is lost.",
    )


def discover_files(root: Path) -> Iterable[Path]:
    """Yield all regular files under root in a deterministic order."""

    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


REPO_ROOT = Path(__file__).resolve().parents[1]


def portable_path(path: Path) -> str:
    """A directory as recorded in the registry: relative to the repository when inside it."""
    try:
        return Path(path).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def build_registry(
    example_id: str,
    generator: str,
    validator_dir: Path,
    similarity_dir: Path,
) -> dict:
    """Create the complete evidence registry for one evaluated BPMN example."""

    validator_dir = validator_dir.resolve()
    similarity_dir = similarity_dir.resolve()
    records: list[EvidenceFile] = []
    source_roots = (
        ("validator", validator_dir),
        ("similarity_evaluator", similarity_dir),
    )

    counter = 1
    for component, root in source_roots:
        for file_path in discover_files(root):
            category, failure_types, description = classify_file(file_path, component)
            extension = file_path.suffix.lower()
            try:
                relative_path = str(file_path.relative_to(root))
            except ValueError:
                relative_path = str(file_path)

            records.append(
                EvidenceFile(
                    evidence_file_id=f"FILE_{counter:04d}",
                    example_id=str(example_id),
                    generator=generator,
                    source_component=component,
                    relative_path=relative_path,
                    file_name=file_path.name,
                    extension=extension or "[no extension]",
                    size_bytes=file_path.stat().st_size,
                    category=category,
                    failure_types=failure_types,
                    description=description,
                    agent_readable=extension in TEXT_EXTENSIONS,
                    human_audit_useful=(extension in TEXT_EXTENSIONS or extension in HUMAN_ONLY_EXTENSIONS),
                    stable_file_key="FILE_" + hashlib.sha256(
                        (component + ":" + relative_path.replace("\\", "/")).encode()).hexdigest()[:20],
                    content_sha256=hashlib.sha256(file_path.read_bytes()).hexdigest(),
                )
            )
            counter += 1

    by_failure_type = {
        failure_type: [record.evidence_file_id for record in records if failure_type in record.failure_types]
        for failure_type in ("T1", "T2", "T3", "T4", "T5", "T6", "T7")
    }

    return {
        "registry_version": "1.1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "example_id": str(example_id),
        "generator": generator,
        "source_directories": {
            "validator": portable_path(validator_dir),
            "similarity_evaluator": portable_path(similarity_dir),
        },
        "file_count": len(records),
        "agent_readable_file_count": sum(record.agent_readable for record in records),
        "missing_source_directories": [
            component for component, root in source_roots if not root.exists()
        ],
        "by_failure_type": by_failure_type,
        "files": [asdict(record) for record in records],
    }


def save_registry(registry: dict, output_dir: Path) -> tuple[Path, Path]:
    """Save the same registry as JSON for tools and CSV for human review."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "10_evidence_file_registry.json"
    csv_path = output_dir / "10_evidence_file_registry.csv"

    json_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = [
        "evidence_file_id",
        "example_id",
        "generator",
        "source_component",
        "relative_path",
        "file_name",
        "extension",
        "size_bytes",
        "category",
        "failure_types",
        "agent_readable",
        "human_audit_useful",
        "description",
        "stable_file_key",
        "content_sha256",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in registry["files"]:
            row = dict(record)
            row["failure_types"] = ",".join(row["failure_types"])
            writer.writerow(row)

    return json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", default="24", help="Dataset example ID.")
    parser.add_argument("--generator", default="openai:gpt-6-luna", help="BPMN generator name.")
    parser.add_argument(
        "--validator-dir",
        type=Path,
        default=Path("inputs/validator/id_24"),
        help="Directory containing Validator outputs for this example.",
    )
    parser.add_argument(
        "--similarity-dir",
        type=Path,
        default=Path("inputs/similarity/id_24"),
        help="Directory containing Similarity Evaluator outputs for this example.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/id_24"),
        help="Directory where the JSON and CSV registries will be written.",
    )
    args = parser.parse_args()

    registry = build_registry(
        example_id=args.id,
        generator=args.generator,
        validator_dir=args.validator_dir,
        similarity_dir=args.similarity_dir,
    )
    json_path, csv_path = save_registry(registry, args.output_dir)

    print("=== EVIDENCE FILE REGISTRY ===")
    print(f"Example ID: {registry['example_id']}")
    print(f"Generator: {registry['generator']}")
    print(f"Registered files: {registry['file_count']}")
    print(f"Agent-readable files: {registry['agent_readable_file_count']}")
    if registry["missing_source_directories"]:
        print("Missing directories: " + ", ".join(registry["missing_source_directories"]))
    for failure_type, file_ids in registry["by_failure_type"].items():
        print(f"{failure_type}: {len(file_ids)} potentially relevant files")
    print(f"JSON: {json_path}")
    print(f"CSV:  {csv_path}")


if __name__ == "__main__":
    main()
