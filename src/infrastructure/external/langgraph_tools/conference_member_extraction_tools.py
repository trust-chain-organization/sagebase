"""会議体メンバー抽出用のLangGraphツール

BAMLを使用した会議体メンバー抽出をLangGraphエージェントから
呼び出すためのツールを提供します。

Issue #903: [LangGraph+BAML] 会議体メンバー抽出のエージェント化
"""

import logging

from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Any

from langchain_core.tools import tool

from src.domain.dtos.conference_member_dto import ExtractedMemberDTO


if TYPE_CHECKING:
    from src.domain.interfaces.member_extractor_service import IMemberExtractorService


logger = logging.getLogger(__name__)


def create_conference_member_extraction_tools(
    member_extractor: "IMemberExtractorService | None" = None,
) -> list[Any]:
    """会議体メンバー抽出用のLangGraphツールを作成

    Args:
        member_extractor: メンバー抽出サービス（省略時はファクトリから取得）
            テスト時にモックを注入可能

    Returns:
        LangGraphツールのリスト:
        - extract_members_from_html: HTMLからメンバーを抽出
        - validate_extracted_members: 抽出結果を検証
        - deduplicate_members: 重複メンバーを除去
    """
    # 外部からextractorが渡されない場合はファクトリから取得
    _extractor = member_extractor

    @tool
    async def extract_members_from_html(
        html_content: str,
        conference_name: str,
    ) -> dict[str, Any]:
        """HTMLコンテンツから会議体メンバーを抽出

        BAMLを使用してHTMLから会議体メンバー情報を抽出します。
        名前、役職、所属政党などの情報を構造化して返します。

        Args:
            html_content: 解析対象のHTMLコンテンツ
            conference_name: 会議体名（抽出精度向上に使用）

        Returns:
            Dictionary with:
            - members: 抽出されたメンバーのリスト
              - name: 議員名
              - role: 役職
              - party_name: 所属政党名
              - additional_info: その他情報
            - count: 抽出されたメンバー数
            - success: 抽出成功フラグ
            - conference_name: 会議体名（入力のエコー）
            - error: エラーメッセージ（エラー時のみ）

        Example:
            >>> result = await extract_members_from_html(
            ...     html_content="<html>...</html>",
            ...     conference_name="総務委員会"
            ... )
            >>> print(result["count"])
            15
        """
        try:
            # 入力検証
            if not html_content or not html_content.strip():
                return {
                    "members": [],
                    "count": 0,
                    "success": False,
                    "conference_name": conference_name,
                    "error": "HTMLコンテンツが空です",
                }

            if not conference_name or not conference_name.strip():
                return {
                    "members": [],
                    "count": 0,
                    "success": False,
                    "conference_name": conference_name,
                    "error": "会議体名が空です",
                }

            logger.info(
                f"Starting member extraction for '{conference_name}' "
                f"(HTML size: {len(html_content)} chars)"
            )

            # 依存性注入: 外部からextractorが渡されていない場合はファクトリから取得
            nonlocal _extractor
            if _extractor is None:
                from src.infrastructure.external.conference_member_extractor.factory import (  # noqa: E501
                    MemberExtractorFactory,
                )

                _extractor = MemberExtractorFactory.create()

            members: list[ExtractedMemberDTO] = await _extractor.extract_members(
                html_content=html_content,
                conference_name=conference_name,
            )

            # DTOを辞書形式に変換
            members_dict = [
                {
                    "name": m.name,
                    "role": m.role,
                    "party_name": m.party_name,
                    "additional_info": m.additional_info,
                }
                for m in members
            ]

            logger.info(
                f"Extraction completed: {len(members_dict)} members "
                f"from '{conference_name}'"
            )

            return {
                "members": members_dict,
                "count": len(members_dict),
                "success": True,
                "conference_name": conference_name,
            }

        except Exception as e:
            logger.error(
                f"Error extracting members from HTML: {e}",
                exc_info=True,
            )
            return {
                "members": [],
                "count": 0,
                "success": False,
                "conference_name": conference_name,
                "error": str(e),
            }

    @tool
    async def validate_extracted_members(
        members: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """抽出されたメンバー情報を検証

        名前の妥当性、役職の妥当性、重複などをチェックします。
        検証に失敗したメンバーはエラーリストに追加されます。

        Args:
            members: 検証対象のメンバーリスト
              - name: 議員名
              - role: 役職
              - party_name: 所属政党名
              - additional_info: その他情報

        Returns:
            Dictionary with:
            - valid_members: 検証に通過したメンバーのリスト
            - invalid_members: 検証に失敗したメンバーのリスト
            - validation_errors: 検証エラーメッセージのリスト
            - total_count: 入力メンバー総数
            - valid_count: 有効メンバー数
            - invalid_count: 無効メンバー数

        Example:
            >>> result = await validate_extracted_members(members=[
            ...     {"name": "田中太郎", "role": "委員長"},
            ...     {"name": "", "role": "委員"}  # 無効
            ... ])
            >>> print(result["valid_count"])
            1
        """
        try:
            if not members:
                return {
                    "valid_members": [],
                    "invalid_members": [],
                    "validation_errors": [],
                    "total_count": 0,
                    "valid_count": 0,
                    "invalid_count": 0,
                }

            valid_members: list[dict[str, Any]] = []
            invalid_members: list[dict[str, Any]] = []
            validation_errors: list[str] = []

            # 名前の重複チェック用
            seen_names: set[str] = set()

            for i, member in enumerate(members):
                errors_for_member: list[str] = []
                name = member.get("name", "")
                role = member.get("role", "")

                # 名前の検証
                if not name or not name.strip():
                    errors_for_member.append(f"メンバー{i + 1}: 名前が空です")
                elif name.isdigit():
                    errors_for_member.append(f"メンバー{i + 1}: 名前が数字のみです")
                elif len(name.strip()) < 2:
                    errors_for_member.append(
                        f"メンバー{i + 1}: 名前が短すぎます ({name})"
                    )

                # 役職の検証（空でも許容、ただし警告）
                valid_roles = {
                    "議長",
                    "副議長",
                    "委員長",
                    "副委員長",
                    "委員",
                    "理事",
                    "幹事",
                    "監事",
                    "会長",
                    "副会長",
                    "理事長",
                }
                if role and role not in valid_roles:
                    # 完全一致しなくても部分一致で許容
                    if not any(vr in role for vr in valid_roles):
                        logger.warning(
                            f"メンバー{i + 1}: 役職 '{role}' "
                            "は一般的でない可能性があります"
                        )

                # 重複チェック
                normalized_name = name.strip() if name else ""
                if normalized_name and normalized_name in seen_names:
                    errors_for_member.append(
                        f"メンバー{i + 1}: 名前 '{name}' が重複しています"
                    )
                elif normalized_name:
                    seen_names.add(normalized_name)

                # 検証結果の振り分け
                if errors_for_member:
                    invalid_members.append(member)
                    validation_errors.extend(errors_for_member)
                else:
                    valid_members.append(member)

            logger.info(
                f"Validation completed: {len(valid_members)} valid, "
                f"{len(invalid_members)} invalid out of {len(members)} total"
            )

            return {
                "valid_members": valid_members,
                "invalid_members": invalid_members,
                "validation_errors": validation_errors,
                "total_count": len(members),
                "valid_count": len(valid_members),
                "invalid_count": len(invalid_members),
            }

        except Exception as e:
            logger.error(
                f"Error validating members: {e}",
                exc_info=True,
            )
            return {
                "valid_members": [],
                "invalid_members": members,
                "validation_errors": [f"検証中にエラーが発生: {str(e)}"],
                "total_count": len(members) if members else 0,
                "valid_count": 0,
                "invalid_count": len(members) if members else 0,
            }

    @tool
    async def deduplicate_members(
        members: list[dict[str, Any]],
        similarity_threshold: float = 0.85,
    ) -> dict[str, Any]:
        """重複メンバーを除去

        名前の類似度に基づいて重複を検出し、統合します。
        同一人物の異なる表記（姓名の間のスペースなど）を統合します。

        Args:
            members: 重複除去対象のメンバーリスト
            similarity_threshold: 類似度の閾値（0.0-1.0、デフォルト0.85）
              - 0.85以上で同一人物と判定

        Returns:
            Dictionary with:
            - unique_members: 重複除去後のメンバーリスト
            - duplicates_removed: 除去された重複メンバーのリスト
            - merge_info: 統合情報のリスト
              - kept: 残したメンバー名
              - removed: 除去したメンバー名
              - similarity: 類似度
            - original_count: 元のメンバー数
            - unique_count: 重複除去後のメンバー数

        Example:
            >>> result = await deduplicate_members(members=[
            ...     {"name": "田中太郎", "role": "委員長"},
            ...     {"name": "田中 太郎", "role": "委員"}  # 重複
            ... ])
            >>> print(result["unique_count"])
            1
        """
        try:
            if not members:
                return {
                    "unique_members": [],
                    "duplicates_removed": [],
                    "merge_info": [],
                    "original_count": 0,
                    "unique_count": 0,
                }

            unique_members: list[dict[str, Any]] = []
            duplicates_removed: list[dict[str, Any]] = []
            merge_info: list[dict[str, Any]] = []

            for member in members:
                name = member.get("name", "")
                if not name:
                    continue

                # 正規化（スペース除去）
                normalized_name = name.replace(" ", "").replace("　", "")

                # 既存のユニークメンバーと比較
                is_duplicate = False
                for existing in unique_members:
                    existing_name = existing.get("name", "")
                    existing_normalized = existing_name.replace(" ", "").replace(
                        "　", ""
                    )

                    # 完全一致チェック（正規化後）
                    if normalized_name == existing_normalized:
                        is_duplicate = True
                        duplicates_removed.append(member)
                        merge_info.append(
                            {
                                "kept": existing_name,
                                "removed": name,
                                "similarity": 1.0,
                            }
                        )
                        break

                    # 類似度チェック
                    similarity = SequenceMatcher(
                        None, normalized_name, existing_normalized
                    ).ratio()
                    if similarity >= similarity_threshold:
                        is_duplicate = True
                        duplicates_removed.append(member)
                        merge_info.append(
                            {
                                "kept": existing_name,
                                "removed": name,
                                "similarity": round(similarity, 3),
                            }
                        )
                        break

                if not is_duplicate:
                    unique_members.append(member)

            logger.info(
                f"Deduplication completed: {len(unique_members)} unique, "
                f"{len(duplicates_removed)} duplicates removed "
                f"from {len(members)} total"
            )

            return {
                "unique_members": unique_members,
                "duplicates_removed": duplicates_removed,
                "merge_info": merge_info,
                "original_count": len(members),
                "unique_count": len(unique_members),
            }

        except Exception as e:
            logger.error(
                f"Error deduplicating members: {e}",
                exc_info=True,
            )
            return {
                "unique_members": members,
                "duplicates_removed": [],
                "merge_info": [],
                "original_count": len(members) if members else 0,
                "unique_count": len(members) if members else 0,
                "error": str(e),
            }

    return [extract_members_from_html, validate_extracted_members, deduplicate_members]
