import sys,unittest,argparse,os
sys.path.insert(0,os.getcwd())
p=argparse.ArgumentParser();p.add_argument('--task',required=True);a=p.parse_args()
pattern={'T-UP':'test_upper.py','T-LOW':'test_lower.py'}[a.task]
suite=unittest.defaultTestLoader.discover('tests',pattern=pattern)
if a.task=='T-UP':
 class SyntheticTransportProbe(unittest.TestCase):
  def runTest(self):
   self.fail('ISOLATION_INJECTED_FAILURE: simulated check dependency unavailable; fixture-only fault')
 suite.addTest(SyntheticTransportProbe())
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
