"""LaTeX table fragments for the paper.

Each table is a complete float (``table``, ``threeparttable``, ``booktabs``
rules, caption, label and notes) that the manuscript pulls in with one
``\\input`` line. Coefficients are typeset in math mode with the standard
error in parentheses on the line below and significance stars from the
cluster-robust t statistic.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np
from scipy import stats

STAR_LEVELS: Tuple[Tuple[float, str], ...] = ((0.01, "***"), (0.05, "**"), (0.10, "*"))
_SPECIALS = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_"}

Row = Union[Sequence[str], Tuple[str, str], Tuple[str]]


def escape(text: str) -> str:
    """Escape the characters that LaTeX would otherwise read as markup."""
    return "".join(_SPECIALS.get(ch, ch) for ch in str(text))


def p_value(coef: float, se: float, n_clusters: Optional[int] = None) -> float:
    """Two-sided p-value of coef/se: t(G-1) given the cluster count, else normal."""
    if se is None or not np.isfinite(se) or se <= 0 or not np.isfinite(coef):
        return float("nan")
    t = abs(coef / se)
    if n_clusters is not None and n_clusters > 1:
        return float(2 * stats.t.sf(t, n_clusters - 1))
    return float(2 * stats.norm.sf(t))


def stars(coef: float, se: float, n_clusters: Optional[int] = None) -> str:
    """Stars at 10, 5 and 1 percent from the cluster-robust t statistic."""
    p = p_value(coef, se, n_clusters)
    if not np.isfinite(p):
        return ""
    for level, s in STAR_LEVELS:
        if p < level:
            return s
    return ""


def num(x: float, digits: int = 3, plus: bool = False) -> str:
    """A number in math mode so the minus sign is typeset as a minus."""
    if x is None or not np.isfinite(x):
        return ""
    sign = "+" if plus else ""
    return f"${x:{sign}.{digits}f}$"


def coef_lines(
    coef: float, se: float, n_clusters: Optional[int] = None, digits: int = 3
) -> Tuple[str, str]:
    """(coefficient with stars, standard error in parentheses), both in math mode."""
    if coef is None or not np.isfinite(coef):
        return "", ""
    s = stars(coef, se, n_clusters)
    top = f"${coef:.{digits}f}" + (f"^{{{s}}}" if s else "") + "$"
    bottom = f"$({se:.{digits}f})$" if se is not None and np.isfinite(se) else ""
    return top, bottom


def int_fmt(x: float) -> str:
    """Thousands-separated integer with a thin-space separator LaTeX accepts."""
    if x is None or not np.isfinite(x):
        return ""
    return f"{int(round(x)):,}".replace(",", r"\,")


def panel(title: str) -> Tuple[str, str]:
    return ("panel", title)


MIDRULE: Tuple[str] = ("midrule",)
SPACE: Tuple[str] = ("addlinespace",)


def _span(cell: str) -> int:
    """Columns a cell occupies (``\\multicolumn{n}`` counts n)."""
    m = re.match(r"\s*\\multicolumn\{(\d+)\}", cell)
    return int(m.group(1)) if m else 1


def _render_row(row: Row, ncols: int) -> str:
    markers = ("panel", "midrule", "addlinespace")
    if isinstance(row, tuple) and row and row[0] in markers:
        if row[0] == "panel":
            head = rf"\multicolumn{{{ncols}}}{{@{{}}l}}{{\textit{{{row[1]}}}}} \\"
            return r"\addlinespace" + "\n" + head
        return "\\" + row[0]
    cells = list(row)
    used = sum(_span(c) for c in cells)
    cells += [""] * max(0, ncols - used)
    return " & ".join(cells) + r" \\"


def table_float(
    label: str,
    caption: str,
    colspec: str,
    header: Sequence[Sequence[str]],
    rows: Sequence[Row],
    notes: str = "",
    size: str = r"\small",
    placement: str = "htbp",
    landscape: bool = False,
    header_rules: Sequence[str] = (),
    note_items: Sequence[str] = (),
    tabcolsep: Optional[str] = None,
    annex: bool = False,
) -> str:
    """A complete table float with booktabs rules inside ``threeparttable``.

    ``header`` is one or more header rows; ``header_rules`` are extra lines
    (``\\cmidrule`` ...) placed after the first header row. ``rows`` are data
    rows (sequences of already formatted cells), ``panel(title)`` markers,
    ``MIDRULE`` or ``SPACE``. ``note_items`` are extra lettered notes placed
    after the main note. ``annex`` switches table numbering to A1, A2, ...
    from this table on, so annex fragments go after the main tables.
    """
    ncols = _count_columns(colspec)
    lines: List[str] = []
    env = "sidewaystable" if landscape else "table"
    if annex:  # numbered A1, A2, ...: input annex tables after the main ones
        lines.append(r"\renewcommand{\thetable}{A\arabic{table}}")
        lines.append(r"\setcounter{table}{0}")
    lines.append(rf"\begin{{{env}}}[{placement}]")
    lines.append(r"\centering")
    lines.append(size)
    if tabcolsep:
        lines.append(rf"\setlength{{\tabcolsep}}{{{tabcolsep}}}")
    lines.append(r"\begin{threeparttable}")
    lines.append(rf"\caption{{{caption}}}")
    lines.append(rf"\label{{{label}}}")
    lines.append(rf"\begin{{tabular}}{{{colspec}}}")
    lines.append(r"\toprule")
    for i, h in enumerate(header):
        lines.append(_render_row(list(h), ncols))
        if i == 0:
            lines.extend(header_rules)
    lines.append(r"\midrule")
    for row in rows:
        lines.append(_render_row(row, ncols))
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    if notes or note_items:
        lines.append(r"\begin{tablenotes}[flushleft]")
        lines.append(r"\footnotesize")
        if notes:
            lines.append(rf"\item \textit{{Notes:}} {notes}")
        for item in note_items:
            lines.append(rf"\item {item}")
        lines.append(r"\end{tablenotes}")
    lines.append(r"\end{threeparttable}")
    lines.append(rf"\end{{{env}}}")
    return "\n".join(lines) + "\n"


def _count_columns(colspec: str) -> int:
    """Number of columns in a tabular column specification."""
    spec = re.sub(r"@\{[^}]*\}", "", colspec)
    spec = re.sub(r"p\{[^}]*\}", "p", spec)
    n = 0
    for m in re.finditer(r"\*\{(\d+)\}\{([^}]*)\}|([lcrp])", spec):
        if m.group(1):
            n += int(m.group(1)) * _count_columns(m.group(2))
        else:
            n += 1
    return n


def figure_float(
    label: str,
    caption: str,
    panels: Sequence[Tuple[str, Optional[str]]],
    width: str = r"\textwidth",
    notes: str = "",
    placement: str = "htbp",
    per_row: int = 1,
    prefix: str = r"\tabfig/",
) -> str:
    """A figure float with one or more image panels.

    ``panels`` are (file name, sub-caption) pairs; a panel without a
    sub-caption is included directly, panels with one become ``\\subfloat``
    entries (``subfig`` package). ``per_row`` panels share one line, each
    ``width`` wide. Files are referenced as ``prefix + name`` so the fragment
    works once the images sit in the paper's ``\tabfig`` directory.
    """
    lines = [rf"\begin{{figure}}[{placement}]", r"\centering"]
    for i, (name, sub) in enumerate(panels):
        img = rf"\includegraphics[width={width}]{{{prefix}{name}}}"
        if sub is None:
            lines.append(img)
        else:
            lines.append(rf"\subfloat[{sub}]{{{img}}}")
        if i + 1 < len(panels):
            lines.append(r"\\" if (i + 1) % per_row == 0 else r"\hfill")
    lines.append(rf"\caption{{{caption}}}")
    lines.append(rf"\label{{{label}}}")
    if notes:  # floatrow places \floatfoot under the caption
        lines.append(rf"\floatfoot{{\footnotesize \textit{{Notes:}} {notes}}}")
    lines.append(r"\end{figure}")
    return "\n".join(lines) + "\n"


def write_fragment(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


CHECK_PREAMBLE = r"""\documentclass[12pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{threeparttable}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{rotating}
\usepackage{lscape}
\usepackage{floatrow}
\usepackage{float}
\usepackage{subfig}
\floatsetup[table]{footnoterule=none,footskip=0.5\skip\footins}
\floatstyle{plaintop} \restylefloat{table}
"""


def find_pdflatex() -> Optional[str]:
    """pdflatex on PATH, else the user TeX Live install under ``~/texlive``."""
    found = shutil.which("pdflatex")
    if found:
        return found
    home = Path(os.path.expanduser("~")) / "texlive"
    for candidate in sorted(home.glob("*/bin/*/pdflatex"), reverse=True):
        if os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _compile(
    exe: str,
    fragments: Sequence[Path],
    pdf_out: Optional[Path] = None,
    preamble: str = "",
) -> Tuple[bool, List[str]]:
    with tempfile.TemporaryDirectory() as tmp:
        main = Path(tmp) / "check.tex"
        body = "\n".join(rf"\input{{{Path(f).resolve()}}}" for f in fragments)
        main.write_text(
            CHECK_PREAMBLE
            + preamble
            + "\n\\begin{document}\n"
            + body
            + "\n\\end{document}\n",
            encoding="utf-8",
        )
        ok = True
        for _ in range(2):  # twice so the label references settle
            proc = subprocess.run(
                [exe, "-interaction=nonstopmode", "-halt-on-error", main.name],
                cwd=tmp,
                capture_output=True,
                text=True,
            )
            ok = proc.returncode == 0
            if not ok:
                break
        log = (Path(tmp) / "check.log").read_text(encoding="utf-8", errors="ignore")
        pdf = Path(tmp) / "check.pdf"
        if ok and pdf_out is not None and pdf.exists():
            pdf_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(pdf, pdf_out)
    messages = [
        line
        for line in log.splitlines()
        if line.startswith("!")
        or line.startswith("Overfull")
        or "undefined" in line.lower()
    ]
    return ok, messages


def compile_check(
    fragments: Sequence[Path],
    pdflatex: Optional[str] = None,
    pdf_out: Optional[Path] = None,
    preamble: str = "",
) -> Tuple[bool, List[str]]:
    """Compile each fragment in a throwaway document with the paper's packages.

    Returns (ok, messages): ``ok`` is True when every fragment compiles alone
    and all of them compile together; ``messages`` holds the error and
    overfull-box lines from each log, prefixed with the fragment's name, and
    the undefined references left after the joint pass. With ``pdf_out`` the
    joint PDF is saved there for inspection. Raises ``RuntimeError`` when no
    pdflatex is found. ``preamble`` is extra LaTeX placed before
    ``\\begin{document}``, for instance a ``\\tabfig`` path macro.
    """
    exe = pdflatex or find_pdflatex()
    if exe is None:
        raise RuntimeError("pdflatex not found on PATH or under ~/texlive")
    ok_all, messages = True, []
    for f in fragments:
        ok, msgs = _compile(exe, [f], preamble=preamble)
        ok_all = ok_all and ok
        # cross-references between fragments only resolve in the joint pass
        messages += [
            f"{Path(f).name}: {m}" for m in msgs if "undefined" not in m.lower()
        ]
    if ok_all and (pdf_out is not None or len(fragments) > 1):
        ok, msgs = _compile(exe, fragments, pdf_out, preamble)
        ok_all = ok_all and ok
        messages += [f"all fragments: {m}" for m in msgs]
    return ok_all, messages
