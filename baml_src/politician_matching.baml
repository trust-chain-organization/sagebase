// Politician Matching for Sagebase
// 政治家マッチング用のBAML定義

// ========================================
// Class Definitions (Pydanticモデルに対応)
// ========================================

// PoliticianMatch - 政治家マッチング結果
class PoliticianMatch {
    matched bool @description("マッチングが成功したか")
    politician_id int? @description("マッチした政治家のID（マッチしない場合はnull）")
    politician_name string? @description("マッチした政治家の名前（マッチしない場合はnull）")
    political_party_name string? @description("所属政党名（マッチしない場合はnull）")
    confidence float @description("マッチングの信頼度（0.0-1.0）")
    reason string @description("マッチング判定の理由")
}

// ========================================
// Function Definitions
// ========================================

// Function: 政治家マッチング
function MatchPolitician(
    speaker_name: string,
    speaker_type: string,
    speaker_party: string,
    available_politicians: string
) -> PoliticianMatch {
    client Gemini2Flash
    prompt #"
        あなたは発言者と政治家のマッチング専門家です。
        発言者情報と既存の政治家リストから最も適切なマッチを見つけてください。

        # 発言者情報
        名前: {{ speaker_name }}
        種別: {{ speaker_type }}
        所属政党: {{ speaker_party }}

        # 候補となる政治家リスト
        {{ available_politicians }}

        # マッチング基準
        1. 氏名の完全一致を最優先
        2. 所属政党が一致する場合は信頼度を上げる
        3. 表記ゆれを考慮（例: "斉藤" と "齊藤"）
        4. 同姓同名の場合は政党や役職で判断
        5. 部分一致や音韻的類似性

        # 信頼度の基準
        - 0.9以上: 氏名と政党が完全一致
        - 0.7-0.9: 氏名は一致するが政党が不明または部分一致
        - 0.5-0.7: 氏名に表記ゆれがあるが政党は一致
        - 0.5未満: マッチング不可（matched: false）

        # 出力要件
        - 確実性が低い場合は matched: false を返す
        - confidence は 0.7 以上の場合のみマッチとして扱う
        - マッチしない場合は politician_id, politician_name, political_party_name を null に設定

        # 重要
        信頼度が0.7未満の場合は、必ず matched: false を返してください。
    "#
}
