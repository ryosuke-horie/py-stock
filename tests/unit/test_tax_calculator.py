"""
税務計算機能のテストケース
"""

import pytest
from decimal import Decimal
from datetime import date, datetime
from unittest.mock import patch, MagicMock

from src.tax_calculation.tax_calculator import TaxCalculator, TradeRecord, TaxResult


@pytest.fixture
def tax_calculator():
    """TaxCalculatorインスタンスを提供"""
    return TaxCalculator()


@pytest.fixture
def sample_trades():
    """サンプル取引データを提供"""
    return [
        TradeRecord(
            symbol="7203.T",
            date=date(2024, 1, 15),
            action="buy",
            quantity=100,
            price=Decimal('2500'),
            fee=Decimal('55')
        ),
        TradeRecord(
            symbol="7203.T",
            date=date(2024, 3, 20),
            action="sell",
            quantity=50,
            price=Decimal('2800'),
            fee=Decimal('55')
        ),
        TradeRecord(
            symbol="9984.T",
            date=date(2024, 2, 10),
            action="buy",
            quantity=10,
            price=Decimal('8000'),
            fee=Decimal('99')
        )
    ]


class TestTaxCalculator:
    """TaxCalculatorクラスのテスト"""
    
    def test_init(self, tax_calculator):
        """初期化のテスト"""
        assert tax_calculator.config is not None
        assert tax_calculator.trades == []
        assert tax_calculator.holdings == {}
    
    def test_add_buy_trade(self, tax_calculator):
        """買い取引追加のテスト"""
        trade = TradeRecord(
            symbol="7203.T",
            date=date(2024, 1, 15),
            action="buy",
            quantity=100,
            price=Decimal('2500'),
            fee=Decimal('55')
        )
        
        tax_calculator.add_trade(trade)
        
        assert len(tax_calculator.trades) == 1
        assert "7203.T" in tax_calculator.holdings
        assert len(tax_calculator.holdings["7203.T"]) == 1
        assert tax_calculator.holdings["7203.T"][0].quantity == 100
    
    def test_add_sell_trade(self, tax_calculator, sample_trades):
        """売り取引追加のテスト（FIFO処理）"""
        # 買い取引を先に追加
        tax_calculator.add_trade(sample_trades[0])  # 100株買い
        
        # 売り取引を追加
        tax_calculator.add_trade(sample_trades[1])  # 50株売り
        
        # 保有数量が減っていることを確認
        assert tax_calculator.holdings["7203.T"][0].quantity == 50
    
    def test_calculate_realized_profit(self, tax_calculator, sample_trades):
        """実現利益計算のテスト"""
        for trade in sample_trades:
            tax_calculator.add_trade(trade)
        
        realized_profit = tax_calculator.calculate_realized_profit(2024)
        
        # 7203.T: (2800-2500) * 50 = 15000円の利益
        assert realized_profit == Decimal('15000')
    
    def test_calculate_unrealized_profit(self, tax_calculator, sample_trades):
        """含み益計算のテスト"""
        # 買い取引のみ追加
        tax_calculator.add_trade(sample_trades[0])  # 7203.T 100株 @2500
        tax_calculator.add_trade(sample_trades[2])  # 9984.T 10株 @8000
        
        current_prices = {
            "7203.T": Decimal('2700'),  # 200円上昇
            "9984.T": Decimal('7500')   # 500円下落
        }
        
        unrealized_profit = tax_calculator.calculate_unrealized_profit(current_prices)
        
        # 7203.T: (2700-2500) * 100 = 20000円
        # 9984.T: (7500-8000) * 10 = -5000円
        # 合計: 15000円
        assert unrealized_profit == Decimal('15000')
    
    def test_calculate_capital_gains_tax(self, tax_calculator):
        """譲渡益税計算のテスト"""
        profit = Decimal('100000')
        tax = tax_calculator.calculate_capital_gains_tax(profit)
        
        # 100000 * 0.20315 = 20315円
        expected_tax = Decimal('20315.00')
        assert tax == expected_tax
    
    def test_calculate_capital_gains_tax_loss(self, tax_calculator):
        """損失時の譲渡益税計算のテスト"""
        loss = Decimal('-50000')
        tax = tax_calculator.calculate_capital_gains_tax(loss)
        
        # 損失の場合は税金0円
        assert tax == Decimal('0')
    
    def test_calculate_total_fees(self, tax_calculator, sample_trades):
        """総手数料計算のテスト"""
        for trade in sample_trades:
            tax_calculator.add_trade(trade)
        
        total_fees = tax_calculator.calculate_total_fees(2024)
        
        # 55 + 55 + 99 = 209円
        assert total_fees == Decimal('209')
    
    def test_calculate_nisa_usage(self, tax_calculator):
        """NISA利用状況計算のテスト"""
        # NISA口座での取引
        nisa_trade = TradeRecord(
            symbol="1570.T",
            date=date(2024, 1, 15),
            action="buy",
            quantity=100,
            price=Decimal('3000'),
            fee=Decimal('0'),
            account_type="nisa"
        )
        
        tax_calculator.add_trade(nisa_trade)
        
        nisa_used, nisa_remaining = tax_calculator.calculate_nisa_usage(2024)
        
        assert nisa_used == Decimal('300000')  # 3000 * 100
        assert nisa_remaining == Decimal('900000')  # 1200000 - 300000
    
    def test_get_tax_summary(self, tax_calculator, sample_trades):
        """税務サマリー取得のテスト"""
        for trade in sample_trades:
            tax_calculator.add_trade(trade)
        
        current_prices = {
            "7203.T": Decimal('2700'),
            "9984.T": Decimal('8200')
        }
        
        summary = tax_calculator.get_tax_summary(current_prices, 2024)
        
        assert isinstance(summary, TaxResult)
        assert summary.realized_profit == Decimal('15000')
        assert summary.capital_gains_tax == Decimal('3047.25')  # 15000 * 0.20315
        assert summary.total_fees == Decimal('209')
        assert summary.net_profit == Decimal('11743.75')  # 15000 - 3047.25 - 209
    
    def test_simulate_tax_optimization(self, tax_calculator):
        """税務最適化シミュレーションのテスト"""
        current_prices = {
            "7203.T": Decimal('2700'),
            "9984.T": Decimal('8200')
        }
        
        potential_sales = [
            ("7203.T", 50, Decimal('2700')),
            ("9984.T", 10, Decimal('8200'))
        ]
        
        # 保有ポジションを先に追加
        buy_trade1 = TradeRecord(
            symbol="7203.T",
            date=date(2024, 1, 15),
            action="buy",
            quantity=100,
            price=Decimal('2500'),
            fee=Decimal('55')
        )
        buy_trade2 = TradeRecord(
            symbol="9984.T",
            date=date(2024, 2, 10),
            action="buy",
            quantity=10,
            price=Decimal('8000'),
            fee=Decimal('99')
        )
        
        tax_calculator.add_trade(buy_trade1)
        tax_calculator.add_trade(buy_trade2)
        
        results = tax_calculator.simulate_tax_optimization(potential_sales, current_prices)
        
        assert "7203.T_profit" in results
        assert "9984.T_profit" in results
        assert results["7203.T_profit"] == Decimal('10000')  # (2700-2500) * 50
        assert results["9984.T_profit"] == Decimal('2000')   # (8200-8000) * 10
    
    def test_export_tax_report(self, tax_calculator, sample_trades):
        """税務レポート出力のテスト"""
        for trade in sample_trades:
            tax_calculator.add_trade(trade)
        
        report = tax_calculator.export_tax_report(2024)
        
        assert "year" in report
        assert "summary" in report
        assert "trade_count" in report
        assert "symbols_traded" in report
        
        assert report["year"] == 2024
        assert report["trade_count"] == 3
        assert "7203.T" in report["symbols_traded"]
        assert "9984.T" in report["symbols_traded"]
    
    def test_round_decimal(self, tax_calculator):
        """小数点丸め処理のテスト"""
        value = Decimal('123.456789')
        rounded = tax_calculator._round_decimal(value)
        
        # デフォルト設定（小数点以下2桁）で丸める
        assert rounded == Decimal('123.46')
    
    def test_process_sell_trade_exact_quantity(self, tax_calculator):
        """FIFO売却処理での完全消化テスト"""
        # 買い取引を先に追加
        buy_trade = TradeRecord(
            symbol="7203.T",
            date=date(2024, 1, 15),
            action="buy",
            quantity=100,
            price=Decimal('2500'),
            fee=Decimal('55')
        )
        tax_calculator.add_trade(buy_trade)
        
        # 完全に同じ数量を売却
        sell_trade = TradeRecord(
            symbol="7203.T",
            date=date(2024, 3, 20),
            action="sell",
            quantity=100,  # 完全消化
            price=Decimal('2800'),
            fee=Decimal('55')
        )
        tax_calculator.add_trade(sell_trade)
        
        # 保有がゼロになっていることを確認
        assert len(tax_calculator.holdings["7203.T"]) == 0


class TestTradeRecord:
    """TradeRecordクラスのテスト"""
    
    def test_trade_record_creation(self):
        """取引記録作成のテスト"""
        trade = TradeRecord(
            symbol="7203.T",
            date=date(2024, 1, 15),
            action="buy",
            quantity=100,
            price=Decimal('2500'),
            fee=Decimal('55'),
            account_type="taxable"
        )
        
        assert trade.symbol == "7203.T"
        assert trade.date == date(2024, 1, 15)
        assert trade.action == "buy"
        assert trade.quantity == 100
        assert trade.price == Decimal('2500')
        assert trade.fee == Decimal('55')
        assert trade.account_type == "taxable"


class TestTaxResult:
    """TaxResultクラスのテスト"""
    
    def test_tax_result_creation(self):
        """税務計算結果作成のテスト"""
        result = TaxResult(
            realized_profit=Decimal('100000'),
            unrealized_profit=Decimal('50000'),
            capital_gains_tax=Decimal('20315'),
            total_fees=Decimal('500'),
            net_profit=Decimal('79185'),
            nisa_used_amount=Decimal('300000'),
            nisa_remaining=Decimal('900000')
        )
        
        assert result.realized_profit == Decimal('100000')
        assert result.unrealized_profit == Decimal('50000')
        assert result.capital_gains_tax == Decimal('20315')
        assert result.total_fees == Decimal('500')
        assert result.net_profit == Decimal('79185')
        assert result.nisa_used_amount == Decimal('300000')
        assert result.nisa_remaining == Decimal('900000')