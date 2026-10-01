"""Design-drift audit for the ChineseVerse frontend (read-only, advisory).

Flags values that bypass the "Ink & Jade" tokens in frontend/src/index.css:
raw colours, pixel font sizes / radii, literal transition durations,
non-canonical breakpoints, `outline: none`, and likely hardcoded UI text.

Usage (from the repo root):
  python .claude/skills/chineseverse-frontend-design/scripts/design_audit.py
      -> audits only lines ADDED in the working tree vs HEAD (plus new
         untracked files under frontend/src), so legacy drift isn't re-reported.
  python .claude/skills/chineseverse-frontend-design/scripts/design_audit.py FILE...
      -> audits every line of the given files.

Never modifies anything. Exit code is 0 unless --strict is passed and
something was flagged. Every finding is a prompt to reuse a token/class, or to
consciously justify the exception (data-viz palettes, the World SVG, etc.).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

CANONICAL_BREAKPOINTS = {1080, 980, 760, 720, 640, 480}

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
RGBA = re.compile(r"\brgba?\(\s*\d")
CSS_FONT_PX = re.compile(r"font-size:\s*[\d.]+px")
JSX_FONT_NUM = re.compile(r"fontSize:\s*[\d.]+\b")
CSS_RADIUS_PX = re.compile(r"border-radius:\s*[\d.]+px")
JSX_RADIUS_NUM = re.compile(r"borderRadius:\s*[\d.]+\b")
# A literal sub-second duration in a transition (infinite ambient loops in
# `animation:` are deliberately allowed and not matched here).
TRANSITION_LITERAL = re.compile(r"transition[^;]*?\b0?\.\d+s\b|transition[^;]*?\b\d{2,3}ms\b")
MEDIA = re.compile(r"@media[^{]*?(?:max|min)-width:\s*(\d+)px")
OUTLINE_NONE = re.compile(r"outline:\s*(none|0)\b")
# >Some English words< directly in JSX: a heuristic for strings that skipped t().
JSX_TEXT = re.compile(r">\s*[A-Z][a-z]+(?:[ ,'][A-Za-z]+){1,}[.!?]?\s*<")
JSX_ATTR_TEXT = re.compile(r'\b(?:aria-label|placeholder|title|alt)="[A-Z][a-z]+[^"]*"')
CUSTOM_PROP_DEF = re.compile(r"^\s*--[\w-]+\s*:")


def check_line(path: str, line: str) -> list[str]:
    issues: list[str] = []
    is_css = path.endswith(".css")
    stripped = line.strip()
    if not stripped or stripped.startswith(("//", "/*", "*")):
        return issues
    # Defining a token is the one place a raw value belongs.
    if is_css and CUSTOM_PROP_DEF.match(line):
        return issues

    if HEX.search(line) or RGBA.search(line):
        issues.append("raw colour - use a theme token (--text, --surface-*, --accent*, --good, --bad ...)")
    if (is_css and CSS_FONT_PX.search(line)) or (not is_css and JSX_FONT_NUM.search(line)):
        issues.append("pixel font size - use --text-2xs..--text-hero or a typography class (.h1 .h2 .sub ...)")
    if (is_css and CSS_RADIUS_PX.search(line)) or (not is_css and JSX_RADIUS_NUM.search(line)):
        issues.append("pixel radius - use --radius-sm/md/lg/full")
    if is_css and TRANSITION_LITERAL.search(line):
        issues.append("literal transition duration - use --dur-fast/base/slow")
    m = MEDIA.search(line)
    if m and int(m.group(1)) not in CANONICAL_BREAKPOINTS:
        issues.append(f"non-canonical breakpoint {m.group(1)}px - use one of {sorted(CANONICAL_BREAKPOINTS, reverse=True)}")
    if is_css and OUTLINE_NONE.search(line):
        issues.append("outline removed - make sure a visible :focus / :focus-visible replacement exists")
    if not is_css and (JSX_TEXT.search(line) or JSX_ATTR_TEXT.search(line)):
        issues.append("possible hardcoded UI text - use t() and add the key to en/ru/tg/zh")
    return issues


def added_lines_vs_head(repo: Path) -> dict[str, list[tuple[int, str]]]:
    out: dict[str, list[tuple[int, str]]] = {}
    diff = subprocess.run(
        ["git", "diff", "-U0", "HEAD", "--", "frontend/src"],
        cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout
    current, lineno = None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            current = raw[6:] if raw.startswith("+++ b/") else None
        elif raw.startswith("@@"):
            lineno = int(re.search(r"\+(\d+)", raw).group(1))
        elif current and raw.startswith("+"):
            out.setdefault(current, []).append((lineno, raw[1:]))
            lineno += 1
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "frontend/src"],
        cwd=repo, capture_output=True, text=True,
    ).stdout.split()
    for rel in untracked:
        out[rel] = whole_file(repo / rel)
    return out


def whole_file(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return list(enumerate(text.splitlines(), start=1))


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    files = [a for a in argv if not a.startswith("--")]
    repo = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or ".")

    if files:
        targets = {f: whole_file(Path(f)) for f in files}
        mode = "whole files"
    else:
        targets = added_lines_vs_head(repo)
        mode = "lines added vs HEAD"

    targets = {p: ls for p, ls in targets.items() if p.endswith((".css", ".jsx", ".js"))}
    findings = 0
    for path, lines in sorted(targets.items()):
        for lineno, line in lines:
            for issue in check_line(path, line):
                findings += 1
                print(f"{path}:{lineno}: {issue}\n    {line.strip()[:110]}")

    print(f"\ndesign_audit ({mode}): {len(targets)} file(s), {findings} finding(s)")
    return 1 if (strict and findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
