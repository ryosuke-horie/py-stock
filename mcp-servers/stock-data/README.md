# MCP Stock Data Server

株価データの取得・配信・キャッシュ管理を担当するMCPサーバです。Claude Codeから直接アクセス可能なリアルタイム株式データサービスを提供します。

## 機能概要

### 🔄 リアルタイムデータ取得
- Yahoo Finance APIを通じた最新株価データ取得
- 日本株・米国株の両方に対応
- 市場状態の自動判定

### 💾 効率的なキャッシュ管理
- SQLiteベースの高速データストレージ
- 自動的なデータ有効期限管理
- 重複データの自動除去

### 🔧 銘柄コード正規化
- 日本株・米国株の銘柄コード統一化
- 入力ミスの自動修正提案
- 銘柄名の自動取得

### ⚡ レート制限管理
- API呼び出し制限の自動管理
- 効率的な並列データ取得
- オーバーロード防止

## 提供ツール

### get_realtime_price
指定銘柄のリアルタイム価格データを取得します。

**パラメータ:**
- `symbol` (string): 銘柄コード (例: "7203.T", "AAPL")

**戻り値:**
```json
{
  "symbol": "7203.T",
  "price": 2150.50,
  "volume": 1250000,
  "change": 25.50,
  "changePercent": 1.20,
  "timestamp": "2024-01-15T09:30:00.000Z",
  "marketStatus": "open"
}
```

### get_historical_data
指定銘柄の履歴データを取得します。

**パラメータ:**
- `symbol` (string): 銘柄コード
- `period` (string, optional): 取得期間 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y)
- `interval` (string, optional): データ間隔 (1m, 2m, 5m, 15m, 30m, 1h, 1d)

**戻り値:**
```json
{
  "symbol": "7203.T",
  "period": "1mo",
  "interval": "1d",
  "dataPoints": 22,
  "data": [
    {
      "timestamp": "2024-01-01T00:00:00.000Z",
      "open": 2100.00,
      "high": 2150.00,
      "low": 2090.00,
      "close": 2140.00,
      "volume": 1100000
    }
  ],
  "summary": {
    "firstDate": "2024-01-01T00:00:00.000Z",
    "lastDate": "2024-01-31T00:00:00.000Z",
    "priceRange": {
      "min": 2050.00,
      "max": 2200.00
    }
  }
}
```

### get_multiple_symbols
複数銘柄のデータを並列取得します。

**パラメータ:**
- `symbols` (string[]): 銘柄コードの配列
- `interval` (string, optional): データ間隔

**戻り値:**
```json
{
  "totalSymbols": 3,
  "successfulSymbols": 2,
  "failedSymbols": ["INVALID"],
  "data": {
    "7203.T": { /* 価格データ */ },
    "AAPL": { /* 価格データ */ },
    "INVALID": null
  }
}
```

### cache_status
キャッシュの状態を確認します。

**戻り値:**
```json
{
  "totalRecords": 15420,
  "uniqueSymbols": 125,
  "latestUpdate": "2024-01-15T10:30:00.000Z",
  "cacheFileSize": "2.35 MB",
  "memoryUsage": {
    "rss": 45678912,
    "heapTotal": 32456789,
    "heapUsed": 28123456
  },
  "uptime": 3600
}
```

### clear_cache
古いキャッシュデータを削除します。

**パラメータ:**
- `olderThanDays` (number, optional): 削除対象日数 (デフォルト: 30)

**戻り値:**
```json
{
  "message": "Cache cleared successfully",
  "deletedRecords": 2340,
  "olderThanDays": 30,
  "remainingRecords": 13080
}
```

### validate_symbol
銘柄コードの妥当性を検証します。

**パラメータ:**
- `symbol` (string): 検証する銘柄コード

**戻り値:**
```json
{
  "symbol": "7203",
  "isValid": true,
  "normalizedSymbol": "7203.T",
  "marketType": "japan",
  "suggestions": ["7203.T: トヨタ自動車"],
  "errors": []
}
```

## インストール・設定

### 1. 依存関係のインストール
```bash
cd mcp-servers/stock-data
npm install
```

### 2. TypeScriptのコンパイル
```bash
npm run build
```

### 3. Claude Code設定
`claude_desktop_config.json`に以下を追加:

```json
{
  "mcpServers": {
    "stock-data": {
      "command": "node",
      "args": ["./mcp-servers/stock-data/dist/index.js"],
      "env": {
        "NODE_ENV": "production"
      }
    }
  }
}
```

### 4. サーバー起動
```bash
npm start
```

## 開発・テスト

### 開発モード起動
```bash
npm run dev
```

### テスト実行
```bash
npm test
```

## アーキテクチャ

```
stock-data-server/
├── src/
│   ├── index.ts              # メインサーバー
│   └── services/
│       ├── stock-data-service.ts    # データ取得サービス
│       ├── cache-manager.ts         # キャッシュ管理
│       ├── symbol-validator.ts      # 銘柄コード検証
│       └── rate-limiter.ts          # レート制限
├── data/                     # SQLiteデータベース
├── dist/                     # コンパイル済みJavaScript
└── package.json
```

## データフロー

1. **リクエスト受信**: Claude CodeからMCPプロトコル経由
2. **銘柄コード正規化**: SymbolValidatorで統一形式に変換
3. **キャッシュ確認**: CacheManagerで既存データをチェック
4. **データ取得**: 必要に応じてYahoo Finance APIから取得
5. **データ保存**: 新しいデータをSQLiteキャッシュに保存
6. **レスポンス返却**: 統一フォーマットでデータを返却

## エラーハンドリング

- **無効な銘柄コード**: 適切なエラーメッセージと修正提案
- **API制限**: 自動的な待機とリトライ機能
- **ネットワークエラー**: タイムアウトとフォールバック処理
- **データベースエラー**: トランザクション管理と整合性保証

## パフォーマンス最適化

- **多層キャッシュ**: メモリ + SQLite
- **並列処理**: 複数銘柄の効率的な取得
- **データ圧縮**: 不要なデータの自動削除
- **インデックス最適化**: SQLiteクエリの高速化

## セキュリティ

- **入力検証**: 全パラメータのZodバリデーション
- **SQLインジェクション対策**: Prepared Statementの使用
- **レート制限**: DDoS攻撃の防止
- **エラー情報の制御**: 機密情報の漏洩防止

## トラブルシューティング

### よくある問題

1. **"Symbol not found"エラー**
   - 銘柄コードのスペルを確認
   - `validate_symbol`ツールで検証

2. **"Rate limit exceeded"エラー**
   - 自動的に待機するため、しばらく待機
   - 並列リクエスト数を減らす

3. **キャッシュサイズが大きい**
   - `clear_cache`ツールで古いデータを削除
   - より短い期間を指定

### ログ確認
```bash
# サーバーログの確認
tail -f logs/stock-data-server.log

# SQLiteデータベースの直接確認
sqlite3 data/stock_cache.db ".tables"
```

## 今後の拡張予定

- [ ] Webソケット対応（リアルタイムストリーミング）
- [ ] 他データプロバイダーとの統合
- [ ] 高度なキャッシュ戦略
- [ ] メトリクス・監視機能
- [ ] 分散キャッシュ対応