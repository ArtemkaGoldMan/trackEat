#!/usr/bin/env python3
"""Food-photo calorie benchmark for Claude models.

Runs every (mode, model, effort, dish, repeat) combination through the Claude Code
CLI in headless mode (uses the signed-in subscription, no API key needed) and
appends one JSON line per call to results.jsonl. Re-running resumes: finished
keys are skipped.

Usage:
  CLAUDE_BIN=/path/to/claude python3 run_bench.py --modes photo --models haiku,sonnet \
      --efforts low,medium,high --reps 10 --workers 8
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = {
    "haiku": "claude-haiku-5-5",
    "sonnet": "claude-sonnet-5-5",
    "opus": "claude-opus-5-5",
}

SYSTEM_PROMPT = """Ти — мій асистент з обліку харчування. Я надсилаю фото їжі (іноді з описом або вагою продуктів). Твоє завдання — якомога точніше оцінити калорійність і БЖУ того, що на фото.

Як оцінювати:
1. Визнач кожен компонент страви.
2. Оціни вагу кожного компонента в грамах (готовий продукт, як подано). Для масштабу використовуй тарілку, миску, прибори та типові розміри порцій.
3. Врахуй ймовірні приховані калорії: олію, на якій готували, заправки, соуси.
4. Порахуй ккал, білки, жири, вуглеводи для кожного компонента за стандартними таблицями харчової цінності й підсумуй.
Якщо я вказав вагу продуктів — використовуй її, а не власну оцінку.
Якщо на фото упаковка з етикеткою — бери дані з етикетки (вага, ккал на 100 г). Для брендових продуктів і мереж (McDonald's тощо) використовуй їхні офіційні дані. Я живу в Україні, тож орієнтуйся на українські/європейські версії продуктів.

Відповідай ЛИШЕ JSON, без жодного тексту чи markdown навколо, у форматі:
{"items":[{"name":"...","grams":0,"kcal":0,"protein_g":0,"fat_g":0,"carbs_g":0}],"total":{"grams":0,"kcal":0,"protein_g":0,"fat_g":0,"carbs_g":0},"confidence":"low|medium|high"}"""

USER_TEXT = {
    "photo": "Оціни калорійність і БЖУ.",
    "hint": None,      # filled from dataset["hint"]
    "weighed": None,   # filled from dataset["weighed"]
}

lock = threading.Lock()


def build_message(dish, mode):
    with open(os.path.join(HERE, dish["image"]), "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    media = "image/png" if dish["image"].endswith(".png") else "image/jpeg"
    if mode == "photo":
        text = ((dish.get("caption") or "") + " " + USER_TEXT["photo"]).strip()
    else:
        text = dish[mode] + " " + USER_TEXT["photo"]
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}},
                {"type": "text", "text": text},
            ],
        },
    }


def parse_json(text):
    if not text:
        return None
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end < 0:
        return None
    try:
        return json.loads(t[start:end + 1])
    except json.JSONDecodeError:
        return None


def call_claude(claude_bin, model_id, effort, msg, timeout=420):
    cmd = [
        claude_bin, "-p",
        "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
        "--model", model_id, "--effort", effort,
        "--tools", "", "--system-prompt", SYSTEM_PROMPT,
        "--no-session-persistence", "--strict-mcp-config", "--setting-sources", "",
    ]
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    t0 = time.time()
    p = subprocess.run(cmd, input=json.dumps(msg) + "\n", capture_output=True, text=True,
                       timeout=timeout, env=env, cwd=HERE)
    wall = time.time() - t0
    result = None
    for line in p.stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            result = ev
    return result, wall, p.stderr[-2000:]


def run_one(args, task):
    mode, mkey, effort, dish, rep = task
    msg = build_message(dish, mode)
    last_err = None
    for attempt in range(5):
        try:
            res, wall, err = call_claude(args.claude_bin, MODELS[mkey], effort, msg)
        except subprocess.TimeoutExpired:
            last_err = "timeout"
            continue
        if res and not res.get("is_error") and res.get("result"):
            usage = res.get("usage", {})
            parsed = parse_json(res["result"])
            return {
                "key": f"{mode}|{mkey}|{effort}|{dish['id']}|{rep}",
                "mode": mode, "model": mkey, "effort": effort, "dish": dish["id"], "rep": rep,
                "parsed": parsed, "raw": res["result"] if parsed is None else None,
                "input_tokens": usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
                + usage.get("cache_read_input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "thinking_tokens": (usage.get("output_tokens_details") or {}).get("thinking_tokens"),
                "cost_usd": res.get("total_cost_usd"),
                "duration_ms": res.get("duration_ms"), "api_ms": res.get("duration_api_ms"),
                "wall_s": round(wall, 2), "attempts": attempt + 1,
            }
        last_err = (res or {}).get("result") or (res or {}).get("api_error_status") or err[-300:]
        time.sleep(min(60, 5 * 2 ** attempt))
    return {"key": f"{mode}|{mkey}|{effort}|{dish['id']}|{rep}", "mode": mode, "model": mkey,
            "effort": effort, "dish": dish["id"], "rep": rep, "error": str(last_err)[:500]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", default="photo")
    ap.add_argument("--models", default="haiku,sonnet,opus")
    ap.add_argument("--efforts", default="low,medium,high")
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dishes", type=int, default=0, help="limit number of items (0 = all)")
    ap.add_argument("--set", default="dish,snack", help="which item sets to include")
    ap.add_argument("--only", default="", help="comma-separated item ids to include")
    ap.add_argument("--out", default=os.path.join(HERE, "results.jsonl"))
    ap.add_argument("--claude-bin", default=os.environ.get("CLAUDE_BIN", "claude"))
    args = ap.parse_args()

    dishes = [d for d in json.load(open(os.path.join(HERE, "dataset.json")))
              if d["set"] in args.set.split(",")]
    if args.only:
        dishes = [d for d in dishes if d["id"] in args.only.split(",")]
    if args.dishes:
        dishes = dishes[: args.dishes]
    done = set()
    if os.path.exists(args.out):
        for line in open(args.out):
            r = json.loads(line)
            if "error" not in r:
                done.add(r["key"])
    tasks = []
    # Interleave so partial runs still cover every config evenly.
    for rep in range(args.reps):
        for dish in dishes:
            for mode in args.modes.split(","):
                for mkey in args.models.split(","):
                    for effort in args.efforts.split(","):
                        if f"{mode}|{mkey}|{effort}|{dish['id']}|{rep}" not in done:
                            tasks.append((mode, mkey, effort, dish, rep))
    print(f"{len(tasks)} tasks to run ({len(done)} already done)", flush=True)
    n_ok = n_err = 0
    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as ex, open(args.out, "a") as out:
        futs = [ex.submit(run_one, args, t) for t in tasks]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            with lock:
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
                out.flush()
            if "error" in r:
                n_err += 1
                print("ERR", r["key"], r["error"][:200], flush=True)
            else:
                n_ok += 1
            if i % 25 == 0 or i == len(tasks):
                el = time.time() - t0
                print(f"[{i}/{len(tasks)}] ok={n_ok} err={n_err} elapsed={el/60:.1f}m "
                      f"eta={el/i*(len(tasks)-i)/60:.1f}m", flush=True)


if __name__ == "__main__":
    main()
