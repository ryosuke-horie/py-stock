/**
 * Stock Data Service
 * 
 * 株価データの取得・処理・キャッシュ管理を行うコアサービス
 */

import fetch from 'node-fetch';
import { CacheManager } from './cache-manager.js';
import { RateLimiter } from './rate-limiter.js';

export interface RealtimePrice {
  symbol: string;
  price: number;
  volume: number;
  change: number;
  changePercent: number;
  timestamp: Date;
  marketStatus: 'open' | 'closed' | 'pre' | 'after';
}

export interface HistoricalDataPoint {
  timestamp: Date;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HistoricalData {
  symbol: string;
  data: HistoricalDataPoint[];
  interval: string;
  period: string;
}

export class StockDataService {
  private cacheManager: CacheManager;
  private rateLimiter: RateLimiter;
  private readonly baseUrl = 'https://query1.finance.yahoo.com/v8/finance/chart';

  constructor(cacheManager: CacheManager, rateLimiter: RateLimiter) {
    this.cacheManager = cacheManager;
    this.rateLimiter = rateLimiter;
  }

  /**
   * リアルタイム価格データを取得
   */
  async getRealtimePrice(symbol: string): Promise<RealtimePrice | null> {
    try {
      // キャッシュから最新データをチェック（5分以内）
      const cachedData = await this.cacheManager.getLatestPrice(symbol, 5);
      if (cachedData) {
        return this.formatRealtimePrice(cachedData, symbol);
      }

      // Yahoo Finance APIから取得
      const data = await this.fetchFromYahoo(symbol, '1d', '1m');
      if (!data || !data.chart?.result?.[0]) {
        return null;
      }

      const result = data.chart.result[0];
      const meta = result.meta;
      const quotes = result.indicators?.quote?.[0];
      
      if (!quotes || !meta) {
        return null;
      }

      const timestamps = result.timestamp;
      const closes = quotes.close;
      const volumes = quotes.volume;

      if (!timestamps || !closes || timestamps.length === 0) {
        return null;
      }

      // 最新データポイント
      const latestIndex = timestamps.length - 1;
      const currentPrice = closes[latestIndex];
      const previousClose = meta.previousClose || closes[latestIndex - 1] || currentPrice;
      
      const realtimePrice: RealtimePrice = {
        symbol,
        price: currentPrice,
        volume: volumes?.[latestIndex] || 0,
        change: currentPrice - previousClose,
        changePercent: ((currentPrice - previousClose) / previousClose) * 100,
        timestamp: new Date(timestamps[latestIndex] * 1000),
        marketStatus: this.determineMarketStatus(meta.exchangeTimezoneName, meta.gmtoffset),
      };

      // キャッシュに保存
      await this.cacheManager.storePriceData(symbol, [{
        timestamp: realtimePrice.timestamp,
        open: currentPrice,
        high: currentPrice,
        low: currentPrice,
        close: currentPrice,
        volume: realtimePrice.volume,
      }]);

      return realtimePrice;
    } catch (error) {
      console.error(`Error fetching realtime price for ${symbol}:`, error);
      return null;
    }
  }

  /**
   * 履歴データを取得
   */
  async getHistoricalData(symbol: string, period: string, interval: string): Promise<HistoricalData | null> {
    try {
      // キャッシュから確認
      const cacheKey = `${symbol}_${period}_${interval}`;
      const cachedData = await this.cacheManager.getHistoricalData(cacheKey, this.getCacheValidityMinutes(interval));
      
      if (cachedData && cachedData.length > 0) {
        return {
          symbol,
          data: cachedData,
          interval,
          period,
        };
      }

      // Yahoo Finance APIから取得
      const data = await this.fetchFromYahoo(symbol, period, interval);
      if (!data || !data.chart?.result?.[0]) {
        return null;
      }

      const result = data.chart.result[0];
      const timestamps = result.timestamp;
      const quotes = result.indicators?.quote?.[0];

      if (!timestamps || !quotes) {
        return null;
      }

      const historicalData: HistoricalDataPoint[] = timestamps.map((timestamp: number, index: number) => ({
        timestamp: new Date(timestamp * 1000),
        open: quotes.open?.[index] || 0,
        high: quotes.high?.[index] || 0,
        low: quotes.low?.[index] || 0,
        close: quotes.close?.[index] || 0,
        volume: quotes.volume?.[index] || 0,
      })).filter(point => point.close > 0); // 無効なデータを除外

      // キャッシュに保存
      await this.cacheManager.storePriceData(symbol, historicalData);

      return {
        symbol,
        data: historicalData,
        interval,
        period,
      };
    } catch (error) {
      console.error(`Error fetching historical data for ${symbol}:`, error);
      return null;
    }
  }

  /**
   * 複数銘柄のデータを並列取得
   */
  async getMultipleSymbols(symbols: string[], interval: string = '1d'): Promise<Record<string, RealtimePrice | null>> {
    const results: Record<string, RealtimePrice | null> = {};
    
    // 並列処理で取得（レート制限を考慮して5つずつ）
    const batchSize = 5;
    for (let i = 0; i < symbols.length; i += batchSize) {
      const batch = symbols.slice(i, i + batchSize);
      
      const batchPromises = batch.map(async (symbol) => {
        await this.rateLimiter.checkLimit();
        return {
          symbol,
          data: await this.getRealtimePrice(symbol),
        };
      });

      const batchResults = await Promise.all(batchPromises);
      
      for (const result of batchResults) {
        results[result.symbol] = result.data;
      }

      // バッチ間の間隔
      if (i + batchSize < symbols.length) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }

    return results;
  }

  /**
   * Yahoo Finance APIからデータを取得
   */
  private async fetchFromYahoo(symbol: string, period: string, interval: string): Promise<any> {
    const url = `${this.baseUrl}/${symbol}?period1=0&period2=9999999999&interval=${interval}&period=${period}`;
    
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * リアルタイム価格データをフォーマット
   */
  private formatRealtimePrice(cachedData: any, symbol: string): RealtimePrice {
    return {
      symbol,
      price: cachedData.close,
      volume: cachedData.volume,
      change: cachedData.change || 0,
      changePercent: cachedData.changePercent || 0,
      timestamp: new Date(cachedData.timestamp),
      marketStatus: 'closed', // キャッシュデータの場合は市場クローズとみなす
    };
  }

  /**
   * 市場状態を判定
   */
  private determineMarketStatus(timezone: string, gmtOffset: number): 'open' | 'closed' | 'pre' | 'after' {
    const now = new Date();
    const marketTime = new Date(now.getTime() + (gmtOffset * 1000));
    const hour = marketTime.getHours();
    const minute = marketTime.getMinutes();
    const currentMinutes = hour * 60 + minute;

    // 基本的な市場時間（簡易実装）
    if (timezone.includes('Tokyo')) {
      // 東京市場: 9:00-11:30, 12:30-15:00
      if ((currentMinutes >= 540 && currentMinutes <= 690) || 
          (currentMinutes >= 750 && currentMinutes <= 900)) {
        return 'open';
      }
    } else {
      // 米国市場: 9:30-16:00 (EST)
      if (currentMinutes >= 570 && currentMinutes <= 960) {
        return 'open';
      }
    }

    return 'closed';
  }

  /**
   * インターバルに応じたキャッシュ有効期間を取得（分）
   */
  private getCacheValidityMinutes(interval: string): number {
    const intervalMinutes: Record<string, number> = {
      '1m': 2,
      '2m': 4,
      '5m': 10,
      '15m': 30,
      '30m': 60,
      '1h': 120,
      '1d': 1440, // 24時間
    };

    return intervalMinutes[interval] || 60;
  }
}