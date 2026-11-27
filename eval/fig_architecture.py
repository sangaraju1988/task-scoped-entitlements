"""Architecture figure (grayscale-safe): broker, inference, compile, ephemeral role/views, agent, widening.
Drawn for two-column width (figure*), fonts >= 7.5 pt at print size."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FS = 8.5
fig, ax = plt.subplots(figsize=(7.6, 4.0))
ax.set_xlim(0, 104); ax.set_ylim(0, 56); ax.axis("off")


def box(x, y, w, h, text, fill="#ffffff", fs=FS):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fill, ec="black", lw=1.1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def arrow(x1, y1, x2, y2, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=10, lw=1.0, ls=ls, color="black"))


# trusted broker
ax.add_patch(FancyBboxPatch((1, 22), 54, 32, boxstyle="round,pad=0.3", fc="#f2f2f2", ec="black", lw=0.8, ls="--"))
ax.text(2.5, 51.3, "Trusted broker (A3)", fontsize=FS + 0.5, style="italic")
box(3.5, 38, 23, 10, "Scope inference\nLLM proposal, linking,\ngrounding, k, FK closure")
box(30.5, 38, 23, 10, "Compiler\nscope $\\rightarrow$ DDL\n(ephemeral objects)")
box(3.5, 25, 23, 9, "Semantic layer\ncatalog, descriptions,\nforeign keys")
box(30.5, 25, 23, 9, "Widening check\nbound by $E(u)$,\npolicy, audit log")
arrow(15, 34.4, 15, 37.6)
arrow(26.9, 43, 30.1, 43)
ax.text(28.5, 48.9, "$S(t)\\sqcap E(u)$", fontsize=FS, ha="center")
arrow(42, 34.4, 42, 37.6)
ax.text(43, 35.2, "approved", fontsize=FS - 0.5)

# database
ax.add_patch(FancyBboxPatch((59, 1), 44, 53, boxstyle="round,pad=0.3", fc="#ffffff", ec="black", lw=0.8))
ax.text(60.5, 51.3, "PostgreSQL (A1)", fontsize=FS + 0.5, style="italic")
box(61.5, 38, 39, 10, "schema tse_<id>:\nsecurity_barrier views owned by\nuser role U (grants + RLS = $E(u)$)", fill="#d9d9d9")
box(61.5, 23, 18, 10, "tse_r_<id>\nNOLOGIN\nSELECT on views")
box(82.5, 23, 18, 10, "tse_l_<id>\nLOGIN proxy\nINHERIT, no SET")
box(61.5, 3, 39, 11, "base tables (owner role, RLS on)\nPUBLIC: no privileges\nU: column grants + row policy", fill="#ececec")
arrow(53.9, 43, 61.1, 43)
ax.text(57.3, 44.6, "create/\ndrop", fontsize=FS - 1, ha="center", va="bottom")
arrow(81, 37.6, 81, 14.4)
ax.text(82, 18.5, "evaluated as U", fontsize=FS - 0.5, ha="left")
arrow(82.1, 28, 79.9, 28)

# agent
box(3.5, 4, 33, 11, "LLM agent\nrun_query(sql), request_access(...),\nsubmit_answer(sql, answer)")
ax.text(20, 0.6, "untrusted content can inject instructions", fontsize=FS - 0.5, ha="center", style="italic")
arrow(36.9, 13, 91, 22.6)
ax.text(46, 19.6, "only credential: tse_l_<id>", fontsize=FS - 0.5, rotation=10.5)
arrow(28, 15.4, 38, 24.6, ls="--")
ax.text(34.5, 18.2, "widening\nrequest", fontsize=FS - 0.5)
arrow(2.2, 37.6, 2.2, 15.4, style="<|-")
ax.text(2.9, 20, "task\ntext", fontsize=FS - 0.5)
plt.savefig("paper/figs/architecture.pdf", bbox_inches="tight")
print("ok")
