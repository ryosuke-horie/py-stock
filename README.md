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

## 🔧 インストールと使用方法

### セットアップ
```bash
# リポジトリクローン
git clone https://github.com/ryosuke-horie/py-stock.git
cd py-stock

# Python仮想環境作成
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# 依存関係インストール
pip install -r requirements.txt
```

### 基本的な使用例

#### 単一銘柄データ取得
```bash
# トヨタ自動車の1分足データ取得
python main.py --symbol 7203 --interval 1m

# Apple株の5分足データ取得
python main.py --symbol AAPL --interval 5m --period 1d
```

#### 複数銘柄並列取得
```bash
# 日本株と米国株のミックス
python main.py --symbols 7203 9984 AAPL MSFT GOOGL --interval 5m

# 日本テック株のバッチ取得
python main.py --symbols 7203 6758 7974 9984 6861 --interval 1m
```

#### キャッシュ管理
```bash
# キャッシュ統計表示
python main.py --cache-stats

# 7日以上古いキャッシュクリーニング
python main.py --clean-cache 7

# サンプル銘柄表示
python main.py --samples
```

### Python APIでの使用例

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