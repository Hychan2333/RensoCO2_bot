import asyncio
import json
import random
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


ROOT = Path(__file__).resolve().parents[1]
THEME_DIR = ROOT / "resources" / "themes" / "btsrk"
SIGN_DIR = THEME_DIR / "pages" / "builtin" / "sign"
OUTPUT_HTML = SIGN_DIR / "sign_preview.html"
OUTPUT_PNG = SIGN_DIR / "sign_preview.png"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


class ThemeEnvironment(Environment):
    def join_path(self, template: str, parent: str) -> str:
        if template.startswith("./") or template.startswith("../"):
            return str((Path(parent).parent / template).as_posix())
        return super().join_path(template, parent)


def resolve_asset(path: str) -> Path:
    clean_path = path.lstrip("./")
    return SIGN_DIR / "assets" / clean_path


def asset(path: str) -> str:
    return resolve_asset(path).resolve().as_uri()


def random_asset(path: str, key: str | None = None) -> str:
    del key
    asset_dir = resolve_asset(path)
    if not asset_dir.is_dir():
        return ""
    files = [
        item
        for item in asset_dir.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTS
    ]
    if not files:
        return ""
    return random.choice(files).resolve().as_uri()


def render_html() -> None:
    env = ThemeEnvironment(loader=FileSystemLoader(THEME_DIR), autoescape=True)
    template = env.get_template("pages/builtin/sign/main.html")
    palette = json.loads((THEME_DIR / "palette.json").read_text(encoding="utf-8"))
    data = {
        "user": {
            "nickname": "RensoCO2",
            "uid_str": "0000 0000 0001",
            "avatar_url": (SIGN_DIR / "test_avatar.jpg").resolve().as_uri(),
            "sign_count": 28,
        },
        "favorability": {
            "current": 37.42,
            "level_text": "4 [朋友]",
        },
        "reward": {
            "impression_added": 0.86,
            "gold_added": 66,
            "gift_received": "额外金币 +12",
            "is_double": False,
        },
        "page": {"date_str": "2026-06-09 20:00:00"},
        "bot_name": "碳碳",
        "attitude": "对你的态度: 友好",
        "interpolation": "12.58",
        "progress": 62,
        "rank": 12,
        "total_gold": 4761,
        "is_card_view": True,
    }

    html = template.render(
        theme={"palette": palette},
        default_theme_palette={
            "component_colors": {
                "background": {"light": "#ffffff", "dark": "#1e1e1e"},
                "card": {"light": "#f8f9fa", "dark": "#2d2d2d"},
                "primary": {"light": "#3498db", "dark": "#5fa8d3"},
                "text": {"light": "#333333", "dark": "#eeeeee"},
                "accent": {"light": "#e74c3c", "dark": "#c0392b"},
            }
        },
        data=data,
        asset=asset,
        random_asset=random_asset,
    )
    OUTPUT_HTML.write_text(html, encoding="utf-8")


async def screenshot() -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        chrome_path = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        launch_kwargs = {}
        if chrome_path.exists():
            launch_kwargs["executable_path"] = str(chrome_path)
        browser = await p.chromium.launch(**launch_kwargs)
        page = await browser.new_page(viewport={"width": 876, "height": 424})
        await page.goto(OUTPUT_HTML.resolve().as_uri(), wait_until="networkidle")
        await page.screenshot(path=str(OUTPUT_PNG), full_page=True)
        await browser.close()


if __name__ == "__main__":
    render_html()
    asyncio.run(screenshot())
    print(OUTPUT_PNG)
