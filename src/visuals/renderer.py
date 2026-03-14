import asyncio
import os
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)

class SocialCardRenderer:
    def __init__(self, output_dir: str = "downloads/visuals"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def _get_template(self, title: str, subtitle: str, body: list, cta: str, bg_image: str, theme: str = "modern"):
        """Generates a sleek, editorial-style (Codex-inspired) template."""
        
        themes = {
            "modern": {"accent": "#38bdf8", "glow": "rgba(56, 189, 248, 0.3)"},
            "vibrant": {"accent": "#fbbf24", "glow": "rgba(251, 191, 36, 0.3)"},
            "emergency": {"accent": "#ef4444", "glow": "rgba(239, 68, 68, 0.4)"}
        }
        t = themes.get(theme, themes["modern"])
        
        bullets_html = "".join([f'<div class="point"><span></span>{p}</div>' for p in body])
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;900&display=swap');
                body {{
                    margin: 0; padding: 0; width: 1080px; height: 1080px;
                    font-family: 'Outfit', sans-serif;
                    background: #000;
                    display: flex; justify-content: center; align-items: center;
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
                    background: linear-gradient(180deg, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.9) 80%);
                }}
                .content {{
                    position: relative;
                    z-index: 10;
                    padding: 80px;
                    height: 100%;
                    box-sizing: border-box;
                    display: flex; flex-direction: column;
                }}
                .top-line {{
                    display: flex; align-items: center; gap: 15px;
                    margin-bottom: 40px;
                }}
                .brand {{
                    text-transform: uppercase; font-weight: 900; letter-spacing: 4px;
                    font-size: 22px; color: {t['accent']};
                    text-shadow: 0 0 20px {t['glow']};
                }}
                .dot {{ width: 8px; height: 8px; background: {t['accent']}; border-radius: 50%; }}
                .tag {{ font-size: 22px; font-weight: 600; opacity: 0.8; color: #fff; }}
                
                h1 {{
                    font-size: 88px; font-weight: 900; line-height: 1;
                    margin: 0 0 20px 0; color: #fff;
                    letter-spacing: -3px;
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
                
                .footer {{
                    margin-top: auto;
                    display: flex; justify-content: space-between; align-items: center;
                    padding-top: 40px; border-top: 1px solid rgba(255,255,255,0.1);
                }}
                .cta {{
                    background: {t['accent']}; color: #000;
                    padding: 15px 30px; border-radius: 12px;
                    font-weight: 900; font-size: 24px; text-transform: uppercase;
                }}
                .handle {{ font-weight: 600; font-size: 24px; opacity: 0.5; color: #fff; letter-spacing: 2px; }}
            </style>
        </head>
        <body>
            <div class="stage">
                <div class="overlay"></div>
                <div class="content">
                    <div class="top-line">
                        <div class="brand">CivicClaw</div>
                        <div class="dot"></div>
                        <div class="tag">MUNICIPAL DESK</div>
                    </div>
                    <h1>{title}</h1>
                    <div class="sub">{subtitle}</div>
                    <div class="points">
                        {bullets_html}
                    </div>
                    <div class="footer">
                        <div class="cta">{cta}</div>
                        <div class="handle">@TORONTOMINUTES</div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    async def render_card(self, title: str, subtitle: str, body: list, cta: str, bg_image: str, filename: str, theme: str = "modern") -> str:
        """Renders the HTML template to a PNG image using Playwright."""
        output_path = os.path.join(self.output_dir, filename)
        html_content = self._get_template(title, subtitle, body, cta, bg_image, theme)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1080, "height": 1080})
            await page.set_content(html_content)
            # Use JPEG and ensure .jpg extension for better compatibility
            output_path_jpg = output_path.replace('.png', '.jpg')
            await page.screenshot(path=output_path_jpg, type="jpeg", quality=90)
            await browser.close()
            
        logger.info(f"Successfully rendered premium social card: {output_path_jpg}")
        return os.path.abspath(output_path_jpg)

if __name__ == "__main__":
    # Test rendering
    async def test():
        renderer = SocialCardRenderer()
        await renderer.render_card(
            title="THE RENT CRACKDOWN",
            subtitle="City Council EX29.14",
            body=["Toronto is doubling enforcement on bad landlords.", "500 Dawes Rd is the first target for mandatory city-led repairs."],
            cta="DM RENT for more",
            bg_image="https://images.pexels.com/photos/439391/pexels-photo-439391.jpeg",
            filename="test_card_editorial.jpg",
            theme="emergency"
        )
    asyncio.run(test())
