#!/usr/bin/env python3
"""Build docs/index.html: a standalone, bilingual (EN/UK) report page for GitHub Pages.

Reads benchmark/out/*.json and embeds them into one HTML file; charts use Chart.js from a CDN.
Usage: python3 benchmark/build_site.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
DOCS = os.path.join(os.path.dirname(HERE), "docs")


def load(name):
    return json.load(open(os.path.join(OUT, name + ".json")))


summary = [{k: r[k] for k in ("config", "set", "mode", "model", "model_name", "effort", "label", "items", "mape",
                              "mape_lo", "mape_hi", "within10", "within20", "bias", "cv", "wape_protein",
                              "wape_fat", "wape_carbs", "latency_s", "cost_per_1000")} for r in load("summary")]
daily = load("daily")
items = [{k: r[k] for k in ("item", "set", "mode", "model", "effort", "gt_kcal", "median", "min", "max",
                            "err_median_pct")} for r in load("items")]
dataset = [{"item": r["item"], "name": r["name"], "set": r["set"], "gt_kcal": r["gt_kcal"]} for r in load("dataset")]
runs_total = len(load("runs"))

EN_NAMES = {
    "Батат, полуниця …": "Sweet potato, strawberries …", "Курка, броколі …": "Chicken, broccoli …",
    "Батат, омлет з яєчних білків …": "Sweet potato, egg-white omelet …",
    "Лосось, помідори черрі …": "Salmon, cherry tomatoes …", "Лосось, стручкова квасоля …": "Salmon, green beans …",
    "Цвітна капуста, булгур …": "Cauliflower, bulgur …", "Фарш з індички, піца з сиром …": "Ground turkey, cheese pizza …",
    "Яєчня-скрембл, ананас …": "Scrambled eggs, pineapple …", "Курка гриль, помідори черрі …": "Grilled chicken, cherry tomatoes …",
    "Тофу, рукола …": "Tofu, arugula …", "Яєчня-скрембл, брюссельська капуста …": "Scrambled eggs, Brussels sprouts …",
    "Груша, виноград …": "Pear, grapes …", "Диня, свинина …": "Melon, pork …", "Курячі стегна, броколі …": "Chicken thighs, broccoli …",
    "Курка, помідори черрі …": "Chicken, cherry tomatoes …", "Омлет з яєчних білків, бекон …": "Egg-white omelet, bacon …",
    "Яловичина, паста пенне …": "Beef, penne pasta …", "Піца, курка …": "Pizza, chicken …",
    "Яєчня-скрембл, бекон з індички …": "Scrambled eggs, turkey bacon …", "Салат з тунцем, смажений рис …": "Tuna salad, fried rice …",
    "Мигдаль, мала жменя": "Almonds, small handful", "Мигдаль, жменя": "Almonds, handful",
    "Мигдаль, велика жменя": "Almonds, large handful", "Мигдаль, повна тарілка": "Almonds, full plate",
    "Яблуко": "Apple", "Велике печиво": "Large cookie", "Брауні": "Brownie", "Шоколадне печиво": "Chocolate cookie",
    "Snickers в упаковці": "Snickers in wrapper", "Mars в упаковці": "Mars in wrapper",
    "Twix (дві палички, без упаковки)": "Twix (two bars, no wrapper)", "Oreo, 2 печива": "Oreo, 2 cookies",
    "Плитка Milka 100 г (без упаковки)": "Milka bar 100 g (no wrapper)", "Біг Мак": "Big Mac",
    "Біг Мак меню (середнє, з колою)": "Big Mac meal (medium, with cola)",
}
for d in dataset:
    d["name_uk"] = d["name"]
    d["name_en"] = EN_NAMES.get(d["name"], d["name"])
    del d["name"]

DATA = {"summary": summary, "daily": daily, "items": items, "dataset": dataset, "runs": runs_total}

TEMPLATE = open(os.path.join(HERE, "site_template.html"), encoding="utf-8").read()
html = TEMPLATE.replace("/*DATA*/null", json.dumps(DATA, ensure_ascii=False, separators=(",", ":")))
os.makedirs(DOCS, exist_ok=True)
with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as f:
    f.write(html)
open(os.path.join(DOCS, ".nojekyll"), "w").close()
print("wrote docs/index.html", len(html), "bytes")
