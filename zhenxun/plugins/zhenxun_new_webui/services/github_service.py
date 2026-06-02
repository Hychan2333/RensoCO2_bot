import asyncio
from datetime import datetime, timedelta
from typing import ClassVar

import httpx

from zhenxun.services.log import logger


class GitHubService:
    _cache: ClassVar[list[dict]] = []
    _last_fetch: ClassVar[datetime | None] = None
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _refresh_tasks: ClassVar[set[asyncio.Task]] = set()
    _refreshing = False

    CACHE_TTL = timedelta(minutes=20)

    API_URLS: ClassVar[list[str]] = [
        "https://api.github.com/repos/zhenxun-org/zhenxun_bot/commits?sha=main&per_page=30",
        "https://api.kkgithub.com/repos/zhenxun-org/zhenxun_bot/commits?sha=main&per_page=30",
    ]

    HEADERS: ClassVar[dict[str, str]] = {
        "User-Agent": "Mozilla/5.0 ZhenxunBot/1.0",
        "Accept": "application/vnd.github+json",
    }

    @classmethod
    async def get_commits(cls):
        now = datetime.utcnow()

        # 缓存未过期
        if cls._cache and cls._last_fetch and (now - cls._last_fetch < cls.CACHE_TTL):
            return cls._cache

        # 缓存过期，先返回旧缓存，再后台刷新
        if cls._cache:
            if not cls._refreshing:
                cls._refreshing = True
                task = asyncio.create_task(cls._safe_refresh())
                cls._refresh_tasks.add(task)
                task.add_done_callback(cls._refresh_tasks.discard)
            return cls._cache

        # 首次加载必须等一次
        async with cls._lock:
            if cls._cache:
                return cls._cache

            await cls._safe_fetch()
            return cls._cache

    @classmethod
    async def _safe_refresh(cls):
        try:
            await cls._safe_fetch()
        finally:
            cls._refreshing = False

    @classmethod
    async def _safe_fetch(cls):
        try:
            await cls._fetch()
        except Exception as e:
            # 失败不清缓存
            logger.warning("刷新 commits 失败", "GitHubService", e=e)

    @classmethod
    async def _fetch(cls):
        timeout = httpx.Timeout(10.0)

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            data = None

            for idx, url in enumerate(cls.API_URLS):
                try:
                    resp = await client.get(
                        url,
                        headers=cls.HEADERS,
                    )

                    # GitHub 403 -> fallback
                    if resp.status_code == 403 and idx == 0:
                        logger.warning("GitHub 403，切换 kkgithub...", "GitHubService")
                        continue

                    resp.raise_for_status()

                    data = resp.json()
                    break

                except httpx.TimeoutException:
                    logger.warning(f"请求超时: {url}", "GitHubService")

                except httpx.HTTPStatusError as e:
                    logger.warning(
                        f"HTTP {e.response.status_code}: " f"{e.response.text[:150]}",
                        "GitHubService",
                    )

                except Exception as e:
                    logger.warning(f"请求异常 {url}: {e}", "GitHubService")

            if not data:
                return

        result = []

        for c in data:
            try:
                commit = c.get("commit") or {}
                author = commit.get("author") or {}

                result.append(
                    {
                        "sha": (c.get("sha") or "")[:7],
                        "author": author.get("name"),
                        "avatar_url": (c.get("author") or {}).get("avatar_url"),
                        "date": author.get("date"),
                        "message": (commit.get("message") or "").splitlines()[0],
                    }
                )

            except Exception as e:
                logger.warning("commit parse error", "GitHubService", e=e)

        if result:
            cls._cache = result
            cls._last_fetch = datetime.utcnow()
