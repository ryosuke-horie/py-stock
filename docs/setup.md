# セットアップガイド

## 前提条件

- Python 3.10以上
- [uv](https://docs.astral.sh/uv/) (Pythonパッケージ管理ツール)
- Git

## 1. リポジトリのクローン

```bash
git clone https://github.com/ryosuke-horie/py-stock.git
cd py-stock
```

## 2. 仮想環境セットアップ

### 基本インストール（CLI利用のみ）
```bash
uv sync
```

### ダッシュボード利用（推奨）
```bash
uv sync --extra dashboard
```

### 開発用（全機能込み）
```bash
uv sync --extra all
```

## 3. 設定ファイル

設定は以下の方法で管理できます：

### デフォルト設定を使用
特に設定不要。デフォルト値で動作します。

### カスタム設定（オプション）
`config/settings.json` ファイルを作成してカスタマイズ：

```json
{
  "data_sources": {
    "yfinance": {
      "timeout": 10,
      "retry_count": 3
    }
  },
  "cache": {
    "enabled": true,
    "directory": "cache",
    "max_age_hours": 24
  },
  "watchlist": {
    "default_symbols": ["7203", "9984", "AAPL", "MSFT"],
    "max_symbols": 20
  }
}
```

## 4. 動作確認

### CLI動作確認
```bash
# 基本データ取得テスト
uv run python main.py --symbol 7203 --interval 1m

# テクニカル分析テスト
uv run python main.py --technical 7203 --interval 5m

# ヘルプ表示
uv run python main.py --help
```

### ダッシュボード動作確認
```bash
# ダッシュボード起動
uv run streamlit run dashboard/app.py

# または仮想環境をアクティベートしてから
uv shell
streamlit run dashboard/app.py
```

ブラウザで http://localhost:8501 にアクセス

## 5. トラブルシューティング

### よくある問題と解決方法

#### uv が見つからない
```bash
# uvのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# または
pip install uv
```

#### モジュールが見つからないエラー
```bash
# 依存関係の再インストール
uv sync --extra dashboard

# キャッシュクリア
uv cache clean
```

#### ダッシュボードが起動しない
```bash
# ポート変更
uv run streamlit run dashboard/app.py --server.port 8502

# 依存関係確認
uv sync --extra dashboard
```

#### データ取得エラー
```bash
# インターネット接続確認
ping finance.yahoo.com

# キャッシュクリア
uv run python main.py --clean-cache 0
```

## 6. 開発環境セットアップ（開発者向け）

### 開発用ツールインストール
```bash
uv sync --extra all
```

### テスト実行
```bash
# 全テスト実行
uv run pytest

# 特定テスト実行
uv run pytest tests/test_specific.py

# カバレッジ付きテスト
uv run pytest --cov=src tests/
```

### コード品質チェック
```bash
# フォーマット
uv run black .

# リンティング
uv run flake8 .

# 型チェック
uv run mypy .
```

## 次のステップ

セットアップが完了したら：

1. [操作ガイド](usage.md) - 基本的な使い方を学ぶ
2. [MCP セットアップ](mcp-setup.md) - Claude統合を設定する
3. [ダッシュボードガイド](dashboard.md) - ダッシュボードの詳細な使い方

## サポート

問題が発生した場合：

1. [トラブルシューティング](troubleshooting.md)を確認
2. [GitHub Issues](https://github.com/ryosuke-horie/py-stock/issues)で報告
3. [ディスカッション](https://github.com/ryosuke-horie/py-stock/discussions)で質問