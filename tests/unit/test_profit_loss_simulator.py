"""
損益通算シミュレーション機能のテストケース
"""

import pytest
from decimal import Decimal
from datetime import date, datetime

from src.tax_calculation.profit_loss_simulator import (
    ProfitLossSimulator, TradePosition, LossCarryforward, TaxOptimizationResult
)


@pytest.fixture
def profit_loss_simulator():
    """ProfitLossSimulatorインスタンスを提供"""
    return ProfitLossSimulator()


@pytest.fixture
def sample_positions():
    """サンプルポジションデータを提供"""
    return [
        TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100,
            current_price=Decimal('2700')
        ),
        TradePosition(
            symbol="9984.T",
            entry_date=date(2024, 2, 10),
            entry_price=Decimal('8000'),
            quantity=10,
            current_price=Decimal('7500')
        ),
        TradePosition(
            symbol="6758.T",
            entry_date=date(2024, 1, 20),
            entry_price=Decimal('15000'),
            quantity=20,
            exit_date=date(2024, 3, 15),
            exit_price=Decimal('16000')
        )
    ]


class TestProfitLossSimulator:
    """ProfitLossSimulatorクラスのテスト"""
    
    def test_init(self, profit_loss_simulator):
        """初期化のテスト"""
        assert profit_loss_simulator.config is not None
        assert profit_loss_simulator.positions == []
        assert profit_loss_simulator.loss_carryforwards == []
    
    def test_add_position(self, profit_loss_simulator):
        """ポジション追加のテスト"""
        position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100
        )
        
        profit_loss_simulator.add_position(position)
        
        assert len(profit_loss_simulator.positions) == 1
        assert profit_loss_simulator.positions[0] == position
    
    def test_close_position_full(self, profit_loss_simulator):
        """ポジション全決済のテスト"""
        position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100
        )
        
        profit_loss_simulator.add_position(position)
        
        result = profit_loss_simulator.close_position(
            symbol="7203.T",
            exit_date=date(2024, 3, 15),
            exit_price=Decimal('2700')
        )
        
        assert result is True
        assert position.is_closed is True
        assert position.exit_date == date(2024, 3, 15)
        assert position.exit_price == Decimal('2700')
    
    def test_close_position_partial(self, profit_loss_simulator):
        """ポジション部分決済のテスト"""
        position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100
        )
        
        profit_loss_simulator.add_position(position)
        
        result = profit_loss_simulator.close_position(
            symbol="7203.T",
            exit_date=date(2024, 3, 15),
            exit_price=Decimal('2700'),
            quantity=50
        )
        
        assert result is True
        assert position.quantity == 50  # 残り50株
        
        # 部分決済分の新しいポジションが追加される
        assert len(profit_loss_simulator.positions) == 2
        
        # 決済済みポジションを確認
        closed_positions = [p for p in profit_loss_simulator.positions if p.is_closed]
        assert len(closed_positions) == 1
        assert closed_positions[0].quantity == 50
    
    def test_close_position_not_found(self, profit_loss_simulator):
        """存在しないポジション決済のテスト"""
        result = profit_loss_simulator.close_position(
            symbol="NONEXISTENT",
            exit_date=date(2024, 3, 15),
            exit_price=Decimal('1000')
        )
        
        assert result is False
    
    def test_calculate_realized_pnl(self, profit_loss_simulator, sample_positions):
        """実現損益計算のテスト"""
        for position in sample_positions:
            profit_loss_simulator.add_position(position)
        
        realized_profit, realized_loss = profit_loss_simulator.calculate_realized_pnl(2024)
        
        # 6758.T: (16000-15000) * 20 = 20000円の利益
        assert realized_profit == Decimal('20000')
        assert realized_loss == Decimal('0')
    
    def test_calculate_unrealized_pnl(self, profit_loss_simulator, sample_positions):
        """含み損益計算のテスト"""
        for position in sample_positions:
            profit_loss_simulator.add_position(position)
        
        unrealized_profit, unrealized_loss = profit_loss_simulator.calculate_unrealized_pnl()
        
        # 7203.T: (2700-2500) * 100 = 20000円の含み益
        # 9984.T: (7500-8000) * 10 = -5000円の含み損
        assert unrealized_profit == Decimal('20000')
        assert unrealized_loss == Decimal('5000')
    
    def test_add_loss_carryforward(self, profit_loss_simulator):
        """損失繰越追加のテスト"""
        profit_loss_simulator.add_loss_carryforward(2023, Decimal('100000'))
        
        assert len(profit_loss_simulator.loss_carryforwards) == 1
        carryforward = profit_loss_simulator.loss_carryforwards[0]
        assert carryforward.year == 2023
        assert carryforward.loss_amount == Decimal('100000')
        assert carryforward.used_amount == Decimal('0')
    
    def test_apply_loss_carryforward(self, profit_loss_simulator):
        """損失繰越適用のテスト"""
        # 2023年の損失を追加
        profit_loss_simulator.add_loss_carryforward(2023, Decimal('50000'))
        
        # 2024年に利益80000円が発生
        remaining_profit, used_amount = profit_loss_simulator.apply_loss_carryforward(2024, Decimal('80000'))
        
        # 50000円の損失繰越が適用されて、残り利益は30000円
        assert remaining_profit == Decimal('30000')
        assert used_amount == Decimal('50000')
        
        # 損失繰越の使用額が更新される
        carryforward = profit_loss_simulator.loss_carryforwards[0]
        assert carryforward.used_amount == Decimal('50000')
        assert carryforward.is_fully_used is True
    
    def test_simulate_tax_optimization(self, profit_loss_simulator, sample_positions):
        """税務最適化シミュレーションのテスト"""
        for position in sample_positions:
            profit_loss_simulator.add_position(position)
        
        result = profit_loss_simulator.simulate_tax_optimization(2024)
        
        assert isinstance(result, TaxOptimizationResult)
        assert result.current_realized_profit == Decimal('20000')  # 6758.Tの利益
        assert result.current_realized_loss == Decimal('0')
        assert result.net_realized_pnl == Decimal('20000')
        assert result.applicable_tax > Decimal('0')  # 税金が発生
        assert len(result.optimization_suggestions) >= 0
    
    def test_generate_year_end_report(self, profit_loss_simulator, sample_positions):
        """年末税務レポート生成のテスト"""
        for position in sample_positions:
            profit_loss_simulator.add_position(position)
        
        report = profit_loss_simulator.generate_year_end_report(2024)
        
        assert "year" in report
        assert "profit_loss_summary" in report
        assert "loss_carryforward" in report
        assert "positions_analysis" in report
        assert "optimization_suggestions" in report
        
        assert report["year"] == 2024
        
        profit_loss_summary = report["profit_loss_summary"]
        assert profit_loss_summary["realized_profit"] == 20000.0
        assert profit_loss_summary["realized_loss"] == 0.0
        
        positions_analysis = report["positions_analysis"]
        assert "7203.T" in positions_analysis
        assert "9984.T" in positions_analysis
        assert "6758.T" in positions_analysis
    
    def test_simulate_what_if_scenarios(self, profit_loss_simulator, sample_positions):
        """What-ifシナリオシミュレーションのテスト"""
        for position in sample_positions:
            profit_loss_simulator.add_position(position)
        
        scenarios = [
            {
                "name": "利益確定シナリオ",
                "close_positions": [
                    {
                        "symbol": "7203.T",
                        "exit_date": date(2024, 12, 15),
                        "exit_price": "2700",
                        "quantity": 100
                    }
                ],
                "year": 2024
            }
        ]
        
        results = profit_loss_simulator.simulate_what_if_scenarios(scenarios)
        
        assert "利益確定シナリオ" in results
        scenario_result = results["利益確定シナリオ"]
        
        assert "net_pnl" in scenario_result
        assert "tax" in scenario_result
        assert "net_after_tax" in scenario_result
        assert "suggestions" in scenario_result
        
        # 7203.Tの利益: (2700-2500) * 100 = 20000円
        # 6758.Tの利益: (16000-15000) * 20 = 20000円
        # 合計: 40000円
        assert scenario_result["net_pnl"] == 40000.0


class TestTradePosition:
    """TradePositionクラスのテスト"""
    
    def test_trade_position_creation(self):
        """取引ポジション作成のテスト"""
        position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100,
            current_price=Decimal('2700')
        )
        
        assert position.symbol == "7203.T"
        assert position.entry_date == date(2024, 1, 15)
        assert position.entry_price == Decimal('2500')
        assert position.quantity == 100
        assert position.current_price == Decimal('2700')
        assert position.account_type == "taxable"
    
    def test_is_closed_property(self):
        """決済済み判定のテスト"""
        # 未決済ポジション
        open_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100
        )
        assert open_position.is_closed is False
        
        # 決済済みポジション
        closed_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100,
            exit_date=date(2024, 3, 15),
            exit_price=Decimal('2700')
        )
        assert closed_position.is_closed is True
    
    def test_realized_pnl_property(self):
        """実現損益プロパティのテスト"""
        # 未決済ポジション
        open_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100
        )
        assert open_position.realized_pnl is None
        
        # 決済済みポジション
        closed_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100,
            exit_date=date(2024, 3, 15),
            exit_price=Decimal('2700')
        )
        # (2700 - 2500) * 100 = 20000
        assert closed_position.realized_pnl == Decimal('20000')
    
    def test_unrealized_pnl_property(self):
        """含み損益プロパティのテスト"""
        # 決済済みポジション
        closed_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100,
            exit_date=date(2024, 3, 15),
            exit_price=Decimal('2700')
        )
        assert closed_position.unrealized_pnl is None
        
        # 未決済ポジション（現在価格あり）
        open_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100,
            current_price=Decimal('2700')
        )
        # (2700 - 2500) * 100 = 20000
        assert open_position.unrealized_pnl == Decimal('20000')
        
        # 未決済ポジション（現在価格なし）
        no_price_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100
        )
        assert no_price_position.unrealized_pnl is None


class TestLossCarryforward:
    """LossCarryforwardクラスのテスト"""
    
    def test_loss_carryforward_creation(self):
        """損失繰越作成のテスト"""
        carryforward = LossCarryforward(
            year=2023,
            loss_amount=Decimal('100000')
        )
        
        assert carryforward.year == 2023
        assert carryforward.loss_amount == Decimal('100000')
        assert carryforward.used_amount == Decimal('0')
    
    def test_remaining_amount_property(self):
        """残存繰越損失額プロパティのテスト"""
        carryforward = LossCarryforward(
            year=2023,
            loss_amount=Decimal('100000'),
            used_amount=Decimal('30000')
        )
        
        assert carryforward.remaining_amount == Decimal('70000')
    
    def test_is_fully_used_property(self):
        """完全使用済み判定プロパティのテスト"""
        # 部分使用
        partial_used = LossCarryforward(
            year=2023,
            loss_amount=Decimal('100000'),
            used_amount=Decimal('50000')
        )
        assert partial_used.is_fully_used is False
        
        # 完全使用
        fully_used = LossCarryforward(
            year=2023,
            loss_amount=Decimal('100000'),
            used_amount=Decimal('100000')
        )
        assert fully_used.is_fully_used is True
        
        # 使用額超過（エラーケース）
        over_used = LossCarryforward(
            year=2023,
            loss_amount=Decimal('100000'),
            used_amount=Decimal('120000')
        )
        assert over_used.is_fully_used is True


class TestTaxOptimizationResult:
    """TaxOptimizationResultクラスのテスト"""
    
    def test_tax_optimization_result_creation(self):
        """税務最適化結果作成のテスト"""
        result = TaxOptimizationResult(
            current_realized_profit=Decimal('100000'),
            current_realized_loss=Decimal('20000'),
            net_realized_pnl=Decimal('80000'),
            applicable_tax=Decimal('16252'),
            loss_carryforward_used=Decimal('0'),
            remaining_loss_carryforward=Decimal('50000'),
            optimization_suggestions=["含み損の実現を検討してください"]
        )
        
        assert result.current_realized_profit == Decimal('100000')
        assert result.current_realized_loss == Decimal('20000')
        assert result.net_realized_pnl == Decimal('80000')
        assert result.applicable_tax == Decimal('16252')
        assert result.loss_carryforward_used == Decimal('0')
        assert result.remaining_loss_carryforward == Decimal('50000')
        assert len(result.optimization_suggestions) == 1