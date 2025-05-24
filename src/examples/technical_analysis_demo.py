"""
テクニカル分析デモスクリプト
TechnicalIndicatorsクラスの使用例とデイトレード分析デモ
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
from src.technical_analysis.indicators import TechnicalIndicators
from src.config.settings import settings_manager
from loguru import logger


def basic_technical_analysis_demo():
    """基本テクニカル分析デモ"""
    print("=" * 60)
    print("基本テクニカル分析デモ")
    print("=" * 60)
    
    # 設定とログの初期化
    settings_manager.setup_logging()
    
    # データ収集
    collector = StockDataCollector()
    symbol_manager = SymbolManager()
    
    # トヨタ自動車のデータを取得
    symbol = "7203.T"
    print(f"銘柄: {symbol}")
    
    try:
        # 5分足データを1日分取得
        data = collector.get_stock_data(symbol, interval="5m", period="1d")
        
        if data is None or len(data) < 50:
            print("十分なデータが取得できませんでした")
            return
        
        print(f"取得データ: {len(data)}件")
        print(f"期間: {data['timestamp'].min()} 〜 {data['timestamp'].max()}")
        
        # テクニカル指標計算
        indicators = TechnicalIndicators(data)
        
        # 移動平均
        ma_set = indicators.moving_averages()
        print(f"\n📈 移動平均（最新値）:")
        print(f"  SMA(25): {ma_set['sma_25'].iloc[-1]:.2f}")
        print(f"  SMA(75): {ma_set['sma_75'].iloc[-1]:.2f}")
        print(f"  EMA(9):  {ma_set['ema_9'].iloc[-1]:.2f}")
        print(f"  EMA(21): {ma_set['ema_21'].iloc[-1]:.2f}")
        print(f"  現在価格: {data['close'].iloc[-1]:.2f}")
        
        # RSI
        rsi = indicators.rsi()
        current_rsi = rsi.iloc[-1]
        print(f"\n📊 RSI(14): {current_rsi:.2f}")
        if current_rsi > 70:
            print("  → 過買い水準")
        elif current_rsi < 30:
            print("  → 過売り水準")
        else:
            print("  → 中立水準")
        
        # ストキャスティクス
        stoch = indicators.stochastic()
        print(f"\n🎯 ストキャスティクス:")
        print(f"  %K(14): {stoch['stoch_k'].iloc[-1]:.2f}")
        print(f"  %D(3):  {stoch['stoch_d'].iloc[-1]:.2f}")
        
        # MACD
        macd_data = indicators.macd()
        print(f"\n📈 MACD:")
        print(f"  MACD: {macd_data['macd'].iloc[-1]:.4f}")
        print(f"  シグナル: {macd_data['macd_signal'].iloc[-1]:.4f}")
        print(f"  ヒストグラム: {macd_data['macd_histogram'].iloc[-1]:.4f}")
        
        # ボリンジャーバンド
        bb = indicators.bollinger_bands()
        current_price = data['close'].iloc[-1]
        print(f"\n📏 ボリンジャーバンド:")
        print(f"  上限: {bb['bb_upper'].iloc[-1]:.2f}")
        print(f"  中央: {bb['bb_middle'].iloc[-1]:.2f}")
        print(f"  下限: {bb['bb_lower'].iloc[-1]:.2f}")
        print(f"  %B: {bb['bb_percent_b'].iloc[-1]:.3f}")
        
        # VWAP
        vwap_analysis = indicators.vwap_analysis()
        print(f"\n💰 VWAP分析:")
        print(f"  VWAP: {vwap_analysis['vwap'].iloc[-1]:.2f}")
        print(f"  価格 vs VWAP: {vwap_analysis['current_price_vs_vwap']}")
        print(f"  乖離率: {vwap_analysis['vwap_deviation_current']:.2f}%")
        
        # ATR
        vol_analysis = indicators.volatility_analysis()
        print(f"\n📊 ボラティリティ:")
        print(f"  ATR(14): {vol_analysis['current_atr']:.2f}")
        print(f"  ATR比率: {vol_analysis['atr_ratio'].iloc[-1]:.2f}%")
        print(f"  ボラティリティレベル: {vol_analysis['current_volatility_level']}")
        
    except Exception as e:
        logger.error(f"エラー: {e}")


def trading_signals_demo():
    """トレーディングシグナルデモ"""
    print("\n" + "=" * 60)
    print("トレーディングシグナル分析デモ")
    print("=" * 60)
    
    collector = StockDataCollector()
    symbol_manager = SymbolManager()
    
    # 複数銘柄で分析
    symbols = ["7203.T", "AAPL", "MSFT"]
    
    for symbol in symbols:
        try:
            print(f"\n🎯 {symbol} のシグナル分析")
            print("-" * 40)
            
            # データ取得
            data = collector.get_stock_data(symbol, interval="5m", period="1d")
            
            if data is None or len(data) < 50:
                print("  データ不足")
                continue
            
            # シグナル計算
            indicators = TechnicalIndicators(data)
            signals = indicators.get_trading_signals()
            
            # 買いシグナル
            buy_signals = []
            if signals['rsi_oversold']:
                buy_signals.append("RSI過売り")
            if signals['stoch_oversold']:
                buy_signals.append("ストキャス過売り")
            if signals['macd_bullish']:
                buy_signals.append("MACDゴールデンクロス")
            if signals['price_above_vwap']:
                buy_signals.append("VWAP上抜け")
            if signals['bb_lower_return']:
                buy_signals.append("下部バンド反発")
            
            # 売りシグナル
            sell_signals = []
            if signals['rsi_overbought']:
                sell_signals.append("RSI過買い")
            if signals['stoch_overbought']:
                sell_signals.append("ストキャス過買い")
            if signals['macd_bearish']:
                sell_signals.append("MACDデッドクロス")
            if signals['price_below_vwap']:
                sell_signals.append("VWAP下抜け")
            if signals['bb_upper_return']:
                sell_signals.append("上部バンド反発")
            
            # 結果表示
            current_price = data['close'].iloc[-1]
            print(f"  現在価格: {current_price:.2f}")
            
            if buy_signals:
                print(f"  🟢 買いシグナル: {', '.join(buy_signals)}")
            
            if sell_signals:
                print(f"  🔴 売りシグナル: {', '.join(sell_signals)}")
            
            if not buy_signals and not sell_signals:
                print("  ⚪ 明確なシグナルなし")
            
            # 特殊状況
            if signals['bb_squeeze']:
                print("  ⚠️  ボリンジャーバンドスクイーズ（ブレイクアウト待ち）")
            
        except Exception as e:
            logger.error(f"{symbol} 分析エラー: {e}")


def comprehensive_analysis_demo():
    """総合分析デモ"""
    print("\n" + "=" * 60)
    print("総合テクニカル分析デモ")
    print("=" * 60)
    
    collector = StockDataCollector()
    
    try:
        # より多くのデータで分析（日足）
        symbol = "7203.T"
        data = collector.get_stock_data(symbol, interval="1d", period="3mo")
        
        if data is None or len(data) < 100:
            print("十分なデータが取得できませんでした")
            return
        
        print(f"銘柄: {symbol}")
        print(f"分析期間: {data['timestamp'].min().date()} 〜 {data['timestamp'].max().date()}")
        print(f"データ件数: {len(data)}件")
        
        # 総合分析実行
        indicators = TechnicalIndicators(data)
        analysis = indicators.comprehensive_analysis()
        
        print(f"\n📋 総合分析結果 ({analysis['timestamp'].strftime('%Y-%m-%d %H:%M')})")
        print("=" * 50)
        
        # 現在値サマリー
        current = analysis['current_values']
        ohlcv = analysis['ohlcv']
        
        print(f"💰 価格情報:")
        print(f"  始値: {ohlcv['open']:.2f}")
        print(f"  高値: {ohlcv['high']:.2f}")
        print(f"  安値: {ohlcv['low']:.2f}")
        print(f"  終値: {ohlcv['close']:.2f}")
        print(f"  出来高: {ohlcv['volume']:,}")
        
        print(f"\n📊 テクニカル指標:")
        print(f"  RSI(14): {current['rsi_current']:.2f}")
        print(f"  ストキャス%K: {current['stoch_k_current']:.2f}")
        print(f"  ストキャス%D: {current['stoch_d_current']:.2f}")
        print(f"  MACD: {current['macd_current']:.4f}")
        print(f"  MACDシグナル: {current['macd_signal_current']:.4f}")
        print(f"  ボリンジャー%B: {current['bb_percent_b_current']:.3f}")
        print(f"  ATR: {current['atr_current']:.2f}")
        
        # トレンド分析
        ma = analysis['moving_averages']
        close = ohlcv['close']
        
        print(f"\n📈 トレンド分析:")
        print(f"  価格 vs SMA25: {'上' if close > ma['sma_25'].iloc[-1] else '下'}")
        print(f"  価格 vs SMA75: {'上' if close > ma['sma_75'].iloc[-1] else '下'}")
        print(f"  EMA9 vs EMA21: {'上' if ma['ema_9'].iloc[-1] > ma['ema_21'].iloc[-1] else '下'}")
        
        # VWAP分析
        vwap = analysis['vwap_analysis']
        print(f"\n💎 VWAP分析:")
        print(f"  価格 vs VWAP: {vwap['current_price_vs_vwap']}")
        print(f"  乖離率: {vwap['vwap_deviation_current']:.2f}%")
        
        # ボラティリティ
        vol = analysis['volatility_analysis']
        print(f"\n⚡ ボラティリティ:")
        print(f"  レベル: {vol['current_volatility_level']}")
        print(f"  ATR比率: {vol['avg_atr_ratio']:.2f}%")
        
        # 総合判定
        print(f"\n🎯 総合判定:")
        signals = indicators.get_trading_signals()
        
        buy_count = sum([
            signals['rsi_oversold'],
            signals['stoch_oversold'], 
            signals['macd_bullish'],
            signals['price_above_vwap'],
            signals['bb_lower_return']
        ])
        
        sell_count = sum([
            signals['rsi_overbought'],
            signals['stoch_overbought'],
            signals['macd_bearish'], 
            signals['price_below_vwap'],
            signals['bb_upper_return']
        ])
        
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
        
        print(f"  買いシグナル数: {buy_count}/5")
        print(f"  売りシグナル数: {sell_count}/5")
        
    except Exception as e:
        logger.error(f"総合分析エラー: {e}")


def multi_timeframe_analysis_demo():
    """マルチタイムフレーム分析デモ"""
    print("\n" + "=" * 60)
    print("マルチタイムフレーム分析デモ")
    print("=" * 60)
    
    collector = StockDataCollector()
    symbol = "7203.T"
    
    timeframes = [
        ("1m", "1d", "1分足"),
        ("5m", "1d", "5分足"),
        ("1h", "1mo", "1時間足"),
        ("1d", "3mo", "日足")
    ]
    
    print(f"銘柄: {symbol}")
    print("タイムフレーム別RSI比較:")
    print("-" * 40)
    
    for interval, period, name in timeframes:
        try:
            data = collector.get_stock_data(symbol, interval=interval, period=period)
            
            if data is None or len(data) < 20:
                print(f"{name}: データ不足")
                continue
            
            indicators = TechnicalIndicators(data)
            rsi = indicators.rsi().iloc[-1]
            
            # RSIレベルの判定
            if rsi > 70:
                level = "過買い 🔴"
            elif rsi < 30:
                level = "過売り 🟢"
            else:
                level = "中立 ⚪"
            
            print(f"{name:8}: RSI {rsi:5.1f} ({level})")
            
        except Exception as e:
            print(f"{name}: エラー - {e}")
    
    print("\n💡 マルチタイムフレーム戦略:")
    print("- 長期足で方向性を確認")
    print("- 中期足でエントリータイミングを判断") 
    print("- 短期足で精密なエントリーポイントを特定")


def custom_indicators_demo():
    """カスタム指標デモ"""
    print("\n" + "=" * 60)
    print("カスタム指標・応用分析デモ")
    print("=" * 60)
    
    collector = StockDataCollector()
    
    try:
        symbol = "AAPL"
        data = collector.get_stock_data(symbol, interval="1d", period="3mo")
        
        if data is None or len(data) < 50:
            print("データが不足しています")
            return
        
        indicators = TechnicalIndicators(data)
        
        print(f"銘柄: {symbol}")
        print(f"分析データ: {len(data)}件")
        
        # カスタム移動平均組み合わせ
        print(f"\n🔧 カスタム移動平均分析:")
        ema_12 = indicators.ema(12)
        ema_26 = indicators.ema(26)
        sma_50 = indicators.sma(50)
        
        print(f"  EMA12: {ema_12.iloc[-1]:.2f}")
        print(f"  EMA26: {ema_26.iloc[-1]:.2f}")
        print(f"  SMA50: {sma_50.iloc[-1]:.2f}")
        
        # トレンド判定
        current_price = data['close'].iloc[-1]
        if current_price > ema_12.iloc[-1] > ema_26.iloc[-1] > sma_50.iloc[-1]:
            print("  📈 強い上昇トレンド")
        elif current_price < ema_12.iloc[-1] < ema_26.iloc[-1] < sma_50.iloc[-1]:
            print("  📉 強い下降トレンド")
        else:
            print("  📊 レンジまたは転換点")
        
        # ボラティリティブレイクアウト分析
        print(f"\n⚡ ボラティリティ分析:")
        atr_20 = indicators.atr(20)
        atr_current = atr_20.iloc[-1]
        atr_avg = atr_20.rolling(50).mean().iloc[-1]
        
        vol_expansion = atr_current / atr_avg
        print(f"  ATR: {atr_current:.2f}")
        print(f"  ATR50日平均: {atr_avg:.2f}")
        print(f"  ボラティリティ比率: {vol_expansion:.2f}")
        
        if vol_expansion > 1.5:
            print("  🔥 ボラティリティ拡大中（ブレイクアウトの可能性）")
        elif vol_expansion < 0.7:
            print("  😴 ボラティリティ収縮中（レンジ相場）")
        else:
            print("  📊 通常レベル")
        
        # モメンタム分析
        print(f"\n🚀 モメンタム分析:")
        rsi = indicators.rsi()
        rsi_current = rsi.iloc[-1]
        rsi_trend = rsi.iloc[-1] - rsi.iloc[-5]  # 5期間前との比較
        
        stoch = indicators.stochastic()
        stoch_k = stoch['stoch_k'].iloc[-1]
        
        print(f"  RSI: {rsi_current:.2f} (5期間変化: {rsi_trend:+.2f})")
        print(f"  ストキャス%K: {stoch_k:.2f}")
        
        # モメンタム判定
        if rsi_current > 50 and rsi_trend > 0 and stoch_k > 50:
            print("  ⬆️  上昇モメンタム")
        elif rsi_current < 50 and rsi_trend < 0 and stoch_k < 50:
            print("  ⬇️  下降モメンタム")
        else:
            print("  ↔️  中立モメンタム")
        
    except Exception as e:
        logger.error(f"カスタム分析エラー: {e}")


def main():
    """メイン実行関数"""
    print("🎯 テクニカル分析システム デモンストレーション")
    print("デイトレード用テクニカル指標ライブラリ")
    
    try:
        # 各デモを実行
        basic_technical_analysis_demo()
        trading_signals_demo()
        comprehensive_analysis_demo()
        multi_timeframe_analysis_demo()
        custom_indicators_demo()
        
        print("\n" + "=" * 60)
        print("🎉 テクニカル分析デモ完了")
        print("=" * 60)
        
        print("\n💡 利用可能な主要機能:")
        print("📈 移動平均: SMA, EMA (複数期間)")
        print("📊 オシレーター: RSI, ストキャスティクス")
        print("🎯 トレンド: MACD, シグナル検出")
        print("📏 バンド: ボリンジャーバンド, スクイーズ検出")
        print("💰 価格: VWAP, 乖離分析")
        print("⚡ ボラティリティ: ATR, リスク測定")
        print("🚀 総合シグナル: 複数指標組み合わせ判定")
        
    except KeyboardInterrupt:
        print("\n\nデモが中断されました")
    except Exception as e:
        logger.error(f"デモ実行エラー: {e}")


if __name__ == "__main__":
    main()