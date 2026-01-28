// Proposal Parliamentary Group Judge Extraction for Sagebase
// 議案への会派賛否情報抽出用のBAML定義

// ========================================
// Enum Definitions
// ========================================

// 賛否判断の種類
enum JudgmentType {
  FOR @description("賛成")
  AGAINST @description("反対")
  ABSTAIN @description("棄権")
  ABSENT @description("欠席")
}

// ========================================
// Class Definitions
// ========================================

// 会派賛否抽出結果
class ParliamentaryGroupJudgeExtraction {
  group_name string @description("会派名（抽出された生の文字列）")
  judgment JudgmentType @description("賛否")
  member_count int? @description("人数（判明している場合）")
  note string? @description("備考")
}

// ========================================
// Function Definitions
// ========================================

// 会派賛否情報抽出関数
function ExtractParliamentaryGroupJudges(
  html: string
) -> ParliamentaryGroupJudgeExtraction[] {
  client Gemini2Flash
  prompt #"
    以下のHTMLから議案に対する会派（議員団・会派・政党グループ）単位の賛否情報を抽出してください。

    # 入力HTML
    {{ html }}

    # 抽出する情報
    各会派について以下の情報を抽出:
    1. 会派名（必須）: 会派・議員団・政党グループの名称
    2. 賛否（必須）: FOR（賛成）/ AGAINST（反対）/ ABSTAIN（棄権）/ ABSENT（欠席）
    3. 人数（任意）: その判断をした会派メンバーの人数（記載がある場合のみ）
    4. 備考（任意）: 自由投票など特記事項

    # 注意事項
    - 会派名は元のページの表記を維持してください（表記揺れはそのまま抽出）
    - 「賛成」「可」などは FOR に分類
    - 「反対」「否」などは AGAINST に分類
    - 「棄権」は ABSTAIN に分類
    - 「欠席」「不在」は ABSENT に分類
    - 人数が記載されていない場合は null としてください
    - 議案の賛否情報が見つからない場合は空の配列を返してください
    - 個人単位の賛否ではなく、会派単位の賛否のみを抽出してください

    # 出力形式
    **重要: 必ず以下の英語フィールド名でJSONを返してください:**
    - group_name: 会派名
    - judgment: 賛否（FOR / AGAINST / ABSTAIN / ABSENT）
    - member_count: 人数（nullの場合は省略可）
    - note: 備考（nullの場合は省略可）

    {{ ctx.output_format }}
  "#
}
