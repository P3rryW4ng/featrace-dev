import json
from pathlib import Path
import sys

CORE = Path(__file__).resolve().parents[1] / 'skills/dev/core/scripts'
sys.path.insert(0, str(CORE))
from prd_intake import review_digest


def attach_intake(folder, req):
    """Synthetic reviewed evidence for deterministic tests, not an Agent evaluation."""
    req['requirements'][0]['source_item_ids'] = ['S-1']
    source = 'sources/prd-original.txt'
    target = req['requirements'][0]['statement']
    doc = {'version': 1, 'feature_id': 'FEAT-001', 'inventory_complete': True,
           'units': [{'id': 'U-1', 'source': source, 'locator': 'line 1', 'kind': 'text', 'status': 'read'}],
           'items': [{'id': 'S-1', 'unit_id': 'U-1', 'quote': (folder / source).read_text(),
                      'context': 'Entire local computation specification', 'related_ids': [],
                      'kind': 'rule', 'disposition': 'mapped',
                      'aspects': [{'kind': 'behavior', 'text': 'Convert a local string to uppercase',
                                   'requirement_id': 'R-1', 'field': 'statement', 'target_text': target, 'review': 'verified'}]}],
           'review': {'reviewer': 'synthetic-test-fixture', 'notes': 'Hand-authored expectation; not a model evaluation'}}
    doc['review']['digest'] = review_digest(folder, doc, req)
    (folder / 'spec/requirements.json').write_text(json.dumps(req))
    (folder / 'spec/prd-intake.json').write_text(json.dumps(doc))
    return doc
