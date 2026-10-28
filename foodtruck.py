#!/usr/bin/env python3
"""FOOD TRUCK GAME solver.   python3 foodtruck.py [--teams 8] [--trucks 10] [--pub 300] [--priv 100]

Model: zone base popularity is a permutation of 800..1800 (persistent across days); each day
demand = base + U(-300,300).  Public forecast within --pub of actual, private within --priv.
Posterior is exact over all 720 base permutations, using every forecast/actual from every day.
Your customers at zone z = x_z * D_z / (O_z + x_z)  (O_z = other teams' trucks there).
Allocation = greedy marginal gain (optimal: the objective is concave in x_z).

  pub 1200 900 1500 1700 1000 1300   public forecasts for zones 1..6 (today)
  priv 3 1450                        private forecast for zone 3 (repeat for the 2nd one)
  est                                posterior demand per zone + base probabilities
  alloc [N]                          recommended trucks (N defaults to --trucks)
  herd K                             others' model: share ∝ public^K (1=proportional, 3=crowd the top, 0=even)
  others 12 8 20 15 9 6              other teams' trucks per zone if you know/guess them (overrides herd)
  try 3 2 2 1 1 1                    expected customers for a specific allocation
  actual 3 1460  | actual 1460 1180 ...   true demand after the round (or customers/truck * trucks)
  next                               start the next day       undo   remove last entry today
  teams N | help | quit
"""
import itertools, math, sys

BASES = (800, 1000, 1200, 1400, 1600, 1800)
SHOCK = 300
GRID = list(range(-SHOCK, SHOCK + 1, 5))
Z = 6

def lik(x, f, w):
    """Soft 'within w' likelihood: 1 inside the band, fast Gaussian decay outside (robust to bad bounds)."""
    d = abs(x - f) - w
    return 1.0 if d <= 0 else math.exp(-(d / 40.0) ** 2)

class Model:
    def __init__(self, pub=300, priv=100):
        self.pub, self.priv = pub, priv
        self.days = [[[] for _ in range(Z)]]      # days[d][z] = [(value, width)]

    @property
    def today(self): return self.days[-1]

    def add(self, z, value, width): self.today[z].append((value, width))

    def shock_w(self, obs, b):
        return [math.prod(lik(b + s, f, w) for f, w in obs) for s in GRID]

    def base_post(self):
        L = [[math.prod(sum(self.shock_w(day[z], b)) / len(GRID) for day in self.days) for b in BASES] for z in range(Z)]
        P = [[0.0] * 6 for _ in range(Z)]; tot = 0.0
        for perm in itertools.permutations(range(6)):
            w = math.prod(L[z][perm[z]] for z in range(Z))
            tot += w
            for z in range(Z): P[z][perm[z]] += w
        if tot == 0: return [[1 / 6] * 6 for _ in range(Z)]
        return [[p / tot for p in row] for row in P]

    def demand(self):
        """[(mean, sd)] of today's demand per zone."""
        P, out = self.base_post(), []
        for z in range(Z):
            m1 = m2 = tot = 0.0
            for i, b in enumerate(BASES):
                if P[z][i] < 1e-12: continue
                ws = self.shock_w(self.today[z], b); s = sum(ws)
                if s == 0: continue
                for sh, w in zip(GRID, ws):
                    p = P[z][i] * w / s; d = b + sh
                    m1 += p * d; m2 += p * d * d; tot += p
            m = m1 / tot; out.append((m, math.sqrt(max(m2 / tot - m * m, 0))))
        return out, P

def others_model(public, n_other, herd=1.0, override=None):
    if override: return [float(o) for o in override]
    if not public: return [n_other / Z] * Z
    wts = [max(p, 1) ** herd for p in public]; s = sum(wts)
    return [n_other * w / s for w in wts]

def value(x, D, O):
    return sum(xi * d / (o + xi) if xi else 0.0 for xi, d, o in zip(x, D, O))

def allocate(D, O, n):
    x = [0] * Z
    for _ in range(n):
        gains = [d * (x[z] + 1) / (O[z] + x[z] + 1) - (d * x[z] / (O[z] + x[z]) if x[z] else 0) for z, d in enumerate(D)]
        x[max(range(Z), key=lambda z: gains[z])] += 1
    return x

class App:
    def __init__(self, teams=8, trucks=10, pub=300, priv=100):
        self.m, self.teams, self.trucks = Model(pub, priv), teams, trucks
        self.public, self.herd, self.override, self.log = None, 1.0, None, []

    def O(self):
        return others_model(self.public, (self.teams - 1) * self.trucks, self.herd, self.override)

    def run(self, line):
        p = line.split()
        if not p: return True
        c, a = p[0].lower(), p[1:]
        m = self.m
        if c == "pub":
            assert len(a) == Z, "need 6 numbers"
            self.public = [float(v) for v in a]
            for z, v in enumerate(self.public): m.add(z, float(v), m.pub); self.log.append(z)
            print("  public set; now add privates (priv ZONE VALUE) then alloc")
        elif c == "priv":
            z = int(a[0]) - 1; m.add(z, float(a[1]), m.priv); self.log.append(z); print(f"  zone {z+1}: private {a[1]} (±{m.priv})")
        elif c == "actual":
            if len(a) == Z: pairs = list(enumerate(map(float, a)))
            else: pairs = [(int(a[0]) - 1, float(a[1]))]
            for z, v in pairs: m.add(z, v, 3); self.log.append(z)
            print("  recorded actual demand (feeds base estimate for later days)")
        elif c == "undo":
            if self.log: z = self.log.pop(); m.today[z].pop(); print(f"  removed last entry for zone {z+1}")
        elif c == "next":
            m.days.append([[] for _ in range(Z)]); self.public, self.override, self.log = None, None, []
            print(f"  day {len(m.days)} started; enter pub ...")
        elif c == "est":
            D, P = m.demand()
            print("  zone   E[demand]    sd   " + "  ".join(f"{b:>5}" for b in BASES))
            for z in range(Z):
                print(f"  {z+1:>4} {D[z][0]:>10.0f} {D[z][1]:>6.0f}   " + "  ".join(f"{q:5.0%}" if q > 0.005 else "    ." for q in P[z]))
        elif c in ("alloc", "a"):
            n = int(a[0]) if a else self.trucks
            D = [d for d, _ in m.demand()[0]]; O = self.O(); x = allocate(D, O, n)
            ev = value(x, D, O)
            print("  zone  E[D]  others  YOU  cust/truck")
            for z in range(Z):
                print(f"  {z+1:>4} {D[z]:>5.0f} {O[z]:>7.1f} {x[z]:>4}  {D[z] / (O[z] + x[z]) if O[z] + x[z] else 0:>9.1f}")
            print(f"  SEND: " + "  ".join(f"Z{z+1}:{x[z]}" for z in range(Z)) + f"    expected customers {ev:.0f}")
            alt = {"even others": others_model(None, sum(O)), "herd^3 others": others_model(self.public, sum(O), 3.0)}
            for k, Oa in alt.items():
                xa = allocate(D, Oa, n); print(f"  if {k}: " + " ".join(map(str, xa)) + f"  (your plan there: {value(x, D, Oa):.0f} vs best {value(xa, D, Oa):.0f})")
        elif c == "try":
            x = [int(v) for v in a]; D = [d for d, _ in m.demand()[0]]
            print(f"  expected customers {value(x, D, self.O()):.0f}")
        elif c == "herd": self.herd, self.override = float(a[0]), None; print(f"  others share ∝ public^{self.herd}")
        elif c == "others": self.override = [float(v) for v in a]; print("  others fixed:", self.override)
        elif c == "teams": self.teams = int(a[0]); print("  teams =", self.teams)
        elif c in ("help", "h", "?"): print(__doc__)
        elif c in ("quit", "q", "exit"): return False
        else: print("  unknown; help")
        return True

def arg(argv, k, d):
    return type(d)(argv[argv.index(k) + 1]) if k in argv else d

def main(argv):
    app = App(arg(argv, "--teams", 8), arg(argv, "--trucks", 10), arg(argv, "--pub", 300.0), arg(argv, "--priv", 100.0))
    print(__doc__)
    while True:
        try:
            if not app.run(input(f"day{len(app.m.days)}> ")): break
        except (EOFError, KeyboardInterrupt): print(); break
        except (IndexError, ValueError, AssertionError) as e: print("  bad input:", e)

if __name__ == "__main__":
    main(sys.argv[1:])
