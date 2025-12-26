"""ユーザー認証ユースケース。

このモジュールは、ユーザー認証のビジネスロジックを提供します。
Google Sign-Inで取得したユーザー情報を使用して、usersテーブルにユーザーを
作成または更新します。
"""

import logging

from src.domain.entities.user import User
from src.domain.repositories.user_repository import IUserRepository


logger = logging.getLogger(__name__)


class AuthenticateUserUseCase:
    """ユーザー認証ユースケース。

    Google Sign-Inで認証されたユーザー情報を受け取り、
    データベースにユーザーを保存または更新します。
    """

    def __init__(self, user_repository: IUserRepository):
        """Initialize usecase.

        Args:
            user_repository: ユーザーリポジトリ
        """
        self.user_repository = user_repository

    async def execute(
        self,
        email: str,
        name: str | None = None,
        picture: str | None = None,
    ) -> User:
        """ユーザー認証を実行します。

        指定されたメールアドレスでユーザーを検索し、
        存在する場合はlast_login_atを更新、
        存在しない場合は新規作成します。

        Args:
            email: ユーザーのメールアドレス
            name: ユーザーの表示名
            picture: プロフィール画像のURL

        Returns:
            認証されたユーザーエンティティ

        Raises:
            ValueError: メールアドレスが無効な場合
            RuntimeError: データベースエラーが発生した場合
        """
        if not email or not email.strip():
            raise ValueError("メールアドレスは必須です")

        logger.info(f"ユーザー認証を実行: email={email}")

        try:
            # find_or_create_by_emailを使用して、ユーザーを検索または作成
            user = await self.user_repository.find_or_create_by_email(
                email=email,
                name=name,
                picture=picture,
            )

            logger.info(f"ユーザー認証完了: user_id={user.user_id}, email={user.email}")
            return user

        except Exception as e:
            logger.error(f"ユーザー認証エラー: {e}")
            raise RuntimeError(f"ユーザー認証に失敗しました: {e}") from e
