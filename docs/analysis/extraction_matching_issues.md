# 発言抽出・名寄せ処理の品質課題分析

## 1. 概要

本ドキュメントは、Sagebaseプロジェクトにおける発言抽出（議事録分割）および名寄せ処理（話者・政治家マッチング）の品質課題を定量的に分析したものです。

### 1.1 分析対象

- **発言抽出処理**: MinutesDivider（議事録分割・発言抽出）
- **名寄せ処理**: SpeakerMatchingService、PoliticianMatchingService、ParliamentaryGroupMemberMatchingService

### 1.2 分析手法

- ソースコード静的分析
- テストコードカバレッジ分析
- エラーハンドリングパターン分析
- 既存ログ・モニタリング機構の調査

---

## 2. 発言抽出処理（MinutesDivider）の課題

### 2.1 境界検出の脆弱性

#### 課題の詳細

**対象ファイル**: `src/infrastructure/external/minutes_divider/baml_minutes_divider.py:253-398`

境界検出処理 (`split_minutes_by_boundary()`) は、出席者情報と発言部分の境界を検出するために複数のパターンマッチングに依存しています：

```python
# 境界マーカーの検索パターン
boundary_patterns = [
    '｜境界｜',
    '|境界|',
    '境界：',
    '境界:',
]
```

**問題点**:

1. **パターン依存性**: LLMが生成する境界マーカーが上記パターンに完全一致しない場合、検出に失敗する
2. **フォールバック処理の限界**: 部分一致検索が失敗した場合、全文を発言部分として扱う（行397）
3. **出席者情報の混入リスク**: 境界検出失敗時に出席者リストが発言データに混入する可能性

**影響度**: 高

**発生頻度**: 境界検出成功率のデータが不足しているため未測定

#### 具体的なコード例

```python
# baml_minutes_divider.py:376-397
if start_index == -1:
    # 境界マーカーの部分一致を試す
    for pattern in boundary_patterns:
        for i, char in enumerate(pattern):
            partial_pattern = pattern[:i+1]
            start_index = minutes_text.find(partial_pattern)
            if start_index != -1:
                break
        if start_index != -1:
            break

if start_index == -1:
    # 境界が見つからない場合、全文を発言部分として扱う
    logger.warning("境界マーカーが見つかりませんでした。全文を発言部分として扱います。")
    speech_part = minutes_text
    attendee_part = ""
```

### 2.2 キーワード検索の正規化問題

#### 課題の詳細

**対象ファイル**: `src/infrastructure/external/minutes_divider/baml_minutes_divider.py:92-226`

キーワードベースの章分割処理 (`do_divide()`) では、Unicode正規化（NFKC）を適用していますが、以下の問題があります：

**問題点**:

1. **LLM生成キーワードとの不一致**: LLMが生成したキーワードと元テキストの表記揺れ（全角/半角、カタカナ/ひらがな等）
2. **部分一致のフォールバックの危険性**: 10文字以上のキーワードで部分一致（10文字）を試すが、短いキーワードでは誤検出のリスク
3. **連番補正の警告のみ**: `chapter_number`の連番が崩れている場合、警告のみでエラーにならない（行228-231）

**影響度**: 中〜高

**具体的なコード例**:

```python
# baml_minutes_divider.py:153-167
if start_index == -1:
    # 部分一致も試す（キーワードが長すぎる場合）
    if len(keyword) > 10:
        partial_keyword = keyword[:10]
        start_index = normalized_minutes.find(partial_keyword)
        if start_index != -1:
            logger.warning(
                f"キーワード '{keyword}' が見つかりませんでしたが、"
                f"部分一致 '{partial_keyword}' が見つかりました。"
            )
```

### 2.3 エラーハンドリングの一貫性

#### 課題の詳細

**対象ファイル**:
- `src/infrastructure/external/minutes_divider/baml_minutes_divider.py:437-440` (section_divide_run)
- `src/infrastructure/external/minutes_divider/baml_minutes_divider.py:527-535` (detect_attendee_boundary)

MinutesDividerのBAML呼び出しエラー時、空のデータ構造を返して処理を継続します：

```python
# section_divide_run (437-440行目)
except Exception as e:
    logger.error(f"BAML section_divide_run failed: {e}", exc_info=True)
    # エラー時は空のリストを返す
    return SectionInfoList(section_info_list=[])

# detect_attendee_boundary (527-535行目)
except Exception as e:
    logger.error(f"BAML detect_attendee_boundary failed: {e}", exc_info=True)
    return MinutesBoundary(
        boundary_found=False,
        boundary_text=None,
        boundary_type="none",
        confidence=0.0,
        reason=f"境界検出中にエラーが発生しました: {str(e)}",
    )
```

**問題点**:

1. **データ欠落の隠蔽**: 空リスト返却により、議事録分割エラー時に発言が全て失われる
2. **名寄せサービスとの不整合**: SpeakerMatchingService、PoliticianMatchingServiceは`ExternalServiceException`を送出（後述）

**影響度**: 高

---

## 3. 名寄せ処理（Matching Services）の課題

### 3.1 信頼度閾値の不整合

#### 課題の詳細

**対象ファイル**:
- `baml_src/speaker_matching.baml`
- `baml_src/politician_matching.baml`
- `baml_src/parliamentary_group_member_extractor.baml`

各サービスで信頼度閾値が異なります：

| サービス | 信頼度閾値 | BAML定義 | 実装 |
|---------|-----------|---------|------|
| SpeakerMatching | 0.8 | `confidence >= 0.8` | `baml_speaker_matching_service.py:137` |
| PoliticianMatching | 0.7 | `confidence >= 0.7` | `baml_politician_matching_service.py:149` |
| ParliamentaryGroupMemberMatching | 0.7 | `confidence >= 0.7` | `parliamentary_group_member_matching_service.py` |

**問題点**:

1. **マッチング基準の不統一**: 同じ名前でもサービスによってマッチ判定が異なる可能性
2. **閾値設定の根拠不明**: なぜSpeakerMatchingが0.8で、PoliticianMatchingが0.7なのか、ドキュメント化されていない

**影響度**: 中

**推奨対応**: 全サービスで統一閾値（例: 0.8）を設定し、閾値設定の根拠をドキュメント化

### 3.2 候補絞り込みの限界

#### 課題の詳細

**対象ファイル**:
- `src/domain/services/baml_speaker_matching_service.py:89-104`
- `src/domain/services/baml_politician_matching_service.py:92-116`

BAML呼び出し前に候補を絞り込む処理がありますが、絞り込み数に制限があります：

| サービス | 最大候補数 | 実装箇所 |
|---------|-----------|---------|
| SpeakerMatching | 10 | `baml_speaker_matching_service.py:89` |
| PoliticianMatching | 20 | `baml_politician_matching_service.py:92` |

**問題点**:

1. **大規模データセットでの候補漏れ**: 適切な候補が絞り込み外になる可能性
2. **絞り込み基準の不明確**: 候補の選定基準（所属会議体による★マーク付与等）が実装に埋め込まれている

**影響度**: 中

**具体的なコード例**:

```python
# baml_speaker_matching_service.py:89-104
candidates = list(available_speakers)
# 候補を最大10件に絞り込み
if len(candidates) > 10:
    # 会議体所属者を優先
    priority_candidates = [s for s in candidates if s.is_conference_member]
    other_candidates = [s for s in candidates if not s.is_conference_member]

    if len(priority_candidates) >= 10:
        candidates = priority_candidates[:10]
    else:
        remaining = 10 - len(priority_candidates)
        candidates = priority_candidates + other_candidates[:remaining]
```

### 3.3 リトライロジック未適用

#### 課題の詳細

**対象ファイル**: 全BAMLサービス

BAML呼び出し（LLM API呼び出し）に対して、`src/infrastructure/resilience/retry.py`で定義されているリトライポリシーが適用されていません。

**問題点**:

1. **一時的エラーでの処理失敗**: ネットワークエラー、レート制限等で処理が失敗する
2. **リトライポリシーの不活用**: `RetryPolicy.external_service()`（最大5回、指数バックオフ）が利用可能だが未使用

**影響度**: 高

**推奨対応**:

```python
from src.infrastructure.resilience.retry import with_retry, RetryPolicy

@with_retry(policy=RetryPolicy.external_service())
async def _call_baml_matching(self, ...):
    # BAML呼び出し
```

### 3.4 発言者名の正規化不足

#### 課題の詳細

**対象ファイル**: `src/domain/services/speaker_domain_service.py`

`normalize_speaker_name()`メソッドは敬称除去を行いますが、対応リストが限定的です：

```python
honorifics = ["議員", "君", "さん", "氏", "先生", "委員長", "議長"]
```

**問題点**:

1. **未対応の敬称・役職**: 「様」「殿」「代表」「副委員長」等が未対応
2. **地方議会特有の役職**: 「町長」「村長」「副議長」等の自治体固有の役職が未対応

**影響度**: 中

---

## 4. 定量的な課題サマリー

| ID | カテゴリ | 課題 | 影響度 | 対象ファイル | 推奨優先度 |
|----|---------|------|-------|-------------|----------|
| Q-001 | エラーハンドリング | MinutesDivider: 空リスト返却 vs MatchingService: 例外スロー | 高 | `baml_minutes_divider.py:437-440` | P0 |
| Q-002 | 境界検出 | 境界マーカー検索が複数パターン依存、失敗時に全文を発言部分扱い | 高 | `baml_minutes_divider.py:253-398` | P0 |
| Q-003 | 信頼度閾値 | SpeakerMatching: 0.8 vs PoliticianMatching: 0.7 の不整合 | 中 | BAML定義ファイル | P1 |
| Q-004 | 候補絞り込み | SpeakerMatching: max 10 vs PoliticianMatching: max 20 | 中 | `*_matching_service.py` | P1 |
| Q-005 | リトライロジック | BAML呼び出しにリトライポリシー未適用 | 高 | 全BAMLサービス | P0 |
| Q-006 | テストカバレッジ | 境界検出の複雑パターン、異常入力のエッジケース不足 | 中 | `tests/` | P2 |
| Q-007 | 正規化 | キーワード検索の表記揺れ対応不足 | 中 | `baml_minutes_divider.py:92-226` | P1 |
| Q-008 | 正規化 | 発言者名の敬称除去リスト不足 | 中 | `speaker_domain_service.py` | P2 |
| Q-009 | データ整合性 | chapter_number / speech_order の連番補正が警告のみ | 中 | `baml_minutes_divider.py:228-231` | P2 |

**優先度の定義**:
- **P0**: 致命的な品質問題、データ欠落のリスク
- **P1**: 重要な品質問題、マッチング精度に影響
- **P2**: 改善推奨、テストカバレッジ・保守性に影響

---

## 5. 推奨改善項目

### 5.1 短期対応（P0）

1. **エラーハンドリングの統一** (Q-001)
   - MinutesDividerでも`ExternalServiceException`を送出
   - または、全サービスでグレースフル劣化を採用
   - エラー時のフォールバック戦略を明確化

2. **境界検出の堅牢化** (Q-002)
   - 境界マーカーのパターンを拡充
   - LLMプロンプトで境界マーカーのフォーマットを厳密に指定
   - 境界検出失敗時の警告を強化（モニタリング対象に追加）

3. **リトライポリシーの適用** (Q-005)
   - 全BAML呼び出しに`RetryPolicy.external_service()`を適用
   - レート制限エラーの考慮（`retry_after`尊重）

### 5.2 中期対応（P1）

4. **信頼度閾値の統一** (Q-003)
   - 全サービスで閾値を0.8に統一（または0.75に統一）
   - 閾値設定の根拠をドキュメント化

5. **候補絞り込みロジックの改善** (Q-004)
   - 最大候補数を設定可能にする（環境変数化）
   - 絞り込み基準をドキュメント化
   - 候補選定の優先順位ロジックを明示的に実装

6. **キーワード検索の正規化強化** (Q-007)
   - Unicode正規化に加えて、カタカナ→ひらがな変換を検討
   - 部分一致のフォールバック閾値（現在10文字）を調整可能にする

### 5.3 長期対応（P2）

7. **テストカバレッジの拡充** (Q-006)
   - 境界検出の複雑パターンテスト追加
   - 異常入力（空文字、極端に長いテキスト、特殊文字）のエッジケーステスト追加
   - 統合テスト（speaker_matching + politician_matching）の追加

8. **発言者名正規化の拡充** (Q-008)
   - 敬称・役職リストの拡充（地方議会対応）
   - 正規化ルールの設定ファイル化

9. **データ整合性チェックの強化** (Q-009)
   - `chapter_number`の連番チェックをエラーに昇格
   - または、自動的に連番を振り直す処理を追加

---

## 6. モニタリング・メトリクス提案

品質改善のために、以下のメトリクスを追跡することを推奨します：

| メトリクス | 説明 | 目標値 |
|-----------|------|-------|
| 境界検出成功率 | `boundary_found=True`の割合 | 95%以上 |
| 発言抽出成功率 | 空でない発言リストが返される割合 | 98%以上 |
| 話者マッチング成功率 | `matched=True`の割合 | 90%以上 |
| 政治家マッチング成功率 | `matched=True`の割合 | 85%以上 |
| LLMリトライ発生率 | リトライが発生した処理の割合 | 5%未満 |
| 処理エラー率 | 例外が発生した処理の割合 | 1%未満 |

---

## 7. 参考資料

- MinutesDivider実装: `src/infrastructure/external/minutes_divider/baml_minutes_divider.py`
- SpeakerMatching実装: `src/domain/services/baml_speaker_matching_service.py`
- PoliticianMatching実装: `src/domain/services/baml_politician_matching_service.py`
- リトライポリシー定義: `src/infrastructure/resilience/retry.py`
- エラークラス定義: `src/domain/exceptions.py`, `src/infrastructure/external/llm_errors.py`
