import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "plugins/cstack/skills/show-me-your-work/scripts/log.sh"
BASH = shutil.which("bash")


class LogScriptTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.state = self.root / ".cstack"
        self.logfile = self.state / "logs/decisions.tsv"

    def tearDown(self):
        self.temp.cleanup()

    def log(self):
        return subprocess.run(
            [BASH, str(SCRIPT), str(self.logfile), "build", "choix de bun", "déjà présent dans le dépôt", "bun test", "pass"],
            cwd=self.root, text=True, capture_output=True, check=True,
        )

    def write_row(self, phase, decision, why, evidence, result):
        args = [BASH, str(SCRIPT), str(self.logfile), phase, decision, why, evidence, result]
        encoded = [a if isinstance(a, bytes) else os.fsencode(str(a)) for a in args]
        return subprocess.run(encoded, cwd=self.root, capture_output=True, check=True)

    def test_logging_ignores_the_state_directory(self):
        self.log()
        self.assertEqual((self.state / ".gitignore").read_text(), "*\n")
        row = self.logfile.read_text().splitlines()[1].split("\t")
        self.assertEqual(row[1:], ["build", "choix de bun", "déjà présent dans le dépôt", "bun test", "pass"])

    def test_dangling_gitignore_symlink_is_not_followed(self):
        self.state.mkdir()
        outside = self.root / "escaped"
        (self.state / ".gitignore").symlink_to(outside)
        self.log()
        self.assertFalse(outside.exists())
        self.assertTrue((self.state / ".gitignore").is_symlink())

    def test_control_bytes_are_mapped_to_spaces_and_utf8_survives(self):
        why = "évidence — ok"
        evidence = "\033[31mred\033[0m\v\f\a\b"
        subprocess.run(
            [BASH, str(SCRIPT), str(self.logfile), "build", "漢字ひらがな", why, evidence, "ok 🎯"],
            cwd=self.root, capture_output=True, check=True,
        )
        row = self.logfile.read_bytes().split(b"\n")[1]
        self.assertEqual(row.count(b"\t"), 5)
        fields = row.split(b"\t")
        self.assertEqual(len(fields), 6)
        self.assertEqual(fields[3], why.encode("utf-8"))
        self.assertEqual(fields[4], b" [31mred [0m    ")
        self.assertEqual(fields[2], "漢字ひらがな".encode("utf-8"))
        self.assertEqual(fields[5], "ok 🎯".encode("utf-8"))
        for byte in row:
            if byte in (9,):
                continue
            self.assertGreater(byte, 31)
            self.assertNotEqual(byte, 127)

    def test_c1_controls_and_line_separators_map_to_spaces(self):
        evidence = b"A\xc2\x85B\xc2\x9bC\xc2\x9cD\xc2\x9dE\x9bF\xe2\x80\xa8G\xe2\x80\xa9H"
        why = "Û Ç".encode("utf-8")
        self.write_row("build", "chose bun", why, evidence, "pass")
        fields = self.logfile.read_bytes().split(b"\n")[1].split(b"\t")
        self.assertEqual(len(fields), 6)
        self.assertEqual(fields[3], why)
        self.assertEqual(fields[4], b"A B C D E F G H")
        self.assertNotIn(b"\xc2\x85", fields[4])
        self.assertNotIn(b"\xc2\x9b", fields[4])
        self.assertNotIn(b"\xc2\x9c", fields[4])
        self.assertNotIn(b"\xc2\x9d", fields[4])
        self.assertNotIn(b"\x9b", fields[4])
        self.assertNotIn(b"\xe2\x80\xa8", fields[4])
        self.assertNotIn(b"\xe2\x80\xa9", fields[4])

    def test_formula_prefix_applies_after_leading_controls(self):
        cases = [
            (b"\x01=1+1", b"' =1+1"),
            (b"\t=SUM(A1)", b"' =SUM(A1)"),
            (b"\x7f=x", b"' =x"),
            (b" =1+1", b"' =1+1"),
            (b"\xc2\x85=1+1", b"' =1+1"),
            (b"\xc2\x9b=HYPERLINK", b"' =HYPERLINK"),
            (b"\x9b=cmd", b"' =cmd"),
            (b"\xe2\x80\xa8=1+1", b"' =1+1"),
            (b"=1+1", b"'=1+1"),
            (b"  +cmd", b"'  +cmd"),
            (b"\xc2\x9c@SUM(A1)", b"' @SUM(A1)"),
            (b"\xe2\x80\xa9-1+1", b"' -1+1"),
        ]
        for cell, expected in cases:
            with self.subTest(cell=cell):
                if self.logfile.exists():
                    self.logfile.unlink()
                self.write_row(b"build", b"dec", b"why", cell, b"res")
                fields = self.logfile.read_bytes().split(b"\n")[1].split(b"\t")
                self.assertEqual(len(fields), 6)
                self.assertEqual(fields[4], expected)


if __name__ == "__main__":
    unittest.main()
