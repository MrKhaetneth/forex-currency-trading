# Python Imports & Packaging — Notes

Context: these notes came out of debugging `ImportError: attempted relative
import with no known parent package` in `src/mt5/demo/timeslice_return.py`,
which snowballed into restructuring the whole project as an installable
package. Written for someone with a physics background and no CS
fundamentals — so plain-language analogies over jargon where possible.

## 1. How Python finds code — the import system

- `import x` doesn't search your project folder — it searches a specific list of directories called `sys.path`.
- A "package" isn't a special thing Python recognizes by folder name; it's just a directory that's reachable via `sys.path`, either because it contains `__init__.py` (a _regular_ package) or, since Python 3.3+, just because it's sitting somewhere on `sys.path` at all (an _implicit namespace package_ — no `__init__.py` needed).

## 2. Two ways to launch a file, and why they behave differently

- `python file.py` → Python executes it as a bare script. It sets `__package__ = None`. No package context exists, so `.`/`..` (relative imports) have nothing to be relative _to_, and fail.
- `python -m some.dotted.path` → Python imports the file _through_ its dotted package path, so `__package__` gets a real value and relative imports resolve.
- Rule of thumb: relative imports only work for files that are _always imported_, never launched directly.

## 3. Relative vs. absolute imports

- `.sibling` / `..cousin.module` = relative — position-dependent, only valid inside a package context.
- `mt5.packages.module` = absolute — looks the module up by its installed name, works identically no matter who's calling it or how.
- Design rule: **library files** (only ever imported) → relative imports are fine and idiomatic. **Entry-point scripts** (meant to be run directly) → must use absolute imports.

## 4. Path resolution bugs vs. import bugs (a separate failure class)

- `Path(__file__).resolve().parent.parent.parent` is a hardcoded "climb N folders" — it silently breaks the moment a file moves to a different depth (exactly what happened to `check_env.py` after the project restructure: it moved one folder deeper, but the parent-count wasn't updated, so it pointed at `src/keys.env` instead of the real `keys.env` at the project root).
- Fixed by swapping to `find_dotenv()` (from `python-dotenv`), which searches upward dynamically instead of assuming a fixed depth. General pattern: prefer "search for the thing" over "assume how many folders away the thing is."

## 5. Packaging your own project

- `pyproject.toml`'s `[project]` table alone only declares dependencies — it doesn't make _your_ code installable.
- `[build-system]` names the tool (we used `hatchling`) that knows how to package your code into a **wheel** (the standard installable/shippable unit).
- `[tool.hatch.build.targets.wheel]` with `packages = ["src/mt5"]` tells that tool _which_ folder becomes the installed package, and under what name (`mt5`).
- `uv sync` builds and installs your project into `.venv`'s `site-packages` — the shared "shelf" every script in that environment can pull from, regardless of its own location on disk.

## 6. Editable installs — why new files don't need a re-sync

- Editable install ≠ copying your code onto the shelf. It just drops a `.pth` file (we found `_editable_impl_forex_currency_trading.pth`) whose entire contents is the path to `src/`, telling Python "search here too" at every startup.
- Because that's a _live_ filesystem search, not a frozen snapshot, any new file or folder added under the already-declared package is found automatically — proved this by creating a file after syncing and importing it successfully with zero re-sync.
- Re-sync is only needed when `pyproject.toml` itself changes (new dependency, or declaring a _new_ top-level package not already covered by the existing `packages = [...]` entry).

## Gaps worth learning next, roughly in priority order

1. **Virtual environments themselves** — what `.venv` actually is, why it's isolated per-project, what "activating" one does versus using `uv run` / an explicit interpreter path.
2. **The Python import system in more depth** — `sys.modules` (the cache of already-imported modules), how circular imports fail, and what `__init__.py` is _for_ even when not strictly required (controlling what a package exports, running init code).
3. **Packaging beyond "it works locally"** — the difference between an editable install (what we did) and a real distributable wheel/sdist, and what changes if this project is ever `pip install`-ed on another machine or published.
4. **`sys.path` mechanics generally** — how it's ordered, how entries get added (cwd, `.pth` files, `PYTHONPATH` env var, site-packages) — the actual mental model underlying everything above.
5. **Dependency version resolution** — what `uv.lock` does when `uv sync` says "Resolved 153 packages," and how that differs from just listing dependencies in `pyproject.toml`.
