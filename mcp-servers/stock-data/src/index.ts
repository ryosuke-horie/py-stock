#!/usr/bin/env node

/**
 * MCP Stock Data Server
 * 
 * 株価データの取得・配信・キャッシュ管理を担当するMCPサーバ
 * Claude Codeから直接アクセス可能なリアルタイム株式データサービス
 */

import { Server } from '@anthropic-ai/mcp-server';
import { StdioServerTransport } from '@anthropic-ai/mcp-server/stdio';
import { z } from 'zod';
import { StockDataService } from './services/stock-data-service.js';
import { CacheManager } from './services/cache-manager.js';
import { SymbolValidator } from './services/symbol-validator.js';
import { RateLimiter } from './services/rate-limiter.js';

// 入力データのバリデーションスキーマ
const GetRealtimePriceSchema = z.object({
  symbol: z.string().min(1, 'Symbol is required'),
});

const GetHistoricalDataSchema = z.object({
  symbol: z.string().min(1, 'Symbol is required'),
  period: z.string().default('1mo'),
  interval: z.string().default('1d'),
});

const GetMultipleSymbolsSchema = z.object({
  symbols: z.array(z.string()).min(1, 'At least one symbol is required'),
  interval: z.string().default('1d'),
});

const ClearCacheSchema = z.object({
  olderThanDays: z.number().optional(),
});

const ValidateSymbolSchema = z.object({
  symbol: z.string().min(1, 'Symbol is required'),
});

class StockDataMCPServer {
  private server: Server;
  private stockDataService: StockDataService;
  private cacheManager: CacheManager;
  private symbolValidator: SymbolValidator;
  private rateLimiter: RateLimiter;

  constructor() {
    this.server = new Server({
      name: 'mcp-stock-data',
      version: '1.0.0',
    }, {
      capabilities: {
        tools: {},
      },
    });

    // サービス初期化
    this.cacheManager = new CacheManager('./data/stock_cache.db');
    this.rateLimiter = new RateLimiter();
    this.symbolValidator = new SymbolValidator();
    this.stockDataService = new StockDataService(
      this.cacheManager,
      this.rateLimiter
    );

    this.setupTools();
    this.setupErrorHandling();
  }

  private setupTools() {
    // リアルタイム価格取得ツール
    this.server.setRequestHandler('tools/call', async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'get_realtime_price':
            return await this.getRealtimePrice(args);
          
          case 'get_historical_data':
            return await this.getHistoricalData(args);
          
          case 'get_multiple_symbols':
            return await this.getMultipleSymbols(args);
          
          case 'cache_status':
            return await this.getCacheStatus();
          
          case 'clear_cache':
            return await this.clearCache(args);
          
          case 'validate_symbol':
            return await this.validateSymbol(args);
          
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        console.error(`Error executing tool ${name}:`, error);
        return {
          content: [{
            type: 'text',
            text: `Error: ${error.message}`,
          }],
          isError: true,
        };
      }
    });

    // 利用可能なツールの定義
    this.server.setRequestHandler('tools/list', async () => {
      return {
        tools: [
          {
            name: 'get_realtime_price',
            description: '指定銘柄のリアルタイム価格データを取得',
            inputSchema: {
              type: 'object',
              properties: {
                symbol: {
                  type: 'string',
                  description: '銘柄コード (例: 7203.T, AAPL)',
                },
              },
              required: ['symbol'],
            },
          },
          {
            name: 'get_historical_data',
            description: '指定銘柄の履歴データを取得',
            inputSchema: {
              type: 'object',
              properties: {
                symbol: {
                  type: 'string',
                  description: '銘柄コード (例: 7203.T, AAPL)',
                },
                period: {
                  type: 'string',
                  description: '取得期間 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y)',
                  default: '1mo',
                },
                interval: {
                  type: 'string',
                  description: 'データ間隔 (1m, 2m, 5m, 15m, 30m, 1h, 1d)',
                  default: '1d',
                },
              },
              required: ['symbol'],
            },
          },
          {
            name: 'get_multiple_symbols',
            description: '複数銘柄のデータを並列取得',
            inputSchema: {
              type: 'object',
              properties: {
                symbols: {
                  type: 'array',
                  items: { type: 'string' },
                  description: '銘柄コードの配列',
                },
                interval: {
                  type: 'string',
                  description: 'データ間隔',
                  default: '1d',
                },
              },
              required: ['symbols'],
            },
          },
          {
            name: 'cache_status',
            description: 'キャッシュの状態を確認',
            inputSchema: {
              type: 'object',
              properties: {},
            },
          },
          {
            name: 'clear_cache',
            description: '古いキャッシュデータを削除',
            inputSchema: {
              type: 'object',
              properties: {
                olderThanDays: {
                  type: 'number',
                  description: '指定日数より古いデータを削除 (デフォルト: 30日)',
                },
              },
            },
          },
          {
            name: 'validate_symbol',
            description: '銘柄コードの妥当性を検証',
            inputSchema: {
              type: 'object',
              properties: {
                symbol: {
                  type: 'string',
                  description: '検証する銘柄コード',
                },
              },
              required: ['symbol'],
            },
          },
        ],
      };
    });
  }

  private async getRealtimePrice(args: any) {
    const { symbol } = GetRealtimePriceSchema.parse(args);
    
    // 銘柄コード正規化
    const normalizedSymbol = this.symbolValidator.normalizeSymbol(symbol);
    
    // レート制限チェック
    await this.rateLimiter.checkLimit();
    
    // データ取得
    const priceData = await this.stockDataService.getRealtimePrice(normalizedSymbol);
    
    if (!priceData) {
      throw new Error(`Price data not available for symbol: ${symbol}`);
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          symbol: priceData.symbol,
          price: priceData.price,
          volume: priceData.volume,
          change: priceData.change,
          changePercent: priceData.changePercent,
          timestamp: priceData.timestamp,
          marketStatus: priceData.marketStatus,
        }, null, 2),
      }],
    };
  }

  private async getHistoricalData(args: any) {
    const { symbol, period, interval } = GetHistoricalDataSchema.parse(args);
    
    const normalizedSymbol = this.symbolValidator.normalizeSymbol(symbol);
    await this.rateLimiter.checkLimit();
    
    const historicalData = await this.stockDataService.getHistoricalData(
      normalizedSymbol,
      period,
      interval
    );
    
    if (!historicalData || historicalData.data.length === 0) {
      throw new Error(`Historical data not available for symbol: ${symbol}`);
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          symbol: historicalData.symbol,
          period: historicalData.period,
          interval: historicalData.interval,
          dataPoints: historicalData.data.length,
          data: historicalData.data.slice(-50), // 最新50件のみ表示
          summary: {
            firstDate: historicalData.data[0]?.timestamp,
            lastDate: historicalData.data[historicalData.data.length - 1]?.timestamp,
            priceRange: {
              min: Math.min(...historicalData.data.map(d => d.low)),
              max: Math.max(...historicalData.data.map(d => d.high)),
            },
          },
        }, null, 2),
      }],
    };
  }

  private async getMultipleSymbols(args: any) {
    const { symbols, interval } = GetMultipleSymbolsSchema.parse(args);
    
    // 銘柄コード正規化
    const normalizedSymbols = symbols.map(s => this.symbolValidator.normalizeSymbol(s));
    
    // 並列データ取得
    const results = await this.stockDataService.getMultipleSymbols(
      normalizedSymbols,
      interval
    );
    
    const summary = {
      totalSymbols: symbols.length,
      successfulSymbols: Object.keys(results).filter(s => results[s] !== null).length,
      failedSymbols: Object.keys(results).filter(s => results[s] === null),
      data: results,
    };

    return {
      content: [{
        type: 'text',
        text: JSON.stringify(summary, null, 2),
      }],
    };
  }

  private async getCacheStatus() {
    const status = await this.cacheManager.getStatus();
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          totalRecords: status.totalRecords,
          uniqueSymbols: status.uniqueSymbols,
          latestUpdate: status.latestUpdate,
          cacheFileSize: status.cacheFileSize,
          memoryUsage: process.memoryUsage(),
          uptime: process.uptime(),
        }, null, 2),
      }],
    };
  }

  private async clearCache(args: any) {
    const { olderThanDays = 30 } = ClearCacheSchema.parse(args);
    
    const result = await this.cacheManager.clearOldData(olderThanDays);
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          message: `Cache cleared successfully`,
          deletedRecords: result.deletedRecords,
          olderThanDays,
          remainingRecords: result.remainingRecords,
        }, null, 2),
      }],
    };
  }

  private async validateSymbol(args: any) {
    const { symbol } = ValidateSymbolSchema.parse(args);
    
    const validation = this.symbolValidator.validateSymbol(symbol);
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          symbol,
          isValid: validation.isValid,
          normalizedSymbol: validation.normalizedSymbol,
          marketType: validation.marketType,
          suggestions: validation.suggestions,
          errors: validation.errors,
        }, null, 2),
      }],
    };
  }

  private setupErrorHandling() {
    process.on('uncaughtException', (error) => {
      console.error('Uncaught Exception:', error);
      process.exit(1);
    });

    process.on('unhandledRejection', (reason, promise) => {
      console.error('Unhandled Rejection at:', promise, 'reason:', reason);
      process.exit(1);
    });
  }

  async start() {
    // データベース初期化
    await this.cacheManager.initialize();
    
    console.log('MCP Stock Data Server starting...');
    
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    
    console.log('MCP Stock Data Server running');
  }
}

// サーバー起動
if (import.meta.url === `file://${process.argv[1]}`) {
  const server = new StockDataMCPServer();
  server.start().catch((error) => {
    console.error('Failed to start server:', error);
    process.exit(1);
  });
}

export { StockDataMCPServer };