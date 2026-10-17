import unittest
from screen import button

class ButtonRegression(unittest.TestCase):
    def test_enabled_and_zero(self):
        self.assertEqual(button(10), {"enabled": True, "color": "solid-green", "label": "Confirm"})
        self.assertEqual(button(0), {"enabled": False, "color": "half-green", "label": "Confirm"})

if __name__ == "__main__": unittest.main(verbosity=2)
