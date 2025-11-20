from functools import lru_cache
from typing import List, Optional
from pydantic import AnyHttpUrl, BaseModel, field_validator, HttpUrl


class SubCategory(BaseModel):
    title: str
    url: HttpUrl


class Category(BaseModel):
    title: str
    data_id: int
    url: HttpUrl
    subcategories: List[SubCategory]


class SellerPreview(BaseModel):
    thumb_url: Optional[AnyHttpUrl] = None
    url: HttpUrl
    username: str
    rating_stars: int | None = None
    reviews_count: Optional[int] = None
    acc_age: str


class Offer(BaseModel):
    server_name: Optional[str] = None
    server_id: Optional[int] = None

    description: str
    seller: SellerPreview
    price_value: float
    price_currency: str
    url: HttpUrl

    auto_delivery: int
    platform: Optional[str] = None
    ftype1: Optional[str] = None
    ftype2: Optional[str] = None

    @field_validator("auto_delivery", mode="before")
    @classmethod
    @lru_cache(maxsize=2)
    def bool_to_int(cls, v):
        if isinstance(v, bool):
            return int(v)
        return v
