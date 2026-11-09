"""Offline unit checks. These do NOT represent a Windows compile or GUI runtime test."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('builder', Path(__file__).resolve().parents[1] / 'scripts/builder.py')
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)


class BuilderUnitTests(unittest.TestCase):
    def test_stable_semver_numeric(self):
        tags = ['v1.9.0', 'v1.10.0', 'v2.0.0-rc1', 'latest', 'v1.10.2']
        stable = sorted((b.semver(x), x) for x in tags if b.semver(x))
        self.assertEqual(stable[-1][1], 'v1.10.2')
        self.assertIsNone(b.semver('v1.10.2-beta'))

    def test_application_specific_patch_is_before_single_instance(self):
        with tempfile.TemporaryDirectory() as temp:
            original_source = b.SOURCE
            try:
                b.SOURCE = Path(temp)
                file = b.SOURCE / 'apps/desktop/src/main/index.ts'
                file.parent.mkdir(parents=True)
                file.write_text("import { app } from 'electron';\n// Single-instance guard. Without this\n"
                                "const gotSingleInstanceLock = app.requestSingleInstanceLock();\n", encoding='utf-8')
                b.patch()
                patched = file.read_text(encoding='utf-8')
                self.assertLess(patched.index("app.setPath('userData'"),
                                patched.index('app.requestSingleInstanceLock()'))
                self.assertIn("app.setPath('crashDumps'", patched)
                with self.assertRaises(RuntimeError):
                    b.patch()  # must never silently duplicate adapter
            finally:
                b.SOURCE = original_source

    def test_pe_machine_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'synthetic-header.fixture'
            blob = bytearray(10300)
            blob[0:2] = b'MZ'
            struct.pack_into('<I', blob, 0x3c, 0x100)
            blob[0x100:0x104] = b'PE\x00\x00'
            struct.pack_into('<H', blob, 0x104, 0x8664)
            target.write_bytes(blob)
            b.assert_pe(target)
            struct.pack_into('<H', blob, 0x104, 0x14c)
            target.write_bytes(blob)
            with self.assertRaises(ValueError):
                b.assert_pe(target)
            # Valid 32-bit NSIS bootstrap may install a 64-bit application.
            b.assert_pe(target, architecture=(0x014C, 0x8664))

    def test_compiled_adapter_guard_rejects_missing_build(self):
        with tempfile.TemporaryDirectory() as temp:
            original_source = b.SOURCE
            try:
                b.SOURCE = Path(temp)
                main = b.SOURCE / 'apps/desktop/out/main'
                main.mkdir(parents=True)
                (main / 'index.js').write_text('console.log(123);', encoding='utf-8')
                with self.assertRaises(RuntimeError):
                    b.verify_compiled_adapter()
                (main / 'index.js').write_text('FREECRAWL_PORTABLE_DATA;sessionData;crashDumps;', encoding='utf-8')
                b.verify_compiled_adapter()
            finally:
                b.SOURCE = original_source

    def test_github_release_skips_are_404_only(self):
        # Confirm request_json source has a specific 404 allowance, not blanket error handling.
        import inspect
        source = inspect.getsource(b.request_json)
        self.assertIn('exc.code == 404 and allow404', source)


if __name__ == '__main__':
    unittest.main()
