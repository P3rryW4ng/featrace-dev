import unittest
from convert import getHostUserInfo

class LanguageTests(unittest.TestCase):
    def test_nearby_pair_on_one_api(self):
        self.assertEqual(getHostUserInfo(["de-DE", "fr-FR"])["systemLanguages"], ["de-DE", "fr-FR"])
