"""
エントリーシグナル生成デモスクリプト
SignalGeneratorクラスの使用例とバックテスト分析デモ
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.data_collector.stock_data_collector import StockDataCollector
from src.data_collector.symbol_manager import SymbolManager, MarketType
from src.technical_analysis.signal_generator import (
    SignalGenerator, 
    SignalRule, 
    FilterCriteria,
    SignalType
)
from src.config.settings import settings_manager
from loguru import logger


def basic_signal_generation_demo():
    """基本シグナル生成デモ"""
    print("=" * 70)
    print("基本エントリーシグナル生成デモ")
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
        # 1時間足データを1ヶ月分取得（シグナル生成に十分な期間）
        data = collector.get_stock_data(symbol, interval="1h", period="3mo")
        
        if data is None or len(data) < 100:
            print("シグナル生成に十分なデータが取得できませんでした")
            return
        
        print(f"取得データ: {len(data)}件")
        print(f"期間: {data['timestamp'].min()} 〜 {data['timestamp'].max()}")
        
        # シグナル生成器初期化
        generator = SignalGenerator(data)
        
        # シグナル生成
        print(f"\n🎯 シグナル生成中...")
        signals = generator.generate_signals()
        
        current_price = data['close'].iloc[-1]
        print(f"\n💰 現在価格: {current_price:.2f}")
        print(f"🎯 生成されたシグナル: {len(signals)}件")
        
        if not signals:
            print("シグナルが生成されませんでした")
            return
        
        # 最新シグナル（上位5件）
        recent_signals = sorted(signals, key=lambda x: x.timestamp, reverse=True)[:5]
        
        print(f"\n📊 最新シグナル (上位5件):")
        print("-" * 60)
        print(f"{'日時':<12} {'タイプ':<4} {'強度':<4} {'価格':<8} {'リスク':<6} {'信頼度':<6}")
        print("-" * 60)
        
        for signal in recent_signals:
            signal_emoji = "🟢" if signal.signal_type == SignalType.BUY else "🔴"
            signal_type = "買い" if signal.signal_type == SignalType.BUY else "売り"
            
            print(f"{signal.timestamp.strftime('%m/%d %H:%M')} "
                  f"{signal_emoji}{signal_type} "
                  f"{signal.strength:5.1f} "
                  f"{signal.price:8.2f} "
                  f"{signal.risk_level:6} "
                  f"{signal.confidence:6.3f}")
        
        # 強度別分布
        analysis = generator.analyze_signal_performance(signals)
        print(f"\n📈 シグナル分析:")
        print(f"  買いシグナル: {analysis['signal_types']['buy']}件")
        print(f"  売りシグナル: {analysis['signal_types']['sell']}件")
        print(f"  平均強度: {analysis['avg_strength']:.1f}")
        print(f"  平均信頼度: {analysis['avg_confidence']:.3f}")
        print(f"  強度分布: 弱{analysis['strength_distribution']['weak']} / "
              f"中{analysis['strength_distribution']['moderate']} / "
              f"強{analysis['strength_distribution']['strong']}")
        
        # 最新の強いシグナル
        strong_signals = [s for s in recent_signals if s.strength >= 70]
        if strong_signals:
            print(f"\n💪 強いシグナル詳細:")
            latest_strong = strong_signals[0]
            print(f"  タイプ: {latest_strong.signal_type.value}")
            print(f"  強度: {latest_strong.strength:.1f}")
            print(f"  価格: {latest_strong.price:.2f}")
            if latest_strong.stop_loss:
                print(f"  ストップロス: {latest_strong.stop_loss:.2f}")
            if latest_strong.take_profit:
                print(f"  利確目標: {latest_strong.take_profit:.2f}")
            print(f"  ノート: {latest_strong.notes}")
        
    except Exception as e:
        logger.error(f"エラー: {e}")


def filtered_signal_demo():
    """フィルタリング機能デモ"""
    print("\n" + "=" * 70)
    print("フィルタリング機能デモ")
    print("=" * 70)
    
    collector = StockDataCollector()
    
    try:
        # Apple株で分析（出来高の多い銘柄）
        symbol = "AAPL"
        data = collector.get_stock_data(symbol, interval="1h", period="2mo")
        
        if data is None or len(data) < 100:
            print("データが不足しています")
            return
        
        print(f"銘柄: {symbol}")
        print(f"分析データ: {len(data)}件")
        
        generator = SignalGenerator(data)
        
        # 通常のシグナル生成
        all_signals = generator.generate_signals()
        print(f"\n📊 全シグナル: {len(all_signals)}件")
        
        # 出来高フィルター適用
        volume_avg = data['volume'].mean()
        volume_filter = FilterCriteria(min_volume=volume_avg * 1.5)  # 平均の1.5倍以上
        
        volume_signals = generator.generate_signals(volume_filter)
        print(f"📊 高出来高フィルター: {len(volume_signals)}件 ({volume_avg*1.5:,.0f}以上)")
        
        # 時間帯フィルター（米国市場時間）
        time_filter = FilterCriteria(allowed_hours=[14, 15, 16, 17, 18, 19, 20, 21])  # 14-21時
        
        time_signals = generator.generate_signals(time_filter)
        print(f"📊 米国時間フィルター: {len(time_signals)}件 (14-21時)")
        
        # ボラティリティフィルター
        volatility_filter = FilterCriteria(min_volatility=0.01, max_volatility=0.03)  # 1-3%
        
        vol_signals = generator.generate_signals(volatility_filter)
        print(f"📊 ボラティリティフィルター: {len(vol_signals)}件 (1-3%)")
        
        # 複合フィルター
        combined_filter = FilterCriteria(
            min_volume=volume_avg * 1.2,
            allowed_hours=[15, 16, 17, 18, 19, 20],
            max_volatility=0.025
        )
        
        combined_signals = generator.generate_signals(combined_filter)
        print(f"📊 複合フィルター: {len(combined_signals)}件")
        
        # フィルター効果の比較
        print(f"\n🔍 フィルター効果:")
        print(f"  フィルターなし: {len(all_signals)}件 (100%)")
        if len(all_signals) > 0:
            print(f"  出来高フィルター: {len(volume_signals)}件 ({len(volume_signals)/len(all_signals)*100:.1f}%)")
            print(f"  時間フィルター: {len(time_signals)}件 ({len(time_signals)/len(all_signals)*100:.1f}%)")
            print(f"  ボラティリティフィルター: {len(vol_signals)}件 ({len(vol_signals)/len(all_signals)*100:.1f}%)")
            print(f"  複合フィルター: {len(combined_signals)}件 ({len(combined_signals)/len(all_signals)*100:.1f}%)")
        
        # フィルタリング後の強度比較
        if combined_signals:
            combined_strength = np.mean([s.strength for s in combined_signals])
            all_strength = np.mean([s.strength for s in all_signals])
            print(f"\n💪 平均強度比較:")
            print(f"  全シグナル: {all_strength:.1f}")
            print(f"  複合フィルター後: {combined_strength:.1f}")
        
    except Exception as e:
        logger.error(f"フィルタリングデモエラー: {e}")


def backtest_demo():
    """バックテストデモ"""
    print("\n" + "=" * 70)
    print("バックテスト分析デモ")
    print("=" * 70)
    
    collector = StockDataCollector()
    
    try:
        # Microsoft株で長期バックテスト
        symbol = "MSFT"
        data = collector.get_stock_data(symbol, interval="1d", period="6mo")
        
        if data is None or len(data) < 150:
            print("バックテストに十分なデータがありません")
            return
        
        print(f"銘柄: {symbol}")
        print(f"バックテストデータ: {len(data)}件")
        print(f"期間: {data['timestamp'].min().date()} 〜 {data['timestamp'].max().date()}")
        
        generator = SignalGenerator(data)
        
        # シグナル生成
        signals = generator.generate_signals()
        print(f"\nシグナル生成: {len(signals)}件")
        
        if len(signals) == 0:
            print("バックテスト用シグナルがありません")
            return
        
        # バックテスト実行（複数の保有期間）
        holding_periods = [5, 10, 20]  # 5日、10日、20日
        
        print(f"\n📈 バックテスト結果:")
        print("-" * 60)
        print(f"{'期間':<6} {'勝率':<8} {'平均リターン':<12} {'最大DD':<10} {'シャープ':<8} {'PF':<6}")
        print("-" * 60)
        
        best_result = None
        best_score = -999
        
        for period in holding_periods:
            result = generator.backtest_signals(signals, holding_period=period)
            
            print(f"{period:3d}日 "
                  f"{result.win_rate*100:6.1f}% "
                  f"{result.avg_return_per_signal*100:+9.2f}% "
                  f"{result.max_drawdown*100:7.1f}% "
                  f"{result.sharpe_ratio:+7.2f} "
                  f"{result.profit_factor:5.2f}")
            
            # 最良結果を記録（シャープレシオベース）
            if result.sharpe_ratio > best_score:
                best_score = result.sharpe_ratio
                best_result = result
        
        # 最良結果の詳細分析
        if best_result:
            print(f"\n🏆 最良結果詳細:")
            print(f"  総取引: {best_result.total_signals}回")
            print(f"  勝ち: {best_result.winning_signals}回")
            print(f"  負け: {best_result.losing_signals}回")
            print(f"  勝率: {best_result.win_rate*100:.1f}%")
            print(f"  平均リターン: {best_result.avg_return_per_signal*100:+.2f}%")
            print(f"  最大ドローダウン: {best_result.max_drawdown*100:.1f}%")
            print(f"  シャープレシオ: {best_result.sharpe_ratio:.2f}")
            print(f"  プロフィットファクター: {best_result.profit_factor:.2f}")
            
            # 取引詳細（最新5件）
            recent_trades = best_result.signals_detail[-5:]
            print(f"\n📋 最新取引 (5件):")
            print("-" * 50)
            for trade in recent_trades:
                entry_date = trade['entry_time'].strftime('%m/%d')
                signal_type = "買い" if trade['signal_type'] == 'buy' else "売り"
                return_pct = trade['return'] * 100
                result_emoji = "✅" if trade['return'] > 0 else "❌"
                
                print(f"{entry_date} {signal_type} {trade['entry_price']:.2f} → "
                      f"{trade['exit_price']:.2f} {return_pct:+5.1f}% {result_emoji}")
    
    except Exception as e:
        logger.error(f"バックテストエラー: {e}")


def custom_rules_demo():
    """カスタムルールデモ"""
    print("\n" + "=" * 70)
    print("カスタムルール設定デモ")
    print("=" * 70)
    
    collector = StockDataCollector()
    
    try:
        symbol = "7203.T"
        data = collector.get_stock_data(symbol, interval="4h", period="2mo")
        
        if data is None or len(data) < 80:
            print("データが不足しています")
            return
        
        print(f"銘柄: {symbol}")
        print(f"分析データ: {len(data)}件 (4時間足)")
        
        generator = SignalGenerator(data)
        
        # デフォルトルールでのシグナル生成
        default_signals = generator.generate_signals()
        print(f"\n📊 デフォルトルール: {len(default_signals)}シグナル")
        
        # カスタムルールセット作成
        print(f"\n🛠️  カスタムルール作成:")
        
        custom_rules = {
            # シンプルなトレンドフォロー戦略
            'strong_trend_buy': SignalRule(
                name="強いトレンド買い",
                description="EMA9 > EMA21 かつ RSI 40-60",
                conditions=[
                    {'indicator': 'ema_9', 'operator': '>', 'compare_to': 'ema_21'},
                    {'indicator': 'rsi_current', 'operator': '>', 'value': 40},
                    {'indicator': 'rsi_current', 'operator': '<', 'value': 60},
                    {'indicator': 'close_change', 'operator': '>', 'value': 0.002}
                ],
                weight=3.0,
                category="trend_follow"
            ),
            
            'strong_trend_sell': SignalRule(
                name="強いトレンド売り",
                description="EMA9 < EMA21 かつ RSI 40-60",
                conditions=[
                    {'indicator': 'ema_9', 'operator': '<', 'compare_to': 'ema_21'},
                    {'indicator': 'rsi_current', 'operator': '>', 'value': 40},
                    {'indicator': 'rsi_current', 'operator': '<', 'value': 60},
                    {'indicator': 'close_change', 'operator': '<', 'value': -0.002}
                ],
                weight=3.0,
                category="trend_follow"
            ),
            
            # 逆張り戦略
            'oversold_bounce': SignalRule(
                name="過売り反発",
                description="RSI < 25 から30以上への回復",
                conditions=[
                    {'indicator': 'rsi_current', 'operator': '>', 'value': 30},
                    {'indicator': 'rsi_previous', 'operator': '<', 'value': 25},
                    {'indicator': 'volume_ratio', 'operator': '>', 'value': 1.2}
                ],
                weight=2.5,
                category="mean_revert"
            ),
            
            'overbought_decline': SignalRule(
                name="過買い下落",
                description="RSI > 75 から70以下への下落",
                conditions=[
                    {'indicator': 'rsi_current', 'operator': '<', 'value': 70},
                    {'indicator': 'rsi_previous', 'operator': '>', 'value': 75},
                    {'indicator': 'volume_ratio', 'operator': '>', 'value': 1.2}
                ],
                weight=2.5,
                category="mean_revert"
            )
        }
        
        # カスタムルールでシグナル生成
        custom_signals = generator.generate_signals(custom_rules=custom_rules)
        print(f"📊 カスタムルール: {len(custom_signals)}シグナル")
        
        # 両方のバックテスト比較
        print(f"\n⚖️  戦略比較 (10日保有):")
        print("-" * 50)
        
        if default_signals:
            default_bt = generator.backtest_signals(default_signals, holding_period=10)
            print(f"デフォルト戦略:")
            print(f"  勝率: {default_bt.win_rate*100:.1f}%")
            print(f"  平均リターン: {default_bt.avg_return_per_signal*100:+.2f}%")
            print(f"  シャープレシオ: {default_bt.sharpe_ratio:.2f}")
        
        if custom_signals:
            custom_bt = generator.backtest_signals(custom_signals, holding_period=10)
            print(f"カスタム戦略:")
            print(f"  勝率: {custom_bt.win_rate*100:.1f}%")
            print(f"  平均リターン: {custom_bt.avg_return_per_signal*100:+.2f}%")
            print(f"  シャープレシオ: {custom_bt.sharpe_ratio:.2f}")
        
        # ルール保存・読み込みデモ
        print(f"\n💾 ルール保存・読み込みデモ:")
        
        # カスタムルールを追加
        for name, rule in custom_rules.items():
            generator.add_custom_rule(name, rule)
        
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            generator.save_rules_to_file(temp_file)
            print(f"  ルールセット保存完了")
            
            # 新しいジェネレーターで読み込み
            new_generator = SignalGenerator(data)
            original_count = len(new_generator.rules)
            
            new_generator.load_rules_from_file(temp_file)
            loaded_count = len(new_generator.rules)
            
            print(f"  ルールセット読み込み完了: {original_count} → {loaded_count}ルール")
            
        finally:
            # 一時ファイル削除
            Path(temp_file).unlink(missing_ok=True)
        
    except Exception as e:
        logger.error(f"カスタムルールデモエラー: {e}")


def rule_optimization_demo():
    """ルール最適化デモ"""
    print("\n" + "=" * 70)
    print("ルール重要度分析デモ")
    print("=" * 70)
    
    collector = StockDataCollector()
    
    try:
        symbol = "AAPL"
        data = collector.get_stock_data(symbol, interval="1d", period="3mo")
        
        if data is None or len(data) < 100:
            print("データが不足しています")
            return
        
        print(f"銘柄: {symbol}")
        print(f"最適化データ: {len(data)}件")
        
        generator = SignalGenerator(data)
        
        # 最適化実行（簡易版 - 一部ルールのみ）
        print(f"\n🔧 ルール重要度分析実行中...")
        
        # テスト用にルール数を制限
        original_rules = generator.rules.copy()
        test_rules = {k: v for i, (k, v) in enumerate(original_rules.items()) if i < 5}
        generator.rules = test_rules
        
        optimization = generator.optimize_rules('sharpe_ratio')
        
        print(f"\n📊 ルール重要度ランキング (シャープレシオベース):")
        print("-" * 50)
        
        rule_importance = optimization['rule_importance']
        baseline_score = optimization['baseline_score']
        
        print(f"ベースライン スコア: {baseline_score:.3f}")
        print()
        
        for i, (rule_name, importance) in enumerate(rule_importance.items(), 1):
            impact = "向上" if importance > 0 else "悪化"
            impact_emoji = "📈" if importance > 0 else "📉"
            
            print(f"{i}. {rule_name}")
            print(f"   重要度: {importance:+.3f} {impact_emoji} ({impact})")
        
        if optimization['most_important']:
            most_important = optimization['most_important']
            print(f"\n🏆 最重要ルール: {most_important[0]}")
            print(f"   スコア影響: {most_important[1]:+.3f}")
        
        if optimization['least_important']:
            least_important = optimization['least_important']
            print(f"\n⚠️  最低重要ルール: {least_important[0]}")
            print(f"   スコア影響: {least_important[1]:+.3f}")
        
        # ルール管理デモ
        print(f"\n🛠️  ルール管理デモ:")
        
        # 重要度の低いルールを無効化
        if least_important and least_important[1] < 0:
            rule_to_disable = least_important[0]
            generator.enable_rule(rule_to_disable, False)
            print(f"  {rule_to_disable} を無効化")
            
            # 無効化後の性能確認
            optimized_signals = generator.generate_signals()
            if optimized_signals:
                optimized_bt = generator.backtest_signals(optimized_signals)
                print(f"  最適化後 シャープレシオ: {optimized_bt.sharpe_ratio:.3f}")
                improvement = optimized_bt.sharpe_ratio - baseline_score
                print(f"  改善: {improvement:+.3f}")
        
        # 元のルールに戻す
        generator.rules = original_rules
        
    except Exception as e:
        logger.error(f"最適化デモエラー: {e}")


def comprehensive_analysis_demo():
    """総合分析デモ"""
    print("\n" + "=" * 70)
    print("総合シグナル分析デモ")
    print("=" * 70)
    
    collector = StockDataCollector()
    
    try:
        symbol = "GOOGL"
        data = collector.get_stock_data(symbol, interval="1h", period="1mo")
        
        if data is None or len(data) < 100:
            print("データが不足しています")
            return
        
        print(f"銘柄: {symbol}")
        print(f"総合分析データ: {len(data)}件")
        
        generator = SignalGenerator(data)
        
        # シグナル生成
        signals = generator.generate_signals()
        
        if not signals:
            print("分析用シグナルがありません")
            return
        
        # パフォーマンス分析
        analysis = generator.analyze_signal_performance(signals)
        
        print(f"\n📊 総合シグナル分析:")
        print(f"  総シグナル数: {analysis['total_signals']}")
        print(f"  買いシグナル: {analysis['signal_types']['buy']}件")
        print(f"  売りシグナル: {analysis['signal_types']['sell']}件")
        print(f"  平均強度: {analysis['avg_strength']:.1f}")
        print(f"  平均信頼度: {analysis['avg_confidence']:.3f}")
        
        # 強度分布詳細
        strength_dist = analysis['strength_distribution']
        total = sum(strength_dist.values())
        print(f"\n💪 強度分布:")
        print(f"  弱 (0-40):  {strength_dist['weak']:3d}件 ({strength_dist['weak']/total*100:.1f}%)")
        print(f"  中 (41-70): {strength_dist['moderate']:3d}件 ({strength_dist['moderate']/total*100:.1f}%)")
        print(f"  強 (71-100):{strength_dist['strong']:3d}件 ({strength_dist['strong']/total*100:.1f}%)")
        
        # 時間帯分布
        hourly_dist = analysis['hourly_distribution']
        print(f"\n⏰ 時間帯分布 (上位5時間):")
        sorted_hours = sorted(hourly_dist.items(), key=lambda x: x[1], reverse=True)
        for hour, count in sorted_hours[:5]:
            print(f"  {hour:2d}時台: {count:2d}件")
        
        # バックテスト
        backtest = generator.backtest_signals(signals, holding_period=8)
        
        print(f"\n📈 バックテスト結果 (8時間保有):")
        print(f"  勝率: {backtest.win_rate*100:.1f}%")
        print(f"  平均リターン: {backtest.avg_return_per_signal*100:+.2f}%")
        print(f"  最大ドローダウン: {backtest.max_drawdown*100:.1f}%")
        print(f"  シャープレシオ: {backtest.sharpe_ratio:.2f}")
        print(f"  プロフィットファクター: {backtest.profit_factor:.2f}")
        
        # シグナル品質評価
        print(f"\n🎯 シグナル品質評価:")
        
        # 強度とパフォーマンスの相関
        strong_signals = [s for s in signals if s.strength >= 70]
        if strong_signals:
            strong_bt = generator.backtest_signals(strong_signals, holding_period=8)
            print(f"  強いシグナルのみ:")
            print(f"    件数: {len(strong_signals)}件")
            print(f"    勝率: {strong_bt.win_rate*100:.1f}%")
            print(f"    平均リターン: {strong_bt.avg_return_per_signal*100:+.2f}%")
        
        # リスクレベル別分析
        risk_levels = {}
        for signal in signals:
            if signal.risk_level not in risk_levels:
                risk_levels[signal.risk_level] = []
            risk_levels[signal.risk_level].append(signal)
        
        print(f"\n⚠️  リスクレベル別:")
        for level in ['low', 'medium', 'high']:
            if level in risk_levels:
                count = len(risk_levels[level])
                avg_strength = np.mean([s.strength for s in risk_levels[level]])
                print(f"  {level:6}: {count:2d}件 (平均強度: {avg_strength:.1f})")
        
        # 要約
        summary = generator.get_signal_summary()
        print(f"\n📋 サマリー:")
        print(summary)
        
    except Exception as e:
        logger.error(f"総合分析エラー: {e}")


def main():
    """メイン実行関数"""
    print("🎯 エントリーシグナル生成システム デモンストレーション")
    print("デイトレード用複合指標売買判定ライブラリ")
    
    try:
        # 各デモを実行
        basic_signal_generation_demo()
        filtered_signal_demo()
        backtest_demo()
        custom_rules_demo()
        rule_optimization_demo()
        comprehensive_analysis_demo()
        
        print("\n" + "=" * 70)
        print("🎉 エントリーシグナル生成デモ完了")
        print("=" * 70)
        
        print("\n💡 利用可能な主要機能:")
        print("🎯 複合シグナル: 複数指標組み合わせ高精度判定")
        print("📊 強度スコア: 0-100スケールでの信頼度評価")
        print("🔍 フィルタリング: 出来高・時間帯・ボラティリティ")
        print("🛠️  カスタムルール: 柔軟な条件設定・保存読込")
        print("📈 バックテスト: 過去実績検証・最適化")
        print("⚖️  戦略比較: 複数戦略のパフォーマンス比較")
        print("🔧 ルール最適化: 重要度分析・自動調整")
        print("💪 リスク管理: ストップロス・利確自動計算")
        
    except KeyboardInterrupt:
        print("\n\nデモが中断されました")
    except Exception as e:
        logger.error(f"デモ実行エラー: {e}")


if __name__ == "__main__":
    main()