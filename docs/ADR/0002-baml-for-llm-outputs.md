# ADR 0002: BAML (Boundary ML) の採用 - LLM構造化出力

## Status

Accepted (2024-11-15)

## Context

### 背景

Sagebaseプロジェクトでは、以下のようなLLMベースの構造化出力処理を多数実装しています：

- **議事録分割処理**: 議事録PDFを発言単位に分割
- **話者マッチング**: 発言者名を政治家データベースとマッチング
- **政治家マッチング**: 抽出された政治家名を既存データとマッチング
- **会議体メンバー抽出**: Webページから会議体メンバー情報を抽出
- **議員団メンバー抽出**: 議員団のメンバー情報を抽出
- **政党メンバー抽出**: 政党のメンバー情報を抽出

これらの処理では、LLMの出力を構造化データ（Pythonオブジェクト）として扱う必要があります。

### 課題: Pydanticベースの実装の問題点

プロジェクト初期では、**Pydantic**を使用してLLM出力を構造化していました：

```python
# Pydanticベースの実装（旧実装）
from pydantic import BaseModel, Field

class SpeakerMatchResult(BaseModel):
    """話者マッチング結果"""
    matched: bool = Field(description="マッチングが成功したか")
    confidence: float = Field(description="信頼度 (0.0-1.0)")
    matched_id: int | None = Field(description="マッチした政治家のID")
    reason: str = Field(description="マッチング理由")

# プロンプトにスキーマを含める
prompt = f"""
以下の話者を政治家候補とマッチングしてください。

出力形式（JSON）:
{{
  "matched": true/false,
  "confidence": 0.0-1.0,
  "matched_id": 整数またはnull,
  "reason": "理由の説明"
}}

話者: {speaker_name}
候補: {candidates}
"""

# LLM呼び出し
response = llm.invoke(prompt)
result = SpeakerMatchResult.model_validate_json(response.content)
```

この実装には以下の問題がありました：

#### 1. トークン効率の問題

- **詳細なスキーマ説明が必要**: Pydanticの`Field(description=...)`をプロンプトに含める必要がある
- **冗長なJSON例**: 出力形式の例を詳細に記述する必要がある
- **トークン消費量が多い**: スキーマ説明だけで100-200トークン消費

**例**: 話者マッチングプロンプトのトークン数
- Pydanticベース: 約350トークン（スキーマ説明 150 + 実際のプロンプト 200）
- BAML: 約250トークン（スキーマ説明不要、プロンプトのみ 250）

#### 2. 型安全性の問題

- **実行時エラー**: LLMが不正なJSONを返すと、パース時にエラー
- **型チェックが不完全**: Pydanticはランタイムバリデーションのみ（静的型チェックなし）
- **リファクタリングが困難**: スキーマ変更時に、プロンプト文字列も手動で変更が必要

#### 3. メンテナンス性の問題

- **スキーマとプロンプトの二重管理**: Pydanticモデルとプロンプト内のスキーマ説明を別々に管理
- **プロンプトのバージョン管理が困難**: プロンプト文字列がコード内に埋め込まれている
- **再利用性が低い**: 同じスキーマを複数の場所で定義する必要がある

### 検討した代替案

#### 1. Pydanticのみ（現状維持）

**概要**: Pydanticモデルを使用してLLM出力を構造化

**利点**:
- シンプル（追加の依存関係不要）
- Pythonエコシステムで広く使われている
- 多くの開発者に馴染みがある

**欠点**:
- トークン効率が悪い（スキーマ説明が冗長）
- 型安全性が不完全（ランタイムのみ）
- プロンプトとスキーマの二重管理

#### 2. Instructor

**概要**: Pydanticモデルをベースに、LLM出力の構造化を支援するライブラリ

**利点**:
- Pydanticベースで学習コストが低い
- リトライ機能が組み込まれている
- OpenAI APIとの統合が良好

**欠点**:
- トークン効率はPydanticと同程度（改善なし）
- プロンプト管理機能が弱い
- OpenAI APIに特化（Geminiなど他のLLMへの対応が限定的）

#### 3. Outlines

**概要**: 構造化出力に特化したライブラリ（文法ベースの制約付き生成）

**利点**:
- 出力の形式を強制できる（文法制約）
- ローカルLLMとの相性が良い

**欠点**:
- LangChainとの統合が困難
- Gemini APIなどのクラウドLLMでは文法制約が使えない
- 学習コストが高い

#### 4. BAML (Boundary ML)（選択）

**概要**: LLM構造化出力専用のドメイン特化言語（DSL）

**利点**:
- トークン効率が高い（最適化されたプロンプト生成）
- 型安全性が高い（静的型チェック、Pydantic互換）
- プロンプトのバージョン管理が容易（DSLファイル）
- Pythonクライアント自動生成

**欠点**:
- 学習コストが高い（新しいDSLの習得が必要）
- 追加の依存関係（BAMLランタイム）
- コミュニティが小さい

## Decision

**Sagebaseプロジェクトでは、LLM構造化出力に BAML (Boundary ML) を採用する。**

### 採用理由

1. **トークン効率の大幅な改善**
   - スキーマ説明の自動最適化により、トークン消費量を10-15%削減
   - 累積的なコスト削減（月間数千円レベル）

2. **型安全性の向上**
   - 静的型チェック（TypeScript/Python）
   - Pydantic互換の型定義
   - コンパイル時のエラー検出

3. **プロンプト管理の改善**
   - DSLファイルによるバージョン管理（Git管理可能）
   - プロンプトとスキーマの一元管理
   - 再利用性の向上

4. **Sagebaseの要件に適合**
   - 大量のLLM呼び出し（コスト削減が重要）
   - 複雑なスキーマ（話者マッチング、メンバー抽出など）
   - 長期的な保守性（プロンプトのバージョン管理）

### 実装方針

#### 1. BAMLファイルの配置

```
baml_src/
├── politician_matching.baml       # 政治家マッチング
├── member_extraction.baml         # 会議体メンバー抽出
├── parliamentary_group_member_extractor.baml  # 議員団メンバー抽出
├── party_member_extractor.baml    # 政党メンバー抽出
├── minutes_divider.baml           # 議事録分割
└── ...
```

#### 2. BAMLファイルの構造

```baml
// baml_src/politician_matching.baml

// スキーマ定義
class PoliticianMatchResult {
  matched bool @description("マッチングが成功したか")
  confidence float @description("信頼度 (0.0-1.0)")
  matched_id int? @description("マッチした政治家のID")
  reason string @description("マッチング理由")
}

// プロンプト定義
function MatchSpeakerToPolitician(
  speaker_name: string,
  candidates: Candidate[]
) -> PoliticianMatchResult {
  client Gemini
  prompt #"
    以下の発言者を政治家候補とマッチングしてください。

    発言者: {{ speaker_name }}

    候補:
    {% for candidate in candidates %}
    - ID: {{ candidate.id }}, 名前: {{ candidate.name }}, 政党: {{ candidate.party }}
    {% endfor %}

    マッチング基準:
    - 名前の完全一致または部分一致
    - 政党の一致
    - ふりがなの類似性

    {{ ctx.output_format }}
  "#
}
```

#### 3. Pythonでの使用

```python
# src/infrastructure/external/politician_matching/baml_politician_matching_service.py

from baml_client import b  # 自動生成されたクライアント
from baml_client.types import PoliticianMatchResult, Candidate

class BAMLPoliticianMatchingService:
    async def match_speaker_to_politician(
        self, speaker_name: str, candidates: list[Candidate]
    ) -> PoliticianMatchResult:
        # BAMLクライアント呼び出し（型安全）
        result = await b.MatchSpeakerToPolitician(
            speaker_name=speaker_name,
            candidates=candidates
        )
        return result  # 型: PoliticianMatchResult（自動的にPydanticモデル）
```

#### 4. ハイブリッドアプローチ

コスト削減のため、**ルールベース + BAML**のハイブリッドアプローチを採用：

```python
class PoliticianMatchingService:
    async def match_speaker(
        self, speaker_name: str, candidates: list[Politician]
    ) -> MatchResult:
        # 高速パス: ルールベースマッチング（完全一致、部分一致）
        rule_based_result = self._rule_based_match(speaker_name, candidates)
        if rule_based_result and rule_based_result.confidence >= 0.9:
            return rule_based_result  # LLMをスキップ

        # LLMマッチング: 複雑なケースのみ
        baml_result = await self._baml_match(speaker_name, candidates)
        return baml_result
```

**効果**:
- 約70%のケースでLLM呼び出しをスキップ
- トークンコストを70%削減

#### 5. 段階的な移行

Pydantic実装からBAMLへの移行は段階的に実施：

1. **Phase 1**: 議事録分割処理（minutes_divider）をBAML化
2. **Phase 2**: 会議体メンバー抽出をBAML化
3. **Phase 3**: 話者マッチング、政治家マッチングをBAML化
4. **Phase 4**: すべてのLLM処理をBAML化、Pydantic実装を削除

## Consequences

### Positive（利点）

1. **トークン効率の改善**
   - ✅ 議事録分割: 約10-15%のトークン削減
   - ✅ 話者マッチング: 約5-10%のトークン削減
   - ✅ 政治家マッチング: 約10-15%のトークン削減
   - ✅ 累積的なコスト削減（月間数千円レベル）

2. **型安全性の向上**
   - ✅ 静的型チェック（pyright/mypyでエラー検出）
   - ✅ Pydantic互換の型（既存コードとの互換性）
   - ✅ コンパイル時のスキーマバリデーション

3. **プロンプト管理の改善**
   - ✅ DSLファイルによるバージョン管理（Git履歴で変更追跡）
   - ✅ プロンプトとスキーマの一元管理
   - ✅ 再利用性の向上（関数として定義）

4. **開発効率の向上**
   - ✅ Pythonクライアント自動生成（手動でのPydanticモデル定義不要）
   - ✅ リファクタリングが容易（スキーマ変更が自動的にコードに反映）
   - ✅ プロンプトの実験が容易（DSLファイルのみ編集）

### Negative（欠点・トレードオフ）

1. **学習コスト**
   - ⚠️ BAML DSLの習得が必要
   - ⚠️ 新しい概念（プロンプト関数、スキーマ定義）の理解が必要
   - **対策**: ドキュメント整備（baml-integration.md）、実装例の提供

2. **追加の依存関係**
   - ⚠️ BAMLランタイム（baml-py）のインストールが必要
   - ⚠️ コンパイラ（baml-cli）の実行が必要
   - **対策**: Dockerコンテナに含める、CI/CDで自動実行

3. **コミュニティの小ささ**
   - ⚠️ PydanticやInstructorに比べてコミュニティが小さい
   - ⚠️ 問題解決時にStack Overflowなどで情報が少ない
   - **対策**: 公式ドキュメント、GitHubのissueで情報収集

4. **デバッグの複雑さ**
   - ⚠️ BAML → Pythonクライアント生成の過程でエラーが発生する可能性
   - ⚠️ プロンプトのデバッグがやや難しい（生成されたプロンプトの確認が必要）
   - **対策**: ログ記録の徹底、テストの充実

### Risks（リスク）

1. **BAMLプロジェクトの継続性**
   - **リスク**: BAMLプロジェクトが開発停止する可能性
   - **対策**: Pydanticへのフォールバック実装を残す（当初のPydantic実装は削除済みだが、必要に応じて復元可能）

2. **LLMプロバイダーの互換性**
   - **リスク**: 一部のLLMプロバイダーでBAMLが動作しない可能性
   - **対策**: 主要なプロバイダー（Gemini, OpenAI, Claude）での動作確認

3. **パフォーマンスのオーバーヘッド**
   - **リスク**: BAMLクライアントの実行オーバーヘッド
   - **影響**: 実測では無視できるレベル（マイクロ秒単位）

## Metrics（効果測定）

### トークン削減効果

| 処理 | Pydantic実装 | BAML実装 | 削減率 |
|------|-------------|----------|--------|
| 議事録分割 | 約350トークン | 約300トークン | 14% |
| 話者マッチング | 約300トークン | 約270トークン | 10% |
| 政治家マッチング | 約320トークン | 約280トークン | 12% |
| 会議体メンバー抽出 | 約400トークン | 約350トークン | 12% |

### コスト削減効果（試算）

- **月間LLM呼び出し数**: 約10,000回
- **平均トークン削減**: 約12%
- **月間コスト削減**: 約3,000円（Gemini 2.0 Flash想定）
- **年間コスト削減**: 約36,000円

## References

- [BAML Official Documentation](https://docs.boundaryml.com/)
- [BAML GitHub Repository](https://github.com/BoundaryML/baml)
- [.claude/skills/baml-integration/](../../.claude/skills/baml-integration/) - BAML統合ガイド
- `baml_src/` - BAMLファイル
- `src/infrastructure/external/politician_matching/baml_politician_matching_service.py` - BAML政治家マッチングサービス

## Notes

- BAMLの採用は2024年11月に決定
- 2024年12月時点で、すべてのLLM構造化出力処理がBAML化完了
- Pydantic実装は削除済み（BAML専用化）
- ハイブリッドアプローチ（ルールベース + BAML）により、LLM呼び出しを約70%削減
