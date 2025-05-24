"""
基本的な使用例
StockDataCollectorの基本機能をデモンストレーション
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.data_collector.stock_data_collector import StockDataCollector
from src.data_collector.symbol_manager import SymbolManager, MarketType
from src.config.settings import settings_manager
from src.utils.data_validator import DataValidator
from loguru import logger


def basic_single_stock_demo():
    """単一銘柄データ取得デモ"""
    print("=" * 50)
    print("単一銘柄データ取得デモ")
    print("=" * 50)
    
    # 設定読み込み
    settings_manager.setup_logging()
    
    # データ収集器初期化
    collector = StockDataCollector(
        cache_dir=settings_manager.get_cache_dir(),
        max_workers=3
    )
    
    # 銘柄管理器初期化
    symbol_manager = SymbolManager()
    
    # データバリデーター初期化
    validator = DataValidator()
    
    # トヨタ自動車の1分足データを取得
    symbol = "7203"
    normalized_symbol = symbol_manager.normalize_symbol(symbol)
    symbol_info = symbol_manager.get_symbol_info(symbol)
    
    print(f"銘柄情報: {symbol_info}")
    
    try:
        # データ取得
        data = collector.get_stock_data(
            symbol=normalized_symbol,
            interval="1m",
            period="1d",
            use_cache=True
        )
        
        if data is not None:
            print(f"\n取得データ概要:")
            print(f"- レコード数: {len(data)}")
            print(f"- 期間: {data['timestamp'].min()} 〜 {data['timestamp'].max()}")
            print(f"- 価格レンジ: {data['close'].min():.2f} 〜 {data['close'].max():.2f}")
            
            # データ検証
            validation_result = validator.validate_dataframe(data, normalized_symbol)
            print(f"\nデータ検証結果:")
            print(f"- 有効性: {'OK' if validation_result['valid'] else 'NG'}")
            print(f"- 統計情報: {validation_result.get('statistics', {})}")
            
            # 最新5件のデータを表示
            print(f"\n最新データ（5件）:")
            print(data[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())
            
        else:
            print("データ取得に失敗しました")
            
    except Exception as e:
        logger.error(f"エラー: {e}")


def multiple_stocks_demo():
    """複数銘柄データ取得デモ"""
    print("\n" + "=" * 50)
    print("複数銘柄データ取得デモ")
    print("=" * 50)
    
    collector = StockDataCollector(max_workers=5)
    symbol_manager = SymbolManager()
    validator = DataValidator()
    
    # 日本株と米国株のミックス
    symbols = ["7203", "9984", "AAPL", "MSFT", "GOOGL"]
    
    # 銘柄の正規化
    normalized_symbols = []
    for symbol in symbols:
        normalized = symbol_manager.normalize_symbol(symbol)
        normalized_symbols.append(normalized)
        info = symbol_manager.get_symbol_info(symbol)
        print(f"{symbol} -> {normalized} ({info['name']})")
    
    try:
        # 並列でデータ取得
        print(f"\n{len(normalized_symbols)}銘柄のデータを並列取得中...")
        results = collector.get_multiple_stocks(
            symbols=normalized_symbols,
            interval="5m",
            period="1d",
            use_cache=True
        )
        
        print(f"\n取得結果:")
        for symbol, data in results.items():
            if data is not None:
                validation = validator.validate_dataframe(data, symbol)
                print(f"- {symbol}: {len(data)}件 {'(有効)' if validation['valid'] else '(無効)'}")
                
                # 最新の終値を表示
                latest_price = data['close'].iloc[-1]
                print(f"  最新価格: {latest_price:.2f}")
            else:
                print(f"- {symbol}: データ取得失敗")
                
    except Exception as e:
        logger.error(f"エラー: {e}")


def watchlist_demo():
    """ウォッチリスト機能デモ"""
    print("\n" + "=" * 50)
    print("ウォッチリスト機能デモ")
    print("=" * 50)
    
    symbol_manager = SymbolManager()
    
    # ウォッチリスト作成
    japan_tech_symbols = ["7203", "6758", "7974", "9984", "6861"]
    us_tech_symbols = ["AAPL", "MSFT", "GOOGL", "NVDA", "META"]
    
    japan_watchlist = symbol_manager.create_watchlist(
        "日本テック株", japan_tech_symbols
    )
    
    us_watchlist = symbol_manager.create_watchlist(
        "米国テック株", us_tech_symbols
    )
    
    print(f"\n日本テック株ウォッチリスト:")
    for info in japan_watchlist["symbol_info"]:
        print(f"- {info['normalized']}: {info['name']}")
    
    print(f"\n米国テック株ウォッチリスト:")
    for info in us_watchlist["symbol_info"]:
        print(f"- {info['normalized']}: {info['name']}")


def cache_management_demo():
    """キャッシュ管理デモ"""
    print("\n" + "=" * 50)
    print("キャッシュ管理デモ")
    print("=" * 50)
    
    collector = StockDataCollector()
    
    # キャッシュ統計表示
    stats = collector.get_cache_stats()
    print("キャッシュ統計:")
    for key, value in stats.items():
        print(f"- {key}: {value}")
    
    # 古いキャッシュをクリア（7日以上古いデータ）
    print(f"\n古いキャッシュをクリア中...")
    collector.clear_cache(older_than_days=7)
    
    # 統計を再表示
    stats_after = collector.get_cache_stats()
    print("\nクリア後の統計:")
    for key, value in stats_after.items():
        print(f"- {key}: {value}")


def settings_demo():
    """設定管理デモ"""
    print("\n" + "=" * 50)
    print("設定管理デモ")
    print("=" * 50)
    
    # 現在の設定表示
    settings = settings_manager.settings
    
    print("データ収集設定:")
    print(f"- キャッシュディレクトリ: {settings.data_collector.cache_dir}")
    print(f"- 最大ワーカー数: {settings.data_collector.max_workers}")
    print(f"- キャッシュ有効期限: {settings.data_collector.cache_expire_hours}時間")
    
    print(f"\nデフォルトウォッチリスト:")
    for name, symbols in settings.default_watchlists.items():
        print(f"- {name}: {symbols}")


def main():
    """メイン実行関数"""
    print("StockDataCollector 基本使用例デモ")
    print("Python株価データ収集システム")
    
    try:
        # 基本デモを実行
        basic_single_stock_demo()
        multiple_stocks_demo()
        watchlist_demo()
        cache_management_demo()
        settings_demo()
        
        print("\n" + "=" * 50)
        print("デモ完了")
        print("=" * 50)
        
    except KeyboardInterrupt:
        print("\n\nデモが中断されました")
    except Exception as e:
        logger.error(f"デモ実行エラー: {e}")


if __name__ == "__main__":
    main()