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
from src.technical_analysis.indicators import TechnicalIndicators
from src.technical_analysis.support_resistance import SupportResistanceDetector
from src.technical_analysis.signal_generator import SignalGenerator
from src.risk_management.risk_manager import RiskManager, RiskParameters, PositionSide
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


def technical_analysis(symbol: str, interval: str = "5m", period: str = "1d"):
    """テクニカル分析実行"""
    print(f"テクニカル分析: {symbol}")
    
    # 初期化
    settings_manager.setup_logging()
    collector = StockDataCollector()
    symbol_manager = SymbolManager()
    
    # 銘柄正規化
    normalized_symbol = symbol_manager.normalize_symbol(symbol)
    symbol_info = symbol_manager.get_symbol_info(symbol)
    
    print(f"銘柄情報: {symbol_info['name']} ({normalized_symbol})")
    
    try:
        # データ取得
        data = collector.get_stock_data(
            symbol=normalized_symbol,
            interval=interval,
            period=period,
            use_cache=True
        )
        
        if data is None or len(data) < 20:
            print("テクニカル分析に十分なデータがありません")
            return False
        
        print(f"分析データ: {len(data)}件")
        print(f"期間: {data['timestamp'].min()} 〜 {data['timestamp'].max()}")
        
        # テクニカル分析実行
        indicators = TechnicalIndicators(data)
        analysis = indicators.comprehensive_analysis()
        
        # 結果表示
        current = analysis['current_values']
        ohlcv = analysis['ohlcv']
        
        print(f"\n📊 テクニカル分析結果 ({analysis['timestamp'].strftime('%Y-%m-%d %H:%M')})")
        print("=" * 50)
        
        print(f"💰 価格情報:")
        print(f"  終値: {ohlcv['close']:.2f}")
        print(f"  出来高: {ohlcv['volume']:,}")
        
        print(f"\n📈 主要指標:")
        print(f"  RSI(14): {current['rsi_current']:.2f}")
        print(f"  ストキャス%K: {current['stoch_k_current']:.2f}")
        print(f"  MACD: {current['macd_current']:.4f}")
        print(f"  ボリンジャー%B: {current['bb_percent_b_current']:.3f}")
        print(f"  ATR: {current['atr_current']:.2f}")
        
        # シグナル分析
        signals = indicators.get_trading_signals()
        
        # 買いシグナル集計
        buy_signals = [
            ('RSI過売り', signals['rsi_oversold']),
            ('ストキャス過売り', signals['stoch_oversold']),
            ('MACDゴールデンクロス', signals['macd_bullish']),
            ('VWAP上', signals['price_above_vwap']),
            ('下部バンド反発', signals['bb_lower_return'])
        ]
        
        # 売りシグナル集計  
        sell_signals = [
            ('RSI過買い', signals['rsi_overbought']),
            ('ストキャス過買い', signals['stoch_overbought']),
            ('MACDデッドクロス', signals['macd_bearish']),
            ('VWAP下', signals['price_below_vwap']),
            ('上部バンド反発', signals['bb_upper_return'])
        ]
        
        print(f"\n🎯 シグナル分析:")
        
        active_buy = [name for name, active in buy_signals if active]
        active_sell = [name for name, active in sell_signals if active]
        
        if active_buy:
            print(f"  🟢 買いシグナル: {', '.join(active_buy)}")
        if active_sell:
            print(f"  🔴 売りシグナル: {', '.join(active_sell)}")
        
        # 総合判定
        buy_count = len(active_buy)
        sell_count = len(active_sell)
        
        print(f"\n📋 総合判定:")
        if buy_count >= 3:
            print("  🟢 強い買いシグナル")
        elif buy_count >= 2:
            print("  🟢 買いシグナル")
        elif sell_count >= 3:
            print("  🔴 強い売りシグナル")
        elif sell_count >= 2:
            print("  🔴 売りシグナル")
        else:
            print("  ⚪ 中立（様子見）")
        
        print(f"  シグナル比率: 買い{buy_count}/売り{sell_count}")
        
        # 特殊状況
        if signals['bb_squeeze']:
            print("  ⚠️  ボリンジャーバンドスクイーズ（ブレイクアウト待ち）")
        
        return True
        
    except Exception as e:
        logger.error(f"テクニカル分析エラー: {e}")
        return False


def signal_analysis(symbol: str, interval: str = "5m", period: str = "1d"):
    """シグナル生成分析実行"""
    print(f"シグナル生成分析: {symbol}")
    
    # 初期化
    settings_manager.setup_logging()
    collector = StockDataCollector()
    symbol_manager = SymbolManager()
    
    # 銘柄正規化
    normalized_symbol = symbol_manager.normalize_symbol(symbol)
    symbol_info = symbol_manager.get_symbol_info(symbol)
    
    print(f"銘柄情報: {symbol_info['name']} ({normalized_symbol})")
    
    try:
        # データ取得
        data = collector.get_stock_data(
            symbol=normalized_symbol,
            interval=interval,
            period=period,
            use_cache=True
        )
        
        if data is None or len(data) < 50:
            print("シグナル分析に十分なデータがありません")
            return False
        
        print(f"分析データ: {len(data)}件")
        print(f"期間: {data['timestamp'].min()} 〜 {data['timestamp'].max()}")
        
        # シグナル生成実行
        signal_generator = SignalGenerator()
        signals = signal_generator.generate_signals(data)
        
        if signals is None or signals.empty:
            print("シグナル生成に失敗しました")
            return False
        
        # 最新シグナル表示
        latest_signal = signals.iloc[-1]
        current_price = data['close'].iloc[-1]
        
        print(f"\n🎯 シグナル分析結果 ({latest_signal['timestamp'].strftime('%Y-%m-%d %H:%M')})")
        print("=" * 60)
        
        print(f"💰 現在価格: {current_price:.2f}")
        print(f"📊 シグナル: {latest_signal['signal']}")
        print(f"💪 強度: {latest_signal['strength']:.1f}/100")
        print(f"🔍 信頼度: {latest_signal['confidence']:.2f}")
        
        # 有効ルール表示
        active_rules = [rule for rule, active in latest_signal['rule_results'].items() if active]
        if active_rules:
            print(f"✅ 有効ルール: {', '.join(active_rules)}")
        
        # ルール詳細
        print(f"\n📋 ルール詳細:")
        for rule_name, rule_active in latest_signal['rule_results'].items():
            status_emoji = "✅" if rule_active else "❌"
            print(f"  {status_emoji} {rule_name}")
        
        # エントリー・エグジットレベル
        if 'entry_price' in latest_signal and latest_signal['entry_price']:
            print(f"\n💡 エントリーレベル:")
            print(f"  エントリー価格: {latest_signal['entry_price']:.2f}")
            if 'stop_loss' in latest_signal and latest_signal['stop_loss']:
                print(f"  ストップロス: {latest_signal['stop_loss']:.2f}")
            if 'take_profit' in latest_signal and latest_signal['take_profit']:
                tp_levels = latest_signal['take_profit']
                if isinstance(tp_levels, list):
                    for i, tp in enumerate(tp_levels, 1):
                        print(f"  テイクプロフィット{i}: {tp:.2f}")
                else:
                    print(f"  テイクプロフィット: {tp_levels:.2f}")
        
        # パフォーマンス指標
        performance = signal_generator.get_performance_metrics()
        if performance:
            print(f"\n📈 パフォーマンス指標:")
            print(f"  勝率: {performance.get('win_rate', 0) * 100:.1f}%")
            print(f"  平均利益: {performance.get('avg_return', 0) * 100:.2f}%")
            print(f"  シャープレシオ: {performance.get('sharpe_ratio', 0):.2f}")
            print(f"  最大ドローダウン: {performance.get('max_drawdown', 0) * 100:.2f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"シグナル分析エラー: {e}")
        return False


def support_resistance_analysis(symbol: str, interval: str = "1h", period: str = "1mo"):
    """サポート・レジスタンス分析実行"""
    print(f"サポート・レジスタンス分析: {symbol}")
    
    # 初期化
    settings_manager.setup_logging()
    collector = StockDataCollector()
    symbol_manager = SymbolManager()
    
    # 銘柄正規化
    normalized_symbol = symbol_manager.normalize_symbol(symbol)
    symbol_info = symbol_manager.get_symbol_info(symbol)
    
    print(f"銘柄情報: {symbol_info['name']} ({normalized_symbol})")
    
    try:
        # データ取得
        data = collector.get_stock_data(
            symbol=normalized_symbol,
            interval=interval,
            period=period,
            use_cache=True
        )
        
        if data is None or len(data) < 30:
            print("サポレジ分析に十分なデータがありません")
            return False
        
        print(f"分析データ: {len(data)}件")
        print(f"期間: {data['timestamp'].min()} 〜 {data['timestamp'].max()}")
        
        # サポレジ分析実行
        detector = SupportResistanceDetector(data, min_touches=2, tolerance_percent=0.8)
        analysis = detector.comprehensive_analysis()
        
        # 結果表示
        current_price = analysis['current_price']
        
        print(f"\n🎯 サポート・レジスタンス分析結果 ({analysis['timestamp'].strftime('%Y-%m-%d %H:%M')})")
        print("=" * 60)
        
        print(f"💰 現在価格: {current_price:.2f}")
        print(f"📊 市場状況: {analysis['market_condition']}")
        
        # 主要サポレジレベル
        levels = analysis['support_resistance_levels']
        if levels:
            print(f"\n🎯 主要サポート・レジスタンスレベル (上位6件):")
            for i, level in enumerate(levels[:6], 1):
                distance = ((level.price - current_price) / current_price) * 100
                type_emoji = "🔴" if level.level_type == "resistance" else "🟢"
                print(f"  {i}. {type_emoji} {level.level_type.upper():11} "
                      f"{level.price:8.2f} ({distance:+5.1f}%) "
                      f"強度:{level.strength:.2f} 信頼度:{level.confidence:.2f}")
        
        # ピボットポイント
        pivots = analysis['pivot_points']
        print(f"\n📊 ピボットポイント:")
        print(f"  ピボット: {pivots.pivot:.2f}")
        print(f"  レジスタンス: R1={pivots.resistance_levels['R1']:.2f} "
              f"R2={pivots.resistance_levels['R2']:.2f} R3={pivots.resistance_levels['R3']:.2f}")
        print(f"  サポート: S1={pivots.support_levels['S1']:.2f} "
              f"S2={pivots.support_levels['S2']:.2f} S3={pivots.support_levels['S3']:.2f}")
        
        # 最寄りレベル
        nearest_support = analysis['nearest_support']
        nearest_resistance = analysis['nearest_resistance']
        
        print(f"\n📍 最寄りレベル:")
        if nearest_support:
            support_distance = ((current_price - nearest_support.price) / current_price) * 100
            print(f"  🟢 サポート: {nearest_support.price:.2f} ({support_distance:.1f}%下) 強度:{nearest_support.strength:.2f}")
        
        if nearest_resistance:
            resistance_distance = ((nearest_resistance.price - current_price) / current_price) * 100
            print(f"  🔴 レジスタンス: {nearest_resistance.price:.2f} ({resistance_distance:.1f}%上) 強度:{nearest_resistance.strength:.2f}")
        
        # 最近のブレイクアウト
        breakouts = analysis['recent_breakouts']
        if breakouts:
            print(f"\n💥 最近のブレイクアウト:")
            for breakout in breakouts:
                direction_emoji = "⬆️" if breakout.direction == "upward" else "⬇️"
                confirm_emoji = "✅" if breakout.confirmed else "⚠️"
                level_type = "レジスタンス" if breakout.level_type == "resistance" else "サポート"
                print(f"  {direction_emoji} {confirm_emoji} {level_type}{breakout.level_broken:.2f}を"
                      f"{breakout.price:.2f}で突破 ({breakout.timestamp.strftime('%m/%d %H:%M')})")
        
        # トレーディング推奨
        recommendations = analysis['trading_recommendations']
        if recommendations:
            print(f"\n💡 トレーディング推奨:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        return True
        
    except Exception as e:
        logger.error(f"サポレジ分析エラー: {e}")
        return False


def risk_management_analysis(symbol: str, interval: str = "5m", period: str = "1d", capital: float = 1000000):
    """リスク管理分析実行"""
    print(f"リスク管理分析: {symbol}")
    
    # 初期化
    settings_manager.setup_logging()
    collector = StockDataCollector()
    symbol_manager = SymbolManager()
    
    # 銘柄正規化
    normalized_symbol = symbol_manager.normalize_symbol(symbol)
    symbol_info = symbol_manager.get_symbol_info(symbol)
    
    print(f"銘柄情報: {symbol_info['name']} ({normalized_symbol})")
    
    try:
        # データ取得
        data = collector.get_stock_data(
            symbol=normalized_symbol,
            interval=interval,
            period=period,
            use_cache=True
        )
        
        if data is None or len(data) < 30:
            print("リスク分析に十分なデータがありません")
            return False
        
        print(f"分析データ: {len(data)}件")
        print(f"期間: {data['timestamp'].min()} 〜 {data['timestamp'].max()}")
        
        # リスク管理システム初期化
        risk_params = RiskParameters(
            max_position_size_pct=2.0,
            max_daily_loss_pct=5.0,
            stop_loss_pct=2.0,
            atr_multiplier=2.0,
            trailing_stop_pct=1.5,
            risk_reward_ratios=[1.0, 1.5, 2.0, 3.0],
            max_positions=5
        )
        
        risk_manager = RiskManager(risk_params, initial_capital=capital)
        current_price = data['close'].iloc[-1]
        
        print(f"\n🛡️ リスク管理分析結果")
        print("=" * 60)
        
        print(f"💰 現在価格: {current_price:.2f}")
        print(f"💼 総資本: ¥{capital:,}")
        
        # ストップロス計算
        from src.risk_management.risk_manager import StopLossType
        
        stop_types = [
            (StopLossType.FIXED_PERCENTAGE, "固定%"),
            (StopLossType.ATR_BASED, "ATRベース"),
            (StopLossType.SUPPORT_RESISTANCE, "サポレジベース")
        ]
        
        print(f"\n🎯 ストップロス計算:")
        for stop_type, type_name in stop_types:
            stop_loss = risk_manager.calculate_stop_loss(
                data, current_price, PositionSide.LONG, stop_type
            )
            stop_pct = ((current_price - stop_loss) / current_price) * 100
            print(f"  {type_name}: ¥{stop_loss:.2f} ({stop_pct:.1f}%下)")
        
        # ポジションサイジング
        atr_stop_loss = risk_manager.calculate_stop_loss(
            data, current_price, PositionSide.LONG, StopLossType.ATR_BASED
        )
        
        position_size = risk_manager.calculate_position_size(
            normalized_symbol, current_price, atr_stop_loss, PositionSide.LONG
        )
        
        investment_amount = current_price * position_size
        risk_amount = (current_price - atr_stop_loss) * position_size
        
        print(f"\n📊 ポジションサイジング (ATRベース):")
        print(f"  推奨ポジションサイズ: {position_size:,}株")
        print(f"  投資金額: ¥{investment_amount:,} ({(investment_amount/capital)*100:.1f}%)")
        print(f"  最大リスク: ¥{risk_amount:,} ({(risk_amount/capital)*100:.1f}%)")
        
        # テイクプロフィットレベル
        tp_levels = risk_manager.calculate_take_profit_levels(
            current_price, atr_stop_loss, PositionSide.LONG
        )
        
        print(f"\n🎯 テイクプロフィットレベル:")
        for i, (tp_price, rr_ratio) in enumerate(zip(tp_levels, risk_params.risk_reward_ratios)):
            potential_profit = (tp_price - current_price) * position_size
            print(f"  TP{i+1}: ¥{tp_price:.2f} (RR比 1:{rr_ratio:.1f})")
            print(f"       利益: ¥{potential_profit:,.0f}")
        
        # リスク指標
        print(f"\n📊 リスク指標:")
        print(f"  最大ポジション数: {risk_params.max_positions}")
        print(f"  日次最大損失限度: ¥{capital * (risk_params.max_daily_loss_pct/100):,.0f} ({risk_params.max_daily_loss_pct}%)")
        print(f"  ポジション当たり最大リスク: ¥{capital * (risk_params.max_position_size_pct/100):,.0f} ({risk_params.max_position_size_pct}%)")
        
        # ボラティリティ分析
        indicators = TechnicalIndicators(data)
        atr = indicators.calculate_atr()
        if not atr.empty:
            current_atr = atr.iloc[-1]
            atr_pct = (current_atr / current_price) * 100
            print(f"\n📈 ボラティリティ分析:")
            print(f"  ATR(14): ¥{current_atr:.2f} ({atr_pct:.1f}%)")
            
            if atr_pct > 3.0:
                print(f"  ⚠️  高ボラティリティ - ポジションサイズ縮小推奨")
            elif atr_pct < 1.0:
                print(f"  ℹ️  低ボラティリティ - 通常ポジションサイズ可能")
            else:
                print(f"  ✅ 標準ボラティリティ - 推奨ポジションサイズ適用可能")
        
        # 時間ベースリスク
        from datetime import datetime, time
        current_time = datetime.now().time()
        force_close_time = risk_params.force_close_time
        
        print(f"\n⏰ 時間ベースリスク管理:")
        print(f"  強制決済時刻: {force_close_time.strftime('%H:%M')}")
        print(f"  現在時刻: {current_time.strftime('%H:%M')}")
        
        if current_time >= force_close_time:
            print(f"  ⚠️  強制決済時刻を過ぎています")
        else:
            remaining_time = datetime.combine(datetime.today(), force_close_time) - datetime.combine(datetime.today(), current_time)
            print(f"  ⏳ 強制決済まで: {remaining_time}")
        
        return True
        
    except Exception as e:
        logger.error(f"リスク管理分析エラー: {e}")
        return False


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
  
  # テクニカル分析実行（トヨタ5分足）
  python main.py --technical 7203 --interval 5m
  
  # サポレジ分析実行（トヨタ1時間足）
  python main.py --support-resistance 7203 --interval 1h --period 1mo
  
  # シグナル生成分析実行（トヨタ5分足）
  python main.py --signal 7203 --interval 5m --period 1d
  
  # リスク管理分析実行（トヨタ5分足、資本100万円）
  python main.py --risk 7203 --interval 5m --period 1d --capital 1000000
  
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
    parser.add_argument("--technical", type=str, help="テクニカル分析対象銘柄")
    parser.add_argument("--support-resistance", type=str, help="サポレジ分析対象銘柄")
    parser.add_argument("--signal", type=str, help="シグナル分析対象銘柄")
    parser.add_argument("--risk", type=str, help="リスク管理分析対象銘柄")
    parser.add_argument("--capital", type=float, default=1000000, help="初期資本 (デフォルト: 1,000,000円)")
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
        
        # テクニカル分析
        elif args.technical:
            success = technical_analysis(args.technical, args.interval, args.period)
            sys.exit(0 if success else 1)
        
        # サポレジ分析
        elif getattr(args, 'support_resistance', None):
            success = support_resistance_analysis(args.support_resistance, args.interval, args.period)
            sys.exit(0 if success else 1)
        
        # シグナル分析
        elif args.signal:
            success = signal_analysis(args.signal, args.interval, args.period)
            sys.exit(0 if success else 1)
        
        # リスク管理分析
        elif args.risk:
            success = risk_management_analysis(args.risk, args.interval, args.period, args.capital)
            sys.exit(0 if success else 1)
        
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