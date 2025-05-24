"""
シグナルデータストレージ
SQLiteベースのシグナル履歴管理システム
"""

import sqlite3
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SignalStorage:
    """シグナルデータストレージクラス"""
    
    def __init__(self, db_path: str = "dashboard/data/signals.db"):
        """
        初期化
        
        Args:
            db_path: データベースファイルパス
        """
        self.db_path = db_path
        self.ensure_db_directory()
        self.initialize_database()
    
    def ensure_db_directory(self):
        """データベースディレクトリ確保"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def initialize_database(self):
        """データベース初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # シグナル履歴テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signal_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    strength REAL NOT NULL,
                    confidence REAL NOT NULL,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit_1 REAL,
                    take_profit_2 REAL,
                    take_profit_3 REAL,
                    timestamp DATETIME NOT NULL,
                    active_rules TEXT,
                    market_condition TEXT,
                    volume REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # パフォーマンス記録テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER REFERENCES signal_history(id),
                    symbol TEXT NOT NULL,
                    entry_time DATETIME NOT NULL,
                    exit_time DATETIME,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity INTEGER NOT NULL,
                    pnl REAL,
                    pnl_percentage REAL,
                    hold_duration INTEGER,
                    exit_reason TEXT,
                    max_favorable REAL,
                    max_adverse REAL,
                    commission REAL DEFAULT 0,
                    is_closed BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 戦略パフォーマンステーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    total_signals INTEGER DEFAULT 0,
                    successful_signals INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    avg_return REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    sharpe_ratio REAL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(strategy_name, symbol, date)
                )
            """)
            
            # インデックス作成
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_symbol_timestamp ON signal_history(symbol, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_type ON signal_history(signal_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_symbol ON performance_records(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_closed ON performance_records(is_closed)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategy_performance ON strategy_performance(strategy_name, symbol)")
            
            conn.commit()
    
    def store_signal(self, signal_data: Dict[str, Any]) -> int:
        """
        シグナルを保存
        
        Args:
            signal_data: シグナルデータ辞書
            
        Returns:
            保存されたシグナルのID
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # active_rulesをJSON文字列に変換
                active_rules_json = json.dumps(signal_data.get('active_rules', []))
                
                cursor.execute("""
                    INSERT INTO signal_history (
                        symbol, signal_type, strength, confidence, entry_price,
                        stop_loss, take_profit_1, take_profit_2, take_profit_3,
                        timestamp, active_rules, market_condition, volume
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    signal_data['symbol'],
                    signal_data['signal'],
                    signal_data['strength'],
                    signal_data['confidence'],
                    signal_data.get('entry_price'),
                    signal_data.get('stop_loss'),
                    signal_data.get('take_profit', [None, None, None])[0] if signal_data.get('take_profit') else None,
                    signal_data.get('take_profit', [None, None, None])[1] if signal_data.get('take_profit') and len(signal_data.get('take_profit', [])) > 1 else None,
                    signal_data.get('take_profit', [None, None, None])[2] if signal_data.get('take_profit') and len(signal_data.get('take_profit', [])) > 2 else None,
                    signal_data['timestamp'],
                    active_rules_json,
                    signal_data.get('market_condition', 'unknown'),
                    signal_data.get('volume', 0)
                ))
                
                signal_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Signal stored: {signal_data['symbol']} - {signal_data['signal']} (ID: {signal_id})")
                return signal_id
                
        except Exception as e:
            logger.error(f"Error storing signal: {e}")
            raise
    
    def get_signals(self, 
                   symbol: Optional[str] = None,
                   signal_type: Optional[str] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: Optional[int] = None) -> pd.DataFrame:
        """
        シグナル履歴取得
        
        Args:
            symbol: 銘柄コード
            signal_type: シグナルタイプ
            start_date: 開始日時
            end_date: 終了日時
            limit: 取得件数制限
            
        Returns:
            シグナル履歴DataFrame
        """
        try:
            query = "SELECT * FROM signal_history WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if signal_type:
                query += " AND signal_type = ?"
                params.append(signal_type)
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=params)
                
                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df['created_at'] = pd.to_datetime(df['created_at'])
                    
                    # active_rulesをJSONから復元
                    df['active_rules'] = df['active_rules'].apply(
                        lambda x: json.loads(x) if x else []
                    )
                
                return df
                
        except Exception as e:
            logger.error(f"Error getting signals: {e}")
            return pd.DataFrame()
    
    def store_trade_result(self, trade_data: Dict[str, Any]) -> int:
        """
        トレード結果を保存
        
        Args:
            trade_data: トレードデータ辞書
            
        Returns:
            保存されたレコードのID
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO performance_records (
                        signal_id, symbol, entry_time, exit_time, entry_price,
                        exit_price, quantity, pnl, pnl_percentage, hold_duration,
                        exit_reason, max_favorable, max_adverse, commission, is_closed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_data.get('signal_id'),
                    trade_data['symbol'],
                    trade_data['entry_time'],
                    trade_data.get('exit_time'),
                    trade_data['entry_price'],
                    trade_data.get('exit_price'),
                    trade_data['quantity'],
                    trade_data.get('pnl'),
                    trade_data.get('pnl_percentage'),
                    trade_data.get('hold_duration'),
                    trade_data.get('exit_reason'),
                    trade_data.get('max_favorable'),
                    trade_data.get('max_adverse'),
                    trade_data.get('commission', 0),
                    trade_data.get('is_closed', False)
                ))
                
                record_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Trade result stored: {trade_data['symbol']} (ID: {record_id})")
                return record_id
                
        except Exception as e:
            logger.error(f"Error storing trade result: {e}")
            raise
    
    def get_performance_records(self,
                              symbol: Optional[str] = None,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None,
                              closed_only: bool = True) -> pd.DataFrame:
        """
        パフォーマンス記録取得
        
        Args:
            symbol: 銘柄コード
            start_date: 開始日時
            end_date: 終了日時
            closed_only: クローズ済みのみ
            
        Returns:
            パフォーマンス記録DataFrame
        """
        try:
            query = "SELECT * FROM performance_records WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if start_date:
                query += " AND entry_time >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND entry_time <= ?"
                params.append(end_date.isoformat())
            
            if closed_only:
                query += " AND is_closed = 1"
            
            query += " ORDER BY entry_time DESC"
            
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=params)
                
                if not df.empty:
                    df['entry_time'] = pd.to_datetime(df['entry_time'])
                    df['exit_time'] = pd.to_datetime(df['exit_time'])
                    df['created_at'] = pd.to_datetime(df['created_at'])
                
                return df
                
        except Exception as e:
            logger.error(f"Error getting performance records: {e}")
            return pd.DataFrame()
    
    def calculate_strategy_performance(self, 
                                     strategy_name: str,
                                     symbol: Optional[str] = None,
                                     days: int = 30) -> Dict[str, Any]:
        """
        戦略パフォーマンス計算
        
        Args:
            strategy_name: 戦略名
            symbol: 銘柄コード
            days: 計算期間（日数）
            
        Returns:
            パフォーマンス統計
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # パフォーマンスデータ取得
            df = self.get_performance_records(symbol=symbol, start_date=start_date, end_date=end_date)
            
            if df.empty:
                return self._empty_performance_stats()
            
            # 基本統計計算
            total_trades = len(df)
            winning_trades = df[df['pnl'] > 0]
            losing_trades = df[df['pnl'] < 0]
            
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
            total_pnl = df['pnl'].sum()
            avg_return = df['pnl_percentage'].mean() if not df['pnl_percentage'].isna().all() else 0
            
            # 勝敗統計
            avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0
            avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            
            # ドローダウン計算
            cumulative_pnl = df.sort_values('entry_time')['pnl'].cumsum()
            running_max = cumulative_pnl.expanding().max()
            drawdown = cumulative_pnl - running_max
            max_drawdown = drawdown.min()
            
            # シャープレシオ計算（簡易版）
            returns = df['pnl_percentage'].dropna()
            sharpe_ratio = returns.mean() / returns.std() if returns.std() > 0 else 0
            
            # 保持期間統計
            hold_durations = df['hold_duration'].dropna()
            avg_hold_duration = hold_durations.mean() if not hold_durations.empty else 0
            
            return {
                'strategy_name': strategy_name,
                'period_days': days,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_return': avg_return,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'avg_hold_duration': avg_hold_duration,
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'commission_total': df['commission'].sum()
            }
            
        except Exception as e:
            logger.error(f"Error calculating strategy performance: {e}")
            return self._empty_performance_stats()
    
    def _empty_performance_stats(self) -> Dict[str, Any]:
        """空のパフォーマンス統計"""
        return {
            'strategy_name': '',
            'period_days': 0,
            'total_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'avg_return': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'avg_hold_duration': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'commission_total': 0
        }
    
    def get_signal_success_rate(self, 
                               symbol: Optional[str] = None,
                               days: int = 30) -> Dict[str, float]:
        """
        シグナル成功率計算
        
        Args:
            symbol: 銘柄コード
            days: 計算期間（日数）
            
        Returns:
            シグナル別成功率
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # シグナルとパフォーマンスデータ結合取得
            query = """
                SELECT sh.signal_type, pr.pnl, pr.is_closed
                FROM signal_history sh
                LEFT JOIN performance_records pr ON sh.id = pr.signal_id
                WHERE sh.timestamp >= ? AND sh.timestamp <= ?
            """
            params = [start_date.isoformat(), end_date.isoformat()]
            
            if symbol:
                query += " AND sh.symbol = ?"
                params.append(symbol)
            
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=params)
            
            if df.empty:
                return {}
            
            # 成功率計算
            success_rates = {}
            for signal_type in df['signal_type'].unique():
                signal_data = df[df['signal_type'] == signal_type]
                closed_trades = signal_data[signal_data['is_closed'] == 1]
                
                if not closed_trades.empty:
                    successful_trades = closed_trades[closed_trades['pnl'] > 0]
                    success_rate = len(successful_trades) / len(closed_trades)
                    success_rates[signal_type] = success_rate
                else:
                    success_rates[signal_type] = 0.0
            
            return success_rates
            
        except Exception as e:
            logger.error(f"Error calculating signal success rate: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 90):
        """
        古いデータの削除
        
        Args:
            days: 保持期間（日数）
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 古いシグナル履歴削除
                cursor.execute(
                    "DELETE FROM signal_history WHERE timestamp < ?",
                    (cutoff_date.isoformat(),)
                )
                
                # 古いパフォーマンス記録削除
                cursor.execute(
                    "DELETE FROM performance_records WHERE entry_time < ?",
                    (cutoff_date.isoformat(),)
                )
                
                conn.commit()
                logger.info(f"Cleaned up data older than {days} days")
                
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        データベース統計取得
        
        Returns:
            データベース統計情報
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 各テーブルのレコード数取得
                signal_count = cursor.execute("SELECT COUNT(*) FROM signal_history").fetchone()[0]
                performance_count = cursor.execute("SELECT COUNT(*) FROM performance_records").fetchone()[0]
                
                # 銘柄数取得
                unique_symbols = cursor.execute("SELECT COUNT(DISTINCT symbol) FROM signal_history").fetchone()[0]
                
                # 最新データ日時取得
                latest_signal = cursor.execute("SELECT MAX(timestamp) FROM signal_history").fetchone()[0]
                
                return {
                    'signal_records': signal_count,
                    'performance_records': performance_count,
                    'unique_symbols': unique_symbols,
                    'latest_signal_time': latest_signal,
                    'database_path': self.db_path
                }
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}