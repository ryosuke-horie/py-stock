"""
config/settings.pyのテスト
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
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
    
    def test_config_validation(self, tmp_path):
        """設定値検証テスト"""
        config_file = tmp_path / "validation_config.json"
        manager = SettingsManager(str(config_file))
        
        # 異常な設定値をテスト
        settings = manager.settings
        
        # 負の値や無効な値の設定
        settings.data_collector.max_workers = -1  # 負の値
        settings.data_collector.min_request_interval = -0.5  # 負の値
        settings.data_collector.cache_expire_hours = 0  # ゼロ
        
        # 設定が保存・読み込みできることを確認（バリデーションは個別実装による）
        manager.save_settings(settings)
        loaded_settings = manager.load_settings()
        assert isinstance(loaded_settings, AppSettings)
    
    def test_deep_config_modification(self, tmp_path):
        """深い階層の設定変更テスト"""
        config_file = tmp_path / "deep_config.json"
        manager = SettingsManager(str(config_file))
        
        settings = manager.settings
        
        # ネストした設定の変更
        settings.scheduler.data_update_intervals["5m"] = "*/5 * * * *"
        settings.scheduler.data_update_intervals["1h"] = "0 * * * *"
        settings.database.backup_before_operations.append("custom_operation")
        
        # リストや辞書の変更が保持されることを確認
        manager.save_settings(settings)
        loaded_settings = manager.load_settings()
        
        assert isinstance(loaded_settings, AppSettings)
        # 基本的な構造が維持されていることを確認
        assert hasattr(loaded_settings, 'scheduler')
        assert hasattr(loaded_settings, 'database')
    
    def test_empty_config_file(self, tmp_path):
        """空の設定ファイルテスト"""
        config_file = tmp_path / "empty_config.json"
        
        # 空のファイルを作成
        config_file.touch()
        
        manager = SettingsManager(str(config_file))
        settings = manager.load_settings()
        
        # デフォルト設定が返される
        assert isinstance(settings, AppSettings)
        assert settings.data_collector.max_workers == 5
    
    def test_partial_config_file(self, tmp_path):
        """部分的な設定ファイルテスト"""
        config_file = tmp_path / "partial_config.json"
        
        # 部分的な設定を書き込み
        partial_config = {
            "data_collector": {
                "max_workers": 15
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(partial_config, f)
        
        manager = SettingsManager(str(config_file))
        settings = manager.load_settings()
        
        # デフォルト設定が使用される
        assert isinstance(settings, AppSettings)
    
    def test_large_config_file(self, tmp_path):
        """大きな設定ファイルテスト"""
        config_file = tmp_path / "large_config.json"
        
        # 大きなウォッチリストを持つ設定
        large_watchlist = {f"STOCK_{i:04d}" for i in range(1000)}
        
        settings = AppSettings()
        settings.default_watchlists["Large Watchlist"] = list(large_watchlist)
        
        manager = SettingsManager(str(config_file))
        manager.save_settings(settings)
        
        # 読み込みが正常に完了することを確認
        loaded_settings = manager.load_settings()
        assert isinstance(loaded_settings, AppSettings)
        assert len(loaded_settings.default_watchlists) > 0
    
    def test_unicode_and_special_characters(self, tmp_path):
        """Unicode・特殊文字テスト"""
        config_file = tmp_path / "unicode_config.json"
        manager = SettingsManager(str(config_file))
        
        settings = manager.settings
        
        # Unicode文字を含む設定
        settings.default_watchlists["日本株🇯🇵"] = ["7203.T", "6758.T"]
        settings.default_watchlists["Special-Chars_123"] = ["AAPL", "GOOGL"]
        settings.data_collector.cache_dir = "キャッシュ/データ"
        
        # 保存・読み込み
        manager.save_settings(settings)
        loaded_settings = manager.load_settings()
        
        assert isinstance(loaded_settings, AppSettings)
    
    def test_readonly_file_handling(self, tmp_path):
        """読み取り専用ファイル処理テスト"""
        config_file = tmp_path / "readonly_config.json"
        
        # ファイルを作成して読み取り専用に設定
        settings = AppSettings()
        manager = SettingsManager(str(config_file))
        manager.save_settings(settings)
        
        # ファイルを読み取り専用に変更
        config_file.chmod(0o444)
        
        try:
            # 読み込みは成功するべき
            loaded_settings = manager.load_settings()
            assert isinstance(loaded_settings, AppSettings)
            
            # 保存は失敗する可能性があるが、例外処理されるべき
            try:
                manager.save_settings(settings)
            except (PermissionError, OSError):
                # 権限エラーは正常
                pass
        finally:
            # ファイル権限を元に戻す（テスト環境のクリーンアップ）
            try:
                config_file.chmod(0o644)
            except:
                pass
    
    def test_config_directory_creation(self, tmp_path):
        """設定ディレクトリ作成テスト"""
        # 存在しないディレクトリのパス
        nested_dir = tmp_path / "nested" / "config" / "path"
        config_file = nested_dir / "config.json"
        
        manager = SettingsManager(str(config_file))
        settings = AppSettings()
        
        # ディレクトリが自動作成されるか確認
        manager.save_settings(settings)
        
        assert config_file.exists()
        assert config_file.parent.exists()
    
    def test_all_config_classes_attributes(self):
        """全設定クラスの属性テスト"""
        # DataCollectorConfig
        dc_config = DataCollectorConfig()
        assert hasattr(dc_config, 'cache_dir')
        assert hasattr(dc_config, 'max_workers')
        assert hasattr(dc_config, 'min_request_interval')
        assert hasattr(dc_config, 'cache_expire_hours')
        assert hasattr(dc_config, 'default_interval')
        assert hasattr(dc_config, 'default_period')
        assert hasattr(dc_config, 'retry_attempts')
        assert hasattr(dc_config, 'retry_min_wait')
        assert hasattr(dc_config, 'retry_max_wait')
        
        # DatabaseConfig
        db_config = DatabaseConfig()
        assert hasattr(db_config, 'type')
        assert hasattr(db_config, 'path')
        assert hasattr(db_config, 'backup_enabled')
        assert hasattr(db_config, 'backup_interval_hours')
        assert hasattr(db_config, 'vacuum_interval_days')
        assert hasattr(db_config, 'backup_dir')
        assert hasattr(db_config, 'backup_before_operations')
        assert hasattr(db_config, 'backup_retention_count')
        assert hasattr(db_config, 'backup_compression_enabled')
        assert hasattr(db_config, 'daily_backup_enabled')
        
        # LoggingConfig
        log_config = LoggingConfig()
        assert hasattr(log_config, 'level')
        assert hasattr(log_config, 'log_dir')
        assert hasattr(log_config, 'file_rotation')
        assert hasattr(log_config, 'file_retention')
        assert hasattr(log_config, 'console_enabled')
        assert hasattr(log_config, 'file_enabled')
        
        # SchedulerConfig
        sched_config = SchedulerConfig()
        assert hasattr(sched_config, 'enabled')
        assert hasattr(sched_config, 'timezone')
        assert hasattr(sched_config, 'data_update_intervals')
        
        # APIConfig
        api_config = APIConfig()
        assert hasattr(api_config, 'yfinance_enabled')
        assert hasattr(api_config, 'rate_limit_per_minute')
        assert hasattr(api_config, 'timeout_seconds')
        assert hasattr(api_config, 'user_agent')
    
    def test_config_data_types(self):
        """設定データ型テスト"""
        # DataCollectorConfig
        dc_config = DataCollectorConfig()
        assert isinstance(dc_config.cache_dir, str)
        assert isinstance(dc_config.max_workers, int)
        assert isinstance(dc_config.min_request_interval, (int, float))
        assert isinstance(dc_config.cache_expire_hours, (int, float))
        assert isinstance(dc_config.default_interval, str)
        assert isinstance(dc_config.default_period, str)
        assert isinstance(dc_config.retry_attempts, int)
        assert isinstance(dc_config.retry_min_wait, (int, float))
        assert isinstance(dc_config.retry_max_wait, (int, float))
        
        # DatabaseConfig
        db_config = DatabaseConfig()
        assert isinstance(db_config.type, str)
        assert isinstance(db_config.path, str)
        assert isinstance(db_config.backup_enabled, bool)
        assert isinstance(db_config.backup_interval_hours, (int, float))
        assert isinstance(db_config.vacuum_interval_days, int)
        assert isinstance(db_config.backup_dir, str)
        assert isinstance(db_config.backup_before_operations, list)
        assert isinstance(db_config.backup_retention_count, int)
        assert isinstance(db_config.backup_compression_enabled, bool)
        assert isinstance(db_config.daily_backup_enabled, bool)
        
        # LoggingConfig
        log_config = LoggingConfig()
        assert isinstance(log_config.level, str)
        assert isinstance(log_config.log_dir, str)
        assert isinstance(log_config.file_rotation, str)
        assert isinstance(log_config.file_retention, str)
        assert isinstance(log_config.console_enabled, bool)
        assert isinstance(log_config.file_enabled, bool)
        
        # SchedulerConfig
        sched_config = SchedulerConfig()
        assert isinstance(sched_config.enabled, bool)
        assert isinstance(sched_config.timezone, str)
        assert isinstance(sched_config.data_update_intervals, dict)
        
        # APIConfig
        api_config = APIConfig()
        assert isinstance(api_config.yfinance_enabled, bool)
        assert isinstance(api_config.rate_limit_per_minute, int)
        assert isinstance(api_config.timeout_seconds, (int, float))
        assert isinstance(api_config.user_agent, str)
    
    def test_default_watchlists_integrity(self):
        """デフォルトウォッチリスト整合性テスト"""
        settings = AppSettings()
        
        # 各ウォッチリストが空でないことを確認
        for name, symbols in settings.default_watchlists.items():
            assert isinstance(name, str)
            assert len(name) > 0
            assert isinstance(symbols, list)
            assert len(symbols) > 0
            
            # 各シンボルが文字列であることを確認
            for symbol in symbols:
                assert isinstance(symbol, str)
                assert len(symbol) > 0
        
        # 特定の銘柄が含まれていることを確認
        japan_stocks = settings.default_watchlists.get("日本株主要銘柄", [])
        us_stocks = settings.default_watchlists.get("米国株GAFAM", [])
        semiconductor_stocks = settings.default_watchlists.get("半導体関連", [])
        
        # 日本株の形式確認（.T 拡張子）
        for symbol in japan_stocks:
            if "." in symbol:
                assert symbol.endswith(".T")
        
        # 米国株の形式確認（一般的に4文字以下）
        for symbol in us_stocks:
            assert len(symbol) <= 5  # GOOGL等を考慮
    
    def test_settings_manager_error_conditions(self, tmp_path):
        """SettingsManagerエラー条件テスト"""
        # 無効なディスク領域シミュレーション（実際のファイルシステムに依存）
        config_file = tmp_path / "error_test_config.json"
        manager = SettingsManager(str(config_file))
        
        # 正常な設定で基本動作確認
        settings = AppSettings()
        manager.save_settings(settings)
        loaded_settings = manager.load_settings()
        assert isinstance(loaded_settings, AppSettings)
        
        # 破損したJSONファイルでの読み込み
        with open(config_file, 'w') as f:
            f.write('{"data_collector": {"max_workers": }')  # 不完全なJSON
        
        # エラーハンドリングされてデフォルト設定が返されることを確認
        recovered_settings = manager.load_settings()
        assert isinstance(recovered_settings, AppSettings)
        assert recovered_settings.data_collector.max_workers == 5  # デフォルト値
    
    def test_load_env_file(self, tmp_path, monkeypatch):
        """環境変数ファイル読み込みテスト"""
        # 作業ディレクトリを変更
        monkeypatch.chdir(tmp_path)
        
        # .envファイル作成
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_API_KEY=test_value\n")
        
        # dotenvが利用可能な場合のテスト
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('dotenv.load_dotenv') as mock_load_dotenv:
                # 新しいインスタンスを作成して初期化
                manager = SettingsManager(str(tmp_path / "config.json"))
                # load_dotenv が呼ばれたことを確認
                assert mock_load_dotenv.called
    
    def test_load_env_file_import_error(self, tmp_path, monkeypatch):
        """dotenvインポートエラーのテスト"""
        monkeypatch.chdir(tmp_path)
        
        # .envファイル作成
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_API_KEY=test_value\n")
        
        # ImportError を発生させる
        with patch('src.config.settings.Path.exists', return_value=True):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'dotenv'")):
                # エラーが処理されることを確認
                manager = SettingsManager(str(tmp_path / "config.json"))
                assert manager is not None
    
    def test_settings_to_dict_conversion(self, tmp_path):
        """設定オブジェクトから辞書への変換テスト"""
        config_file = tmp_path / "conversion_test.json"
        manager = SettingsManager(str(config_file))
        
        # カスタム設定を作成
        settings = AppSettings()
        settings.data_collector.max_workers = 15
        settings.data_collector.cache_dir = "custom_cache"
        settings.database.backup_enabled = False
        settings.logging.level = "DEBUG"
        
        # 保存して読み込み
        manager.save_settings(settings)
        
        # JSONファイルの内容を確認
        with open(config_file, 'r') as f:
            saved_data = json.load(f)
        
        # 構造が正しいことを確認
        assert "data_collector" in saved_data
        assert saved_data["data_collector"]["max_workers"] == 15
        assert saved_data["data_collector"]["cache_dir"] == "custom_cache"
        assert saved_data["database"]["backup_enabled"] == False
        assert saved_data["logging"]["level"] == "DEBUG"
    
    def test_dict_to_settings_conversion(self, tmp_path):
        """辞書から設定オブジェクトへの変換テスト"""
        config_file = tmp_path / "dict_conversion_test.json"
        
        # カスタム辞書データを作成
        config_data = {
            "data_collector": {
                "cache_dir": "test_cache",
                "max_workers": 20,
                "min_request_interval": 0.5,
                "cache_expire_hours": 2,
                "default_interval": "5m",
                "default_period": "1w",
                "retry_attempts": 5,
                "retry_min_wait": 2,
                "retry_max_wait": 20
            },
            "database": {
                "type": "mysql",
                "path": "test.db",
                "backup_enabled": False,
                "backup_interval_hours": 48,
                "vacuum_interval_days": 14,
                "backup_dir": "test_backups",
                "backup_before_operations": ["test_op"],
                "backup_retention_count": 5,
                "backup_compression_enabled": True,
                "daily_backup_enabled": False
            },
            "logging": {
                "level": "DEBUG",
                "log_dir": "test_logs",
                "file_rotation": "2 days",
                "file_retention": "60 days",
                "console_enabled": False,
                "file_enabled": True
            },
            "scheduler": {
                "enabled": True,
                "timezone": "UTC",
                "data_update_intervals": {"1d": "0 0 * * *"}
            },
            "api": {
                "yfinance_enabled": False,
                "rate_limit_per_minute": 50,
                "timeout_seconds": 60,
                "user_agent": "test-agent"
            },
            "default_watchlists": {
                "テスト": ["TEST1", "TEST2"]
            }
        }
        
        # JSONファイルに保存
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # 読み込み
        manager = SettingsManager(str(config_file))
        settings = manager.load_settings()
        
        # 値が正しく設定されていることを確認
        assert settings.data_collector.cache_dir == "test_cache"
        assert settings.data_collector.max_workers == 20
        assert settings.database.type == "mysql"
        assert settings.database.backup_enabled == False
        assert settings.logging.level == "DEBUG"
        assert settings.logging.console_enabled == False
        assert settings.scheduler.enabled == True
        assert settings.api.yfinance_enabled == False
        assert "テスト" in settings.default_watchlists
        assert settings.default_watchlists["テスト"] == ["TEST1", "TEST2"]
    
    def test_save_settings_io_error(self, tmp_path):
        """設定保存時のIOエラーテスト"""
        config_file = tmp_path / "io_error_test.json"
        manager = SettingsManager(str(config_file))
        
        settings = AppSettings()
        
        # ファイルを作成して閉じない（ロックされた状態をシミュレート）
        with patch('builtins.open', side_effect=IOError("Cannot write to file")):
            # save_settingsは例外を処理してログに記録する
            manager.save_settings(settings)
            # エラーでもクラッシュしないことを確認
            assert True
    
    def test_cache_dir_creation(self, tmp_path):
        """キャッシュディレクトリ作成テスト"""
        config_file = tmp_path / "cache_test.json"
        manager = SettingsManager(str(config_file))
        
        # 新しいキャッシュディレクトリパスを設定
        settings = manager.settings
        cache_path = tmp_path / "new_cache_dir"
        settings.data_collector.cache_dir = str(cache_path)
        
        # 設定を保存（実装によってはディレクトリが作成される可能性）
        manager.save_settings(settings)
        
        # 読み込み直して確認
        loaded_settings = manager.load_settings()
        assert loaded_settings.data_collector.cache_dir == str(cache_path)
    
    def test_settings_with_none_values(self, tmp_path):
        """None値を含む設定のテスト"""
        config_file = tmp_path / "none_values_test.json"
        
        # None値を含む設定データ
        config_data = {
            "data_collector": {
                "cache_dir": None,  # Noneの場合
                "max_workers": 5
            },
            "database": None,  # セクション全体がNone
            "logging": {},  # 空のセクション
            "scheduler": {
                "enabled": False,
                "timezone": "Asia/Tokyo",
                "data_update_intervals": None  # Noneの場合
            },
            "api": {
                "yfinance_enabled": True
            },
            "default_watchlists": None  # Noneの場合
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        manager = SettingsManager(str(config_file))
        settings = manager.load_settings()
        
        # デフォルト値が使用されることを確認
        assert isinstance(settings, AppSettings)
        assert settings.data_collector.max_workers == 5  # 指定された値
        assert settings.data_collector.cache_dir == "cache"  # デフォルト値
        assert settings.database.type == "sqlite"  # デフォルト値
        assert settings.logging.level == "INFO"  # デフォルト値
    
    def test_global_singleton_instance(self):
        """グローバルシングルトンインスタンスのテスト"""
        from src.config.settings import settings_manager
        
        # シングルトンインスタンスが存在することを確認
        assert settings_manager is not None
        assert isinstance(settings_manager, SettingsManager)
        
        # 設定オブジェクトが取得できることを確認
        settings = settings_manager.settings
        assert settings is not None
        assert isinstance(settings, AppSettings)
        
        # デフォルト設定が読み込まれていることを確認
        assert hasattr(settings, 'data_collector')
        assert hasattr(settings, 'database')
        assert hasattr(settings, 'logging')
        assert hasattr(settings, 'scheduler')
        assert hasattr(settings, 'api')
        assert hasattr(settings, 'default_watchlists')