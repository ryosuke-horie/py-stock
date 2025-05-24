"""
サポート・レジスタンス検出デモスクリプト
SupportResistanceDetectorクラスの使用例とデイトレード分析デモ
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.data_collector.stock_data_collector import StockDataCollector
from src.data_collector.symbol_manager import SymbolManager, MarketType
from src.technical_analysis.support_resistance import SupportResistanceDetector
from src.config.settings import settings_manager
from loguru import logger


def basic_support_resistance_demo():
    """基本サポート・レジスタンス検出デモ"""
    print("=" * 70)
    print("基本サポート・レジスタンス検出デモ")
    print("=" * 70)
    
    # 設定とログの初期化
    settings_manager.setup_logging()
    
    # データ収集
    collector = StockDataCollector()
    symbol_manager = SymbolManager()
    
    # トヨタ自動車のデータを取得
    symbol = "7203.T"
    print(f"銘柄: {symbol}")
    
    try:
        # 1時間足データを1週間分取得（より多くのデータポイント）
        data = collector.get_stock_data(symbol, interval="1h", period="1mo")
        
        if data is None or len(data) < 50:
            print("十分なデータが取得できませんでした")
            return
        
        print(f"取得データ: {len(data)}件")
        print(f"期間: {data['timestamp'].min()} 〜 {data['timestamp'].max()}")
        
        # サポレジ検出器初期化
        detector = SupportResistanceDetector(data, min_touches=2, tolerance_percent=0.8)
        
        # サポート・レジスタンスレベル検出
        levels = detector.detect_support_resistance_levels(min_strength=0.3, max_levels=8)
        
        current_price = data['close'].iloc[-1]
        print(f"\n💰 現在価格: {current_price:.2f}")
        
        print(f"\n🎯 検出されたサポート・レジスタンスレベル ({len(levels)}件):")
        print("-" * 60)
        
        for i, level in enumerate(levels, 1):
            distance = ((level.price - current_price) / current_price) * 100
            type_emoji = "🔴" if level.level_type == "resistance" else "🟢"
            
            print(f"{i:2d}. {type_emoji} {level.level_type.upper():11} "
                  f"{level.price:8.2f} ({distance:+5.1f}%) "
                  f"強度:{level.strength:.3f} タッチ:{level.touch_count}回 "
                  f"信頼度:{level.confidence:.3f}")
        
        # 最寄りのサポート・レジスタンス
        nearest_support = detector._find_nearest_level(levels, current_price, 'support')
        nearest_resistance = detector._find_nearest_level(levels, current_price, 'resistance')
        
        print(f"\n📍 最寄りレベル:")
        if nearest_support:
            support_distance = ((current_price - nearest_support.price) / current_price) * 100
            print(f"  🟢 サポート: {nearest_support.price:.2f} ({support_distance:.1f}%下)")
        
        if nearest_resistance:
            resistance_distance = ((nearest_resistance.price - current_price) / current_price) * 100
            print(f"  🔴 レジスタンス: {nearest_resistance.price:.2f} ({resistance_distance:.1f}%上)")
        
    except Exception as e:
        logger.error(f"エラー: {e}")


def pivot_points_demo():
    """ピボットポイント分析デモ"""
    print("\n" + "=" * 70)
    print("ピボットポイント分析デモ")
    print("=" * 70)
    
    collector = StockDataCollector()
    
    try:
        # Apple株で分析（24時間取引のため）
        symbol = "AAPL"
        data = collector.get_stock_data(symbol, interval="1h", period="1mo")
        
        if data is None or len(data) < 20:
            print("データが不足しています")
            return
        
        print(f"銘柄: {symbol}")
        print(f"分析データ: {len(data)}件")
        
        detector = SupportResistanceDetector(data)
        
        # 各種ピボットポイント計算
        daily_pivots = detector.calculate_pivot_points('daily')
        weekly_pivots = detector.calculate_pivot_points('weekly')
        camarilla_pivots = detector.calculate_camarilla_pivots()
        
        current_price = data['close'].iloc[-1]
        print(f"\n💰 現在価格: ${current_price:.2f}")
        
        # 日次ピボットポイント
        print(f"\n📊 日次ピボットポイント:")
        print(f"  ピボット: ${daily_pivots.pivot:.2f}")
        print(f"  レジスタンス:")
        for level, price in daily_pivots.resistance_levels.items():
            distance = ((price - current_price) / current_price) * 100
            print(f"    {level}: ${price:.2f} ({distance:+5.1f}%)")
        print(f"  サポート:")
        for level, price in daily_pivots.support_levels.items():
            distance = ((price - current_price) / current_price) * 100
            print(f"    {level}: ${price:.2f} ({distance:+5.1f}%)")
        
        # 週次ピボットポイント
        print(f"\n📊 週次ピボットポイント:")
        print(f"  ピボット: ${weekly_pivots.pivot:.2f}")
        print(f"  R1: ${weekly_pivots.resistance_levels['R1']:.2f}")
        print(f"  S1: ${weekly_pivots.support_levels['S1']:.2f}")
        
        # カマリラピボット
        print(f"\n📊 カマリラピボット:")
        for level in ['H4', 'H3', 'H2', 'H1']:
            price = camarilla_pivots[level]
            distance = ((price - current_price) / current_price) * 100
            print(f"  {level}: ${price:.2f} ({distance:+5.1f}%)")
        
        print(f"  現在価格: ${current_price:.2f}")
        
        for level in ['L1', 'L2', 'L3', 'L4']:
            price = camarilla_pivots[level]
            distance = ((price - current_price) / current_price) * 100
            print(f"  {level}: ${price:.2f} ({distance:+5.1f}%)")
        
    except Exception as e:
        logger.error(f"ピボット分析エラー: {e}")


def breakout_detection_demo():
    """ブレイクアウト検出デモ"""
    print("\n" + "=" * 70)
    print("ブレイクアウト検出デモ")
    print("=" * 70)
    
    collector = StockDataCollector()
    symbol_manager = SymbolManager()
    
    # 複数銘柄でブレイクアウト監視
    symbols = ["7203.T", "AAPL", "MSFT", "GOOGL"]
    
    for symbol in symbols:
        try:
            print(f"\n🎯 {symbol} のブレイクアウト分析")
            print("-" * 40)
            
            # データ取得
            data = collector.get_stock_data(symbol, interval="1h", period="1mo")
            
            if data is None or len(data) < 50:
                print("  データ不足")
                continue
            
            detector = SupportResistanceDetector(data, min_touches=2)
            
            # レベル検出
            levels = detector.detect_support_resistance_levels(min_strength=0.25)
            
            if not levels:
                print("  有効なサポレジレベルが検出されませんでした")
                continue
            
            # ブレイクアウト検出
            breakouts = detector.detect_breakouts(levels, confirmation_bars=2, volume_threshold=1.3)
            
            current_price = data['close'].iloc[-1]
            print(f"  現在価格: {current_price:.2f}")
            
            # 最近のブレイクアウト
            recent_breakouts = [b for b in breakouts 
                               if (data['timestamp'].iloc[-1] - b.timestamp).days <= 3]
            
            if recent_breakouts:
                print(f"  💥 最近のブレイクアウト ({len(recent_breakouts)}件):")
                for breakout in recent_breakouts[-3:]:  # 最新3件
                    direction_emoji = "⬆️" if breakout.direction == "upward" else "⬇️"
                    confirm_emoji = "✅" if breakout.confirmed else "⚠️"
                    level_type = "レジスタンス" if breakout.level_type == "resistance" else "サポート"
                    
                    print(f"    {direction_emoji} {confirm_emoji} {level_type}{breakout.level_broken:.2f}を"
                          f"{breakout.price:.2f}で{breakout.direction}")
                    print(f"      時刻: {breakout.timestamp.strftime('%m/%d %H:%M')} "
                          f"出来高: {breakout.volume:,.0f}")
            else:
                print("  📊 最近のブレイクアウトなし")
            
            # 現在の注目レベル
            nearest_support = detector._find_nearest_level(levels, current_price, 'support')
            nearest_resistance = detector._find_nearest_level(levels, current_price, 'resistance')
            
            print(f"  📍 注目レベル:")
            if nearest_support:
                print(f"    🟢 サポート: {nearest_support.price:.2f} (強度: {nearest_support.strength:.2f})")
            if nearest_resistance:
                print(f"    🔴 レジスタンス: {nearest_resistance.price:.2f} (強度: {nearest_resistance.strength:.2f})")
            
        except Exception as e:
            print(f"  ❌ エラー: {e}")


def comprehensive_analysis_demo():
    """総合サポレジ分析デモ"""
    print("\n" + "=" * 70)
    print("総合サポート・レジスタンス分析デモ")
    print("=" * 70)
    
    collector = StockDataCollector()
    
    try:
        # より長期間のデータで総合分析
        symbol = "7203.T"
        data = collector.get_stock_data(symbol, interval="1d", period="6mo")
        
        if data is None or len(data) < 100:
            print("総合分析に十分なデータがありません")
            return
        
        print(f"銘柄: {symbol}")
        print(f"分析期間: {data['timestamp'].min().date()} 〜 {data['timestamp'].max().date()}")
        print(f"データ件数: {len(data)}件")
        
        # 総合分析実行
        detector = SupportResistanceDetector(data, min_touches=3, tolerance_percent=1.0)
        analysis = detector.comprehensive_analysis()
        
        print(f"\n📋 総合分析結果 ({analysis['timestamp'].strftime('%Y-%m-%d')})")
        print("=" * 60)
        
        # 基本情報
        print(f"💰 現在価格: {analysis['current_price']:.2f}")
        print(f"📊 市場状況: {analysis['market_condition']}")
        
        # 主要レベル
        levels = analysis['support_resistance_levels']
        if levels:
            print(f"\n🎯 主要サポート・レジスタンスレベル (上位5件):")
            for i, level in enumerate(levels[:5], 1):
                distance = ((level.price - analysis['current_price']) / analysis['current_price']) * 100
                type_emoji = "🔴" if level.level_type == "resistance" else "🟢"
                print(f"  {i}. {type_emoji} {level.price:.2f} ({distance:+5.1f}%) "
                      f"強度:{level.strength:.2f} 信頼度:{level.confidence:.2f}")
        
        # ピボットポイント情報
        pivots = analysis['pivot_points']
        print(f"\n📊 ピボットポイント:")
        print(f"  中央値: {pivots.pivot:.2f}")
        print(f"  主要レジスタンス(R1): {pivots.resistance_levels['R1']:.2f}")
        print(f"  主要サポート(S1): {pivots.support_levels['S1']:.2f}")
        
        # 最近のブレイクアウト
        breakouts = analysis['recent_breakouts']
        if breakouts:
            print(f"\n💥 最近のブレイクアウト:")
            for breakout in breakouts:
                direction_emoji = "⬆️" if breakout.direction == "upward" else "⬇️"
                confirm_emoji = "✅" if breakout.confirmed else "⚠️"
                print(f"  {direction_emoji} {confirm_emoji} {breakout.level_broken:.2f}レベル "
                      f"({breakout.timestamp.strftime('%m/%d')})")
        
        # トレーディング推奨
        recommendations = analysis['trading_recommendations']
        if recommendations:
            print(f"\n💡 トレーディング推奨:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        # 時間帯分析（簡略版）
        time_analysis = analysis['time_based_analysis']
        print(f"\n⏰ 時間帯別分析（主要セッション）:")
        
        sessions = ['asian_session', 'european_session', 'us_session']
        for session in sessions:
            if session in time_analysis:
                session_data = time_analysis[session]
                session_name = {
                    'asian_session': 'アジア',
                    'european_session': '欧州', 
                    'us_session': '米国'
                }[session]
                
                print(f"  {session_name}セッション: {session_data['total_bars']}件 "
                      f"平均出来高:{session_data['avg_volume']:,.0f}")
        
    except Exception as e:
        logger.error(f"総合分析エラー: {e}")


def custom_analysis_demo():
    """カスタム分析デモ"""
    print("\n" + "=" * 70)
    print("カスタムサポレジ分析デモ")
    print("=" * 70)
    
    collector = StockDataCollector()
    
    try:
        symbol = "MSFT"
        data = collector.get_stock_data(symbol, interval="4h", period="1mo")
        
        if data is None or len(data) < 30:
            print("データが不足しています")
            return
        
        print(f"銘柄: {symbol}")
        print(f"分析データ: {len(data)}件 (4時間足)")
        
        # カスタムパラメータでの分析
        detector = SupportResistanceDetector(
            data, 
            min_touches=2,          # 少ないタッチでも検出
            tolerance_percent=1.2,  # やや緩い許容誤差
            lookback_period=30      # 短期間フォーカス
        )
        
        # 高感度検出
        levels = detector.detect_support_resistance_levels(min_strength=0.15, max_levels=12)
        
        current_price = data['close'].iloc[-1]
        print(f"\n💰 現在価格: ${current_price:.2f}")
        
        # レベル強度分析
        print(f"\n🔍 詳細レベル分析:")
        print(f"{'No':<3} {'Type':<11} {'Price':<8} {'距離%':<6} {'強度':<6} {'信頼度':<6} {'タッチ':<5}")
        print("-" * 50)
        
        for i, level in enumerate(levels[:8], 1):
            distance = ((level.price - current_price) / current_price) * 100
            print(f"{i:<3} {level.level_type:<11} ${level.price:<7.2f} {distance:>+5.1f}% "
                  f"{level.strength:<6.3f} {level.confidence:<6.3f} {level.touch_count:<5}")
        
        # 価格帯分析
        print(f"\n📈 価格帯分析:")
        support_levels = [l for l in levels if l.level_type == 'support']
        resistance_levels = [l for l in levels if l.level_type == 'resistance']
        
        if support_levels and resistance_levels:
            strongest_support = max(support_levels, key=lambda x: x.strength)
            strongest_resistance = max(resistance_levels, key=lambda x: x.strength)
            
            range_size = strongest_resistance.price - strongest_support.price
            range_percent = (range_size / current_price) * 100
            
            print(f"  主要レンジ: ${strongest_support.price:.2f} - ${strongest_resistance.price:.2f}")
            print(f"  レンジ幅: {range_percent:.1f}%")
            
            # 現在位置
            position_in_range = (current_price - strongest_support.price) / range_size
            if position_in_range < 0.3:
                position_desc = "レンジ下部"
            elif position_in_range > 0.7:
                position_desc = "レンジ上部"
            else:
                position_desc = "レンジ中央"
            
            print(f"  現在位置: {position_desc} ({position_in_range*100:.0f}%)")
        
        # 出来高プロファイル（簡易版）
        print(f"\n📊 価格帯別出来高分析:")
        price_bins = pd.cut(data['close'], bins=5, precision=2)
        volume_profile = data.groupby(price_bins)['volume'].sum()
        
        for price_range, volume in volume_profile.items():
            range_str = f"${price_range.left:.2f}-${price_range.right:.2f}"
            print(f"  {range_str:<15}: {volume:>12,.0f}")
        
        # ブレイクアウト可能性
        print(f"\n⚡ ブレイクアウト可能性:")
        recent_volatility = ((data['high'] - data['low']) / data['close']).tail(10).mean() * 100
        print(f"  最近のボラティリティ: {recent_volatility:.2f}%")
        
        if recent_volatility < 2:
            print("  🔸 低ボラティリティ - ブレイクアウト待ち")
        elif recent_volatility > 5:
            print("  🔥 高ボラティリティ - ブレイクアウト継続中")
        else:
            print("  📊 通常ボラティリティ")
        
    except Exception as e:
        logger.error(f"カスタム分析エラー: {e}")


def main():
    """メイン実行関数"""
    print("🎯 サポート・レジスタンス検出システム デモンストレーション")
    print("デイトレード用価格水準分析ライブラリ")
    
    try:
        # 各デモを実行
        basic_support_resistance_demo()
        pivot_points_demo()
        breakout_detection_demo()
        comprehensive_analysis_demo()
        custom_analysis_demo()
        
        print("\n" + "=" * 70)
        print("🎉 サポート・レジスタンス分析デモ完了")
        print("=" * 70)
        
        print("\n💡 利用可能な主要機能:")
        print("🎯 自動レベル検出: スイング高値・安値の自動識別")
        print("🔍 価格クラスター: 類似価格レベルのグループ化")
        print("📊 ピボットポイント: 標準・カマリラピボット計算")
        print("💥 ブレイクアウト検出: リアルタイム突破判定")
        print("⏰ 時間帯分析: セッション別強度評価")
        print("🏆 強度スコア: 出来高・タッチ回数総合評価")
        print("💡 自動推奨: エントリー・ストップロス提案")
        
    except KeyboardInterrupt:
        print("\n\nデモが中断されました")
    except Exception as e:
        logger.error(f"デモ実行エラー: {e}")


if __name__ == "__main__":
    main()