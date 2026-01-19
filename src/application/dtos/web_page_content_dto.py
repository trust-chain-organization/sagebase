"""WebページコンテンツDTO

WebスクレイピングでHTMLコンテンツを取得した結果を表現します。
"""

from pydantic import BaseModel, Field


class WebPageContentDTO(BaseModel):
    """Webページのコンテンツ"""

    url: str = Field(description="ページのURL")
    html_content: str = Field(description="HTMLコンテンツ")
    page_number: int | None = Field(
        description="ページ番号（ページネーションがある場合）", default=None
    )
