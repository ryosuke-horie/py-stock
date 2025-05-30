"""
手数料計算機能のテストケース
"""

import pytest
from decimal import Decimal

from src.tax_calculation.fee_calculator import FeeCalculator, MarketType, FeeStructure


@pytest.fixture
def fee_calculator():
    """FeeCalculatorインスタンスを提供"""
    return FeeCalculator()


class TestFeeCalculator:
    """FeeCalculatorクラスのテスト"""
    
    def test_init(self, fee_calculator):
        """初期化のテスト"""
        assert fee_calculator.config is not None
        assert fee_calculator.fee_structures is not None
        assert "sbi" in fee_calculator.fee_structures
        assert "rakuten" in fee_calculator.fee_structures
    
    def test_calculate_fee_sbi_small_amount(self, fee_calculator):
        """SBI証券小額取引の手数料計算テスト"""
        amount = Decimal('30000')  # 3万円
        fee = fee_calculator.calculate_fee(amount, "sbi", MarketType.TOKYO_STOCK)
        
        # 5万円以下なので55円
        assert fee == Decimal('55')
    
    def test_calculate_fee_sbi_medium_amount(self, fee_calculator):
        """SBI証券中額取引の手数料計算テスト"""
        amount = Decimal('150000')  # 15万円
        fee = fee_calculator.calculate_fee(amount, "sbi", MarketType.TOKYO_STOCK)
        
        # 20万円以下なので115円
        assert fee == Decimal('115')
    
    def test_calculate_fee_sbi_large_amount(self, fee_calculator):
        """SBI証券高額取引の手数料計算テスト"""
        amount = Decimal('5000000')  # 500万円
        fee = fee_calculator.calculate_fee(amount, "sbi", MarketType.TOKYO_STOCK)
        
        # 300万円超なので1013円
        assert fee == Decimal('1013')
    
    def test_calculate_fee_sbi_us_stock(self, fee_calculator):
        """SBI証券米国株の手数料計算テスト"""
        amount = Decimal('100000')  # 10万円相当
        fee = fee_calculator.calculate_fee(amount, "sbi", MarketType.US_STOCK)
        
        # 0.495%だが最大22ドル
        expected_fee = amount * Decimal('0.00495')
        assert fee == expected_fee
    
    def test_calculate_fee_matsui_free_range(self, fee_calculator):
        """松井証券無料範囲の手数料計算テスト"""
        amount = Decimal('300000')  # 30万円
        fee = fee_calculator.calculate_fee(amount, "matsui", MarketType.TOKYO_STOCK)
        
        # 50万円以下なので0円
        assert fee == Decimal('0')
    
    def test_calculate_fee_matsui_paid_range(self, fee_calculator):
        """松井証券有料範囲の手数料計算テスト"""
        amount = Decimal('800000')  # 80万円
        fee = fee_calculator.calculate_fee(amount, "matsui", MarketType.TOKYO_STOCK)
        
        # 100万円以下なので1100円
        assert fee == Decimal('1100')
    
    def test_calculate_fee_unknown_broker(self, fee_calculator):
        """未対応証券会社の手数料計算テスト"""
        amount = Decimal('100000')
        fee = fee_calculator.calculate_fee(amount, "unknown", MarketType.TOKYO_STOCK)
        
        # 未対応なので0円
        assert fee == Decimal('0')
    
    def test_calculate_round_trip_fee(self, fee_calculator):
        """往復手数料計算のテスト"""
        amount = Decimal('100000')
        round_trip_fee = fee_calculator.calculate_round_trip_fee(amount, "sbi", MarketType.TOKYO_STOCK)
        
        single_fee = fee_calculator.calculate_fee(amount, "sbi", MarketType.TOKYO_STOCK)
        expected_round_trip = single_fee * 2
        
        assert round_trip_fee == expected_round_trip
    
    def test_compare_brokers(self, fee_calculator):
        """証券会社比較のテスト"""
        amount = Decimal('100000')
        comparison = fee_calculator.compare_brokers(amount, MarketType.TOKYO_STOCK)
        
        assert "sbi" in comparison
        assert "rakuten" in comparison
        assert "matsui" in comparison
        
        # SBIとRakutenは同じ手数料体系
        assert comparison["sbi"] == comparison["rakuten"]
        
        # Matsuiは50万円以下無料
        assert comparison["matsui"] == Decimal('0')
    
    def test_get_cheapest_broker(self, fee_calculator):
        """最安証券会社取得のテスト"""
        amount = Decimal('100000')
        cheapest_broker, cheapest_fee = fee_calculator.get_cheapest_broker(amount, MarketType.TOKYO_STOCK)
        
        # 松井証券が最安（0円）
        assert cheapest_broker == "matsui"
        assert cheapest_fee == Decimal('0')
    
    def test_calculate_fee_impact(self, fee_calculator):
        """手数料影響分析のテスト"""
        amount = Decimal('100000')
        impact = fee_calculator.calculate_fee_impact(amount, "sbi", MarketType.TOKYO_STOCK)
        
        assert "single_fee" in impact
        assert "round_trip_fee" in impact
        assert "fee_rate" in impact
        assert "round_trip_rate" in impact
        assert "breakeven_rate" in impact
        
        # SBI証券の10万円取引は99円
        assert impact["single_fee"] == Decimal('99')
        assert impact["round_trip_fee"] == Decimal('198')
        
        # 手数料率の計算
        expected_fee_rate = Decimal('99') / Decimal('100000') * 100
        assert abs(impact["fee_rate"] - expected_fee_rate) < Decimal('0.01')
    
    def test_suggest_optimal_amount(self, fee_calculator):
        """最適投資金額提案のテスト"""
        suggestions = fee_calculator.suggest_optimal_amount("sbi", MarketType.TOKYO_STOCK)
        
        assert len(suggestions) > 0
        
        # 各提案に必要な項目が含まれているか確認
        for suggestion in suggestions:
            assert "amount" in suggestion
            assert "fee" in suggestion
            assert "fee_rate" in suggestion
            assert "description" in suggestion
    
    def test_get_fee_structure_info(self, fee_calculator):
        """手数料体系情報取得のテスト"""
        info = fee_calculator.get_fee_structure_info("sbi")
        
        assert "tokyo" in info  # MarketType.TOKYO_STOCK
        assert "us" in info     # MarketType.US_STOCK
        
        tokyo_info = info["tokyo"]
        assert tokyo_info["broker_name"] == "SBI証券"
        assert tokyo_info["fee_type"] == "tiered"
        assert tokyo_info["tiers"] is not None
    
    def test_get_fee_structure_info_unknown_broker(self, fee_calculator):
        """未対応証券会社の手数料体系情報取得のテスト"""
        info = fee_calculator.get_fee_structure_info("unknown")
        assert info == {}


class TestFeeStructure:
    """FeeStructureクラスのテスト"""
    
    def test_fee_structure_creation(self):
        """手数料体系作成のテスト"""
        structure = FeeStructure(
            broker_name="テスト証券",
            market_type=MarketType.TOKYO_STOCK,
            fee_type="fixed",
            fixed_fee=Decimal('100')
        )
        
        assert structure.broker_name == "テスト証券"
        assert structure.market_type == MarketType.TOKYO_STOCK
        assert structure.fee_type == "fixed"
        assert structure.fixed_fee == Decimal('100')


class TestMarketType:
    """MarketTypeクラスのテスト"""
    
    def test_market_type_values(self):
        """市場区分の値テスト"""
        assert MarketType.TOKYO_STOCK.value == "tokyo"
        assert MarketType.US_STOCK.value == "us"
        assert MarketType.FOREIGN_STOCK.value == "foreign"