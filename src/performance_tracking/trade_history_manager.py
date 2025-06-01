"""
投資履歴記録・管理モジュール

投資履歴の自動記録、管理、分析を行う
"""

from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import pandas as pd
import json
from pathlib import Path
from loguru import logger


class TradeStatus(Enum):
    """取引ステータス"""
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TradeDirection(Enum):
    """取引方向"""
    LONG = "long"
    SHORT = "short"


@dataclass
class TradeRecord:
    """取引記録データクラス"""
    trade_id: str
    symbol: str
    direction: TradeDirection
    entry_time: datetime
    entry_price: float
    quantity: int
    
    # 決済情報（オープンポジションの場合はNone）
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    
    # 損益情報
    realized_pnl: Optional[float] = None
    realized_pnl_pct: Optional[float] = None
    
    # 手数料・コスト
    entry_commission: float = 0.0
    exit_commission: float = 0.0
    other_fees: float = 0.0
    
    # 戦略・シグナル情報
    strategy_name: Optional[str] = None
    signal_strength: Optional[float] = None
    signal_confidence: Optional[float] = None
    
    # リスク管理
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    max_loss_pct: Optional[float] = None
    
    # 市場環境・条件
    market_condition: Optional[str] = None
    volatility: Optional[float] = None
    volume_ratio: Optional[float] = None
    
    # メタデータ
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    
    # ステータス
    status: TradeStatus = TradeStatus.OPEN
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        # Enumを文字列に変換
        data['direction'] = self.direction.value
        data['status'] = self.status.value
        # datetimeを文字列に変換
        if self.entry_time:
            data['entry_time'] = self.entry_time.isoformat()
        if self.exit_time:
            data['exit_time'] = self.exit_time.isoformat()
        # リストをJSONに変換
        if self.tags:
            data['tags'] = json.dumps(self.tags)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeRecord':
        """辞書から作成"""
        # データベース固有のフィールドを除外
        data = data.copy()
        data.pop('created_at', None)
        data.pop('updated_at', None)
        
        # Enumに変換
        data['direction'] = TradeDirection(data['direction'])
        data['status'] = TradeStatus(data['status'])
        # 文字列をdatetimeに変換
        if data.get('entry_time'):
            try:
                data['entry_time'] = datetime.fromisoformat(data['entry_time'])
            except (ValueError, TypeError):
                data['entry_time'] = None
        if data.get('exit_time'):
            try:
                data['exit_time'] = datetime.fromisoformat(data['exit_time'])
            except (ValueError, TypeError):
                data['exit_time'] = None
        # JSONをリストに変換
        if data.get('tags') and data['tags'] != 'null':
            try:
                data['tags'] = json.loads(data['tags'])
            except (ValueError, TypeError, json.JSONDecodeError):
                data['tags'] = None
        else:
            data['tags'] = None
        return cls(**data)


class TradeHistoryManager:
    """投資履歴記録・管理クラス"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初期化
        
        Args:
            db_path: データベースファイルパス（Noneの場合はデフォルトパス使用）
        """
        if db_path is None:
            db_path = Path.home() / ".py-stock" / "trade_history.db"
        
        self.db_path = Path(db_path)
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create database directory: {e}")
            # 無効なパスでも続行（テスト用）
        
        # データベース初期化
        try:
            self._init_database()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
        
        logger.info(f"TradeHistoryManager initialized with database: {self.db_path}")
    
    def _init_database(self):
        """データベーステーブル初期化"""
        with sqlite3.connect(self.db_path) as conn:
            # 取引履歴テーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    trade_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_time TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    exit_time TEXT,
                    exit_price REAL,
                    exit_reason TEXT,
                    realized_pnl REAL,
                    realized_pnl_pct REAL,
                    entry_commission REAL DEFAULT 0.0,
                    exit_commission REAL DEFAULT 0.0,
                    other_fees REAL DEFAULT 0.0,
                    strategy_name TEXT,
                    signal_strength REAL,
                    signal_confidence REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    max_loss_pct REAL,
                    market_condition TEXT,
                    volatility REAL,
                    volume_ratio REAL,
                    notes TEXT,
                    tags TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # インデックス作成
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON trade_history(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_time ON trade_history(entry_time)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON trade_history(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_strategy ON trade_history(strategy_name)")
            
            # パフォーマンス統計テーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0.0,
                    total_pnl REAL DEFAULT 0.0,
                    total_return_pct REAL DEFAULT 0.0,
                    average_win REAL DEFAULT 0.0,
                    average_loss REAL DEFAULT 0.0,
                    profit_factor REAL DEFAULT 0.0,
                    max_drawdown REAL DEFAULT 0.0,
                    max_drawdown_pct REAL DEFAULT 0.0,
                    sharpe_ratio REAL DEFAULT 0.0,
                    sortino_ratio REAL DEFAULT 0.0,
                    calmar_ratio REAL DEFAULT 0.0,
                    average_hold_time_hours REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def add_trade(self, trade: TradeRecord) -> bool:
        """
        取引を追加
        
        Args:
            trade: 取引記録
            
        Returns:
            成功した場合True
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                trade_dict = trade.to_dict()
                
                # 必要なフィールドのみ抽出（テーブル定義に合わせる）
                fields = [
                    'trade_id', 'symbol', 'direction', 'entry_time', 'entry_price', 'quantity',
                    'exit_time', 'exit_price', 'exit_reason', 'realized_pnl', 'realized_pnl_pct',
                    'entry_commission', 'exit_commission', 'other_fees', 'strategy_name',
                    'signal_strength', 'signal_confidence', 'stop_loss', 'take_profit',
                    'max_loss_pct', 'market_condition', 'volatility', 'volume_ratio',
                    'notes', 'tags', 'status'
                ]
                
                placeholders = ', '.join(['?' for _ in fields])
                values = [trade_dict.get(field) for field in fields]
                
                conn.execute(
                    f"INSERT OR REPLACE INTO trade_history ({', '.join(fields)}) VALUES ({placeholders})",
                    values
                )
                
                logger.info(f"Trade added: {trade.trade_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add trade {trade.trade_id}: {e}")
            return False
    
    def update_trade(self, trade: TradeRecord) -> bool:
        """
        取引を更新
        
        Args:
            trade: 更新する取引記録
            
        Returns:
            成功した場合True
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                trade_dict = trade.to_dict()
                
                # 更新フィールド設定
                update_fields = [
                    'exit_time', 'exit_price', 'exit_reason', 'realized_pnl', 'realized_pnl_pct',
                    'exit_commission', 'other_fees', 'stop_loss', 'take_profit', 'max_loss_pct',
                    'market_condition', 'volatility', 'volume_ratio', 'notes', 'tags', 'status'
                ]
                
                set_clause = ', '.join([f"{field} = ?" for field in update_fields])
                values = [trade_dict.get(field) for field in update_fields]
                values.append(trade.trade_id)
                
                cursor = conn.execute(
                    f"UPDATE trade_history SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE trade_id = ?",
                    values
                )
                
                if cursor.rowcount == 0:
                    logger.warning(f"Trade not found for update: {trade.trade_id}")
                    return False
                
                logger.info(f"Trade updated: {trade.trade_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update trade {trade.trade_id}: {e}")
            return False
    
    def close_trade(self, trade_id: str, exit_price: float, exit_reason: str, 
                   exit_commission: float = 0.0) -> bool:
        """
        取引を決済
        
        Args:
            trade_id: 取引ID
            exit_price: 決済価格
            exit_reason: 決済理由
            exit_commission: 決済手数料
            
        Returns:
            成功した場合True
        """
        try:
            trade = self.get_trade(trade_id)
            if not trade:
                logger.error(f"Trade not found: {trade_id}")
                return False
            
            if trade.status != TradeStatus.OPEN:
                logger.warning(f"Trade is not open: {trade_id}")
                return False
            
            # 決済情報を更新
            trade.exit_time = datetime.now()
            trade.exit_price = exit_price
            trade.exit_reason = exit_reason
            trade.exit_commission = exit_commission
            trade.status = TradeStatus.CLOSED
            
            # 損益計算
            if trade.direction == TradeDirection.LONG:
                trade.realized_pnl = (exit_price - trade.entry_price) * trade.quantity
            else:
                trade.realized_pnl = (trade.entry_price - exit_price) * trade.quantity
            
            # 手数料差し引き
            trade.realized_pnl -= (trade.entry_commission + trade.exit_commission + trade.other_fees)
            
            # 損益率計算
            investment_amount = trade.entry_price * trade.quantity
            trade.realized_pnl_pct = (trade.realized_pnl / investment_amount) * 100
            
            return self.update_trade(trade)
            
        except Exception as e:
            logger.error(f"Failed to close trade {trade_id}: {e}")
            return False
    
    def get_trade(self, trade_id: str) -> Optional[TradeRecord]:
        """
        特定の取引を取得
        
        Args:
            trade_id: 取引ID
            
        Returns:
            取引記録（見つからない場合はNone）
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM trade_history WHERE trade_id = ?",
                    (trade_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return TradeRecord.from_dict(dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Failed to get trade {trade_id}: {e}")
            return None
    
    def get_trades(self, 
                   symbol: Optional[str] = None,
                   status: Optional[TradeStatus] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   strategy: Optional[str] = None,
                   limit: Optional[int] = None) -> List[TradeRecord]:
        """
        取引リストを取得
        
        Args:
            symbol: 銘柄フィルタ
            status: ステータスフィルタ
            start_date: 開始日フィルタ
            end_date: 終了日フィルタ
            strategy: 戦略フィルタ
            limit: 取得件数制限
            
        Returns:
            取引記録リスト
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                where_conditions = []
                params = []
                
                if symbol:
                    where_conditions.append("symbol = ?")
                    params.append(symbol)
                
                if status:
                    where_conditions.append("status = ?")
                    params.append(status.value)
                
                if start_date:
                    where_conditions.append("entry_time >= ?")
                    params.append(start_date.isoformat())
                
                if end_date:
                    where_conditions.append("entry_time <= ?")
                    params.append(end_date.isoformat())
                
                if strategy:
                    where_conditions.append("strategy_name = ?")
                    params.append(strategy)
                
                where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                limit_clause = f" LIMIT {limit}" if limit else ""
                
                query = f"SELECT * FROM trade_history{where_clause} ORDER BY entry_time DESC{limit_clause}"
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [TradeRecord.from_dict(dict(row)) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return []
    
    def get_open_trades(self, symbol: Optional[str] = None) -> List[TradeRecord]:
        """
        オープンポジション取得
        
        Args:
            symbol: 銘柄フィルタ
            
        Returns:
            オープン取引記録リスト
        """
        return self.get_trades(symbol=symbol, status=TradeStatus.OPEN)
    
    def get_closed_trades(self, 
                         symbol: Optional[str] = None,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> List[TradeRecord]:
        """
        決済済み取引取得
        
        Args:
            symbol: 銘柄フィルタ
            start_date: 開始日フィルタ
            end_date: 終了日フィルタ
            
        Returns:
            決済済み取引記録リスト
        """
        return self.get_trades(
            symbol=symbol, 
            status=TradeStatus.CLOSED,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_trades_dataframe(self, **kwargs) -> pd.DataFrame:
        """
        取引データをDataFrameで取得
        
        Args:
            **kwargs: get_tradesと同じ引数
            
        Returns:
            取引データのDataFrame
        """
        trades = self.get_trades(**kwargs)
        if not trades:
            return pd.DataFrame()
        
        data = [trade.to_dict() for trade in trades]
        df = pd.DataFrame(data)
        
        # 日時カラムを変換
        if 'entry_time' in df.columns:
            df['entry_time'] = pd.to_datetime(df['entry_time'])
        if 'exit_time' in df.columns:
            df['exit_time'] = pd.to_datetime(df['exit_time'])
        
        return df
    
    def calculate_basic_stats(self, 
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None,
                            symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        基本統計計算
        
        Args:
            start_date: 開始日
            end_date: 終了日  
            symbol: 銘柄フィルタ
            
        Returns:
            統計データ辞書
        """
        closed_trades = self.get_closed_trades(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if not closed_trades:
            return {}
        
        # 基本統計
        total_trades = len(closed_trades)
        winning_trades = [t for t in closed_trades if t.realized_pnl > 0]
        losing_trades = [t for t in closed_trades if t.realized_pnl < 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        total_pnl = sum(t.realized_pnl for t in closed_trades if t.realized_pnl)
        average_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        average_win = sum(t.realized_pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        average_loss = sum(t.realized_pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        profit_factor = abs(average_win / average_loss) if average_loss != 0 else float('inf')
        
        # 保有期間統計
        hold_times = []
        for trade in closed_trades:
            if trade.entry_time and trade.exit_time:
                hold_time = (trade.exit_time - trade.entry_time).total_seconds() / 3600  # 時間単位
                hold_times.append(hold_time)
        
        average_hold_time = sum(hold_times) / len(hold_times) if hold_times else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'average_pnl': average_pnl,
            'average_win': average_win,
            'average_loss': average_loss,
            'profit_factor': profit_factor,
            'average_hold_time_hours': average_hold_time,
        }
    
    def delete_trade(self, trade_id: str) -> bool:
        """
        取引を削除
        
        Args:
            trade_id: 取引ID
            
        Returns:
            成功した場合True
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM trade_history WHERE trade_id = ?", (trade_id,))
                
                if cursor.rowcount == 0:
                    logger.warning(f"Trade not found for deletion: {trade_id}")
                    return False
                
                logger.info(f"Trade deleted: {trade_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete trade {trade_id}: {e}")
            return False
    
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """
        データベースのバックアップ
        
        Args:
            backup_path: バックアップファイルパス
            
        Returns:
            成功した場合True
        """
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.db_path.parent / f"trade_history_backup_{timestamp}.db"
            
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Database backed up to: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False