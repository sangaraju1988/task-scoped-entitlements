"""Shared helpers for experiment drivers."""
import json, os, sys, subprocess, random, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tse import config, semantic_layer, infer
from tse.scope import Scope
from tse.policies.generate import generate

INF_MODEL_MAIN = "qwen2.5-coder:7b"     # preregistered inference model (trusted broker side)
INF_MODEL_SMALL = "llama3.2:3b"         # ablation: smaller inference model


def commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=config.ROOT).decode().strip()
    except Exception:
        return "unknown"


def load_tasks():
    return [json.loads(l) for l in open(os.path.join(config.DATA, "tasks", "tasks.jsonl"))]


def load_prep():
    return {json.loads(l)["task_id"]: json.loads(l) for l in open(os.path.join(config.RESULTS, "prep.jsonl"))}


_PROPS = {}
def proposals(model, variant):
    key = (model, variant)
    if key not in _PROPS:
        p = os.path.join(config.RESULTS, f"proposals_{model.replace(':', '_').replace('/', '_')}_{variant}.jsonl")
        _PROPS[key] = {}
        if os.path.exists(p):
            for l in open(p):
                r = json.loads(l)
                pr = r["proposal"]
                pr["columns"] = [tuple(x) for x in pr["columns"]]
                _PROPS[key][r["task_id"]] = pr
    return _PROPS[key]


_POL = {}
def entitlement(task, role, seed=1, frac=0.25):
    k = (task["pgdb"], seed, frac)
    if k not in _POL:
        sl = semantic_layer.get(task["pgdb"], task["dataset"], task["db_id"])
        _POL[k] = generate(sl, seed=seed, frac=frac)
    return _POL[k][role]


# TSE variants: (inference model, proposal variant, k, linking, closure)
VARIANTS = {
    "tse":        dict(model=INF_MODEL_MAIN, pvar="main", k=1, linking=True, closure=True),
    "tse_k0":     dict(model=INF_MODEL_MAIN, pvar="main", k=0, linking=True, closure=True),
    "tse_k2":     dict(model=INF_MODEL_MAIN, pvar="main", k=2, linking=True, closure=True),
    "tse_noclose": dict(model=INF_MODEL_MAIN, pvar="main", k=1, linking=True, closure=False),
    "tse_nosl":   dict(model=INF_MODEL_MAIN, pvar="nodesc", k=1, linking=False, closure=True),
    "tse_small":  dict(model=INF_MODEL_SMALL, pvar="main", k=1, linking=True, closure=True),
    "tse_haiku":  dict(model="claude-haiku-5-5", pvar="main", k=1, linking=True, closure=True),  # exploratory
}


def tse_scope(task, role, variant="tse", E=None):
    v = VARIANTS[variant]
    sl = semantic_layer.get(task["pgdb"], task["dataset"], task["db_id"])
    prop = proposals(v["model"], v["pvar"]).get(task["task_id"])
    if prop is None:
        raise KeyError(f"no cached proposal for {task['task_id']} ({v['model']},{v['pvar']})")
    E = E or entitlement(task, role)
    s, _, _ = infer.infer(task, sl, E, None, k=v["k"], use_linking=v["linking"], use_closure=v["closure"], proposal=prop)
    return s


def assign_cells(tasks, cells, seed=11):
    """Balanced assignment of (model, framework) cells to tasks within (dataset, difficulty) strata."""
    rng = random.Random(seed)
    strata = collections.defaultdict(list)
    for t in tasks:
        strata[(t["dataset"], t["difficulty"])].append(t["task_id"])
    out = {}
    offset = 0
    for k in sorted(strata):
        ids = sorted(strata[k]); rng.shuffle(ids)
        for i, tid in enumerate(ids):
            out[tid] = cells[(i + offset) % len(cells)]
        offset += len(ids)
    return out
