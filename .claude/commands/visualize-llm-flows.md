# LLM処理フロー可視化コマンド

プロジェクト内のLangGraphおよびBAMLで定義されたLLM処理をマーメイド形式で可視化します。

## 実行手順

以下のLLM処理フローをマーメイド形式で `tmp/llm-flows.md` ファイルに出力してください：

### 1. LangGraph処理

#### 1.1 政党スクレイピングエージェント（拡張版）
- ファイル: `src/infrastructure/external/langgraph_party_scraping_agent_with_classification.py`
- 処理フロー:
  - START → initialize → pop_next_url
  - pop_next_url → (current_url判定) → classify_page または END
  - classify_page → (ページ種別判定) → explore_children / extract_members / continue / END
  - explore_children → pop_next_url (ループ)
  - extract_members → pop_next_url (ループ)
- ノード説明:
  - initialize: 状態初期化（visited_urls, pending_urls等）
  - pop_next_url: pending_urlsから次のURLをポップして処理
  - classify_page: ページ種別を分類（index_page, member_list_page, other）
  - explore_children: 子リンクを解析してpending_urlsに追加
  - extract_members: メンバー情報を抽出

#### 1.2 議事録処理エージェント
- ファイル: `src/minutes_divide_processor/minutes_process_agent.py`
- 処理フロー:
  - process_minutes → divide_minutes_to_keyword → divide_minutes_to_string → check_length → divide_speech
  - divide_speech → (インデックス判定) → divide_speech (ループ) または END
- ノード説明:
  - process_minutes: 議事録の前処理と出席者部分の分離
  - divide_minutes_to_keyword: 議事録をセクションに分割してキーワードリスト作成
  - divide_minutes_to_string: セクション情報を基に実際の文字列を分割
  - check_length: セクションの長さをチェックして必要に応じて再分割
  - divide_speech: 各セクションを発言者と発言内容に分割（全セクションをループ処理）

### 2. BAML処理

#### 2.1 会議体メンバー抽出
- ファイル: `baml_src/member_extraction.baml`
- 処理:
  - ExtractMembers(html, conference_name) → ExtractedMember[]
  - クライアント: Gemini2Flash
  - 出力: 議員名、役職、所属政党、その他情報

#### 2.2 議事録分割処理
- ファイル: `baml_src/minutes_divider.baml`
- 処理群:
  1. DivideMinutesToKeywords(minutes) → SectionInfo[]
     - 議事録をセクションに分割してキーワードリスト作成
  2. DetectBoundary(minutes_text) → MinutesBoundary
     - 出席者情報と発言部分の境界を検出
  3. ExtractAttendees(attendees_text) → AttendeesMapping
     - 出席者情報から役職と人名のマッピングを抽出
  4. DivideSpeech(section_string) → SpeakerAndSpeechContent[]
     - セクションを発言者と発言内容に分割
  5. RedivideSection(section_text, divide_counter, original_index) → SectionInfo[]
     - 長いセクションを再分割
- クライアント: Gemini2Flash

#### 2.3 議員団メンバー抽出
- ファイル: `baml_src/parliamentary_group_member_extractor.baml`
- 処理:
  - ExtractParliamentaryGroupMembers(html, text_content) → ParliamentaryGroupMember[]
  - クライアント: Gemini2Flash
  - 出力: 議員名、役職、所属政党、選挙区、その他情報

## 出力フォーマット

マーメイドの `graph TD` または `flowchart TD` 形式で作成してください。

各処理について以下の形式で出力：

```markdown
## [処理名]

### 概要
[処理の概要説明]

### フロー図
```mermaid
graph TD
    [ノード定義とエッジ]
```

### ノード説明
- **ノード名**: 説明
```

LangGraph処理は分岐やループを含む複雑なフローとして表現し、BAML処理は関数呼び出しとして表現してください。

出力先: `tmp/llm-flows.md`
