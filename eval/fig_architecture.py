"""Architecture figure (grayscale-safe): broker, inference, compile, ephemeral role/views, agent, widening."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(7.0, 3.6))
ax.set_xlim(0, 100); ax.set_ylim(0, 52); ax.axis("off")

def box(x, y, w, h, text, fill="#ffffff", hatch=None, lw=1.2, fs=7.2, bold=False):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fill, ec="black", lw=lw, hatch=hatch)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", wrap=True)

def arrow(x1, y1, x2, y2, text="", style="-|>", ls="-", fs=6.5, off=(0, 1.2)):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=9, lw=1.0, ls=ls, color="black"))
    if text:
        ax.text((x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1], text, fontsize=fs, ha="center", va="bottom")

# trust boundary
ax.add_patch(FancyBboxPatch((1, 21), 52, 29, boxstyle="round,pad=0.3", fc="#f2f2f2", ec="black", lw=0.8, ls="--"))
ax.text(2.5, 47.5, "Trusted broker (A3)", fontsize=7, style="italic")
box(4, 36, 21, 8, "Scope inference\nLLM proposal + linking\n+ grounding + k + FK closure")
box(29, 36, 21, 8, "Compiler\nscope $\\rightarrow$ DDL\n(ephemeral objects)")
box(4, 24, 21, 8, "Semantic layer\ncatalog + dataset\ndescriptions, FKs")
box(29, 24, 21, 8, "Widening check\nbound by $E(u)$, policy,\naudit log")
arrow(14.5, 32, 14.5, 36)
arrow(25.5, 40, 29, 40)
ax.text(27.2, 44.6, "$S(t)\\sqcap E(u)$", fontsize=6.3, ha="center")
arrow(39.5, 32, 39.5, 36)
ax.text(41, 33.2, "approved", fontsize=6.3)

# database
ax.add_patch(FancyBboxPatch((57, 2), 41, 48, boxstyle="round,pad=0.3", fc="#ffffff", ec="black", lw=0.8))
ax.text(58.5, 47.5, "PostgreSQL (A1)", fontsize=7, style="italic")
box(60, 36, 35, 8, "schema tse_<id>: security_barrier views\nowned by user role U  (grants + RLS = $E(u)$)", fill="#d9d9d9")
box(60, 24, 16, 8, "tse_r_<id>\nNOLOGIN\nSELECT on views", fill="#ffffff")
box(79, 24, 16, 8, "tse_l_<id>\nLOGIN proxy\nINHERIT, no SET", fill="#ffffff")
box(60, 3, 35, 9.5, "base tables (owner role; RLS enabled)\nPUBLIC: no privileges\nuser role U: column grants + row policy", fill="#ececec")
arrow(50, 40, 60, 40)
ax.text(55, 41.0, "create /\ndrop", fontsize=6.0, ha="center", va="bottom")
arrow(96.6, 36, 96.6, 12.8, "", style="-|>")
ax.text(98.3, 24.5, "evaluated as U", fontsize=6.3, rotation=90, ha="center", va="center")
arrow(79, 28, 76.2, 28)

# agent
box(4, 4, 30, 11, "LLM agent\nrun_query(sql), request_access(...)\nsubmit_answer(sql, answer)", fill="#ffffff", bold=False)
ax.text(19, 1.0, "untrusted content can inject instructions", fontsize=6.3, ha="center", style="italic")
arrow(34, 12, 86, 24, "")
ax.text(42, 15.6, "only credential: tse_l_<id>", fontsize=6.3, rotation=12.5)
arrow(26, 15, 35, 24, "", ls="--")
ax.text(31.5, 17.0, "widening\nrequest", fontsize=6.3)
arrow(2.2, 36.5, 2.2, 15.2, "", style="<|-")
ax.text(3, 18.5, "task\ntext", fontsize=6.3)
plt.tight_layout()
plt.savefig("paper/figs/architecture.pdf", bbox_inches="tight")
print("ok")
