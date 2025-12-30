// Speaker Matching Tools - BAML Definitions
// LangGraph ReActエージェント用のツール定義

// ===================================================================
// judge_confidence: マッチング候補の確信度を総合判定
// ===================================================================

function JudgeMatchingConfidence(
  speaker_name: string,
  candidate_json: string,
  additional_info_json: string?
) -> ConfidenceJudgement {
  client Gemini2Flash
  prompt #"
    あなたは発言者と政治家の名寄せを専門とするエキスパートです。
    発言者と政治家候補のマッチングの確信度を総合的に判定してください。

    ## 入力情報

    **発言者名**: {{ speaker_name }}

    **候補政治家** (JSON):
    {{ candidate_json }}

    {% if additional_info_json %}
    **追加情報** (JSON):
    {{ additional_info_json }}
    {% endif %}

    ## 判定基準

    以下の要素を総合的に評価してください：

    1. **名前の一致度** (重要度: 最高)
       - 完全一致（EXACT）: 非常に高い確信度
       - 部分一致（PARTIAL）: 高い確信度
       - 類似（FUZZY）: 中程度の確信度

    2. **所属情報の一致** (重要度: 高)
       - 会議体所属（is_affiliated: true）: 確信度を大きく向上
       - 所属履歴（affiliation）あり: 確信度を向上

    3. **政党情報の一致** (重要度: 中)
       - 政党情報が一致: 確信度を向上

    4. **文脈的整合性** (重要度: 中)
       - 名前の意味的類似性
       - 活動時期の整合性

    ## 出力要件

    **必須フィールド（すべて出力してください）:**

    1. **confidence**: 0.0〜1.0の数値
       - 例: 0.95

    2. **confidence_level**: 確信度レベル（必ず以下のいずれか）
       - "HIGH": 確信度0.9以上
       - "MEDIUM": 確信度0.7〜0.9
       - "LOW": 確信度0.7未満

    3. **should_match**: マッチ推奨（boolean）
       - true: 確信度0.8以上
       - false: 確信度0.8未満

    4. **reason**: 判定理由（日本語で明確に）

    5. **contributing_factors**: 確信度に影響した要素（配列）
       各要素には以下を含める:
       - factor: 要素名（例: "base_score", "affiliation", "party"）
       - impact: 影響度（-1.0〜1.0の数値）
       - description: 日本語の説明

    6. **recommendation**: 推奨アクション（日本語で）

    **重要**: 上記のすべてのフィールドを必ず出力してください。
    特に `confidence_level` フィールドは必須です。
  "#
}

// ===================================================================
// Data Classes
// ===================================================================

class ConfidenceJudgement {
  confidence float @description("確信度 (0.0-1.0)")
  confidence_level string @description("確信度レベル (HIGH/MEDIUM/LOW)")
  should_match bool @description("マッチすべきかどうか (confidence >= 0.8)")
  reason string @description("判定理由の説明")
  contributing_factors ContributingFactor[] @description("確信度に寄与した要素")
  recommendation string @description("推奨アクション")
}

class ContributingFactor {
  factor string @description("要素名 (例: base_score, affiliation, party)")
  impact float @description("スコアへの影響 (-1.0 to 1.0)")
  description string @description("説明")
}
