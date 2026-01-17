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

        【重要】以下の視覚的な区切り線はセクションの境界として扱わないでください:
        - ～～～～～～（波線）
        - ──────（ダッシュ）
        - ━━━━━━（罫線）
        - ========（イコール）
        - --------（ハイフン）
        これらは議事録のフォーマット上の装飾であり、発言の区切りではありません。
        発言者の変更（○議長、◆議員、◎委員長など）や議題の変更を境界として使用してください。

        注意:
        - キーワードは議事録内に実際に存在する文字列である必要があります
        - キーワードは先頭から正確に30文字抽出してください（30文字未満の場合は全文）
        - 区切り線のみで構成されるセクションは作成しないでください

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

        議事録の一般的なフォーマット:
        - ○議長（名前）発言内容
        - ◆議員（名前）発言内容
        - ○委員長（名前）発言内容
        - ◎市長（名前）発言内容
        - ◎副市長（名前）発言内容
        - ◎部長（名前）発言内容
        ※ ○、◆、◎、●などの記号で発言者が示されます

        【重要】以下は発言として抽出しないでください:
        - 発言者を特定できないテキスト（「不明」として出力しないこと）
        - 括弧で囲まれた文書要素: （イメージ）、（表）、（図）、（資料）、（請願文書表）など
        - 議事進行の説明文やト書き
        - 議題名や文書タイトルのみのセクション

        【発言者として認められるもの】:
        - 人名（姓名、または姓のみ）
        - 役職名（議長、委員長、大臣など）
        - 役職名（人名）の形式

        注意:
        - 発言者が明確に特定できる発言のみを抽出してください
        - 発言内容は元のテキストから正確に抽出してください
        - 発言者を特定できない場合は、その部分はスキップしてください

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

// Function 5: 発言者名を正規化して人名を抽出
class NormalizedSpeaker {
    original_speaker string @description("元の発言者名")
    normalized_name string @description("正規化された人名（役職を除いた人名）")
    is_valid bool @description("有効な人名かどうか（役職のみでマッピングもない場合はfalse）")
    extraction_method string @description("抽出方法: pattern（括弧内から抽出）, mapping（マッピングから取得）, as_is（そのまま使用）, skipped（スキップ）")
}

function NormalizeSpeakerNames(
    speakers: string[],
    role_name_mappings: map<string, string>?
) -> NormalizedSpeaker[] {
    client Gemini2Flash
    prompt #"
        以下の発言者名リストを正規化し、人名のみを抽出してください。
        **重要: 入力リストの各要素に対して、必ず1つのNormalizedSpeakerオブジェクトを返してください。**

        発言者名リスト:
        {{ speakers }}

        役職-人名マッピング（提供されている場合）:
        {{ role_name_mappings }}

        【処理ルール】優先順位順に適用してください:

        1. **括弧内の人名抽出**（最優先）
           - 「役職（人名）」または「役職(人名)」形式の場合、括弧内の人名のみを抽出
           - 例: "市長（松井一郎）" → "松井一郎"
           - 例: "○議長（西村義直君）" → "西村義直"（敬称も除去）
           - 例: "委員長（山田太郎議員）" → "山田太郎"
           - extraction_method: "pattern"

        2. **役職のみの場合はマッピング参照**
           - 役職名のみ（議長、市長、委員長など）でマッピングがある場合は人名を取得
           - 例: "市長" + マッピング{"市長": "松井一郎"} → "松井一郎"
           - extraction_method: "mapping"

        3. **役職のみでマッピングなしはスキップ**
           - 役職名のみでマッピングがない場合は無効としてマーク
           - 例: "市長"（マッピングなし）→ is_valid: false
           - extraction_method: "skipped"

        4. **人名のみはそのまま使用**
           - 人名と判断できる場合はそのまま使用
           - 例: "西村義直" → "西村義直"
           - extraction_method: "as_is"

        【役職として扱うキーワード】:
        議長、副議長、委員長、副委員長、会長、副会長、理事、幹事、書記、議員、
        市長、副市長、町長、副町長、村長、副村長、区長、副区長、知事、副知事、
        部長、局長、課長、事務局長、事務局次長、
        参考人、証人、説明員、政府参考人、大臣、副大臣、政務官

        【敬称として除去するもの】:
        君、氏、議員、委員、参考人、証人、説明員、さん、様、先生

        【注意】:
        - 記号（○◆◇■□●）は無視してください
        - 全角括弧（）と半角括弧()の両方に対応してください
        - 空の発言者名はis_valid: falseとしてください

        【出力形式の例】入力: ["議長(西村義直)", "市長", "田中太郎"]、マッピング: {"市長": "松井一郎"}
        出力:
        [
          {"original_speaker": "議長(西村義直)", "normalized_name": "西村義直", "is_valid": true, "extraction_method": "pattern"},
          {"original_speaker": "市長", "normalized_name": "松井一郎", "is_valid": true, "extraction_method": "mapping"},
          {"original_speaker": "田中太郎", "normalized_name": "田中太郎", "is_valid": true, "extraction_method": "as_is"}
        ]

        {{ ctx.output_format }}
    "#
}

// Function 6: 長いセクションを再分割
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
