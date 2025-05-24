from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json
import os
from loguru import logger


@dataclass
class DataCollectorConfig:
    """データ収集設定"""
    cache_dir: str = "cache"
    max_workers: int = 5
    min_request_interval: float = 0.1
    cache_expire_hours: int = 1
    default_interval: str = "1m"
    default_period: str = "1d"
    retry_attempts: int = 3
    retry_min_wait: int = 4
    retry_max_wait: int = 10


@dataclass
class DatabaseConfig:
    """データベース設定"""
    type: str = "sqlite"
    path: str = "cache/stock_data.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    vacuum_interval_days: int = 7


@dataclass
class LoggingConfig:
    """ログ設定"""
    level: str = "INFO"
    log_dir: str = "logs"
    file_rotation: str = "1 day"
    file_retention: str = "30 days"
    console_enabled: bool = True
    file_enabled: bool = True


@dataclass
class SchedulerConfig:
    """スケジューラー設定"""
    enabled: bool = False
    timezone: str = "Asia/Tokyo"
    data_update_intervals: Dict[str, str] = field(default_factory=lambda: {
        "1m": "*/1 * * * *",  # 毎分
        "5m": "*/5 * * * *",  # 5分毎
        "1h": "0 * * * *",    # 毎時
        "1d": "0 9 * * *"     # 毎日9時
    })


@dataclass
class APIConfig:
    """API設定"""
    yfinance_enabled: bool = True
    rate_limit_per_minute: int = 100
    timeout_seconds: int = 30
    user_agent: str = "py-stock-data-collector/1.0"


@dataclass
class AppSettings:
    """アプリケーション全体設定"""
    data_collector: DataCollectorConfig = field(default_factory=DataCollectorConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    api: APIConfig = field(default_factory=APIConfig)
    
    # デフォルトウォッチリスト
    default_watchlists: Dict[str, List[str]] = field(default_factory=lambda: {
        "日本株主要銘柄": ["7203.T", "9984.T", "6758.T", "7974.T", "9983.T"],
        "米国株GAFAM": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
        "半導体関連": ["NVDA", "TSM", "INTC", "6861.T", "6954.T"]
    })


class SettingsManager:
    """設定管理クラス"""
    
    def __init__(self, config_file: str = "config/settings.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(exist_ok=True)
        self._settings: Optional[AppSettings] = None
        
        # 環境変数読み込み
        self._load_env_variables()
    
    def _load_env_variables(self):
        """環境変数から設定を読み込み"""
        # .envファイルが存在する場合は読み込み
        env_file = Path(".env")
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                logger.info("環境変数ファイル読み込み完了")
            except ImportError:
                logger.warning("python-dotenvがインストールされていません")
    
    @property
    def settings(self) -> AppSettings:
        """設定オブジェクト取得"""
        if self._settings is None:
            self._settings = self.load_settings()
        return self._settings
    
    def load_settings(self) -> AppSettings:
        """設定ファイルから設定を読み込み"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    logger.info(f"設定ファイル読み込み完了: {self.config_file}")
                    return self._dict_to_settings(config_data)
            else:
                logger.info("設定ファイルが存在しないため、デフォルト設定を使用")
                default_settings = AppSettings()
                self.save_settings(default_settings)
                return default_settings
                
        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")
            logger.info("デフォルト設定を使用")
            return AppSettings()
    
    def save_settings(self, settings: AppSettings):
        """設定をファイルに保存"""
        try:
            config_dict = self._settings_to_dict(settings)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
                logger.info(f"設定保存完了: {self.config_file}")
                
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
    
    def _dict_to_settings(self, config_dict: Dict[str, Any]) -> AppSettings:
        """辞書から設定オブジェクトに変換"""
        settings = AppSettings()
        
        # データ収集設定
        if "data_collector" in config_dict:
            dc_config = config_dict["data_collector"]
            settings.data_collector = DataCollectorConfig(**dc_config)
        
        # データベース設定
        if "database" in config_dict:
            db_config = config_dict["database"]
            settings.database = DatabaseConfig(**db_config)
        
        # ログ設定
        if "logging" in config_dict:
            log_config = config_dict["logging"]
            settings.logging = LoggingConfig(**log_config)
        
        # スケジューラー設定
        if "scheduler" in config_dict:
            sched_config = config_dict["scheduler"]
            settings.scheduler = SchedulerConfig(**sched_config)
        
        # API設定
        if "api" in config_dict:
            api_config = config_dict["api"]
            settings.api = APIConfig(**api_config)
        
        # ウォッチリスト
        if "default_watchlists" in config_dict:
            settings.default_watchlists = config_dict["default_watchlists"]
        
        # 環境変数での上書き
        self._apply_env_overrides(settings)
        
        return settings
    
    def _settings_to_dict(self, settings: AppSettings) -> Dict[str, Any]:
        """設定オブジェクトから辞書に変換"""
        return {
            "data_collector": {
                "cache_dir": settings.data_collector.cache_dir,
                "max_workers": settings.data_collector.max_workers,
                "min_request_interval": settings.data_collector.min_request_interval,
                "cache_expire_hours": settings.data_collector.cache_expire_hours,
                "default_interval": settings.data_collector.default_interval,
                "default_period": settings.data_collector.default_period,
                "retry_attempts": settings.data_collector.retry_attempts,
                "retry_min_wait": settings.data_collector.retry_min_wait,
                "retry_max_wait": settings.data_collector.retry_max_wait
            },
            "database": {
                "type": settings.database.type,
                "path": settings.database.path,
                "backup_enabled": settings.database.backup_enabled,
                "backup_interval_hours": settings.database.backup_interval_hours,
                "vacuum_interval_days": settings.database.vacuum_interval_days
            },
            "logging": {
                "level": settings.logging.level,
                "log_dir": settings.logging.log_dir,
                "file_rotation": settings.logging.file_rotation,
                "file_retention": settings.logging.file_retention,
                "console_enabled": settings.logging.console_enabled,
                "file_enabled": settings.logging.file_enabled
            },
            "scheduler": {
                "enabled": settings.scheduler.enabled,
                "timezone": settings.scheduler.timezone,
                "data_update_intervals": settings.scheduler.data_update_intervals
            },
            "api": {
                "yfinance_enabled": settings.api.yfinance_enabled,
                "rate_limit_per_minute": settings.api.rate_limit_per_minute,
                "timeout_seconds": settings.api.timeout_seconds,
                "user_agent": settings.api.user_agent
            },
            "default_watchlists": settings.default_watchlists
        }
    
    def _apply_env_overrides(self, settings: AppSettings):
        """環境変数での設定上書き"""
        # キャッシュディレクトリ
        if cache_dir := os.getenv("CACHE_DIR"):
            settings.data_collector.cache_dir = cache_dir
        
        # ログレベル
        if log_level := os.getenv("LOG_LEVEL"):
            settings.logging.level = log_level
        
        # データベースパス
        if db_path := os.getenv("DATABASE_PATH"):
            settings.database.path = db_path
        
        # ワーカー数
        if max_workers := os.getenv("MAX_WORKERS"):
            try:
                settings.data_collector.max_workers = int(max_workers)
            except ValueError:
                logger.warning(f"無効なMAX_WORKERS値: {max_workers}")
    
    def get_cache_dir(self) -> Path:
        """キャッシュディレクトリパス取得"""
        cache_dir = Path(self.settings.data_collector.cache_dir)
        cache_dir.mkdir(exist_ok=True)
        return cache_dir
    
    def get_log_dir(self) -> Path:
        """ログディレクトリパス取得"""
        log_dir = Path(self.settings.logging.log_dir)
        log_dir.mkdir(exist_ok=True)
        return log_dir
    
    def setup_logging(self):
        """ログ設定のセットアップ"""
        from loguru import logger as loguru_logger
        
        # 既存のハンドラーを削除
        loguru_logger.remove()
        
        log_config = self.settings.logging
        
        # コンソールログ
        if log_config.console_enabled:
            loguru_logger.add(
                lambda msg: print(msg, end=""),
                level=log_config.level,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
            )
        
        # ファイルログ
        if log_config.file_enabled:
            log_file = self.get_log_dir() / "app.log"
            loguru_logger.add(
                log_file,
                level=log_config.level,
                rotation=log_config.file_rotation,
                retention=log_config.file_retention,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
            )
        
        logger.info("ログ設定完了")
    
    def update_setting(self, section: str, key: str, value: Any):
        """設定値を更新"""
        settings = self.settings
        
        if hasattr(settings, section):
            section_obj = getattr(settings, section)
            if hasattr(section_obj, key):
                setattr(section_obj, key, value)
                self.save_settings(settings)
                logger.info(f"設定更新: {section}.{key} = {value}")
            else:
                logger.error(f"無効な設定キー: {section}.{key}")
        else:
            logger.error(f"無効な設定セクション: {section}")
    
    def get_watchlist(self, name: str) -> List[str]:
        """ウォッチリスト取得"""
        return self.settings.default_watchlists.get(name, [])
    
    def add_watchlist(self, name: str, symbols: List[str]):
        """ウォッチリスト追加"""
        settings = self.settings
        settings.default_watchlists[name] = symbols
        self.save_settings(settings)
        logger.info(f"ウォッチリスト追加: {name} ({len(symbols)}銘柄)")


# グローバル設定インスタンス
settings_manager = SettingsManager()