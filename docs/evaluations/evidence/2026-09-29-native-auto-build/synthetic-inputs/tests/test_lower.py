import unittest,json
from lower import convert
class EventTest(unittest.TestCase):
 def test_empty(self):self.assertEqual(convert(' \n'),{'records':[],'errors':[]})
 def test_offsets(self):
  x=convert(json.dumps({'id':'a','timestamp':'2026-01-01T02:00:00+02:00','payload':{'x':1}}))
  self.assertEqual(x,{'records':[{'id':'a','timestamp':'2026-01-01T00:00:00Z','payload':{'x':1}}],'errors':[]})
 def test_bad_json_and_line_numbers(self):
  self.assertEqual(convert('\nnope\n[]')['errors'],[{'line':2,'code':'invalid_json'},{'line':3,'code':'invalid_event'}])
 def test_invalid_schema(self):
  for obj in [{'id':'a'}, {'id':1,'timestamp':'x','payload':None},{'id':'','timestamp':'x','payload':None}]:
   with self.subTest(obj=obj):self.assertEqual(convert(json.dumps(obj))['errors'][0]['code'],'invalid_event')
 def test_bad_timestamps(self):
  for t in ['bad','2026-01-01T00:00:00']:
   with self.subTest(t=t):self.assertEqual(convert(json.dumps({'id':'a','timestamp':t,'payload':None}))['errors'][0]['code'],'invalid_timestamp')
 def test_duplicate_and_invalid_does_not_reserve(self):
  lines=[{'id':'a','timestamp':'bad','payload':0},{'id':'a','timestamp':'2026-01-01T00:00:00Z','payload':1},{'id':'a','timestamp':'2026-01-01T00:00:00Z','payload':2}]
  x=convert('\n'.join(map(json.dumps,lines)))
  self.assertEqual(x['errors'],[{'line':1,'code':'invalid_timestamp'},{'line':3,'code':'duplicate_id'}]);self.assertEqual(x['records'][0]['payload'],1)
 def test_order(self):
  x=convert('\n'.join(json.dumps({'id':i,'timestamp':'2026-01-01T00:00:00Z','payload':None}) for i in ['b','a']))
  self.assertEqual([v['id'] for v in x['records']],['b','a'])
