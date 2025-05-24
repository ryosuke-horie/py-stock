"""
リスク管理システムのデモンストレーション
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import logging

from ..data_collector.stock_data_collector import StockDataCollector
from ..technical_analysis.signal_generator import SignalGenerator
from ..risk_management.risk_manager import (
    RiskManager, RiskParameters, PositionSide, StopLossType
)

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RiskManagementDemo:
    """リスク管理システムのデモクラス"""
    
    def __init__(self):
        """初期化"""
        self.data_collector = StockDataCollector()
        self.signal_generator = SignalGenerator()
        
        # リスクパラメータ設定
        self.risk_params = RiskParameters(
            max_position_size_pct=1.5,      # 最大ポジションサイズ1.5%
            max_daily_loss_pct=3.0,         # 日次最大損失3%
            stop_loss_pct=2.0,              # 固定ストップロス2%
            atr_multiplier=2.5,             # ATR倍率2.5倍
            trailing_stop_pct=1.2,          # トレイリングストップ1.2%
            risk_reward_ratios=[1.0, 1.5, 2.0, 2.5, 3.0],  # RR比率
            max_positions=3,                # 最大3ポジション
            force_close_time=time(14, 50)   # 14:50強制決済
        )
        
        self.risk_manager = RiskManager(self.risk_params, initial_capital=1000000)
        
        logger.info("リスク管理デモシステム初期化完了")
    
    def demo_position_sizing(self, symbol: str, period: str = "1mo"):
        """ポジションサイジングのデモ"""
        print(f"\n{'='*60}")
        print(f"ポジションサイジングデモ: {symbol}")
        print(f"{'='*60}")
        
        try:
            # データ取得
            data = self.data_collector.get_stock_data(symbol, period=period)
            if data.empty:
                print(f"データ取得失敗: {symbol}")
                return
            
            current_price = data['Close'].iloc[-1]
            print(f"現在価格: ¥{current_price:.2f}")
            
            # 各ストップロスタイプでのポジションサイズ計算
            stop_types = [
                (StopLossType.FIXED_PERCENTAGE, "固定%"),
                (StopLossType.ATR_BASED, "ATRベース"),
                (StopLossType.SUPPORT_RESISTANCE, "サポレジベース")
            ]
            
            print(f"\n総資本: ¥{self.risk_manager.current_capital:,}")
            print(f"最大ポジションリスク: {self.risk_params.max_position_size_pct}%")
            print("-" * 60)
            
            for stop_type, type_name in stop_types:
                stop_loss = self.risk_manager.calculate_stop_loss(
                    data, current_price, PositionSide.LONG, stop_type
                )
                
                position_size = self.risk_manager.calculate_position_size(
                    symbol, current_price, stop_loss, PositionSide.LONG
                )
                
                risk_per_share = current_price - stop_loss
                total_investment = current_price * position_size
                total_risk = risk_per_share * position_size
                
                print(f"{type_name}:")
                print(f"  ストップロス: ¥{stop_loss:.2f} ({((current_price - stop_loss) / current_price * 100):.1f}%下)")
                print(f"  ポジションサイズ: {position_size:,}株")
                print(f"  投資金額: ¥{total_investment:,}")
                print(f"  最大リスク: ¥{total_risk:,}")
                print()
                
        except Exception as e:
            logger.error(f"ポジションサイジングデモエラー: {e}")
    
    def demo_risk_reward_calculation(self, symbol: str, period: str = "1mo"):
        """リスクリワード計算のデモ"""
        print(f"\n{'='*60}")
        print(f"リスクリワード計算デモ: {symbol}")
        print(f"{'='*60}")
        
        try:
            # データ取得
            data = self.data_collector.get_stock_data(symbol, period=period)
            if data.empty:
                print(f"データ取得失敗: {symbol}")
                return
            
            current_price = data['Close'].iloc[-1]
            
            # ATRベースのストップロス計算
            stop_loss = self.risk_manager.calculate_stop_loss(
                data, current_price, PositionSide.LONG, StopLossType.ATR_BASED
            )
            
            # テイクプロフィットレベル計算
            tp_levels = self.risk_manager.calculate_take_profit_levels(
                current_price, stop_loss, PositionSide.LONG
            )
            
            risk_amount = current_price - stop_loss
            
            print(f"エントリー価格: ¥{current_price:.2f}")
            print(f"ストップロス: ¥{stop_loss:.2f}")
            print(f"リスク: ¥{risk_amount:.2f} ({(risk_amount / current_price * 100):.1f}%)")
            print("\nテイクプロフィットレベル:")
            print("-" * 40)
            
            for i, (tp_price, rr_ratio) in enumerate(zip(tp_levels, self.risk_params.risk_reward_ratios)):
                reward_amount = tp_price - current_price
                print(f"TP{i+1}: ¥{tp_price:.2f} (RR比 1:{rr_ratio:.1f})")
                print(f"      利益: ¥{reward_amount:.2f} ({(reward_amount / current_price * 100):.1f}%)")
                
        except Exception as e:
            logger.error(f"リスクリワード計算デモエラー: {e}")
    
    def demo_trailing_stop(self, symbol: str, period: str = "3mo"):
        """トレイリングストップのデモ"""
        print(f"\n{'='*60}")
        print(f"トレイリングストップデモ: {symbol}")
        print(f"{'='*60}")
        
        try:
            # データ取得
            data = self.data_collector.get_stock_data(symbol, period=period)
            if data.empty:
                print(f"データ取得失敗: {symbol}")
                return
            
            # 仮想的なポジション開設（データの中間地点）
            entry_idx = len(data) // 2
            entry_price = data['Close'].iloc[entry_idx]
            
            print(f"仮想エントリー: ¥{entry_price:.2f} ({data.index[entry_idx].strftime('%Y-%m-%d')})")
            
            # ポジション開設
            success = self.risk_manager.open_position(
                symbol, PositionSide.LONG, entry_price, data[:entry_idx+1], quantity=1000
            )
            
            if not success:
                print("ポジション開設失敗")
                return
            
            position = self.risk_manager.positions[symbol]
            print(f"初期ストップロス: ¥{position.stop_loss:.2f}")
            
            print("\nトレイリングストップ履歴:")
            print("-" * 50)
            
            # エントリー後の価格変動でトレイリングストップ更新
            trailing_history = []
            
            for i in range(entry_idx + 1, len(data)):
                current_price = data['Close'].iloc[i]
                date = data.index[i].strftime('%Y-%m-%d')
                
                old_trailing = position.trailing_stop
                self.risk_manager.update_trailing_stop(symbol, current_price)
                new_trailing = position.trailing_stop
                
                # トレイリングストップが更新された場合
                if old_trailing != new_trailing:
                    trailing_history.append({
                        'date': date,
                        'price': current_price,
                        'trailing_stop': new_trailing,
                        'gain_protected': new_trailing - entry_price if new_trailing > entry_price else 0
                    })
                
                # 決済条件チェック
                exit_condition = self.risk_manager.check_exit_conditions(
                    symbol, current_price, datetime.strptime(date, '%Y-%m-%d')
                )
                
                if exit_condition["should_exit"]:
                    self.risk_manager.close_position(
                        symbol, current_price, exit_condition["reason"]
                    )
                    print(f"\n決済: {date} ¥{current_price:.2f} ({exit_condition['reason']})")
                    break
            
            # トレイリングストップ履歴表示
            for record in trailing_history[-10:]:  # 最新10件
                protected_gain = record['gain_protected']
                print(f"{record['date']}: 価格¥{record['price']:.2f} → "
                      f"トレイリング¥{record['trailing_stop']:.2f} "
                      f"(保護利益: ¥{protected_gain:.2f})")
                
        except Exception as e:
            logger.error(f"トレイリングストップデモエラー: {e}")
    
    def demo_portfolio_management(self, symbols: list, period: str = "2mo"):
        """ポートフォリオ管理のデモ"""
        print(f"\n{'='*60}")
        print(f"ポートフォリオ管理デモ")
        print(f"{'='*60}")
        
        try:
            # 複数銘柄でシグナル検証
            for symbol in symbols:
                print(f"\n{symbol} の分析:")
                print("-" * 30)
                
                # データ取得
                data = self.data_collector.get_stock_data(symbol, period=period)
                if data.empty:
                    print(f"  データ取得失敗")
                    continue
                
                # シグナル生成
                signals = self.signal_generator.generate_signals(data)
                latest_signal = signals.iloc[-1] if not signals.empty else None
                
                if latest_signal is not None and latest_signal['signal'] != 'HOLD':
                    current_price = data['Close'].iloc[-1]
                    side = PositionSide.LONG if latest_signal['signal'] == 'BUY' else PositionSide.SHORT
                    
                    # リスク分析
                    stop_loss = self.risk_manager.calculate_stop_loss(
                        data, current_price, side, StopLossType.ATR_BASED
                    )
                    
                    position_size = self.risk_manager.calculate_position_size(
                        symbol, current_price, stop_loss, side
                    )
                    
                    print(f"  シグナル: {latest_signal['signal']}")
                    print(f"  強度: {latest_signal['strength']:.1f}")
                    print(f"  現在価格: ¥{current_price:.2f}")
                    print(f"  推奨サイズ: {position_size:,}株")
                    print(f"  投資金額: ¥{current_price * position_size:,.0f}")
                else:
                    print(f"  シグナル: なし")
            
            # ポートフォリオサマリー
            print(f"\n{'='*40}")
            print("ポートフォリオサマリー")
            print(f"{'='*40}")
            
            summary = self.risk_manager.get_portfolio_summary()
            print(f"総資本: ¥{summary['current_capital']:,}")
            print(f"初期資本: ¥{summary['initial_capital']:,}")
            print(f"総損益: ¥{summary['total_pnl']:,}")
            print(f"開設ポジション数: {summary['open_positions']}/{summary['max_positions']}")
            print(f"未実現損益: ¥{summary['unrealized_pnl']:,}")
            
            if summary['position_details']:
                print("\n保有ポジション:")
                for symbol, pos_detail in summary['position_details'].items():
                    print(f"  {symbol}: {pos_detail['side']} {pos_detail['quantity']:,}株")
                    print(f"    エントリー: ¥{pos_detail['entry_price']:.2f}")
                    if pos_detail['current_price']:
                        print(f"    現在価格: ¥{pos_detail['current_price']:.2f}")
                        print(f"    未実現PnL: ¥{pos_detail['unrealized_pnl']:,}")
                    
        except Exception as e:
            logger.error(f"ポートフォリオ管理デモエラー: {e}")
    
    def demo_risk_scenarios(self, symbol: str, period: str = "6mo"):
        """リスクシナリオのデモ"""
        print(f"\n{'='*60}")
        print(f"リスクシナリオデモ: {symbol}")
        print(f"{'='*60}")
        
        try:
            # データ取得
            data = self.data_collector.get_stock_data(symbol, period=period)
            if data.empty:
                print(f"データ取得失敗: {symbol}")
                return
            
            current_price = data['Close'].iloc[-1]
            
            # 様々なシナリオでのリスク計算
            scenarios = [
                {"name": "保守的", "params": RiskParameters(max_position_size_pct=1.0, stop_loss_pct=1.5, atr_multiplier=1.5)},
                {"name": "標準", "params": RiskParameters(max_position_size_pct=2.0, stop_loss_pct=2.0, atr_multiplier=2.0)},
                {"name": "積極的", "params": RiskParameters(max_position_size_pct=3.0, stop_loss_pct=3.0, atr_multiplier=2.5)},
            ]
            
            print(f"現在価格: ¥{current_price:.2f}")
            print(f"総資本: ¥{self.risk_manager.current_capital:,}")
            print("\nリスクシナリオ比較:")
            print("-" * 80)
            print(f"{'シナリオ':<10} {'ポジション':<8} {'ストップロス':<12} {'投資額':<12} {'最大リスク':<12}")
            print("-" * 80)
            
            for scenario in scenarios:
                temp_manager = RiskManager(scenario["params"], self.risk_manager.current_capital)
                
                stop_loss = temp_manager.calculate_stop_loss(
                    data, current_price, PositionSide.LONG, StopLossType.ATR_BASED
                )
                
                position_size = temp_manager.calculate_position_size(
                    symbol, current_price, stop_loss, PositionSide.LONG
                )
                
                investment = current_price * position_size
                max_risk = (current_price - stop_loss) * position_size
                
                print(f"{scenario['name']:<10} "
                      f"{position_size:,}株  "
                      f"¥{stop_loss:.2f}     "
                      f"¥{investment:,.0f}    "
                      f"¥{max_risk:,.0f}")
            
            print("-" * 80)
            
        except Exception as e:
            logger.error(f"リスクシナリオデモエラー: {e}")


def main():
    """メイン実行関数"""
    demo = RiskManagementDemo()
    
    # デモ銘柄
    symbols = ["7203.T", "6758.T", "9984.T"]  # トヨタ、ソニー、ソフトバンク
    
    try:
        print("リスク管理システム デモンストレーション")
        print("=" * 60)
        
        # 1. ポジションサイジング
        demo.demo_position_sizing(symbols[0])
        
        # 2. リスクリワード計算
        demo.demo_risk_reward_calculation(symbols[0])
        
        # 3. トレイリングストップ
        demo.demo_trailing_stop(symbols[1])
        
        # 4. ポートフォリオ管理
        demo.demo_portfolio_management(symbols)
        
        # 5. リスクシナリオ
        demo.demo_risk_scenarios(symbols[0])
        
        print(f"\n{'='*60}")
        print("デモ完了")
        print(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"デモ実行エラー: {e}")


if __name__ == "__main__":
    main()