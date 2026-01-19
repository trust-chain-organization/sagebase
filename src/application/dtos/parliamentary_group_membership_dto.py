"""議員団メンバーシップDTO

議員団メンバーシップに関連するDTOを定義します。
リポジトリコントラクトで使用されます。
"""

from dataclasses import dataclass

from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership,
)
from src.domain.entities.politician import Politician


@dataclass
class ParliamentaryGroupMembershipWithRelationsDTO:
    """議員団メンバーシップと関連エンティティのDTO

    議員団メンバーシップを関連する政治家・議員団データと一緒に
    取得する際に使用します。ドメインエンティティへの動的属性
    追加を避けることでClean Architectureを維持します。
    """

    membership: ParliamentaryGroupMembership
    politician: Politician | None
    parliamentary_group: ParliamentaryGroup | None
