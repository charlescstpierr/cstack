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
            [BASH, str(SCRIPT), str(self.logfile), "build", "chose bun", why, evidence, "pass"],
            cwd=self.root, capture_output=True, check=True,
        )
        row = self.logfile.read_bytes().split(b"\n")[1]
        self.assertEqual(row.count(b"\t"), 5)
        fields = row.split(b"\t")
        self.assertEqual(len(fields), 6)
        self.assertEqual(fields[3], why.encode("utf-8"))
        self.assertEqual(fields[4], b" [31mred [0m    ")
        for byte in row:
            if byte in (9,):
                continue
            self.assertGreater(byte, 31)
            self.assertNotEqual(byte, 127)


if __name__ == "__main__":
    unittest.main()
