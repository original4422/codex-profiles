"""Generate the README illustration as an editable, dependency-free SVG."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCOUNTS = [
    ("01", "Personal", "#456CFA", "personal"),
    ("02", "Work", "#00947C", "work"),
    ("03", "Research", "#A56A22", "research"),
]


def render() -> str:
    parts = [
        """<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="560" viewBox="0 0 1280 560" role="img" aria-labelledby="title desc">
<title id="title">Codex Profiles: one Mac, independent accounts</title>
<desc id="desc">Personal, Work and Research each have a dedicated desktop launcher and CLI entry. More profiles can be added. This is a workflow illustration, not an application screenshot.</desc>
<rect width="1280" height="560" rx="24" fill="#F4F6F3"/>
<g font-family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif">
<text x="64" y="66" fill="#51665D" font-size="14" font-weight="700" letter-spacing="3">CODEX PROFILES / macOS</text>
<text x="64" y="129" fill="#172C22" font-size="44" font-weight="700">One Mac. Every account has a home.</text>
<text x="64" y="166" fill="#5D6B64" font-size="19">Dedicated Dock launchers. Account-scoped CLI. Your official app.</text>
"""
    ]
    for index, (number, label, color, identifier) in enumerate(ACCOUNTS):
        x = 64 + index * 360
        parts.append(f'''<g transform="translate({x},210)">
<rect width="336" height="245" rx="18" fill="#FFFFFF" stroke="#DAE1DB"/>
<rect x="24" y="24" width="64" height="64" rx="16" fill="{color}"/>
<text x="56" y="67" text-anchor="middle" fill="white" font-size="28" font-weight="700">{number}</text>
<text x="108" y="52" fill="#172C22" font-size="23" font-weight="700">{label}</text>
<text x="108" y="77" fill="#68766E" font-size="14">Independent profile</text>
<path d="M24 111 H312" stroke="#E5EAE6"/>
<text x="24" y="145" fill="#526359" font-size="14">DOCK</text>
<text x="98" y="145" fill="#172C22" font-size="16">Open {label}</text>
<text x="24" y="181" fill="#526359" font-size="14">CLI</text>
<text x="98" y="181" fill="#172C22" font-size="15" font-family="SFMono-Regular, Consolas, monospace">cli {identifier}</text>
<circle cx="31" cy="216" r="4" fill="{color}"/>
<text x="44" y="221" fill="#68766E" font-size="13">Separate sign-in and history</text>
</g>''')
    parts.append("""<text x="1192" y="337" fill="#85968A" font-size="44" text-anchor="middle">+</text>
<text x="64" y="512" fill="#526359" font-size="16">Add the profiles you need. No built-in two-account limit.</text>
<text x="1216" y="512" text-anchor="end" fill="#89958E" font-size="12">WORKFLOW OVERVIEW</text>
</g></svg>""")
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    (ROOT / "assets/overview.svg").write_text(render())
