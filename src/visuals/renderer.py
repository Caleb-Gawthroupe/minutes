import asyncio
import os
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)


class SocialCardRenderer:
    def __init__(self, output_dir: str = "downloads/visuals"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _base_css(self, bg_image: str, accent: str, glow: str):
        """Shared CSS foundation for all slides."""
        return f"""
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;900&display=swap');
            body {{
                margin: 0; padding: 0; width: 1080px; height: 1080px;
                font-family: 'Outfit', sans-serif;
                background: #000;
            }}
            .stage {{
                width: 100%; height: 100%;
                background-image: url('{bg_image}');
                background-size: cover;
                background-position: center;
                position: relative;
                display: flex; flex-direction: column;
            }}
            .overlay {{
                position: absolute; inset: 0;
                background: linear-gradient(180deg, rgba(0,0,0,0.25) 0%, rgba(0,0,0,0.92) 75%);
            }}
            .content {{
                position: relative; z-index: 10;
                padding: 80px; height: 100%; box-sizing: border-box;
                display: flex; flex-direction: column;
            }}
            .top-line {{
                display: flex; align-items: center; gap: 15px;
                margin-bottom: 40px;
            }}
            .brand {{
                text-transform: uppercase; font-weight: 900; letter-spacing: 4px;
                font-size: 22px; color: {accent};
                text-shadow: 0 0 20px {glow};
            }}
            .dot {{ width: 8px; height: 8px; background: {accent}; border-radius: 50%; }}
            .tag {{ font-size: 22px; font-weight: 600; opacity: 0.8; color: #fff; }}
            .slide-indicator {{
                display: flex; gap: 8px; margin-top: auto; justify-content: center; padding-top: 30px;
            }}
            .slide-dot {{
                width: 10px; height: 10px; border-radius: 50%;
                background: rgba(255,255,255,0.3);
            }}
            .slide-dot.active {{ background: {accent}; box-shadow: 0 0 10px {glow}; }}
            .footer {{
                display: flex; justify-content: space-between; align-items: center;
                padding-top: 30px; border-top: 1px solid rgba(255,255,255,0.1);
            }}
            .cta {{
                background: {accent}; color: #000;
                padding: 15px 30px; border-radius: 12px;
                font-weight: 900; font-size: 24px; text-transform: uppercase;
            }}
            .handle {{ font-weight: 600; font-size: 24px; opacity: 0.5; color: #fff; letter-spacing: 2px; }}
        """

    def _slide_dots_html(self, active_index: int, total: int = 3):
        dots = ""
        for i in range(total):
            cls = "slide-dot active" if i == active_index else "slide-dot"
            dots += f'<div class="{cls}"></div>'
        return f'<div class="slide-indicator">{dots}</div>'

    # ─── SLIDE 1: THE DECISION ───
    def _slide_decision(self, label: str, title: str, subtitle: str, summary: str, bg_image: str, accent: str, glow: str):
        return f"""<!DOCTYPE html><html><head><style>
            {self._base_css(bg_image, accent, glow)}
            h1 {{
                font-size: 82px; font-weight: 900; line-height: 1;
                margin: 0 0 30px 0; color: #fff; letter-spacing: -3px;
            }}
            .sub {{ font-size: 28px; font-weight: 600; opacity: 0.7; color: #fff; margin-bottom: 50px; }}
            .summary {{
                font-size: 34px; font-weight: 400; line-height: 1.5; color: #fff;
                opacity: 0.9; flex-grow: 1;
            }}
            .label {{
                display: inline-block; background: {accent}; color: #000;
                padding: 8px 20px; border-radius: 8px; font-weight: 900;
                font-size: 18px; text-transform: uppercase; letter-spacing: 3px;
                margin-bottom: 25px;
            }}
        </style></head><body>
        <div class="stage"><div class="overlay"></div><div class="content">
            <div class="top-line">
                <div class="brand">CivicClaw</div>
                <div class="dot"></div>
                <div class="tag">MUNICIPAL DESK</div>
            </div>
            <div class="label">{label}</div>
            <h1>{title}</h1>
            <div class="sub">{subtitle}</div>
            <div class="summary">{summary}</div>
            {self._slide_dots_html(0)}
            <div class="footer">
                <div class="handle">@TORONTOMINUTES</div>
                <div class="tag">SWIPE →</div>
            </div>
        </div></div>
        </body></html>"""

    # ─── SLIDE 2: THE IMPACT ───
    def _slide_impact(self, label: str, title: str, stats: list, bg_image: str, accent: str, glow: str):
        stats_html = ""
        for stat in stats:
            stats_html += f"""
            <div class="stat-row">
                <div class="stat-bullet" style="border-color: {accent};"></div>
                <div class="stat-text">{stat}</div>
            </div>"""
        return f"""<!DOCTYPE html><html><head><style>
            {self._base_css(bg_image, accent, glow)}
            .label {{
                display: inline-block; background: {accent}; color: #000;
                padding: 8px 20px; border-radius: 8px; font-weight: 900;
                font-size: 18px; text-transform: uppercase; letter-spacing: 3px;
                margin-bottom: 25px;
            }}
            h2 {{
                font-size: 60px; font-weight: 900; line-height: 1.1;
                margin: 0 0 50px 0; color: #fff; letter-spacing: -2px;
            }}
            .stats {{ display: flex; flex-direction: column; gap: 35px; flex-grow: 1; }}
            .stat-row {{ display: flex; gap: 22px; align-items: flex-start; }}
            .stat-bullet {{
                width: 14px; height: 14px; border: 3px solid {accent};
                border-radius: 50%; margin-top: 16px; flex-shrink: 0;
            }}
            .stat-text {{
                font-size: 32px; font-weight: 500; line-height: 1.4; color: #fff;
            }}
        </style></head><body>
        <div class="stage"><div class="overlay"></div><div class="content">
            <div class="top-line">
                <div class="brand">CivicClaw</div>
                <div class="dot"></div>
                <div class="tag">MUNICIPAL DESK</div>
            </div>
            <div class="label">{label}</div>
            <h2>{title}</h2>
            <div class="stats">{stats_html}</div>
            {self._slide_dots_html(1)}
            <div class="footer">
                <div class="handle">@TORONTOMINUTES</div>
                <div class="tag">SWIPE →</div>
            </div>
        </div></div>
        </body></html>"""

    # ─── SLIDE 3: ADAPTIVE (context, contradiction, or next steps) ───
    def _slide_context(self, label: str, title: str, body: str, cta: str, bg_image: str, accent: str, glow: str):
        return f"""<!DOCTYPE html><html><head><style>
            {self._base_css(bg_image, accent, glow)}
            .label {{
                display: inline-block; background: {accent}; color: #000;
                padding: 8px 20px; border-radius: 8px; font-weight: 900;
                font-size: 18px; text-transform: uppercase; letter-spacing: 3px;
                margin-bottom: 25px;
            }}
            h2 {{
                font-size: 56px; font-weight: 900; line-height: 1.1;
                margin: 0 0 40px 0; color: #fff; letter-spacing: -2px;
            }}
            .body-text {{
                font-size: 32px; font-weight: 400; line-height: 1.6; color: #fff;
                opacity: 0.9; flex-grow: 1;
            }}
        </style></head><body>
        <div class="stage"><div class="overlay"></div><div class="content">
            <div class="top-line">
                <div class="brand">CivicClaw</div>
                <div class="dot"></div>
                <div class="tag">MUNICIPAL DESK</div>
            </div>
            <div class="label">{label}</div>
            <h2>{title}</h2>
            <div class="body-text">{body}</div>
            {self._slide_dots_html(2)}
            <div class="footer">
                <div class="cta">{cta}</div>
                <div class="handle">@TORONTOMINUTES</div>
            </div>
        </div></div>
        </body></html>"""

    async def render_carousel(self, slides_data: dict, bg_image: str, theme: str = "modern") -> list[str]:
        """
        Renders a 3-slide carousel. Returns list of file paths.
        slides_data keys:
          - slide1_label, slide1_title, slide1_subtitle, slide1_summary
          - slide2_label, slide2_title, slide2_stats (list)
          - slide3_label, slide3_title, slide3_body
          - cta, img_keyword
        """
        themes = {
            "modern": {"accent": "#38bdf8", "glow": "rgba(56, 189, 248, 0.3)"},
            "vibrant": {"accent": "#fbbf24", "glow": "rgba(251, 191, 36, 0.3)"},
            "emergency": {"accent": "#ef4444", "glow": "rgba(239, 68, 68, 0.4)"}
        }
        t = themes.get(theme, themes["modern"])
        accent, glow = t["accent"], t["glow"]

        htmls = [
            self._slide_decision(
                slides_data.get("slide1_label", "The Decision"),
                slides_data.get("slide1_title", "CIVIC UPDATE"),
                slides_data.get("slide1_subtitle", ""),
                slides_data.get("slide1_summary", ""),
                bg_image, accent, glow
            ),
            self._slide_impact(
                slides_data.get("slide2_label", "The Hard Stats"),
                slides_data.get("slide2_title", "BY THE NUMBERS"),
                slides_data.get("slide2_stats", ["Details pending."]),
                bg_image, accent, glow
            ),
            self._slide_context(
                slides_data.get("slide3_label", "What This Means"),
                slides_data.get("slide3_title", "LOOKING AHEAD"),
                slides_data.get("slide3_body", "Stay tuned for updates."),
                slides_data.get("cta", "DM MINUTES for more"),
                bg_image, accent, glow
            )
        ]

        paths = []
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1080, "height": 1080})

            for i, html in enumerate(htmls):
                fname = f"carousel_{i+1}_{int(asyncio.get_event_loop().time())}.jpg"
                out = os.path.join(self.output_dir, fname)
                await page.set_content(html)
                await page.screenshot(path=out, type="jpeg", quality=90)
                paths.append(os.path.abspath(out))
                logger.info(f"Rendered carousel slide {i+1}: {out}")

            await browser.close()

        return paths

    # ─── Legacy single-card renderer (kept for backward compat) ───
    def _get_template(self, title, subtitle, body, cta, bg_image, theme="modern"):
        themes = {
            "modern": {"accent": "#38bdf8", "glow": "rgba(56, 189, 248, 0.3)"},
            "vibrant": {"accent": "#fbbf24", "glow": "rgba(251, 191, 36, 0.3)"},
            "emergency": {"accent": "#ef4444", "glow": "rgba(239, 68, 68, 0.4)"}
        }
        t = themes.get(theme, themes["modern"])
        bullets_html = "".join([f'<div class="point"><span></span>{p}</div>' for p in body])
        return f"""<!DOCTYPE html><html><head><style>
            {self._base_css(bg_image, t['accent'], t['glow'])}
            h1 {{
                font-size: 88px; font-weight: 900; line-height: 1;
                margin: 0 0 20px 0; color: #fff; letter-spacing: -3px;
            }}
            .sub {{ font-size: 32px; font-weight: 400; opacity: 0.7; color: #fff; margin-bottom: 60px; }}
            .points {{ display: flex; flex-direction: column; gap: 30px; flex-grow: 1; }}
            .point {{
                display: flex; gap: 20px; align-items: flex-start;
                font-size: 30px; font-weight: 500; line-height: 1.4; color: #fff;
            }}
            .point span {{
                width: 12px; height: 12px; border: 3px solid {t['accent']};
                border-radius: 50%; margin-top: 14px; flex-shrink: 0;
            }}
        </style></head><body>
        <div class="stage"><div class="overlay"></div><div class="content">
            <div class="top-line">
                <div class="brand">CivicClaw</div>
                <div class="dot"></div>
                <div class="tag">MUNICIPAL DESK</div>
            </div>
            <h1>{title}</h1>
            <div class="sub">{subtitle}</div>
            <div class="points">{bullets_html}</div>
            <div class="footer">
                <div class="cta">{cta}</div>
                <div class="handle">@TORONTOMINUTES</div>
            </div>
        </div></div>
        </body></html>"""

    async def render_card(self, title, subtitle, body, cta, bg_image, filename, theme="modern"):
        output_path = os.path.join(self.output_dir, filename)
        html_content = self._get_template(title, subtitle, body, cta, bg_image, theme)
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1080, "height": 1080})
            await page.set_content(html_content)
            output_path_jpg = output_path.replace('.png', '.jpg')
            await page.screenshot(path=output_path_jpg, type="jpeg", quality=90)
            await browser.close()
        logger.info(f"Successfully rendered premium social card: {output_path_jpg}")
        return os.path.abspath(output_path_jpg)
