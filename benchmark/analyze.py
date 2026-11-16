#!/usr/bin/env python3
"""Turn results.jsonl into summary tables for the report (pure stdlib)."""
import csv
import json
import math
import os
import random
import statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
MODEL_ORDER = ["haiku", "sonnet", "opus"]
EFFORT_ORDER = ["low", "medium", "high"]
MODE_ORDER = ["photo", "hint", "cooked", "rough", "main_weight", "weighed"]
MODEL_NAME = {"haiku": "Haiku 5.5", "sonnet": "Sonnet 5.5", "opus": "Opus 5.5"}

items = {d["id"]: d for d in json.load(open(os.path.join(HERE, "dataset.json")))}

runs, seen = [], set()
for line in open(os.path.join(HERE, "results.jsonl")):
    r = json.loads(line)
    if "error" in r or r["key"] in seen or r["dish"] not in items:
        continue
    seen.add(r["key"])
    p = r.get("parsed") or {}
    t = p.get("total") if isinstance(p, dict) else None

    def num(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    kcal = num((t or {}).get("kcal"))
    if kcal is None and isinstance(p, dict) and p.get("items"):
        kcal = sum(num(i.get("kcal")) or 0 for i in p["items"]) or None
    it = items[r["dish"]]
    runs.append({
        "set": it["set"], "mode": r["mode"], "model": r["model"], "effort": r["effort"],
        "item": r["dish"], "rep": r["rep"], "ok": kcal is not None and kcal > 0,
        "kcal": kcal, "protein": num((t or {}).get("protein_g")), "fat": num((t or {}).get("fat_g")),
        "carbs": num((t or {}).get("carbs_g")), "grams": num((t or {}).get("grams")),
        "confidence": (p.get("confidence") if isinstance(p, dict) else None),
        "gt_kcal": it["kcal"], "gt_protein": it["protein"], "gt_fat": it["fat"], "gt_carbs": it["carbs"],
        "cost": r.get("cost_usd") or 0.0, "latency": (r.get("duration_ms") or 0) / 1000,
        "out_tokens": r.get("output_tokens") or 0, "thinking_tokens": r.get("thinking_tokens") or 0,
    })

groups = defaultdict(list)
for r in runs:
    groups[(r["set"], r["mode"], r["model"], r["effort"])].append(r)


def by_item(rs):
    d = defaultdict(list)
    for r in rs:
        if r["ok"]:
            d[r["item"]].append(r)
    return d


def item_stats(rs_item):
    gt = rs_item[0]["gt_kcal"]
    preds = [r["kcal"] for r in rs_item]
    mean = st.mean(preds)
    return {
        "ape": st.mean(abs(p - gt) / gt for p in preds),
        "signed": st.mean((p - gt) / gt for p in preds),
        "cv": (st.pstdev(preds) / mean) if mean else 0,
        "ape_of_mean": abs(mean - gt) / gt,
    }


rng = random.Random(7)
summary = []
for key in sorted(groups, key=lambda k: (k[0], MODE_ORDER.index(k[1]), MODEL_ORDER.index(k[2]), EFFORT_ORDER.index(k[3]))):
    rs = groups[key]
    ok = [r for r in rs if r["ok"]]
    bi = by_item(rs)
    stats = {i: item_stats(v) for i, v in bi.items()}
    ids = list(stats)
    apes = [s["ape"] for s in stats.values()]
    boots = []
    for _ in range(2000):
        sample = [stats[rng.choice(ids)]["ape"] for _ in ids]
        boots.append(st.mean(sample))
    boots.sort()
    all_ape = [abs(r["kcal"] - r["gt_kcal"]) / r["gt_kcal"] for r in ok]

    def wape(m):
        pairs = [(r[m], r["gt_" + m]) for r in ok if r[m] is not None]
        return sum(abs(p - g) for p, g in pairs) / sum(g for _, g in pairs) if pairs else None

    def mae(m):
        pairs = [(r[m], r["gt_" + m]) for r in ok if r[m] is not None]
        return st.mean(abs(p - g) for p, g in pairs) if pairs else None

    s, mode, model, effort = key
    summary.append({
        "config": f"{s}|{mode}|{model}|{effort}", "set": s, "mode": mode, "model": model,
        "model_name": MODEL_NAME[model], "effort": effort, "label": f"{MODEL_NAME[model]} · {effort}",
        "runs": len(rs), "parsed": len(ok), "items": len(ids),
        "mape": round(100 * st.mean(apes), 2),
        "mape_lo": round(100 * boots[int(0.025 * len(boots))], 2),
        "mape_hi": round(100 * boots[int(0.975 * len(boots)) - 1], 2),
        "median_ape": round(100 * st.median(all_ape), 2),
        "within10": round(100 * sum(a <= 0.10 for a in all_ape) / len(all_ape), 1),
        "within20": round(100 * sum(a <= 0.20 for a in all_ape) / len(all_ape), 1),
        "within30": round(100 * sum(a <= 0.30 for a in all_ape) / len(all_ape), 1),
        "bias": round(100 * st.mean(s_["signed"] for s_ in stats.values()), 2),
        "cv": round(100 * st.mean(s_["cv"] for s_ in stats.values()), 2),
        "ape_of_mean": round(100 * st.mean(s_["ape_of_mean"] for s_ in stats.values()), 2),
        "wape_protein": round(100 * wape("protein"), 1), "wape_fat": round(100 * wape("fat"), 1),
        "wape_carbs": round(100 * wape("carbs"), 1),
        "mae_kcal": round(st.mean(abs(r["kcal"] - r["gt_kcal"]) for r in ok), 1),
        "mae_protein": round(mae("protein"), 1), "mae_fat": round(mae("fat"), 1), "mae_carbs": round(mae("carbs"), 1),
        "cost_per_call": round(st.mean(r["cost"] for r in rs), 5),
        "cost_per_1000": round(1000 * st.mean(r["cost"] for r in rs), 2),
        "latency_s": round(st.mean(r["latency"] for r in rs), 2),
        "out_tokens": round(st.mean(r["out_tokens"] for r in rs)),
        "thinking_tokens": round(st.mean(r["thinking_tokens"] for r in rs)),
    })

# Per item x config
item_rows = []
for key, rs in groups.items():
    s, mode, model, effort = key
    for iid, v in by_item(rs).items():
        it = items[iid]
        preds = sorted(r["kcal"] for r in v)
        med = st.median(preds)
        item_rows.append({
            "row": f"{iid}|{mode}|{model}|{effort}", "item": iid, "name": it["name"], "set": s, "mode": mode,
            "model": model, "model_name": MODEL_NAME[model], "effort": effort, "config": f"{s}|{mode}|{model}|{effort}",
            "gt_kcal": it["kcal"], "n": len(preds), "median": round(med), "mean": round(st.mean(preds)),
            "min": round(preds[0]), "max": round(preds[-1]),
            "err_median_pct": round(100 * (med - it["kcal"]) / it["kcal"], 1),
            "ape_mean_pct": round(100 * st.mean(abs(p - it["kcal"]) / it["kcal"] for p in preds), 1),
            "cv_pct": round(100 * st.pstdev(preds) / st.mean(preds), 1),
            "protein_median": round(st.median(r["protein"] for r in v if r["protein"] is not None), 1),
            "fat_median": round(st.median(r["fat"] for r in v if r["fat"] is not None), 1),
            "carbs_median": round(st.median(r["carbs"] for r in v if r["carbs"] is not None), 1),
        })
item_rows.sort(key=lambda r: (r["set"], r["item"], MODE_ORDER.index(r["mode"]), MODEL_ORDER.index(r["model"]), EFFORT_ORDER.index(r["effort"])))

# Daily simulation: 3 dishes + 1 snack per day, one random run each.
daily = []
for model in MODEL_ORDER:
    for effort in EFFORT_ORDER:
        snack_runs = by_item(groups.get(("snack", "photo", model, effort), []))
        for mode in MODE_ORDER:
            dish_runs = by_item(groups.get(("dish", mode, model, effort), []))
            if len(dish_runs) < 3 or not snack_runs:
                continue
            dkeys, skeys = list(dish_runs), list(snack_runs)
            errs, signed = [], []
            for _ in range(5000):
                chosen = [rng.choice(dish_runs[k]) for k in rng.sample(dkeys, 3)] + [rng.choice(snack_runs[rng.choice(skeys)])]
                pred = sum(r["kcal"] for r in chosen)
                gt = sum(r["gt_kcal"] for r in chosen)
                errs.append(abs(pred - gt) / gt)
                signed.append((pred - gt) / gt)
            errs.sort()
            daily.append({
                "config": f"day|{mode}|{model}|{effort}", "mode": mode, "model": model, "model_name": MODEL_NAME[model],
                "effort": effort, "label": f"{MODEL_NAME[model]} · {effort}",
                "day_mape": round(100 * st.mean(errs), 1), "day_median": round(100 * errs[len(errs) // 2], 1),
                "day_p90": round(100 * errs[int(0.9 * len(errs))], 1),
                "day_within10": round(100 * sum(e <= 0.10 for e in errs) / len(errs), 1),
                "day_within20": round(100 * sum(e <= 0.20 for e in errs) / len(errs), 1),
                "day_bias": round(100 * st.mean(signed), 1),
            })

dataset_rows = [{
    "item": d["id"], "name": d["name"], "set": d["set"], "gt_kcal": d["kcal"], "gt_protein": d["protein"],
    "gt_fat": d["fat"], "gt_carbs": d["carbs"], "gt_mass_g": d.get("mass"), "caption": d.get("caption") or "",
    "hint": d.get("hint", ""), "cooked": d.get("cooked", ""), "rough": d.get("rough", ""),
    "main_weight": d.get("main_weight", ""), "weighed": d.get("weighed", ""), "gt_source": d["gt_source"],
    "photo_license": d.get("license", ""), "photo_page": d.get("photo_page", ""),
} for d in items.values()]

raw_rows = [{k: r[k] for k in ["set", "mode", "model", "effort", "item", "rep", "kcal", "protein", "fat", "carbs",
                                 "grams", "confidence", "gt_kcal", "cost", "latency", "out_tokens", "thinking_tokens"]}
            for r in runs]


def dump(name, rows):
    if not rows:
        return
    json.dump(rows, open(os.path.join(OUT, name + ".json"), "w"), ensure_ascii=False)
    with open(os.path.join(OUT, name + ".csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


dump("summary", summary)
dump("items", item_rows)
dump("daily", daily)
dump("dataset", dataset_rows)
dump("runs", raw_rows)

print(f"runs={len(runs)} ok={sum(r['ok'] for r in runs)} groups={len(groups)}")
print(f"{'config':32} {'n':>4} {'MAPE':>6} {'CI':>13} {'≤20%':>6} {'bias':>6} {'CV':>5} {'P%':>5} {'F%':>5} {'C%':>5} {'$/1k':>7} {'sec':>5}")
for s in summary:
    print(f"{s['config']:32} {s['parsed']:4} {s['mape']:6.1f} [{s['mape_lo']:5.1f},{s['mape_hi']:5.1f}] {s['within20']:6.1f} {s['bias']:6.1f} {s['cv']:5.1f} "
          f"{s['wape_protein']:5.0f} {s['wape_fat']:5.0f} {s['wape_carbs']:5.0f} {s['cost_per_1000']:7.2f} {s['latency_s']:5.1f}")
print()
for d in daily:
    print(f"{d['config']:28} dayMAPE={d['day_mape']:5.1f} med={d['day_median']:5.1f} ≤10%={d['day_within10']:5.1f} ≤20%={d['day_within20']:5.1f} bias={d['day_bias']:5.1f}")
