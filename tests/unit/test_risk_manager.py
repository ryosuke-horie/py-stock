"""
RiskManager のテスト
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, time
from unittest.mock import Mock, patch

from src.risk_management.risk_manager import (
    RiskManager, RiskParameters, Position, StopLossType, PositionSide
)


class TestRiskManager(unittest.TestCase):
    
    def setUp(self):
        """テストの初期設定"""
        self.risk_params = RiskParameters(
            max_position_size_pct=2.0,
            max_daily_loss_pct=5.0,
            stop_loss_pct=2.0,
            atr_multiplier=2.0,
            trailing_stop_pct=1.5,
            risk_reward_ratios=[1.0, 1.5, 2.0, 3.0],
            max_positions=5,
            force_close_time=time(15, 0)
        )
        self.risk_manager = RiskManager(self.risk_params, initial_capital=1000000)
        
        # テスト用データ作成
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        prices = 1000 + np.cumsum(np.random.randn(100) * 10)
        
        self.test_data = pd.DataFrame({
            'Open': prices + np.random.randn(100) * 5,
            'High': prices + abs(np.random.randn(100) * 10),
            'Low': prices - abs(np.random.randn(100) * 10),
            'Close': prices,
            'Volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
    
    def test_risk_manager_initialization(self):
        """RiskManager の初期化テスト"""
        self.assertEqual(self.risk_manager.initial_capital, 1000000)
        self.assertEqual(self.risk_manager.current_capital, 1000000)
        self.assertEqual(len(self.risk_manager.positions), 0)
        self.assertEqual(self.risk_manager.daily_pnl, 0.0)
    
    def test_calculate_position_size(self):
        """ポジションサイズ計算テスト"""
        entry_price = 1000
        stop_loss = 980  # 2%下
        
        # ロングポジション
        size = self.risk_manager.calculate_position_size(
            "7203.T", entry_price, stop_loss, PositionSide.LONG
        )
        
        expected_risk = 1000000 * 0.02  # 20,000円
        expected_size = int(expected_risk / 20)  # 1000株
        expected_size = (expected_size // 100) * 100  # 100株単位
        
        self.assertEqual(size, expected_size)
    
    def test_calculate_stop_loss_fixed_percentage(self):
        """固定パーセンテージストップロス計算テスト"""
        entry_price = 1000
        
        # ロングポジション
        stop_loss = self.risk_manager.calculate_stop_loss(
            self.test_data, entry_price, PositionSide.LONG, StopLossType.FIXED_PERCENTAGE
        )
        expected = entry_price * (1 - 0.02)  # 2%下
        self.assertAlmostEqual(stop_loss, expected, places=2)
        
        # ショートポジション
        stop_loss = self.risk_manager.calculate_stop_loss(
            self.test_data, entry_price, PositionSide.SHORT, StopLossType.FIXED_PERCENTAGE
        )
        expected = entry_price * (1 + 0.02)  # 2%上
        self.assertAlmostEqual(stop_loss, expected, places=2)
    
    def test_calculate_stop_loss_atr_based(self):
        """ATRベースストップロス計算テスト"""
        entry_price = 1000
        
        with patch.object(self.risk_manager.technical_indicators, 'calculate_atr') as mock_atr:
            mock_atr.return_value = pd.Series([20.0])  # ATR = 20
            
            stop_loss = self.risk_manager.calculate_stop_loss(
                self.test_data, entry_price, PositionSide.LONG, StopLossType.ATR_BASED
            )
            
            expected = entry_price - (20.0 * 2.0)  # ATR * multiplier
            self.assertAlmostEqual(stop_loss, expected, places=2)
    
    def test_calculate_take_profit_levels(self):
        """テイクプロフィットレベル計算テスト"""
        entry_price = 1000
        stop_loss = 980
        
        tp_levels = self.risk_manager.calculate_take_profit_levels(
            entry_price, stop_loss, PositionSide.LONG
        )
        
        risk = entry_price - stop_loss  # 20
        expected_levels = [
            entry_price + (risk * 1.0),  # 1020
            entry_price + (risk * 1.5),  # 1030
            entry_price + (risk * 2.0),  # 1040
            entry_price + (risk * 3.0)   # 1060
        ]
        
        self.assertEqual(len(tp_levels), 4)
        for i, level in enumerate(tp_levels):
            self.assertAlmostEqual(level, expected_levels[i], places=2)
    
    def test_open_position(self):
        """ポジション開設テスト"""
        symbol = "7203.T"
        entry_price = 1000
        
        success = self.risk_manager.open_position(
            symbol, PositionSide.LONG, entry_price, self.test_data, quantity=1000
        )
        
        self.assertTrue(success)
        self.assertIn(symbol, self.risk_manager.positions)
        
        position = self.risk_manager.positions[symbol]
        self.assertEqual(position.symbol, symbol)
        self.assertEqual(position.side, PositionSide.LONG)
        self.assertEqual(position.entry_price, entry_price)
        self.assertEqual(position.quantity, 1000)
        self.assertIsNotNone(position.stop_loss)
        self.assertTrue(len(position.take_profit) > 0)
    
    def test_close_position(self):
        """ポジション決済テスト"""
        symbol = "7203.T"
        entry_price = 1000
        exit_price = 1020
        
        # ポジション開設
        self.risk_manager.open_position(
            symbol, PositionSide.LONG, entry_price, self.test_data, quantity=1000
        )
        
        initial_capital = self.risk_manager.current_capital
        
        # ポジション決済
        success = self.risk_manager.close_position(symbol, exit_price, "Test close")
        
        self.assertTrue(success)
        self.assertNotIn(symbol, self.risk_manager.positions)
        
        # PnL計算確認
        expected_pnl = (exit_price - entry_price) * 1000  # 20,000円
        commission = (entry_price + exit_price) * 1000 * 0.001  # 手数料
        expected_net_pnl = expected_pnl - commission
        
        self.assertAlmostEqual(
            self.risk_manager.current_capital - initial_capital,
            expected_net_pnl,
            places=0
        )
    
    def test_trailing_stop_update(self):
        """トレイリングストップ更新テスト"""
        symbol = "7203.T"
        entry_price = 1000
        
        # ポジション開設
        self.risk_manager.open_position(
            symbol, PositionSide.LONG, entry_price, self.test_data, quantity=1000
        )
        
        # 価格上昇時のトレイリングストップ更新
        self.risk_manager.update_trailing_stop(symbol, 1050)
        position = self.risk_manager.positions[symbol]
        
        expected_trailing = 1050 * (1 - 0.015)  # 1.5%下
        self.assertAlmostEqual(position.trailing_stop, expected_trailing, places=2)
        
        # さらに価格が上昇
        self.risk_manager.update_trailing_stop(symbol, 1100)
        position = self.risk_manager.positions[symbol]
        
        new_expected_trailing = 1100 * (1 - 0.015)
        self.assertAlmostEqual(position.trailing_stop, new_expected_trailing, places=2)
        
        # 価格下落時（トレイリングストップは更新されない）
        old_trailing = position.trailing_stop
        self.risk_manager.update_trailing_stop(symbol, 1080)
        self.assertEqual(position.trailing_stop, old_trailing)
    
    def test_check_exit_conditions_stop_loss(self):
        """ストップロス条件チェックテスト"""
        symbol = "7203.T"
        entry_price = 1000
        
        self.risk_manager.open_position(
            symbol, PositionSide.LONG, entry_price, self.test_data, quantity=1000
        )
        
        position = self.risk_manager.positions[symbol]
        stop_loss_price = position.stop_loss - 1  # ストップロスを下回る価格
        
        exit_condition = self.risk_manager.check_exit_conditions(symbol, stop_loss_price)
        
        self.assertTrue(exit_condition["should_exit"])
        self.assertIn("Stop loss", exit_condition["reason"])
    
    def test_check_exit_conditions_take_profit(self):
        """テイクプロフィット条件チェックテスト"""
        symbol = "7203.T"
        entry_price = 1000
        
        self.risk_manager.open_position(
            symbol, PositionSide.LONG, entry_price, self.test_data, quantity=1000
        )
        
        position = self.risk_manager.positions[symbol]
        tp_price = position.take_profit[0] + 1  # 最初のTPを上回る価格
        
        exit_condition = self.risk_manager.check_exit_conditions(symbol, tp_price)
        
        self.assertTrue(exit_condition["should_exit"])
        self.assertIn("Take profit", exit_condition["reason"])
    
    def test_check_exit_conditions_force_close_time(self):
        """強制決済時刻チェックテスト"""
        symbol = "7203.T"
        entry_price = 1000
        
        self.risk_manager.open_position(
            symbol, PositionSide.LONG, entry_price, self.test_data, quantity=1000
        )
        
        # 強制決済時刻後の時刻でテスト
        force_close_time = datetime.now().replace(hour=15, minute=30)
        
        exit_condition = self.risk_manager.check_exit_conditions(
            symbol, entry_price, force_close_time
        )
        
        self.assertTrue(exit_condition["should_exit"])
        self.assertIn("Force close", exit_condition["reason"])
    
    def test_update_positions(self):
        """ポジション更新テスト"""
        symbol = "7203.T"
        entry_price = 1000
        
        self.risk_manager.open_position(
            symbol, PositionSide.LONG, entry_price, self.test_data, quantity=1000
        )
        
        # 価格データで更新
        price_data = {symbol: 1050}
        self.risk_manager.update_positions(price_data)
        
        position = self.risk_manager.positions[symbol]
        self.assertEqual(position.current_price, 1050)
        self.assertEqual(position.unrealized_pnl, 50000)  # (1050-1000)*1000
    
    def test_get_portfolio_summary(self):
        """ポートフォリオサマリー取得テスト"""
        symbol = "7203.T"
        entry_price = 1000
        
        self.risk_manager.open_position(
            symbol, PositionSide.LONG, entry_price, self.test_data, quantity=1000
        )
        
        # 価格更新
        self.risk_manager.positions[symbol].update_price(1050)
        
        summary = self.risk_manager.get_portfolio_summary()
        
        self.assertEqual(summary["current_capital"], 1000000)
        self.assertEqual(summary["initial_capital"], 1000000)
        self.assertEqual(summary["open_positions"], 1)
        self.assertEqual(summary["unrealized_pnl"], 50000)
        self.assertIn(symbol, summary["position_details"])
    
    def test_max_positions_limit(self):
        """最大ポジション数制限テスト"""
        # 最大ポジション数を2に設定
        self.risk_manager.risk_params.max_positions = 2
        
        # 2つのポジションを開設
        self.risk_manager.open_position(
            "7203.T", PositionSide.LONG, 1000, self.test_data, quantity=1000
        )
        self.risk_manager.open_position(
            "6758.T", PositionSide.LONG, 2000, self.test_data, quantity=500
        )
        
        # 3つ目のポジション開設は失敗するはず
        size = self.risk_manager.calculate_position_size(
            "9984.T", 3000, 2940, PositionSide.LONG
        )
        self.assertEqual(size, 0)  # 最大ポジション数に達しているため0
    
    def test_risk_parameters_default(self):
        """デフォルトリスクパラメータテスト"""
        default_params = RiskParameters()
        
        self.assertEqual(default_params.max_position_size_pct, 2.0)
        self.assertEqual(default_params.max_daily_loss_pct, 5.0)
        self.assertEqual(default_params.stop_loss_pct, 2.0)
        self.assertEqual(default_params.atr_multiplier, 2.0)
        self.assertEqual(default_params.trailing_stop_pct, 1.5)
        self.assertEqual(default_params.risk_reward_ratios, [1.0, 1.5, 2.0, 3.0])
        self.assertEqual(default_params.max_positions, 5)
        self.assertEqual(default_params.force_close_time, time(15, 0))


if __name__ == '__main__':
    unittest.main()