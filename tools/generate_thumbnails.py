"""Generate the synthetic video thumbnails used by the course guides.

The brief requires synthetic content only, so the guides use these generated
SVG cards instead of images copied from third-party video sites. Run from the
repository root:  python3 tools/generate_thumbnails.py
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent.parent / "static" / "thumbnails"

PALETTES = {
    "blue": ("#0f2f66", "#2667d8", "#9cc3ff"),
    "violet": ("#2c1856", "#6a44b8", "#cdb8f5"),
    "teal": ("#0b3b40", "#178a8d", "#9ee3df"),
}

# slug, course colour, kicker, headline (max two short lines).
# Text stays in the top third so the page's centred play button never covers it.
THUMBNAILS = [
    ("cyber-basics", "blue", "TOPIC OVERVIEW", ["Cybersecurity", "basics"]),
    ("security-concepts", "blue", "START HERE", ["What security", "protects"]),
    ("choosing-passwords", "blue", "ACCOUNT SECURITY", ["Choosing a", "password"]),
    ("password-managers", "blue", "ACCOUNT SECURITY", ["Password", "managers"]),
    ("sql-first-queries", "violet", "TOPIC OVERVIEW", ["Your first", "SQL queries"]),
    ("database-design", "violet", "PLANNING", ["Designing a", "database"]),
    ("relational-design", "violet", "STRUCTURE", ["Tables, keys", "and relations"]),
    ("sql-in-practice", "violet", "PRACTICE", ["SQL in", "practice"]),
    ("api-security", "teal", "TOPIC OVERVIEW", ["API security", "risks"]),
    ("html-css-basics", "teal", "FOUNDATIONS", ["HTML and CSS", "building blocks"]),
    ("javascript-basics", "teal", "FOUNDATIONS", ["JavaScript", "essentials"]),
    ("web-authentication", "teal", "ACCESS CONTROL", ["Signing users", "in safely"]),
]


def shapes(slug: str, accent: str) -> str:
    """Deterministic decorative circles and squares derived from the slug."""
    digest = hashlib.sha256(slug.encode()).digest()
    parts = []
    for i in range(6):
        x = 700 + digest[i] * 2.2
        y = 40 + digest[i + 6] * 2.6
        size = 40 + digest[i + 12] % 140
        opacity = 0.08 + (digest[i + 18] % 10) / 60
        if i % 2:
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{size}" fill="none" stroke="{accent}" stroke-width="10" opacity="{opacity:.2f}"/>')
        else:
            parts.append(
                f'<rect x="{x:.0f}" y="{y:.0f}" width="{size}" height="{size}" rx="18" fill="{accent}" '
                f'opacity="{opacity:.2f}" transform="rotate({digest[i + 24] % 40 - 20} {x:.0f} {y:.0f})"/>'
            )
    return "\n  ".join(parts)


def render(slug: str, colour: str, kicker: str, lines: list[str]) -> str:
    dark, mid, accent = PALETTES[colour]
    headline = "".join(
        f'<tspan x="96" dy="{0 if i == 0 else 92}">{escape(line)}</tspan>' for i, line in enumerate(lines)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720" role="img" aria-label="{escape(" ".join(lines))}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{dark}"/>
      <stop offset="1" stop-color="{mid}"/>
    </linearGradient>
  </defs>
  <rect width="1280" height="720" fill="url(#bg)"/>
  {shapes(slug, accent)}
  <text x="96" y="92" fill="{accent}" font-family="Arial, Helvetica, sans-serif" font-size="34" font-weight="700" letter-spacing="6">{escape(kicker)}</text>
  <text x="96" y="178" fill="#ffffff" font-family="Arial, Helvetica, sans-serif" font-size="84" font-weight="800">{headline}</text>
  <rect x="96" y="560" width="300" height="60" rx="12" fill="#ffffff" opacity="0.14"/>
  <text x="120" y="601" fill="#ffffff" font-family="Arial, Helvetica, sans-serif" font-size="28" font-weight="700">EduStream study clip</text>
</svg>
'''


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, colour, kicker, lines in THUMBNAILS:
        (OUT / f"{slug}.svg").write_text(render(slug, colour, kicker, lines), encoding="utf-8")
    print(f"Wrote {len(THUMBNAILS)} thumbnails to {OUT}")


if __name__ == "__main__":
    main()
