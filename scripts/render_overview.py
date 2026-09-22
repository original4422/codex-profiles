"""Generate the README illustration as an editable, dependency-free SVG."""

from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCOUNTS = [
    ("01", "Personal", "个人账号", "#456CFA", "personal"),
    ("02", "Work", "工作账号", "#00947C", "work"),
    ("03", "Research", "研究账号", "#A56A22", "research"),
]


def render(*, chinese: bool = False) -> str:
    def text(english: str, translated: str) -> str:
        return escape(translated if chinese else english)

    parts = [
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="560" viewBox="0 0 1280 560" role="img" aria-labelledby="title desc" lang="{"zh-CN" if chinese else "en"}">
<title id="title">{text("Codex Profiles: one Mac, independent accounts", "Codex Profiles：一台 Mac，多个独立账号")}</title>
<desc id="desc">{text("Personal, Work and Research each have a dedicated desktop launcher and CLI entry. More profiles can be added. This is a workflow illustration, not an application screenshot.", "个人、工作、研究账号各有独立的桌面启动器与 CLI 入口，可按需添加更多账号。这是工作流示意图，并非应用截图。")}</desc>
<rect width="1280" height="560" rx="24" fill="#F4F6F3"/>
<g font-family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, Microsoft YaHei, Noto Sans CJK SC, sans-serif">
<text x="64" y="66" fill="#51665D" font-size="14" font-weight="700" letter-spacing="3">CODEX PROFILES / macOS</text>
<text x="64" y="129" fill="#172C22" font-size="44" font-weight="700">{text("One Mac. Every account has a home.", "一台 Mac，每个账号都有独立空间。")}</text>
<text x="64" y="166" fill="#5D6B64" font-size="19">{text("Dedicated Dock launchers. Account-scoped CLI. Your official app.", "独立 Dock 启动器，按账号选择 CLI，直接使用官方应用。")}</text>
"""
    ]
    for index, (number, english, translated, color, identifier) in enumerate(ACCOUNTS):
        label = text(english, translated)
        x = 64 + index * 360
        parts.append(f'''<g transform="translate({x},210)">
<rect width="336" height="245" rx="18" fill="#FFFFFF" stroke="#DAE1DB"/>
<rect x="24" y="24" width="64" height="64" rx="16" fill="{color}"/>
<text x="56" y="67" text-anchor="middle" fill="white" font-size="28" font-weight="700">{number}</text>
<text x="108" y="52" fill="#172C22" font-size="23" font-weight="700">{label}</text>
<text x="108" y="77" fill="#68766E" font-size="14">{text("Independent profile", "独立账号配置")}</text>
<path d="M24 111 H312" stroke="#E5EAE6"/>
<text x="24" y="145" fill="#526359" font-size="14">DOCK</text>
<text x="98" y="145" fill="#172C22" font-size="16">{text("Open ", "打开")}{label}</text>
<text x="24" y="181" fill="#526359" font-size="14">CLI</text>
<text x="98" y="181" fill="#172C22" font-size="15" font-family="SFMono-Regular, Consolas, monospace">cli {identifier}</text>
<circle cx="31" cy="216" r="4" fill="{color}"/>
<text x="44" y="221" fill="#68766E" font-size="13">{text("Separate sign-in and history", "登录信息与会话记录各自独立")}</text>
</g>''')
    parts.append(f"""<text x="1192" y="337" fill="#85968A" font-size="44" text-anchor="middle">+</text>
<text x="64" y="512" fill="#526359" font-size="16">{text("Add the profiles you need. No built-in two-account limit.", "按需添加更多账号，不限于双开。")}</text>
<text x="1216" y="512" text-anchor="end" fill="#89958E" font-size="12">{text("WORKFLOW OVERVIEW", "工作流示意图")}</text>
</g></svg>""")
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    (ROOT / "assets/overview.svg").write_text(render())
    (ROOT / "assets/overview.zh-CN.svg").write_text(render(chinese=True))
