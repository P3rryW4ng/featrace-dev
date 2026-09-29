import unittest,json,builtins,io,socket,subprocess
from unittest.mock import patch
from upper import convert as catalog
from lower import convert as events
class ContractTest(unittest.TestCase):
 def test_csv_logical_lines_after_multiline(self):
  x=catalog('sku,name,price\na,"A\nB",1\nb,B,wrong\nc,C,2\na,A,3\n')
  self.assertEqual(x,{'records':[{'sku':'a','name':'A\nB','price':'1.00'},{'sku':'c','name':'C','price':'2.00'}],'errors':[{'line':3,'code':'invalid_price'},{'line':5,'code':'duplicate_sku'}]})
 def test_csv_row_errors_exact_and_atomic(self):
  self.assertEqual(catalog('sku,name,price\n,A,1\na,,1\na,A\na,A,1,extra\na,A,1\n'),{'records':[{'sku':'a','name':'A','price':'1.00'}],'errors':[{'line':2,'code':'invalid_row'},{'line':3,'code':'invalid_row'},{'line':4,'code':'invalid_row'},{'line':5,'code':'invalid_row'}]})
 def test_csv_header_trim_and_stop(self):
  self.assertEqual(catalog(' sku , name , price \na,A,1')['errors'],[])
  self.assertEqual(catalog('wrong\na,A,1\nb,B,2'),{'records':[],'errors':[{'line':1,'code':'header'}]})
 def test_csv_finite_decimal_formats(self):
  for value,expected in [('0','0.00'),('-0','0.00'),('1.2','1.20'),(' 2.50 ','2.50')]:
   with self.subTest(value=value):self.assertEqual(catalog('sku,name,price\na,A,'+value)['records'][0]['price'],expected)
  for value in ['-Infinity','sNaN','0.000']:
   with self.subTest(value=value):self.assertEqual(catalog('sku,name,price\na,A,'+value)['errors'],[{'line':2,'code':'invalid_price'}])
 def test_json_schema_fields_individually(self):
  good={'id':'a','timestamp':'2026-01-01T00:00:00Z','payload':None}
  bad=[dict(good) for _ in range(7)]
  del bad[0]['payload'];del bad[1]['id'];del bad[2]['timestamp'];bad[3]['id']=0;bad[4]['id']='';bad[5]['timestamp']=0;bad[6]['timestamp']=''
  for obj in bad+[None,[],1,'text',True]:
   with self.subTest(obj=obj):self.assertEqual(events(json.dumps(obj)),{'records':[],'errors':[{'line':1,'code':'invalid_event'}]})
 def test_json_z_negative_offsets_and_calendar(self):
  for value in ['2026-01-01T00:00:00Z','2025-12-31T22:00:00-02:00','2026-01-01T02:00:00+02:00']:
   with self.subTest(value=value):self.assertEqual(events(json.dumps({'id':'a','timestamp':value,'payload':0}))['records'][0]['timestamp'],'2026-01-01T00:00:00Z')
  for value in ['2026-02-30T00:00:00Z','2026-01-01T00:00:00+24:00','2026-01-01T00:00:00+00:60']:
   with self.subTest(value=value):self.assertEqual(events(json.dumps({'id':'a','timestamp':value,'payload':0}))['errors'],[{'line':1,'code':'invalid_timestamp'}])
 def test_json_payload_types_and_physical_order(self):
  payloads=[None,0,'text',[],{},True]
  text='\n'.join(json.dumps({'id':str(i),'timestamp':'2026-01-01T00:00:00Z','payload':v}) for i,v in enumerate(payloads))
  self.assertEqual([x['payload'] for x in events(text)['records']],payloads)
  self.assertEqual(events(' \nnull\n\nnope')['errors'],[{'line':2,'code':'invalid_event'},{'line':4,'code':'invalid_json'}])
 def test_both_directions_no_shared_mutable_results(self):
  c='sku,name,price\nx,X,1';e='{"id":"x","timestamp":"2026-01-01T00:00:00Z","payload":null}'
  a=events(e);catalog(c);self.assertEqual(events(e),a)
  a=catalog(c);events(e);self.assertEqual(catalog(c),a)
  a['records'].clear();self.assertEqual(len(catalog(c)['records']),1)
  a=events(e);a['records'].clear();self.assertEqual(len(events(e)['records']),1)
 def test_no_external_io_on_representative_paths(self):
  def forbidden(*args,**kwargs):raise AssertionError('unexpected external I/O')
  with patch.object(builtins,'open',forbidden),patch.object(io,'open',forbidden),patch.object(socket,'socket',forbidden),patch.object(subprocess,'Popen',forbidden):
   self.assertEqual(len(catalog('sku,name,price\na,A,1')['records']),1)
   self.assertEqual(len(events('{"id":"a","timestamp":"2026-01-01T00:00:00Z","payload":null}')['records']),1)
   self.assertEqual(catalog('sku,name,price\na,A,bad')['errors'][0]['code'],'invalid_price')
   self.assertEqual(events('bad')['errors'][0]['code'],'invalid_json')
