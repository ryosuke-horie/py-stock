from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import sqlite3
from pathlib import Path
import time
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class StockDataCollector:
    """
    株価データ取得・管理クラス
    複数銘柄の1分足・5分足データを効率的に取得し、SQLiteにキャッシュする
    """
    
    def __init__(self, cache_dir: str = "cache", max_workers: int = 5):
        """
        初期化
        
        Args:
            cache_dir: キャッシュディレクトリパス
            max_workers: 並列処理のワーカー数
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = self.cache_dir / "stock_data.db"
        self.max_workers = max_workers
        
        # データベース初期化
        self._init_database()
        
        # レート制限管理
        self._last_request_time = 0
        self._request_lock = threading.Lock()
        self.min_request_interval = 0.1  # 100ms間隔
    
    def _init_database(self):
        """SQLiteデータベース初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_data (
                    symbol TEXT,
                    interval TEXT,
                    timestamp TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    created_at TEXT,
                    PRIMARY KEY (symbol, interval, timestamp)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_interval_time 
                ON stock_data(symbol, interval, timestamp)
            """)
    
    def _rate_limit(self):
        """レート制限の実装"""
        with self._request_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            if time_since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last
                time.sleep(sleep_time)
            self._last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _fetch_data_yfinance(
        self, 
        symbol: str, 
        interval: str = "1m",
        period: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        yfinanceを使用してデータ取得（リトライ機能付き）
        
        Args:
            symbol: 銘柄コード
            interval: データ間隔 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            period: 取得期間 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        
        Returns:
            株価データのDataFrame
        """
        try:
            self._rate_limit()
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"データが取得できませんでした: {symbol}")
                return None
            
            # インデックスをリセットしてtimestampカラムに
            data.reset_index(inplace=True)
            
            # カラム名を標準化
            column_mapping = {
                'Datetime': 'timestamp',
                'Date': 'timestamp',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }
            data.rename(columns=column_mapping, inplace=True)
            
            # 追加情報
            data['symbol'] = symbol
            data['interval'] = interval
            data['created_at'] = datetime.now().isoformat()
            
            logger.info(f"データ取得成功: {symbol} ({len(data)}件)")
            return data
            
        except Exception as e:
            logger.error(f"データ取得エラー {symbol}: {str(e)}")
            raise
    
    def _save_to_cache(self, data: pd.DataFrame):
        """データをSQLiteキャッシュに保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # timestampを文字列に変換
                data_copy = data.copy()
                data_copy['timestamp'] = data_copy['timestamp'].astype(str)
                
                # REPLACE INTOで重複データを上書き
                data_copy.to_sql('stock_data', conn, if_exists='append', 
                               index=False, method='multi')
                
                logger.debug(f"キャッシュ保存完了: {data['symbol'].iloc[0]} ({len(data)}件)")
                
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {str(e)}")
    
    def _load_from_cache(
        self, 
        symbol: str, 
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """キャッシュからデータを読み込み"""
        try:
            query = """
                SELECT * FROM stock_data 
                WHERE symbol = ? AND interval = ?
            """
            params = [symbol, interval]
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            query += " ORDER BY timestamp"
            
            with sqlite3.connect(self.db_path) as conn:
                data = pd.read_sql_query(query, conn, params=params)
                
                if data.empty:
                    return None
                
                # timestampをdatetimeに変換
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                
                logger.debug(f"キャッシュ読み込み: {symbol} ({len(data)}件)")
                return data
                
        except Exception as e:
            logger.error(f"キャッシュ読み込みエラー: {str(e)}")
            return None
    
    def get_stock_data(
        self,
        symbol: str,
        interval: str = "1m",
        period: str = "1d",
        use_cache: bool = True,
        cache_expire_hours: int = 1
    ) -> Optional[pd.DataFrame]:
        """
        株価データ取得（キャッシュ機能付き）
        
        Args:
            symbol: 銘柄コード
            interval: データ間隔
            period: 取得期間
            use_cache: キャッシュ使用フラグ
            cache_expire_hours: キャッシュ有効期限（時間）
        
        Returns:
            株価データのDataFrame
        """
        cached_data = None
        
        if use_cache:
            cached_data = self._load_from_cache(symbol, interval)
            
            if cached_data is not None:
                # キャッシュの有効期限チェック
                latest_cache_time = pd.to_datetime(cached_data['created_at'].iloc[-1])
                if datetime.now() - latest_cache_time < timedelta(hours=cache_expire_hours):
                    logger.info(f"キャッシュデータを使用: {symbol}")
                    return cached_data
        
        # 新しいデータを取得
        fresh_data = self._fetch_data_yfinance(symbol, interval, period)
        
        if fresh_data is not None and use_cache:
            self._save_to_cache(fresh_data)
        
        return fresh_data
    
    def get_multiple_stocks(
        self,
        symbols: List[str],
        interval: str = "1m",
        period: str = "1d",
        use_cache: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        複数銘柄のデータを並列取得
        
        Args:
            symbols: 銘柄コードのリスト
            interval: データ間隔
            period: 取得期間
            use_cache: キャッシュ使用フラグ
        
        Returns:
            銘柄コードをキーとした株価データの辞書
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 並列でデータ取得タスクを実行
            future_to_symbol = {
                executor.submit(
                    self.get_stock_data, 
                    symbol, interval, period, use_cache
                ): symbol
                for symbol in symbols
            }
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    data = future.result()
                    if data is not None:
                        results[symbol] = data
                    else:
                        logger.warning(f"データ取得失敗: {symbol}")
                except Exception as e:
                    logger.error(f"並列処理エラー {symbol}: {str(e)}")
        
        logger.info(f"複数銘柄取得完了: {len(results)}/{len(symbols)}")
        return results
    
    def clear_cache(self, symbol: Optional[str] = None, older_than_days: int = 30):
        """
        キャッシュクリア
        
        Args:
            symbol: 特定銘柄のみクリア（Noneの場合は全て）
            older_than_days: 指定日数より古いデータをクリア
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cutoff_date = (datetime.now() - timedelta(days=older_than_days)).isoformat()
                
                if symbol:
                    conn.execute(
                        "DELETE FROM stock_data WHERE symbol = ? AND created_at < ?",
                        (symbol, cutoff_date)
                    )
                    logger.info(f"キャッシュクリア完了: {symbol}")
                else:
                    conn.execute(
                        "DELETE FROM stock_data WHERE created_at < ?",
                        (cutoff_date,)
                    )
                    logger.info("全キャッシュクリア完了")
                    
        except Exception as e:
            logger.error(f"キャッシュクリアエラー: {str(e)}")
    
    def get_cache_stats(self) -> Dict[str, Union[int, str]]:
        """キャッシュ統計情報取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 総レコード数
                cursor.execute("SELECT COUNT(*) FROM stock_data")
                total_records = cursor.fetchone()[0]
                
                # 銘柄数
                cursor.execute("SELECT COUNT(DISTINCT symbol) FROM stock_data")
                unique_symbols = cursor.fetchone()[0]
                
                # 最新データ時刻
                cursor.execute("SELECT MAX(created_at) FROM stock_data")
                latest_update = cursor.fetchone()[0]
                
                return {
                    'total_records': total_records,
                    'unique_symbols': unique_symbols,
                    'latest_update': latest_update or 'N/A',
                    'cache_file_size': f"{self.db_path.stat().st_size / 1024 / 1024:.2f} MB"
                }
                
        except Exception as e:
            logger.error(f"キャッシュ統計取得エラー: {str(e)}")
            return {}