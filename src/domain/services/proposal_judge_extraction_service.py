"""Domain service for proposal judge extraction and matching."""

import re
from typing import Any


class ProposalJudgeExtractionService:
    """議案賛否情報抽出ドメインサービス

    議案ページから賛否情報を抽出し、名前の正規化や
    判定タイプの変換などのドメインロジックを提供します。
    """

    @staticmethod
    def normalize_judgment_type(judgment_text: str) -> tuple[str, bool]:
        """判定タイプテキストを正規化する

        Args:
            judgment_text: 判定テキスト（賛成、反対、棄権、欠席など）

        Returns:
            タプル（正規化された判定タイプ, 既知の判定タイプかどうか）
        """
        text = judgment_text.strip().upper()

        # Map Japanese and English variations to standard types
        if text in ["賛成", "APPROVE", "YES", "FOR", "賛", "○"]:
            return ("賛成", True)
        elif text in ["反対", "OPPOSE", "NO", "AGAINST", "反", "×", "✕"]:
            return ("反対", True)
        else:
            # Return 賛成 as default but indicate it was unknown
            return ("賛成", False)

    @staticmethod
    def normalize_politician_name(name: str) -> str:
        """政治家名を正規化する

        敬称の除去、スペースの正規化などを行います。

        Args:
            name: 政治家名

        Returns:
            正規化された政治家名
        """
        # Remove common honorifics and titles
        # Note: Longer titles first to avoid partial matches
        honorifics = [
            "副委員長",
            "委員長",
            "副議長",
            "議長",
            "副市長",
            "市長",
            "副知事",
            "知事",
            "議員",
            "先生",
            "氏",
            "さん",
            "君",
            "様",
        ]

        normalized = name.strip()

        # Remove honorifics at the end
        for honorific in honorifics:
            if normalized.endswith(honorific):
                normalized = normalized[: -len(honorific)].strip()

        # Normalize spaces
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = normalized.replace("　", " ")  # Replace full-width space

        return normalized

    @staticmethod
    def extract_party_from_text(text: str) -> str | None:
        """テキストから政党名を抽出する

        Args:
            text: 政党情報を含む可能性のあるテキスト

        Returns:
            抽出された政党名、見つからない場合はNone
        """
        # Common party patterns
        party_patterns = [
            r"（([^）]+)）",  # Parentheses (full-width)
            r"\(([^)]+)\)",  # Parentheses (half-width)
            r"【([^】]+)】",  # Square brackets (full-width)
            r"\[([^\]]+)\]",  # Square brackets (half-width)
        ]

        for pattern in party_patterns:
            match = re.search(pattern, text)
            if match:
                party = match.group(1).strip()
                # Check if it looks like a party name (not too long)
                if len(party) <= 20:
                    return party

        return None

    @staticmethod
    def parse_voting_result_text(text: str) -> list[dict[str, Any]]:
        """投票結果テキストをパースして賛否情報を抽出する

        Args:
            text: 投票結果を含むテキスト

        Returns:
            賛否情報のリスト（名前、政党、判定を含む辞書のリスト）
        """
        results = []

        # Split text into sections (approve, oppose)
        sections = {
            "賛成": ["賛成", "賛成者", "賛成議員", "可決", "承認"],
            "反対": ["反対", "反対者", "反対議員", "否決", "不承認"],
        }

        current_judgment = None
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this line indicates a judgment section
            for judgment, keywords in sections.items():
                if any(keyword in line for keyword in keywords):
                    current_judgment = judgment
                    break

            # 棄権や欠席のセクションは無視（賛成・反対のみ処理）
            if any(
                keyword in line
                for keyword in ["棄権", "欠席", "退席", "ABSTAIN", "ABSENT"]
            ):
                current_judgment = None
                continue

            # If we have a current judgment and the line contains names
            if current_judgment and not any(
                keyword in line
                for keywords in sections.values()
                for keyword in keywords
            ):
                # Try to extract names from the line
                # Names might be separated by various delimiters
                delimiters = ["、", "，", ",", "・", " "]
                names = [line]

                for delimiter in delimiters:
                    if delimiter in line:
                        names = line.split(delimiter)
                        break

                for name in names:
                    name = name.strip()
                    if not name:
                        continue

                    # Extract party if present
                    party = ProposalJudgeExtractionService.extract_party_from_text(name)

                    # Remove party from name
                    if party:
                        name = re.sub(r"[（(【\[].*?[）)】\]]", "", name).strip()

                    # Normalize the name
                    name = ProposalJudgeExtractionService.normalize_politician_name(
                        name
                    )

                    if name:  # Only add if name is not empty after normalization
                        results.append(
                            {
                                "name": name,
                                "party": party,
                                "judgment": current_judgment,
                            }
                        )

        return results

    @staticmethod
    def calculate_matching_confidence(
        extracted_name: str,
        politician_name: str,
        extracted_party: str | None = None,
        politician_party: str | None = None,
    ) -> float:
        """政治家名のマッチング信頼度を計算する

        Args:
            extracted_name: 抽出された名前
            politician_name: 政治家データベースの名前
            extracted_party: 抽出された政党名（オプション）
            politician_party: 政治家の所属政党名（オプション）

        Returns:
            マッチング信頼度（0.0〜1.0）
        """
        # Normalize names for comparison
        norm_extracted = ProposalJudgeExtractionService.normalize_politician_name(
            extracted_name
        )
        norm_politician = ProposalJudgeExtractionService.normalize_politician_name(
            politician_name
        )

        # Exact match
        if norm_extracted == norm_politician:
            confidence = 1.0
        # One name contains the other
        elif norm_extracted in norm_politician or norm_politician in norm_extracted:
            confidence = 0.8
        # Similar length and some common characters
        else:
            # Calculate character similarity
            common_chars = sum(1 for c in norm_extracted if c in norm_politician)
            max_len = max(len(norm_extracted), len(norm_politician))
            confidence = common_chars / max_len if max_len > 0 else 0.0

        # Adjust based on party match
        if extracted_party and politician_party:
            if extracted_party == politician_party:
                confidence = min(1.0, confidence + 0.2)
            else:
                confidence = max(0.0, confidence - 0.1)

        return confidence

    @staticmethod
    def is_parliamentary_group(name: str) -> bool:
        """名前が議員団・会派名かどうかを判定する

        Args:
            name: チェックする名前

        Returns:
            議員団・会派名の場合True
        """
        group_keywords = [
            "会派",
            "議員団",
            "クラブ",
            "の会",
            "グループ",
            "連合",
            "連盟",
            "同盟",
            "協議会",
            "委員会",
        ]

        return any(keyword in name for keyword in group_keywords)

    @staticmethod
    def extract_members_from_group_text(group_text: str) -> list[str]:
        """議員団・会派のテキストから個別メンバー名を抽出する

        Args:
            group_text: 議員団・会派の情報を含むテキスト

        Returns:
            メンバー名のリスト
        """
        members = []

        # Look for patterns like "所属議員：" or "メンバー："
        member_patterns = [
            r"所属議員[：:]\s*(.+)",
            r"メンバー[：:]\s*(.+)",
            r"構成員[：:]\s*(.+)",
            r"議員[：:]\s*(.+)",
        ]

        for pattern in member_patterns:
            match = re.search(pattern, group_text)
            if match:
                member_text = match.group(1)
                # Split by common delimiters
                for delimiter in ["、", "，", ",", "・"]:
                    if delimiter in member_text:
                        names = member_text.split(delimiter)
                        for name in names:
                            service = ProposalJudgeExtractionService
                            normalized = service.normalize_politician_name(name.strip())
                            if normalized:
                                members.append(normalized)
                        break
                # If we found members, stop looking for other patterns
                if members:
                    break

        return members
