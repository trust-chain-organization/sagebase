// Speaker Matching for Sagebase
// 話者マッチング用のBAML定義

// ========================================
// Class Definitions (Pydanticモデルに対応)
// ========================================

// SpeakerMatch - 話者マッチング結果
class SpeakerMatch {
    matched bool @description("マッチングが成功したか")
    speaker_id int? @description("マッチした発言者のID（マッチしない場合はnull）")
    speaker_name string? @description("マッチした発言者の名前（マッチしない場合はnull）")
    confidence float @description("マッチングの信頼度（0.0-1.0）")
    reason string @description("マッチング判定の理由")
}

// ========================================
// Function Definitions
// ========================================

// Function: 話者マッチング
function MatchSpeaker(
    speaker_name: string,
    available_speakers: string
) -> SpeakerMatch {
    client Gemini2Flash
    prompt #"
        あなたは議事録の発言者名マッチング専門家です。
        議事録から抽出された発言者名と、既存の発言者リストから最も適切なマッチを見つけてください。

        # 抽出された発言者名
        {{ speaker_name }}

        # 既存の発言者リスト
        {{ available_speakers }}

        # マッチング基準
        1. 完全一致を最優先
        2. 括弧内の名前との一致（例: "委員長(平山たかお)" → "平山たかお"）
        3. 記号除去後の一致（例: "◆委員(下村あきら)" → "委員(下村あきら)"）
        4. 部分一致や音韻的類似性
        5. 漢字の異なる読みや表記ゆれ
        6. 会議体所属情報（★マーク）を重視（同じ会議体のメンバーを優先）

        # 出力要件
        - 確実性が低い場合は matched: false を返す
        - confidence は 0.8 以上の場合のみマッチとして扱う
        - 複数の候補がある場合は最も確からしいものを選ぶ
        - 会議体所属メンバー（★マーク付き）は信頼度を+0.1加算
        - マッチしない場合は speaker_id と speaker_name を null に設定

        # 重要
        信頼度が0.8未満の場合は、必ず matched: false を返してください。
    "#
}
