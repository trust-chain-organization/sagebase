// Conference Member Extraction for Sagebase
// 会議体メンバー抽出用のBAML定義

// 抽出されたメンバー情報の型定義
class ExtractedMember {
    name string @description("議員名（フルネーム）")
    role string? @description("役職（議長、副議長、委員長、委員など）")
    party_name string? @description("所属政党名")
    additional_info string? @description("その他の情報")
}

// メンバー抽出関数
function ExtractMembers(
    html: string,
    conference_name: string
) -> ExtractedMember[] {
    client Gemini2Flash
    prompt #"
        以下のHTMLから{{ conference_name }}の議員メンバー情報を抽出してください。

        重要: このページに複数の委員会や議会の情報が含まれている場合、
        必ず「{{ conference_name }}」に所属する議員のみを抽出してください。
        他の委員会や議会のメンバーは抽出しないでください。

        HTMLコンテンツ:
        {{ html }}

        抽出する情報:
        1. 議員名（フルネーム）
        2. 役職（議長、副議長、委員長、副委員長、委員など）
        3. 所属政党名（わかる場合）
        4. その他の重要な情報

        注意事項:
        - 議員名は姓名を正確に抽出してください
        - 敬称（議員、氏、さん、様、先生など）は除外してください
        - 役職がない場合は「委員」としてください
        - 所属政党が明記されていない場合はnullとしてください
        - 複数の役職がある場合は主要な役職を選択してください
        - 必ず指定された「{{ conference_name }}」に関連する議員のみを抽出し、
          他の委員会や議会のメンバーは含めないでください

        **重要: 必ず以下の英語フィールド名でJSONを返してください:**
        - name: 議員名
        - role: 役職
        - party_name: 所属政党名
        - additional_info: その他の情報
    "#
}
