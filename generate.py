#!/usr/bin/env python3
"""Generate the terminal-style profile card (EN/ES, light/dark) and the contribution snake.

Standard library only. Needs GH_TOKEN (see update.sh). Stops if the GitHub API fails.
"""
import datetime
import json
import math
import os
import random
import sys
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USER = "d4nnABR"
HANDLE = "d4nnabr@github:~$"
OUT = Path(__file__).resolve().parent
FONT = "ui-monospace, 'SF Mono', SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
CW = 0.6  # monospace advance as a fraction of the font size

THEMES = {
    "dark": dict(bg="#000000", fg="#f2f2f2", dim="#8c8c8c", faint="#262626", line="#3d3d3d", star="#ffffff",
                 cells=["#161616", "#3a3a3a", "#6e6e6e", "#a6a6a6", "#f2f2f2"], snake="#ffffff"),
    "light": dict(bg="#ffffff", fg="#0d0d0d", dim="#6b6b6b", faint="#e6e6e6", line="#c2c2c2", star="#000000",
                  cells=["#ececec", "#c4c4c4", "#8c8c8c", "#505050", "#0d0d0d"], snake="#000000"),
}

CONTENT = {
    "en": dict(
        panel="NAV.MAP",
        tiles=["contributions / year", "current streak", "public repos", "stars"],
        streak_unit=("days", "day"),
        sections=[
            ("ROLE", "rows", [("role", "Data Analyst | Accounting Automation")]),
            ("STATUS", "rows", [("now", "Data Science specialization + MSc IT Mgmt"),
                                 ("goal", "Data analysis / BI role")]),
            ("TOOLS", "pills", [("daily", ["SQL", "Python", "Power BI", "Power Automate", "Git",
                                           "PostgreSQL", "VBA", "SAP", "Linux", "Claude Code"])]),
            ("STACK", "pills", [("frontend", ["HTML", "CSS", "JavaScript", "Astro"]),
                                ("backend", ["Python", "Bash", "Linux", "VBA", "pytest"]),
                                ("database", ["PostgreSQL", "SQL", "SQLite"]),
                                ("cloud", ["Databricks", "Kafka", "Azure Data Lake", "Vercel"]),
                                ("bi", ["Power BI", "Looker Studio", "Excel", "Power Query"]),
                                ("automation", ["Power Automate", "Power Apps", "SharePoint"]),
                                ("data/ml", ["pandas", "NumPy", "scikit-learn", "TensorFlow", "PyTorch", "PySpark", "MLflow", "R"])]),
            ("PROJECTS", "rows", [("acme-ev", "Kafka telemetry + live dashboard, Databricks"),
                                   ("churn-bank", "Customer churn analysis, Looker Studio"),
                                   ("attrition", "Employee attrition model + dashboard"),
                                   ("bike-sales", "PySpark + Spark ML capstone on Databricks"),
                                   ("xray-cnn", "Pneumonia classification, transfer learning")]),
            ("TRACK RECORD", "rows", [("experience", "4 years in data: reporting, BI, automation"),
                                       ("sap-reports", "Monthly automation, ~6 h/month saved per person"),
                                       ("certified", "PL-900 Power Platform; Lean Six Sigma Yellow Belt")]),
            ("CONTACT", "rows", [("web", "garyabrigo.github.io"),
                                  ("linkedin", "linkedin.com/in/garyabr"),
                                  ("email", "abrigogary@gmail.com")]),
        ],
    ),
    "es": dict(
        panel="NAV.MAP",
        tiles=["contribuciones / año", "racha actual", "repos públicos", "estrellas"],
        streak_unit=("días", "día"),
        sections=[
            ("ROL", "rows", [("rol", "Analista de Datos | Automatización contable")]),
            ("ESTADO", "rows", [("ahora", "Especialización en Data Science + Maestría IT"),
                                 ("meta", "Rol de análisis de datos / BI")]),
            ("HERRAMIENTAS", "pills", [("diarias", ["SQL", "Python", "Power BI", "Power Automate", "Git",
                                                    "PostgreSQL", "VBA", "SAP", "Linux", "Claude Code"])]),
            ("STACK", "pills", [("frontend", ["HTML", "CSS", "JavaScript", "Astro"]),
                                ("backend", ["Python", "Bash", "Linux", "VBA", "pytest"]),
                                ("base de datos", ["PostgreSQL", "SQL", "SQLite"]),
                                ("nube", ["Databricks", "Kafka", "Azure Data Lake", "Vercel"]),
                                ("bi", ["Power BI", "Looker Studio", "Excel", "Power Query"]),
                                ("procesos", ["Power Automate", "Power Apps", "SharePoint"]),
                                ("datos/ml", ["pandas", "NumPy", "scikit-learn", "TensorFlow", "PyTorch", "PySpark", "MLflow", "R"])]),
            ("PROYECTOS", "rows", [("acme-ev", "Telemetría con Kafka + dashboard en vivo, Databricks"),
                                    ("churn-banco", "Análisis de fuga de clientes, Looker Studio"),
                                    ("rotación", "Modelo de fuga de empleados + tablero"),
                                    ("bike-sales", "Proyecto PySpark + Spark ML en Databricks"),
                                    ("rayos-x", "Clasificación de neumonía, transfer learning")]),
            ("TRAYECTORIA", "rows", [("experiencia", "4 años en datos: reporting, BI, automatización"),
                                      ("reportes-sap", "Automatización mensual, ~6 h/mes ahorradas por persona"),
                                      ("certificado", "PL-900 Power Platform; Lean Six Sigma Yellow Belt")]),
            ("CONTACTO", "rows", [("web", "garyabrigo.github.io"),
                                   ("linkedin", "linkedin.com/in/garyabr"),
                                   ("email", "abrigogary@gmail.com")]),
        ],
    ),
}

QUERY = """query($login:String!){user(login:$login){
 contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}
 repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC){totalCount nodes{stargazerCount}}}}"""
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def fetch():
    token = os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("GH_TOKEN is not set. Run: GH_TOKEN=$(gh auth token) python3 generate.py")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-card"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.load(r)
        user = body["data"]["user"]
        cal = user["contributionsCollection"]["contributionCalendar"]
        repos = user["repositories"]
    except Exception as e:  # network, auth, schema: never fall back to made-up numbers
        sys.exit(f"GitHub API call failed, nothing was written: {e!r}")
    if repos["totalCount"] > len(repos["nodes"]):
        sys.exit("More than 100 public repos: add pagination before trusting the star count.")
    days = []
    for w in cal["weeks"]:
        for d in w["contributionDays"]:
            date = datetime.date.fromisoformat(d["date"])
            days.append(dict(col=0, date=date, count=d["contributionCount"],
                             level=LEVELS[d["contributionLevel"]], row=(date.weekday() + 1) % 7))
    # column = week index (calendar weeks start on Sunday)
    col = 0
    for i, d in enumerate(days):
        if i and d["row"] == 0:
            col += 1
        d["col"] = col
    streak = 0
    for i, d in enumerate(reversed(days)):
        if d["count"] > 0:
            streak += 1
        elif i == 0:
            continue  # today may still be empty
        else:
            break
    return dict(total=cal["totalContributions"], streak=streak, repos=repos["totalCount"],
                stars=sum(n["stargazerCount"] for n in repos["nodes"]), days=days)


class Card:
    def __init__(self, theme, content, stats):
        self.t, self.c, self.s = THEMES[theme], content, stats
        self.parts, self.n = [], 0

    def delay(self):
        self.n += 1
        return f"animation-delay:{0.25 + self.n * 0.09:.2f}s"

    def add(self, svg, fade=True):
        if fade:
            svg = f'<g class="ln" style="{self.delay()}">{svg}</g>'
        self.parts.append(svg)

    @staticmethod
    def text(x, y, s, cls="", size=12):
        return f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}">{escape(s)}</text>'

    def pills(self, items, x, y, maxx):
        out, cx = [], x
        for it in items:
            w = len(it) * 11 * CW + 18
            if cx + w > maxx:
                cx, y = x, y + 36
            out.append(f'<rect x="{cx:.1f}" y="{y - 13}" width="{w:.1f}" height="19" rx="9.5" class="pill"/>'
                       f'<text x="{cx + 9:.1f}" y="{y}" class="fg" font-size="11">{escape(it)}</text>')
            cx += w + 6
        return "".join(out), y

    def starfield(self, rng, x0, y0, w, h, count, bright):
        out = []
        for _ in range(count):
            x, y = rng.uniform(x0, x0 + w), rng.uniform(y0, y0 + h)
            r = rng.choice([0.6, 0.8, 1.0, 1.3]) if bright else rng.choice([0.5, 0.7, 0.9])
            dur, dl = rng.uniform(2.4, 6.5), -rng.uniform(0, 6)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" class="star" '
                       f'style="animation-duration:{dur:.1f}s;animation-delay:{dl:.1f}s"/>')
        return "".join(out)

    def panel(self, x, y, w, h):
        rng = random.Random(7)
        cx, cy = x + w / 2, y + max(160, (h - 110) / 2)
        g = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" class="frame"/>',
             self.starfield(rng, x + 4, y + 4, w - 8, h - 8, 70, True),
             self.text(x + 14, y + 22, self.c["panel"], "dim", 11)]
        g.append(f'<ellipse cx="{cx}" cy="{cy}" rx="140" ry="140" class="orbit"/>'
                 f'<ellipse cx="{cx}" cy="{cy}" rx="84" ry="84" class="orbit"/>'
                 f'<circle cx="{cx}" cy="{cy}" r="7" class="solid"/>'
                 f'<circle cx="{cx}" cy="{cy}" r="11" class="orbit"/>')
        g.append(f'<g class="spin a" style="transform-origin:{cx}px {cy}px"><circle cx="{cx + 84}" cy="{cy}" r="3.4" class="solid"/></g>'
                 f'<g class="spin b" style="transform-origin:{cx}px {cy}px"><circle cx="{cx - 140}" cy="{cy}" r="4.6" class="hollow"/>'
                 f'<circle cx="{cx - 140}" cy="{cy}" r="1.6" class="solid"/></g>')
        # TARS: four articulated slabs
        tx, ty = x + 52, y + h - 98
        for i in range(4):
            sx = tx + i * 17
            extra = ' style="animation-delay:-0.6s"' if i % 2 else ""
            g.append(f'<g class="slab"{extra}><rect x="{sx}" y="{ty}" width="13" height="70" rx="1.5" class="body"/>'
                     f'<line x1="{sx + 3}" y1="{ty + 8}" x2="{sx + 10}" y2="{ty + 8}" class="fgline"/></g>')
        g.append(self.text(tx + 32, y + h - 6, "TARS", "dim anchor-mid", 10))
        # Rocky: carapace and five legs
        rx_, ry_ = x + w - 92, y + h - 68
        pts = [(rx_ + r * math.cos(a), ry_ + r * math.sin(a))
               for a, r in [(-1.5, 19), (-0.55, 23), (0.4, 18), (1.2, 22), (2.1, 17), (2.95, 23), (3.9, 18), (4.6, 22)]]
        legs = []
        for k in range(5):
            a = -1.5708 + k * 1.25664
            p0 = (rx_ + 19 * math.cos(a), ry_ + 19 * math.sin(a))
            p1 = (rx_ + 36 * math.cos(a + 0.18), ry_ + 36 * math.sin(a + 0.18))
            p2 = (rx_ + 50 * math.cos(a), ry_ + 50 * math.sin(a))
            ph = "-1.1s" if k % 2 else "0s"
            legs.append(f'<g class="leg" style="transform-origin:{rx_:.1f}px {ry_:.1f}px;animation-delay:{ph}">'
                        f'<polyline points="{p0[0]:.1f},{p0[1]:.1f} {p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}" class="legline"/>'
                        f'<circle cx="{p2[0]:.1f}" cy="{p2[1]:.1f}" r="2.2" class="solid"/></g>')
        g.append("".join(legs))
        g.append(f'<polygon points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in pts)}" class="body"/>'
                 f'<circle cx="{rx_ - 6}" cy="{ry_ - 4}" r="1.3" class="dimfill"/>'
                 f'<circle cx="{rx_ + 7}" cy="{ry_ + 3}" r="1.6" class="dimfill"/>'
                 f'<circle cx="{rx_ - 2}" cy="{ry_ + 9}" r="1.1" class="dimfill"/>')
        g.append(self.text(rx_, y + h - 6, "ROCKY", "dim anchor-mid", 10))
        self.add("".join(g), fade=True)

    def tiles(self, x, y):
        s = self.s
        vals = [f'{s["total"]:,}', f'{s["streak"]} {self.c["streak_unit"][s["streak"] == 1]}', str(s["repos"]), str(s["stars"])]
        for i, (v, label) in enumerate(zip(vals, self.c["tiles"])):
            tx, ty = x + (i % 2) * 160, y + (i // 2) * 60
            self.add(f'<rect x="{tx}" y="{ty}" width="150" height="52" rx="5" class="frame"/>'
                     f'{self.text(tx + 12, ty + 25, v, "fg bold", 17)}'
                     f'{self.text(tx + 12, ty + 42, label, "dim", 10)}')
        return y + 120

    def build(self, lang_name):
        W, X0, X1, MAXX = 960, 364, 482, 932
        rng = random.Random(11)
        self.add(self.text(24, 38, HANDLE, "dim", 13)
                 + f'<text x="{24 + len(HANDLE) * 13 * CW + 8:.1f}" y="38" class="fg" font-size="13">whoami</text>')
        y = 92
        right = []
        for title, kind, rows in self.c["sections"]:
            self.add(self.text(X0, y, title, "dim bold", 11)
                     + f'<line x1="{X0 + len(title) * 11 * CW + 10:.1f}" y1="{y - 4}" x2="{MAXX}" y2="{y - 4}" class="rule"/>')
            y += 28
            for key, val in rows:
                kend = X0 + (len(key) + 1) * 12 * CW
                lead = f'<line x1="{kend + 4:.1f}" y1="{y - 3}" x2="{X1 - 8}" y2="{y - 3}" class="leader"/>'
                if kind == "rows":
                    self.add(self.text(X0, y, key, "dim", 12) + lead + self.text(X1, y, val, "fg", 12))
                    y += 31
                else:
                    svg, ly = self.pills(val, X1, y, MAXX)
                    self.add(self.text(X0, y, key, "dim", 12) + lead + svg)
                    y += 36 + (ly - y)
            y += 30
        right_end = y
        tiles_y = right_end - 30 - 112
        self.panel(24, 64, 316, tiles_y - 16 - 64)
        left_end = self.tiles(24, tiles_y)
        H = max(left_end, right_end) + 44
        cursor_y = H - 24
        self.add(self.text(24, cursor_y, HANDLE, "dim", 13)
                 + f'<rect x="{24 + len(HANDLE) * 13 * CW + 8:.1f}" y="{cursor_y - 12}" width="8" height="15" class="cursor"/>',
                 fade=False)
        bg_stars = self.starfield(rng, 0, 0, W, H, 55, False)
        t = self.t
        css = f"""
.fg{{fill:{t['fg']}}} .dim{{fill:{t['dim']}}} .bold{{font-weight:700}} .anchor-mid{{text-anchor:middle}}
text{{font-family:{FONT}}}
.frame{{fill:none;stroke:{t['line']};stroke-width:1}}
.rule{{stroke:{t['faint']};stroke-width:1}}
.leader{{stroke:{t['line']};stroke-width:1;stroke-dasharray:1 4;stroke-linecap:round}}
.pill{{fill:none;stroke:{t['line']};stroke-width:1}}
.orbit{{fill:none;stroke:{t['line']};stroke-width:1;stroke-dasharray:2 4}}
.solid{{fill:{t['fg']}}} .hollow{{fill:{t['bg']};stroke:{t['fg']};stroke-width:1}} .dimfill{{fill:{t['dim']}}}
.body{{fill:{t['bg']};stroke:{t['fg']};stroke-width:1.2}}
.fgline{{stroke:{t['fg']};stroke-width:1.2}}
.legline{{fill:none;stroke:{t['fg']};stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}}
.star{{fill:{t['star']};opacity:.2;animation:tw 4s ease-in-out infinite}}
.ln{{opacity:0;animation:fade .6s ease-out forwards}}
.cursor{{fill:{t['fg']};animation:blink 1.1s steps(1) infinite}}
.spin{{animation:rot 24s linear infinite}} .spin.b{{animation-duration:46s}}
.slab{{animation:walk 1.2s ease-in-out infinite alternate}}
.leg{{animation:wig 1.4s ease-in-out infinite alternate}}
@keyframes tw{{0%,100%{{opacity:.12}}50%{{opacity:.95}}}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes blink{{0%,50%{{opacity:1}}50.01%,100%{{opacity:0}}}}
@keyframes rot{{to{{transform:rotate(360deg)}}}}
@keyframes walk{{from{{transform:translateY(0)}}to{{transform:translateY(-5px)}}}}
@keyframes wig{{from{{transform:rotate(-7deg)}}to{{transform:rotate(7deg)}}}}
@media (prefers-reduced-motion:reduce){{.star,.ln,.cursor,.spin,.slab,.leg{{animation:none;opacity:1}}}}
"""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
                f'role="img" aria-label="Gary Abrigo, terminal-style profile card ({lang_name})">'
                f'<style>{css}</style><rect width="{W}" height="{H}" rx="10" fill="{t["bg"]}"/>'
                f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" class="frame"/>'
                f'{bg_stars}{"".join(self.parts)}</svg>')


def snake(theme, days):
    t = THEMES[theme]
    cell, gap, pad = 11, 3, 14
    step = cell + gap
    cols = max(d["col"] for d in days) + 1
    W, H = cols * step - gap + pad * 2, 7 * step - gap + pad * 2
    lead = 8  # off-screen steps before and after, so the loop jump is never visible
    path = [(-lead + i, 0) for i in range(lead)]
    for c in range(cols):
        rows = range(7) if c % 2 == 0 else range(6, -1, -1)
        path += [(c, r) for r in rows]
    last_row = path[-1][1]
    path += [(cols + i, last_row) for i in range(lead)]
    N = len(path)
    secs = N * 0.075
    pos = {p: i for i, p in enumerate(path)}

    def xy(c, r):
        return pad + c * step, pad + r * step

    cells, kf = [], []
    for d in days:
        x, y = xy(d["col"], d["row"])
        lvl = d["level"]
        anim = ""
        if lvl:
            p = pos[(d["col"], d["row"])] / N * 100
            q = min(p + 22, 98.5)
            name = f"e{d['col']}_{d['row']}"
            kf.append(f"@keyframes {name}{{0%,{p:.2f}%{{opacity:1}}{p + .4:.2f}%,{q:.2f}%{{opacity:.1}}{q + 1:.2f}%,100%{{opacity:1}}}}")
            anim = f' style="animation:{name} {secs:.1f}s linear infinite"'
        cells.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{t["cells"][lvl]}"{anim}/>')
    stops = "".join(f"{i / (N - 1) * 100:.3f}%{{transform:translate({xy(*p)[0]}px,{xy(*p)[1]}px)}}" for i, p in enumerate(path))
    kf.append(f"@keyframes run{{{stops}}}")
    # a negative delay shifts each segment back along the same path, one step apart
    segs = []
    for k in range(7):
        size = cell + 1 if k == 0 else cell
        delay = secs - k * (secs / N)
        segs.append(f'<rect width="{size}" height="{size}" rx="3" fill="{t["snake"]}" opacity="{1 - k * 0.11:.2f}" '
                    f'style="animation:run {secs:.1f}s linear infinite;animation-delay:-{delay:.3f}s"/>')
    segs.reverse()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
            f'aria-label="Contribution calendar with an animated snake">'
            f'<style>{"".join(kf)}@media (prefers-reduced-motion:reduce){{rect{{animation:none!important}}}}</style>'
            f'{"".join(cells)}{"".join(segs)}</svg>')


def main():
    stats = fetch()
    for lang, content in CONTENT.items():
        for theme in THEMES:
            svg = Card(theme, content, stats).build(lang)
            (OUT / f"card-{lang}-{theme}.svg").write_text(svg, encoding="utf-8")
    for theme in THEMES:
        (OUT / f"snake-{theme}.svg").write_text(snake(theme, stats["days"]), encoding="utf-8")
    print(f"ok: {stats['total']} contributions, streak {stats['streak']}, "
          f"{stats['repos']} repos, {stats['stars']} stars")


if __name__ == "__main__":
    main()
