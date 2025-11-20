import re
import asyncio
from random import uniform
import aiohttp
from bs4 import BeautifulSoup, Tag
from typing import Dict, List, Literal
from src.schemas import Category, SubCategory, Offer, SellerPreview
from src.utils.cooldown_manager import CoolDownManager
from fake_headers import Headers, random_browser, random_os
from urllib.parse import urlparse

DOMAIN_NAME = "funpay.com"


def get_domain(url: str) -> str:
    return urlparse(url).netloc


def get_path(url: str) -> str:
    return urlparse(url).path


class FunPayScraper(CoolDownManager):
    def __init__(
        self,
        currency: Literal["usd", "eur"] = "usd",
        min_request_interval: float = None,
        cache_ttl: float = 30.0,
    ):
        super().__init__(
            min_request_interval=min_request_interval,
            cache_ttl=cache_ttl,
            base_url="https://" + DOMAIN_NAME,
        )

        self.base_headers: dict = {}
        self.addit_headers: dict = {}
        self.session.headers.update(self.headers)
        self.session.cookie_jar.update_cookies({"cy": currency})

    @property
    def headers(self) -> dict:
        if not self.addit_headers:
            self._generate_headers()
        return {**self.base_headers, **self.addit_headers}

    def _generate_headers(self) -> None:
        headers = Headers(
            browser=random_browser(),  # chrome / firefox / safari / edge
            os=random_os(),  # win / mac / linux
            headers=True,
        )
        headers = headers.generate()
        self.base_headers = headers.copy()
        self.base_headers["Accept-Language"] = "en-GB,en;q=0.5"
        self.base_headers["Referer"] = "https://www.google.com/"
        self.addit_headers = {
            "Sec-GPC": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Priority": "u=0, i",
        }

    async def _get_offers_html(self, url: str) -> str:
        async with self.session.get(url=get_path(url=url)) as resp:
            return await resp.text()

    async def _get_categories_html(self, path: str = "") -> str:
        async with self.session.get(path) as resp:
            return await resp.text()

    async def get_categories(self) -> List[Category]:
        await self.cooldown(DOMAIN_NAME)
        html = await self._get_categories_html()
        data = self._parse_categories(html=html)

        await asyncio.sleep(uniform(0.2, 1))
        html = await self._get_categories_html(path="/en/")
        if not data:
            data = self._parse_categories(html=html)

        return data

    async def get_offers(self, url: str) -> List[Offer]:
        await self.cooldown(DOMAIN_NAME)
        html = await self._get_offers_html(url=url)
        data = self._parse_offers(html=html)
        return data

    def _parse_categories(self, html: str) -> List[Category]:
        data: List[Category] = []

        soup = BeautifulSoup(html, "lxml")
        rows = soup.select(".promo-games-all .promo-game-list .row.row-10.flex")
        for row in rows:
            for category_div in row.select("div.col-md-3.col-xs-6 .promo-game-item"):
                game_title = category_div.select_one(".game-title")
                data_id = game_title["data-id"]
                link = game_title.select_one("a")
                name = link.text.strip()
                url = link["href"]

                subcategories: List[SubCategory] = [
                    SubCategory(title=sub_link.text.strip(), url=sub_link["href"])
                    for sub_link in category_div.select("ul li a")
                ]

                data.append(
                    Category(
                        title=name,
                        data_id=data_id,
                        url=url,
                        subcategories=subcategories,
                    )
                )

        return data

    def _parse_offers(self, html: str) -> List[Offer]:
        """Parse ALL offers from funpay main page.
        FunPay gives all offers from one request, and hiding some.
        Most of sellers thumbs will not be avaible.

        Args:
            html (str): html page

        Returns:
            List[Offer]: List of offers Objs
        """
        soup = BeautifulSoup(html, "lxml")
        data: List[Offer] = []
        sellers_cache: Dict[str, SellerPreview] = {}

        offers = soup.select(
            ".cd-forward .content-with-cd-wide.showcase "
            ".tc.table-hover.table-clickable.tc-short.showcase-table.tc-lazyload.tc-sortable "
            ".tc-item"
        )

        for offer in offers:
            offer_data = self._parse_offer(offer, sellers_cache)
            if offer_data:
                data.append(offer_data)

        return data

    def _extract_price(self, offer: Tag) -> tuple[str, str]:
        """Извлекает цену и валюту."""
        price_div = offer.find(class_="tc-price").find("div")
        value = price_div.contents[0].strip()
        currency = price_div.find("span").get_text(strip=True)
        return value, currency

    def _parse_user_from_offers(
        self, user_div: Tag, sellers_cache: Dict[str, SellerPreview]
    ) -> SellerPreview:
        """Парсит продавца и кэширует SellerPreview."""
        avatar_div = user_div.select_one(".media-left .avatar-photo")
        user_url = avatar_div.get("data-href")

        if user_url in sellers_cache:
            return sellers_cache[user_url]

        thumb_match = re.search(r"url\((.*?)\)", avatar_div["style"])
        thumb_url = thumb_match.group(1) if thumb_match else None
        if thumb_url == "/img/layout/avatar.png":
            thumb_url = None

        user_body = user_div.select_one(".media-body")
        username = user_body.select_one(".media-user-name").get_text(strip=True)

        rating_div = user_body.select_one(".media-user-reviews div")
        rating_stars = (
            int(rating_div["class"][-1].split("-")[-1]) if rating_div else None
        )

        reviews_el = user_body.select_one(".media-user-reviews .rating-mini-count")
        reviews_count = reviews_el.text.strip() if reviews_el else None
        if not reviews_count or not reviews_count.isdigit():
            raw_text = user_body.select_one(".media-user-reviews").get_text(strip=True)
            reviews_count = next((s for s in raw_text.split() if s.isdigit()), None)

        acc_age = user_body.select_one(".media-user-info").get_text(strip=True)

        seller = SellerPreview(
            thumb_url=thumb_url,
            url=user_url,
            username=username,
            rating_stars=rating_stars,
            reviews_count=reviews_count,
            acc_age=acc_age,
        )
        sellers_cache[user_url] = seller
        return seller

    def _parse_offer(
        self, offer: Tag, sellers_cache: Dict[str, SellerPreview]
    ) -> Offer | None:
        """Парсит один оффер."""
        try:
            platform = offer.get("data-f-platform")
            url = offer.get("href")
            server_id = offer.get("data-server")
            server_name = None

            if server_id:
                server_name_el = offer.select_one(".tc-server.hidden-xs")
                server_name = (
                    server_name_el.get_text(strip=True) if server_name_el else None
                )

            description = offer.select_one(".tc-desc .tc-desc-text").get_text(
                strip=True
            )
            auto_delivery = offer.get("data-auto") == "1"

            price_value, price_currency = self._extract_price(offer)

            ftype1 = offer.get("data-f-type")
            ftype2 = offer.get("data-f-type2")

            user_div = offer.select_one(".tc-user > div")
            seller = self._parse_user_from_offers(user_div, sellers_cache)

            return Offer(
                server_id=server_id,
                server_name=server_name,
                description=description,
                seller=seller,
                url=url,
                platform=platform,
                price_value=price_value,
                price_currency=price_currency,
                auto_delivery=auto_delivery,
                ftype1=ftype1,
                ftype2=ftype2,
            )

        except Exception as e:
            print(f"[WARN] Error parsing offer: {e}")
            return None
