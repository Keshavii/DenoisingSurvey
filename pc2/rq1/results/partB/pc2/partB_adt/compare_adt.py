"""Part B scorecard for ADT: our rerun (mylog/) vs the authors' released logs (log/). Metrics @50 and @100."""
import glob, os, re, sys
root = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/repos/DenoisingRec")
def last(path):
    rec = ndcg = None
    for line in open(path, errors="ignore"):
        m = re.match(r"Recall ([\d.]+)-([\d.]+)", line)
        if m: rec = tuple(map(float, m.groups()))
        m = re.match(r"NDCG ([\d.]+)-([\d.]+)", line)
        if m: ndcg = tuple(map(float, m.groups()))
    return rec, ndcg
print(f"{'method':6s} {'dataset':12s} {'config':22s} {'R@50 paper':>10s} {'ours':>7s} {'gap':>7s} | {'N@50 paper':>10s} {'ours':>7s} {'gap':>7s} | {'R@100 gap':>9s} {'N@100 gap':>9s}")
for d in ("T_CE", "R_CE"):
    for f in sorted(glob.glob(f"{root}/{d}/log/*/*.log")):
        ds, name = f.split("/")[-2], os.path.basename(f)[:-4]
        method = "Plain" if name.endswith("_0-0") else ("T-CE" if d == "T_CE" else "R-CE")
        ours_f = f"{root}/{d}/mylog/{ds}/{name}.log"
        pr, pn = last(f)
        orr, on = last(ours_f) if os.path.exists(ours_f) else (None, None)
        if orr is None or on is None:
            print(f"{method:6s} {ds:12s} {name:22s} {pr[0]:10.4f} {'--':>7s} {'':7s} | {pn[0]:10.4f} {'--':>7s}"); continue
        g = lambda o, p: f"{100*(o/p-1):+6.1f}%"
        print(f"{method:6s} {ds:12s} {name:22s} {pr[0]:10.4f} {orr[0]:7.4f} {g(orr[0],pr[0])} | {pn[0]:10.4f} {on[0]:7.4f} {g(on[0],pn[0])} | {g(orr[1],pr[1]):>9s} {g(on[1],pn[1]):>9s}")
