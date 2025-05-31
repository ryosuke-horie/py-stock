# 操作ガイド

## 概要

py-stockは株式投資の投資タイミング見極めを支援するPython分析システムです。テクニカル分析、ファンダメンタルズ分析、リスク管理、税務計算などの機能を提供します。

## 利用方法

### 1. ダッシュボードによる操作（推奨）

#### ダッシュボード起動
```bash
uv run streamlit run dashboard/app.py
```

ブラウザで http://localhost:8501 にアクセス

#### ダッシュボードの主要機能

##### 📊 Overview タブ
**ウォッチリスト監視の中心**
- 複数銘柄の価格・指標をリアルタイム表示
- パフォーマンス概要と統計情報
- アクティブアラート一覧

**使い方：**
1. サイドバーで監視銘柄を設定（例：7203, 9984, AAPL）
2. 更新間隔を調整（デフォルト：30秒）
3. 全体的な市況を一目で確認

##### 📈 Charts タブ
**詳細なテクニカル分析**
- インタラクティブローソク足チャート
- テクニカル指標のオーバーレイ表示
- 複数時間軸対応（1分〜日足）

**使い方：**
1. 銘柄を選択
2. 時間軸を選択（1m, 5m, 1h, 1d）
3. 表示したい指標を選択：
   - 移動平均（EMA9, EMA21, SMA25）
   - オシレーター（RSI, ストキャスティクス）
   - トレンド（MACD）
   - バンド（ボリンジャーバンド）
   - 出来高（VWAP）

##### 🚦 Signals タブ
**売買シグナル管理**
- リアルタイムシグナル監視
- シグナル履歴とパフォーマンス分析
- 仮想トレード機能

**主なシグナル：**
- **買いシグナル**: RSI過売り、ストキャス過売り、MACDゴールデンクロス
- **売りシグナル**: RSI過買い、ストキャス過買い、MACDデッドクロス
- **中立シグナル**: ボリンジャーバンドスクイーズ、RSI中立圏

**使い方：**
1. シグナル履歴で過去のパフォーマンスを確認
2. 現在のシグナル状況をリアルタイム監視
3. 仮想トレードで戦略をテスト

##### 🔔 Alerts タブ
**アラート設定・管理**
- 価格アラート（上限・下限）
- シグナルアラート
- ボラティリティアラート
- 出来高アラート

**設定方法：**
1. アラート種類を選択
2. 対象銘柄を選択
3. 条件を設定（価格、％変動など）
4. アラートを有効化

##### 🔄 Backtest タブ
**戦略検証**
- 過去データでの戦略バックテスト
- パフォーマンス可視化
- 詳細統計サマリー

**使い方：**
1. 戦略パラメータを設定
2. バックテスト期間を選択
3. 結果を分析：
   - 総リターン
   - 勝率
   - 最大ドローダウン
   - シャープレシオ

##### 📋 Fundamental Analysis タブ
**企業ファンダメンタルズ分析**
- 企業財務指標の表示
- 財務健全性スコア（100点満点）
- 同業他社比較
- 成長トレンド分析

**主な指標：**
- **収益性**: PER, PBR, ROE, ROA
- **安全性**: 流動比率, 自己資本比率, 負債比率
- **成長性**: 売上成長率, 利益成長率（CAGR）
- **配当**: 配当利回り, 配当性向

##### 📖 Investment Story タブ
**AI投資レポート**
- 自然言語での分析結果説明
- 3シナリオ分析（楽観・中立・悲観）
- リスクマトリックス
- 投資用語自動解説

**活用方法：**
1. 銘柄を選択してストーリー生成
2. 3つのシナリオで投資判断を検討
3. リスク要因を体系的に理解
4. 専門用語の解説で学習

##### 💰 Tax & Cost タブ
**税務・コスト管理**
- 手数料比較（主要証券会社）
- NISA枠利用状況追跡
- 税務計算（20.315%）
- 損益通算シミュレーション

**機能：**
- **手数料最適化**: 投資額に応じた最安証券会社の表示
- **NISA管理**: 成長投資枠・つみたて投資枠の残高管理
- **税務計算**: FIFO方式での譲渡益計算
- **節税提案**: 含み損実現による税務最適化

##### 📊 Performance Tracking タブ
**投資パフォーマンス追跡**
- 総合スコア（100点満点）
- 投資傾向分析
- 取引パターン認識
- 改善提案

**分析内容：**
- **勝率・損益比**: 取引の成功率と平均利益
- **投資傾向**: 損切り・利確・リスク管理の傾向
- **時間帯分析**: 時間帯別・保有期間別の成功率
- **行動分析**: リベンジトレード・パニック決済の検出

### 2. コマンドライン操作

#### 基本データ取得

```bash
# 単一銘柄データ取得
uv run python main.py --symbol 7203 --interval 1m
uv run python main.py --symbol AAPL --interval 5m --period 1d

# 複数銘柄並列取得
uv run python main.py --symbols 7203 9984 AAPL MSFT --interval 5m

# 利用可能オプション
uv run python main.py --help
```

#### テクニカル分析

```bash
# RSI, MACD, ボリンジャーバンドなどの総合分析
uv run python main.py --technical 7203 --interval 5m

# より詳細な分析（長期間）
uv run python main.py --technical AAPL --interval 1d --period 3mo
```

#### サポート・レジスタンス分析

```bash
# 重要価格水準の自動検出
uv run python main.py --support-resistance 7203 --interval 1h --period 1mo

# デイトレード用（短期間）
uv run python main.py --support-resistance MSFT --interval 5m --period 1d
```

#### キャッシュ管理

```bash
# キャッシュ状況確認
uv run python main.py --cache-stats

# 古いキャッシュ削除（7日より古い）
uv run python main.py --clean-cache 7

# サンプルデータ表示
uv run python main.py --samples
```

### 3. Python APIによる操作

#### 基本的な分析フロー

```python
from src.data_collector.stock_data_collector import StockDataCollector
from src.technical_analysis.indicators import TechnicalIndicators
from src.technical_analysis.support_resistance import SupportResistanceDetector

# 1. データ収集
collector = StockDataCollector()
data = collector.get_stock_data("7203.T", interval="5m", period="1d")

# 2. テクニカル分析
indicators = TechnicalIndicators(data)
analysis = indicators.comprehensive_analysis()

# 3. 売買シグナル確認
signals = indicators.get_trading_signals()
if signals['rsi_oversold'] and signals['price_above_vwap']:
    print("買いシグナル検出")

# 4. サポート・レジスタンス分析
detector = SupportResistanceDetector(data)
levels = detector.detect_support_resistance_levels()
current_price = data['close'].iloc[-1]

# 最寄りのサポート・レジスタンス確認
for level in levels:
    distance = abs(level.price - current_price) / current_price * 100
    print(f"{level.level_type}: {level.price:.2f} (距離: {distance:.1f}%)")
```

#### 税務・NISA管理

```python
from src.tax_calculation.tax_calculator import TaxCalculator
from src.tax_calculation.nisa_manager import NisaManager

# 税務計算
tax_calc = TaxCalculator()
tax_calc.add_trade("7203", 100, 2500, "buy")   # 100株を2500円で購入
tax_calc.add_trade("7203", 50, 2700, "sell")   # 50株を2700円で売却

tax_result = tax_calc.calculate_taxes()
print(f"譲渡益税: {tax_result.total_tax:,.0f}円")
print(f"実現損益: {tax_result.realized_pnl:,.0f}円")

# NISA枠管理
nisa = NisaManager()
nisa.add_investment("成長投資枠", 500000, "2024-01-15")
remaining = nisa.get_remaining_capacity()
print(f"成長投資枠残り: {remaining['growth']:,.0f}円")
```

#### パフォーマンス追跡

```python
from src.performance_tracking.performance_tracker import PerformanceTracker
from src.performance_tracking.improvement_suggestions import ImprovementSuggestionEngine

# 取引履歴分析
tracker = PerformanceTracker()
tracker.add_trade("7203", 2500, 2700, "2024-01-15", "2024-01-20")
tracker.add_trade("9984", 1800, 1750, "2024-01-16", "2024-01-21")

performance = tracker.get_comprehensive_analysis()
print(f"総合スコア: {performance.overall_score}/100")
print(f"勝率: {performance.win_rate:.1%}")

# 改善提案
suggestion_engine = ImprovementSuggestionEngine(tracker)
suggestions = suggestion_engine.generate_suggestions()

for suggestion in suggestions.high_priority:
    print(f"【高優先度】{suggestion.title}")
    print(f"説明: {suggestion.description}")
```

## 推奨ワークフロー

### デイトレーダー向け

1. **朝の準備**（9:00前）
   ```bash
   uv run streamlit run dashboard/app.py
   ```
   - Overviewタブでプレマーケット状況確認
   - Alertsタブでアラート設定

2. **取引時間中**（9:00-15:00）
   - Chartsタブで個別銘柄分析
   - Signalsタブでリアルタイムシグナル監視
   - アラート通知で機会を逃さない

3. **引け後分析**（15:00以降）
   - Performance Trackingタブで今日の成績確認
   - Backtestタブで戦略改善
   - 明日の戦略をメモ

### 中長期投資家向け

1. **週次分析**
   - Fundamental Analysisタブで企業分析
   - Investment Storyタブで投資判断
   - Tax & Costタブで税務最適化

2. **月次レビュー**
   - Performance Trackingで月次成績確認
   - NISAタブで枠利用状況確認
   - ポートフォリオリバランス検討

3. **四半期レビュー**
   - 年間税務戦略の見直し
   - 投資方針の調整

## ベストプラクティス

### セキュリティ
- API キーは環境変数で管理
- 個人情報はローカル保存のみ
- パスワードは適切に保護

### パフォーマンス
- ウォッチリスト銘柄数は10銘柄以下を推奨
- 更新間隔は用途に応じて調整
- 古いキャッシュは定期的に削除

### データ品質
- 市場開始前・終了後のデータに注意
- yfinanceの15-20分遅延を考慮
- 異常値は自動で検出・除外

## 次のステップ

- [MCP セットアップ](mcp-setup.md) - Claude統合を設定
- [トラブルシューティング](troubleshooting.md) - 問題解決方法
- [開発者ガイド](development.md) - カスタマイズ方法