import unittest
from convert import getHostUserInfo, getHostUserInfoAll, getUserInfoAll

class LanguageTests(unittest.TestCase):
    def test_exact_pair_on_all_three_apis(self):
        for api in (getHostUserInfo, getHostUserInfoAll, getUserInfoAll):
            with self.subTest(api=api.__name__):
                self.assertEqual(api(["de-DE", "en-GB"])["systemLanguages"], ["de-DE", "en-GB"])
