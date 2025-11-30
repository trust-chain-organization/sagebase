// Minutes Divider for Sagebase
// 議事録分割処理用のBAML定義

// ========================================
// Class Definitions (Pydanticモデルに対応)
// ========================================

// 1. SectionInfo - 分割されたセクションの情報
class SectionInfo {
    chapter_number int @description("分割した文字列を前から順に割り振った番号")
    keyword string @description("分割した文字列の先頭30文字をそのまま抽出した文字列")
}

// 2. SectionString - 分割されたセクションの文字列
class SectionString {
    chapter_number int @description("分割した文字列を前から順に割り振った番号")
    sub_chapter_number int @description("再分割した場合の文字列番号")
    section_string string @description("分割した文字列")
}

// 3. RedividedSectionInfo - 再分割されたセクションの情報
class RedividedSectionInfo {
    chapter_number int @description("再分割前の順番を表す番号")
    sub_chapter_number int @description("再分割した中での順番を表す番号")
    keyword string @description("分割した文字列の先頭30文字をそのまま抽出した文字列")
}

// 4. SpeakerAndSpeechContent - 発言者と発言内容
class SpeakerAndSpeechContent {
    speaker string @description("発言者")
    speech_content string @description("発言内容")
    chapter_number int @description("分割した文字列を前から順に割り振った番号")
    sub_chapter_number int @description("再分割した場合の文字列番号")
    speech_order int @description("発言順")
}

// 5. MinutesBoundary - 議事録の境界検出結果
class MinutesBoundary {
    boundary_found bool @description("境界が見つかったかどうか")
    boundary_text string? @description("境界前後の文字列（｜境界｜でマーク）")
    boundary_type string @description("境界の種類: separator_line, speech_start, time_marker, none")
    confidence float @description("境界検出の信頼度（0.0-1.0）")
    reason string @description("境界判定の理由")
}

// 6. AttendeesMapping - 出席者の役職と名前のマッピング
class AttendeesMapping {
    attendees_mapping map<string, string?>? @description("役職から人名へのマッピング（使用しない場合はnull）")
    regular_attendees string[] @description("出席者の人名リスト")
    confidence float @description("抽出の信頼度（0.0-1.0）")
}

// ========================================
// Function Definitions
// ========================================

// Function 1: 議事録を章に分割してキーワードリストを返す
function DivideMinutesToKeywords(minutes: string) -> SectionInfo[] {
    client Gemini2Flash
    prompt #"
        以下の議事録を意味のあるセクション（章）に分割して、各セクションの先頭キーワードを抽出してください。

        議事録:
        {{ minutes }}

        指示:
        1. 議事録を意味のある単位で分割してください（発言者の変更、議題の変更など）
        2. 各セクションの先頭30文字をキーワードとして抽出してください
        3. chapter_numberは1から順番に割り振ってください
        4. キーワードは元の文字列から正確に抽出してください（改変しない）
        5. できるだけ多くのセクションに分割してください（目安: 5-30セクション）

        注意:
        - キーワードは議事録内に実際に存在する文字列である必要があります
        - キーワードは先頭から正確に30文字抽出してください（30文字未満の場合は全文）

        出力形式（JSON配列）:
        [
          {
            "chapter_number": 1,
            "keyword": "先頭30文字のキーワード"
          },
          {
            "chapter_number": 2,
            "keyword": "次のセクションの先頭30文字"
          }
        ]

        重要: "keyword"フィールドを使用してください（"keywords"ではありません）
    "#
}

// Function 2: 出席者情報と発言部分の境界を検出
function DetectBoundary(minutes_text: string) -> MinutesBoundary {
    client Gemini2Flash
    prompt #"
        以下の議事録テキストから、出席者情報と発言部分の境界を検出してください。

        議事録テキスト:
        {{ minutes_text }}

        指示:
        1. 出席者リストや役員名簿と、実際の発言内容の境界を見つけてください
        2. 境界が見つかった場合、boundary_foundをtrueにしてください
        3. boundary_textには境界前後のテキストを「｜境界｜」でマークして返してください
           - 境界の前20文字 + ｜境界｜ + 境界の後20文字 の形式
        4. boundary_typeは以下のいずれか:
           - separator_line: 区切り線（---、===など）で区切られている
           - speech_start: 発言開始パターン（○、◆など）で区切られている
           - time_marker: 時刻表記で区切られている
           - none: 境界が見つからない
        5. confidenceは境界検出の確信度（0.0-1.0）
        6. reasonには判定理由を簡潔に説明してください

        境界が見つからない場合:
        - boundary_found=false
        - boundary_text=null
        - boundary_type="none"
        - confidence=0.0
    "#
}

// Function 3: 出席者情報を抽出
function ExtractAttendees(attendees_text: string) -> AttendeesMapping {
    client Gemini2Flash
    prompt #"
        以下の出席者情報テキストから、役職と人名のマッピングを抽出してください。

        出席者情報:
        {{ attendees_text }}

        指示:
        1. 役職と人名の対応関係を抽出してください（例: "議長" -> "山田太郎"）
        2. regular_attendeesには全ての出席者の名前をリストで返してください
        3. 敬称（議員、氏、さん、様、先生など）は除外してください
        4. confidenceは抽出の確信度（0.0-1.0）
        5. attendees_mappingは役職が明確な場合のみ設定し、不明な場合はnullとしてください

        注意:
        - 人名は姓名を正確に抽出してください
        - 同じ人物が複数回出現する場合は重複を除いてください
    "#
}

// Function 4: 発言者と発言内容に分割
function DivideSpeech(section_string: string) -> SpeakerAndSpeechContent[] {
    client Gemini2Flash
    prompt #"
        以下のセクションテキストから、発言者と発言内容を抽出してください。

        セクション内容:
        {{ section_string }}

        指示:
        1. 各発言を発言者と発言内容に分割してください
        2. 発言者名は正確に抽出してください（敬称を除く）
        3. speech_orderは1から順番に割り振ってください
        4. chapter_numberとsub_chapter_numberは1に設定してください（後で更新されます）
        5. 発言内容は発言者の発言部分のみを含めてください

        国会議事録の一般的なフォーマット:
        - ○議長（名前）発言内容
        - ◆議員（名前）発言内容
        - ○委員長（名前）発言内容

        注意:
        - 発言者が明示されていない場合でも、文脈から推測して抽出してください
        - 発言内容は元のテキストから正確に抽出してください

        出力形式（JSON配列）:
        [
          {
            "speaker": "発言者名（敬称なし）",
            "speech_content": "発言内容",
            "chapter_number": 1,
            "sub_chapter_number": 1,
            "speech_order": 1
          },
          {
            "speaker": "次の発言者名",
            "speech_content": "次の発言内容",
            "chapter_number": 1,
            "sub_chapter_number": 1,
            "speech_order": 2
          }
        ]

        重要: "speech_content"フィールドを使用してください（"utterance", "speech"ではありません）
    "#
}

// Function 5: 長いセクションを再分割
function RedivideSection(section_text: string, divide_counter: int, original_index: int) -> SectionInfo[] {
    client Gemini2Flash
    prompt #"
        以下のセクションを{{ divide_counter }}個に再分割してください。

        元のインデックス: {{ original_index }}

        セクション内容:
        {{ section_text }}

        指示:
        1. セクションを{{ divide_counter }}個の意味のある単位に分割してください
        2. 各セクションの先頭30文字をキーワードとして抽出してください
        3. chapter_numberは1から順番に割り振ってください
        4. キーワードは元の文字列から正確に抽出してください（改変しない）

        注意:
        - 意味のある区切りで分割してください（発言者の変更、議題の変更など）
        - キーワードは議事録内に実際に存在する文字列である必要があります
    "#
}
