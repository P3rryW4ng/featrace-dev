import unittest
from upper import convert
class CatalogTest(unittest.TestCase):
 def test_empty(self): self.assertEqual(convert(''), {'records':[], 'errors':[]})
 def test_header(self): self.assertEqual(convert('wrong\n'), {'records':[], 'errors':[{'line':1,'code':'header'}]})
 def test_prices(self):
  x=convert('sku,name,price\na,A,1\nb,B,2.50\n')
  self.assertEqual(x,{'records':[{'sku':'a','name':'A','price':'1.00'},{'sku':'b','name':'B','price':'2.50'}],'errors':[]})
 def test_quoted_multiline_bom(self):
  x=convert('\ufeffsku,name,price\na,"A, B\nC",0\n')
  self.assertEqual(x['records'][0],{'sku':'a','name':'A, B\nC','price':'0.00'})
 def test_duplicate_and_invalid_does_not_reserve(self):
  x=convert('sku,name,price\na,A,bad\na,A,1\na,B,2\n')
  self.assertEqual(x['errors'],[{'line':2,'code':'invalid_price'},{'line':4,'code':'duplicate_sku'}]);self.assertEqual(len(x['records']),1)
 def test_invalid_prices(self):
  for v in ['NaN','Infinity','-1','0.001','oops']:
   with self.subTest(v=v):self.assertEqual(convert('sku,name,price\na,A,'+v)['errors'],[{'line':2,'code':'invalid_price'}])
 def test_missing_extra_and_trim(self):
  x=convert('sku,name,price\n,A,1\na,,1\na,A,1,extra\n b , B , 1.20 \n')
  self.assertEqual(len(x['errors']),3);self.assertEqual(x['records'],[{'sku':'b','name':'B','price':'1.20'}])
