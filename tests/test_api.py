import doctest
import unittest

import subscene.api


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(subscene.api, optionflags=doctest.ELLIPSIS))
    return tests


if __name__ == "__main__":
    unittest.main()
