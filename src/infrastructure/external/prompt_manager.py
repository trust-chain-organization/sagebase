"""Centralized prompt management for all LLM operations"""

import logging

from typing import TYPE_CHECKING, Any

from langchain import hub
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

if TYPE_CHECKING:
    from src.infrastructure.external.versioned_prompt_manager import (
        VersionedPromptManager,
    )

logger = logging.getLogger(__name__)


class PromptManager:
    """Manages prompts for different LLM operations"""

    # Centralized prompt templates
    PROMPTS = {
        "minutes_divide": """議事録を分析し、30個のセクションに分割してください。
各セクションには以下の情報を含めてください：
- chapter_number: セクション番号（1から始まる連番）
- keyword: そのセクションを識別するキーワード（発言者名や重要な語句）

議事録:
{minutes}
""",
        "speech_divide": """以下のセクションから発言者と発言内容を抽出してください。
各発言について以下の情報を含めてください：
- speech_order: 発言順序（1から始まる連番）
- speaker: 発言者名
- content: 発言内容

セクション:
{section_string}
""",
        "politician_extract": """議事録から政治家の情報を抽出してください。
各政治家について以下の情報を含めてください：
- name: 氏名
- party: 所属政党（わかる場合）
- position: 役職（わかる場合）

議事録:
{minutes}
""",
        "speaker_match": """あなたは議事録の発言者名マッチング専門家です。
議事録から抽出された発言者名と、既存の発言者リストから最も適切なマッチを見つけてください。

# 抽出された発言者名
{speaker_name}

# 既存の発言者リスト
{available_speakers}

# マッチング基準
1. 完全一致を最優先
2. 括弧内の名前との一致（例: "委員長(平山たかお)" → "平山たかお"）
3. 記号除去後の一致（例: "◆委員(下村あきら)" → "委員(下村あきら)"）
4. 部分一致や音韻的類似性
5. 漢字の異なる読みや表記ゆれ

# 出力形式
以下のJSON形式で回答してください：
{{
    "matched": true/false,
    "speaker_id": マッチした場合のID (数値) または null,
    "speaker_name": マッチした場合の名前 (文字列) または null,
    "confidence": 信頼度 (0.0-1.0の小数),
    "reason": "マッチング判定の理由"
}}

# 重要な注意事項
- 確実性が低い場合は matched: false を返してください
- confidence は 0.8 以上の場合のみマッチとして扱ってください
- 複数の候補がある場合は最も確からしいものを選んでください
""",
        "speech_divide_kokkai": """以下の国会議事録のセクションから発言者と
発言内容を抽出してください。

国会議事録の形式:
- 発言者名は通常「○」や「◆」などの記号に続いて記載されます（例：○林国務大臣、○原口委員）
- 委員長の発言は記号なしで記載されることがあります
- 議事録の末尾には「発言者一覧」として発言者リストが記載されていることがあります

抽出ルール:
1. 人名として適切な発言者名のみを抽出してください
2. 以下は発言者名として扱わないでください:
   - 「タイトル」「発言者」「御質問」「我が国」「警察庁」「岸田内閣」「冒頭」
     「短くお願いします」など一般名詞
   - 「==」などの区切り文字
   - 「不明」（発言者が特定できない場合のみ使用）
3. 発言者名から役職や敬称を含めて抽出してください（例：林国務大臣、原口委員）
4. 発言内容が空の場合や意味のない内容の場合は除外してください

各発言について以下の情報を含めてください：
- speech_order: 発言順序（1から始まる連番）
- speaker: 発言者名（人名のみ）
- speech_content: 発言内容

セクション:
{section_string}
""",
        "party_member_extract": """あなたは政党の議員一覧ページから議員情報を抽出する
専門家です。
以下のHTMLコンテンツから、{party_name}所属の全ての議員情報（国会議員および地方議員）を抽出してください。

抽出する情報：
- name: 議員の氏名（姓名）
- position: 役職（衆議院議員、参議院議員、都道府県議会議員、市区町村議会議員など）
- electoral_district: 選挙区（例：東京1区、比例北海道、渋谷区、盛岡市など）
- prefecture: 都道府県（地方議員の場合は所属自治体から、国会議員の場合は選挙区から推測）
- profile_url: プロフィールページのURL（相対URLの場合は{base_url}を基準に絶対URLに変換）
- party_position: 党内役職（代表、幹事長など）

注意事項：
- 国会議員（衆議院議員、参議院議員）だけでなく、
  地方議員（都道府県議会議員、市区町村議会議員）も全て含めてください
- 「自治体議員」「地方議員」というセクションがある場合は、その全員を抽出してください
- position には具体的な議会名を含めてください
  （例：「東京都渋谷区議会議員」「岩手県盛岡市議会議員」）
- 議員でない人物（スタッフ、事務所関係者、候補予定者など）は除外してください
- 氏名は漢字表記を優先し、ふりがなは除外してください
- URLは絶対URLに変換してください

HTMLコンテンツ：
{content}
""",
    }

    # LangChain Hub prompt mappings
    HUB_PROMPTS = {
        "divide_chapter_prompt": "divide_chapter_prompt",
        "redivide_chapter_prompt": "redivide_chapter_prompt",
        "comment_divide_prompt": "comment_divide_prompt",
        "politician_extraction_prompt": "politician_extraction_prompt",
    }

    def __init__(self):
        self._cached_prompts: dict[str, ChatPromptTemplate] = {}
        self._hub_prompts: dict[str, PromptTemplate] = {}
        self._versioned_manager: VersionedPromptManager | None = None

    def set_versioned_manager(self, manager: "VersionedPromptManager") -> None:
        """Set the versioned prompt manager for database-backed prompts.

        Args:
            manager: VersionedPromptManager instance
        """
        self._versioned_manager = manager

    async def get_prompt_async(
        self, prompt_key: str, variables: dict[str, Any] | None = None
    ) -> tuple[str, str]:
        """Get a prompt template asynchronously (supports versioning).

        Args:
            prompt_key: Key identifying the prompt
            variables: Optional variables for prompt formatting

        Returns:
            Tuple of (formatted_prompt, version)
        """
        # Try versioned manager first
        if self._versioned_manager:
            try:
                return await self._versioned_manager.get_versioned_prompt(
                    prompt_key, variables
                )
            except Exception as e:
                logger.warning(f"Failed to get versioned prompt for {prompt_key}: {e}")

        # Fall back to static prompts
        template = self.get_prompt(prompt_key)
        formatted = template.format(**(variables or {}))
        return formatted, "static"

    def get_prompt(self, prompt_key: str) -> ChatPromptTemplate:
        """
        Get a prompt template by key

        Args:
            prompt_key: Key identifying the prompt

        Returns:
            ChatPromptTemplate instance
        """
        if prompt_key not in self._cached_prompts:
            if prompt_key in self.PROMPTS:
                self._cached_prompts[prompt_key] = ChatPromptTemplate.from_template(
                    self.PROMPTS[prompt_key]
                )
            else:
                raise ValueError(f"Unknown prompt key: {prompt_key}")

        return self._cached_prompts[prompt_key]

    def get_hub_prompt(self, prompt_key: str) -> PromptTemplate:
        """
        Get a prompt from LangChain Hub

        Args:
            prompt_key: Key identifying the hub prompt

        Returns:
            PromptTemplate from hub
        """
        if prompt_key not in self._hub_prompts:
            if prompt_key in self.HUB_PROMPTS:
                try:
                    self._hub_prompts[prompt_key] = hub.pull(
                        self.HUB_PROMPTS[prompt_key]
                    )
                except Exception as e:
                    logger.warning(f"Failed to pull prompt from hub: {e}")
                    # Fallback to local prompt if available
                    fallback_key = prompt_key.replace("_prompt", "")
                    if fallback_key in self.PROMPTS:
                        # Return a PromptTemplate from the string
                        return PromptTemplate.from_template(self.PROMPTS[fallback_key])
                    raise
            else:
                raise ValueError(f"Unknown hub prompt key: {prompt_key}")

        return self._hub_prompts[prompt_key]

    def create_custom_prompt(
        self, template: str, cache_key: str | None = None
    ) -> ChatPromptTemplate:
        """
        Create a custom prompt template

        Args:
            template: Prompt template string
            cache_key: Optional key to cache the prompt

        Returns:
            ChatPromptTemplate instance
        """
        prompt = ChatPromptTemplate.from_template(template)

        if cache_key:
            self._cached_prompts[cache_key] = prompt

        return prompt

    async def save_prompt_version(
        self,
        prompt_key: str,
        template: str,
        version: str | None = None,
        description: str | None = None,
        created_by: str | None = None,
    ) -> bool:
        """Save a new version of a prompt (if versioned manager is available).

        Args:
            prompt_key: Key identifying the prompt
            template: The prompt template content
            version: Version identifier (auto-generated if not provided)
            description: Optional description
            created_by: Creator identifier

        Returns:
            True if saved successfully, False otherwise
        """
        if not self._versioned_manager:
            logger.warning("No versioned manager available for saving prompts")
            return False

        try:
            # Extract variables from template
            test_prompt = ChatPromptTemplate.from_template(template)
            variables = list(test_prompt.input_variables)

            result = await self._versioned_manager.save_new_version(
                prompt_key=prompt_key,
                template=template,
                version=version,
                description=description,
                variables=variables,
                created_by=created_by,
                activate=True,
            )

            return result is not None
        except Exception as e:
            logger.error(f"Failed to save prompt version: {e}")
            return False

    @classmethod
    def get_default_instance(cls) -> "PromptManager":
        """Get default instance (singleton pattern)"""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance
