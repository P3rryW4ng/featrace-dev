"""Independent, read-only probe for the synthetic CSV contract's large finite price."""
import importlib.util
import json
from pathlib import Path
import sys


def run(source):
    spec = importlib.util.spec_from_file_location('csv_probe_subject', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected = {
        'records': [{'sku': 'a', 'name': 'A', 'price': '10000000000000000000000000000.00'}],
        'errors': [],
    }
    try:
        actual = module.convert('sku,name,price\na,A,1e28\n')
        return {'status': 'passed' if actual == expected else 'wrong_result',
                'actual': actual, 'expected': expected}
    except Exception as exc:
        return {'status': 'exception', 'exception_type': type(exc).__name__,
                'expected': expected}


if __name__ == '__main__':
    results = {name: run(Path(path) / 'upper.py')
               for name, path in zip(('serial', 'parallel_candidate'), sys.argv[1:])}
    print(json.dumps(results, indent=2))
