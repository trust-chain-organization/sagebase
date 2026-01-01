"""発言（Statement）エンティティをAI抽出結果から更新するUseCase。

このモジュールは、UpdateConversationFromExtractionUseCaseのエイリアスを提供します。
ドメイン用語として「Statement」の方が汎用的であり、Issue #865の要件に対応します。

Note:
    Conversation エンティティはデータベース上の実体であり、ビジネスドメインでは
    「Statement（発言）」として扱われます。このエイリアスにより、ドメイン用語と
    技術実装の両方をサポートします。
"""

from src.application.usecases.update_conversation_from_extraction_usecase import (
    UpdateConversationFromExtractionUseCase,
)


# StatementはConversationのビジネス用語としてのエイリアス
# Issue #865: Statement処理パイプラインへの抽出ログ統合
UpdateStatementFromExtractionUseCase = UpdateConversationFromExtractionUseCase

__all__ = ["UpdateStatementFromExtractionUseCase"]
