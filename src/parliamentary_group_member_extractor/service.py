"""議員団メンバーシップ管理サービス

抽出された議員情報と既存の政治家データをマッチングし、
議員団メンバーシップを作成・管理する。
"""

import json
import re
from datetime import date
from typing import Any, TypedDict
from uuid import UUID

from langchain_core.prompts import PromptTemplate
from sqlalchemy import text

from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.interfaces.llm_service import ILLMService
from src.infrastructure.config.database import get_db_session
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupMembershipRepositoryImpl,
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_sync_impl import (
    PoliticianRepositorySyncImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.parliamentary_group_member_extractor.models import (
    ExtractedMember,
    MatchingResult,
    MembershipCreationResult,
)
from src.services.llm_service import LLMService


class PoliticianCandidate(TypedDict):
    """政治家候補の型定義"""

    id: int
    name: str
    political_party_id: int | None
    party_name: str | None
    district: str | None
    profile: str | None


def _clean_json_response(response_text: str) -> str:
    """LLMのレスポンスからJSON文字列を抽出してクリーニングする

    Args:
        response_text: LLMからの生のレスポンステキスト

    Returns:
        クリーニングされたJSON文字列
    """
    # Remove markdown code blocks if present
    # Pattern: ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"```(?:json)?\s*\n?", "", response_text)
    cleaned = cleaned.strip()

    # If still wrapped in backticks, remove them
    if cleaned.startswith("`") and cleaned.endswith("`"):
        cleaned = cleaned[1:-1].strip()

    return cleaned


class ParliamentaryGroupMembershipService:
    """議員団メンバーシップ管理サービス"""

    def __init__(
        self,
        llm_service: ILLMService | LLMService | None = None,
        politician_repo: PoliticianRepository
        | PoliticianRepositorySyncImpl
        | None = None,
        group_repo: Any | None = None,
        membership_repo: Any | None = None,
    ):
        """初期化

        Args:
            llm_service: LLMサービス
            politician_repo: 政治家リポジトリ
            group_repo: 議員団リポジトリ
            membership_repo: メンバーシップリポジトリ
        """
        self.llm_service = llm_service or LLMService()
        self.politician_repo = politician_repo or PoliticianRepositorySyncImpl(
            get_db_session()
        )
        self.group_repo = group_repo or RepositoryAdapter(
            ParliamentaryGroupRepositoryImpl, get_db_session()
        )
        self.membership_repo = membership_repo or RepositoryAdapter(
            ParliamentaryGroupMembershipRepositoryImpl, get_db_session()
        )

    async def match_politicians(
        self,
        extracted_members: list[ExtractedMember],
        conference_id: int | None = None,
    ) -> list[MatchingResult]:
        """抽出されたメンバーと既存の政治家をマッチング

        Args:
            extracted_members: 抽出されたメンバーリスト
            conference_id: 会議体ID（検索範囲を絞る場合）

        Returns:
            マッチング結果リスト
        """
        results: list[MatchingResult] = []

        for member in extracted_members:
            # 名前で政治家を検索
            candidates = self._search_politician_candidates(
                member.name, member.party_name, conference_id
            )

            if not candidates:
                results.append(
                    MatchingResult(
                        extracted_member=member,
                        politician_id=None,
                        politician_name=None,
                        confidence_score=0.0,
                        matching_reason="No matching politician found",
                    )
                )
                continue

            # LLMでベストマッチを判定
            best_match = await self._find_best_match_with_llm(member, candidates)
            results.append(best_match)

        return results

    def _search_politician_candidates(
        self,
        name: str,
        party_name: str | None = None,
        conference_id: int | None = None,
    ) -> list[PoliticianCandidate]:
        """政治家の候補を検索

        Args:
            name: 名前
            party_name: 政党名
            conference_id: 会議体ID

        Returns:
            候補となる政治家のリスト
        """
        # まず完全一致で検索
        candidates = []

        # 名前のスペースを正規化（全角・半角スペースを削除）
        normalized_name = name.replace(" ", "").replace("　", "")

        # 名前で検索（部分一致、スペースを無視）
        query = """
        SELECT DISTINCT p.id, p.name, p.political_party_id, pp.name as party_name,
               p.electoral_district, p.profile_url
        FROM politicians p
        LEFT JOIN political_parties pp ON p.political_party_id = pp.id
        LEFT JOIN politician_affiliations pa ON p.id = pa.politician_id
        WHERE REPLACE(REPLACE(p.name, ' ', ''), '　', '') LIKE :name_pattern
        """

        params: dict[str, str | int] = {"name_pattern": f"%{normalized_name}%"}

        # 会議体で絞り込み
        if conference_id:
            query += " AND pa.conference_id = :conference_id"
            params["conference_id"] = conference_id

        # 政党名で絞り込み（あいまい検索）
        if party_name:
            query += " AND pp.name LIKE :party_pattern"
            params["party_pattern"] = f"%{party_name}%"

        # PoliticianRepositoryは直接クエリ実行メソッドを持たないため、
        # 新しいセッションを作成して実行
        session = get_db_session()
        try:
            result = session.execute(text(query), params)
            rows = result.fetchall()
            candidates = [
                PoliticianCandidate(
                    id=row.id,
                    name=row.name,
                    political_party_id=row.political_party_id,
                    party_name=row.party_name,
                    district=row.electoral_district,
                    profile=row.profile_url,
                )
                for row in rows
            ]
        finally:
            session.close()

        return candidates

    async def _find_best_match_with_llm(
        self, extracted_member: ExtractedMember, candidates: list[PoliticianCandidate]
    ) -> MatchingResult:
        """LLMを使用してベストマッチを見つける

        Args:
            extracted_member: 抽出されたメンバー
            candidates: 候補となる政治家リスト

        Returns:
            マッチング結果
        """
        prompt = PromptTemplate(
            template="""以下の抽出された議員情報と、データベース内の政治家候補から最も適切なマッチを見つけてください。

抽出された議員情報:
- 名前: {member_name}
- 役職: {member_role}
- 政党: {member_party}
- 選挙区: {member_district}
- その他: {member_info}

候補となる政治家:
{candidates}

以下の基準でマッチングしてください:
1. 名前の一致度（漢字、ひらがな、カタカナの表記揺れを考慮）
2. 政党の一致
3. 選挙区の一致
4. その他の情報の整合性

出力形式:
- best_match_id: 最も適切な候補のID（マッチしない場合は-1）
- confidence_score: 信頼度（0.0-1.0）
- reason: 判定理由

JSONで回答してください。
""",
            input_variables=[
                "member_name",
                "member_role",
                "member_party",
                "member_district",
                "member_info",
                "candidates",
            ],
        )

        # 候補をフォーマット
        candidates_text = "\n".join(
            [
                (
                    f"ID: {c['id']}, 名前: {c['name']}, "
                    f"政党: {c.get('party_name', 'なし')}, "
                    f"選挙区: {c.get('district', 'なし')}"
                )
                for c in candidates
            ]
        )

        # GeminiLLMServiceを直接使用（LangChainのラッパーとして）
        # シンプルな文字列レスポンス用にLLMを直接呼び出す
        formatted_prompt = prompt.format(
            member_name=extracted_member.name,
            member_role=extracted_member.role or "なし",
            member_party=extracted_member.party_name or "なし",
            member_district=extracted_member.district or "なし",
            member_info=extracted_member.additional_info or "なし",
            candidates=candidates_text,
        )

        content: str = ""  # Initialize for error logging
        try:
            # Use LLM service's llm property to invoke directly
            if hasattr(self.llm_service, "llm"):
                response = self.llm_service.llm.invoke(formatted_prompt)  # type: ignore[attr-defined]
            else:
                raise AttributeError("LLM service does not have llm property")

            # レスポンスをパース
            if hasattr(response, "content"):
                raw_content = response.content
                if isinstance(raw_content, str):
                    content = raw_content
                    # Check if content is empty
                    if not content.strip():
                        raise ValueError("Empty response from LLM")

                    # Clean the JSON response (remove markdown code blocks, etc.)
                    cleaned_content = _clean_json_response(content)

                    # Parse JSON
                    result = json.loads(cleaned_content)
                else:
                    raise ValueError(f"Unexpected content type: {type(raw_content)}")
            else:
                # 予期しない形式の場合はエラーとして扱う
                raise ValueError("Unexpected response format from LLM")

            if result["best_match_id"] == -1:
                return MatchingResult(
                    extracted_member=extracted_member,
                    politician_id=None,
                    politician_name=None,
                    confidence_score=0.0,
                    matching_reason=result.get("reason", "No match found"),
                )

            # マッチした政治家を探す
            matched_politician = next(
                (c for c in candidates if c["id"] == result["best_match_id"]), None
            )

            if matched_politician:
                return MatchingResult(
                    extracted_member=extracted_member,
                    politician_id=matched_politician["id"],
                    politician_name=matched_politician["name"],
                    confidence_score=float(result.get("confidence_score", 0.8)),
                    matching_reason=result.get("reason", "LLM matching"),
                )
            else:
                return MatchingResult(
                    extracted_member=extracted_member,
                    politician_id=None,
                    politician_name=None,
                    confidence_score=0.0,
                    matching_reason="Invalid match ID returned",
                )

        except json.JSONDecodeError as e:
            print(f"LLM matching JSON parse error: {e}")
            print(
                f"Raw response content: {content if 'content' in locals() else 'N/A'}"
            )
            # エラー時は信頼度0で返す
            return MatchingResult(
                extracted_member=extracted_member,
                politician_id=None,
                politician_name=None,
                confidence_score=0.0,
                matching_reason=f"JSON parsing error: {str(e)}",
            )
        except Exception as e:
            print(f"LLM matching error: {e}")
            # エラー時は信頼度0で返す
            return MatchingResult(
                extracted_member=extracted_member,
                politician_id=None,
                politician_name=None,
                confidence_score=0.0,
                matching_reason=f"Matching error: {str(e)}",
            )

    def create_memberships(
        self,
        parliamentary_group_id: int,
        matching_results: list[MatchingResult],
        start_date: date | None = None,
        confidence_threshold: float = 0.7,
        dry_run: bool = False,
        user_id: UUID | None = None,
    ) -> MembershipCreationResult:
        """マッチング結果からメンバーシップを作成

        Args:
            parliamentary_group_id: 議員団ID
            matching_results: マッチング結果リスト
            start_date: 所属開始日（デフォルトは今日）
            confidence_threshold: 作成する最低信頼度
            dry_run: ドライラン（実際には作成しない）
            user_id: 作成したユーザーのID（UUID）

        Returns:
            作成結果
        """
        if start_date is None:
            start_date = date.today()

        result = MembershipCreationResult(
            total_extracted=len(matching_results),
            matched_count=0,
            created_count=0,
            skipped_count=0,
            errors=[],
        )

        # 現在のメンバーを取得
        current_members = self.membership_repo.get_current_members(
            parliamentary_group_id
        )
        current_politician_ids = {m["politician_id"] for m in current_members}

        for match in matching_results:
            # マッチしなかった場合
            if match.politician_id is None:
                continue

            result.matched_count += 1

            # 信頼度が閾値未満
            if match.confidence_score < confidence_threshold:
                result.errors.append(
                    f"{match.extracted_member.name}: 信頼度が低い "
                    f"({match.confidence_score:.2f} < {confidence_threshold})"
                )
                continue

            # すでにメンバーの場合
            if match.politician_id in current_politician_ids:
                result.skipped_count += 1
                continue

            # ドライランでない場合はメンバーシップを作成
            if not dry_run:
                try:
                    self.membership_repo.add_membership(
                        politician_id=match.politician_id,
                        parliamentary_group_id=parliamentary_group_id,
                        start_date=start_date,
                        role=match.extracted_member.role,
                        created_by_user_id=user_id,
                    )
                    result.created_count += 1
                except Exception as e:
                    result.errors.append(
                        f"{match.extracted_member.name}: 作成エラー - {str(e)}"
                    )
            else:
                # ドライランの場合はカウントのみ
                result.created_count += 1

        return result
