#!/usr/bin/env python3
"""Manage PR stack TOML files and sidecar event logs."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_STACKS_DIR = SCRIPT_DIR / "stacks"
EVENT_KEYS = ("date", "kind", "summary", "pr_ids", "notes")
PR_KEYS = ("id", "title", "tickets", "branch", "parent", "base_ref", "github_pr", "notes")


@dataclass(frozen=True)
class StackFile:
    path: Path
    data: dict[str, Any]


@dataclass(frozen=True)
class Match:
    stack: StackFile
    kind: str
    value: str


class CliError(Exception):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage PR stack TOML files and event logs.")
    parser.add_argument(
        "--stacks-dir",
        type=Path,
        default=DEFAULT_STACKS_DIR,
        help=f"stack directory (default: {DEFAULT_STACKS_DIR})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit JSON for commands that support structured output",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_stack = subparsers.add_parser("add-stack", help="create a new stack file")
    add_stack.add_argument("--id", required=True, help="stack id, usually the story key")
    add_stack.add_argument("--title", required=True, help="stack title")
    add_stack.add_argument("--github", required=True, help="GitHub repo as owner/name")
    add_stack.add_argument("--workspace", required=True, help="absolute local workspace path")
    add_stack.add_argument("--base-ref", default="master", help="stack base ref")
    add_stack.add_argument(
        "--filename",
        help="filename to create inside stacks-dir; defaults to a slug from id and title",
    )

    add_to_stack = subparsers.add_parser(
        "add-to-stack",
        help="append a new PR at the top of an existing stack",
    )
    add_to_stack.add_argument("stack", help="stack id, filename stem, or path")
    add_to_stack.add_argument("--id", help="PR id; defaults to the sole ticket")
    add_to_stack.add_argument("--title", required=True, help="PR title")
    add_to_stack.add_argument(
        "--ticket",
        action="append",
        dest="tickets",
        required=True,
        help="ticket key; repeat for multi-ticket PRs",
    )
    add_to_stack.add_argument("--branch", required=True, help="new PR branch name")
    add_to_stack.add_argument("--github-pr", required=True, type=int, help="GitHub PR number")
    add_to_stack.add_argument("--notes", default="", help="durable stack notes")
    add_to_stack.add_argument("--parent", help="parent PR id")
    add_to_stack.add_argument("--base-ref", help="base ref")

    subparsers.add_parser("list", help="list stacks")

    show = subparsers.add_parser("show", help="show a stack in order")
    show.add_argument("stack", help="stack id, filename stem, or path")

    find = subparsers.add_parser("find", help="search stacks")
    find.add_argument("query", help="stack id, ticket, branch, PR number, or text")

    tip = subparsers.add_parser("tip", help="show the current stack tip")
    tip.add_argument("stack", help="stack id, filename stem, or path")

    validate = subparsers.add_parser("validate", help="validate one stack")
    validate.add_argument("stack", help="stack id, filename stem, or path")

    descendants = subparsers.add_parser("descendants", help="show descendants of a PR")
    descendants.add_argument("stack", help="stack id, filename stem, or path")
    descendants.add_argument("target", help="PR id, ticket, branch, PR number, or stack-base")

    rebase_plan = subparsers.add_parser("rebase-plan", help="emit stack-rebase TSV")
    rebase_plan.add_argument("stack", help="stack id, filename stem, or path")
    rebase_plan.add_argument("--from", dest="from_target", required=True, help="first PR")
    rebase_plan.add_argument("--onto", required=True, help="new parent for the first row")

    mark_merged = subparsers.add_parser("mark-merged", help="record a merged PR")
    mark_merged.add_argument("stack", help="stack id, filename stem, or path")
    mark_merged.add_argument("target", help="PR id, ticket, branch, or PR number")
    mark_merged.add_argument("--base", required=True, help="new base ref for immediate descendants")
    mark_merged.add_argument("--notes", default="", help="durable notes to append to the merged PR")

    record_event = subparsers.add_parser("record-event", help="append one event")
    record_event.add_argument("stack", help="stack id, filename stem, or path")
    record_event.add_argument("--kind", required=True, help="event kind")
    record_event.add_argument("--summary", required=True, help="event summary")
    record_event.add_argument("--pr", action="append", dest="prs", default=[], help="PR target")
    record_event.add_argument("--notes", default="", help="event notes")

    import_pr = subparsers.add_parser("import-pr", help="import one GitHub PR")
    import_pr.add_argument("stack", help="stack id, filename stem, or path")
    import_pr.add_argument("github_pr", type=int, help="GitHub PR number")
    import_pr.add_argument("--id", help="PR id override")
    import_pr.add_argument("--notes", default="", help="durable stack notes")

    args = parser.parse_args()

    try:
        result = dispatch(args)
        if result is not None:
            print(result)
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


def dispatch(args: argparse.Namespace) -> str | None:
    if args.command == "add-stack":
        path = create_stack(args)
        return json_or_text(args, {"path": str(path)}, str(path))
    if args.command == "add-to-stack":
        stack_file, pr = add_to_stack_tip(args)
        return json_or_text(args, pr_output(stack_file, pr), f"added {pr['id']} to {stack_file.path}")
    if args.command == "list":
        return list_stacks_command(args)
    if args.command == "show":
        return show_command(args)
    if args.command == "find":
        return find_command(args)
    if args.command == "tip":
        return tip_command(args)
    if args.command == "validate":
        return validate_command(args)
    if args.command == "descendants":
        return descendants_command(args)
    if args.command == "rebase-plan":
        return rebase_plan_command(args)
    if args.command == "mark-merged":
        return mark_merged_command(args)
    if args.command == "record-event":
        return record_event_command(args)
    if args.command == "import-pr":
        return import_pr_command(args)
    raise CliError(f"unknown command: {args.command}")


def create_stack(args: argparse.Namespace) -> Path:
    stacks_dir = args.stacks_dir
    stacks_dir.mkdir(parents=True, exist_ok=True)

    filename = args.filename or f"{slugify(args.id)}-{slugify(args.title)}.toml"
    if not filename.endswith(".toml"):
        filename += ".toml"
    path = stacks_dir / filename
    if path.exists():
        raise CliError(f"stack file already exists: {path}")
    if event_log_path(path).exists():
        raise CliError(f"event log already exists: {event_log_path(path)}")

    data: dict[str, Any] = {
        "version": 1,
        "stack": {"id": args.id, "title": args.title, "base_ref": args.base_ref},
        "repo": {"github": args.github, "workspace": args.workspace},
    }
    write_stack(path, data)
    event_log_path(path).touch()
    return path


def add_to_stack_tip(args: argparse.Namespace) -> tuple[StackFile, dict[str, Any]]:
    stack_file = resolve_stack(args.stacks_dir, args.stack)
    data = stack_file.data
    prs = get_prs(data)

    pr_id = args.id or default_pr_id(data, args.tickets, args.branch)
    ensure_new_pr(prs, pr_id, args.branch, args.github_pr)

    tip = stack_tip(data)
    parent = args.parent or (tip["id"] if tip else "stack-base")
    base_ref = args.base_ref or (tip["branch"] if tip else data["stack"]["base_ref"])
    if parent != "stack-base" and find_pr(data, parent) is None:
        raise CliError(f"parent does not exist in stack: {parent}")

    pr = make_pr(pr_id, args.title, args.tickets, args.branch, parent, base_ref, args.github_pr, args.notes)
    prs.append(pr)

    write_stack(stack_file.path, data)
    append_event(stack_file.path, add_pr_event(pr_id))
    return stack_file, pr


def list_stacks_command(args: argparse.Namespace) -> str:
    stacks = list(iter_stacks(args.stacks_dir))
    rows = []
    for stack_file in stacks:
        data = stack_file.data
        tip = stack_tip(data)
        rows.append(
            {
                "id": data["stack"]["id"],
                "title": data["stack"]["title"],
                "repo": data["repo"]["github"],
                "prs": len(get_prs(data)),
                "tip": tip["branch"] if tip else "",
                "path": str(stack_file.path),
            }
        )
    if args.json_output:
        return to_json(rows)
    return format_rows(rows, ("id", "prs", "tip", "repo", "title"))


def show_command(args: argparse.Namespace) -> str:
    stack_file = resolve_stack(args.stacks_dir, args.stack)
    data = stack_file.data
    rows = [pr_output(stack_file, pr) for pr in get_prs(data)]
    if args.json_output:
        return to_json({"stack": stack_summary(stack_file), "prs": rows})
    return format_rows(rows, ("id", "tickets", "branch", "parent", "base_ref", "github"))


def find_command(args: argparse.Namespace) -> str:
    matches = find_matches(args.stacks_dir, args.query)
    if args.json_output:
        return to_json([match_output(match) for match in matches])
    if not matches:
        return ""
    return format_rows([match_output(match) for match in matches], ("stack", "kind", "value", "path"))


def tip_command(args: argparse.Namespace) -> str:
    stack_file = resolve_stack(args.stacks_dir, args.stack)
    tip = stack_tip(stack_file.data)
    if tip is None:
        output = {"stack": stack_file.data["stack"]["id"], "tip": None}
        return json_or_text(args, output, "")
    output = pr_output(stack_file, tip)
    return json_or_text(args, output, f"{tip['id']}\t{tip['branch']}\t{github_pr_url(stack_file, tip)}")


def validate_command(args: argparse.Namespace) -> str:
    stack_file = resolve_stack(args.stacks_dir, args.stack)
    issues = validate_stack(stack_file)
    output = {"ok": not issues, "issues": issues}
    if issues:
        text = "\n".join(issues)
        if args.json_output:
            print(to_json(output))
        raise CliError(text)
    return json_or_text(args, output, "ok")


def descendants_command(args: argparse.Namespace) -> str:
    stack_file = resolve_stack(args.stacks_dir, args.stack)
    descendants = descendant_prs(stack_file.data, args.target)
    rows = [pr_output(stack_file, pr) for pr in descendants]
    if args.json_output:
        return to_json(rows)
    return format_rows(rows, ("id", "branch", "parent", "base_ref", "github"))


def rebase_plan_command(args: argparse.Namespace) -> str:
    stack_file = resolve_stack(args.stacks_dir, args.stack)
    rows = rebase_plan(stack_file.data, args.from_target, args.onto)
    if args.json_output:
        return to_json(rows)
    return "\n".join(
        "\t".join(filter(None, (row["branch"], row["new_parent"], row.get("old_parent", ""))))
        for row in rows
    )


def mark_merged_command(args: argparse.Namespace) -> str:
    stack_file = resolve_stack(args.stacks_dir, args.stack)
    data = stack_file.data
    target = require_pr(data, args.target)
    children = [pr for pr in get_prs(data) if pr["parent"] == target["id"]]
    for child in children:
        child["base_ref"] = args.base
    if args.notes:
        target["notes"] = append_note(target.get("notes", ""), args.notes)

    write_stack(stack_file.path, data)
    append_event(
        stack_file.path,
        {
            "date": date.today().isoformat(),
            "kind": "merge",
            "summary": f"Marked {target['id']} as merged.",
            "pr_ids": [target["id"], *[child["id"] for child in children]],
            "notes": f"Updated {len(children)} immediate descendant base_ref values to {args.base}.",
        },
    )
    output = {"merged": target["id"], "updated_descendants": [child["id"] for child in children]}
    return json_or_text(args, output, f"marked {target['id']} merged; updated {len(children)} descendants")


def record_event_command(args: argparse.Namespace) -> str:
    stack_file = resolve_stack(args.stacks_dir, args.stack)
    pr_ids = [require_pr(stack_file.data, target)["id"] for target in args.prs]
    event = {
        "date": date.today().isoformat(),
        "kind": args.kind,
        "summary": args.summary,
        "pr_ids": pr_ids,
        "notes": args.notes,
    }
    append_event(stack_file.path, event)
    return json_or_text(args, event, f"recorded {args.kind} event for {stack_file.data['stack']['id']}")


def import_pr_command(args: argparse.Namespace) -> str:
    stack_file = resolve_stack(args.stacks_dir, args.stack)
    data = stack_file.data
    metadata = fetch_pr_metadata(data["repo"]["github"], args.github_pr)
    branch = metadata["headRefName"]
    base_ref = metadata["baseRefName"]
    existing = find_existing_import_target(data, args.id, args.github_pr, branch)
    parent = parent_from_base_ref(data, base_ref)
    pr_id = args.id or (existing["id"] if existing else default_import_id(data, metadata))

    if existing is None:
        tip = stack_tip(data)
        if tip is not None and parent != tip["id"]:
            raise CliError(f"new PR base {base_ref!r} is not the current stack tip branch")
        ensure_new_pr(get_prs(data), pr_id, branch, args.github_pr)
        pr = make_pr(pr_id, metadata["title"], tickets_from_metadata(metadata), branch, parent, base_ref, args.github_pr, args.notes)
        get_prs(data).append(pr)
        action = "imported"
    else:
        existing.update(
            make_pr(pr_id, metadata["title"], tickets_from_metadata(metadata), branch, parent, base_ref, args.github_pr, args.notes or existing.get("notes", ""))
        )
        pr = existing
        action = "updated"

    write_stack(stack_file.path, data)
    append_event(
        stack_file.path,
        {
            "date": date.today().isoformat(),
            "kind": "import-pr",
            "summary": f"{action.title()} GitHub PR #{args.github_pr} as {pr_id}.",
            "pr_ids": [pr_id],
            "notes": "",
        },
    )
    return json_or_text(args, pr_output(stack_file, pr), f"{action} {pr_id} from PR #{args.github_pr}")


def iter_stacks(stacks_dir: Path) -> list[StackFile]:
    if not stacks_dir.exists():
        return []
    stacks = []
    for path in sorted(stacks_dir.glob("*.toml")):
        stacks.append(StackFile(path=path, data=read_stack(path)))
    return stacks


def resolve_stack(stacks_dir: Path, selector: str) -> StackFile:
    path = Path(selector)
    if path.exists():
        return StackFile(path=path, data=read_stack(path))

    matches = []
    for stack_file in iter_stacks(stacks_dir):
        stack = stack_file.data["stack"]
        if selector in {stack_file.path.stem, stack_file.path.name, stack["id"]}:
            matches.append(stack_file)
    if not matches:
        raise CliError(f"no stack matched {selector!r} in {stacks_dir}")
    if len(matches) > 1:
        raise CliError(f"multiple stacks matched {selector!r}: {', '.join(str(match.path) for match in matches)}")
    return matches[0]


def find_matches(stacks_dir: Path, query: str) -> list[Match]:
    query_lower = query.lower()
    matches: list[Match] = []
    for stack_file in iter_stacks(stacks_dir):
        stack = stack_file.data["stack"]
        stack_values = {
            "stack-id": stack["id"],
            "stack-title": stack["title"],
            "filename": stack_file.path.name,
        }
        for kind, value in stack_values.items():
            if query_lower in str(value).lower():
                matches.append(Match(stack_file, kind, str(value)))
        for pr in get_prs(stack_file.data):
            values = {
                "pr-id": pr["id"],
                "title": pr["title"],
                "branch": pr["branch"],
                "github-pr": str(pr["github_pr"]),
            }
            values.update({f"ticket:{ticket}": ticket for ticket in pr["tickets"]})
            for kind, value in values.items():
                if query_lower in str(value).lower():
                    matches.append(Match(stack_file, kind, str(value)))
    return matches


def read_stack(path: Path) -> dict[str, Any]:
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise CliError(f"invalid TOML in {path}: {exc}") from exc
    return data


def read_events(stack_path: Path) -> list[dict[str, Any]]:
    path = event_log_path(stack_path)
    if not path.exists():
        return []
    events = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CliError(f"invalid JSONL in {path}:{lineno}: {exc}") from exc
        events.append(event)
    return events


def validate_stack(stack_file: StackFile) -> list[str]:
    issues: list[str] = []
    data = stack_file.data
    if data.get("version") != 1:
        issues.append(f"unsupported version: {data.get('version')!r}")
    for table in ("stack", "repo"):
        if not isinstance(data.get(table), dict):
            issues.append(f"missing [{table}] table")
    if issues:
        return issues

    require_fields(issues, "[stack]", data["stack"], ("id", "title", "base_ref"))
    require_fields(issues, "[repo]", data["repo"], ("github", "workspace"))

    prs = data.get("prs", [])
    if prs is None:
        prs = []
    if not isinstance(prs, list):
        issues.append("prs must be an array of tables")
        return issues

    seen: dict[str, set[Any]] = {"id": set(), "branch": set(), "github_pr": set()}
    ids: set[str] = set()
    branch_by_id: dict[str, str] = {}
    for index, pr in enumerate(prs, start=1):
        label = f"prs[{index}]"
        require_fields(issues, label, pr, PR_KEYS)
        for key in ("id", "branch", "github_pr"):
            value = pr.get(key)
            if value in seen[key]:
                issues.append(f"duplicate {key}: {value}")
            seen[key].add(value)
        if isinstance(pr.get("tickets"), list) and all(isinstance(ticket, str) for ticket in pr["tickets"]):
            pass
        else:
            issues.append(f"{label}.tickets must be a string array")
        if isinstance(pr.get("id"), str):
            ids.add(pr["id"])
        if isinstance(pr.get("id"), str) and isinstance(pr.get("branch"), str):
            branch_by_id[pr["id"]] = pr["branch"]

    known_base_refs = {data["stack"].get("base_ref"), *branch_by_id.values()}
    for pr in prs:
        parent = pr.get("parent")
        if parent == "stack-base":
            if pr.get("base_ref") != data["stack"].get("base_ref"):
                issues.append(f"{pr.get('id')}: stack-base PR base_ref must be {data['stack'].get('base_ref')}")
        elif parent not in ids:
            issues.append(f"{pr.get('id')}: parent does not exist: {parent}")
        elif pr.get("base_ref") not in known_base_refs:
            issues.append(f"{pr.get('id')}: base_ref is not stack base or a known PR branch: {pr.get('base_ref')}")

    try:
        events = read_events(stack_file.path)
    except CliError as exc:
        issues.append(str(exc))
        events = []
    for index, event in enumerate(events, start=1):
        label = f"events[{index}]"
        if set(event) != set(EVENT_KEYS):
            issues.append(f"{label}: keys must be {', '.join(EVENT_KEYS)}")
            continue
        if not isinstance(event["pr_ids"], list) or not all(isinstance(pr_id, str) for pr_id in event["pr_ids"]):
            issues.append(f"{label}.pr_ids must be a string array")
        for pr_id in event.get("pr_ids", []):
            if pr_id not in ids and not any(pr_id in pr.get("tickets", []) for pr in prs):
                issues.append(f"{label}: unknown pr_id {pr_id}")
    return issues


def require_fields(issues: list[str], label: str, values: dict[str, Any], keys: tuple[str, ...]) -> None:
    for key in keys:
        if key not in values:
            issues.append(f"{label}: missing {key}")


def get_prs(data: dict[str, Any]) -> list[dict[str, Any]]:
    prs = data.setdefault("prs", [])
    if not isinstance(prs, list):
        raise CliError("invalid prs table")
    return prs


def find_pr(data: dict[str, Any], target: str) -> dict[str, Any] | None:
    for pr in get_prs(data):
        if target in {pr["id"], pr["branch"], str(pr["github_pr"])} or target in pr["tickets"]:
            return pr
    return None


def require_pr(data: dict[str, Any], target: str) -> dict[str, Any]:
    pr = find_pr(data, target)
    if pr is None:
        raise CliError(f"no PR matched {target!r}")
    return pr


def stack_tip(data: dict[str, Any]) -> dict[str, Any] | None:
    prs = get_prs(data)
    return prs[-1] if prs else None


def descendant_prs(data: dict[str, Any], target: str) -> list[dict[str, Any]]:
    prs = get_prs(data)
    if target == "stack-base":
        return prs
    start = require_pr(data, target)
    descendants = []
    active_parent = start["id"]
    for pr in prs:
        if pr["id"] == start["id"]:
            continue
        if pr["parent"] == active_parent:
            descendants.append(pr)
            active_parent = pr["id"]
    return descendants


def rebase_plan(data: dict[str, Any], target: str, onto: str) -> list[dict[str, str]]:
    prs = get_prs(data) if target == "stack-base" else [require_pr(data, target), *descendant_prs(data, target)]
    rows = []
    previous_branch = onto
    for index, pr in enumerate(prs):
        row = {"branch": pr["branch"], "new_parent": previous_branch}
        if index == 0:
            row["old_parent"] = pr["base_ref"]
        rows.append(row)
        previous_branch = pr["branch"]
    return rows


def parent_from_base_ref(data: dict[str, Any], base_ref: str) -> str:
    if base_ref == data["stack"]["base_ref"]:
        return "stack-base"
    for pr in get_prs(data):
        if pr["branch"] == base_ref:
            return pr["id"]
    raise CliError(f"base ref {base_ref!r} does not match stack base or any PR branch")


def find_existing_import_target(data: dict[str, Any], pr_id: str | None, github_pr: int, branch: str) -> dict[str, Any] | None:
    for pr in get_prs(data):
        if pr_id and pr["id"] == pr_id:
            return pr
        if pr["github_pr"] == github_pr or pr["branch"] == branch:
            return pr
    return None


def fetch_pr_metadata(repo: str, pr_number: int) -> dict[str, Any]:
    if shutil.which("gh") is None:
        raise CliError("gh CLI is not available")
    command = [
        "gh",
        "pr",
        "view",
        str(pr_number),
        "--repo",
        repo,
        "--json",
        "number,title,headRefName,baseRefName",
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise CliError(result.stderr.strip() or f"gh pr view failed with exit code {result.returncode}")
    try:
        metadata = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CliError(f"gh returned invalid JSON: {exc}") from exc
    for key in ("number", "title", "headRefName", "baseRefName"):
        if key not in metadata or metadata[key] in ("", None):
            raise CliError(f"gh metadata missing {key}")
    if metadata["number"] != pr_number:
        raise CliError(f"gh returned PR #{metadata['number']} for requested PR #{pr_number}")
    return metadata


def tickets_from_metadata(metadata: dict[str, Any]) -> list[str]:
    text = f"{metadata['title']} {metadata['headRefName']}"
    tickets = list(dict.fromkeys(re.findall(r"[A-Z]+-\d+", text.upper())))
    return tickets or [f"PR-{metadata['number']}"]


def default_import_id(data: dict[str, Any], metadata: dict[str, Any]) -> str:
    tickets = tickets_from_metadata(metadata)
    if len(tickets) == 1 and not tickets[0].startswith("PR-"):
        return tickets[0]
    return f"{data['stack']['id']}-{slugify(metadata['headRefName'])}"


def ensure_new_pr(prs: list[dict[str, Any]], pr_id: str, branch: str, github_pr: int) -> None:
    if any(pr.get("id") == pr_id for pr in prs):
        raise CliError(f"PR id already exists in stack: {pr_id}")
    if any(pr.get("branch") == branch for pr in prs):
        raise CliError(f"branch already exists in stack: {branch}")
    if any(pr.get("github_pr") == github_pr for pr in prs):
        raise CliError(f"GitHub PR already exists in stack: {github_pr}")


def make_pr(
    pr_id: str,
    title: str,
    tickets: list[str],
    branch: str,
    parent: str,
    base_ref: str,
    github_pr: int,
    notes: str,
) -> dict[str, Any]:
    return {
        "id": pr_id,
        "title": title,
        "tickets": tickets,
        "branch": branch,
        "parent": parent,
        "base_ref": base_ref,
        "github_pr": github_pr,
        "notes": notes,
    }


def default_pr_id(data: dict[str, Any], tickets: list[str], branch: str) -> str:
    if len(tickets) == 1:
        return tickets[0]
    return f"{data['stack']['id']}-{slugify(branch)}"


def read_events_for_output(stack_file: StackFile) -> list[dict[str, Any]]:
    try:
        return read_events(stack_file.path)
    except CliError:
        return []


def write_stack(path: Path, data: dict[str, Any]) -> None:
    text = render_stack(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def append_event(stack_path: Path, event: dict[str, Any]) -> None:
    path = event_log_path(stack_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
        handle.write("\n")


def event_log_path(stack_path: Path) -> Path:
    return stack_path.with_suffix(".events.jsonl")


def add_pr_event(pr_id: str) -> dict[str, Any]:
    return {
        "date": date.today().isoformat(),
        "kind": "add-pr",
        "summary": f"Added {pr_id} at the top of the stack.",
        "pr_ids": [pr_id],
        "notes": "",
    }


def render_stack(data: dict[str, Any]) -> str:
    lines = ["version = 1", "", "[stack]"]
    write_table(lines, data["stack"], ("id", "title", "base_ref"))
    lines.extend(["", "[repo]"])
    write_table(lines, data["repo"], ("github", "workspace"))

    for pr in data.get("prs", []):
        lines.extend(["", "[[prs]]"])
        write_table(lines, pr, PR_KEYS)

    return "\n".join(lines) + "\n"


def write_table(lines: list[str], values: dict[str, Any], keys: tuple[str, ...]) -> None:
    for key in keys:
        if key in values:
            lines.append(f"{key} = {format_value(values[key])}")


def format_value(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "[" + ", ".join(json.dumps(item, ensure_ascii=False) for item in value) + "]"
    raise CliError(f"cannot render TOML value: {value!r}")


def pr_output(stack_file: StackFile, pr: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": pr["id"],
        "title": pr["title"],
        "tickets": ",".join(pr["tickets"]),
        "branch": pr["branch"],
        "parent": pr["parent"],
        "base_ref": pr["base_ref"],
        "github_pr": pr["github_pr"],
        "github": github_pr_url(stack_file, pr),
        "notes": pr.get("notes", ""),
    }


def stack_summary(stack_file: StackFile) -> dict[str, Any]:
    tip = stack_tip(stack_file.data)
    return {
        "id": stack_file.data["stack"]["id"],
        "title": stack_file.data["stack"]["title"],
        "repo": stack_file.data["repo"]["github"],
        "path": str(stack_file.path),
        "prs": len(get_prs(stack_file.data)),
        "events": len(read_events_for_output(stack_file)),
        "tip": tip["id"] if tip else None,
    }


def match_output(match: Match) -> dict[str, str]:
    return {
        "stack": match.stack.data["stack"]["id"],
        "kind": match.kind,
        "value": match.value,
        "path": str(match.stack.path),
    }


def github_pr_url(stack_file: StackFile, pr: dict[str, Any]) -> str:
    return f"https://github.com/{stack_file.data['repo']['github']}/pull/{pr['github_pr']}"


def append_note(current: str, addition: str) -> str:
    if not current:
        return addition
    return f"{current} {addition}"


def json_or_text(args: argparse.Namespace, data: Any, text: str) -> str:
    return to_json(data) if args.json_output else text


def to_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def format_rows(rows: list[dict[str, Any]], columns: tuple[str, ...]) -> str:
    if not rows:
        return ""
    widths = {column: len(column) for column in columns}
    for row in rows:
        for column in columns:
            widths[column] = max(widths[column], len(str(row.get(column, ""))))
    header = "  ".join(column.ljust(widths[column]) for column in columns)
    divider = "  ".join("-" * widths[column] for column in columns)
    body = ["  ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns) for row in rows]
    return "\n".join([header, divider, *body])


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "stack"


if __name__ == "__main__":
    raise SystemExit(main())
