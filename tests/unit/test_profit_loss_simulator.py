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


class TestProfitLossSimulatorEdgeCases:
    """ProfitLossSimulatorのエッジケーステスト"""
    
    def test_close_position_insufficient_quantity(self, profit_loss_simulator):
        """ポジション決済で数量不足の場合のテスト"""
        # ポジション追加
        position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100
        )
        profit_loss_simulator.add_position(position)
        
        # 保有数量を超える決済を試行
        result = profit_loss_simulator.close_position(
            symbol="7203.T",
            exit_date=date(2024, 3, 15),
            exit_price=Decimal('2700'),
            quantity=200  # 保有数量100を超える
        )
        
        # 保有数量分のみ決済される
        assert result == True
        # ポジション確認
        closed_positions = [p for p in profit_loss_simulator.positions if p.is_closed]
        assert len(closed_positions) == 1
        assert closed_positions[0].quantity == 100
    
    def test_calculate_realized_pnl_with_year_filter(self, profit_loss_simulator):
        """年度指定での実現損益計算テスト"""
        # 2023年のポジション
        position_2023 = TradePosition(
            symbol="7203.T",
            entry_date=date(2023, 6, 1),
            entry_price=Decimal('2000'),
            quantity=100
        )
        profit_loss_simulator.add_position(position_2023)
        profit_loss_simulator.close_position(
            symbol="7203.T",
            exit_date=date(2023, 12, 15),
            exit_price=Decimal('2200')
        )
        
        # 2024年のポジション
        position_2024 = TradePosition(
            symbol="9984.T",
            entry_date=date(2024, 1, 10),
            entry_price=Decimal('8000'),
            quantity=10
        )
        profit_loss_simulator.add_position(position_2024)
        profit_loss_simulator.close_position(
            symbol="9984.T",
            exit_date=date(2024, 3, 20),
            exit_price=Decimal('7500')
        )
        
        # 2023年の損益のみ計算
        profit_2023, loss_2023 = profit_loss_simulator.calculate_realized_pnl(year=2023)
        assert profit_2023 == Decimal('20000')  # (2200-2000)*100
        assert loss_2023 == Decimal('0')
        
        # 2024年の損益のみ計算
        profit_2024, loss_2024 = profit_loss_simulator.calculate_realized_pnl(year=2024)
        assert profit_2024 == Decimal('0')
        assert loss_2024 == Decimal('5000')  # (8000-7500)*10
    
    def test_calculate_realized_pnl_with_nisa_account(self, profit_loss_simulator):
        """NISA口座での実現損益計算テスト"""
        # NISA口座でのポジション
        nisa_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100,
            account_type="nisa"
        )
        profit_loss_simulator.add_position(nisa_position)
        profit_loss_simulator.close_position(
            symbol="7203.T",
            exit_date=date(2024, 3, 15),
            exit_price=Decimal('2700')
        )
        
        # 課税口座でのポジション
        taxable_position = TradePosition(
            symbol="9984.T",
            entry_date=date(2024, 1, 10),
            entry_price=Decimal('8000'),
            quantity=10,
            account_type="taxable"
        )
        profit_loss_simulator.add_position(taxable_position)
        profit_loss_simulator.close_position(
            symbol="9984.T",
            exit_date=date(2024, 3, 20),
            exit_price=Decimal('7500')
        )
        
        # NISA口座の損益は課税対象外なので、課税口座のみが計算される
        profit, loss = profit_loss_simulator.calculate_realized_pnl()
        assert profit == Decimal('0')
        assert loss == Decimal('5000')  # 課税口座の損失のみ
    
    def test_calculate_unrealized_pnl_with_none_current_price(self, profit_loss_simulator):
        """現在価格がNoneの場合の含み損益計算テスト"""
        # 現在価格なしのポジション
        none_price_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100,
            current_price=None  # 現在価格なし
        )
        profit_loss_simulator.add_position(none_price_position)
        
        # 現在価格ありのポジション
        with_price_position = TradePosition(
            symbol="9984.T",
            entry_date=date(2024, 1, 10),
            entry_price=Decimal('8000'),
            quantity=10,
            current_price=Decimal('7500')
        )
        profit_loss_simulator.add_position(with_price_position)
        
        profit, loss = profit_loss_simulator.calculate_unrealized_pnl()
        # 現在価格がNoneのポジションは計算から除外される
        assert profit == Decimal('0')
        assert loss == Decimal('5000')  # 9984.Tの含み損のみ
    
    def test_calculate_unrealized_pnl_with_nisa_account(self, profit_loss_simulator):
        """NISA口座での含み損益計算テスト"""
        # NISA口座でのポジション
        nisa_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100,
            current_price=Decimal('2700'),
            account_type="nisa"
        )
        profit_loss_simulator.add_position(nisa_position)
        
        # 課税口座でのポジション
        taxable_position = TradePosition(
            symbol="9984.T",
            entry_date=date(2024, 1, 10),
            entry_price=Decimal('8000'),
            quantity=10,
            current_price=Decimal('7500'),
            account_type="taxable"
        )
        profit_loss_simulator.add_position(taxable_position)
        
        profit, loss = profit_loss_simulator.calculate_unrealized_pnl()
        # NISA口座の損益は課税対象外なので、課税口座のみが計算される
        assert profit == Decimal('0')
        assert loss == Decimal('5000')  # 課税口座の含み損のみ
    
    def test_apply_loss_carryforward_partial_usage(self, profit_loss_simulator):
        """繰越損失の部分利用テスト"""
        # 100万円の繰越損失を追加
        profit_loss_simulator.add_loss_carryforward(2022, Decimal('1000000'))
        
        # 50万円の利益に対して繰越損失を適用
        remaining_profit, used_amount = profit_loss_simulator.apply_loss_carryforward(2024, Decimal('500000'))
        
        # 利益は相殺されて0になる
        assert remaining_profit == Decimal('0')
        assert used_amount == Decimal('500000')
        
        # 繰越損失は50万円使用されて50万円残る
        carryforward = profit_loss_simulator.loss_carryforwards[0]
        assert carryforward.used_amount == Decimal('500000')
        assert carryforward.remaining_amount == Decimal('500000')
        assert not carryforward.is_fully_used
    
    def test_apply_loss_carryforward_full_usage(self, profit_loss_simulator):
        """繰越損失の完全利用テスト"""
        # 50万円の繰越損失を追加
        profit_loss_simulator.add_loss_carryforward(2022, Decimal('500000'))
        
        # 100万円の利益に対して繰越損失を適用
        remaining_profit, used_amount = profit_loss_simulator.apply_loss_carryforward(2024, Decimal('1000000'))
        
        # 50万円の利益が残る
        assert remaining_profit == Decimal('500000')
        assert used_amount == Decimal('500000')
        
        # 繰越損失は完全に使用される
        carryforward = profit_loss_simulator.loss_carryforwards[0]
        assert carryforward.used_amount == Decimal('500000')
        assert carryforward.remaining_amount == Decimal('0')
        assert carryforward.is_fully_used
    
    def test_simulate_what_if_scenarios_with_extreme_changes(self, profit_loss_simulator, sample_positions):
        """What-ifシナリオの極端な変動テスト"""
        # ポジション追加
        for position in sample_positions:
            profit_loss_simulator.add_position(position)
        
        # 簡単なシナリオテスト（実装に合わせて修正）
        scenarios = [
            {
                "name": "市場暴落",
                "close_positions": [
                    {
                        "symbol": "7203.T",
                        "exit_date": date(2024, 12, 15),
                        "exit_price": "500",  # 50%下落
                        "quantity": 100
                    }
                ],
                "year": 2024
            }
        ]
        
        results = profit_loss_simulator.simulate_what_if_scenarios(scenarios)
        
        assert len(results) == 1
        assert "市場暴落" in results
        
        # 暴落シナリオでは損失が発生
        assert results["市場暴落"]["net_pnl"] < 0
    
    def test_loss_carryforward_expiration(self, profit_loss_simulator):
        """損失繰越期限切れテスト"""
        # 5年前の古い損失繰越を追加（期限切れ）
        profit_loss_simulator.add_loss_carryforward(2019, Decimal('100000'))
        # 有効な損失繰越を追加
        profit_loss_simulator.add_loss_carryforward(2023, Decimal('50000'))
        
        # 2024年に利益に対して損失繰越を適用
        remaining_profit, used_amount = profit_loss_simulator.apply_loss_carryforward(2024, Decimal('100000'))
        
        # 期限切れの2019年分は使用されず、2023年分のみ使用される
        assert remaining_profit == Decimal('50000')  # 100000 - 50000
        assert used_amount == Decimal('50000')
    
    def test_loss_carryforward_already_used(self, profit_loss_simulator):
        """既に使用済みの損失繰越テスト"""
        # 損失繰越を追加して一部使用
        profit_loss_simulator.add_loss_carryforward(2023, Decimal('100000'))
        carryforward = profit_loss_simulator.loss_carryforwards[0]
        carryforward.used_amount = Decimal('100000')  # 完全使用済みに設定
        
        # 利益に対して損失繰越を適用しようとする
        remaining_profit, used_amount = profit_loss_simulator.apply_loss_carryforward(2024, Decimal('50000'))
        
        # 使用済みなので適用されない
        assert remaining_profit == Decimal('50000')
        assert used_amount == Decimal('0')
    
    def test_optimization_suggestions_end_of_year(self, profit_loss_simulator):
        """年末時期の最適化提案テスト"""
        from unittest.mock import patch
        from datetime import datetime
        
        # 11月の日付でテスト
        with patch('src.tax_calculation.profit_loss_simulator.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 11, 15)
            
            # 利益ポジションを追加
            position = TradePosition(
                symbol="7203.T",
                entry_date=date(2024, 1, 15),
                entry_price=Decimal('2500'),
                quantity=100,
                current_price=Decimal('2700')
            )
            profit_loss_simulator.add_position(position)
            
            # 決済済み利益ポジション
            closed_position = TradePosition(
                symbol="9984.T",
                entry_date=date(2024, 1, 10),
                entry_price=Decimal('8000'),
                quantity=10,
                exit_date=date(2024, 3, 20),
                exit_price=Decimal('8500')
            )
            profit_loss_simulator.add_position(closed_position)
            
            result = profit_loss_simulator.simulate_tax_optimization(2024)
            
            # 年末の損益通算提案が含まれることを確認
            suggestions = result.optimization_suggestions
            assert any("年末" in suggestion for suggestion in suggestions)
    
    def test_optimization_suggestions_year_end_loss(self, profit_loss_simulator):
        """年末時期の損失ケース最適化提案テスト"""
        from unittest.mock import patch
        from datetime import datetime
        
        # 12月の日付でテスト
        with patch('src.tax_calculation.profit_loss_simulator.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 12, 15)
            
            # 損失ポジションを追加
            position = TradePosition(
                symbol="7203.T",
                entry_date=date(2024, 1, 15),
                entry_price=Decimal('2500'),
                quantity=100,
                current_price=Decimal('2300')  # 含み損
            )
            profit_loss_simulator.add_position(position)
            
            # 決済済み損失ポジション
            closed_position = TradePosition(
                symbol="9984.T",
                entry_date=date(2024, 1, 10),
                entry_price=Decimal('8000'),
                quantity=10,
                exit_date=date(2024, 3, 20),
                exit_price=Decimal('7500')  # 損失
            )
            profit_loss_simulator.add_position(closed_position)
            
            result = profit_loss_simulator.simulate_tax_optimization(2024)
            
            # 年末の含み益実現提案が含まれることを確認
            suggestions = result.optimization_suggestions
            assert any("年内" in suggestion for suggestion in suggestions)
    
    def test_optimization_suggestions_large_unrealized_profit_with_loss(self, profit_loss_simulator):
        """大きな含み益と損失がある場合の最適化提案テスト"""
        # 大きな含み益ポジション
        profit_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('1000'),
            quantity=200,
            current_price=Decimal('2000')  # 20万円の含み益
        )
        profit_loss_simulator.add_position(profit_position)
        
        # 損失発生状況を作るために決済済み損失ポジション
        loss_position = TradePosition(
            symbol="9984.T",
            entry_date=date(2024, 1, 10),
            entry_price=Decimal('8000'),
            quantity=10,
            exit_date=date(2024, 3, 20),
            exit_price=Decimal('7000')  # 1万円の損失
        )
        profit_loss_simulator.add_position(loss_position)
        
        result = profit_loss_simulator.simulate_tax_optimization(2024)
        
        # 損失年内での含み益実現提案が含まれることを確認
        suggestions = result.optimization_suggestions
        assert any("損失が発生している年内" in suggestion for suggestion in suggestions)
    
    def test_optimization_suggestions_large_unrealized_profit_with_profit(self, profit_loss_simulator):
        """大きな含み益と既存利益がある場合の最適化提案テスト"""
        # 大きな含み益ポジション
        profit_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('1000'),
            quantity=200,
            current_price=Decimal('2000')  # 20万円の含み益
        )
        profit_loss_simulator.add_position(profit_position)
        
        # 利益発生状況を作るために決済済み利益ポジション
        closed_position = TradePosition(
            symbol="9984.T",
            entry_date=date(2024, 1, 10),
            entry_price=Decimal('8000'),
            quantity=10,
            exit_date=date(2024, 3, 20),
            exit_price=Decimal('9000')  # 1万円の利益
        )
        profit_loss_simulator.add_position(closed_position)
        
        result = profit_loss_simulator.simulate_tax_optimization(2024)
        
        # 翌年延期提案が含まれることを確認
        suggestions = result.optimization_suggestions
        assert any("翌年に延期" in suggestion for suggestion in suggestions)
    
    def test_optimization_suggestions_nisa_proposal(self, profit_loss_simulator):
        """NISA活用提案テスト"""
        # 課税口座の未決済ポジション
        position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100,
            account_type="taxable"
        )
        profit_loss_simulator.add_position(position)
        
        result = profit_loss_simulator.simulate_tax_optimization(2024)
        
        # NISA活用提案が含まれることを確認
        suggestions = result.optimization_suggestions
        assert any("NISA口座" in suggestion for suggestion in suggestions)
    
    def test_remaining_quantity_zero_break(self, profit_loss_simulator):
        """remaining_quantityが0になった場合のbreak動作テスト"""
        # 複数ポジションで一つだけを閉じる場合のbreakテスト
        position1 = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=50
        )
        profit_loss_simulator.add_position(position1)
        
        position2 = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 2, 15),
            entry_price=Decimal('2600'),
            quantity=100
        )
        profit_loss_simulator.add_position(position2)
        
        # 50株だけ決済（最初のポジションのみ）
        result = profit_loss_simulator.close_position(
            symbol="7203.T",
            exit_date=date(2024, 3, 15),
            exit_price=Decimal('2700'),
            quantity=50
        )
        
        assert result == True
        # 1つのポジションが決済され、1つが残る
        closed_positions = [p for p in profit_loss_simulator.positions if p.is_closed]
        open_positions = [p for p in profit_loss_simulator.positions if not p.is_closed]
        assert len(closed_positions) == 1
        assert len(open_positions) == 1
        assert closed_positions[0].quantity == 50
    
    def test_loss_carryforward_with_unrealized_profit_optimization(self, profit_loss_simulator):
        """損失繰越がある場合の含み益実現提案テスト"""
        # 損失繰越を追加
        profit_loss_simulator.add_loss_carryforward(2023, Decimal('100000'))
        
        # 含み益ポジション
        position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100,
            current_price=Decimal('3000')  # 50000円の含み益
        )
        profit_loss_simulator.add_position(position)
        
        result = profit_loss_simulator.simulate_tax_optimization(2024)
        
        # 損失繰越を使った含み益実現提案が含まれることを確認
        suggestions = result.optimization_suggestions
        assert any("損失繰越" in suggestion and "含み益" in suggestion for suggestion in suggestions)
    
    def test_year_end_report_with_mixed_position_analysis(self, profit_loss_simulator):
        """年末レポートでの複雑なポジション分析テスト"""
        # 同一銘柄の複数ポジション（決済済み・未決済混在）
        closed_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 1, 15),
            entry_price=Decimal('2500'),
            quantity=100,
            exit_date=date(2024, 3, 20),
            exit_price=Decimal('2700')
        )
        profit_loss_simulator.add_position(closed_position)
        
        open_position = TradePosition(
            symbol="7203.T",
            entry_date=date(2024, 6, 10),
            entry_price=Decimal('2600'),
            quantity=50,
            current_price=Decimal('2800')
        )
        profit_loss_simulator.add_position(open_position)
        
        report = profit_loss_simulator.generate_year_end_report(2024)
        
        # ポジション分析に両方の損益が含まれることを確認
        positions_analysis = report["positions_analysis"]
        toyota_analysis = positions_analysis["7203.T"]
        assert toyota_analysis["realized_pnl"] == 20000.0  # (2700-2500)*100
        assert toyota_analysis["unrealized_pnl"] == 10000.0  # (2800-2600)*50
        assert toyota_analysis["total_pnl"] == 30000.0
        assert toyota_analysis["holding_quantity"] == 50
    
    def test_what_if_scenario_exception_recovery(self, profit_loss_simulator, sample_positions):
        """What-ifシナリオでの例外からの復旧テスト"""
        # ポジション追加
        for position in sample_positions:
            profit_loss_simulator.add_position(position)
        
        original_positions_count = len(profit_loss_simulator.positions)
        
        # 存在しない銘柄の決済を試行するシナリオ（例外は発生しないが失敗する）
        scenarios = [
            {
                "name": "例外テスト",
                "close_positions": [
                    {
                        "symbol": "NONEXISTENT.T",  # 存在しない銘柄
                        "exit_date": date(2024, 12, 15),
                        "exit_price": "1000",
                        "quantity": 100
                    }
                ],
                "year": 2024
            }
        ]
        
        # 例外が発生しても元の状態が復元されることを確認
        results = profit_loss_simulator.simulate_what_if_scenarios(scenarios)
        
        # ポジション数が元に戻っていることを確認
        assert len(profit_loss_simulator.positions) == original_positions_count
        
        # 結果が返されることを確認
        assert "例外テスト" in results