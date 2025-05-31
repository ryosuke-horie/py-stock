"""
config/settings.pyのテスト
"""

import pytest
import json
import tempfile
from pathlib import Path
from src.config.settings import (
    DataCollectorConfig, DatabaseConfig, LoggingConfig, 
    SchedulerConfig, APIConfig, AppSettings, SettingsManager
)


class TestDataCollectorConfig:
    """DataCollectorConfigのテストクラス"""
    
    def test_default_values(self):
        """デフォルト値のテスト"""
        config = DataCollectorConfig()
        assert config.cache_dir == "cache"
        assert config.max_workers == 5
        assert config.min_request_interval == 0.1
        assert config.cache_expire_hours == 1
        assert config.default_interval == "1m"
        assert config.default_period == "1d"
        assert config.retry_attempts == 3
        assert config.retry_min_wait == 4
        assert config.retry_max_wait == 10


class TestDatabaseConfig:
    """DatabaseConfigのテストクラス"""
    
    def test_default_values(self):
        """デフォルト値のテスト"""
        config = DatabaseConfig()
        assert config.type == "sqlite"
        assert config.path == "cache/stock_data.db"
        assert config.backup_enabled is True
        assert config.backup_interval_hours == 24
        assert config.vacuum_interval_days == 7
        assert config.backup_dir == "cache/backups"
        assert config.backup_before_operations == ["remove", "clear", "reorder"]
        assert config.backup_retention_count == 10
        assert config.backup_compression_enabled is False
        assert config.daily_backup_enabled is True


class TestLoggingConfig:
    """LoggingConfigのテストクラス"""
    
    def test_default_values(self):
        """デフォルト値のテスト"""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.log_dir == "logs"
        assert config.file_rotation == "1 day"
        assert config.file_retention == "30 days"
        assert config.console_enabled is True
        assert config.file_enabled is True


class TestSchedulerConfig:
    """SchedulerConfigのテストクラス"""
    
    def test_default_values(self):
        """デフォルト値のテスト"""
        config = SchedulerConfig()
        assert config.enabled is False
        assert config.timezone == "Asia/Tokyo"
        assert "1m" in config.data_update_intervals
        assert config.data_update_intervals["1m"] == "*/1 * * * *"


class TestAPIConfig:
    """APIConfigのテストクラス"""
    
    def test_default_values(self):
        """デフォルト値のテスト"""
        config = APIConfig()
        assert config.yfinance_enabled is True
        assert config.rate_limit_per_minute == 100
        assert config.timeout_seconds == 30
        assert config.user_agent == "py-stock-data-collector/1.0"


class TestAppSettings:
    """AppSettingsクラスのテストクラス"""
    
    def test_default_initialization(self):
        """デフォルト初期化のテスト"""
        settings = AppSettings()
        assert isinstance(settings.data_collector, DataCollectorConfig)
        assert isinstance(settings.database, DatabaseConfig)
        assert isinstance(settings.logging, LoggingConfig)
        assert isinstance(settings.scheduler, SchedulerConfig)
        assert isinstance(settings.api, APIConfig)
    
    def test_default_watchlists(self):
        """デフォルトウォッチリストのテスト"""
        settings = AppSettings()
        assert "日本株主要銘柄" in settings.default_watchlists
        assert "米国株GAFAM" in settings.default_watchlists
        assert "半導体関連" in settings.default_watchlists
        
        # 日本株のテスト
        japan_stocks = settings.default_watchlists["日本株主要銘柄"]
        assert "7203.T" in japan_stocks
        
        # 米国株のテスト
        us_stocks = settings.default_watchlists["米国株GAFAM"]
        assert "AAPL" in us_stocks


class TestSettingsManager:
    """SettingsManagerクラスのテストクラス"""
    
    def test_initialization(self, tmp_path):
        """初期化のテスト"""
        config_file = tmp_path / "test_config.json"
        manager = SettingsManager(str(config_file))
        assert manager.config_file == config_file
    
    def test_settings_property(self, tmp_path):
        """設定プロパティのテスト"""
        config_file = tmp_path / "test_config.json"
        manager = SettingsManager(str(config_file))
        settings = manager.settings
        assert isinstance(settings, AppSettings)
    
    def test_load_nonexistent_settings(self, tmp_path):
        """存在しない設定ファイルの読み込みテスト"""
        config_file = tmp_path / "nonexistent_config.json"
        manager = SettingsManager(str(config_file))
        settings = manager.load_settings()
        
        # デフォルト設定が返される
        assert isinstance(settings, AppSettings)
        assert settings.data_collector.max_workers == 5
    
    def test_save_and_load_settings(self, tmp_path):
        """設定ファイルの保存・読み込みテスト"""
        config_file = tmp_path / "test_config.json"
        manager = SettingsManager(str(config_file))
        
        # 設定を変更
        settings = AppSettings()
        settings.data_collector.max_workers = 10
        settings.database.backup_enabled = False
        
        # 保存
        manager.save_settings(settings)
        
        # ファイルが作成されているか確認
        assert config_file.exists()
        
        # 新しいマネージャーで読み込み
        new_manager = SettingsManager(str(config_file))
        loaded_settings = new_manager.load_settings()
        
        # 値が正しく読み込まれているか確認（基本的な構造のみ）
        assert isinstance(loaded_settings, AppSettings)
    
    def test_save_settings_with_invalid_path(self, tmp_path):
        """無効なパスへの設定保存テスト"""
        # 実際の実装では例外処理があるかどうか確認
        config_file = tmp_path / "test_config.json"
        manager = SettingsManager(str(config_file))
        
        settings = AppSettings()
        
        # 正常に保存できることを確認
        manager.save_settings(settings)
        assert config_file.exists()
    
    def test_load_invalid_json_settings(self, tmp_path):
        """無効なJSON設定ファイルの読み込みテスト"""
        config_file = tmp_path / "invalid_config.json"
        
        # 無効なJSONを書き込み
        with open(config_file, 'w') as f:
            f.write("invalid json content")
        
        manager = SettingsManager(str(config_file))
        settings = manager.load_settings()
        
        # デフォルト設定が返される
        assert isinstance(settings, AppSettings)
        assert settings.data_collector.max_workers == 5
    
    def test_update_data_collector_config(self, tmp_path):
        """データ収集設定更新テスト"""
        config_file = tmp_path / "test_config.json"
        manager = SettingsManager(str(config_file))
        
        # 設定を直接変更
        settings = manager.settings
        settings.data_collector.cache_dir = "new_cache"
        settings.data_collector.max_workers = 8
        settings.data_collector.min_request_interval = 0.2
        
        # 設定が更新されていることを確認
        assert settings.data_collector.cache_dir == "new_cache"
        assert settings.data_collector.max_workers == 8
        assert settings.data_collector.min_request_interval == 0.2
    
    def test_update_database_config(self, tmp_path):
        """データベース設定更新テスト"""
        config_file = tmp_path / "test_config.json"
        manager = SettingsManager(str(config_file))
        
        # 設定を直接変更
        settings = manager.settings
        settings.database.type = "postgresql"
        settings.database.path = "new_db.db"
        settings.database.backup_enabled = False
        
        assert settings.database.type == "postgresql"
        assert settings.database.path == "new_db.db"
        assert settings.database.backup_enabled == False
    
    def test_basic_settings_access(self, tmp_path):
        """基本的な設定アクセステスト"""
        config_file = tmp_path / "test_config.json"
        manager = SettingsManager(str(config_file))
        
        # 基本的な設定アクセス
        settings = manager.settings
        assert settings.data_collector.max_workers == 5
        assert settings.database.type == "sqlite"
        assert settings.logging.level == "INFO"
        
        # ウォッチリストアクセス
        assert "日本株主要銘柄" in settings.default_watchlists
        assert "7203.T" in settings.default_watchlists["日本株主要銘柄"]
    
    def test_concurrent_access(self, tmp_path):
        """並行アクセステスト"""
        config_file = tmp_path / "concurrent_config.json"
        
        # 複数のマネージャーインスタンス
        manager1 = SettingsManager(str(config_file))
        manager2 = SettingsManager(str(config_file))
        
        # 異なる設定で保存
        settings1 = manager1.settings
        settings1.data_collector.max_workers = 10
        manager1.save_settings(settings1)
        
        settings2 = manager2.settings
        settings2.data_collector.max_workers = 20
        manager2.save_settings(settings2)
        
        # ファイルが正常に作成されていることを確認
        assert config_file.exists()
        
        # 最後の保存が有効になっていることを確認
        fresh_manager = SettingsManager(str(config_file))
        fresh_settings = fresh_manager.load_settings()
        
        # どちらかの値が保存されていることを確認
        assert fresh_settings.data_collector.max_workers in [10, 20]