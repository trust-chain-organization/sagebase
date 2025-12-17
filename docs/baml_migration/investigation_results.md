# その他LLM処理のBAML化調査結果

## 調査概要

- **調査日**: 2025-12-17
- **調査者**: Claude Code
- **目的**: プロジェクト内の全LLM使用箇所を調査し、BAML化の優先度を決定する

## エグゼクティブサマリー

プロジェクト内のLLM使用箇所を調査した結果、以下が判明しました：

- **既にBAML化済み**: 4処理（会議体メンバー抽出、議事録分割、議員団メンバー抽出、政党メンバー抽出）
- **BAML化候補**: 4処理（リンク分類、ページ分類、話者マッチング、政治家マッチング）
- **推奨される次のPBI**: リンク分類とページ分類のBAML化（High優先度）

---

## 1. LLM使用箇所一覧

### 1.1 既にBAML化されている処理

| 処理名 | BAMLファイル | 関数名 | 実装状態 |
|--------|-------------|--------|---------|
| 会議体メンバー抽出 | `baml_src/member_extraction.baml` | `ExtractMembers` | ✅ 完了 |
| 議事録分割 | `baml_src/minutes_divider.baml` | `DivideMinutesToKeywords`等 | ✅ 完了 |
| 議員団メンバー抽出 | `baml_src/parliamentary_group_member_extractor.baml` | `ExtractParliamentaryGroupMembers` | ✅ 完了 |
| 政党メンバー抽出 | `baml_src/party_member_extractor.baml` | `ExtractPartyMembers` | ✅ 完了 |

### 1.2 BAML化されていない処理（候補）

| 処理名 | ファイルパス | 出力モデル | 実装方式 |
|--------|------------|-----------|---------|
| リンク分類 | `src/infrastructure/external/llm_link_classifier_service.py` | `LinkClassification` | 手動JSONパース |
| ページ分類 | `src/infrastructure/external/llm_page_classifier_service.py` | `PageClassification` | 手動JSONパース |
| 話者マッチング | `src/domain/services/speaker_matching_service.py` | `SpeakerMatch` | `get_structured_llm()` |
| 政治家マッチング | `src/domain/services/politician_matching_service.py` | `PoliticianMatch` | `get_prompt()` |

---

## 2. 各処理の詳細分析

### 2.1 リンク分類（LLMLinkClassifierService）

**ファイル**: `src/infrastructure/external/llm_link_classifier_service.py`

#### 現在の実装

- **プロンプト**: `classify_page_links`
- **出力モデル**: `LinkClassification`, `LinkClassificationResult`
- **実装方式**: 手動JSONパース（`json.loads`でパース、エラーハンドリングあり）
- **問題点**:
  - JSONパースが複雑（コードブロック除去、エラーハンドリング）
  - パース失敗時のフォールバック処理が必要
  - 型安全性が低い

#### トークン使用量推定

- **入力**: リンク情報（URL、テキスト、タイトル）× 複数
- **推定トークン数**: 500-2000トークン/リクエスト
- **呼び出し頻度**: 政党ページ解析時（中頻度）

#### BAML化のメリット

- ✅ 型安全性の向上
- ✅ JSONパース処理の削減（100行以上のコード削減）
- ✅ エラーハンドリングの簡素化
- ✅ トークン使用量の最適化（20-30%削減見込み）

#### 実装難易度

- **難易度**: Medium
- **必要な作業**:
  1. BAMLファイル作成（`link_classifier.baml`）
  2. `LinkClassification`モデルをBAMLクラスに変換
  3. `LLMLinkClassifierService`の実装をBAML呼び出しに置き換え
  4. テストの更新

#### BAML化優先度

**優先度: High**

- 理由:
  - 手動JSONパースが複雑
  - エラーハンドリングの改善が必要
  - トークン削減効果が高い
  - 実装が比較的単純

---

### 2.2 ページ分類（LLMPageClassifierService）

**ファイル**: `src/infrastructure/external/llm_page_classifier_service.py`

#### 現在の実装

- **プロンプト**: `classify_page_type`
- **出力モデル**: `PageClassification`
- **実装方式**: 手動JSONパース（`json.loads`でパース）
- **問題点**:
  - リンク分類と同様の問題点
  - HTMLエクセプトの切り取り処理が必要

#### トークン使用量推定

- **入力**: HTML抜粋（最大`MAX_HTML_EXCERPT_LENGTH`）、URL、コンテキスト
- **推定トークン数**: 1000-3000トークン/リクエスト
- **呼び出し頻度**: 階層的スクレイピング時（中頻度）

#### BAML化のメリット

- ✅ 型安全性の向上
- ✅ JSONパース処理の削減（70行以上のコード削減）
- ✅ エラーハンドリングの簡素化
- ✅ トークン使用量の最適化（15-25%削減見込み）

#### 実装難易度

- **難易度**: Medium
- **必要な作業**:
  1. BAMLファイル作成（`page_classifier.baml`）
  2. `PageClassification`モデルをBAMLクラスに変換
  3. `LLMPageClassifierService`の実装をBAML呼び出しに置き換え
  4. テストの更新

#### BAML化優先度

**優先度: High**

- 理由:
  - リンク分類と同様の問題点
  - トークン削減効果が高い
  - 実装が比較的単純
  - リンク分類と同時に実装することで効率化

---

### 2.3 話者マッチング（SpeakerMatchingService）

**ファイル**: `src/domain/services/speaker_matching_service.py`

#### 現在の実装

- **出力モデル**: `SpeakerMatch`
- **実装方式**: `llm_service.get_structured_llm(SpeakerMatch)`を使用
- **特徴**:
  - すでに構造化出力を使用している
  - ルールベースマッチングと組み合わせている
  - 候補フィルタリング処理が複雑

#### トークン使用量推定

- **入力**: 発言者名、候補リスト（フィルタリング済み、最大20件）
- **推定トークン数**: 300-1000トークン/リクエスト
- **呼び出し頻度**: 議事録処理時（高頻度）

#### BAML化のメリット

- ⚠️ 限定的なメリット
  - すでに`get_structured_llm`で構造化出力を使用
  - プロンプトテンプレートの明示化
  - トークン削減効果は小（5-10%程度）

#### 実装難易度

- **難易度**: Low-Medium
- **必要な作業**:
  1. BAMLファイル作成（`speaker_matching.baml`）
  2. `SpeakerMatch`モデルをBAMLクラスに変換
  3. プロンプトをBAMLに移行
  4. テストの更新

#### BAML化優先度

**優先度: Low-Medium**

- 理由:
  - すでに構造化出力を使用
  - メリットが限定的
  - より優先度の高い処理がある
  - ただし、呼び出し頻度が高いため、トークン削減の累積効果は大きい可能性あり

---

### 2.4 政治家マッチング（PoliticianMatchingService）

**ファイル**: `src/domain/services/politician_matching_service.py`

#### 現在の実装

- **出力モデル**: `PoliticianMatch`
- **実装方式**: `llm_service.get_prompt(prompt_name)`を使用
- **特徴**:
  - プロンプトテンプレートを使用
  - ルールベースマッチングと組み合わせている
  - 候補フィルタリング処理が複雑

#### トークン使用量推定

- **入力**: 発言者名、候補リスト（フィルタリング済み、最大20件）
- **推定トークン数**: 400-1200トークン/リクエスト
- **呼び出し頻度**: 議事録処理時（中頻度）

#### BAML化のメリット

- ✅ 構造化出力の明示化
- ✅ 型安全性の向上
- ✅ プロンプトの管理が容易に
- ⚠️ トークン削減効果は中程度（10-15%程度）

#### 実装難易度

- **難易度**: Medium
- **必要な作業**:
  1. BAMLファイル作成（`politician_matching.baml`）
  2. `PoliticianMatch`モデルをBAMLクラスに変換
  3. プロンプトをBAMLに移行
  4. 構造化出力の実装
  5. テストの更新

#### BAML化優先度

**優先度: Medium**

- 理由:
  - 構造化出力の明示化が必要
  - トークン削減効果が中程度
  - 実装難易度がやや高い
  - 呼び出し頻度が中程度

---

## 3. BAML化の技術的課題

### 3.1 共通の課題

1. **プロンプトの移行**
   - 既存のプロンプトテンプレート（`prompts/`ディレクトリ）からBAMLへの移行
   - プロンプトの品質を維持しつつ、BAMLの文法に適合させる

2. **テストの更新**
   - 既存のテストをBAML実装に対応させる
   - モック戦略の見直し（BAML生成コードのモック）

3. **エラーハンドリング**
   - BAMLのエラーハンドリングと既存のエラーハンドリングの統合
   - `ExternalServiceException`との整合性

4. **依存関係の管理**
   - BAML生成コードの管理
   - `baml_client`パッケージの更新タイミング

### 3.2 処理固有の課題

#### リンク分類・ページ分類

- 複数の分類結果を返す処理（`LinkClassificationResult`）の扱い
- リスト形式の出力のBAML表現

#### 話者マッチング・政治家マッチング

- ルールベースマッチングとの統合
- 候補フィルタリング処理との連携
- 信頼度スコアの扱い

---

## 4. 優先度評価マトリクス

| 処理名 | トークン削減効果 | 実装難易度 | コード改善効果 | 総合優先度 |
|--------|----------------|-----------|---------------|-----------|
| リンク分類 | High (20-30%) | Medium | High | **High** |
| ページ分類 | High (15-25%) | Medium | High | **High** |
| 政治家マッチング | Medium (10-15%) | Medium | Medium | **Medium** |
| 話者マッチング | Low (5-10%) | Low-Medium | Low | **Low-Medium** |

### 優先度の判定基準

- **High**: トークン削減効果が高く、コード改善効果も高い。実装難易度が許容範囲内。
- **Medium**: トークン削減効果またはコード改善効果が中程度。実装難易度がやや高い可能性あり。
- **Low**: メリットが限定的、または実装難易度が高い。

---

## 5. 次のPBI提案

### PBI-005: リンク分類とページ分類のBAML化

#### 概要

政党ページの階層的スクレイピングで使用されているリンク分類とページ分類処理をBAML化し、トークン使用量を削減する。

#### ユーザーストーリー

As a 開発者
I want リンク分類とページ分類処理をBAML化する
So that トークン使用量を削減し、コードの保守性を向上できる

#### 受入条件

- [ ] `baml_src/link_classifier.baml`が作成されている
- [ ] `baml_src/page_classifier.baml`が作成されている
- [ ] `LLMLinkClassifierService`がBAML実装に置き換えられている
- [ ] `LLMPageClassifierService`がBAML実装に置き換えられている
- [ ] 既存のテストが全て通過する
- [ ] トークン使用量が15-25%削減されている（ベンチマーク実施）
- [ ] ドキュメントが更新されている

#### 技術的実装内容

1. **BAMLファイル作成**
   - `baml_src/link_classifier.baml`
     - `LinkClassification`クラス定義
     - `ClassifyLinks`関数定義
   - `baml_src/page_classifier.baml`
     - `PageClassification`クラス定義
     - `ClassifyPage`関数定義

2. **実装の置き換え**
   - `src/infrastructure/external/llm_link_classifier_service.py`
     - 手動JSONパース処理を削除
     - BAML呼び出しに置き換え
   - `src/infrastructure/external/llm_page_classifier_service.py`
     - 手動JSONパース処理を削除
     - BAML呼び出しに置き換え

3. **テストの更新**
   - `tests/unit/llm_link_classifier_service/`
   - `tests/unit/llm_page_classifier_service/`

4. **ベンチマーク**
   - トークン使用量の測定と比較
   - パフォーマンステスト

#### 依存関係

- **前提PBI**: なし
- **ブロック対象**: PBI-006（話者・政治家マッチングのBAML化）

#### 見積もり

- **開発工数**: 2-3日
- **複雑度**: Medium

---

### PBI-006: 話者・政治家マッチングのBAML化

#### 概要

議事録処理で使用される話者マッチングと政治家マッチング処理をBAML化し、プロンプト管理を改善する。

#### ユーザーストーリー

As a 開発者
I want 話者・政治家マッチング処理をBAML化する
So that プロンプト管理を改善し、トークン使用量を削減できる

#### 受入条件

- [ ] `baml_src/speaker_matching.baml`が作成されている
- [ ] `baml_src/politician_matching.baml`が作成されている
- [ ] `SpeakerMatchingService`がBAML実装を使用している
- [ ] `PoliticianMatchingService`がBAML実装を使用している
- [ ] 既存のテストが全て通過する
- [ ] トークン使用量が5-15%削減されている（ベンチマーク実施）
- [ ] ドキュメントが更新されている

#### 技術的実装内容

1. **BAMLファイル作成**
   - `baml_src/speaker_matching.baml`
     - `SpeakerMatch`クラス定義
     - `MatchSpeaker`関数定義
   - `baml_src/politician_matching.baml`
     - `PoliticianMatch`クラス定義
     - `MatchPolitician`関数定義

2. **実装の更新**
   - `src/domain/services/speaker_matching_service.py`
     - BAML呼び出しに置き換え
   - `src/domain/services/politician_matching_service.py`
     - BAML呼び出しに置き換え

3. **テストの更新**
   - `tests/unit/speaker_matching_service/`
   - `tests/unit/politician_matching_service/`

4. **ベンチマーク**
   - トークン使用量の測定と比較
   - マッチング精度の検証

#### 依存関係

- **前提PBI**: #PBI-005（リンク・ページ分類のBAML化）
- **ブロック対象**: なし

#### 見積もり

- **開発工数**: 2-3日
- **複雑度**: Medium

---

## 6. 実装ロードマップ

### フェーズ1: リンク・ページ分類のBAML化（PBI-005）

**期間**: 2-3日

1. Week 1: BAMLファイル作成とリンク分類の実装
2. Week 2: ページ分類の実装とテスト
3. Week 3: ベンチマークとドキュメント作成

### フェーズ2: 話者・政治家マッチングのBAML化（PBI-006）

**期間**: 2-3日

1. Week 1: BAMLファイル作成と話者マッチングの実装
2. Week 2: 政治家マッチングの実装とテスト
3. Week 3: ベンチマークとドキュメント作成

### 総期間: 4-6日

---

## 7. リスクと対策

### リスク1: トークン削減効果が期待値より低い

- **対策**: ベンチマークを早期に実施し、効果を検証
- **代替案**: プロンプトの最適化で補完

### リスク2: BAML生成コードの品質問題

- **対策**: 生成コードのレビューとテストの充実
- **代替案**: 必要に応じて手動で修正

### リスク3: 既存のテストが失敗する

- **対策**: 段階的な移行とテストの並行実施
- **代替案**: フィーチャーフラグで切り替え可能にする

---

## 8. まとめ

本調査により、プロジェクト内のLLM使用箇所を網羅的に調査し、BAML化の優先度を決定しました。

### 主な成果

1. **4つのBAML化候補を特定**
2. **優先度評価マトリクスを作成**
3. **2つのPBIを提案**（リンク・ページ分類、話者・政治家マッチング）
4. **実装ロードマップを策定**（総期間4-6日）

### 推奨アクション

1. **即時**: PBI-005（リンク・ページ分類のBAML化）を開始
2. **短期**: PBI-006（話者・政治家マッチングのBAML化）を実施
3. **中長期**: BAML化のベストプラクティスをドキュメント化

---

## 参考資料

- [BAML公式ドキュメント](https://docs.boundaryml.com/)
- [既存のBAML実装](../../../baml_src/)
- [LLMサービスインターフェース](../../../src/domain/services/interfaces/llm_service.py)
