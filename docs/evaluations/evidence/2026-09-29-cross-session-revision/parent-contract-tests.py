import unittest
from src.formatting import preview_label, receipt_id, status_label

class CurrentProductContract(unittest.TestCase):
    def test_preview_changed_boundary(self):
        self.assertEqual(preview_label('abcdefg'), 'abcdef')
    def test_preview_long(self):
        self.assertEqual(preview_label('abcdefghijklmnop'), 'abcdef')
    def test_preview_short_empty(self):
        self.assertEqual(preview_label('abc'), 'abc')
        self.assertEqual(preview_label(''), '')
    def test_preview_unicode_characters(self):
        self.assertEqual(preview_label('甲乙丙丁戊己庚'), '甲乙丙丁戊己')
    def test_receipt_preserved(self):
        self.assertEqual(receipt_id('abcdefghijklmnop'), 'abcdefghijkl')
        self.assertEqual(receipt_id('abc'), 'abc')
    def test_status_remaining_task(self):
        self.assertEqual(status_label('  ready  '), 'READY')
        self.assertEqual(status_label(' \t\n'), '')
    def test_no_other_formatter_uppercase(self):
        self.assertEqual(preview_label('abcdefgh'), 'abcdef')
        self.assertEqual(receipt_id('abcdefghijklmnop'), 'abcdefghijkl')

if __name__ == '__main__': unittest.main(verbosity=2)
