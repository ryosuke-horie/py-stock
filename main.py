#!/usr/bin/env python3
"""
メインエントリーポイント
株価データ収集システムの実行スクリプト
"""

import argparse
import sys
from pathlib import Path
from typing import List

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent))

from src.data_collector.stock_data_collector import StockDataCollector
from src.data_collector.symbol_manager import SymbolManager, MarketType
from src.config.settings import settings_manager
from src.utils.data_validator import DataValidator
from loguru import logger


def collect_single_stock(symbol: str, interval: str = "1m", period: str = "1d"):
    """単一銘柄データ収集"""
    print(f"銘柄データ収集: {symbol}")
    
    # 初期化
    settings_manager.setup_logging()
    collector = StockDataCollector()
    symbol_manager = SymbolManager()
    validator = DataValidator()
    
    # 銘柄正規化
    normalized_symbol = symbol_manager.normalize_symbol(symbol)
    symbol_info = symbol_manager.get_symbol_info(symbol)
    
    print(f"銘柄情報: {symbol_info['name']} ({normalized_symbol})")
    
    # データ取得
    data = collector.get_stock_data(
        symbol=normalized_symbol,
        interval=interval,
        period=period,
        use_cache=True
    )
    
    if data is not None:
        # データ検証
        validation = validator.validate_dataframe(data, normalized_symbol)
        
        print(f"取得成功: {len(data)}件")
        print(f"期間: {data['timestamp'].min()} 〜 {data['timestamp'].max()}")
        print(f"価格レンジ: {data['close'].min():.2f} 〜 {data['close'].max():.2f}")
        print(f"データ品質: {'OK' if validation['valid'] else 'NG'}")
        
        # 最新データ表示
        latest = data.iloc[-1]
        print(f"最新価格: {latest['close']:.2f} (出来高: {latest['volume']:,})")
        
        return True
    else:
        print("データ取得失敗")
        return False


def collect_multiple_stocks(symbols: List[str], interval: str = "5m", period: str = "1d"):
    """複数銘柄データ収集"""
    print(f"複数銘柄データ収集: {len(symbols)}銘柄")
    
    # 初期化
    settings_manager.setup_logging()
    collector = StockDataCollector(max_workers=min(len(symbols), 5))
    symbol_manager = SymbolManager()
    validator = DataValidator()
    
    # 銘柄正規化
    normalized_symbols = []
    for symbol in symbols:
        normalized = symbol_manager.normalize_symbol(symbol)
        normalized_symbols.append(normalized)
        info = symbol_manager.get_symbol_info(symbol)
        print(f"  {symbol} -> {normalized} ({info['name']})")
    
    # 並列データ取得
    print(f"\n並列取得開始...")
    results = collector.get_multiple_stocks(
        symbols=normalized_symbols,
        interval=interval,
        period=period,
        use_cache=True
    )
    
    # 結果表示
    print(f"\n取得結果:")
    success_count = 0
    for symbol, data in results.items():
        if data is not None:
            validation = validator.validate_dataframe(data, symbol)
            latest_price = data['close'].iloc[-1]
            print(f"  ✓ {symbol}: {len(data)}件, 最新価格: {latest_price:.2f}")
            success_count += 1
        else:
            print(f"  ✗ {symbol}: 取得失敗")
    
    print(f"\n成功率: {success_count}/{len(symbols)} ({success_count/len(symbols)*100:.1f}%)")
    return success_count


def show_cache_stats():
    """キャッシュ統計表示"""
    print("キャッシュ統計情報")
    
    collector = StockDataCollector()
    stats = collector.get_cache_stats()
    
    print(f"総レコード数: {stats.get('total_records', 0):,}")
    print(f"登録銘柄数: {stats.get('unique_symbols', 0)}")
    print(f"最終更新: {stats.get('latest_update', 'N/A')}")
    print(f"キャッシュサイズ: {stats.get('cache_file_size', 'N/A')}")


def show_sample_symbols():
    """サンプル銘柄表示"""
    print("サンプル銘柄コード")
    
    symbol_manager = SymbolManager()
    
    # 日本株サンプル
    japan_symbols = symbol_manager.get_sample_symbols(MarketType.JAPAN, 5)
    print(f"\n日本株サンプル:")
    for symbol in japan_symbols:
        info = symbol_manager.get_symbol_info(symbol)
        print(f"  {symbol}: {info['name']}")
    
    # 米国株サンプル
    us_symbols = symbol_manager.get_sample_symbols(MarketType.US, 5)
    print(f"\n米国株サンプル:")
    for symbol in us_symbols:
        info = symbol_manager.get_symbol_info(symbol)
        print(f"  {symbol}: {info['name']}")


def clean_cache(days: int = 30):
    """キャッシュクリーニング"""
    print(f"{days}日以上古いキャッシュをクリーニング")
    
    collector = StockDataCollector()
    
    # クリーニング前の統計
    stats_before = collector.get_cache_stats()
    print(f"クリーニング前: {stats_before.get('total_records', 0):,}件")
    
    # クリーニング実行
    collector.clear_cache(older_than_days=days)
    
    # クリーニング後の統計
    stats_after = collector.get_cache_stats()
    print(f"クリーニング後: {stats_after.get('total_records', 0):,}件")
    
    removed = stats_before.get('total_records', 0) - stats_after.get('total_records', 0)
    print(f"削除されたレコード: {removed:,}件")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="株価データ収集システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 単一銘柄（トヨタ）の1分足データを取得
  python main.py --symbol 7203 --interval 1m
  
  # 複数銘柄の5分足データを取得
  python main.py --symbols 7203 AAPL MSFT --interval 5m
  
  # キャッシュ統計表示
  python main.py --cache-stats
  
  # 30日以上古いキャッシュをクリーニング
  python main.py --clean-cache 30
  
  # サンプル銘柄表示
  python main.py --samples
        """
    )
    
    # 引数定義
    parser.add_argument("--symbol", type=str, help="単一銘柄コード")
    parser.add_argument("--symbols", nargs="+", help="複数銘柄コード")
    parser.add_argument("--interval", default="1m", 
                       choices=["1m", "2m", "5m", "15m", "30m", "1h", "1d"],
                       help="データ間隔 (デフォルト: 1m)")
    parser.add_argument("--period", default="1d",
                       choices=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y"],
                       help="取得期間 (デフォルト: 1d)")
    parser.add_argument("--cache-stats", action="store_true", 
                       help="キャッシュ統計表示")
    parser.add_argument("--clean-cache", type=int, metavar="DAYS",
                       help="指定日数以上古いキャッシュをクリーニング")
    parser.add_argument("--samples", action="store_true",
                       help="サンプル銘柄表示")
    
    args = parser.parse_args()
    
    try:
        # 単一銘柄処理
        if args.symbol:
            success = collect_single_stock(args.symbol, args.interval, args.period)
            sys.exit(0 if success else 1)
        
        # 複数銘柄処理
        elif args.symbols:
            success_count = collect_multiple_stocks(args.symbols, args.interval, args.period)
            sys.exit(0 if success_count > 0 else 1)
        
        # キャッシュ統計
        elif args.cache_stats:
            show_cache_stats()
        
        # キャッシュクリーニング
        elif args.clean_cache is not None:
            clean_cache(args.clean_cache)
        
        # サンプル銘柄表示
        elif args.samples:
            show_sample_symbols()
        
        # 引数なしの場合はヘルプ表示
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        sys.exit(1)
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()