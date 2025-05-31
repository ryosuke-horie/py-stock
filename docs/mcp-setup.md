# MCP (Model Context Protocol) セットアップガイド

## 概要

py-stockは**MCP (Model Context Protocol)** を活用してClaude Codeと深く統合されています。MCPにより、Claude Codeから直接リアルタイム株価データや高度な分析機能にアクセスできます。

## MCPとは

**Model Context Protocol (MCP)** は、AIアシスタントと外部データソース・ツールを接続するためのオープンなプロトコルです。py-stockでは以下のMCPサーバを提供しています：

- **Stock Data Server**: リアルタイム株価データ取得・キャッシュ管理

## 前提条件

- Node.js 18.0以上
- Claude Code (claude.ai/code) のアクセス
- py-stockプロジェクトのセットアップ完了

## 1. MCPサーバのセットアップ

### Stock Data Server

#### インストール
```bash
cd mcp-servers/stock-data
npm install
npm run build
```

#### 動作確認
```bash
npm start
```

#### 提供機能
- **get_realtime_price**: 指定銘柄のリアルタイム価格取得
- **get_historical_data**: 履歴データ取得（1分足〜日足）
- **get_multiple_symbols**: 複数銘柄並列取得
- **cache_status**: キャッシュ状況確認
- **clear_cache**: 古いキャッシュ削除
- **validate_symbol**: 銘柄コード妥当性検証


## 2. Claude Code統合設定

### MCPサーバ設定ファイル

Claude Codeの設定ファイル (`claude_desktop_config.json`) に以下を追加：

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

### 設定ファイルの場所

#### Windows
```
%APPDATA%\Claude\claude_desktop_config.json
```

#### macOS
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

#### Linux
```
~/.config/Claude/claude_desktop_config.json
```

## 3. Claude Codeでの使用方法

### 基本的なデータ取得

```
トヨタ自動車（7203）の現在価格を教えて
```

Claude Codeが自動的に `get_realtime_price` ツールを使用して最新価格を取得します。

### 履歴データ分析

```
Appleの過去1ヶ月の日足データを取得して、トレンドを分析して
```

`get_historical_data` ツールでデータを取得し、テクニカル分析を実行します。

### 複数銘柄の比較

```
7203、9984、AAPLの現在価格を比較して
```

`get_multiple_symbols` ツールで効率的に並列取得します。


## 4. 高度な利用例

### トレーディング戦略の分析

```
以下の戦略を分析して：
1. 7203の5分足データを1日分取得
2. RSI、MACD、ボリンジャーバンドを計算
3. テクニカル指標を総合的に評価
4. 総合的な投資判断を提示
```

Claude Codeが複数のMCPツールを組み合わせて包括的な分析を実行します。

### ポートフォリオ監視

```
私のウォッチリスト銘柄（7203, 9984, AAPL, MSFT, GOOGL）について：
1. 現在価格とパフォーマンスを確認
2. テクニカル指標の状況を分析
3. 注意すべき銘柄があれば教えて
```

### リスク管理

```
保有銘柄のリスク分析を実行：
1. 各銘柄のボラティリティ（ATR）を計算
2. 相関関係を分析
3. ポートフォリオ全体のVaRを計算
4. リスク分散の改善提案をして
```

## 5. パフォーマンス最適化

### キャッシュ管理

MCPサーバは効率的なキャッシュシステムを内蔵しています：

```
キャッシュ状況を確認して、必要なら古いデータを削除して
```

Claude Codeが `cache_status` および `clear_cache` ツールを使用します。

### レート制限対応

```
大量の銘柄データ（日経225全銘柄）を効率的に取得して分析
```

MCPサーバの自動レート制限機能により、API制限を超えることなく効率的にデータを取得します。

## 6. トラブルシューティング

### よくある問題

#### MCPサーバが起動しない
```bash
# Node.jsバージョン確認
node --version  # 18.0以上必要

# 依存関係再インストール
cd mcp-servers/stock-data
npm clean-install
npm run build
```

#### Claude Codeでツールが見つからない
1. `claude_desktop_config.json` の場所とパスを確認
2. MCPサーバが正常に起動しているか確認
3. Claude Codeを再起動

#### データ取得エラー
```
銘柄コード "7203" のデータ取得で問題が発生
```

Claude Codeが `validate_symbol` ツールで銘柄コードを検証し、適切な形式を提案します。

#### ニュース取得エラー
```
NewsAPIキーが設定されているか確認
```

環境変数 `NEWS_API_KEY` が正しく設定されているかを確認してください。

### デバッグ方法

#### MCPサーバログ確認
```bash
# Stock Data Server
cd mcp-servers/stock-data
npm run dev  # 詳細ログ付きで起動

```

#### Claude Code デバッグ
Claude Codeの開発者ツールでMCP通信ログを確認できます。

## 7. カスタマイズ

### 独自MCPサーバの作成

py-stockの既存MCPサーバをベースに、独自の分析ツールを作成できます：

```typescript
// カスタム分析ツールの例
export async function customTechnicalAnalysis(params: {
  symbol: string;
  strategy: 'momentum' | 'mean_reversion' | 'breakout';
}) {
  // 独自の分析ロジック
  return {
    signal: 'buy' | 'sell' | 'hold',
    confidence: 0.85,
    reasons: ['RSI oversold', 'Volume spike']
  };
}
```

### 既存ツールの拡張

```typescript
// get_historical_data の拡張例
export async function getEnhancedHistoricalData(params: {
  symbol: string;
  includeIndicators?: boolean;
  customPeriod?: string;
}) {
  const data = await getHistoricalData(params);
  
  if (params.includeIndicators) {
    // テクニカル指標を自動計算
    data.technicalIndicators = calculateIndicators(data.prices);
  }
  
  return data;
}
```

## 8. セキュリティ考慮事項

### APIキー管理
- 環境変数でAPIキーを管理
- 設定ファイルにAPIキーを直接記載しない
- 必要最小限の権限のみを付与

### データプライバシー
- 取引データはローカルに保存
- 外部への不要なデータ送信を避ける
- キャッシュデータの定期的な削除

## 次のステップ

1. [高度な使用例](advanced-usage.md) - 複雑な分析パターン
2. [カスタムツール開発](custom-tools.md) - 独自機能の追加
3. [パフォーマンス調整](performance.md) - 最適化技術

## サポート

MCP関連の問題：
1. [MCPトラブルシューティング](troubleshooting.md#mcp)を確認
2. [GitHub Discussions](https://github.com/ryosuke-horie/py-stock/discussions)で質問
3. Claude Codeの[公式ドキュメント](https://docs.anthropic.com/claude-code)を参照