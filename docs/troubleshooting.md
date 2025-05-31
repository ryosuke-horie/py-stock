# トラブルシューティングガイド

## 一般的な問題と解決方法

### 🚀 セットアップ関連

#### uvが見つからない
```bash
# uvのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# または pipでインストール
pip install uv

# パス確認
which uv
```

#### 依存関係インストール失敗
```bash
# キャッシュクリア
uv cache clean

# 依存関係再インストール
uv sync --extra dashboard

# Python バージョン確認（3.10以上必要）
python --version
```

#### 権限エラー（Windows）
```powershell
# 管理者権限でPowerShellを起動
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# uvインストール後にパスを確認
$env:PATH
```

### 📊 ダッシュボード関連

#### Streamlitが起動しない
```bash
# 基本診断
uv run python -c "import streamlit; print('OK')"

# ポート変更
uv run streamlit run dashboard/app.py --server.port 8502

# ブラウザ自動起動無効化
uv run streamlit run dashboard/app.py --server.headless true
```

#### モジュールインポートエラー
```bash
# 依存関係確認
uv pip list | grep streamlit

# Streamlit関連パッケージの再インストール
uv sync --extra dashboard --reinstall-package streamlit
```

#### ダッシュボードが遅い
**原因**: ウォッチリスト銘柄数過多、更新間隔短すぎ

**解決策**:
1. ウォッチリスト銘柄を10銘柄以下に制限
2. 更新間隔を60秒以上に設定
3. 使用していないタブを閉じる
4. ブラウザキャッシュをクリア

#### チャートが表示されない
```bash
# plotly インストール確認
uv run python -c "import plotly; print('OK')"

# plotly 再インストール
uv sync --reinstall-package plotly
```

### 💾 データ取得関連

#### 株価データ取得エラー
```bash
# ネットワーク接続確認
ping finance.yahoo.com

# yfinance テスト
uv run python -c "import yfinance as yf; print(yf.download('AAPL', period='1d'))"

# キャッシュクリア
uv run python main.py --clean-cache 0
```

#### 銘柄コードエラー
**よくある間違い**:
- `7203` → `7203.T` (日本株にはサフィックス必要)
- `apple` → `AAPL` (正式ティッカー使用)
- `トヨタ` → `7203.T` (日本語名では検索不可)

**解決法**:
```bash
# 銘柄コード検証
uv run python main.py --symbol 7203  # 自動で 7203.T に変換される
```

#### API制限エラー
**原因**: yfinance の呼び出し頻度制限

**解決策**:
1. 取得間隔を空ける（最低30秒）
2. 同時取得銘柄数を減らす（最大10銘柄）
3. キャッシュを有効活用

```bash
# キャッシュ状況確認
uv run python main.py --cache-stats
```

### 🤖 MCP統合関連

#### MCPサーバが起動しない
```bash
# Node.js バージョン確認（18.0以上必要）
node --version

# MCP サーバビルド
cd mcp-servers/stock-data
npm clean-install
npm run build
npm start
```

#### Claude CodeでMCPツールが見つからない
**チェック項目**:
1. `claude_desktop_config.json` の場所確認
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. 設定ファイル内容確認:
```json
{
  "mcpServers": {
    "stock-data": {
      "command": "node",
      "args": ["./mcp-servers/stock-data/dist/index.js"]
    }
  }
}
```

3. Claude Code再起動

#### MCPサーバのパスエラー
```bash
# 絶対パス使用
{
  "command": "node",
  "args": ["/full/path/to/py-stock/mcp-servers/stock-data/dist/index.js"]
}

# または現在ディレクトリからの相対パス確認
pwd
ls -la mcp-servers/stock-data/dist/index.js
```

#### NewsAPI関連エラー
```bash
# 環境変数確認
echo $NEWS_API_KEY

# 環境変数設定
export NEWS_API_KEY="your-api-key"

# または設定ファイルで指定
{
  "mcpServers": {
    "news-analysis": {
      "env": {
        "NEWS_API_KEY": "your-api-key"
      }
    }
  }
}
```

### 📈 分析機能関連

#### テクニカル指標計算エラー
**原因**: データ不足、NaN値の存在

```python
# データ確認
import pandas as pd
data = collector.get_stock_data("7203.T", interval="1d", period="1mo")
print(f"データ数: {len(data)}")
print(f"NaN値: {data.isnull().sum()}")

# データクリーニング
data = data.dropna()
```

#### サポレジ検出で結果なし
**原因**: データ期間短すぎ、タッチ回数設定厳しすぎ

```python
# パラメータ調整
detector = SupportResistanceDetector(
    data, 
    min_touches=2,  # デフォルト: 3
    tolerance_percent=1.0  # デフォルト: 0.5
)
```

#### パフォーマンス追跡で空の結果
**原因**: 取引履歴データ未入力

```python
# サンプルデータで動作確認
tracker = PerformanceTracker()
tracker.add_sample_trades()  # テスト用データ追加
performance = tracker.get_comprehensive_analysis()
```

### 💰 税務計算関連

#### NISA枠計算が間違っている
**チェック項目**:
1. 投資年度の確認（年をまたぐ計算）
2. 枠の種類確認（成長投資枠 vs つみたて投資枠）
3. 既投資額の正確性

```python
# デバッグ用詳細出力
nisa = NisaManager()
print(nisa.get_detailed_status())
```

#### 税務計算の不一致
**原因**: FIFO管理の理解不足、取引日の重複

```python
# 取引履歴確認
tax_calc = TaxCalculator()
print(tax_calc.get_trade_history())

# 手動検証
tax_calc.calculate_taxes(debug=True)
```

### 🔍 デバッグ・ログ確認

#### アプリケーションログ
```bash
# Streamlit ログ
tail -f ~/.streamlit/logs/streamlit.log

# MCP サーバログ（開発モード）
cd mcp-servers/stock-data
npm run dev
```

#### Python デバッグ
```python
# ログレベル設定
import logging
logging.basicConfig(level=logging.DEBUG)

# 詳細エラー情報
import traceback
try:
    # 問題のコード
    pass
except Exception as e:
    traceback.print_exc()
```

#### ネットワーク診断
```bash
# DNS解決確認
nslookup finance.yahoo.com

# HTTPSアクセス確認
curl -I https://finance.yahoo.com

# プロキシ環境の場合
export https_proxy=http://your-proxy:port
```

## パフォーマンス最適化

### メモリ使用量削減
```python
# 大量データ処理時
import gc

# 不要オブジェクト削除
del large_dataframe
gc.collect()

# データフレームサイズ制限
data = data.tail(1000)  # 最新1000行のみ使用
```

### レスポンス時間改善
1. **キャッシュ活用**: 同じデータの重複取得を避ける
2. **並列処理**: 複数銘柄の同時取得
3. **データ制限**: 過度に長期間データを避ける

```bash
# キャッシュ効率確認
uv run python main.py --cache-stats
```

## よくある質問 (FAQ)

### Q: リアルタイムデータは取得できますか？
A: yfinanceは15-20分遅延データです。リアルタイム性が必要な場合は、有料APIの利用を検討してください。

### Q: 対応証券会社はありますか？
A: py-stockは分析ツールであり、実際の取引機能はありません。分析結果を基に、お使いの証券会社で取引を行ってください。

### Q: 他の国の株式は対応していますか？
A: 現在は日本株・米国株のみ対応。yfinanceが対応している範囲で拡張可能です。

### Q: バックテスト結果の精度は？
A: 過去データに基づく理論値です。実際の取引では手数料・スリッページ・流動性を考慮してください。

### Q: 商用利用は可能ですか？
A: MITライセンスにより商用利用可能ですが、投資顧問業等には適切な許可が必要です。

## エラーメッセージ別対処法

### `ModuleNotFoundError: No module named 'streamlit'`
```bash
uv sync --extra dashboard
```

### `yfinance.exceptions.YFinanceError`
```bash
# yfinance更新
uv sync --upgrade

# 銘柄コード確認
uv run python main.py --symbol AAPL --validate
```

### `Connection refused` (MCP)
```bash
# MCPサーバ起動確認
cd mcp-servers/stock-data
npm start

# ポート確認
netstat -an | grep 3000
```

### `Permission denied` (ファイルアクセス)
```bash
# ディレクトリ権限確認
ls -la cache/
chmod 755 cache/

# SQLiteファイル権限
chmod 664 cache/*.db
```

## サポート連絡先

解決しない問題については：

1. **[GitHub Issues](https://github.com/ryosuke-horie/py-stock/issues)** - バグ報告
2. **[GitHub Discussions](https://github.com/ryosuke-horie/py-stock/discussions)** - 質問・議論
3. **[Claude Code コミュニティ](https://docs.anthropic.com/claude-code)** - MCP関連

報告時には以下の情報を含めてください：
- OS・Pythonバージョン
- エラーメッセージの全文
- 再現手順
- 期待する動作vs実際の動作