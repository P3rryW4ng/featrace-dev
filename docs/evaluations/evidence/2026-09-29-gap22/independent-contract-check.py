from pathlib import Path
import sys, unittest, copy, decimal
p=Path(sys.argv[1]);sys.path.insert(0,str(p));sys.dont_write_bytecode=True
from src.catalog.query import product_snapshot, receipt_for, all_product_ids
from src.audit.summary import event_snapshot, legacy_summary
class Contract(unittest.TestCase):
 def item(self,**x):
  d={'id':'p1','name':'ABCDEFGHIJK','active':True,'category':'food','price':'001.2'};d.update(x);return d
 def event(self,**x):
  d={'id':'e1','kind':'sale','timestamp':'2024-02-29T12:00:00Z'};d.update(x);return d
 def test_product_exact_output(self):
  self.assertEqual(product_snapshot([self.item()]),{'products':[{'id':'p1','label':'ABCDEFGH','price':'1.20'}],'errors':[]})
 def test_product_empty_name_zero_and_whitespace_id(self):
  self.assertEqual(product_snapshot([self.item(id=' ',name='',price='0')]),{'products':[{'id':' ','label':'','price':'0.00'}],'errors':[]})
 def test_product_unicode_character_limit(self):
  self.assertEqual(product_snapshot([self.item(name='中文测试名称展示abc')])['products'][0]['label'],'中文测试名称展示')
 def test_product_order_duplicates(self):
  x=product_snapshot([self.item(id='b'),self.item(id='a'),self.item(id='b')]);self.assertEqual([a['id'] for a in x['products']],['b','a','b'])
 def test_product_filter_after_validation(self):
  rows=[self.item(active=False),self.item(category='other'),self.item(active=False,price='bad'),self.item(category='other',price='bad'),self.item(id='yes')]
  self.assertEqual(product_snapshot(rows,'food'),{'products':[{'id':'yes','label':'ABCDEFGH','price':'1.20'}],'errors':[{'index':2,'reason':'invalid_price'},{'index':3,'reason':'invalid_price'}]})
 def test_product_validation_order(self):
  rows=[{},self.item(name=None,active=1,category=None,price='bad'),self.item(active=1,category=None,price='bad'),self.item(category=None,price='bad'),self.item(price='bad')]
  self.assertEqual(product_snapshot(rows)['errors'],[{'index':i,'reason':a} for i,a in enumerate(['invalid_id','invalid_name','invalid_active','invalid_category','invalid_price'])])
 def test_product_price_boundaries(self):
  bad=['-1','+1','1e2','NaN','Infinity','1.',' .5','1.234','１２.３','١.٢','1\n','',None,1]
  self.assertEqual(product_snapshot([self.item(price=x) for x in bad])['errors'],[{'index':i,'reason':'invalid_price'} for i in range(len(bad))])
 def test_product_long_price_exact(self):
  v='123456789012345678901234567890.01';self.assertEqual(product_snapshot([self.item(price=v)])['products'][0]['price'],v)
 def test_product_context_unchanged(self):
  with decimal.localcontext() as c:
   c.prec=6;c.flags[decimal.Inexact]=True;before=(c.prec,c.rounding,dict(c.flags),dict(c.traps))
   self.assertEqual(product_snapshot([self.item()])['products'][0]['price'],'1.20')
   self.assertEqual((c.prec,c.rounding,dict(c.flags),dict(c.traps)),before)
 def test_product_empty_category_is_exact_filter(self):
  rows=[self.item(category='food'),self.item(id='empty',category='')]
  self.assertEqual([x['id'] for x in product_snapshot(rows,category='')['products']],['empty'])
 def test_product_missing_fields(self):
  rows=[];names=['id','name','active','category','price']
  for name in names:
   x=self.item();del x[name];rows.append(x)
  self.assertEqual(product_snapshot(rows)['errors'],[{'index':i,'reason':'invalid_'+name} for i,name in enumerate(names)])
 def test_product_no_mutation_or_state(self):
  rows=[self.item(extra={'x':[1]})];before=copy.deepcopy(rows);a=product_snapshot(rows);self.assertEqual(rows,before);a['products'][0]['id']='changed';self.assertEqual(product_snapshot(rows)['products'][0]['id'],'p1')
 def test_product_legacy(self):
  self.assertEqual(receipt_for('123456789012XYZ'),'receipt:123456789012');self.assertEqual(all_product_ids([{'id':'a'},{'id':'a'}]),['a','a'])
 def test_event_empty(self):
  self.assertEqual(event_snapshot([]),{'counts':{},'accepted_ids':[],'errors':[]})
 def test_event_exact_output(self):
  self.assertEqual(event_snapshot([self.event()]),{'counts':{'sale':1},'accepted_ids':['e1'],'errors':[]})
 def test_event_window_inclusive(self):
  a='2024-02-29T12:00:00Z';b='2024-02-29T12:00:02Z';rows=[self.event(id='before',timestamp='2024-02-29T11:59:59Z'),self.event(id='start',timestamp=a),self.event(id='end',timestamp=b),self.event(id='after',timestamp='2024-02-29T12:00:03Z')]
  self.assertEqual(event_snapshot(rows,a,b),{'counts':{'sale':2},'accepted_ids':['start','end'],'errors':[]})
 def test_event_first_eligible_id_wins(self):
  rows=[self.event(id='x',kind='one'),self.event(id='x',kind='two'),self.event(id='y',kind='two'),self.event(id='x',kind='one')]
  self.assertEqual(event_snapshot(rows),{'counts':{'one':1,'two':1},'accepted_ids':['x','y'],'errors':[]})
 def test_event_invalid_and_outside_do_not_reserve(self):
  rows=[self.event(timestamp='bad'),self.event(timestamp='2024-01-01T00:00:00Z'),self.event(),self.event(kind='other')]
  self.assertEqual(event_snapshot(rows,start='2024-02-29T12:00:00Z'),{'counts':{'sale':1},'accepted_ids':['e1'],'errors':[{'index':0,'reason':'invalid_timestamp'}]})
 def test_event_validation_order(self):
  rows=[{},self.event(kind='',timestamp='bad'),self.event(timestamp='bad')]
  self.assertEqual(event_snapshot(rows)['errors'],[{'index':i,'reason':x} for i,x in enumerate(['invalid_id','invalid_kind','invalid_timestamp'])])
 def test_event_timestamp_strict(self):
  vals=['2023-02-29T12:00:00Z','2024-02-29T25:00:00Z','2024-02-29T12:00:00+00:00','2024-02-29T12:00:00Z\n','２０２４-02-29T12:00:00Z','2024-02-29T12:00:00.1Z',None]
  self.assertEqual(event_snapshot([self.event(timestamp=x,id=str(i)) for i,x in enumerate(vals)])['errors'],[{'index':i,'reason':'invalid_timestamp'} for i in range(len(vals))])
 def test_event_one_sided_windows(self):
  rows=[self.event(id='a',timestamp='2024-02-29T11:00:00Z'),self.event(id='b',timestamp='2024-02-29T13:00:00Z')]
  self.assertEqual(event_snapshot(rows,start='2024-02-29T12:00:00Z')['accepted_ids'],['b']);self.assertEqual(event_snapshot(rows,end='2024-02-29T12:00:00Z')['accepted_ids'],['a'])
 def test_event_no_mutation_or_state(self):
  rows=[self.event(extra={'x':[1]})];before=copy.deepcopy(rows);a=event_snapshot(rows);self.assertEqual(rows,before);a['counts']['sale']=99;self.assertEqual(event_snapshot(rows)['counts'],{'sale':1})
 def test_event_legacy(self):
  self.assertEqual(legacy_summary([self.event(),self.event()]),{'total':2})
if __name__=='__main__':
 unittest.main(argv=[sys.argv[0]],verbosity=2)
