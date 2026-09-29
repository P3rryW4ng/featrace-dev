"""Agent technical probe: observe runtime effects of upper/lower convert() in-process.

Read-only against the project; run with cwd = project root.
"""
import copy, decimal, io, json, os, sys, threading, warnings, contextlib

sys.dont_write_bytecode = True
sys.path.insert(0, os.getcwd())
import upper, lower  # noqa: E402

mods = {m: getattr(sys.modules.get(m), '__file__', 'builtin') for m in
        ['csv', '_csv', 'io', 'decimal', '_decimal', 'json', 'json.decoder', '_json', 're', 'datetime']}
H = 'sku,name,price\n'
csv_inputs = ['', '﻿', 'wrong\n', H, H + 'a,A,1\nb,B,2.50\n', '﻿sku,name,price\na,"A, B\nC",0\n',
              H + ',A,1\na,,1\na,A\na,A,1,extra\na,A,1\n', H + 'a,A,bad\na,A,NaN\na,A,sNaN\na,A,-1\na,A,0.001\na,A,1\na,B,2\n',
              H + 'a,"A\nB",1\nb,B,wrong\nc,C,2\na,A,3\n', ' sku , name , price \n b , B , 1.20 \n', H + '\n\n', H + 'a,"A,1']
jsonl_inputs = ['', ' \n', '\nnope\n[]', 'null\n1\n"x"\ntrue',
                '\n'.join(json.dumps({'id': str(i), 'timestamp': t, 'payload': p}) for i, (t, p) in enumerate(
                    [('2026-01-01T00:00:00Z', None), ('2025-12-31T22:00:00-02:00', 0), ('2026-01-01T02:00:00+02:00', {}),
                     ('2026-02-30T00:00:00Z', []), ('2026-01-01T00:00:00', 'x'), ('bad', True),
                     ('2026-01-01T00:00:00+24:00', 1), ('0001-01-01T00:30:00+01:00', 2)])),
                '{"id":"a","timestamp":"x"}\n{"id":1,"timestamp":"2026-01-01T00:00:00Z","payload":1}\n'
                '{"id":"a","timestamp":"2026-01-01T00:00:00Z","payload":1}\n{"id":"a","timestamp":"2026-01-01T00:00:00Z","payload":2}']

snap_before = (copy.deepcopy(upper._HEADER), lower._TIMESTAMP.pattern, sorted(vars(upper)), sorted(vars(lower)))
ctx_before = repr(decimal.getcontext())
cwd_before = sorted(os.listdir('.'))
events = []
active = [False]


def hook(name, args):
    if active[0] and threading.current_thread() is threading.main_thread():
        events.append(name)


sys.addaudithook(hook)
out, err = io.StringIO(), io.StringIO()
results = []
with warnings.catch_warnings():
    warnings.simplefilter('error')
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        active[0] = True
        for _ in range(2):  # interleave both importers twice
            for c, j in zip(csv_inputs, jsonl_inputs + jsonl_inputs):
                results.append((upper.convert(c), lower.convert(j)))
        active[0] = False

# independence of repeated results and aliasing
active[0] = True
r1 = upper.convert(csv_inputs[4]); r1['records'].clear(); r2 = upper.convert(csv_inputs[4])
e1 = lower.convert(jsonl_inputs[4]); e1['records'][0]['payload'] = 'mutated'; e2 = lower.convert(jsonl_inputs[4])
active[0] = False
half = len(results) // 2
# alter ambient decimal context and confirm identical CSV output
with decimal.localcontext() as ctx:
    ctx.prec = 1; ctx.rounding = decimal.ROUND_UP; ctx.traps[decimal.InvalidOperation] = False
    alt = [upper.convert(c) for c in csv_inputs]

report = {
    'python': sys.version.split()[0], 'executable': sys.executable, 'resolved_modules': mods,
    'audit_events_during_convert': sorted(set(events)), 'audit_event_count': len(events),
    'stdout': out.getvalue(), 'stderr': err.getvalue(),
    'module_state_unchanged': snap_before == (upper._HEADER, lower._TIMESTAMP.pattern, sorted(vars(upper)), sorted(vars(lower))),
    'decimal_context_unchanged': ctx_before == repr(decimal.getcontext()),
    'cwd_listing_unchanged': cwd_before == sorted(os.listdir('.')),
    'repeat_pass_identical': results[:half] == results[half:],
    'csv_result_not_aliased': len(r2['records']) == 2,
    'jsonl_result_not_aliased': e2['records'][0]['payload'] is None,
    'csv_independent_of_decimal_context': alt == [r[0] for r in results[:len(csv_inputs)]],
    'upper_imports_lower': 'lower' in vars(upper), 'lower_imports_upper': 'upper' in vars(lower),
    'upper_globals': sorted(k for k in vars(upper) if not k.startswith('__')),
    'lower_globals': sorted(k for k in vars(lower) if not k.startswith('__')),
}
print(json.dumps(report, indent=1))
