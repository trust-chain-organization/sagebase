"""Use case for creating parliamentary group memberships from matched members."""

from datetime import date
from uuid import UUID

from src.domain.repositories.extracted_parliamentary_group_member_repository import (
    ExtractedParliamentaryGroupMemberRepository,
)
from src.domain.repositories.parliamentary_group_membership_repository import (
    ParliamentaryGroupMembershipRepository,
)


class CreateParliamentaryGroupMembershipsUseCase:
    """議員団メンバーシップ作成ユースケース

    マッチング済みの抽出メンバーから、parliamentary_group_memberships
    テーブルにレコードを作成します。

    Attributes:
        member_repository: 抽出メンバーリポジトリ
        membership_repository: メンバーシップリポジトリ

    Transaction Management:
        各メンバーシップ作成は個別にコミットされます。
        エラーが発生した場合は該当メンバーのみスキップされ、
        他のメンバーシップ作成は継続されます。

    Example:
        >>> use_case = CreateParliamentaryGroupMembershipsUseCase(
        ...     member_repo, membership_repo
        ... )
        >>> results = await use_case.execute(parliamentary_group_id=1)
        >>> print(f"Created {results['created_count']} memberships")
    """

    def __init__(
        self,
        member_repository: ExtractedParliamentaryGroupMemberRepository,
        membership_repository: ParliamentaryGroupMembershipRepository,
    ):
        """Initialize the use case.

        Args:
            member_repository: 抽出メンバーリポジトリ
            membership_repository: メンバーシップリポジトリ
        """
        self.member_repo = member_repository
        self.membership_repo = membership_repository

    async def execute(
        self,
        parliamentary_group_id: int | None = None,
        min_confidence: float = 0.7,
        start_date: date | None = None,
        user_id: UUID | None = None,
    ) -> dict[str, int | list[dict[str, int | str | None]]]:
        """マッチング済みメンバーからメンバーシップを作成する

        Args:
            parliamentary_group_id: 処理対象の議員団ID（Noneの場合は全matched）
            min_confidence: 最小信頼度（デフォルト: 0.7）
            start_date: メンバーシップ開始日（Noneの場合は今日）
            user_id: 作成したユーザーのID（UUID）

        Returns:
            作成結果の辞書。以下を含む：
            - created_count: 作成されたメンバーシップ数
            - skipped_count: スキップされたメンバー数
            - created_memberships: 作成されたメンバーシップの詳細リスト

        Transaction Boundary:
            各メンバーシップ作成は個別のトランザクションで実行されます。
            これにより、1つのメンバーシップ作成が失敗しても、
            他のメンバーシップ作成は継続されます。
            エラーが発生したメンバーはskipped_countに計上されます。
        """
        # matched状態のメンバーを取得
        matched_members = await self.member_repo.get_matched_members(
            parliamentary_group_id=parliamentary_group_id,
            min_confidence=min_confidence,
        )

        created_memberships: list[dict[str, int | str | None]] = []
        skipped_count = 0

        # デフォルトの開始日は今日
        if start_date is None:
            start_date = date.today()

        for member in matched_members:
            # matched_politician_idが設定されているか確認
            if member.matched_politician_id is None:
                skipped_count += 1
                continue

            # メンバーシップを作成
            try:
                await self.membership_repo.create_membership(
                    politician_id=member.matched_politician_id,
                    group_id=member.parliamentary_group_id,
                    start_date=start_date,
                    role=member.extracted_role,
                    created_by_user_id=user_id,
                )

                created_memberships.append(
                    {
                        "politician_id": member.matched_politician_id,
                        "parliamentary_group_id": member.parliamentary_group_id,
                        "role": member.extracted_role,
                        "member_name": member.extracted_name,
                    }
                )
            except Exception as e:
                # エラーが発生した場合はスキップ
                print(f"Failed to create membership for {member.extracted_name}: {e}")
                skipped_count += 1

        return {
            "created_count": len(created_memberships),
            "skipped_count": skipped_count,
            "created_memberships": created_memberships,
        }
