"""提出者種別を表す値オブジェクト."""

from enum import Enum


class SubmitterType(Enum):
    """提出者種別.

    議案の提出者の種別を表す。
    """

    MAYOR = "mayor"
    POLITICIAN = "politician"
    PARLIAMENTARY_GROUP = "parliamentary_group"
    COMMITTEE = "committee"
    OTHER = "other"
