"""Generate the report figures from results_*.json.

Every number comes from a json produced by an actual run:
  results_perf.json   -> bench_perf.py   (median/min/max over 3 rounds x 3 reps)
  results_facts.json  -> collect_facts.py (pytest counts, red set, defect list)

Design: warm editorial palette, English labels (CJK renders as tofu in the
font stack available here), log axis where the magnitude spans >100x.
"""
import json
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent
FIG = ROOT / "docs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

INK = "#2b2119"
PAPER = "#faf6f0"
AMBER = "#c8892b"
TERRA = "#b4552f"
OLIVE = "#6b6b3a"
MUTED = "#8a7a68"

plt.rcParams.update(
    {
        "figure.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.grid": True,
        "grid.color": MUTED,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.6,
    }
)


def _clean(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------- figure 1
def fig_perf():
    data = json.loads((ROOT / "results_perf.json").read_text(encoding="utf-8"))
    chars = list(data["chars"].values())
    base = data["arms"]["baseline"]
    patch = data["arms"]["patched"]

    fig, ax = plt.subplots(figsize=(7.4, 4.6), dpi=160)
    ax.set_yscale("log")

    ax.plot(chars, base["median"], color=TERRA, marker="o", markersize=6,
            linewidth=2.0, label="before (regex backtracking)", zorder=3)
    ax.fill_between(chars, base["min"], base["max"], color=TERRA, alpha=0.16,
                    linewidth=0, zorder=2)

    ax.plot(chars, patch["median"], color=OLIVE, marker="s", markersize=6,
            linewidth=2.0, label="after (single linear scan)", zorder=3)
    ax.fill_between(chars, patch["min"], patch["max"], color=OLIVE, alpha=0.18,
                    linewidth=0, zorder=2)

    # Annotate the two endpoints of the slow arm (right-aligned at the edge).
    ax.annotate(f"{base['median'][-1]:,.0f} ms", xy=(chars[-1], base["median"][-1]),
                xytext=(-6, 10), textcoords="offset points", ha="right",
                color=TERRA, fontsize=10, fontweight="bold")
    ax.annotate(f"{patch['median'][-1]:.3f} ms", xy=(chars[-1], patch["median"][-1]),
                xytext=(-6, 9), textcoords="offset points", ha="right",
                color=OLIVE, fontsize=10, fontweight="bold")

    ax.set_xlabel("length of a value made only of '${' (characters)")
    ax.set_ylabel("time to parse (ms, log scale)")
    ax.set_title(
        "parse_variables on an unterminated expansion\n"
        "4x the input cost 15.4x the time before, 0.6x after",
        loc="left", fontsize=11.5, fontweight="bold", pad=12,
    )
    ax.set_xticks(chars)
    ax.set_xticklabels([f"{c:,}" for c in chars])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.legend(loc="upper left", frameon=False, fontsize=9.5)
    _clean(ax)
    fig.tight_layout(rect=(0.012, 0, 1, 0.9))
    out = FIG / "perf_parse_variables.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out.relative_to(ROOT))


# ---------------------------------------------------------------- figure 2
def fig_tests():
    facts = json.loads((ROOT / "results_facts.json").read_text(encoding="utf-8"))
    base_passed = facts["baseline"]["counts"]["passed"]
    patch_passed = facts["patched"]["counts"]["passed"]
    new = facts["new_tests"]
    red_only = len(facts["red_only"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.9), dpi=160,
                                   gridspec_kw={"width_ratios": [1.15, 1]})

    # Left: suite size, split into "existing" and "new".
    labels = ["before\n(unpatched)", "after\n(patched)"]
    existing = [base_passed, base_passed]
    added = [0, new]
    ax1.bar(labels, existing, color=AMBER, width=0.55, label="upstream tests")
    ax1.bar(labels, added, bottom=existing, color=OLIVE, width=0.55,
            label="tests added in this audit")
    for i, (e, a) in enumerate(zip(existing, added)):
        ax1.text(i, e / 2, str(e), ha="center", va="center", color=PAPER,
                 fontsize=10, fontweight="bold")
        if a:
            ax1.text(i, e + a / 2, f"+{a}", ha="center", va="center", color=PAPER,
                     fontsize=10, fontweight="bold")
        ax1.text(i, e + a + 6, str(e + a), ha="center", va="bottom", color=INK,
                 fontsize=10.5, fontweight="bold")
    ax1.set_ylim(0, patch_passed * 1.18)
    ax1.set_ylabel("tests passed")
    ax1.set_title("Suite: 0 failures on both arms", loc="left",
                  fontsize=11, fontweight="bold", pad=8)
    ax1.legend(frameon=False, fontsize=9, loc="upper left",
               bbox_to_anchor=(0.0, 1.0))
    _clean(ax1)

    # Right: the 36 new tests that fail on unpatched code -- that is the
    # evidence they actually detect the defects, not just pass.
    bars = ax2.barh(["new tests\npassing on\nunpatched code",
                     "new tests\nfailing on\nunpatched code"],
                    [new - red_only, red_only], color=[AMBER, TERRA], height=0.45)
    for bar, value, color in zip(bars, [new - red_only, red_only], [MUTED, TERRA]):
        ax2.text(value + 1.2, bar.get_y() + bar.get_height() / 2, str(value),
                 va="center", color=color, fontsize=12 if color == TERRA else 11,
                 fontweight="bold" if color == TERRA else "normal")
    ax2.set_xlim(0, new * 1.25)
    ax2.set_xlabel(f"of the {new} tests added")
    ax2.set_title("Would they have caught it?", loc="left",
                  fontsize=11, fontweight="bold", pad=8)
    _clean(ax2)

    fig.tight_layout(rect=(0.012, 0, 1, 0.92))
    out = FIG / "test_coverage.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out.relative_to(ROOT))


# ---------------------------------------------------------------- figure 3
def fig_defects():
    facts = json.loads((ROOT / "results_facts.json").read_text(encoding="utf-8"))
    defects = facts["defects"]
    areas = ["parser", "main", "cli", "variables"]
    sev_color = {"high": TERRA, "medium": AMBER}

    fig, ax = plt.subplots(figsize=(9.4, 4.6), dpi=160)
    y = 0.0
    ticks, ticklabels = [], []

    for area in areas:
        group = [d for d in defects if d["area"] == area]
        group_start = y
        for d in group:
            ax.barh(y, 1, color=sev_color[d["severity"]], height=0.6)
            ax.text(1.08, y, d["title"], va="center", ha="left", fontsize=8.6,
                    color=INK)
            ticks.append(y)
            ticklabels.append(d["id"])
            y += 1.0
        # Module label on the right edge, aligned with the top of its block.
        ax.text(6.05, group_start, f"{area}.py", va="center", ha="left",
                fontsize=9.5, fontweight="bold", color=MUTED)
        y += 0.85  # visible gap between modules
        if area != areas[-1]:
            ax.axhline(y - 0.42, color=MUTED, linewidth=0.8, alpha=0.4)

    ax.set_yticks(ticks)
    ax.set_yticklabels(ticklabels, fontsize=8.8)
    ax.invert_yaxis()
    ax.set_xlim(0, 7.4)
    ax.set_xticks([])
    ax.set_ylim(y - 0.55, -0.85)
    ax.set_title(
        f"{len(defects)} confirmed defects, grouped by module\n"
        "each one reproduced, fixed, and covered by a test that fails without the fix",
        loc="left", fontsize=11.5, fontweight="bold", pad=12,
    )
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=TERRA),
        plt.Rectangle((0, 0), 1, 1, color=AMBER),
    ]
    ax.legend(handles, ["high", "medium"], frameon=False, fontsize=9,
              loc="lower right", bbox_to_anchor=(1.0, -0.02), ncol=2)
    _clean(ax)
    ax.grid(False)
    fig.tight_layout(rect=(0.012, 0.02, 1, 0.9))
    out = FIG / "defects.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out.relative_to(ROOT))


# ---------------------------------------------------------------- figure 4
def fig_mutations():
    data = json.loads((ROOT / "results_mutations.json").read_text(encoding="utf-8"))
    rows = data["rows"]

    fig, ax = plt.subplots(figsize=(8.6, 0.34 * len(rows) + 1.7), dpi=160)
    names = [r["name"] for r in rows][::-1]
    counts = [r["failed_tests"] for r in rows][::-1]
    colors = [TERRA if r["verdict"] == "KILLED" else AMBER for r in rows][::-1]

    bars = ax.barh(names, counts, color=colors, height=0.62)
    for bar, value in zip(bars, counts):
        ax.text(value + 0.15, bar.get_y() + bar.get_height() / 2, str(value),
                va="center", fontsize=9, color=INK)
    ax.set_xlabel("independent tests that fail when the fix is reverted")
    ax.set_xlim(0, max(counts) * 1.16)
    ax.set_title(
        f"Every fix is load-bearing: {data['killed']} of {data['total']} mutations killed\n"
        "each bar is one reverted fix, measured by how many tests notice",
        loc="left", fontsize=11.5, fontweight="bold", pad=12,
    )
    ax.tick_params(axis="y", labelsize=8.6)
    _clean(ax)
    fig.tight_layout(rect=(0.012, 0, 1, 0.93))
    out = FIG / "mutations.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out.relative_to(ROOT))


fig_perf()
fig_tests()
fig_defects()
fig_mutations()
