"""
ウォッチリストデータストレージ
SQLiteベースのウォッチリスト永続化システム
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass

from .symbol_manager import SymbolManager, MarketType
from .backup_manager import BackupManager, BackupConfig
from ..config.settings import DatabaseConfig

logger = logging.getLogger(__name__)


@dataclass
class WatchlistItem:
    """ウォッチリストアイテム"""
    symbol: str
    name: str
    market_type: str
    position: int
    created_at: datetime
    updated_at: datetime


class WatchlistStorage:
    """ウォッチリストデータストレージクラス"""
    
    def __init__(self, 
                 db_path: str = "cache/watchlist.db", 
                 user_id: str = "default_user",
                 db_config: DatabaseConfig = None):
        """
        初期化
        
        Args:
            db_path: データベースファイルパス
            user_id: ユーザーID（将来の複数ユーザー対応用）
            db_config: データベース設定
        """
        self.db_path = db_path
        self.user_id = user_id
        self.symbol_manager = SymbolManager()
        
        # バックアップ設定とマネージャー初期化
        self.db_config = db_config or DatabaseConfig()
        backup_config = BackupConfig(
            backup_enabled=self.db_config.backup_enabled,
            backup_dir=self.db_config.backup_dir,
            backup_before_operations=self.db_config.backup_before_operations,
            backup_retention_count=self.db_config.backup_retention_count,
            backup_compression_enabled=self.db_config.backup_compression_enabled,
            daily_backup_enabled=self.db_config.daily_backup_enabled,
            backup_interval_hours=self.db_config.backup_interval_hours
        )
        self.backup_manager = BackupManager(backup_config)
        
        self.ensure_db_directory()
        self.initialize_database()
        
        # 日次バックアップチェック
        self._check_daily_backup()
    
    def ensure_db_directory(self):
        """データベースディレクトリ確保"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def initialize_database(self):
        """データベース初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # ウォッチリストテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT DEFAULT 'default_user',
                    symbol TEXT NOT NULL,
                    name TEXT,
                    market_type TEXT,
                    position INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, symbol)
                )
            """)
            
            # インデックス作成
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_watchlists_user_position 
                ON watchlists(user_id, position)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_watchlists_user_symbol 
                ON watchlists(user_id, symbol)
            """)
            
            conn.commit()
            logger.info(f"ウォッチリストデータベース初期化完了: {self.db_path}")
    
    def add_symbol(self, symbol: str) -> bool:
        """
        ウォッチリストに銘柄を追加
        
        Args:
            symbol: 銘柄コード
            
        Returns:
            成功した場合True
        """
        try:
            # 入力値チェック
            if not symbol or not symbol.strip():
                logger.warning("空の銘柄コードは追加できません")
                return False
            
            # 銘柄情報を取得
            symbol_info = self.symbol_manager.get_symbol_info(symbol)
            normalized_symbol = symbol_info['normalized']
            name = symbol_info['name']
            market_type = symbol_info['market_type']
            
            # 無効な市場タイプの場合は追加しない
            if market_type == 'unknown':
                logger.warning(f"未知の市場タイプのため追加をスキップ: {symbol}")
                return False
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 最大ポジションを取得
                cursor.execute("""
                    SELECT COALESCE(MAX(position), -1) + 1 
                    FROM watchlists 
                    WHERE user_id = ?
                """, (self.user_id,))
                
                next_position = cursor.fetchone()[0]
                
                # 銘柄を追加
                cursor.execute("""
                    INSERT OR REPLACE INTO watchlists 
                    (user_id, symbol, name, market_type, position, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (self.user_id, normalized_symbol, name, market_type, next_position))
                
                conn.commit()
                logger.info(f"ウォッチリストに追加: {normalized_symbol} ({name})")
                return True
                
        except Exception as e:
            logger.error(f"ウォッチリスト追加エラー: {symbol} - {e}")
            return False
    
    def remove_symbol(self, symbol: str) -> bool:
        """
        ウォッチリストから銘柄を削除
        
        Args:
            symbol: 銘柄コード
            
        Returns:
            成功した場合True
        """
        try:
            # 操作前バックアップ
            self._backup_before_operation("remove", f"銘柄削除: {symbol}")
            
            # 銘柄コードを正規化
            normalized_symbol = self.symbol_manager.normalize_symbol(symbol)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 削除対象のポジションを取得
                cursor.execute("""
                    SELECT position FROM watchlists 
                    WHERE user_id = ? AND symbol = ?
                """, (self.user_id, normalized_symbol))
                
                result = cursor.fetchone()
                if not result:
                    logger.warning(f"削除対象が見つかりません: {normalized_symbol}")
                    return False
                
                deleted_position = result[0]
                
                # 銘柄を削除
                cursor.execute("""
                    DELETE FROM watchlists 
                    WHERE user_id = ? AND symbol = ?
                """, (self.user_id, normalized_symbol))
                
                # より大きいポジションの銘柄を前に詰める
                cursor.execute("""
                    UPDATE watchlists 
                    SET position = position - 1, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND position > ?
                """, (self.user_id, deleted_position))
                
                conn.commit()
                logger.info(f"ウォッチリストから削除: {normalized_symbol}")
                return True
                
        except Exception as e:
            logger.error(f"ウォッチリスト削除エラー: {symbol} - {e}")
            return False
    
    def get_symbols(self) -> List[str]:
        """
        ウォッチリストの銘柄リストを取得
        
        Returns:
            銘柄コードリスト（ポジション順）
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT symbol FROM watchlists 
                    WHERE user_id = ? 
                    ORDER BY position ASC
                """, (self.user_id,))
                
                results = cursor.fetchall()
                symbols = [row[0] for row in results]
                
                logger.debug(f"ウォッチリスト取得: {len(symbols)}銘柄")
                return symbols
                
        except Exception as e:
            logger.error(f"ウォッチリスト取得エラー: {e}")
            return []
    
    def get_watchlist_items(self) -> List[WatchlistItem]:
        """
        ウォッチリストの詳細情報を取得
        
        Returns:
            ウォッチリストアイテムリスト
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT symbol, name, market_type, position, created_at, updated_at 
                    FROM watchlists 
                    WHERE user_id = ? 
                    ORDER BY position ASC
                """, (self.user_id,))
                
                results = cursor.fetchall()
                items = []
                
                for row in results:
                    item = WatchlistItem(
                        symbol=row[0],
                        name=row[1] or "N/A",
                        market_type=row[2] or "unknown",
                        position=row[3],
                        created_at=datetime.fromisoformat(row[4]) if row[4] else datetime.now(),
                        updated_at=datetime.fromisoformat(row[5]) if row[5] else datetime.now()
                    )
                    items.append(item)
                
                logger.debug(f"ウォッチリスト詳細取得: {len(items)}銘柄")
                return items
                
        except Exception as e:
            logger.error(f"ウォッチリスト詳細取得エラー: {e}")
            return []
    
    def reorder_symbols(self, symbol_order: List[str]) -> bool:
        """
        ウォッチリストの順序を変更
        
        Args:
            symbol_order: 新しい順序の銘柄コードリスト
            
        Returns:
            成功した場合True
        """
        try:
            # 操作前バックアップ
            self._backup_before_operation("reorder", f"順序変更: {len(symbol_order)}銘柄")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 正規化された銘柄コードで更新
                for position, symbol in enumerate(symbol_order):
                    normalized_symbol = self.symbol_manager.normalize_symbol(symbol)
                    cursor.execute("""
                        UPDATE watchlists 
                        SET position = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND symbol = ?
                    """, (position, self.user_id, normalized_symbol))
                
                conn.commit()
                logger.info(f"ウォッチリスト順序変更: {len(symbol_order)}銘柄")
                return True
                
        except Exception as e:
            logger.error(f"ウォッチリスト順序変更エラー: {e}")
            return False
    
    def migrate_from_session(self, session_symbols: List[str]) -> bool:
        """
        セッション状態からデータベースに移行
        
        Args:
            session_symbols: セッション状態の銘柄リスト
            
        Returns:
            成功した場合True
        """
        try:
            # 現在のウォッチリストが空の場合のみ移行
            current_symbols = self.get_symbols()
            if current_symbols:
                logger.info("ウォッチリストに既存データがあるため移行をスキップ")
                return True
            
            logger.info(f"セッション状態から移行開始: {session_symbols}")
            
            # セッションの銘柄を順番に追加
            for symbol in session_symbols:
                if symbol and symbol.strip():
                    self.add_symbol(symbol)
            
            logger.info("セッション状態からの移行完了")
            return True
            
        except Exception as e:
            logger.error(f"データ移行エラー: {e}")
            return False
    
    def clear_watchlist(self) -> bool:
        """
        ウォッチリストをクリア
        
        Returns:
            成功した場合True
        """
        try:
            # 操作前バックアップ
            self._backup_before_operation("clear", "ウォッチリストクリア")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM watchlists WHERE user_id = ?
                """, (self.user_id,))
                
                conn.commit()
                logger.info("ウォッチリストをクリア")
                return True
                
        except Exception as e:
            logger.error(f"ウォッチリストクリアエラー: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        ウォッチリスト統計情報を取得
        
        Returns:
            統計情報辞書
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 総銘柄数
                cursor.execute("""
                    SELECT COUNT(*) FROM watchlists WHERE user_id = ?
                """, (self.user_id,))
                total_symbols = cursor.fetchone()[0]
                
                # 市場別分布
                cursor.execute("""
                    SELECT market_type, COUNT(*) 
                    FROM watchlists 
                    WHERE user_id = ? 
                    GROUP BY market_type
                """, (self.user_id,))
                market_distribution = dict(cursor.fetchall())
                
                # 最新追加日時
                cursor.execute("""
                    SELECT MAX(created_at) FROM watchlists WHERE user_id = ?
                """, (self.user_id,))
                latest_added = cursor.fetchone()[0]
                
                stats = {
                    "total_symbols": total_symbols,
                    "market_distribution": market_distribution,
                    "latest_added": latest_added,
                    "user_id": self.user_id
                }
                
                logger.debug(f"ウォッチリスト統計: {stats}")
                return stats
                
        except Exception as e:
            logger.error(f"統計取得エラー: {e}")
            return {}
    
    def _backup_before_operation(self, operation: str, context: str):
        """
        操作前バックアップ
        
        Args:
            operation: 操作名
            context: 操作コンテキスト
        """
        try:
            if operation in self.db_config.backup_before_operations:
                backup_path = self.backup_manager.create_backup(
                    self.db_path,
                    backup_type="before_operation",
                    operation_context=context
                )
                if backup_path:
                    logger.debug(f"操作前バックアップ作成: {backup_path}")
                    # 古いバックアップをクリーンアップ
                    self.backup_manager.cleanup_old_backups("watchlist")
        except Exception as e:
            logger.warning(f"操作前バックアップエラー: {e}")
    
    def _check_daily_backup(self):
        """
        日次バックアップのチェックと実行
        """
        try:
            if self.backup_manager.should_create_daily_backup(self.db_path):
                backup_path = self.backup_manager.create_backup(
                    self.db_path,
                    backup_type="auto",
                    operation_context="日次自動バックアップ"
                )
                if backup_path:
                    logger.info(f"日次自動バックアップ作成: {backup_path}")
                    # 古いバックアップをクリーンアップ
                    self.backup_manager.cleanup_old_backups("watchlist")
        except Exception as e:
            logger.warning(f"日次バックアップエラー: {e}")
    
    def create_manual_backup(self) -> Optional[str]:
        """
        手動バックアップ作成
        
        Returns:
            作成されたバックアップファイルパス（失敗時はNone）
        """
        try:
            backup_path = self.backup_manager.create_backup(
                self.db_path,
                backup_type="manual",
                operation_context="ユーザー手動バックアップ"
            )
            if backup_path:
                logger.info(f"手動バックアップ作成: {backup_path}")
                # 古いバックアップをクリーンアップ
                self.backup_manager.cleanup_old_backups("watchlist")
            return backup_path
        except Exception as e:
            logger.error(f"手動バックアップエラー: {e}")
            return None
    
    def get_backup_info(self) -> Dict[str, Any]:
        """
        バックアップ情報取得
        
        Returns:
            バックアップ統計情報
        """
        try:
            return self.backup_manager.get_backup_statistics("watchlist")
        except Exception as e:
            logger.error(f"バックアップ情報取得エラー: {e}")
            return {}
    
    def list_available_backups(self):
        """
        利用可能なバックアップ一覧取得
        
        Returns:
            バックアップ情報リスト
        """
        try:
            return self.backup_manager.list_backups("watchlist")
        except Exception as e:
            logger.error(f"バックアップ一覧取得エラー: {e}")
            return []
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """
        バックアップからの復元
        
        Args:
            backup_path: バックアップファイルパス
            
        Returns:
            復元成功の場合True
        """
        try:
            result = self.backup_manager.restore_backup(backup_path, self.db_path)
            if result:
                logger.info(f"バックアップ復元完了: {backup_path}")
            return result
        except Exception as e:
            logger.error(f"バックアップ復元エラー: {e}")
            return False