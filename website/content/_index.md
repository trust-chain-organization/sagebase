---
title: "Sagebase - 日本の政治活動を可視化する"
date: 2025-11-16
draft: false
description: "Sagebaseは、日本の政治活動を追跡・分析し、透明性を高めるためのアプリケーションです。議事録分析、政治家データベース、発言追跡など、多彩な機能を提供します。"
---

## サービス概要

Sagebase（セージベース）は、日本の政治活動を追跡・分析するためのオープンデータプラットフォームです。全国1,966の自治体にわたる議事録を収集・分析し、政治家の発言や活動を可視化します。LLM（大規模言語モデル）を活用した高精度な発言者マッチングにより、誰が何を発言したかを正確に追跡できます。クリーンアーキテクチャに基づいた設計により、拡張性と保守性を両立し、研究者、ジャーナリスト、市民活動家のデータドリブンな意思決定を支援します。

---

## 💡 価値提案

Sagebaseが提供する3つの価値：

### 🔍 透明性の向上

政治家の発言や活動を時系列で追跡し、公約と実際の行動を比較できます。データの可視化により、政治活動の透明性を高め、市民の知る権利を保障します。

### 📊 データドリブンな意思決定支援

全国の議事録データを統合的に分析し、政策トレンドや地域間の比較を可能にします。研究者やジャーナリストが、データに基づいた調査・報道を行うための強力なツールを提供します。

### 🏛️ 民主主義の強化

市民が政治家の活動を容易に監視できる環境を整備することで、説明責任を強化し、民主主義の健全な発展に貢献します。

---

## 🎯 ターゲットユーザー

Sagebaseは、以下のような方々を対象としています：

- **📚 研究者**: 政治学、社会学の研究に必要なデータを収集・分析
- **📰 ジャーナリスト**: 政治報道のファクトチェックと深堀り取材
- **🗣️ 市民活動家**: 地域政治の監視と住民運動の根拠づくり
- **🏢 シンクタンク**: 政策提言のためのエビデンス収集
- **👥 一般市民**: 地域の政治活動に関心を持つすべての人

---

## 🚀 主要機能

### 1. 議事録分析

会議の議事録（PDFやテキスト）から発言を自動的に抽出し、構造化して保存します。LangGraphを使用した複数ステップの処理により、高精度な分析を実現します。

### 2. 政治家データベース

全国の政治家プロフィールを自動収集し、所属政党や経歴情報を管理します。最新の情報を常に反映し、包括的なデータベースを提供します。

### 3. 発言追跡

LLM（Google Gemini API）を活用し、議事録中の発言者を実際の政治家に紐付けます。ハイブリッドアプローチにより、高い精度でマッチングを実現します。

### 4. データカバレッジモニタリング

日本全国1,966の自治体にわたるデータの完全性をインタラクティブダッシュボードで可視化します。地域別のデータカバレッジとデータ品質メトリクスを提供します。

### 5. LLM処理履歴追跡

すべてのLLM処理を記録し、プロンプトバージョン管理と監査証跡を提供します。処理の再現性を確保し、データの信頼性を高めます。

---

## 🛠️ 技術的な特徴

- **クリーンアーキテクチャ**: 明確なレイヤー分離による拡張性と保守性
- **型安全性**: Python型ヒントとpyrightによる堅牢なコード
- **コード品質**: Ruffによる自動フォーマットとリント
- **テスト**: pytestによる非同期テスト
- **Docker**: コンテナベースの開発環境
- **LLM**: Google Gemini APIを活用した高精度な分析

---

## 📞 お問い合わせ・詳細情報

Sagebaseについてもっと知りたい方は、以下のページをご覧ください。

<div style="text-align: center; margin: 40px 0;">
  <a href="/about" style="display: inline-block; padding: 12px 24px; margin: 10px; background-color: #0066cc; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">📖 概要を見る</a>
  <a href="/features" style="display: inline-block; padding: 12px 24px; margin: 10px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">⚡ 機能詳細を見る</a>
  <a href="/contact" style="display: inline-block; padding: 12px 24px; margin: 10px; background-color: #6c757d; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">✉️ お問い合わせ</a>
</div>

---

## 🔗 リソース

- **GitHubリポジトリ**: [trust-chain-organization/sagebase](https://github.com/trust-chain-organization/sagebase)
- **ドキュメント**: [ARCHITECTURE.md](https://github.com/trust-chain-organization/sagebase/blob/main/docs/ARCHITECTURE.md)
- **開発ガイド**: [DEVELOPMENT_GUIDE.md](https://github.com/trust-chain-organization/sagebase/blob/main/docs/DEVELOPMENT_GUIDE.md)
