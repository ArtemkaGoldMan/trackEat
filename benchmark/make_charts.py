#!/usr/bin/env python3
"""Render PNG charts (EN and UK) from benchmark/out/*.json into docs/img/ for the Markdown reports."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
IMG = os.path.join(os.path.dirname(HERE), "docs", "img")
os.makedirs(IMG, exist_ok=True)

S = json.load(open(f"{OUT}/summary.json"))
D = json.load(open(f"{OUT}/daily.json"))
I = json.load(open(f"{OUT}/items.json"))
DS = json.load(open(f"{OUT}/dataset.json"))

MODELS = ["haiku", "sonnet", "opus"]
EFFORTS = ["low", "medium", "high"]
MODES = ["photo", "hint", "cooked", "rough", "main_weight", "weighed"]
COL = {"haiku": "#d97757", "sonnet": "#3b82c4", "opus": "#8b5cc6"}
ALPHA = {"low": .45, "medium": .72, "high": 1.0}
NAME = {"haiku": "Haiku 5.5", "sonnet": "Sonnet 5.5", "opus": "Opus 5.5"}

L = {
    "en": {
        "err": "Mean calorie error, %", "day": "Daily error, %", "cost": "Cost, $ per 1,000 photos (log scale)",
        "modes": {"photo": "Photo only", "hint": "Photo + item list", "cooked": "Photo + cooking description",
                  "rough": "Photo + rough amounts", "main_weight": "Photo + main item weight", "weighed": "Photo + all weights"},
        "scen": "What you send with the photo (20 dishes, effort low)", "dish": "Plated dishes, photo only",
        "snack": "Snacks and branded products, photo only", "daily": "Error over a whole day (5,000 simulated days, effort low)",
        "costt": "Accuracy versus price (dishes, photo only)", "heat": "Median error per photo, % (dishes, photo only; red = over, blue = under)",
        "ci": "whisker = 95% CI over photos",
    },
    "uk": {
        "err": "Середня похибка калорій, %", "day": "Похибка за день, %", "cost": "Ціна, $ за 1 000 фото (логарифмічна шкала)",
        "modes": {"photo": "Лише фото", "hint": "Фото + перелік продуктів", "cooked": "Фото + опис приготування",
                  "rough": "Фото + приблизні кількості", "main_weight": "Фото + вага основного", "weighed": "Фото + вага всього"},
        "scen": "Що надсилати разом з фото (20 страв, effort low)", "dish": "Страви з тарілки, лише фото",
        "snack": "Снеки й брендові продукти, лише фото", "daily": "Похибка за цілий день (5 000 змодельованих днів, effort low)",
        "costt": "Точність проти ціни (страви, лише фото)", "heat": "Похибка медіани по фото, % (страви, лише фото; червоне — завищено, синє — занижено)",
        "ci": "риска = 95% ДІ по фото",
    },
}
EN_NAMES = json.load(open(os.path.join(HERE, "name_en.json"))) if os.path.exists(os.path.join(HERE, "name_en.json")) else {}


def row(cfg):
    return next((r for r in S if r["config"] == cfg), None)


def drow(cfg):
    return next((r for r in D if r["config"] == cfg), None)


def ordered(rows):
    return sorted(rows, key=lambda r: (MODELS.index(r["model"]), EFFORTS.index(r["effort"])))


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color="#e6e4dc", lw=.8)
    ax.set_axisbelow(True)


def save(fig, name, lang):
    fig.savefig(f"{IMG}/{name}.{lang}.png", dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def hbars(rows, title, lang, name, ref=20):
    t = L[lang]
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(rows) + 1.4))
    ys = range(len(rows))[::-1]
    for y, r in zip(ys, rows):
        ax.barh(y, r["mape"], color=COL[r["model"]], alpha=ALPHA[r["effort"]], height=.68)
        ax.plot([r["mape_lo"], r["mape_hi"]], [y, y], color="#222", lw=1.3)
        for x in (r["mape_lo"], r["mape_hi"]):
            ax.plot([x, x], [y - .15, y + .15], color="#222", lw=1.3)
        ax.text(r["mape_hi"] + 1, y, f'{r["mape"]:.1f}%', va="center", fontsize=8, color="#444")
    ax.axvline(ref, color="#888", ls="--", lw=1)
    ax.set_yticks(list(ys)); ax.set_yticklabels([r["label"] for r in rows])
    ax.set_xlabel(f'{t["err"]}  ({t["ci"]})'); ax.set_title(title, loc="left", fontweight="bold")
    ax.set_xlim(0, max(r["mape_hi"] for r in rows) * 1.18); style(ax)
    save(fig, name, lang)


def scen(lang):
    t = L[lang]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    h = .36
    for k, m in enumerate(["sonnet", "opus"]):
        for i, md in enumerate(MODES):
            r = row(f"dish|{md}|{m}|low")
            y = len(MODES) - 1 - i + (.19 if k == 0 else -.19)
            ax.barh(y, r["mape"], height=h, color=COL[m], label=f"{NAME[m]} · low" if i == 0 else None)
            ax.plot([r["mape_lo"], r["mape_hi"]], [y, y], color="#222", lw=1.2)
            ax.text(r["mape_hi"] + .8, y, f'{r["mape"]:.1f}%', va="center", fontsize=8, color="#444")
    ax.set_yticks(range(len(MODES))[::-1]); ax.set_yticklabels([t["modes"][m] for m in MODES])
    ax.set_xlabel(f'{t["err"]}  ({t["ci"]})'); ax.set_title(t["scen"], loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="lower right"); ax.set_xlim(0, 62); style(ax)
    save(fig, "scenarios", lang)


def daily(lang):
    t = L[lang]
    fig, ax = plt.subplots(figsize=(8, 4))
    w = .26
    for k, m in enumerate(MODELS):
        xs, ys = [], []
        for i, md in enumerate(MODES):
            r = drow(f"day|{md}|{m}|low")
            if r:
                xs.append(i + (k - 1) * w); ys.append(r["day_mape"])
        ax.bar(xs, ys, width=w, color=COL[m], label=f"{NAME[m]} · low")
        for x, y in zip(xs, ys):
            ax.text(x, y + .4, f"{y:.0f}", ha="center", fontsize=7, color="#444")
    ax.set_xticks(range(len(MODES))); ax.set_xticklabels([t["modes"][m].replace(" + ", "\n+ ", 1) for m in MODES], fontsize=7.5)
    ax.set_ylabel(t["day"]); ax.set_title(t["daily"], loc="left", fontweight="bold")
    ax.legend(frameon=False); ax.grid(axis="y", color="#e6e4dc"); ax.grid(axis="x", visible=False)
    ax.spines[["top", "right"]].set_visible(False); ax.set_axisbelow(True)
    save(fig, "daily", lang)


def cost(lang):
    t = L[lang]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for r in S:
        if r["set"] == "dish" and r["mode"] == "photo":
            ax.scatter(r["cost_per_1000"], r["mape"], s=80, color=COL[r["model"]], alpha=ALPHA[r["effort"]], edgecolor="white", zorder=3)
            ax.annotate(f'{r["effort"]}', (r["cost_per_1000"], r["mape"]), textcoords="offset points", xytext=(7, 4), fontsize=7, color="#555")
    ax.set_xscale("log"); ax.set_xticks([1, 2, 5, 10, 20]); ax.set_xticklabels(["$1", "$2", "$5", "$10", "$20"])
    ax.set_xlabel(t["cost"]); ax.set_ylabel(t["err"]); ax.set_ylim(0, 50)
    ax.set_title(t["costt"], loc="left", fontweight="bold")
    for m in MODELS:
        ax.scatter([], [], color=COL[m], label=NAME[m])
    ax.legend(frameon=False); ax.grid(color="#e6e4dc"); ax.spines[["top", "right"]].set_visible(False); ax.set_axisbelow(True)
    save(fig, "cost", lang)


def heat(lang):
    t = L[lang]
    cfgs = ordered([r for r in S if r["set"] == "dish" and r["mode"] == "photo"])
    items = [d for d in DS if d["set"] == "dish"]
    mat = []
    for d in items:
        line = []
        for c in cfgs:
            r = next((x for x in I if x["item"] == d["item"] and x["mode"] == "photo" and x["model"] == c["model"] and x["effort"] == c["effort"]), None)
            line.append(r["err_median_pct"] if r else float("nan"))
        mat.append(line)
    fig, ax = plt.subplots(figsize=(8, 0.34 * len(items) + 1.6))
    cmap = LinearSegmentedColormap.from_list("d", ["#3c82c8", "#ffffff", "#dc5a32"])
    ax.imshow(mat, cmap=cmap, vmin=-100, vmax=100, aspect="auto")
    for i, line in enumerate(mat):
        for j, v in enumerate(line):
            ax.text(j, i, f"{v:+.0f}", ha="center", va="center", fontsize=7, color="#222")
    ax.set_xticks(range(len(cfgs))); ax.set_xticklabels([c["label"].replace(" · ", "\n") for c in cfgs], fontsize=7)
    ax.xaxis.tick_top()
    labels = []
    for d in items:
        n = d["name"] if lang == "uk" else EN_NAMES.get(d["name"], d["name"])
        labels.append(f'{n}  ({d["gt_kcal"]:.0f})')
    ax.set_yticks(range(len(items))); ax.set_yticklabels(labels, fontsize=7.5)
    ax.set_title(t["heat"], loc="left", fontweight="bold", fontsize=9, pad=34)
    for s in ax.spines.values():
        s.set_visible(False)
    save(fig, "heatmap", lang)


# Ukrainian dish names -> English (same mapping as the site generator).
src = open(os.path.join(HERE, "build_site.py"), encoding="utf-8").read()
ns = {}
exec(src[src.index("EN_NAMES = {"):src.index("for d in dataset:")], ns)
EN_NAMES = ns["EN_NAMES"]

for lang in ("en", "uk"):
    scen(lang)
    hbars(ordered([r for r in S if r["set"] == "dish" and r["mode"] == "photo"]), L[lang]["dish"], lang, "dishes")
    hbars(ordered([r for r in S if r["set"] == "snack" and r["mode"] == "photo"]), L[lang]["snack"], lang, "snacks")
    daily(lang)
    cost(lang)
    heat(lang)
print("charts written to docs/img/")
