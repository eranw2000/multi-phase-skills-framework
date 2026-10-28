#!/usr/bin/env python3
"""Keep a project's plan-status Google Sheet in step with its plan and its repository.

ONE SHEET PER PROJECT, ONE ADDRESS THAT NEVER CHANGES. A file gets copied, mailed and
goes stale in somebody's downloads folder. A Sheet has one link, so the link handed out
once keeps working, and Google keeps the version history for free.

WHAT THIS DOES NOT DECIDE. It never judges that a feature is finished. A human or a
session makes that call and edits the project's own row data. What this enforces is
that the claim is checkable: every row carries a date, every date is a real past date,
and every numbered section of the plan either has a row or is written down as
deliberately having none.

    sync.py --project <name> --check    offline. No token, no network, no writes.
    sync.py --project <name> --setup    create the Sheet once and record its id.
    sync.py --project <name> --push     rewrite the Sheet, then read it back.
    sync.py --project <name> --status   print the link and the headline counts.
"""
import argparse
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
# Where the OAuth client (credentials.json) and the minted token live. Override with
# PLAN_STATUS_GOOGLE_DIR; mint_token.py reads the same variable.
GOOGLE_DIR = Path(os.environ.get("PLAN_STATUS_GOOGLE_DIR")
                  or "~/.config/plan-status-sheet").expanduser()
TOKEN = str(GOOGLE_DIR / "sheets_token.json")
CONFIG_NAME = "plan_status_config.py"
ID_NAME = "plan_status_gsheet.json"

# The ten columns every project shares. A project may append its own columns; it may not
# reorder or drop these, because the summary and the guards below read them by position.
BASE_HEADERS = ["Plan section", "Feature", "What it does", "Status", "Date implemented",
                "Dependencies: what must happen first", "Plan phase",
                "Plan's budget for the phase", "Build effort", "Where it stands today"]

STATUS_ORDER = ["Live", "Implemented, not live", "Testing", "In implementation",
                "Not started"]

# The colour for each status. The names live above in STATUS_ORDER, so the names and
# their colours have one owner between them. A data module that defines STATUS_STYLE
# still wins, for a project whose own generator reads it.
# (fill, text) as ARGB.
DEFAULT_STATUS_STYLE = {
    "Live": ("FF1E7A3C", "FFFFFFFF"),
    "Implemented, not live": ("FFDDEBF7", "FF1F3864"),
    "Testing": ("FFFFF2CC", "FF7F6000"),
    "In implementation": ("FFFCE4D6", "FF833C00"),
    "Not started": ("FFF2F2F2", "FF595959"),
}

ENABLE_URL = "https://console.cloud.google.com/flows/enableapi?apiid=sheets.googleapis.com"


# ------------------------------------------------------------------ loading a project

def project_dir(name: str) -> Path:
    """Resolve a project by name or path. Never string-build a path and assume it exists."""
    candidate = Path(name).expanduser()
    if candidate.is_dir():
        return candidate.resolve()
    exact = PROJECTS / name
    if exact.is_dir():
        return exact.resolve()
    if not PROJECTS.is_dir():
        raise SystemExit(f"no project matching {name!r}: {PROJECTS} does not exist")
    matches = [p for p in PROJECTS.iterdir()
               if p.is_dir() and name.lower() in p.name.lower()]
    if len(matches) == 1:
        return matches[0].resolve()
    if not matches:
        raise SystemExit(f"no project matching {name!r} under {PROJECTS}")
    raise SystemExit(f"{name!r} matches {len(matches)} projects: "
                     + ", ".join(sorted(p.name for p in matches)))


NO_SHEET_FOR_REPO = 3   # a distinct exit code so a caller can say "skipped", not "failed"


def project_for_repo(repo: str):
    """Find the project whose config declares this repository.

    The link is DECLARED, never inferred from names. A project data folder is often
    named differently from its repository, and several repositories come in near
    identical pairs, so a name match would eventually pick the wrong one and write one
    project's status into another project's Sheet.
    """
    wanted = _repo_identity(repo)
    matches = []
    for config in sorted(PROJECTS.glob(f"*/{CONFIG_NAME}")):
        try:
            module = load_module(config, f"probe_{config.parent.name}")
        except Exception:  # noqa: BLE001 - a broken config must not break the search
            continue
        if wanted in _declared_repos(module):
            matches.append(config.parent)
    if len(matches) == 1:
        return matches[0].name
    if not matches:
        return None
    raise SystemExit(f"{len(matches)} projects claim {wanted}: "
                     + ", ".join(p.name for p in matches))


def _repo_identity(path) -> Path:
    """The main checkout of the repository `path` sits in, so a git WORKTREE (or a
    subfolder) of a declared repository matches it.
    A path that is not in a
    git repository is compared as itself."""
    p = Path(path).expanduser().resolve()
    try:
        out = subprocess.run(["git", "-C", str(p), "rev-parse", "--path-format=absolute",
                              "--git-common-dir"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return p
    common = out.stdout.strip()
    if out.returncode != 0 or not common:
        return p
    common = Path(common).resolve()
    return common.parent if common.name == ".git" else p


def _declared_repos(module) -> set:
    """REPO plus HAND_UPDATED_REPOS: every repository whose releases move this Sheet."""
    declared = [getattr(module, "REPO", None)] + list(
        getattr(module, "HAND_UPDATED_REPOS", None) or ())
    return {_repo_identity(d) for d in declared if d}


def hand_updated(repo: str, project_name: str) -> bool:
    """True when the project keeps this repository's rows by hand, not from its git."""
    module = load_module(PROJECTS / project_name / CONFIG_NAME, f"hand_{project_name}")
    wanted = _repo_identity(repo)
    return wanted in {_repo_identity(d)
                      for d in (getattr(module, "HAND_UPDATED_REPOS", None) or ())}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def literal_from_source(source: Path, varname: str, namespace: dict):
    """Recover a string a generator builds inline, such as its title or its note banner.

    Those live inside the generator's main() and cannot be imported. Copying them into
    the skill would make a second copy of one sentence, and the copies would drift, so
    this reads the ORIGINAL out of the source. It walks the syntax tree rather than
    matching text, so rewrapping a paragraph does not break it, and it insists on
    EXACTLY ONE match, because a silent zero would print an empty banner that reads
    like a design choice.
    """
    import ast
    tree = ast.parse(source.read_text())
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        if not any(isinstance(t, ast.Name) and t.id == varname for t in node.targets):
            continue
        found += [k.value for k in node.value.keywords if k.arg == "value"]
    if len(found) != 1:
        return None
    expression = ast.Expression(body=found[0])
    ast.fix_missing_locations(expression)
    return eval(compile(expression, str(source), "eval"), dict(namespace))  # noqa: S307


ASK_WHICH_INITIATIVE = 4   # more than one, and none named: the caller must ask


# A plan header line naming the plan this one continues. The chain is read from the
# header rather than from a field somebody would have to add to every file.
CONTINUES = re.compile(r"^\s*\*\*Plan it continues:\*\*\s*(.+?)\s*$", re.M)
PLAN_TITLE = re.compile(r"^#\s+(.+?)\s*$", re.M)
SHEET_LINK = re.compile(r"^\s*\*\*Status sheet:\*\*\s*(\S+)", re.M)


def plan_title(path: Path):
    """The plan's own H1. A generated filename says nothing to a reader.

    Plan files often carry generated names, so a picker listing filenames is
    unusable. The title is what a person recognises.
    """
    try:
        found = PLAN_TITLE.search(path.read_text())
    except OSError:
        return None
    return found.group(1) if found else None


def plan_continues(path: Path):
    """The plan this one supersedes, as a resolved Path, or None."""
    try:
        found = CONTINUES.search(path.read_text())
    except OSError:
        return None
    if not found:
        return None
    raw = found.group(1)
    # the line often carries a parenthetical after the path: take the first bare token
    token = raw.split("(")[0].strip().strip("`").strip()
    if not token:
        return None
    candidate = Path(token).expanduser()
    if not candidate.is_absolute():
        candidate = (path.parent / candidate)
    try:
        return candidate.resolve()
    except OSError:
        return None


def superseded_plans(plans):
    """Every plan that some OTHER plan says it continues.

    A file named by another file's chain is an ANCESTOR. It is never a valid target:
    pointing a push at an old version would rewrite the Sheet against a plan that
    was replaced since.
    """
    out = set()
    for p in plans:
        ancestor = plan_continues(p)
        if ancestor is not None:
            out.add(ancestor)
    return out


class Initiative:
    """One tracked body of work, and the Sheet that belongs to it.

    The Sheet is keyed to the INITIATIVE and not to a filename, so the link survives every
    rewrite of that initiative's plan. That is what keeps "one address that never changes"
    true while a project tracks more than one thing.
    """

    def __init__(self, project, name, plan_name, rows_attr=None):
        self.project = project
        self.name = name
        self.plan_name = plan_name
        self.rows_attr = rows_attr
        self.plan = (project.dir / plan_name) if plan_name else None

    @property
    def title(self):
        return (plan_title(self.plan) if self.plan and self.plan.is_file() else None) or self.name

    def __repr__(self):
        return f"<Initiative {self.name!r} plan={self.plan_name!r}>"


# --------------------------------------------------------------- the derived columns
#
# The facts that rot get buried in the "Where it stands today" prose: a commit, a pull
# request number, a suite count. Prose cannot be checked; a column can. So the branch,
# its state and its commit come from git and gh at push time, and the prose keeps only
# judgement.
#
# The suite count deliberately stays hand-written. It comes from RUNNING tests, not from
# git, and deriving a number nobody measured would be worse than leaving it typed.

DERIVED_HEADERS = ["Branch or PR", "PR state", "Head commit", "On main"]
GIT_TIMEOUT = 20


def _run(args, cwd=None):
    """(exit code, output). Never raises: a missing tool is a fact to report, not a crash.

    It returns the CODE, not a boolean. `git merge-base --is-ancestor` answers "no" with
    exit 1 and "I could not tell you" with 128, and a boolean would report a missing
    `main` branch as a confident "not merged". Code -1 means the process never
    ran at all, which is a third thing again.
    """
    import subprocess
    try:
        done = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                              timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return -1, ""
    return done.returncode, (done.stdout or "").strip()


def repo_facts(repo, branch):
    """What git and gh say about one branch, right now.

    Every field falls back to a word that says the lookup did not answer, never to a blank
    that reads like a real absence. "unknown" and "not found" are different facts and a
    reader has to be able to tell them apart.
    """
    out = {"branch": branch, "state": "unknown", "head": "unknown", "on_main": "unknown"}
    if not repo or not Path(repo).expanduser().is_dir():
        out["state"] = "no repo"
        return out
    root = str(Path(repo).expanduser())
    # 128 means "git refused", which covers BOTH a missing branch and a directory that is
    # not a repository. Only the first is an answer, so settle which it is FIRST rather
    # than reporting "not found" about a branch in a place that has no branches.
    inrepo, _ = _run(["git", "-C", root, "rev-parse", "--git-dir"], cwd=root)
    if inrepo != 0:
        out["state"] = "no repo"
        return out
    # git distinguishes "this branch does not exist" (128) from "git could not run" (-1),
    # and only the first is an ANSWER. The second must stay unknown: absence of a lookup
    # is not evidence of absence in the repository.
    code, head = _run(["git", "-C", root, "log", "-1", "--format=%h %ad", "--date=short",
                       branch], cwd=root)
    if code == 0 and head:
        out["head"] = head
    elif code == 128:
        out["head"] = "not found"
    else:
        out["head"] = "unknown"
    if code == 0 and head:
        anc, _ = _run(["git", "-C", root, "merge-base", "--is-ancestor", branch, "main"],
                      cwd=root)
        # 0 is an ancestor, 1 is not, anything else (128 for a missing main, -1 for no git)
        # could not tell us and must not be reported as "no".
        if anc == 0:
            out["on_main"] = "yes"
        elif anc == 1:
            out["on_main"] = "no"
        else:
            out["on_main"] = "unknown"
        out["_ancestor"] = anc == 0
    code, slug = _run(["git", "-C", root, "remote", "get-url", "origin"], cwd=root)
    if code == 0 and slug:
        slug = slug.rstrip("/").removesuffix(".git")
        slug = slug.split("github.com")[-1].lstrip(":/")
        code, state = _run(["gh", "pr", "list", "-R", slug, "--head", branch, "--state",
                            "all", "--limit", "1", "--json", "number,state"])
        if code == 0:
            try:
                found = json.loads(state or "[]")
            except json.JSONDecodeError:
                # gh exited 0 and handed back something that is not JSON. That is a broken
                # lookup, not an empty result, and calling it "no PR" would assert an
                # absence nobody established.
                out["state"] = "unknown"
                found = None
            if found is None:
                return out
            # Parse the JSON: an empty list is the only honest way to say "no pull request".
            out["state"] = (f"{found[0]['state'].lower()} #{found[0]['number']}"
                            if found else "no PR")
    # A SQUASH merge rewrites the commits, so a merged branch is never an ancestor of main
    # and the ancestry test reports "no" about work that shipped weeks ago. The pull
    # request is the authority on whether the CONTENT landed; ancestry only answers it for
    # a fast-forward.
    if out["state"].startswith("merged"):
        out["on_main"] = "yes (squashed)" if not out.get("_ancestor") else "yes"
    out.pop("_ancestor", None)
    return out


def derived_columns(project):
    """(headers, {feature: [cells]}) for a project that declares SOURCES, else ([], {}).

    SOURCES maps a feature name to the branch that carries it:
        SOURCES = {"1.4 Export to CSV": "feat/csv-export"}
    A feature with no entry gets blanks, because inventing a branch for it would be worse
    than saying nothing.
    """
    sources = getattr(project.data, "SOURCES", None)
    if not sources:
        return [], {}
    repo = getattr(project.config, "REPO", None)
    cells = {}
    for feature, branch in sources.items():
        facts = repo_facts(repo, branch)
        cells[feature] = [facts["branch"], facts["state"], facts["head"], facts["on_main"]]
    return list(DERIVED_HEADERS), cells


def default_sheet_rows(data, data_module: str):
    """Map a project's ROWS onto the ten shared columns. The default for every project.

    One owner, so per-project copies cannot drift apart. A config may still define
    its own `sheet_rows` and it wins, but a project whose shape is the normal one
    carries no copy.

    The shape is eight fields per row plus a DATES map keyed by feature name. A MISSING
    entry is an error rather than a blank, because blank already means "nothing has
    happened to this row", so letting an unlisted feature render as one would report
    shipped work as untouched.
    """
    rows = []
    for section, feature, what, status, phase, effort, where, depends in data.ROWS:
        if feature not in data.DATES:
            raise SystemExit(
                f"no date recorded for {feature!r}: add it to DATES in {data_module}, "
                f"and read it from a commit or a deploy rather than recalling it")
        rows.append([section, feature, what, status, data.DATES[feature], depends,
                     phase, data.PHASE_BUDGET.get(phase, ""), effort, where])
    return rows


class Project:
    """Everything the engine needs about one project, resolved from its config file."""

    def __init__(self, name: str):
        self.dir = project_dir(name)
        self.name = self.dir.name
        config_path = self.dir / CONFIG_NAME
        if not config_path.is_file():
            raise SystemExit(
                f"{self.name} has no {CONFIG_NAME}.\n"
                f"Run --setup to scaffold one, or write it by hand: it names the module "
                f"holding ROWS, the plan file, the Sheet title, and how a row maps onto "
                f"the ten columns.")
        self.config = load_module(config_path, "plan_status_config")
        data_path = self.dir / self.config.DATA_MODULE
        if not data_path.is_file():
            raise SystemExit(f"{CONFIG_NAME} names {self.config.DATA_MODULE}, "
                             f"which is not in {self.dir}")
        self.data_path = data_path
        self.data = load_module(data_path, "plan_status_data")
        self.id_file = self.dir / ID_NAME

    @property
    def status_style(self):
        """The status colours: the data module's if it declares them, else the skill's."""
        return dict(getattr(self.data, "STATUS_STYLE", None) or DEFAULT_STATUS_STYLE)

    @property
    def headers(self):
        """The ten shared columns, plus the derived ones when the project declares SOURCES.

        Appending is allowed; reordering or dropping the ten is not, because the summary
        reads them by position. check_schema asserts that.
        """
        base = list(getattr(self.data, "HEADERS", BASE_HEADERS))
        if getattr(self.data, "SOURCES", None):
            base = base + list(DERIVED_HEADERS)
        return base

    @property
    def rows(self):
        """Every row as a list aligned to headers.

        The skill owns the mapping. A config that defines its own `sheet_rows` overrides
        it, for a project whose row shape genuinely differs.
        """
        adapter = getattr(self.config, "sheet_rows", None)
        if adapter is not None:
            return self._with_derived([list(r) for r in adapter(self.data)])
        # An initiative may name its own ROWS attribute, so one data module can hold two
        # tracked bodies of work without either pretending to be the other.
        active = getattr(self, "active", None)
        attr = (active.rows_attr if active is not None and active.rows_attr else "ROWS")
        if not hasattr(self.data, attr):
            raise SystemExit(f"{self.config.DATA_MODULE} has no {attr!r}, which "
                             f"initiative {getattr(active, 'name', 'default')!r} names")
        rows = getattr(self.data, attr)
        dates_attr = f"DATES_{attr[5:]}" if attr.startswith("ROWS_") else "DATES"
        dates = getattr(self.data, dates_attr, None)
        if dates is None:
            raise SystemExit(f"{self.config.DATA_MODULE} has {attr!r} but no "
                             f"{dates_attr!r}; a missing date map cannot be a blank one")
        shim = type("RowsView", (), {"ROWS": rows, "DATES": dates,
                                     "PHASE_BUDGET": self.data.PHASE_BUDGET})
        out = [list(r) for r in default_sheet_rows(shim, self.config.DATA_MODULE)]
        return self._with_derived(out)

    def _with_derived(self, out):
        """Append the git-derived cells, once per push, cached so N rows are not N lookups
        of the same branch."""
        if not getattr(self.data, "SOURCES", None):
            return out
        if getattr(self, "_derived_cache", None) is None:
            _, self._derived_cache = derived_columns(self)
        blank = [""] * len(DERIVED_HEADERS)
        return [row + list(self._derived_cache.get(str(row[1]).strip(), blank))
                for row in out]

    @property
    def plan_path(self):
        """The plan of the ACTIVE initiative, or the project's single PLAN."""
        active = getattr(self, "active", None)
        if active is not None and active.plan_name:
            return self.dir / active.plan_name
        name = getattr(self.config, "PLAN", None) or getattr(self.data, "PLAN", None)
        return (self.dir / name) if name else None

    @property
    def doc_title(self):
        return for_initiative(self, "DOC_TITLE", f"{self.name}: plan status")

    def banner(self):
        """(title, note) for the top of the grid, from the config or from the source."""
        title = getattr(self.config, "TITLE", None)
        note = getattr(self.config, "NOTE", None)
        namespace = {"PLAN": getattr(self.data, "PLAN", "")}
        if title is None:
            title = literal_from_source(self.data_path, "title", namespace) or ""
        if note is None:
            note = literal_from_source(self.data_path, "note", namespace) or ""
        return title, note

    # ------------------------------------------------------------------- initiatives
    #
    # A project tracks one BODY OF WORK per Sheet. One folder can hold several versions
    # of one initiative's plan next to a different initiative altogether. Versions must
    # share a Sheet; initiatives must not. So the key is the initiative's NAME, never a
    # filename, and the link survives every plan rewrite.

    @property
    def initiatives(self):
        """Every initiative this project tracks, in config order.

        A config with no INITIATIVES declares one, synthesized from PLAN, so a
        single-plan config needs no edit and keeps its existing link.
        """
        declared = getattr(self.config, "INITIATIVES", None)
        if not declared:
            return [Initiative(self, "default", getattr(self.config, "PLAN", None))]
        out = []
        for entry in declared:
            if not isinstance(entry, dict) or "name" not in entry:
                raise SystemExit("each INITIATIVES entry needs at least a 'name' and a "
                                 f"'plan'; got {entry!r}")
            out.append(Initiative(self, entry["name"], entry.get("plan"),
                                  entry.get("rows")))
        names = [i.name for i in out]
        if len(names) != len(set(names)):
            raise SystemExit(f"two initiatives share a name in {CONFIG_NAME}: {names}")
        return out

    def superseded(self):
        """Plan files that ANY plan in this project says it continues.

        Scanning only the plans listed in INITIATIVES cannot work: when a config points
        at an OLD plan, the plan that supersedes it is precisely the one nobody listed.

        So the scan reads the project's own markdown, not the config's opinion of it. Only
        files carrying the phrase are opened, so the cost is one cheap read per file.
        """
        candidates = [i.plan for i in self.initiatives if i.plan and i.plan.is_file()]
        for path in sorted(self.dir.glob("*.md")):
            if path not in candidates:
                candidates.append(path)
        return superseded_plans(candidates)

    def resolve_initiative(self, wanted=None):
        """Pick one. With several and none named, this REFUSES rather than guessing."""
        options = self.initiatives
        stale = self.superseded()

        def refuse_if_stale(i):
            """Refuse only the initiative actually SELECTED.

            A stale sibling is worth a warning; it is not a reason to stop work on a
            different body of work.
            """
            if i.plan is not None and i.plan.resolve() in stale:
                raise SystemExit(
                    f"initiative {i.name!r} points at {i.plan.name}, which another plan "
                    f"in this project says it CONTINUES. That file is an ancestor, not the "
                    f"current plan. Point it at the plan that supersedes it.")
            return i

        for other in options:
            if other.plan is not None and other.plan.resolve() in stale and other.name != wanted:
                print(f"    WARN  initiative {other.name!r} points at a superseded plan "
                      f"({other.plan.name}); it will be refused if you select it.")
        if len(options) == 1 and wanted in (None, options[0].name):
            return refuse_if_stale(options[0])
        if wanted is not None:
            match = [i for i in options if i.name == wanted]
            if not match:
                raise SystemExit(f"no initiative named {wanted!r}. This project tracks: "
                                 + ", ".join(i.name for i in options))
            return refuse_if_stale(match[0])
        self.print_initiatives()
        raise SystemExit(ASK_WHICH_INITIATIVE)

    def print_initiatives(self):
        """The picker. Never a bare file list: a generated plan name means nothing."""
        stale = self.superseded()
        print(f"{self.name} tracks {len(self.initiatives)} initiatives. "
              f"Name one with --initiative <name>.")
        for i in self.initiatives:
            link = self.url(i) or "no Sheet yet"
            when = ""
            if i.plan is not None and i.plan.is_file():
                when = datetime.date.fromtimestamp(i.plan.stat().st_mtime).isoformat()
            behind = len([p for p in stale if p != (i.plan.resolve() if i.plan else None)])
            print(f"    {i.name}")
            print(f"        {i.title}")
            print(f"        plan  {i.plan_name or '(none)'}  {when}")
            print(f"        sheet {link}")
            if behind:
                print(f"        {behind} superseded version(s) behind it")

    # ------------------------------------------------------------- the Sheet id per one

    def _ids(self):
        if not self.id_file.is_file():
            return {}
        return json.loads(self.id_file.read_text())

    def spreadsheet_id(self, initiative=None):
        """The Sheet id for one initiative.

        Two shapes on disk. The original is a bare {"spreadsheetId": ...} written before
        initiatives existed, and it belongs to the default initiative; reading it that way
        is what stops existing links moving. The newer shape keys ids by name.
        """
        data = self._ids()
        if not data:
            return None
        # Fall back to the ACTIVE initiative, exactly as url() does, so every internal
        # caller that passes no argument looks under the same key as the printed link.
        if initiative is None:
            initiative = getattr(self, "active", None)
        name = initiative.name if initiative is not None else "default"
        by_name = data.get("initiatives") or {}
        if name in by_name:
            return by_name[name].get("spreadsheetId")
        if name == "default":
            return data.get("spreadsheetId")
        return None

    def record_id(self, sheet_id, initiative=None):
        """Write one initiative's id without disturbing any other's."""
        data = self._ids()
        name = initiative.name if initiative is not None else "default"
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
        if name == "default" and "initiatives" not in data:
            data = {"spreadsheetId": sheet_id, "url": url}
        else:
            data.setdefault("initiatives", {})[name] = {"spreadsheetId": sheet_id,
                                                        "url": url}
        self.id_file.write_text(json.dumps(data, indent=2) + "\n")
        return url

    def url(self, initiative=None):
        sid = self.spreadsheet_id(initiative if initiative is not None
                                  else getattr(self, "active", None))
        return f"https://docs.google.com/spreadsheets/d/{sid}/edit" if sid else None


# ------------------------------------------------------------------ the offline checks

SECTION_NUMBER = re.compile(r"^#{2,3}\s+(\d+(?:\.\d+)*)\.?\s")
NUMBER_TOKEN = re.compile(r"\d+(?:\.\d+)*")


def for_initiative(project, attr, default=None):
    """A config value declared once for the project, or once per initiative.

    The flat form keeps working unchanged. A project tracking several initiatives
    may instead declare the value as a dict keyed by initiative NAME, because a
    second plan has its own excused sections, its own pinned cell and its own Sheet
    title: the first plan's pin names a row the second plan does not have, and its
    excuse list carries reasons under the second plan's section numbers.

    The two dict shapes are told apart by their KEYS: a per-initiative dict's keys are all
    names the project declares (or "default"), while a flat SECTIONS_WITHOUT_ROWS maps
    section numbers, which no initiative is called.
    """
    value = getattr(project.config, attr, default)
    if isinstance(value, dict) and value:
        names = {i.name for i in getattr(project, "initiatives", [])} | {"default"}
        if set(value) <= names:
            active = getattr(project, "active", None)
            name = active.name if active is not None else "default"
            return value.get(name, value.get("default", default))
    return value


def plan_sections(plan: Path):
    """Every NUMBERED heading in the plan, in order, as (number, heading text).

    Unnumbered headings are skipped on purpose. A plan opens with narrative sections
    that describe the problem rather than name a feature, and reporting those as missing
    rows would make this check cry wolf on every run until somebody switched it off.
    """
    if not plan or not plan.is_file():
        return []
    out = []
    for line in plan.read_text().splitlines():
        match = SECTION_NUMBER.match(line)
        if match:
            out.append((match.group(1), line.lstrip("#").strip()))
    return out


def covered_numbers(section_values):
    """Which plan numbers the rows claim to cover, ranges expanded.

    A section cell is free text, so it holds things like '4.1-4.3', '18 / Phase 6' and
    'new'. Every number inside it counts, and a simple 'X.a-X.b' range counts as every
    number between its ends. Anything with no number in it covers no plan section, which
    is correct: 'new', 'open' and 'needed' rows are work the plan never named.
    """
    covered = set()
    for value in section_values:
        text = str(value)
        for part in re.split(r"[/,]", text):
            span = re.match(r"\s*(\d+)\.(\d+)\s*-\s*(?:(\d+)\.)?(\d+)\s*$", part)
            if span:
                major, first, other_major, last = span.groups()
                if other_major in (None, major):
                    for n in range(int(first), int(last) + 1):
                        covered.add(f"{major}.{n}")
                    covered.add(major)
                    continue
            for token in NUMBER_TOKEN.findall(part):
                covered.add(token)
                if "." in token:
                    covered.add(token.split(".")[0])
    return covered


def check_plan_coverage(project, report):
    plan = project.plan_path
    if plan is None or not plan.is_file():
        report.warn(f"no plan file found, so plan coverage was NOT checked "
                    f"(config names {getattr(project.config, 'PLAN', None)!r})")
        return
    sections = plan_sections(plan)
    report.note(f"plan {plan.name}: {len(sections)} numbered sections")
    if not sections:
        report.warn("the plan has no numbered headings, so coverage cannot be measured")
        return
    covered = covered_numbers(r[0] for r in project.rows)
    # A section deliberately without a row is declared once in the config, with a reason.
    # That is what keeps this check quiet enough to stay switched on.
    excused = dict(for_initiative(project, "SECTIONS_WITHOUT_ROWS", {}) or {})
    missing = [(n, t) for n, t in sections if n not in covered and n not in excused]
    stale = [n for n in excused if n in covered]
    report.count("plan sections with no row", len(missing))
    for number, text in missing:
        report.item(f"section {number}: {text}")
    for number in stale:
        report.warn(f"section {number} is excused in {CONFIG_NAME} but a row now covers "
                    f"it; delete the excuse so it stops hiding a real gap")


def check_dates(project, report):
    """A date is a claim about a record. These catch the claims that cannot be true."""
    today = datetime.date.today()
    rows = project.rows
    blank = future = malformed = 0
    for row in rows:
        value = str(row[4] or "").strip()
        if not value:
            blank += 1
            continue
        try:
            when = datetime.date.fromisoformat(value)
        except ValueError:
            malformed += 1
            report.fail(f"{row[1]!r} has a date that is not a real date: {value!r}")
            continue
        if when > today:
            future += 1
            report.fail(f"{row[1]!r} is dated {value}, which is in the future. "
                        f"A date must be READ from a commit or a deploy, never recalled.")
    report.note(f"dates: {len(rows) - blank} carried, {blank} deliberately blank, "
                f"{malformed} malformed, {future} in the future")


def check_schema(project, report):
    headers = project.headers
    rows = project.rows
    if headers[:len(BASE_HEADERS)] != BASE_HEADERS:
        report.fail("the first ten headers are not the shared set. A project may APPEND "
                    "columns; it may not reorder or drop these.")
        for got, want in zip(headers, BASE_HEADERS):
            if got != want:
                report.item(f"got {got!r}, expected {want!r}")
    widths = {len(r) for r in rows}
    if widths != {len(headers)}:
        report.fail(f"rows are not all {len(headers)} wide: found widths {sorted(widths)}")
    statuses = {str(r[3]) for r in rows}
    unknown = statuses - set(project.status_style)
    if unknown:
        report.fail(f"status values with no colour: {sorted(unknown)}")
    off_scale = statuses - set(STATUS_ORDER)
    if off_scale:
        report.warn(f"status values outside the shared scale, so the summary will not "
                    f"count them: {sorted(off_scale)}")
    report.note(f"{len(rows)} rows, {len(headers)} columns, "
                f"{len(statuses)} distinct statuses")


# ------------------------------------------------------------------ reporting

class Report:
    def __init__(self):
        self.failures = []
        self.warnings = []

    def note(self, text):
        print(f"    {text}")

    def item(self, text):
        print(f"      - {text}")

    def count(self, label, number):
        print(f"    {label}: {number}")

    def warn(self, text):
        self.warnings.append(text)
        print(f"    WARN  {text}")

    def fail(self, text):
        self.failures.append(text)
        print(f"    FAIL  {text}")

    def verdict(self):
        if self.failures:
            print(f"\n{len(self.failures)} problem(s) must be fixed before pushing.")
            return 1
        if self.warnings:
            print(f"\nno blocking problems; {len(self.warnings)} thing(s) to look at.")
            return 0
        print("\nclean.")
        return 0


# ------------------------------------------------------------------ cells and colours

def rgb(argb: str) -> dict:
    hexpart = argb[2:] if len(argb) == 8 else argb
    r, g, b = (int(hexpart[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return {"red": r, "green": g, "blue": b}


GREY = {"style": "SOLID", "color": rgb("FFBFBFBF")}
BORDERS = {side: GREY for side in ("top", "bottom", "left", "right")}


def cell(value, *, bold=False, italic=False, size=10, colour=None, fill=None,
         halign="LEFT", valign="TOP", borders=True):
    fmt = {"textFormat": {"bold": bold, "italic": italic, "fontSize": size},
           "horizontalAlignment": halign, "verticalAlignment": valign,
           "wrapStrategy": "WRAP"}
    if colour:
        fmt["textFormat"]["foregroundColor"] = rgb(colour)
    if fill:
        fmt["backgroundColor"] = rgb(fill)
    if borders:
        fmt["borders"] = BORDERS
    return {"userEnteredValue": {"stringValue": "" if value is None else str(value)},
            "userEnteredFormat": fmt}


def number_cell(value, *, bold=False):
    return {"userEnteredValue": {"numberValue": float(value)},
            "userEnteredFormat": {"textFormat": {"bold": bold, "fontSize": 10}}}


# ------------------------------------------------------------------ the two tabs

def grid_rows(project):
    headers = project.headers
    title, note = project.banner()
    style = project.status_style
    blank = lambda: cell("", borders=False)  # noqa: E731

    # THE BANNER STARTS AT COLUMN C, and that is not a style choice. Google refuses a
    # merge that crosses the frozen-column line, and the first two columns are frozen so
    # the section and the feature name stay on screen while you read the wide columns on
    # the right. Keeping the merge inside the unfrozen block buys both.
    out = [[blank(), blank(),
            cell(title, bold=True, size=14, borders=False, valign="MIDDLE")]
           + [blank() for _ in headers[3:]],
           [blank(), blank(),
            cell(note, italic=True, colour="FF595959", borders=False)]
           + [blank() for _ in headers[3:]],
           [blank() for _ in headers],
           [cell(name, bold=True, colour="FFFFFFFF", fill="FF1F3864", valign="MIDDLE")
            for name in headers]]

    for row in project.rows:
        fill, colour = style[str(row[3])]
        line = [cell(row[0], bold=True, halign="CENTER", valign="MIDDLE"),
                cell(row[1], bold=True),
                cell(row[2]),
                cell(row[3], bold=True, colour=colour, fill=fill,
                     halign="CENTER", valign="MIDDLE"),
                cell(row[4], halign="CENTER", valign="MIDDLE"),
                cell(row[5]),
                cell(row[6], halign="CENTER", valign="MIDDLE"),
                cell(row[7], halign="CENTER", valign="MIDDLE"),
                cell(row[8], halign="CENTER", valign="MIDDLE"),
                cell(row[9])]
        line += [cell(value) for value in row[10:]]
        out.append(line)
    return out


def summary_rows(project):
    rows = project.rows
    style = project.status_style
    counts = {}
    for row in rows:
        counts[str(row[3])] = counts.get(str(row[3]), 0) + 1

    out = [[cell("Status", bold=True, borders=False),
            cell("Features", bold=True, borders=False)]]
    for status in STATUS_ORDER:
        fill, colour = style.get(status, ("FFF2F2F2", "FF595959"))
        out.append([cell(status, bold=True, colour=colour, fill=fill, borders=False),
                    number_cell(counts.get(status, 0))])
    out.append([cell("Total", bold=True, borders=False),
                number_cell(len(rows), bold=True)])

    unfinished = ("Testing", "In implementation", "Not started")
    remaining = sum(float(str(row[8]).split()[0]) for row in rows
                    if str(row[3]) in unfinished and str(row[8])[:1].isdigit())
    blocked = [r for r in rows if str(r[5]).startswith("BLOCKED")]
    # FINISHED rows only. A not-started row whose dependency reads 'None' is not one
    # setting away, it is unwritten, and counting it here overstates what a deploy buys.
    waiting = [r for r in rows
               if str(r[3]) == "Implemented, not live" and str(r[5]).startswith("None")]
    needed = [r for r in rows if str(r[0]) == "needed"]
    dated = [r for r in rows if str(r[4] or "").strip()]

    out.append([cell("", borders=False)])
    for label, value in [
            ("Estimated days left on the unfinished rows", remaining),
            ("Finished, and one setting away", len(waiting)),
            ("Blocked by a dependency", len(blocked)),
            ("Functionality needed to unblock those", len(needed)),
            ("Rows carrying a date read from a record", len(dated))]:
        out.append([cell(label, bold=True, borders=False),
                    number_cell(value, bold=True)])

    out.append([cell("", borders=False)])
    out.append([cell("By plan phase (rows, not days)", bold=True, borders=False)])
    phases = {}
    for row in rows:
        phases[str(row[6])] = phases.get(str(row[6]), 0) + 1
    for phase, number in sorted(phases.items()):
        out.append([cell(phase, borders=False), number_cell(number)])

    out.append([cell("", borders=False)])
    stamp = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    out.append([cell(f"This Sheet was rewritten by the plan-status skill on {stamp}. "
                     f"Edit the rows in the project, never here: the next run replaces "
                     f"every cell.", italic=True, colour="FF595959", borders=False)])
    return out, counts, remaining, waiting, blocked, needed


# ------------------------------------------------------------------ talking to Google

def service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    if not os.path.isfile(TOKEN):
        raise SystemExit(
            f"no Sheets token at {TOKEN}.\n"
            f"Mint one once, in a terminal where a browser can open:\n"
            f"    python3 {Path(__file__).parent / 'mint_token.py'}")
    # NO scopes= here. A refresh-token grant's scopes are fixed at consent time, and
    # passing a list makes google-auth send it on refresh, which fails the WHOLE refresh
    # if any entry was never consented, taking down every call the token did have.
    return build("sheets", "v4", credentials=Credentials.from_authorized_user_file(TOKEN))


def explain(error) -> str:
    text = str(error)
    if "SERVICE_DISABLED" in text or "has not been used in project" in text:
        return (f"The Google Sheets API is not switched on for this Cloud project.\n"
                f"Enable it here, wait a minute, then run this again:\n    {ENABLE_URL}")
    return text


def rewrite(sheet_id, rows, widths=None, frozen_rows=0, frozen_cols=0,
            merges=(), filter_range=None):
    """Requests that replace one tab's whole contents while keeping its id, and so its URL.

    Three things here are not preference, they are rules Google enforces or ignores:

    THE ROWS ARE DROPPED AND REGROWN, so no row keeps a fixed height. A fixed height is
    what clips wrapped text, and Google's own 'fit rows to data' request is INERT for
    wrapped text: a long wrapped cell comes back at the default one-line height.
    Setting no height at all is the only thing that
    leaves the browser free to grow the row.

    THE FREEZE IS CLEARED IN ITS OWN REQUEST FIRST, because Google refuses to delete
    every unfrozen row, and clearing the freeze in the same request is still refused.

    NO TAB IS EVER DELETED, because that changes the tab id and breaks a saved link.
    """
    height, width = len(rows), max(len(r) for r in rows)
    requests = [
        {"clearBasicFilter": {"sheetId": sheet_id}},
        {"unmergeCells": {"range": {"sheetId": sheet_id}}},
        {"updateSheetProperties": {
            "properties": {"sheetId": sheet_id,
                           "gridProperties": {"frozenRowCount": 0,
                                              "frozenColumnCount": 0}},
            "fields": ("gridProperties.frozenRowCount,"
                       "gridProperties.frozenColumnCount")}},
        {"updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"rowCount": 1}},
            "fields": "gridProperties.rowCount"}},
        {"updateSheetProperties": {
            "properties": {"sheetId": sheet_id,
                           "gridProperties": {"rowCount": max(height, 1),
                                              "columnCount": max(width, 1),
                                              "frozenRowCount": frozen_rows,
                                              "frozenColumnCount": frozen_cols}},
            "fields": ("gridProperties.rowCount,gridProperties.columnCount,"
                       "gridProperties.frozenRowCount,"
                       "gridProperties.frozenColumnCount")}},
        {"updateCells": {
            "rows": [{"values": r + [cell("", borders=False)] * (width - len(r))}
                     for r in rows],
            "fields": "userEnteredValue,userEnteredFormat",
            "start": {"sheetId": sheet_id, "rowIndex": 0, "columnIndex": 0}}},
    ]
    for start, end, pixels in (widths or []):
        requests.append({"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                      "startIndex": start, "endIndex": end},
            "properties": {"pixelSize": pixels}, "fields": "pixelSize"}})
    for row_start, row_end, col_start, col_end in merges:
        requests.append({"mergeCells": {
            "range": {"sheetId": sheet_id, "startRowIndex": row_start,
                      "endRowIndex": row_end, "startColumnIndex": col_start,
                      "endColumnIndex": col_end}, "mergeType": "MERGE_ALL"}})
    if filter_range:
        row_start, row_end, col_start, col_end = filter_range
        requests.append({"setBasicFilter": {"filter": {"range": {
            "sheetId": sheet_id, "startRowIndex": row_start, "endRowIndex": row_end,
            "startColumnIndex": col_start, "endColumnIndex": col_end}}}})
    return requests


GRID_TAB = "Plan status"
SUMMARY_TAB = "Summary"


def tabs_for(project):
    """A project may keep its own tab names, and an existing Sheet must keep the ones it
    has. Renaming a tab is not cosmetic here: it changes the tab id, so a link somebody
    saved to a tab stops working, and the old tab would be left behind holding a stale
    copy of the same table.

    Both names may also be a dict keyed by initiative name, so two initiatives can share
    ONE Sheet (one link) with a tab pair each. Two
    initiatives that share a Sheet and resolve to the same tab would overwrite each other
    on every push, so `shared_tab_clash` refuses that before anything is written."""
    return (for_initiative(project, "GRID_TAB", GRID_TAB),
            for_initiative(project, "SUMMARY_TAB", SUMMARY_TAB))


def shared_tab_clash(project):
    """Another initiative recorded on the SAME Sheet whose tabs overlap the active one's.

    Returns that initiative's name, or None. Each initiative's tabs are resolved on its
    own, so a flat GRID_TAB shared by two initiatives on one Sheet is caught as well."""
    active = getattr(project, "active", None)
    mine = project.spreadsheet_id(active)
    if not mine:
        return None
    my_tabs = set(tabs_for(project))
    for other in project.initiatives:
        if active is not None and other.name == active.name:
            continue
        if project.spreadsheet_id(other) != mine:
            continue
        project.active = other
        try:
            theirs = set(tabs_for(project))
        finally:
            project.active = active
        if my_tabs & theirs:
            return other.name
    return None


def open_sheet(svc, project, create=False):
    sid = project.spreadsheet_id()
    if sid:
        meta = svc.spreadsheets().get(spreadsheetId=sid).execute()
        return sid, {s["properties"]["title"]: s["properties"]["sheetId"]
                     for s in meta["sheets"]}
    if not create:
        raise SystemExit(f"{project.name} has no Sheet yet. Run --setup first.")
    grid_tab, summary_tab = tabs_for(project)
    made = svc.spreadsheets().create(body={
        "properties": {"title": project.doc_title},
        "sheets": [{"properties": {"title": grid_tab, "index": 0}},
                   {"properties": {"title": summary_tab, "index": 1}}]}).execute()
    sid = made["spreadsheetId"]
    project.record_id(sid, getattr(project, "active", None))
    print(f"    created the Sheet and recorded its id in {project.id_file.name} "
          f"under {getattr(getattr(project, 'active', None), 'name', 'default')!r}")
    return sid, {s["properties"]["title"]: s["properties"]["sheetId"]
                 for s in made["sheets"]}


def strangers(svc, sid, headers, tab):
    """Header names on the Sheet that this run does not write.

    The Sheet is online and easy to open, so somebody adding a column in the browser is
    the LIKELY case rather than the unlikely one, and this rewrites the whole grid.
    Refusing costs one message; a silent rebuild costs their afternoon.
    """
    from googleapiclient.errors import HttpError
    try:
        got = svc.spreadsheets().values().get(
            spreadsheetId=sid, range=f"'{tab}'!A4:ZZ4").execute()
    except HttpError:
        return []
    row = (got.get("values") or [[]])[0]
    return [name for name in row if name and name not in headers]


# ------------------------------------------------------------------ the commands

COLUMN_WIDTHS = [96, 215, 313, 152, 110, 369, 82, 96, 82, 313]


# ------------------------------------- dependencies, blockers, cross-references, pin
#
# Whether each of these fails or only warns is decided by how much existing, well-formed
# data it would stop. A check that stops every existing project on arrival is a check
# somebody switches off.

MEASURE_WORDS = ("measured", "re-measured", "remeasured", "verified", "checked")

# A quoted span with MATCHING quotes, used only to name what a dangling reference tried to
# say. Straight and curly pairs, and a name may contain the other kind of quote.
QUOTED_SPAN = re.compile(r"'([^']{2,})'|\"([^\"]{2,})\"|\u2018([^\u2019]{2,})\u2019"
                         r"|\u201c([^\u201d]{2,})\u201d")

# "not checked since", "never measured", "no longer verified": the measurement word is
# present and the sentence says the opposite. A window is enough, because the negation
# always sits immediately before the word it negates.
# The negation must sit IMMEDIATELY before the measurement word, with at most two
# fillers in between. "THE OLD REASONS NO LONGER HOLD, measured <date>" is well formed:
# its "no longer" negates HOLD, not "measured", and a wider window would refuse it.
NEGATED_MEASURE = re.compile(
    r"\b(?:not|never|no longer|nobody has|hasn't|has not|haven't|have not|isn't|is not)\s+"
    r"(?:(?:been|yet|ever|actually|since|recently)\s+){0,2}"
    r"(?:" + "|".join(MEASURE_WORDS) + r")\b", re.I)

# The date that belongs to the measurement is the one NEXT TO the measurement word, not
# any date in the cell: `BLOCKED until 2099-01-01; measured 2026-09-06` is well formed,
# and its first date is a target, not the measurement. The word comes FIRST and the date
# follows it (`measured <date>`, `Blocker last measured <date>`); accepting a date before
# the word would capture the target date and refuse that cell.
MEASURED_DATE = re.compile(
    r"\b(?:" + "|".join(MEASURE_WORDS) + r")\b[^0-9]{0,30}?(\d{4}-\d{2}-\d{2})", re.I)


def check_dependencies(project, report):
    """Every row says what must happen first. WARNS, and the count is why.

    Empty dependency cells are common in tables that existed before this check, so
    failing on them would block most projects on arrival. This reports the number
    and leaves the judgement with whoever reads it.
    """
    rows = project.rows
    empty = [r[1] for r in rows if not str(r[5] or "").strip()]
    report.count("rows with no dependency written", len(empty))
    if empty:
        report.warn(f"{len(empty)} of {len(rows)} rows do not say what must happen first. "
                    f"A status with no reason is a fact nobody can act on.")
        for feature in empty[:5]:
            report.item(f"no dependency: {feature}")
        if len(empty) > 5:
            report.item(f"...and {len(empty) - 5} more")


def check_blocker_measured(project, report):
    """A BLOCKED cell must say WHEN its blocker was last measured. FAILS.

    `Blocker last measured <date>` and `measured <date>` are both honest wordings, so
    matching one phrase would fail a good row. What matters is the MECHANISM: a
    measurement word and a real, non-future date. Match that, not one phrasing.
    """
    rows = project.rows
    blocked = [r for r in rows if str(r[5] or "").strip().upper().startswith("BLOCKED")]
    if not blocked:
        report.note("SKIPPED: no BLOCKED rows, so there is no blocker to date. "
                    "This project does not use that vocabulary.")
        return
    today = datetime.date.today()
    for row in blocked:
        cell = str(row[5])
        if NEGATED_MEASURE.search(cell):
            report.fail(f"{row[1]!r} says the blocker was NOT measured. The words are there "
                        f"and the sentence says the opposite; go and measure it.")
            continue
        found = [d for d in MEASURED_DATE.findall(cell) if d]
        if not found:
            report.fail(f"{row[1]!r} is BLOCKED but does not say when the blocker was last "
                        f"measured. A blocker copied forward is a claim, not a fact. Other "
                        f"dates in the cell do not count: the date must sit beside the "
                        f"measurement word.")
            continue
        bad = [d for d in found if _as_date(d) is None or _as_date(d) > today]
        if bad:
            report.fail(f"{row[1]!r} dates its MEASUREMENT {bad[0]}, which is not a real "
                        f"past date. A future target date elsewhere in the cell is fine.")
    report.count("BLOCKED rows", len(blocked))


def _as_date(value):
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def check_cross_references(project, report):
    """A blocked row names its fix, and the fix exists. FAILS on a dangling name.

    The mirror half, a `needed` row that no blocked row names, only warns.
    """
    rows = project.rows
    features = {str(r[1]).strip() for r in rows}
    blocked = [r for r in rows if str(r[5] or "").strip().upper().startswith("BLOCKED")]
    needed = [r for r in rows if str(r[0]).strip().lower() == "needed"]
    if not blocked and not needed:
        report.note("SKIPPED: no BLOCKED and no `needed` rows, so there is no "
                    "cross-reference to resolve.")
        return
    for row in blocked:
        cell = str(row[5])
        mine = str(row[1]).strip()
        # Ask whether the cell NAMES a real row, rather than whether it contains a
        # quote-shaped span. Quote matching breaks on an apostrophe inside a name, on a
        # contraction earlier in the sentence, and on a short name such as `SSO`.
        named = sorted((f for f in features if f and f != mine and f in cell),
                       key=len, reverse=True)
        if named:
            continue
        # findall over an alternation of four groups yields a 4-tuple per match, one
        # non-empty. Flatten, or the message crashes on a tuple.
        quoted = [g for match in QUOTED_SPAN.findall(cell) for g in match if g]
        if quoted:
            report.fail(f"{row[1]!r} names {quoted[0].strip()!r} as its fix and no row has "
                        f"that name. A dangling cross-reference is worse than none.")
        else:
            report.fail(f"{row[1]!r} is BLOCKED but names no row as its fix. Work out what "
                        f"would resolve it; if that needs new work, it becomes its own row.")
    unlinked = [r[1] for r in needed
                if not any(str(r[1]).strip() in str(o[5] or "") for o in rows if o is not r)]
    if unlinked:
        report.warn(f"{len(unlinked)} `needed` row(s) that no blocked row names. Write the "
                    f"link in BOTH directions or one of the two questions goes unanswered.")
        for feature in unlinked[:3]:
            report.item(f"unreferenced `needed` row: {feature}")


def report_todo_coverage(project, report):
    """Which unfinished rows the project's TODO does not mention. REPORTS, never fails.

    A feature can read done in one and not started in the other with nothing
    noticing. The two stay separate with ONE pointer between them, so the TODO stays
    the thing read daily and the Sheet stays the thing shown to other people.

    It reports rather than warns on purpose. A TODO is prose, and the same work is often
    written there in different words, so a guard keyed on the feature name would fire on
    well-formed input. A check that cries wolf is a check somebody switches off, and this
    one has to survive to be worth anything.
    """
    todo = project.dir / "TODO.md"
    if not todo.is_file():
        report.note("no TODO.md in this project, so there is nothing to cross-check")
        return
    text = todo.read_text(errors="replace").lower()
    unfinished = [r for r in project.rows if str(r[3]).strip() != "Live"]
    missing = [r[1] for r in unfinished if str(r[1]).strip().lower() not in text]
    report.count("unfinished rows the TODO does not name", len(missing))
    for feature in missing[:5]:
        report.item(f"not in TODO.md: {feature}")
    if len(missing) > 5:
        report.item(f"...and {len(missing) - 5} more")
    if missing:
        report.note("These are named in the Sheet and nowhere in the daily list. Add a "
                    "TODO item naming each, or accept that the Sheet is the only record.")


def unrecorded_prs(rows, merged, excused):
    """Numbers of merged PRs that no row names, by "PR #N" or by the first 7 characters of
    the merge commit, minus the ones `excused` lists with a reason.

    Without it, merged work can sit unrecorded while every push says "clean".
    "PR #31" must not count as naming #3, hence the lookahead.
    """
    text = "\n".join(" ".join(str(cell) for cell in r) for r in rows)
    missing = []
    for pr in merged:
        number = pr["number"]
        if number in excused:
            continue
        sha = ((pr.get("mergeCommit") or {}).get("oid") or "")[:7]
        if re.search(rf"PR #{number}(?!\d)", text) or (sha and sha in text):
            continue
        missing.append(number)
    return sorted(missing)


def _merged_prs(repo):
    """Every merged PR of the repo's origin, or None when gh could not answer."""
    root = str(Path(repo).expanduser())
    code, url = _run(["git", "-C", root, "remote", "get-url", "origin"], cwd=root)
    if code != 0 or not url:
        return None
    slug = url.rstrip("/").removesuffix(".git").split("github.com")[-1].lstrip(":/")
    code, out = _run(["gh", "pr", "list", "-R", slug, "--state", "merged", "--limit", "1000",
                      "--json", "number,mergeCommit"])
    if code != 0:
        return None
    try:
        return json.loads(out or "[]")
    except json.JSONDecodeError:
        return None


def check_released_prs(project, report, merged=None, lister=_merged_prs):
    """Every merged PR of REPO is named in some row, or listed in PRS_WITHOUT_ROWS.

    It FAILS only from the PR number in PRS_TRACKED_FROM on, so a project switches it on
    when its rows start naming PRs; without it the count is shown and nothing fails
    Runs on --push only, because --check promises no network.
    """
    repo = getattr(project.config, "REPO", None)
    if not repo:
        report.note("SKIPPED: no REPO in the config, so there are no merged PRs to match.")
        return
    if merged is None:
        merged = lister(repo)
    if merged is None:
        report.warn("could not list the merged PRs (gh or git did not answer), so the "
                    "rows were not compared with what shipped.")
        return
    excused = dict(getattr(project.config, "PRS_WITHOUT_ROWS", None) or {})
    missing = unrecorded_prs(project.rows, merged, excused)
    since = getattr(project.config, "PRS_TRACKED_FROM", None)
    if since is None:
        report.note(f"merged PRs no row names: {len(missing)} (not enforced: the config "
                    f"sets no PRS_TRACKED_FROM)")
        return
    for number in missing:
        if number >= since:
            report.fail(f"merged PR #{number} is named in no row. Add \"PR #{number}\" and its "
                        f"merge commit to the row it moved, or list it in PRS_WITHOUT_ROWS "
                        f"with a reason.")
    report.count("merged PRs checked against the rows", len(merged))


def check_pinned_control(project, report):
    """One cell whose exact text is pinned in the config. FAILS on a mismatch.

    This is the check that stops a rebuild which silently wrote an empty Sheet from
    reporting success the same way a good one does. Every other check here can pass over
    nothing at all.

    Declare it in the config as PINNED_CELL = (<feature>, <column index>, <exact text>).
    Expect it to fire when you edit the cell it pins: that is the control working. Update
    the expected text and move on.
    """
    pin = for_initiative(project, "PINNED_CELL", None)
    if pin is None:
        report.warn("SKIPPED: no PINNED_CELL in the config, so nothing proves this build "
                    "wrote real content. Add one; it is the only check here that a Sheet "
                    "rebuilt as empty cannot pass.")
        return
    try:
        feature, column, expected = pin
    except (TypeError, ValueError):
        report.fail("PINNED_CELL must be (feature, column index, exact text)")
        return
    match = [r for r in project.rows if str(r[1]).strip() == str(feature).strip()]
    if not match:
        report.fail(f"PINNED_CELL names {feature!r}, and no row has that name. The control "
                    f"is pointed at nothing, so it can no longer fail.")
        return
    got = str(match[0][column])
    if got != expected:
        report.fail(f"PINNED_CELL mismatch on {feature!r} column {column}.\n"
                    f"        expected {expected!r}\n"
                    f"        got      {got!r}")
    else:
        report.note(f"pinned control cell matches on {feature!r}")


def do_check(project, online=False):
    print(f"CHECKING {project.name}")
    report = Report()
    check_schema(project, report)
    check_dates(project, report)
    check_plan_coverage(project, report)
    check_dependencies(project, report)
    check_blocker_measured(project, report)
    check_cross_references(project, report)
    check_pinned_control(project, report)
    report_todo_coverage(project, report)
    if online:
        check_released_prs(project, report)
    url = project.url()
    print(f"    Sheet: {url}" if url else
          "    no Sheet yet for this project; run --setup")
    return report.verdict()


def push(project, create=False):
    from googleapiclient.errors import HttpError
    clash = shared_tab_clash(project)
    if clash:
        raise SystemExit(
            f"initiative {clash!r} writes the same tab of the same Sheet. Give each "
            f"initiative its own GRID_TAB and SUMMARY_TAB (a dict keyed by initiative "
            f"name) before pushing; otherwise each push overwrites the other's table.")
    svc = service()
    try:
        sid, tabs = open_sheet(svc, project, create=create)
    except HttpError as error:
        raise SystemExit(explain(error))

    grid_tab, summary_tab = tabs_for(project)
    for wanted in (grid_tab, summary_tab):
        if wanted not in tabs:
            made = svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": [
                {"addSheet": {"properties": {"title": wanted}}}]}).execute()
            tabs[wanted] = made["replies"][0]["addSheet"]["properties"]["sheetId"]

    headers = project.headers
    unknown = strangers(svc, sid, headers, grid_tab)
    if unknown and "--force" not in sys.argv:
        print(f"    REFUSING to rewrite: row 4 holds {len(unknown)} column(s) this run "
              f"does not write, so rebuilding would delete them.")
        for name in unknown:
            print(f"      {name!r}")
        print(f"    Add each to HEADERS and to the row data in the project, then run "
              f"again. Pass --force only if you mean to discard them.")
        return 1

    grid = grid_rows(project)
    summary, counts, remaining, waiting, blocked, needed = summary_rows(project)
    columns = len(headers)
    widths = [(i, i + 1, px) for i, px in enumerate(
        COLUMN_WIDTHS + [200] * (columns - len(COLUMN_WIDTHS)))]

    requests = rewrite(tabs[grid_tab], grid, widths=widths, frozen_rows=4,
                       frozen_cols=2,
                       merges=[(0, 1, 2, columns), (1, 2, 2, columns)],
                       filter_range=(3, len(grid), 0, columns))
    requests += rewrite(tabs[summary_tab], summary, widths=[(0, 1, 320), (1, 2, 90)])
    try:
        svc.spreadsheets().batchUpdate(spreadsheetId=sid,
                                       body={"requests": requests}).execute()
    except HttpError as error:
        raise SystemExit(explain(error))

    failures = read_back(svc, sid, project, grid)
    print(f"    {len(project.rows)} rows; by status: {counts}")
    print(f"    days left on unfinished rows: {remaining}")
    print(f"    one setting away: {len(waiting)}; blocked: {len(blocked)}; "
          f"needed: {len(needed)}")
    print(f"    {project.url()}")
    return 1 if failures else 0


def read_back(svc, sid, project, grid):
    """A successful write is not proof of correct content. Read the Sheet and compare.

    The comparison carries its own control: a value the Sheet cannot hold must be
    reported as different, or a checker that always agrees would look identical to one
    that works.
    """
    got = svc.spreadsheets().values().get(
        spreadsheetId=sid, range=f"'{tabs_for(project)[0]}'!A1:ZZ{len(grid)}",
        valueRenderOption="UNFORMATTED_VALUE").execute().get("values", [])

    def live(r, c):
        row = got[r] if r < len(got) else []
        return str(row[c]) if c < len(row) else ""

    differing = [(r, c) for r in range(3, len(grid))
                 for c in range(len(project.headers))
                 if grid[r][c]["userEnteredValue"]["stringValue"] != live(r, c)]
    control_fires = live(4, 1) != "A VALUE THE SHEET DOES NOT HOLD"
    print(f"    read back {len(grid) - 3} rows: {len(differing)} cell(s) differ "
          f"(control fires: {control_fires})")
    for r, c in differing[:5]:
        print(f"      row {r + 1} col {c + 1}: "
              f"sent {grid[r][c]['userEnteredValue']['stringValue'][:60]!r}, "
              f"live {live(r, c)[:60]!r}")
    if not control_fires:
        print("    FAIL the read-back control did not fire, so this comparison is "
              "not trustworthy")
        return True
    return bool(differing)


def do_status(project):
    rows = project.rows
    counts = {}
    for row in rows:
        counts[str(row[3])] = counts.get(str(row[3]), 0) + 1
    print(f"{project.name}")
    print(f"    {len(rows)} rows: " + ", ".join(
        f"{s} {counts.get(s, 0)}" for s in STATUS_ORDER if counts.get(s)))
    print(f"    {project.url() or 'no Sheet yet; run --setup'}")
    return 0


SCAFFOLD = '''"""How this project's rows map onto the shared plan-status Sheet.

The skill owns the Sheet AND the row mapping. This file owns what is project-specific:
which module holds the rows, which plan they track, and which cell is pinned.

You do NOT write `sheet_rows()`. The skill's `default_sheet_rows` is the one owner, so
per-project copies cannot drift apart. Define
`sheet_rows(data)` here ONLY if this project's row shape genuinely differs; a definition
here overrides the skill's, and an out-of-date one silently writes the wrong columns.
"""

# The module in this directory. It must hold ROWS, DATES and PHASE_BUDGET.
#
#   ROWS  = [(section, feature, what, status, phase, effort, where, depends), ...]
#   DATES = {{feature: "YYYY-MM-DD" or ""}}
#
# Eight fields per row, and the date lives in DATES rather than inline. A MISSING entry in
# DATES is an ERROR, not a blank: blank already means "nothing has happened to this row",
# so letting an unlisted feature render as one would report shipped work as untouched.
DATA_MODULE = "build_plan_status_xlsx.py"

# The plan this table tracks, in this directory. Coverage is measured against its numbered
# headings.
PLAN = None

# Tracking more than one body of work? Replace PLAN with INITIATIVES. The Sheet is then
# keyed to the initiative name, so its link survives every rewrite of that initiative's
# plan, and a run with several present and none named stops and asks.
#
#   INITIATIVES = [
#       {{"name": "first",  "plan": "FIRST_PLAN.md"}},
#       {{"name": "second", "plan": "SECOND_PLAN.md", "rows": "ROWS_SECOND"}},
#   ]

# The name of the Google Sheet, set once when it is created.
DOC_TITLE = "{title}"

# Numbered plan sections that deliberately have no row, each with the reason. This is what
# keeps the coverage check quiet enough to stay switched on. Delete an entry once a row
# covers it; the check says so when that happens.
SECTIONS_WITHOUT_ROWS = {{
    # "1": "analysis of the current system, not work to do",
}}

# REQUIRED. The anti-vacuous control: one cell whose EXACT text is pinned here. Every other
# check can pass over a Sheet rebuilt as empty; this one cannot. Expect it to fire when you
# edit the cell it pins, and treat that as the control working rather than as a fault.
# (feature name, column index, exact text)
PINNED_CELL = None

# The repository this table tracks. DECLARED, never inferred from names: repositories come
# in near-identical pairs, so a name match would eventually write one project's status into
# another project's Sheet. `sync.py --repo <path>` finds this Sheet by it.
REPO = None

# Other repositories whose work packages this Sheet also tracks, with rows updated BY HAND
# (their status is not read from git). A release in one of them finds this Sheet too and is
# told to set its rows, instead of hearing "no Sheet" and leaving them stale.
HAND_UPDATED_REPOS = ()
'''


def do_setup(project_name, initiative=None):
    directory = project_dir(project_name)
    config = directory / CONFIG_NAME
    if config.is_file():
        print(f"{config} already exists; leaving it alone.")
    else:
        title = f"{directory.name}: plan status"
        config.write_text(SCAFFOLD.format(title=title))
        print(f"wrote {config}")
        print("Open it, point DATA_MODULE and PLAN at the right files, and set "
              "PINNED_CELL and REPO. Then run --check.")
        return 0
    project = Project(project_name)
    project.active = project.resolve_initiative(initiative)
    if do_check(project) != 0:
        return 1
    return push(project, create=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project",
                        help="project name, a unique fragment of it, or a path")
    parser.add_argument("--repo",
                        help="a repository path; the project is the one whose config "
                             "declares REPO equal to it. Exits 3 when no project does, "
                             "which means this repo simply keeps no plan Sheet.")
    parser.add_argument("--initiative",
                        help="which initiative to act on, when the project tracks "
                             "more than one. Omitted with several present, the "
                             "picker prints and this exits 4 rather than guessing.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="rewrite even over columns this run does not write")
    args, _ = parser.parse_known_args()

    if args.repo and not args.project:
        found = project_for_repo(args.repo)
        if not found:
            print(f"no project keeps a plan-status Sheet for {args.repo}, so there is "
                  f"nothing to update.")
            raise SystemExit(NO_SHEET_FOR_REPO)
        args.project = found
        if hand_updated(args.repo, found):
            print(f"{args.repo} is tracked by {found}'s Sheet with HAND-UPDATED rows: set "
                  f"the rows this release moved in {PROJECTS / found / 'plan_status_rows.py'}"
                  f" (status and date), then push again.")
    if not args.project:
        parser.error("give --project or --repo")

    if args.setup:
        raise SystemExit(do_setup(args.project, args.initiative))
    project = Project(args.project)
    # Resolve BEFORE any command. With several initiatives and none named this exits 4
    # with the picker printed, which is the caller's cue to ask rather than to pick.
    project.active = project.resolve_initiative(args.initiative)
    if args.status:
        raise SystemExit(do_status(project))
    if args.check:
        raise SystemExit(do_check(project))
    if args.push:
        # A push always checks first. A Sheet built from rows that failed their own
        # checks is worse than no Sheet, because it looks authoritative.
        if do_check(project, online=True) != 0:
            print("\nnot pushing.")
            raise SystemExit(1)
        print(f"\nPUSHING {project.name}")
        raise SystemExit(push(project))
    parser.print_help()
    raise SystemExit(2)


if __name__ == "__main__":
    main()
