"""Create display geometry while retaining the original business model."""
from __future__ import annotations
from functools import lru_cache
import io
import re
import xml.etree.ElementTree as ET

try:
    from .flow_layout import MODEL, DI, DC, DD, ARTIFACTS, NODES, add_flow_diagrams, local
except ImportError:
    from flow_layout import MODEL, DI, DC, DD, ARTIFACTS, NODES, add_flow_diagrams, local


@lru_cache(maxsize=24)
def prepare_display_xml(original: str, *, reorganize: bool = False) -> tuple[str, list[str]]:
    """Arrange a display copy by control flow; keep existing DI unless requested."""
    root = ET.fromstring(original)
    if root.tag != f"{{{MODEL}}}definitions":
        raise ValueError("Expected BPMN definitions in the BPMN 2.0 model namespace")
    has_diagram = root.find(f"{{{DI}}}BPMNDiagram") is not None
    if has_diagram and not reorganize:
        return original, []
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate element IDs prevent a reliable diagram; inspect the original XML")
    used_ids = set(ids)
    counters = {}

    def fresh(prefix):
        count = counters.get(prefix, 0) + 1
        while f"{prefix}_{count}" in used_ids:
            count += 1
        counters[prefix] = count
        value = f"{prefix}_{count}"
        used_ids.add(value)
        return value

    # Reorganizing replaces display geometry, never semantic nodes or flows.
    for element in list(root):
        if element.tag == f"{{{DI}}}BPMNDiagram":
            root.remove(element)
    warnings = ["Flow-aware layout applied to a display copy. Evaluation uses the original XML."]
    warnings.extend(add_flow_diagrams(root, fresh))
    for element in root.iter():
        if local(element) in {"group", "dataInputAssociation", "dataOutputAssociation"}:
            warnings.append(f"Display layout does not include {local(element)} {element.get('id', '')}; inspect the original XML")
    for prefix, uri in [("bpmn", MODEL), ("bpmndi", DI), ("dc", DC), ("di", DD)]:
        ET.register_namespace(prefix, uri)
    rendered = ET.tostring(root, encoding="unicode")
    namespaces = dict(value for _, value in ET.iterparse(io.StringIO(original), events=("start-ns",)))
    for prefix, uri in namespaces.items():
        if prefix and f'xmlns:{prefix}=' not in rendered and re.search(r'="' + re.escape(prefix) + r':', rendered):
            root.set(f"xmlns:{prefix}", uri)
    return ET.tostring(root, encoding="unicode"), warnings
