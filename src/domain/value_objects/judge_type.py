"""賛否情報の種別を表す値オブジェクト."""

from enum import Enum


class JudgeType(Enum):
    """賛否情報の種別.

    賛否情報が会派単位か政治家単位かを区別する。
    """

    PARLIAMENTARY_GROUP = "parliamentary_group"
    POLITICIAN = "politician"
