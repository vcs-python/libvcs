"""
Credit: https://github.com/django/django/blob/4.0.4/tests/utils_tests/test_module_loading.py

From April 25th, 2021. Changes:

- pytest compatibility, use monkeypatch.syspath_prepend
- Removed django-specific material
"""  # noqa: E501
import os
import sys
import unittest
from importlib import import_module

import pytest

from libvcs.utils.module_loading import import_string, module_has_submodule

PY310 = sys.version_info >= (3, 10)


class DefaultLoader(unittest.TestCase):
    def test_loader(self):
        "Normal module existence can be tested"
        test_module = import_module("tests.utils.test_module")
        test_no_submodule = import_module("tests.utils.test_no_submodule")

        # An importable child
        self.assertTrue(module_has_submodule(test_module, "good_module"))
        mod = import_module("tests.utils.test_module.good_module")
        self.assertEqual(mod.content, "Good Module")

        # A child that exists, but will generate an import error if loaded
        self.assertTrue(module_has_submodule(test_module, "bad_module"))
        with self.assertRaises(ImportError):
            import_module("tests.utils.test_module.bad_module")

        # A child that doesn't exist
        self.assertFalse(module_has_submodule(test_module, "no_such_module"))
        with self.assertRaises(ImportError):
            import_module("tests.utils.test_module.no_such_module")

        # A child that doesn't exist, but is the name of a package on the path
        self.assertFalse(module_has_submodule(test_module, "django"))
        with self.assertRaises(ImportError):
            import_module("tests.utils.test_module.django")

        # Don't be confused by caching of import misses
        import types  # NOQA: causes attempted import of tests.utils.types

        self.assertFalse(module_has_submodule(sys.modules["tests.utils"], "types"))

        # A module which doesn't have a __path__ (so no submodules)
        self.assertFalse(module_has_submodule(test_no_submodule, "anything"))
        with self.assertRaises(ImportError):
            import_module("tests.utils.test_no_submodule.anything")

    def test_has_sumbodule_with_dotted_path(self):
        """Nested module existence can be tested."""
        test_module = import_module("tests.utils.test_module")
        # A grandchild that exists.
        self.assertIs(
            module_has_submodule(test_module, "child_module.grandchild_module"), True
        )
        # A grandchild that doesn't exist.
        self.assertIs(
            module_has_submodule(test_module, "child_module.no_such_module"), False
        )
        # A grandchild whose parent doesn't exist.
        self.assertIs(
            module_has_submodule(test_module, "no_such_module.grandchild_module"), False
        )
        # A grandchild whose parent is not a package.
        self.assertIs(
            module_has_submodule(test_module, "good_module.no_such_module"), False
        )


class EggLoader:
    def setUp(self):
        self.egg_dir = "%s/eggs" % os.path.dirname(__file__)

    def tearDown(self):
        sys.path_importer_cache.clear()

        sys.modules.pop("egg_module.sub1.sub2.bad_module", None)
        sys.modules.pop("egg_module.sub1.sub2.good_module", None)
        sys.modules.pop("egg_module.sub1.sub2", None)
        sys.modules.pop("egg_module.sub1", None)
        sys.modules.pop("egg_module.bad_module", None)
        sys.modules.pop("egg_module.good_module", None)
        sys.modules.pop("egg_module", None)

    def test_shallow_loader(self, monkeypatch: pytest.MonkeyPatch):
        "Module existence can be tested inside eggs"
        egg_name = "%s/test_egg.egg" % self.egg_dir
        monkeypatch.syspath_prepend(egg_name)
        egg_module = import_module("egg_module")

        # An importable child
        self.assertTrue(module_has_submodule(egg_module, "good_module"))
        mod = import_module("egg_module.good_module")
        self.assertEqual(mod.content, "Good Module")

        # A child that exists, but will generate an import error if loaded
        self.assertTrue(module_has_submodule(egg_module, "bad_module"))
        with self.assertRaises(ImportError):
            import_module("egg_module.bad_module")

        # A child that doesn't exist
        self.assertFalse(module_has_submodule(egg_module, "no_such_module"))
        with self.assertRaises(ImportError):
            import_module("egg_module.no_such_module")

    def test_deep_loader(self, monkeypatch: pytest.MonkeyPatch):
        "Modules deep inside an egg can still be tested for existence"
        egg_name = "%s/test_egg.egg" % self.egg_dir
        monkeypatch.syspath_prepend(egg_name)
        egg_module = import_module("egg_module.sub1.sub2")

        # An importable child
        self.assertTrue(module_has_submodule(egg_module, "good_module"))
        mod = import_module("egg_module.sub1.sub2.good_module")
        self.assertEqual(mod.content, "Deep Good Module")

        # A child that exists, but will generate an import error if loaded
        self.assertTrue(module_has_submodule(egg_module, "bad_module"))
        with self.assertRaises(ImportError):
            import_module("egg_module.sub1.sub2.bad_module")

        # A child that doesn't exist
        self.assertFalse(module_has_submodule(egg_module, "no_such_module"))
        with self.assertRaises(ImportError):
            import_module("egg_module.sub1.sub2.no_such_module")


class ModuleImportTests:
    def test_import_string(self):
        cls = import_string("libvcs.utils.module_loading.import_string")
        self.assertEqual(cls, import_string)

        # Test exceptions raised
        with self.assertRaises(ImportError):
            import_string("no_dots_in_path")
        msg = 'Module "tests.utils" does not define a "unexistent" attribute'
        with self.assertRaisesMessage(ImportError, msg):
            import_string("tests.utils.unexistent")
