"""Stack-base rebase boundary: rebase-plan emission and stack-rebase preflight.

Run from the skill directory: python3 -m unittest tests/test_stack_cli.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
STACK_PY = SKILL_DIR / "stack.py"
STACK_REBASE = SKILL_DIR / "scripts" / "stack-rebase"


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), cwd=cwd, text=True, capture_output=True, check=False)


def git(cwd: Path, *args: str) -> str:
    proc = run("git", *args, cwd=cwd)
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout.strip()


def commit_file(cwd: Path, name: str, content: str, message: str) -> str:
    (cwd / name).write_text(content)
    git(cwd, "add", name)
    git(cwd, "commit", "-q", "-m", message)
    return git(cwd, "rev-parse", "HEAD")


class StaleLocalBaseTest(unittest.TestCase):
    """Local master stays at A while the stack is built on origin/master C, then origin/master moves to D."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        origin = root / "origin.git"
        self.repo = root / "work"
        other = root / "other"
        git(root, "init", "-q", "--bare", "-b", "master", str(origin))
        for clone in (self.repo, other):
            git(root, "clone", "-q", str(origin), str(clone))
            git(clone, "config", "user.email", "test@example.com")
            git(clone, "config", "user.name", "Test")
            git(clone, "config", "commit.gpgsign", "false")

        self.a = commit_file(self.repo, "shared.txt", "0\n", "A")
        git(self.repo, "push", "-q", "origin", "HEAD:master")
        git(self.repo, "branch", "-q", "release")
        git(self.repo, "push", "-q", "origin", "release")

        git(other, "pull", "-q", "origin", "master")
        self.b = commit_file(other, "shared.txt", "1\n", "B")
        self.c = commit_file(other, "shared.txt", "2\n", "C")
        git(other, "push", "-q", "origin", "HEAD:master")

        git(self.repo, "fetch", "-q", "origin")
        git(self.repo, "switch", "-q", "-c", "feature-one", "origin/master")
        self.f1 = commit_file(self.repo, "one.txt", "one\n", "F1")
        git(self.repo, "switch", "-q", "-c", "feature-two")
        self.f2 = commit_file(self.repo, "two.txt", "two\n", "F2")
        git(self.repo, "push", "-q", "origin", "feature-one", "feature-two")

        self.d = commit_file(other, "other.txt", "d\n", "D")
        git(other, "push", "-q", "origin", "HEAD:master")
        git(self.repo, "fetch", "-q", "origin")
        assert git(self.repo, "rev-parse", "master") == self.a

        self.stacks = root / "stacks"
        self.stacks.mkdir()
        (self.stacks / "abc-1.toml").write_text(
            f"""version = 1

[stack]
id = "ABC-1"
title = "Test stack"
base_ref = "master"

[repo]
github = "example/test"
workspace = "{self.repo}"

[[prs]]
id = "ABC-2"
title = "One"
tickets = ["ABC-2"]
branch = "feature-one"
parent = "stack-base"
base_ref = "master"
github_pr = 1
notes = ""

[[prs]]
id = "ABC-3"
title = "Two"
tickets = ["ABC-3"]
branch = "feature-two"
parent = "ABC-2"
base_ref = "feature-one"
github_pr = 2
notes = ""
"""
        )
        (self.stacks / "abc-1.events.jsonl").touch()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def rebase_plan(self, *extra: str, target: str = "ABC-2", onto: str = "origin/master") -> list[list[str]]:
        proc = run(
            sys.executable,
            str(STACK_PY),
            "--stacks-dir",
            str(self.stacks),
            "rebase-plan",
            "ABC-1",
            "--from",
            target,
            "--onto",
            onto,
            *extra,
            cwd=SKILL_DIR,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return [line.split("\t") for line in proc.stdout.strip().splitlines()]

    def dry_run(self, rows: list[list[str]]) -> subprocess.CompletedProcess[str]:
        plan = Path(self.tmp.name) / "plan.tsv"
        plan.write_text("\n".join("\t".join(row) for row in rows) + "\n")
        return run(sys.executable, str(STACK_REBASE), "--repo", str(self.repo), "--plan", str(plan), cwd=self.repo)

    def test_plan_without_repo_uses_remote_base(self) -> None:
        rows = self.rebase_plan()
        self.assertEqual(rows[0], ["feature-one", "origin/master", "origin/master"])
        self.assertEqual(rows[1], ["feature-two", "feature-one"])

    def test_plan_with_repo_resolves_merge_base(self) -> None:
        rows = self.rebase_plan("--repo", str(self.repo))
        self.assertEqual(rows[0], ["feature-one", "origin/master", self.c])

    def test_mid_stack_plan_uses_parent_branch(self) -> None:
        rows = self.rebase_plan(target="ABC-3", onto="origin/feature-one")
        self.assertEqual(rows, [["feature-two", "origin/feature-one", "feature-one"]])

    def test_stale_local_base_is_refused(self) -> None:
        proc = self.dry_run([["feature-one", "origin/master", "master"], ["feature-two", "feature-one"]])
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("would replay 2 commit(s) already in origin/master", proc.stderr)
        self.assertIn(f"{self.b[:7]} B", proc.stderr)
        self.assertIn(f"{self.c[:7]} C", proc.stderr)
        self.assertIn(f"merge-base of feature-one and origin/master is {self.c[:7]}", proc.stderr)
        self.assertNotIn("DRY-RUN", proc.stdout)

    def test_non_ancestor_boundary_is_refused(self) -> None:
        proc = self.dry_run(self.rebase_plan())
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("is not an ancestor of feature-one", proc.stderr)
        self.assertIn(f"merge-base of feature-one and origin/master is {self.c[:7]}", proc.stderr)

    def test_resolved_plan_replays_only_stack_commits(self) -> None:
        proc = self.dry_run(self.rebase_plan("--repo", str(self.repo)))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("DRY-RUN feature-one: replay 1 commit(s)", proc.stdout)
        self.assertIn(f"  {self.f1[:7]} F1", proc.stdout)
        self.assertIn("DRY-RUN feature-two: replay 1 commit(s)", proc.stdout)
        self.assertIn(f"  {self.f2[:7]} F2", proc.stdout)
        self.assertIn("Dry-run clean.", proc.stdout)

    def test_resolved_plan_onto_another_base(self) -> None:
        proc = self.dry_run(self.rebase_plan("--repo", str(self.repo), onto="origin/release"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("DRY-RUN feature-one: replay 1 commit(s)", proc.stdout)
        self.assertIn("Dry-run clean.", proc.stdout)


if __name__ == "__main__":
    unittest.main()
