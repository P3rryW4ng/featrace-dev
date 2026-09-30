import unittest,sys,json
from pathlib import Path
project=Path(sys.argv.pop(1));phase=sys.argv.pop(1);sys.path.insert(0,str(project))
from src.storeflow.storefront import preview
from src.storeflow.pricing import calculate_total
from src.storeflow.legacy_export import export_subtotal
from src.storeflow.inventory import Inventory
from src.storeflow.payments import Ledger,PaymentDeclined
from src.storeflow.checkout import Checkout
from src.storeflow.receipts import Receipt,export_receipt
from src.storeflow.catalog import PRICES
RATE,CAP=(10,2000) if phase=='v1' else (15,1200)

def expected(total):return total-min(total*RATE//100,CAP)
class PreviewContract(unittest.TestCase):
 def test_default_and_legacy_unchanged(self):
  lines=[('bag',2)]
  self.assertEqual(preview(lines),{'subtotal_cents':30000,'discount_cents':0,'total_cents':30000})
  self.assertEqual(calculate_total(lines),30000);self.assertEqual(export_subtotal(lines),{'gross_cents':30000})
 def test_member_uncapped(self):
  self.assertEqual(preview([('book',1)],member=True),{'subtotal_cents':5000,'discount_cents':5000-expected(5000),'total_cents':expected(5000)})
 def test_member_capped(self):
  self.assertEqual(preview([('bag',2)],member=True)['total_cents'],30000-CAP)
 def test_revision_discriminator(self):
  self.assertEqual(preview([('book',2)],member=True)['total_cents'],expected(10000))
 def test_empty(self):
  self.assertEqual(preview([],member=True),{'subtotal_cents':0,'discount_cents':0,'total_cents':0})
 def test_floor_cents(self):
  from unittest.mock import patch
  with patch.dict(PRICES,{'odd':333}):self.assertEqual(preview([('odd',1)],member=True)['total_cents'],expected(333))
 def test_invalid_preserved(self):
  for lines in [[('unknown',1)],[('book',0)],[('book',True)]]:
   with self.assertRaises(ValueError):preview(lines,member=True)
 def test_duplicate_lines_and_no_input_mutation(self):
  lines=[('pen',1),('pen',2)];self.assertEqual(preview(lines,member=True)['total_cents'],expected(1500));self.assertEqual(lines,[('pen',1),('pen',2)])
class CheckoutContract(unittest.TestCase):
 def setUp(self):
  self.inv=Inventory({'book':3,'pen':4,'bag':2});self.ledger=Ledger();self.shop=Checkout(self.inv,self.ledger)
 def snapshot(self):return dict(self.inv.stock),dict(self.ledger.charges),dict(self.shop.receipts),self.ledger.charge_count
 def test_member_charge_and_receipt(self):
  r=self.shop.place_order('one',[('book',2)],member=True)
  self.assertEqual(r.paid_cents,expected(10000));self.assertEqual(export_receipt(r),{'receipt_id':'one','amount_cents':expected(10000)});self.assertEqual(self.inv.stock['book'],1)
 def test_default_charge(self):
  self.assertEqual(self.shop.place_order('default',[('book',1)]).paid_cents,5000)
 def test_repeat_different_basket(self):
  r=self.shop.place_order('dup',[('book',1)],member=True);old=self.snapshot()
  self.assertIs(self.shop.place_order('dup',[('bag',99)],member=False),r);self.assertEqual(self.snapshot(),old)
 def test_repeat_invalid_input(self):
  r=self.shop.place_order('dup',[('book',1)],member=True);old=self.snapshot()
  self.assertIs(self.shop.place_order('dup',[('nope',-1)],member=False),r);self.assertEqual(self.snapshot(),old)
 def test_preserve_old_receipt(self):
  r=Receipt('historical',7777);self.shop.receipts['historical']=r;old=self.snapshot()
  self.assertIs(self.shop.place_order('historical',[],member=True),r);self.assertEqual(self.snapshot(),old);self.assertEqual(export_receipt(r)['amount_cents'],7777)
 def test_insufficient_later_line_atomic(self):
  old=self.snapshot()
  with self.assertRaises(ValueError):self.shop.place_order('stock',[('book',1),('pen',99)],member=True)
  self.assertEqual(self.snapshot(),old)
 def test_duplicate_sku_atomic(self):
  old=self.snapshot()
  with self.assertRaises(ValueError):self.shop.place_order('stock',[('book',2),('book',2)],member=True)
  self.assertEqual(self.snapshot(),old)
 def test_decline_rolls_back(self):
  old=self.snapshot();self.ledger.decline_next=True
  with self.assertRaises(PaymentDeclined):self.shop.place_order('declined',[('book',1)],member=True)
  self.assertEqual(self.snapshot(),old)
 def test_decline_then_retry_once(self):
  self.ledger.decline_next=True
  with self.assertRaises(PaymentDeclined):self.shop.place_order('retry',[('book',1)],member=True)
  r=self.shop.place_order('retry',[('book',1)],member=True)
  self.assertEqual(self.inv.stock['book'],2);self.assertEqual(self.ledger.charge_count,1);self.assertEqual(r.paid_cents,expected(5000))
  self.assertIs(self.shop.place_order('retry',[('book',1)],member=False),r);self.assertEqual(self.inv.stock['book'],2)
 def test_invalid_does_not_write(self):
  for lines in [[('book',0)],[('unknown',1)],[]]:
   old=self.snapshot()
   with self.assertRaises(ValueError):self.shop.place_order('invalid',lines,member=True)
   self.assertEqual(self.snapshot(),old)

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(PreviewContract)
 if phase!='v1':suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(CheckoutContract))
 result=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(not result.wasSuccessful())
