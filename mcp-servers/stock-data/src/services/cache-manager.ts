/**
 * Cache Manager
 * 
 * SQLiteベースの効率的なデータキャッシュ管理
 */

import sqlite3 from 'sqlite3';
import { promisify } from 'util';
import fs from 'fs';
import path from 'path';

export interface CacheStatus {
  totalRecords: number;
  uniqueSymbols: number;
  latestUpdate: Date | null;
  cacheFileSize: string;
}

export interface ClearResult {
  deletedRecords: number;
  remainingRecords: number;
}

export class CacheManager {
  private db: sqlite3.Database | null = null;
  private dbPath: string;

  constructor(dbPath: string) {
    this.dbPath = dbPath;
  }

  /**
   * データベース初期化
   */
  async initialize(): Promise<void> {
    // ディレクトリ作成
    const dir = path.dirname(this.dbPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    return new Promise((resolve, reject) => {
      this.db = new sqlite3.Database(this.dbPath, (err) => {
        if (err) {
          reject(err);
          return;
        }

        this.createTables().then(resolve).catch(reject);
      });
    });
  }

  /**
   * テーブル作成
   */
  private async createTables(): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const runAsync = promisify(this.db.run.bind(this.db));

    // 価格データテーブル
    await runAsync(`
      CREATE TABLE IF NOT EXISTS price_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, timestamp)
      )
    `);

    // キャッシュメタデータテーブル
    await runAsync(`
      CREATE TABLE IF NOT EXISTS cache_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cache_key TEXT UNIQUE NOT NULL,
        symbol TEXT NOT NULL,
        data_type TEXT NOT NULL,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
        expiry_minutes INTEGER NOT NULL,
        record_count INTEGER DEFAULT 0
      )
    `);

    // インデックス作成
    await runAsync('CREATE INDEX IF NOT EXISTS idx_price_symbol_timestamp ON price_data(symbol, timestamp)');
    await runAsync('CREATE INDEX IF NOT EXISTS idx_price_timestamp ON price_data(timestamp)');
    await runAsync('CREATE INDEX IF NOT EXISTS idx_cache_key ON cache_metadata(cache_key)');
    await runAsync('CREATE INDEX IF NOT EXISTS idx_cache_symbol ON cache_metadata(symbol)');
  }

  /**
   * 価格データを保存
   */
  async storePriceData(symbol: string, data: any[]): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const runAsync = promisify(this.db.run.bind(this.db));

    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO price_data 
      (symbol, timestamp, open, high, low, close, volume)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `);

    const stmtRunAsync = promisify(stmt.run.bind(stmt));

    try {
      await runAsync('BEGIN TRANSACTION');

      for (const point of data) {
        await stmtRunAsync(
          symbol,
          point.timestamp.toISOString(),
          point.open,
          point.high,
          point.low,
          point.close,
          point.volume
        );
      }

      await runAsync('COMMIT');
    } catch (error) {
      await runAsync('ROLLBACK');
      throw error;
    } finally {
      stmt.finalize();
    }

    // キャッシュメタデータ更新
    await this.updateCacheMetadata(symbol, 'price_data', data.length);
  }

  /**
   * 最新価格データを取得
   */
  async getLatestPrice(symbol: string, maxAgeMinutes: number): Promise<any | null> {
    if (!this.db) throw new Error('Database not initialized');

    const getAsync = promisify(this.db.get.bind(this.db));

    const result = await getAsync(`
      SELECT * FROM price_data 
      WHERE symbol = ? 
        AND timestamp > datetime('now', '-${maxAgeMinutes} minutes')
      ORDER BY timestamp DESC 
      LIMIT 1
    `, [symbol]);

    return result || null;
  }

  /**
   * 履歴データを取得
   */
  async getHistoricalData(cacheKey: string, maxAgeMinutes: number): Promise<any[]> {
    if (!this.db) throw new Error('Database not initialized');

    const allAsync = promisify(this.db.all.bind(this.db));

    // キャッシュメタデータをチェック
    const metadata = await this.getCacheMetadata(cacheKey, maxAgeMinutes);
    if (!metadata) {
      return [];
    }

    // 実際のデータを取得
    const results = await allAsync(`
      SELECT * FROM price_data 
      WHERE symbol = ? 
      ORDER BY timestamp ASC
    `, [metadata.symbol]);

    return results.map(row => ({
      timestamp: new Date(row.timestamp),
      open: row.open,
      high: row.high,
      low: row.low,
      close: row.close,
      volume: row.volume,
    }));
  }

  /**
   * キャッシュメタデータを取得
   */
  private async getCacheMetadata(cacheKey: string, maxAgeMinutes: number): Promise<any | null> {
    if (!this.db) throw new Error('Database not initialized');

    const getAsync = promisify(this.db.get.bind(this.db));

    const result = await getAsync(`
      SELECT * FROM cache_metadata 
      WHERE cache_key = ? 
        AND last_updated > datetime('now', '-${maxAgeMinutes} minutes')
    `, [cacheKey]);

    return result || null;
  }

  /**
   * キャッシュメタデータを更新
   */
  private async updateCacheMetadata(symbol: string, dataType: string, recordCount: number): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const runAsync = promisify(this.db.run.bind(this.db));

    const cacheKey = `${symbol}_${dataType}`;

    await runAsync(`
      INSERT OR REPLACE INTO cache_metadata 
      (cache_key, symbol, data_type, last_updated, expiry_minutes, record_count)
      VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
    `, [cacheKey, symbol, dataType, 60, recordCount]);
  }

  /**
   * キャッシュ状態を取得
   */
  async getStatus(): Promise<CacheStatus> {
    if (!this.db) throw new Error('Database not initialized');

    const getAsync = promisify(this.db.get.bind(this.db));

    const totalRecords = await getAsync(`
      SELECT COUNT(*) as count FROM price_data
    `);

    const uniqueSymbols = await getAsync(`
      SELECT COUNT(DISTINCT symbol) as count FROM price_data
    `);

    const latestUpdate = await getAsync(`
      SELECT MAX(created_at) as latest FROM price_data
    `);

    // ファイルサイズ取得
    let cacheFileSize = 'Unknown';
    try {
      const stats = fs.statSync(this.dbPath);
      const sizeInMB = (stats.size / (1024 * 1024)).toFixed(2);
      cacheFileSize = `${sizeInMB} MB`;
    } catch (error) {
      // ファイルが存在しない場合
    }

    return {
      totalRecords: totalRecords?.count || 0,
      uniqueSymbols: uniqueSymbols?.count || 0,
      latestUpdate: latestUpdate?.latest ? new Date(latestUpdate.latest) : null,
      cacheFileSize,
    };
  }

  /**
   * 古いデータを削除
   */
  async clearOldData(olderThanDays: number): Promise<ClearResult> {
    if (!this.db) throw new Error('Database not initialized');

    const runAsync = promisify(this.db.run.bind(this.db));
    const getAsync = promisify(this.db.get.bind(this.db));

    // 削除前のレコード数
    const beforeCount = await getAsync(`SELECT COUNT(*) as count FROM price_data`);

    // 古いデータを削除
    const deleteResult = await runAsync(`
      DELETE FROM price_data 
      WHERE timestamp < datetime('now', '-${olderThanDays} days')
    `);

    // 削除後のレコード数
    const afterCount = await getAsync(`SELECT COUNT(*) as count FROM price_data`);

    // 使用されなくなったメタデータも削除
    await runAsync(`
      DELETE FROM cache_metadata 
      WHERE symbol NOT IN (SELECT DISTINCT symbol FROM price_data)
    `);

    return {
      deletedRecords: (beforeCount?.count || 0) - (afterCount?.count || 0),
      remainingRecords: afterCount?.count || 0,
    };
  }

  /**
   * データベース接続を閉じる
   */
  async close(): Promise<void> {
    if (!this.db) return;

    return new Promise((resolve, reject) => {
      this.db!.close((err) => {
        if (err) {
          reject(err);
        } else {
          this.db = null;
          resolve();
        }
      });
    });
  }
}