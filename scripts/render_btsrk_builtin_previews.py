import asyncio
import json
import random
from html import escape
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from jinja2 import Environment, FileSystemLoader, pass_context
from markupsafe import Markup


ROOT = Path(__file__).resolve().parents[1]
THEME_DIR = ROOT / "resources" / "themes" / "btsrk"
PAGES_DIR = THEME_DIR / "pages" / "builtin"
OUTPUT_DIR = THEME_DIR / "preview"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
CHROME_PATH = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
OUTPUT_PAGE_DIRS = {
    "help": PAGES_DIR / "help",
}


class ThemeEnvironment(Environment):
    def join_path(self, template: str, parent: str) -> str:
        if template.startswith("./") or template.startswith("../"):
            return str((Path(parent).parent / template).as_posix())
        return super().join_path(template, parent)


def _template_base(ctx_name: str | None) -> Path:
    return THEME_DIR / Path(ctx_name or "").parent


def _resolve_asset_path(asset_path: str, ctx_name: str | None) -> Path | None:
    clean = asset_path[2:] if asset_path.startswith("./") else asset_path
    candidates: list[Path]
    if asset_path.startswith(("./", "../")):
        base = _template_base(ctx_name)
        candidates = [
            (base / asset_path).resolve(),
            (base / clean).resolve(),
            (base / "assets" / clean).resolve(),
        ]
    else:
        candidates = [
            (THEME_DIR / "assets" / asset_path).resolve(),
            (THEME_DIR / asset_path).resolve(),
        ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else None


@pass_context
def asset(ctx, asset_path: str) -> str:
    resolved = _resolve_asset_path(asset_path, ctx.name)
    return resolved.as_uri() if resolved else ""


@pass_context
def random_asset(ctx, asset_path: str, key: str | None = None) -> str:
    del key
    directory = _resolve_asset_path(asset_path, ctx.name)
    if not directory or not directory.is_dir():
        return ""
    files = [
        item
        for item in directory.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTS
    ]
    return random.choice(files).resolve().as_uri() if files else ""


def md(value: Any) -> Markup:
    text = escape(str(value or ""))
    text = text.replace("\n", "<br>")
    return Markup(text)


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def load_manifest(page_dir: Path) -> dict[str, Any]:
    manifest = page_dir / "manifest.json"
    if not manifest.exists():
        return {}
    return json.loads(manifest.read_text(encoding="utf-8"))


def create_env() -> ThemeEnvironment:
    env = ThemeEnvironment(loader=FileSystemLoader(THEME_DIR), autoescape=True)
    env.globals.update(
        {
            "asset": asset,
            "random_asset": random_asset,
            "collected_inline_css": [],
            "collected_asset_styles": [],
            "required_scripts": [],
            "theme": {"palette": json.loads((THEME_DIR / "palette.json").read_text(encoding="utf-8"))},
            "default_theme_palette": {
                "component_colors": {
                    "background": {"light": "#ffffff", "dark": "#1e1e1e"},
                    "card": {"light": "#f8f9fa", "dark": "#2d2d2d"},
                    "primary": {"light": "#3498db", "dark": "#5fa8d3"},
                    "text": {"light": "#333333", "dark": "#eeeeee"},
                    "accent": {"light": "#e74c3c", "dark": "#c0392b"},
                }
            },
        }
    )
    env.filters.update({"md": md, "dump_json": dump_json})
    return env


def avatar_uri() -> str:
    avatar = PAGES_DIR / "sign" / "test_avatar.jpg"
    return avatar.resolve().as_uri() if avatar.exists() else ""


def icon_uri(name: str = "gold.png") -> str:
    candidate = PAGES_DIR / "my_info" / "assets" / "img" / name
    return candidate.resolve().as_uri() if candidate.exists() else ""


def sample_data() -> dict[str, tuple[str, dict[str, Any]]]:
    shop_goods = [
        {
            "id": 1,
            "name": "幸运护符",
            "description": "提升今日随机事件触发概率。",
            "price": 120,
            "discount_price": None,
            "daily_limit": 1,
            "limit_time": "",
            "icon_url": icon_uri("gold.png"),
        },
        {
            "id": 2,
            "name": "记忆碎片",
            "description": "用于兑换限定收藏物。",
            "price": 300,
            "discount_price": 240,
            "daily_limit": 2,
            "limit_time": "23:59",
            "icon_url": icon_uri("prop.png"),
        },
    ]
    return {
        "bot_profile": (
            "pages/builtin/bot_profile/main.html",
            {
                "title": "碳碳的自我介绍",
                "avatar": avatar_uri(),
                "bot_name": "碳碳",
                "tags": [{"text": "RensoCO2"}, {"text": "群管"}, {"text": "娱乐"}],
                "bot_description": "你好呀，我是碳碳。\n负责群内提醒、签到、商店和一些小工具。",
                "plugin_list": [
                    {
                        "name": "签到",
                        "introduction": "每天记录好感度、金币和随机奖励。",
                        "precautions": ["每天只能签到一次"],
                    },
                    {
                        "name": "商店",
                        "introduction": "使用金币购买道具或限时物品。",
                        "precautions": [],
                    },
                ],
            },
        ),
        "check": (
            "pages/builtin/check/main.html",
            {
                "nickname": "碳碳",
                "baidu": "#22c55e",
                "google": "#ef4444",
                "cpu_process": 38,
                "ram_process": 62,
                "swap_process": 8,
                "disk_process": 47,
                "cpu_info": "38% / 12 Core",
                "ram_info": "7.8G / 16G",
                "swap_info": "0.8G / 8G",
                "disk_info": "216G / 512G",
                "brand_raw": "Intel(R) Xeon CPU",
                "system": "Windows Server 2022",
                "version": "3.2.0",
                "plugin_count": 128,
            },
        ),
        "help": (
            "pages/core/plugin_menu/main.html",
            {
                "plugin_count": 28,
                "active_count": 28,
                "bot_name": "\u78b3\u78b3",
                "is_detail": False,
                "categories": [
                    {
                        "name": "\u4e3b\u8981\u529f\u80fd",
                        "items": [
                            {"id": 49, "name": "\u67e5\u770b\u4fe1\u606f", "status": 0},
                            {"id": 58, "name": "\u7b7e\u5230", "status": 0},
                            {"id": 65, "name": "\u70b9\u8d5e\u5c0f\u52a9\u624b", "status": 0},
                            {"id": 72, "name": "\u7fa4\u804a\u603b\u7ed3", "status": 0},
                            {"id": 73, "name": "\u8bcd\u4e91", "status": 0},
                            {"id": 74, "name": "\u67e5\u770b\u8bcd\u6761", "status": 0},
                            {"id": 75, "name": "B\u7ad9\u8ba2\u9605", "status": 0},
                            {"id": 77, "name": "\u8bcd\u6761\u68c0\u6d4b", "status": 0},
                            {"id": 81, "name": "\u7fa4\u804a\u8bed\u5f55", "status": 0},
                            {"id": 82, "name": "\u91d1\u5e01\u7ea2\u5305", "status": 0},
                            {"id": 83, "name": "github\u8ba2\u9605", "status": 0},
                            {"id": 88, "name": "\u8fdb\u7fa4\u9a8c\u8bc1", "status": 0},
                            {"id": 89, "name": "\u81ea\u52a8\u7b7e\u5230", "status": 0},
                        ],
                    },
                    {
                        "name": "\u7fa4\u5185\u5c0f\u6e38\u620f",
                        "items": [
                            {"id": 11, "name": "\u5c0f\u771f\u5bfb\u94f6\u884c", "status": 0},
                            {"id": 63, "name": "\u4e0a\u4e0d\u4e0a", "status": 0},
                        ],
                    },
                    {
                        "name": "\u6570\u636e\u7edf\u8ba1",
                        "items": [
                            {"id": 47, "name": "\u6d88\u606f\u7edf\u8ba1", "status": 0},
                            {"id": 52, "name": "\u529f\u80fd\u8c03\u7528\u7edf\u8ba1", "status": 0},
                        ],
                    },
                    {"name": "\u5546\u5e97", "items": [{"id": 18, "name": "\u5546\u5e97", "status": 0}]},
                    {"name": "\u6765\u70b9\u597d\u5eb7\u7684", "items": [{"id": 68, "name": "\u672c\u5730\u56fe\u5e93", "status": 0}]},
                    {
                        "name": "\u5176\u4ed6",
                        "items": [
                            {"id": 15, "name": "ChatInter", "status": 0},
                            {"id": 34, "name": "\u81ea\u6211\u4ecb\u7ecd", "status": 0},
                            {"id": 37, "name": "\u5173\u4e8e", "status": 0},
                            {"id": 50, "name": "\u7fa4\u7ec4\u7533\u8bf7", "status": 0},
                            {"id": 54, "name": "\u6d88\u606f\u64a4\u56de", "status": 0},
                            {"id": 64, "name": "\u590d\u8bfb", "status": 0},
                            {"id": 80, "name": "B\u7ad9\u5185\u5bb9\u89e3\u6790", "status": 0},
                        ],
                    },
                    {"name": "\u8054\u7cfb\u7ba1\u7406\u5458", "items": [{"id": 71, "name": "\u8054\u7cfb\u7ba1\u7406\u5458", "status": 0}]},
                    {"name": "\u4e00\u4e9b\u5de5\u5177", "items": [{"id": 86, "name": "Minecraft\u67e5\u670d", "status": 0}]},
                ],
            },
        ),
        "mahiro_bank": (
            "pages/builtin/mahiro_bank/dispatch.html",
            {
                "page_type": "user",
                "payload": {
                    "avatar_url": avatar_uri(),
                    "name": "RensoCO2",
                    "rank": 7,
                    "amount": 12000,
                    "deposit_count": 18,
                    "projected_revenue": 88,
                    "cumulative_gain": 560,
                    "today_deposit_count": 3,
                    "today_deposit_amount": 2600,
                    "create_time": "2026-06-09 20:30:00",
                    "deposit_list": [
                        {
                            "id": 101,
                            "date": "06-09",
                            "amount": 1000,
                            "start_time": "2026-06-09",
                            "projected_revenue": 24,
                            "end_time": "2026-06-16",
                            "rate": 2.4,
                        },
                        {
                            "id": 102,
                            "date": "06-08",
                            "amount": 1600,
                            "start_time": "2026-06-08",
                            "projected_revenue": 38,
                            "end_time": "2026-06-15",
                            "rate": 2.4,
                        },
                    ],
                },
            },
        ),
        "my_info": (
            "pages/builtin/my_info/main.html",
            {
                "page": {"date": "2026-06-09", "weather_icon_name": "sun", "temperature": 26},
                "info": {
                    "avatar_url": avatar_uri(),
                    "title": "RensoCO2",
                    "nickname": "碳碳",
                    "race": "兽人",
                    "sex": "未知",
                    "occupation": "Bot 管理员",
                    "uid": "0000 0000 0001",
                    "description": "这里是一段用于预览的个人简介，展示卡片的文字排版。",
                },
                "favorability": {"level": 4, "selected_indices": ["", "", "", "", "selected", "", "", "", ""]},
                "permission_level": 5,
                "stats": {"gold": 4761, "prop_count": 12, "call_count": 233, "chat_count": 1024},
                "chart": {"labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "data": [5, 12, 9, 18, 22, 16, 24]},
            },
        ),
        "shop": (
            "pages/builtin/shop/main.html",
            {
                "bot_nickname": "碳碳",
                "categories": [
                    {"partition_title": "每日补给", "goods_list": shop_goods},
                    {"partition_title": "限定收藏", "goods_list": list(reversed(shop_goods))},
                ],
            },
        ),
    }


def render_html(env: ThemeEnvironment, name: str, template_path: str, data: dict[str, Any]) -> Path:
    if name == "help":
        data = dict(data)
        data["categories"] = [
            SimpleNamespace(
                name=category["name"],
                items=[SimpleNamespace(**item) for item in category["items"]],
            )
            for category in data["categories"]
        ]
    template = env.get_template(template_path)
    html = template.render(data=data)
    page_dir = THEME_DIR / Path(template_path).parent
    manifest = load_manifest(page_dir)
    rendered_styles = []
    for style in manifest.get("styles", []):
        style_path = (Path(template_path).parent / style).as_posix()
        rendered_styles.append(env.get_template(style_path).render(data=data))
    if rendered_styles:
        html = html.replace(
            "</head>",
            "<style>\n" + "\n".join(rendered_styles) + "\n</style>\n</head>",
        )
    output_dir = OUTPUT_PAGE_DIRS.get(name, page_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{name}_preview.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path


async def screenshot(html_path: Path, output_path: Path, viewport: dict[str, int]) -> None:
    from playwright.async_api import async_playwright

    launch_kwargs = {}
    if CHROME_PATH.exists():
        launch_kwargs["executable_path"] = str(CHROME_PATH)
    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        page = await browser.new_page(viewport=viewport)
        await page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        await page.screenshot(path=str(output_path), full_page=True)
        await browser.close()


async def main() -> None:
    random.seed()
    OUTPUT_DIR.mkdir(exist_ok=True)
    env = create_env()
    results = []
    for name, (template_path, data) in sample_data().items():
        page_dir = THEME_DIR / Path(template_path).parent
        manifest = load_manifest(page_dir)
        viewport = manifest.get("render_options", {}).get("viewport", {})
        viewport = {
            "width": int(viewport.get("width", 900)),
            "height": max(int(viewport.get("height", 10)), 600),
        }
        output_dir = OUTPUT_PAGE_DIRS.get(name, page_dir)
        html_path = render_html(env, name, template_path, data)
        png_path = output_dir / f"{name}_preview.png"
        await screenshot(html_path, png_path, viewport)
        results.append(png_path)
    for path in results:
        print(path)


if __name__ == "__main__":
    asyncio.run(main())
