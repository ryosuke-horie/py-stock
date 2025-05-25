"""
データベースバックアップ管理システム
SQLiteデータベースの自動バックアップ・復元・管理機能
"""

import sqlite3
import shutil
import gzip
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class BackupInfo:
    """バックアップ情報"""
    file_path: str
    created_at: datetime
    file_size: int
    is_compressed: bool
    original_db_path: str
    backup_type: str  # 'auto', 'manual', 'before_operation'
    operation_context: Optional[str] = None


@dataclass
class BackupConfig:
    """バックアップ設定"""
    backup_enabled: bool = True
    backup_dir: str = "cache/backups"
    backup_before_operations: List[str] = None
    backup_retention_count: int = 10
    backup_compression_enabled: bool = False
    daily_backup_enabled: bool = True
    backup_interval_hours: int = 24
    
    def __post_init__(self):
        if self.backup_before_operations is None:
            self.backup_before_operations = ["remove", "clear", "reorder"]


class BackupManager:
    """データベースバックアップ管理クラス"""
    
    def __init__(self, config: BackupConfig = None):
        """
        初期化
        
        Args:
            config: バックアップ設定
        """
        self.config = config or BackupConfig()
        self.ensure_backup_directory()
    
    def ensure_backup_directory(self):
        """バックアップディレクトリの確保"""
        backup_dir = Path(self.config.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"バックアップディレクトリ確保: {backup_dir}")
    
    def create_backup(self, 
                     db_path: str, 
                     backup_type: str = "manual",
                     operation_context: Optional[str] = None) -> Optional[str]:
        """
        データベースのバックアップを作成
        
        Args:
            db_path: バックアップ対象のデータベースパス
            backup_type: バックアップタイプ ('auto', 'manual', 'before_operation')
            operation_context: 操作コンテキスト（操作前バックアップの場合）
            
        Returns:
            作成されたバックアップファイルパス（失敗時はNone）
        """
        try:
            if not self.config.backup_enabled:
                logger.debug("バックアップが無効化されています")
                return None
            
            if not Path(db_path).exists():
                logger.warning(f"バックアップ対象のDBファイルが存在しません: {db_path}")
                return None
            
            # バックアップファイル名生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            db_name = Path(db_path).stem
            backup_filename = f"{db_name}_{backup_type}_{timestamp}.db"
            backup_path = Path(self.config.backup_dir) / backup_filename
            
            # SQLiteオンラインバックアップを使用
            backup_path_str = self._create_sqlite_backup(db_path, str(backup_path))
            
            if backup_path_str:
                # 圧縮が有効な場合
                if self.config.backup_compression_enabled:
                    compressed_path = self._compress_backup(backup_path_str)
                    if compressed_path:
                        Path(backup_path_str).unlink()  # 元ファイル削除
                        backup_path_str = compressed_path
                
                # バックアップ情報を記録
                self._record_backup_info(backup_path_str, db_path, backup_type, operation_context)
                
                logger.info(f"バックアップ作成完了: {backup_path_str}")
                return backup_path_str
            
            return None
            
        except Exception as e:
            logger.error(f"バックアップ作成エラー: {e}")
            return None
    
    def _create_sqlite_backup(self, source_db: str, backup_path: str) -> Optional[str]:
        """
        SQLiteオンラインバックアップAPI使用
        
        Args:
            source_db: ソースデータベースパス
            backup_path: バックアップ先パス
            
        Returns:
            作成されたバックアップパス（失敗時はNone）
        """
        try:
            # ソースDB接続
            source_conn = sqlite3.connect(source_db)
            
            # バックアップDB作成
            backup_conn = sqlite3.connect(backup_path)
            
            # オンラインバックアップ実行
            source_conn.backup(backup_conn)
            
            # 接続クローズ
            backup_conn.close()
            source_conn.close()
            
            return backup_path
            
        except Exception as e:
            logger.error(f"SQLiteバックアップエラー: {e}")
            # フォールバック: ファイルコピー
            try:
                shutil.copy2(source_db, backup_path)
                logger.info(f"ファイルコピーでバックアップ作成: {backup_path}")
                return backup_path
            except Exception as fallback_error:
                logger.error(f"ファイルコピーバックアップも失敗: {fallback_error}")
                return None
    
    def _compress_backup(self, backup_path: str) -> Optional[str]:
        """
        バックアップファイルを圧縮
        
        Args:
            backup_path: 圧縮対象パス
            
        Returns:
            圧縮ファイルパス（失敗時はNone）
        """
        try:
            compressed_path = f"{backup_path}.gz"
            
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            logger.debug(f"バックアップ圧縮完了: {compressed_path}")
            return compressed_path
            
        except Exception as e:
            logger.error(f"バックアップ圧縮エラー: {e}")
            return None
    
    def _record_backup_info(self, 
                           backup_path: str, 
                           original_db_path: str,
                           backup_type: str,
                           operation_context: Optional[str]):
        """
        バックアップ情報をメタデータファイルに記録
        
        Args:
            backup_path: バックアップファイルパス
            original_db_path: 元データベースパス
            backup_type: バックアップタイプ
            operation_context: 操作コンテキスト
        """
        try:
            backup_info = BackupInfo(
                file_path=backup_path,
                created_at=datetime.now(),
                file_size=Path(backup_path).stat().st_size,
                is_compressed=backup_path.endswith('.gz'),
                original_db_path=original_db_path,
                backup_type=backup_type,
                operation_context=operation_context
            )
            
            # メタデータファイルパス
            metadata_path = Path(self.config.backup_dir) / "backup_metadata.json"
            
            # 既存メタデータ読み込み
            metadata = []
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        metadata = data.get('backups', [])
                except Exception as e:
                    logger.warning(f"メタデータ読み込みエラー: {e}")
            
            # 新しい情報を追加
            backup_dict = asdict(backup_info)
            backup_dict['created_at'] = backup_info.created_at.isoformat()
            metadata.append(backup_dict)
            
            # メタデータ保存
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'backups': metadata,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"バックアップ情報記録完了: {backup_path}")
            
        except Exception as e:
            logger.error(f"バックアップ情報記録エラー: {e}")
    
    def list_backups(self, db_name: Optional[str] = None) -> List[BackupInfo]:
        """
        利用可能なバックアップ一覧を取得
        
        Args:
            db_name: 特定のDBのバックアップのみ取得（Noneの場合は全て）
            
        Returns:
            バックアップ情報リスト
        """
        try:
            metadata_path = Path(self.config.backup_dir) / "backup_metadata.json"
            
            if not metadata_path.exists():
                return []
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                backup_data = data.get('backups', [])
            
            backups = []
            for item in backup_data:
                # ファイルが実際に存在するかチェック
                if not Path(item['file_path']).exists():
                    continue
                
                backup_info = BackupInfo(
                    file_path=item['file_path'],
                    created_at=datetime.fromisoformat(item['created_at']),
                    file_size=item['file_size'],
                    is_compressed=item['is_compressed'],
                    original_db_path=item['original_db_path'],
                    backup_type=item['backup_type'],
                    operation_context=item.get('operation_context')
                )
                
                # DB名でフィルタリング
                if db_name:
                    backup_db_name = Path(backup_info.original_db_path).stem
                    if backup_db_name != db_name:
                        continue
                
                backups.append(backup_info)
            
            # 作成日時で降順ソート
            backups.sort(key=lambda x: x.created_at, reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"バックアップ一覧取得エラー: {e}")
            return []
    
    def restore_backup(self, backup_path: str, target_path: str) -> bool:
        """
        バックアップからデータベースを復元
        
        Args:
            backup_path: 復元元バックアップパス
            target_path: 復元先データベースパス
            
        Returns:
            復元成功の場合True
        """
        try:
            if not Path(backup_path).exists():
                logger.error(f"バックアップファイルが存在しません: {backup_path}")
                return False
            
            # 現在のDBをバックアップ（復元前バックアップ）
            if Path(target_path).exists():
                restore_backup_path = self.create_backup(
                    target_path, 
                    backup_type="before_restore",
                    operation_context=f"復元前バックアップ: {backup_path}"
                )
                if restore_backup_path:
                    logger.info(f"復元前バックアップ作成: {restore_backup_path}")
            
            # 圧縮ファイルの場合は解凍
            if backup_path.endswith('.gz'):
                temp_path = f"{target_path}.tmp"
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # 元ファイルを置き換え
                if Path(target_path).exists():
                    Path(target_path).unlink()
                shutil.move(temp_path, target_path)
            else:
                # 直接コピー
                shutil.copy2(backup_path, target_path)
            
            logger.info(f"バックアップ復元完了: {backup_path} -> {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"バックアップ復元エラー: {e}")
            return False
    
    def cleanup_old_backups(self, db_name: Optional[str] = None) -> int:
        """
        古いバックアップを削除
        
        Args:
            db_name: 特定のDBのバックアップのみクリーンアップ（Noneの場合は全て）
            
        Returns:
            削除されたファイル数
        """
        try:
            backups = self.list_backups(db_name)
            
            if len(backups) <= self.config.backup_retention_count:
                return 0
            
            # 削除対象（保持数を超えた古いバックアップ）
            backups_to_delete = backups[self.config.backup_retention_count:]
            deleted_count = 0
            
            for backup in backups_to_delete:
                try:
                    Path(backup.file_path).unlink()
                    deleted_count += 1
                    logger.debug(f"古いバックアップ削除: {backup.file_path}")
                except Exception as e:
                    logger.warning(f"バックアップ削除失敗: {backup.file_path} - {e}")
            
            # メタデータも更新
            self._cleanup_metadata()
            
            if deleted_count > 0:
                logger.info(f"古いバックアップ削除完了: {deleted_count}ファイル")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"バックアップクリーンアップエラー: {e}")
            return 0
    
    def _cleanup_metadata(self):
        """存在しないファイルのメタデータを削除"""
        try:
            metadata_path = Path(self.config.backup_dir) / "backup_metadata.json"
            
            if not metadata_path.exists():
                return
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                backup_data = data.get('backups', [])
            
            # 存在するファイルのみ保持
            valid_backups = []
            for item in backup_data:
                if Path(item['file_path']).exists():
                    valid_backups.append(item)
            
            # メタデータ更新
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'backups': valid_backups,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            
            logger.debug("メタデータクリーンアップ完了")
            
        except Exception as e:
            logger.error(f"メタデータクリーンアップエラー: {e}")
    
    def get_backup_statistics(self, db_name: Optional[str] = None) -> Dict[str, Any]:
        """
        バックアップ統計情報を取得
        
        Args:
            db_name: 特定のDBの統計のみ取得（Noneの場合は全て）
            
        Returns:
            統計情報辞書
        """
        try:
            backups = self.list_backups(db_name)
            
            if not backups:
                return {
                    "total_count": 0,
                    "total_size": 0,
                    "latest_backup": None,
                    "backup_types": {},
                    "disk_usage_mb": 0
                }
            
            # 統計計算
            total_size = sum(backup.file_size for backup in backups)
            backup_types = {}
            
            for backup in backups:
                backup_type = backup.backup_type
                if backup_type not in backup_types:
                    backup_types[backup_type] = 0
                backup_types[backup_type] += 1
            
            stats = {
                "total_count": len(backups),
                "total_size": total_size,
                "disk_usage_mb": round(total_size / (1024 * 1024), 2),
                "latest_backup": backups[0].created_at.isoformat() if backups else None,
                "backup_types": backup_types,
                "retention_count": self.config.backup_retention_count,
                "compression_enabled": self.config.backup_compression_enabled
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"バックアップ統計取得エラー: {e}")
            return {}
    
    def should_create_daily_backup(self, db_path: str) -> bool:
        """
        日次バックアップを作成すべきかチェック
        
        Args:
            db_path: 対象データベースパス
            
        Returns:
            日次バックアップが必要な場合True
        """
        try:
            if not self.config.daily_backup_enabled:
                return False
            
            db_name = Path(db_path).stem
            backups = self.list_backups(db_name)
            
            # 自動バックアップのみをチェック
            auto_backups = [b for b in backups if b.backup_type == 'auto']
            
            if not auto_backups:
                return True
            
            # 最新の自動バックアップから指定時間が経過しているかチェック
            latest_auto = auto_backups[0]
            time_diff = datetime.now() - latest_auto.created_at
            
            return time_diff.total_seconds() >= (self.config.backup_interval_hours * 3600)
            
        except Exception as e:
            logger.error(f"日次バックアップチェックエラー: {e}")
            return False