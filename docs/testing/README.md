# テスト関連ドキュメント

このディレクトリには、py-stockプロジェクトのテストカバレッジ分析と向上に関するドキュメントが格納されています。

## 📁 ファイル一覧

### 📊 分析レポート
- **`coverage_analysis_report.md`** - 最新のカバレッジ分析レポート（自動生成）
- **`coverage_data.json`** - カバレッジ分析の詳細データ（自動生成）

### 📚 ガイドライン
- **`coverage_improvement_guide.md`** - テストカバレッジ向上のための具体的なガイド
- **`coverage_difficulty_analysis.md`** - カバレッジ向上難易度の詳細分析

### 🛠️ ツール
- **`coverage_analyzer.py`** - カバレッジ分析自動化スクリプト

## 🚀 クイックスタート

### 1. カバレッジ分析の実行
```bash
# プロジェクトルートから実行
uv run python docs/testing/coverage_analyzer.py
```

### 2. 生成されるレポートの確認
- **HTMLレポート**: `htmlcov/index.html` をブラウザで開く
- **Markdownレポート**: `docs/testing/coverage_analysis_report.md` を確認

### 3. 改善作業の開始
1. `coverage_improvement_guide.md` でガイドラインを確認
2. `coverage_difficulty_analysis.md` で優先度を確認
3. 簡単改善対象（80%以上のファイル）から開始

## 📊 現在のカバレッジ状況

**全体カバレッジ**: 70.80%

### 難易度別分類
- 🟢 **Easy（80%以上）**: 28ファイル
- 🟡 **Medium（60-79%）**: 7ファイル  
- 🟠 **Hard（40-59%）**: 0ファイル
- 🔴 **Very Hard（40%未満）**: 0ファイル
- 📚 **Examples（特殊）**: 7ファイル

## 🎯 改善目標

### 短期目標（1-2週間）
- **目標カバレッジ**: 75%
- **対象**: Easy分類の100%達成

### 中期目標（1ヶ月）
- **目標カバレッジ**: 80%
- **対象**: Medium分類の改善

### 長期目標（3ヶ月）
- **目標カバレッジ**: 85%
- **対象**: アーキテクチャ改善

## 🛠️ 使用方法

### 定期的な分析実行
```bash
# 週次でカバレッジ分析を実行
uv run python docs/testing/coverage_analyzer.py

# 特定の閾値でテスト実行
uv run pytest --cov=src --cov-fail-under=75
```

### 新機能開発時のチェック
```bash
# 新機能のカバレッジチェック
uv run pytest tests/unit/test_new_feature.py --cov=src.new_module --cov-report=term-missing
```

### CI/CDでの自動チェック
```yaml
# GitHub Actions example
- name: Test with coverage
  run: |
    uv run pytest --cov=src --cov-report=xml --cov-fail-under=70
```

## 📚 関連ドキュメント

### プロジェクト全体
- [`../../README.md`](../../README.md) - プロジェクト概要
- [`../../CLAUDE.md`](../../CLAUDE.md) - 開発ガイドライン

### テスト実行
- [`../setup.md`](../setup.md) - 環境セットアップ
- [`../usage.md`](../usage.md) - 基本的な使用方法

## 🔄 更新頻度

### 自動生成ファイル
- `coverage_analysis_report.md` - カバレッジ分析実行時に更新
- `coverage_data.json` - カバレッジ分析実行時に更新

### 手動更新ファイル
- `coverage_improvement_guide.md` - 必要に応じて更新
- `coverage_difficulty_analysis.md` - 大幅なアーキテクチャ変更時に更新
- `README.md` - ドキュメント構造変更時に更新

## 🤝 貢献方法

### テストカバレッジ向上への貢献
1. Easy分類ファイルのエラーハンドリングテスト追加
2. Medium分類ファイルのモック活用テスト追加
3. 新機能開発時の包括的テスト作成

### ドキュメント改善への貢献
1. ガイドラインの具体例追加
2. 分析結果の解釈方法改善
3. 自動化スクリプトの機能拡張

## 📞 質問・サポート

テストカバレッジに関する質問や改善提案がある場合：

1. **GitHub Issues**: プロジェクトのIssueで質問
2. **ドキュメント**: このディレクトリのガイドを参照
3. **コードレビュー**: テスト追加時の相談

---

**最終更新**: 2025-05-31  
**作成者**: カバレッジ分析自動化システム