# py-stock

株式投資の投資タイミングの見極めをPython x Claude Code x MCPでやってみる試み

## 🚀 実装状況

### ✅ 完了済み

**基盤データ収集システム v1.0**
- **StockDataCollector**: yfinanceを使った効率的な株価データ取得
- **SymbolManager**: 日本株・米国株の銘柄コード統一管理
- **SettingsManager**: JSON設定管理と環境変数対応
- **DataValidator**: データ品質検証と異常値検出機能
- **SQLiteキャッシュ**: 取得データの永続化とパフォーマンス最適化
- **並列処理**: 複数銘柄の効率的な並列データ取得
- **エラーハンドリング**: リトライ機能とレート制限対応

**テクニカル分析エンジン v1.0** 🆕
- **TechnicalIndicators**: デイトレード用主要指標ライブラリ
- **移動平均**: EMA(9,21)、SMA(25,75) 完全対応
- **オシレーター**: RSI(14)、ストキャスティクス(%K,%D)
- **トレンド**: MACD(12,26,9)、シグナル検出、ヒストグラム
- **バンド**: ボリンジャーバンド(20,±2σ)、スクイーズ検出
- **価格**: VWAP(当日・前日比較)、乖離分析
- **ボラティリティ**: ATR(14)、リスクレベル判定
- **総合シグナル**: 複数指標組み合わせ売買判定

**サポート・レジスタンス検出システム v1.0** 🆕
- **SupportResistanceDetector**: 価格水準重要ポイント自動特定
- **スイング検出**: 直近高値・安値の自動検出アルゴリズム
- **価格クラスター**: 類似レベルのグループ化と強度評価
- **ピボットポイント**: 標準・カマリラピボット完全対応
- **ブレイクアウト**: リアルタイム突破判定・確認機能
- **時間帯分析**: セッション別強度・拒否率評価
- **出来高連動**: 出来高を考慮した信頼度スコアリング

**税務・NISA管理システム v1.0** 🆕  
- **TaxCalculator**: 日本の投資税制完全対応（20.315%税率、FIFO管理）
- **NisaManager**: 新NISA制度対応（成長投資枠240万円、つみたて枠120万円）
- **FeeCalculator**: 主要証券会社手数料比較（SBI・楽天・松井証券）
- **ProfitLossSimulator**: 損益通算・損失繰越3年間管理
- **税務最適化**: 含み損益実現タイミング最適化提案
- **節税効果計算**: NISA活用による具体的節税額算出

**パフォーマンス追跡・学習システム v1.0** 🆕
- **PerformanceTracker**: 包括的取引履歴分析（勝率・損益比・総合スコア）
- **PatternAnalyzer**: AI駆動取引パターン認識・成功パターン検出
- **TendencyAnalyzer**: 個人投資行動詳細分析（損切り・利確傾向）
- **ImprovementEngine**: 個別化改善提案システム（優先度別アクション）
- **感情分析**: リベンジトレード・パニック決済の検出
- **パフォーマンスレベル**: 初心者〜エキスパート判定システム

**高度ファンダメンタルズ分析 v1.0** 🆕
- **FundamentalAnalyzer**: 企業財務深度分析（PER・ROE・財務健全性スコア）
- **同業他社比較**: 業界内ポジション自動評価・順位付け
- **成長トレンド分析**: 売上・利益のCAGR（年平均成長率）計算
- **財務健全性判定**: 流動比率・自己資本比率による100点満点評価
- **配当分析**: 配当利回り・配当性向・継続性評価

**投資ストーリー・シナリオ生成 v1.0** 🆕
- **InvestmentStoryGenerator**: AI投資レポート自動生成（初心者向け）
- **3シナリオ分析**: 楽観・中立・悲観シナリオ投資分析
- **投資用語解説**: 専門用語の自動解説・具体例提示
- **IntegratedAnalyzer**: ファンダメンタルズ+テクニカル統合分析
- **リスクマトリックス**: 体系的リスク要因整理
- **目標株価算出**: シナリオ別発生確率と目標価格

**MCP統合アーキテクチャ v1.0** 🆕
- **Stock Data MCPサーバ**: リアルタイム株価データ配信・キャッシング
- **News Analysis MCPサーバ**: 銘柄関連ニュース・センチメント分析
- **レート制限管理**: API制限対応・インテリジェント制御
- **銘柄コード正規化**: 日本株・米国株統一管理
- **TypeScript実装**: 高性能MCP サーバアーキテクチャ

**Streamlitダッシュボード v2.0** 🆕
- **リアルタイム監視**: ウォッチリスト銘柄の価格・指標表示
- **インタラクティブチャート**: ローソク足+テクニカル指標オーバーレイ
- **シグナル履歴管理**: 売買シグナル発生履歴とパフォーマンス追跡
- **アラートシステム**: 価格・シグナル・ボラティリティ・出来高アラート
- **バックテスト機能**: 戦略検証と結果可視化
- **仮想トレード**: リスクフリーでの戦略テスト
- **ファンダメンタルズタブ**: 企業財務指標・同業他社比較可視化
- **投資ストーリータブ**: ストーリー形式分析結果・3シナリオ表示
- **税務・コストタブ**: 手数料比較・NISA枠利用状況・税務計算
- **パフォーマンス追跡タブ**: 総合スコア・投資傾向・改善提案表示

## 🔧 インストールと使用方法

### セットアップ
```bash
# リポジトリクローン
git clone https://github.com/ryosuke-horie/py-stock.git
cd py-stock

# uvで仮想環境作成と依存関係インストール
uv sync

# ダッシュボード用ライブラリも含めてインストール
uv sync --extra dashboard

# 開発用ツールも含めてインストール（開発者向け）
uv sync --extra all
```

## 🖥️ ダッシュボード使用方法

### ダッシュボード起動
```bash
# Streamlitダッシュボードを起動
uv run streamlit run dashboard/app.py

# または仮想環境をアクティベートしてから
uv shell
streamlit run dashboard/app.py

# ブラウザで自動的に開く（通常 http://localhost:8501）
```

### ダッシュボード機能

#### 1. Overview タブ
- **ウォッチリスト監視**: 複数銘柄の価格・指標をリアルタイム表示
- **パフォーマンス概要**: 総合パフォーマンス指標と統計
- **アクティブアラート**: 現在発火中のアラート一覧

#### 2. Charts タブ
- **インタラクティブチャート**: ローソク足チャートにテクニカル指標をオーバーレイ
- **時間軸切り替え**: 1分足、5分足、1時間足、日足の表示切り替え
- **指標選択**: RSI、MACD、ボリンジャーバンド、移動平均の表示制御

#### 3. Signals タブ
- **リアルタイムシグナル**: 現在の売買シグナル状況を監視
- **シグナル履歴**: 過去のシグナル発生履歴と結果分析
- **パフォーマンス統計**: 勝率、平均利益、最大ドローダウン等
- **仮想トレード**: リアルマネーを使わない戦略テスト

#### 4. Alerts タブ
- **アラート設定**: 価格・シグナル・ボラティリティ・出来高アラートの作成
- **アラート履歴**: 過去のアラート発火履歴
- **アクティブ管理**: アラートの有効/無効切り替え

#### 5. Backtest タブ
- **戦略バックテスト**: 過去データでの戦略検証
- **パフォーマンス可視化**: 損益グラフ、ドローダウン分析
- **統計サマリー**: 詳細なパフォーマンス指標

#### 6. Fundamental Analysis タブ 🆕
- **企業財務指標**: PER・PBR・ROE・配当利回り表示
- **財務健全性スコア**: 100点満点での企業評価
- **成長トレンドチャート**: 売上・利益のCAGR可視化
- **同業他社比較**: 業界内ポジション・順位表示

#### 7. Investment Story タブ 🆕
- **AIストーリー生成**: 自然言語での分析結果説明
- **3シナリオ表示**: 楽観・中立・悲観シナリオ分析
- **リスクマトリックス**: 体系的リスク要因可視化
- **投資用語解説**: 専門用語の自動解説機能

#### 8. Tax & Cost タブ 🆕
- **手数料比較チャート**: 主要証券会社別手数料比較
- **NISA枠利用状況**: 成長投資枠・つみたて投資枠の残高表示
- **税務計算結果**: 譲渡益税・実現損益の自動計算
- **損益通算シミュレーション**: 最適な売却タイミング提案

#### 9. Performance Tracking タブ 🆕
- **総合スコアゲージ**: 投資パフォーマンス100点満点表示
- **投資傾向レーダーチャート**: 損切り・利確・リスク管理傾向
- **取引パターン分析**: 時間帯別・保有期間別成功率
- **改善提案表示**: 優先度別アクション項目と実装計画

### ダッシュボード使用の流れ

#### ステップ1: 初回セットアップ
1. ダッシュボードを起動: `streamlit run dashboard/app.py`
2. ブラウザでhttp://localhost:8501 にアクセス
3. サイドバーでウォッチリスト銘柄を設定（例: 7203, 9984, AAPL）

#### ステップ2: リアルタイム監視
1. **Overview タブ**でウォッチリスト全体の状況を確認
2. **Charts タブ**で個別銘柄の詳細チャート分析
3. 指標オーバーレイでテクニカル分析を実行

#### ステップ3: シグナル活用
1. **Signals タブ**でリアルタイムシグナルを監視
2. 仮想トレード機能で戦略をテスト
3. シグナル履歴でパフォーマンスを分析

#### ステップ4: アラート設定
1. **Alerts タブ**で価格やシグナルアラートを設定
2. ブレイクアウトやボラティリティ変化を自動監視
3. アラート履歴でタイミングを検証

#### ステップ5: 戦略検証
1. **Backtest タブ**で過去データを使った戦略検証
2. パフォーマンス指標で戦略の有効性を評価
3. 最適化パラメータの調整

## 🔧 コマンドライン使用方法

### 基本的なデータ取得例

#### 単一銘柄データ取得
```bash
uv run python main.py --symbol 7203 --interval 1m
uv run python main.py --symbol AAPL --interval 5m --period 1d
```

#### 複数銘柄並列取得
```bash
uv run python main.py --symbols 7203 9984 AAPL MSFT GOOGL --interval 5m
uv run python main.py --symbols 7203 6758 7974 9984 6861 --interval 1m
```

#### キャッシュ管理
```bash
uv run python main.py --cache-stats
uv run python main.py --clean-cache 7
uv run python main.py --samples
```

#### テクニカル分析
```bash
uv run python main.py --technical 7203 --interval 5m
uv run python main.py --technical AAPL --interval 1d --period 3mo
uv run python main.py --technical MSFT --interval 1m --period 1d
```

#### サポート・レジスタンス分析
```bash
uv run python main.py --support-resistance 7203 --interval 1h --period 1mo
uv run python main.py --support-resistance AAPL --interval 1d --period 6mo
uv run python main.py --support-resistance MSFT --interval 5m --period 1d
```

## 🚨 トラブルシューティング

### 一般的な問題と解決方法

#### ダッシュボード起動時のエラー
```bash
# モジュールが見つからない場合
uv sync --extra dashboard

# ポートが使用中の場合
uv run streamlit run dashboard/app.py --server.port 8502
```

#### データ取得エラー
```bash
# インターネット接続を確認
ping finance.yahoo.com

# yfinanceライブラリの更新
uv sync --upgrade

# キャッシュクリア
uv run python main.py --clean-cache 0
```

#### パフォーマンス改善
```bash
# ウォッチリスト銘柄数を制限（推奨: 10銘柄以下）
# 更新間隔の調整（サイドバーで設定）
# 不要なタブを閉じる
```

### ログとデバッグ

#### ログファイル確認
```bash
# ダッシュボードのログ
tail -f ~/.streamlit/logs/streamlit.log

# アプリケーションログ（実装時）
tail -f logs/app.log
```

## 📚 Python APIでの使用例

#### 税務・NISA管理

```python
from src.tax_calculation.tax_calculator import TaxCalculator
from src.tax_calculation.nisa_manager import NisaManager
from src.tax_calculation.fee_calculator import FeeCalculator

# 税務計算
tax_calc = TaxCalculator()
tax_calc.add_trade("7203", 100, 2500, "buy")   # 購入
tax_calc.add_trade("7203", 50, 2700, "sell")   # 売却
tax_result = tax_calc.calculate_taxes()
print(f"譲渡益税: {tax_result.total_tax:,.0f}円")

# NISA枠管理
nisa = NisaManager()
nisa.add_investment("成長投資枠", 500000, "2024-01-15")
remaining = nisa.get_remaining_capacity()
print(f"成長投資枠残り: {remaining['growth']:,.0f}円")

# 手数料比較
fee_calc = FeeCalculator()
comparison = fee_calc.compare_fees(1000000)  # 100万円投資
print(f"最安証券会社: {comparison['cheapest']['broker']}")
```

#### パフォーマンス追跡・学習

```python
from src.performance_tracking.performance_tracker import PerformanceTracker
from src.performance_tracking.improvement_suggestions import ImprovementSuggestionEngine

# パフォーマンス分析
tracker = PerformanceTracker()
tracker.add_trade("7203", 2500, 2700, "2024-01-15", "2024-01-20")
performance = tracker.get_comprehensive_analysis()
print(f"総合スコア: {performance.overall_score}/100")
print(f"勝率: {performance.win_rate:.1%}")

# 改善提案
suggestion_engine = ImprovementSuggestionEngine(tracker)
suggestions = suggestion_engine.generate_suggestions()
for suggestion in suggestions.high_priority:
    print(f"【高優先度】{suggestion.title}: {suggestion.description}")
```

#### 高度ファンダメンタルズ分析

```python
from src.technical_analysis.fundamental_analysis import FundamentalAnalyzer

# ファンダメンタルズ分析
analyzer = FundamentalAnalyzer("7203")
analysis = analyzer.get_comprehensive_analysis()

print(f"財務健全性スコア: {analysis.health_score}/100")
print(f"PER: {analysis.valuation_metrics.per:.2f}")
print(f"ROE: {analysis.profitability_metrics.roe:.1%}")

# 同業他社比較
comparison = analyzer.compare_with_peers(["7267", "7201"])
print(f"業界順位: {comparison.industry_rank}/{len(comparison.peers)+1}")
```

#### 投資ストーリー・シナリオ生成

```python
from src.technical_analysis.investment_story_generator import InvestmentStoryGenerator
from src.technical_analysis.integrated_analysis import IntegratedAnalyzer

# 投資ストーリー生成
story_gen = InvestmentStoryGenerator("7203")
story = story_gen.generate_comprehensive_story()

print("=== 投資ストーリー ===")
print(story.summary)
print("\n=== 3シナリオ分析 ===")
for scenario in story.scenarios:
    print(f"{scenario.name}: 目標株価 {scenario.target_price}円 (確率{scenario.probability}%)")

# 統合分析
integrated = IntegratedAnalyzer("7203")
analysis = integrated.analyze()
print(f"\n総合判断: {analysis.recommendation}")
print(f"信頼度: {analysis.confidence_score}/100")
```

#### データ収集

```python
from src.data_collector.stock_data_collector import StockDataCollector
from src.data_collector.symbol_manager import SymbolManager
from src.config.settings import settings_manager

# 初期化
collector = StockDataCollector()
symbol_manager = SymbolManager()

# 単一銘柄データ取得
data = collector.get_stock_data("7203.T", interval="1m", period="1d")

# 複数銘柄並列取得
symbols = ["7203.T", "AAPL", "MSFT"]
results = collector.get_multiple_stocks(symbols, interval="5m")

# ウォッチリスト管理
watchlist = symbol_manager.create_watchlist(
    "テック株", ["7203", "6758", "AAPL", "MSFT", "GOOGL"]
)
```

#### テクニカル分析

```python
from src.technical_analysis.indicators import TechnicalIndicators

# データ取得後にテクニカル分析
data = collector.get_stock_data("7203.T", interval="5m", period="1d")
indicators = TechnicalIndicators(data)

# 個別指標計算
rsi = indicators.rsi(14)              # RSI
macd = indicators.macd(12, 26, 9)     # MACD
bb = indicators.bollinger_bands(20, 2) # ボリンジャーバンド
vwap = indicators.vwap()              # VWAP

# 総合分析
analysis = indicators.comprehensive_analysis()
print(f"RSI: {analysis['current_values']['rsi_current']:.2f}")

# 売買シグナル判定
signals = indicators.get_trading_signals()
if signals['rsi_oversold']:
    print("RSI過売りシグナル")
if signals['macd_bullish']:
    print("MACDゴールデンクロス")
```

#### サポート・レジスタンス分析

```python
from src.technical_analysis.support_resistance import SupportResistanceDetector

# データ取得後にサポレジ分析
data = collector.get_stock_data("7203.T", interval="1h", period="1mo")
detector = SupportResistanceDetector(data, min_touches=2, tolerance_percent=0.8)

# 主要レベル検出
levels = detector.detect_support_resistance_levels(min_strength=0.3)
print(f"検出レベル数: {len(levels)}")

# ピボットポイント計算
pivots = detector.calculate_pivot_points('daily')
print(f"ピボット: {pivots.pivot:.2f}")
print(f"R1: {pivots.resistance_levels['R1']:.2f}")
print(f"S1: {pivots.support_levels['S1']:.2f}")

# ブレイクアウト検出
breakouts = detector.detect_breakouts(levels)
for breakout in breakouts:
    print(f"ブレイクアウト: {breakout.level_broken:.2f}を{breakout.direction}")

# 総合分析
analysis = detector.comprehensive_analysis()
print(f"市場状況: {analysis['market_condition']}")
print(f"推奨事項: {analysis['trading_recommendations']}")
```

## 📊 データ仕様

## 必要そうなもの

### データ収集・処理基盤

- 株価データの取得: yfinance、Alpha Vantage、QuandlなどのAPIを使った価格・出来高データの収集
- ファンダメンタルデータ: 財務諸表、業績予想、企業指標の取得
- マクロ経済指標: 金利、為替、経済統計データ
- ニュース・センチメント分析: 企業関連ニュースの収集と感情分析

### 分析・予測モデル

- テクニカル分析: 移動平均、RSI、MACD、ボリンジャーバンドなどの指標計算
- 機械学習モデル: 価格予測、トレンド分析、パターン認識
- リスク分析: VaR、シャープレシオ、相関分析
- バックテスト機能: 戦略の過去データでの検証

### MCP統合アーキテクチャ

- データソース用MCP: 各種API（株価、ニュース、経済指標）をMCPサーバとして統合
- 分析エンジン用MCP: 分析結果をClaude Codeから呼び出し可能にする
- アラート・通知システム: 投資タイミングの判定結果を通知

### 実装に必要な技術スタック

- Python: pandas, numpy, scikit-learn, tensorflow/pytorch
- データベース: PostgreSQL/SQLiteでの履歴データ管理
- 可視化: matplotlib, plotly, streamlitでのダッシュボード
- MCP開発: TypeScript/Pythonでのサーバ実装

## 最初に対応する方法はデイトレードを検討中

- リアルタイム性と短期の価格変動分析が重要

### リアルタイムデータ基盤

- 高頻度価格データ: 1分足、5分足の価格・出来高データ
- 板情報: 買い板・売り板の厚みとスプレッド分析
- 取引量分析: 異常出来高の検知、VWAP計算
- リアルタイム更新: WebSocketやストリーミングAPIの活用

### デイトレード特化の分析指標

- 短期テクニカル: EMA（9, 21）、RSI（14）、ストキャスティクス
- サポート・レジスタンス: 直近の高値・安値、ピボットポイント
- ブレイクアウト検知: 価格帯・パターンブレイクの自動検出
- モメンタム分析: 価格変化率、加速度の計算

### エントリー・エグジット判定

- エントリーシグナル: 複数指標の組み合わせ条件
- ストップロス設定: 動的なリスク管理
- 利確ポイント: リスクリワード比の最適化
- タイムアウト: 時間ベースの決済ルール

### MCP構成例
```
MCP Stock Data Server (リアルタイム価格配信)
├── MCP Technical Analysis Server (指標計算)
├── MCP Signal Generator Server (売買判定)
└── MCP Risk Manager Server (リスク管理)
```

## Claude Codeでの実行フロー

- 市況確認とウォッチリスト更新
- 各銘柄の短期分析実行
- エントリー機会の検出とアラート
- ポジション管理と利確・損切り判定

## 市況分析API

yfincanceを利用する
- 15-20分遅延（リアルタイムではない）
- 無料のためプロトタイプをこちらで作成する

## 🎯 クイックスタート

最も簡単な開始方法：

```bash
# 1. リポジトリクローン
git clone https://github.com/ryosuke-horie/py-stock.git && cd py-stock

# 2. 環境セットアップ（ダッシュボード含む）
uv sync --extra dashboard

# 3. ダッシュボード起動
uv run streamlit run dashboard/app.py
```

ブラウザで http://localhost:8501 にアクセスして、株式取引分析ダッシュボードを開始！# CI再実行のための軽微な修正
