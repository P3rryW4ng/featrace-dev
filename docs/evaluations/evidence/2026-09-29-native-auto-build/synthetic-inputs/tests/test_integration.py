import unittest
from upper import convert as catalog
from lower import convert as events
class IntegrationTest(unittest.TestCase):
 def test_independent_empty_contracts(self):
  self.assertEqual(catalog(''), {'records':[],'errors':[]});self.assertEqual(events(''), {'records':[],'errors':[]})
 def test_no_state_between_calls(self):
  a=catalog('sku,name,price\nx,X,1');events('{"id":"x","timestamp":"2026-01-01T00:00:00Z","payload":null}')
  self.assertEqual(catalog('sku,name,price\nx,X,1'),a)
