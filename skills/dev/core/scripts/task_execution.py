"""Scoped execution semantics. Reader/query changes are not execution inputs."""
import ast
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time
import task_inputs
import task_policy
import task_authorization

VERSION = 2


def protocol(workflow):
    # Actual execution/collection/permission code binds the contract, not a caller's label.
    tree=ast.parse(Path(workflow).read_text())
    definitions={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    constants={}
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name):constants[target.id]=node
    pending=['run_check','check_identity_payload'];selected={}
    while pending:
        name=pending.pop()
        if name in selected:continue
        node=definitions.get(name) or constants.get(name)
        if node is None:continue
        selected[name]=ast.dump(node,include_attributes=False)
        pending.extend(n.id for n in ast.walk(node) if isinstance(n,ast.Name)
                       and (n.id in definitions or n.id in constants) and n.id not in selected)
    return {'version': VERSION, 'implementation': {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__), Path(task_inputs.__file__), Path(task_policy.__file__), Path(task_authorization.__file__))},
        'workflow_execution':hashlib.sha256(json.dumps(selected,sort_keys=True).encode()).hexdigest()}


def producer(workflow):
    return {'workflow_sha256': hashlib.sha256(Path(workflow).read_bytes()).hexdigest(),
            'protocol': protocol(workflow)}


def stop(process):
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def invoke(argv, root, path, budget, timeout, start):
    """Return command outcome, never a claim that nested tests physically executed."""
    status, code, interrupted, reason = 'unavailable', None, None, None
    with path.open('xb') as stream:
        stream.write(('Featrace task ' + start['task'] + ' attempt ' + start['id'] + '\n').encode())
        stream.write(('Featrace start ' + json.dumps(start, sort_keys=True, separators=(',', ':')) + '\n').encode())
        stream.flush()
        process = None
        try:
            process = subprocess.Popen(argv, cwd=root, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic() + timeout
            process.poll()
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    if time.monotonic() > deadline:
                        stop(process)
                        reason = 'EXECUTION_TIMEOUT'
                        break
                    if not selector.select(.05):
                        continue
                    block = os.read(process.stdout.fileno(), 65536)
                    if not block:
                        try:
                            code = process.wait(timeout=max(.01, deadline-time.monotonic()))
                            status = 'passed' if code == 0 else 'failed'
                        except subprocess.TimeoutExpired:
                            stop(process)
                            reason = 'EXECUTION_TIMEOUT'
                        break
                    # Reserve room for a bounded completion footer. Never truncate to a pass.
                    remaining = budget - stream.tell() - 2048
                    stream.write(block[:max(0, remaining)])
                    if len(block) > remaining:
                        stop(process)
                        reason = 'EXECUTION_OUTPUT_LIMIT'
                        break
        except OSError:
            stop(process)
            reason = 'EXECUTION_IO_UNAVAILABLE'
        except BaseException as exc:
            stop(process)
            interrupted, reason = exc, 'EXECUTION_INTERRUPTED'
        finally:
            if process is not None and process.stdout is not None:
                process.stdout.close()
    return status, code, interrupted, reason


def finish(path, budget, result):
    body = ('\nFeatrace result ' + json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n').encode()
    if path.stat().st_size + len(body) > budget:
        raise ValueError('EXECUTION_OUTPUT_LIMIT')
    with path.open('ab') as stream:
        stream.write(body)
