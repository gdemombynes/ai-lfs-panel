import pytest

from lfspanel.latex import (
    MIDRULE,
    _count_columns,
    coef_lines,
    compile_check,
    escape,
    find_pdflatex,
    int_fmt,
    num,
    p_value,
    panel,
    stars,
    table_float,
    write_fragment,
)


def test_escape():
    assert escape("a & b_c 5% #1 $") == r"a \& b\_c 5\% \#1 \$"


def test_p_value_and_stars():
    assert abs(p_value(1.96, 1.0) - 0.05) < 0.001
    assert stars(2.0, 1.0) == "**"  # normal: p = 0.0455
    assert stars(2.0, 1.0, n_clusters=5) == ""  # t(4): p = 0.116
    assert stars(3.0, 1.0) == "***"
    assert stars(1.7, 1.0) == "*"
    assert stars(0.5, 1.0) == ""
    assert stars(1.0, 0.0) == "" and stars(float("nan"), 1.0) == ""


def test_coef_lines_and_numbers():
    top, bottom = coef_lines(-0.1128, 0.0291, n_clusters=82)
    assert top == "$-0.113^{***}$" and bottom == "$(0.029)$"
    assert coef_lines(0.0166, 0.0229, 655) == ("$0.017$", "$(0.023)$")
    assert coef_lines(float("nan"), 1.0) == ("", "")
    assert num(-1.5, 1) == "$-1.5$" and num(1.5, 2, plus=True) == "$+1.50$"
    assert int_fmt(59536) == r"59\,536" and int_fmt(655) == "655"


def test_count_columns():
    assert _count_columns("lcccrr") == 6
    assert _count_columns("@{}l*{3}{c}r@{}") == 5
    assert _count_columns("lp{3cm}r") == 3


def test_table_float_structure():
    rows = [
        panel("Panel A"),
        ["Brazil", "$0.014$", "$(0.023)$"],
        MIDRULE,
        ["", r"\multicolumn{2}{c}{span}"],
    ]
    tex = table_float(
        "tab:x",
        "A caption",
        "lcc",
        [["", "coef", "se"]],
        rows,
        notes="Some notes.",
        note_items=["$^{a}$ a note"],
        tabcolsep="3pt",
    )
    assert tex.count(r"\begin{table}") == 1 and tex.count(r"\end{table}") == 1
    assert r"\label{tab:x}" in tex and r"\caption{A caption}" in tex
    assert r"\begin{threeparttable}" in tex and r"\begin{tablenotes}[flushleft]" in tex
    assert r"\multicolumn{3}{@{}l}{\textit{Panel A}} \\" in tex
    assert r"Brazil & $0.014$ & $(0.023)$ \\" in tex
    assert r"\midrule" in tex and r"\toprule" in tex and r"\bottomrule" in tex
    # a multicolumn cell counts for its span: no extra alignment tabs are added
    assert r" & \multicolumn{2}{c}{span} \\" in tex
    assert r"\setlength{\tabcolsep}{3pt}" in tex
    assert r"\item $^{a}$ a note" in tex
    assert table_float("tab:y", "c", "lc", [["a", "b"]], [], landscape=True).startswith(
        r"\begin{sidewaystable}"
    )


@pytest.mark.skipif(find_pdflatex() is None, reason="pdflatex not installed")
def test_compile_check(tmp_path):
    tex = table_float("tab:z", "Check", "lc", [["x", "y"]], [["1", "$-2^{*}$"]])
    frag = write_fragment(tmp_path / "frag.tex", tex)
    ok, messages = compile_check([frag])
    assert ok, messages
    broken = write_fragment(tmp_path / "broken.tex", tex.replace(r"\end{tabular}", ""))
    ok, messages = compile_check([broken])
    assert not ok and any(m.startswith("broken.tex: !") for m in messages)


def test_figure_float():
    from lfspanel.latex import figure_float

    one = figure_float("fig:a", "Cap", [("a.png", None)], notes="N.")
    assert r"\includegraphics[width=\textwidth]{\tabfig/a.png}" in one
    assert r"\label{fig:a}" in one and r"\caption{Cap}" in one
    assert r"\textit{Notes:} N." in one and r"\subfloat" not in one
    two = figure_float(
        "fig:b",
        "Cap",
        [("a.png", "A"), ("b.png", "B")],
        width="0.49\\textwidth",
        per_row=2,
    )
    assert two.count(r"\subfloat[") == 2 and r"\hfill" in two
    assert "\n\\\\\n" not in two  # both panels on one row
    three = figure_float("fig:c", "Cap", [("a.png", "A"), ("b.png", "B")], per_row=1)
    assert "\n\\\\\n" in three
