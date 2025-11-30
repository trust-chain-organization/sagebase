// Parliamentary Group Member Extraction for Sagebase
// 議員団メンバー抽出用のBAML定義

// 抽出された議員団メンバー情報の型定義
class ParliamentaryGroupMember {
    name string @description("議員名（フルネーム）")
    role string? @description("役職（団長、幹事長、政調会長など）")
    party_name string? @description("所属政党名")
    district string? @description("選挙区")
    additional_info string? @description("その他の情報")
}

// 議員団メンバー抽出関数
function ExtractParliamentaryGroupMembers(
    html: string,
    text_content: string
) -> ParliamentaryGroupMember[] {
    client Gemini2Flash
    prompt #"
        以下のWebページから議員団に所属する議員の情報を抽出してください。

        各議員について以下の情報を抽出:
        1. 議員の氏名（必須、フルネーム）
        2. 議員団内での役職（団長、幹事長、政調会長など）
        3. 所属政党名（議員団名とは異なる場合のみ）
        4. 選挙区
        5. その他の重要な情報

        注意事項:
        - 議員団（会派）のメンバー一覧を抽出してください
        - 役職者だけでなく、一般のメンバーも含めて全員を抽出してください
        - 名前の表記は元のページの表記を維持してください
        - 敬称（議員、氏、さん、様、先生など）は除外してください
        - 議員団名と政党名は異なる場合があります（例：「○○会派」と「△△党」）
        - 役職がない場合はnullとしてください
        - 所属政党が明記されていない場合はnullとしてください

        テキストコンテンツ:
        {{ text_content }}

        HTMLコンテンツ（構造の参考用）:
        {{ html }}

        上記の情報から、議員団メンバー全員の情報を抽出してください。
    "#
}
