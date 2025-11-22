---
title: "主要機能紹介"
date: 2025-01-16
draft: false
description: "Sagebaseの4つの主要機能と技術的特徴を詳しくご紹介します"
---

# 主要機能紹介

Sagebase（セージベース）は、日本の政治活動を追跡・分析するための先進的なアプリケーションです。本ページでは、Sagebaseの主要な4つの機能と、それを支える技術的特徴をご紹介します。

---

## 📄 1. 議事録自動処理

### 概要

会議の議事録（PDFやテキスト）から発言を自動的に抽出・構造化し、データベースに保存します。手作業では膨大な時間がかかる議事録の処理を、効率的に自動化します。

### 価値提案

- **時間削減**: 数百ページの議事録を数分で処理
- **高精度**: LangGraphによる多段階処理で正確な発言抽出
- **スケーラビリティ**: 全国1,966自治体の議事録に対応可能

### 技術特徴

- **LangGraph**: 複雑なワークフローを状態機械として管理
- **Google Gemini API**: 最新のLLMで高精度なテキスト解析
- **Google Cloud Storage**: PDFファイルを安全に保管
- **非同期処理**: 大量の議事録を効率的に並列処理

### 処理フロー

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant CLI as CLI Command
    participant UseCase as ProcessMinutesUseCase
    participant Storage as IStorageService
    participant LLM as ILLMService
    participant DomainSvc as MinutesDomainService
    participant MeetingRepo as IMeetingRepository
    participant ConvRepo as IConversationRepository
    participant DB as Database

    User->>CLI: sagebase process-minutes --meeting-id 123
    activate CLI

    CLI->>UseCase: execute(meeting_id=123)
    activate UseCase

    %% Fetch PDF/Text from GCS
    UseCase->>MeetingRepo: get_meeting(123)
    activate MeetingRepo
    MeetingRepo->>DB: SELECT * FROM meetings WHERE id=123
    DB-->>MeetingRepo: meeting data (with gcs_text_uri)
    MeetingRepo-->>UseCase: Meeting entity
    deactivate MeetingRepo

    UseCase->>Storage: download_text(gcs_text_uri)
    activate Storage
    Storage-->>UseCase: raw text content
    deactivate Storage

    %% LLM Processing
    UseCase->>LLM: divide_into_speeches(raw_text)
    activate LLM
    Note over LLM: Uses Gemini API<br/>with prompt template
    LLM-->>UseCase: speeches_data (JSON)
    deactivate LLM

    %% Domain Logic
    UseCase->>DomainSvc: create_conversations(speeches_data, meeting_id)
    activate DomainSvc

    loop For each speech
        DomainSvc->>DomainSvc: validate speech data
        DomainSvc->>DomainSvc: create Conversation entity
    end

    DomainSvc-->>UseCase: List[Conversation]
    deactivate DomainSvc

    %% Save to Database
    UseCase->>ConvRepo: save_batch(conversations)
    activate ConvRepo

    loop For each conversation
        ConvRepo->>DB: INSERT INTO conversations
        DB-->>ConvRepo: saved
    end

    ConvRepo-->>UseCase: success
    deactivate ConvRepo

    %% Update meeting status
    UseCase->>MeetingRepo: update_processing_status(meeting_id, "completed")
    activate MeetingRepo
    MeetingRepo->>DB: UPDATE meetings SET status='completed'
    DB-->>MeetingRepo: updated
    MeetingRepo-->>UseCase: success
    deactivate MeetingRepo

    UseCase-->>CLI: ProcessingResult(success=True, conversations_count=50)
    deactivate UseCase

    CLI-->>User: ✓ Processed 50 conversations from meeting 123
    deactivate CLI
```

---

## 👥 2. 政治家データベース（全国1,966自治体対応）

### 概要

日本全国の政治家情報を網羅的に管理します。国会議員から都道府県議、市町村議まで、1,966すべての自治体をカバーします。

### 価値提案

- **網羅性**: 全国すべての自治体（国、47都道府県、1,918市町村）
- **最新性**: 政党ウェブサイトから自動的にデータを収集・更新
- **正確性**: 組織コードによる自治体の一意識別

### 技術特徴

- **Web Scraping**: Playwrightによる動的サイト対応
- **マスターデータ管理**: governing_bodiesテーブルで全自治体を管理
- **段階的処理**: 議員抽出→レビュー→承認のワークフロー
- **重複排除**: ドメインサービスによる政治家の自動重複検出

### データカバレッジ

- **国**: 1自治体（日本国政府）
- **都道府県**: 47自治体
- **市町村**: 1,918自治体（全市町村対応）
- **合計**: 1,966自治体

---

## 🤖 3. LLMベース発言者マッチング

### 概要

議事録中の発言者名を実際の政治家に自動的に紐付けます。従来の単純な文字列マッチングでは困難だった日本語特有の表記揺れに対応します。

### 価値提案

- **高精度マッチング**: LLMによる文脈理解で90%以上の精度
- **表記揺れ対応**: 敬称、漢字バリエーション、名前の順序などに対応
- **信頼性**: 信頼度スコアによる自動/手動判定の切り分け

### 技術特徴

- **ハイブリッドアプローチ**: ルールベース + LLMの組み合わせ
- **段階的マッチング**:
  1. 名前の正規化
  2. 候補者検索（名前・政党・期間）
  3. LLMによるファジーマッチング
  4. 信頼度評価
- **信頼度閾値**:
  - 高（≥0.9）: 自動リンク
  - 中（0.7-0.9）: 自動リンク + ログ記録
  - 低（0.5-0.7）: 手動レビュー
  - 極低（<0.5）: マッチなし

### マッチングフロー

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant CLI as CLI Command
    participant UseCase as MatchSpeakersUseCase
    participant MatchingSvc as SpeakerMatchingService
    participant DomainSvc as SpeakerDomainService
    participant LLM as ILLMService
    participant SpeakerRepo as ISpeakerRepository
    participant PoliticianRepo as IPoliticianRepository
    participant ConvRepo as IConversationRepository
    participant DB as Database

    User->>CLI: sagebase update-speakers --use-llm
    activate CLI

    CLI->>UseCase: execute(use_llm=True)
    activate UseCase

    %% Fetch unlinked conversations
    UseCase->>ConvRepo: get_unlinked_conversations()
    activate ConvRepo
    ConvRepo->>DB: SELECT * FROM conversations WHERE speaker_id IS NULL
    DB-->>ConvRepo: unlinked conversations
    ConvRepo-->>UseCase: List[Conversation]
    deactivate ConvRepo

    loop For each conversation
        UseCase->>DomainSvc: normalize_speaker_name(conversation.speaker_text)
        activate DomainSvc
        DomainSvc-->>UseCase: normalized_name
        deactivate DomainSvc

        %% Try to find existing speaker
        UseCase->>SpeakerRepo: find_by_name(normalized_name)
        activate SpeakerRepo
        SpeakerRepo->>DB: SELECT * FROM speakers WHERE name=?
        DB-->>SpeakerRepo: speaker or None
        SpeakerRepo-->>UseCase: Optional[Speaker]
        deactivate SpeakerRepo

        alt Speaker not found
            %% Create new speaker
            UseCase->>DomainSvc: create_speaker(normalized_name, conversation)
            activate DomainSvc
            DomainSvc->>DomainSvc: extract party name
            DomainSvc->>DomainSvc: extract position
            DomainSvc-->>UseCase: new Speaker entity
            deactivate DomainSvc

            UseCase->>SpeakerRepo: save(speaker)
            activate SpeakerRepo
            SpeakerRepo->>DB: INSERT INTO speakers
            DB-->>SpeakerRepo: speaker_id
            SpeakerRepo-->>UseCase: saved Speaker
            deactivate SpeakerRepo
        end

        %% Match speaker to politician (LLM-based)
        UseCase->>MatchingSvc: match_speaker_to_politician(speaker)
        activate MatchingSvc

        MatchingSvc->>PoliticianRepo: search_candidates(speaker.name, speaker.party)
        activate PoliticianRepo
        PoliticianRepo->>DB: SELECT * FROM politicians WHERE...
        DB-->>PoliticianRepo: candidate politicians
        PoliticianRepo-->>MatchingSvc: List[Politician]
        deactivate PoliticianRepo

        alt Has candidates
            MatchingSvc->>LLM: fuzzy_match(speaker, candidates)
            activate LLM
            Note over LLM: LLM determines<br/>best match with<br/>confidence score
            LLM-->>MatchingSvc: match_result (politician_id, confidence)
            deactivate LLM

            alt confidence >= 0.7
                MatchingSvc->>SpeakerRepo: link_to_politician(speaker_id, politician_id)
                activate SpeakerRepo
                SpeakerRepo->>DB: UPDATE speakers SET politician_id=?
                DB-->>SpeakerRepo: updated
                SpeakerRepo-->>MatchingSvc: success
                deactivate SpeakerRepo
            else confidence < 0.7
                Note over MatchingSvc: Low confidence<br/>requires manual review
            end
        end

        MatchingSvc-->>UseCase: matching result
        deactivate MatchingSvc

        %% Link conversation to speaker
        UseCase->>ConvRepo: update_speaker_link(conversation_id, speaker_id)
        activate ConvRepo
        ConvRepo->>DB: UPDATE conversations SET speaker_id=?
        DB-->>ConvRepo: updated
        ConvRepo-->>UseCase: success
        deactivate ConvRepo
    end

    UseCase-->>CLI: MatchingResult(linked=45, created_speakers=12, matched_politicians=8)
    deactivate UseCase

    CLI-->>User: ✓ Linked 45 conversations, created 12 speakers, matched 8 politicians
    deactivate CLI
```

### なぜLLMマッチングが必要か？

日本語の議事録には様々な表記揺れがあります：

- **敬称**: 山田太郎君、山田議員、山田太郎
- **順序**: 太郎山田 vs 山田太郎
- **漢字バリエーション**: 齊藤 vs 斉藤 vs 斎藤

従来の文字列マッチングではこれらの揺れに対応できませんが、LLMは文脈を理解して正確にマッチングできます。

---

## 📊 4. BIダッシュボード

### 概要

Plotly Dashを使用したインタラクティブなデータカバレッジ可視化ツールです。全国の自治体におけるデータ収集状況をリアルタイムで確認できます。

### 価値提案

- **視覚的理解**: 円グラフ、棒グラフ、テーブルで直感的に把握
- **リアルタイム更新**: 最新のデータベース情報を即座に反映
- **詳細分析**: 都道府県別、組織タイプ別のカバレッジ比較

### 主な機能

1. **全体カバレッジ率**: 円グラフでデータ取得状況を可視化
2. **組織タイプ別カバレッジ**: 国/都道府県/市町村別の棒グラフ
3. **都道府県別カバレッジ**: 上位10都道府県の詳細テーブル
4. **リアルタイム更新**: 更新ボタンでデータを再取得

### 技術スタック

- **Dash 2.14.2**: Plotlyのダッシュボードフレームワーク
- **Plotly 5.18.0**: インタラクティブグラフライブラリ
- **Pandas 2.1.4**: データ処理
- **SQLAlchemy 2.0.23**: ORMとデータベース接続

### アクセス方法

```bash
# Docker Composeで起動
docker compose -f docker/docker-compose.yml up -d bi-dashboard

# ブラウザでアクセス
# http://localhost:8050
```

---

## 🏗️ 技術的特徴

Sagebaseは、保守性と拡張性を重視した**Clean Architecture**に基づいて設計されています。

### Clean Architectureの4層構造

```mermaid
graph TB
    subgraph interfaces["🖥️ Interfaces Layer"]
        direction LR
        CLI["CLI Commands<br/>(src/interfaces/cli/)"]
        WEB["Streamlit UI<br/>(src/interfaces/web/)"]
    end

    subgraph application["⚙️ Application Layer"]
        direction LR
        UC["Use Cases (21)<br/>ProcessMinutesUseCase<br/>MatchSpeakersUseCase<br/>ScrapePoliticiansUseCase"]
        DTO["DTOs (16)<br/>Data Transfer Objects"]
    end

    subgraph domain["🎯 Domain Layer (Core)"]
        direction TB
        ENT["Entities (21)<br/>Politician, Speaker<br/>Meeting, Conference"]
        DS["Domain Services (18)<br/>SpeakerDomainService<br/>PoliticianDomainService"]
        RI["Repository Interfaces (22)<br/>BaseRepository<br/>ISessionAdapter"]
        SI["Service Interfaces (8)<br/>ILLMService<br/>IStorageService"]

        ENT --- DS
        DS --- RI
        DS --- SI
    end

    subgraph infrastructure["🔧 Infrastructure Layer"]
        direction TB
        PERSIST["Persistence (22+)<br/>BaseRepositoryImpl<br/>AsyncSessionAdapter"]
        EXT["External Services<br/>GeminiLLMService<br/>GCSStorageService<br/>WebScraperService"]
        SUPPORT["Support<br/>DI Container<br/>Logging, Monitoring"]

        PERSIST --- EXT
        EXT --- SUPPORT
    end

    %% Dependencies (arrows point FROM dependent TO dependency)
    CLI --> UC
    WEB --> UC
    UC --> DS
    UC --> RI
    UC --> SI

    PERSIST -.implements.-> RI
    EXT -.implements.-> SI

    %% Styling
    classDef interfaceStyle fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef applicationStyle fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef domainStyle fill:#f3e5f5,stroke:#4a148c,stroke-width:3px
    classDef infrastructureStyle fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px

    class interfaces interfaceStyle
    class application applicationStyle
    class domain domainStyle
    class infrastructure infrastructureStyle

    %% Notes
    note1["Note: Solid arrows = direct dependencies<br/>Dotted arrows = implements interface"]

    style note1 fill:#fff9c4,stroke:#f57f17,stroke-width:1px
```

### 主要な設計原則

1. **依存性逆転の原則**: 依存関係は内側（Domain層）に向かう
   - Interfaces → Application → Domain ← Infrastructure

2. **Domain層の独立性**: ビジネスロジックはフレームワークに依存しない
   - 純粋なPythonコードのみ
   - 外部サービスはインターフェースで抽象化

3. **テスタビリティ**: 各層を独立してテスト可能
   - Domain層は外部サービスなしでテスト
   - Infrastructure層は簡単に差し替え可能

### その他の技術的特徴

- **型安全性**: Python型ヒントとpyrightによる静的型チェック
- **コード品質**: Ruffによる自動フォーマットとリント
- **非同期処理**: async/awaitによる高パフォーマンス
- **コンテナ化**: Docker Composeによる一貫した開発環境
- **CI/CD**: GitHub Actionsによる自動テスト・デプロイ

---

## 💡 ユースケース

Sagebaseは、様々なユーザーに価値を提供します。

### 研究者向け

- **学術研究**: 政治家の発言パターンや投票行動の分析
- **データセット構築**: 構造化された議事録データのエクスポート
- **時系列分析**: 長期的な政治動向の追跡

### ジャーナリスト向け

- **ファクトチェック**: 政治家の過去の発言を迅速に検索
- **記事作成**: データに基づいた政治報道の作成
- **透明性の向上**: 政治活動の可視化と公開

### 市民向け

- **情報アクセス**: 地元議員の活動を簡単に確認
- **政治参加**: データに基づいた投票判断
- **監視**: 政治家の公約と実際の行動の比較

---

## まとめ

Sagebaseは、最新のLLM技術とクリーンアーキテクチャを組み合わせることで、政治活動の透明性向上に貢献します。全国1,966自治体をカバーする包括的なデータベースと、高精度な自動処理機能により、研究者・ジャーナリスト・市民すべてに価値を提供します。

### さらに詳しく

- [Sagebaseについて](/about)
- [GitHubリポジトリ](https://github.com/trust-chain-organization/sagebase)
- [お問い合わせ](/contact)
