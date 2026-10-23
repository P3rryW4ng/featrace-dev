"""Use actual pinned 0.24.0 CLI bytes in an isolated synthetic task."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import subprocess
import sys
import argparse

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo',type=Path,default=Path.cwd())
REPO=parser.parse_args().repo.resolve()
sys.path.insert(0,str(REPO/'tests'))
from test_task_workflow import TaskWorkflowTests, w


def old_bytes(name):
    return subprocess.check_output(['git','-C',str(REPO),'show','v0.24.0:'+name])


def run():
    commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','v0.24.0^{commit}']).decode().strip()
    assert commit==w.CORRECTION_PREDECESSOR['source_commit']
    manifest=json.loads(old_bytes('release.json'))
    fixture=TaskWorkflowTests();fixture.setUp()
    try:
        with TemporaryDirectory(prefix='featrace-pinned-predecessor-') as temporary:
            folder=Path(temporary)
            for name in ('task_workflow.py','task_inputs.py','task_policy.py'):
                data=old_bytes('skills/dev/core/scripts/'+name)
                assert hashlib.sha256(data).hexdigest()==manifest['files']['core/scripts/'+name]
                assert hashlib.sha256(data).hexdigest()==w.CORRECTION_PREDECESSOR['runner'][name]
                (folder/name).write_bytes(data)
            def old_cli(*args):
                return subprocess.run([sys.executable,'-B',str(folder/'task_workflow.py'),*args],capture_output=True,text=True)
            for args in [('run',str(fixture.root),fixture.ident,'--check','target'),
                         ('assess',str(fixture.root),fixture.ident,'--criterion','C1','--verdict','supported','--reason','Actual synthetic label assertion'),
                         ('close',str(fixture.root),fixture.ident)]:
                result=old_cli(*args);assert result.returncode==0,result.stdout+result.stderr
            original=fixture.doc();execution=original['executions']['target'].copy()
            w.correct(fixture.root,fixture.ident,['C1'],'Correct the fixture attribution','Synthetic user authority')
            unsupported=old_cli('status',str(fixture.root),fixture.ident)
            assert unsupported.returncode==2
            assert json.loads(unsupported.stdout)['reason']=='TASK_CONTRACT_UNSUPPORTED'
            reused=w.run_check(fixture.root,fixture.ident,'target')
            assert reused['reused'] and reused['identity_profile']=='v0.24.0'
            assert fixture.doc()['executions']['target']==execution
            assert (fixture.root/'run-count').read_text()=='1'
            w.assess(fixture.root,fixture.ident,'C1','supported','Same original assertion, corrected interpretation')
            receipt=w.close(fixture.root,fixture.ident,[])
            assert receipt['corrects_receipt']==w.digest(original['receipt'])
            assert fixture.doc()['corrections'][0]['prior_receipt']==original['receipt']
            return {'predecessor':'v0.24.0','pinned_bytes_match':True,'old_reader_refuses_corrected_record':True,
                    'physical_execution_count':1,'same_execution_id':reused['execution']==execution['id'],
                    'original_execution_fields_unchanged':True,'original_receipt_preserved':True,
                    'corrected_receipt_links_original':True,'business_operations':False}
    finally:fixture.doCleanups()


if __name__=='__main__':
    data=run();(HERE/'legacy-probe.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data))
