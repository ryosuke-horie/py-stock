"""
NISA枠管理機能のテストケース
"""

import pytest
from decimal import Decimal
from datetime import date

from src.tax_calculation.nisa_manager import NisaManager, NisaInvestment, NisaType, NisaStatus, NisaLimits


@pytest.fixture
def nisa_manager():
    """NisaManagerインスタンスを提供"""
    return NisaManager()


@pytest.fixture
def sample_investments():
    """サンプルNISA投資データを提供"""
    return [
        NisaInvestment(
            symbol="1570.T",
            date=date(2024, 1, 15),
            amount=Decimal('300000'),
            nisa_type=NisaType.GROWTH
        ),
        NisaInvestment(
            symbol="VTI",
            date=date(2024, 2, 10),
            amount=Decimal('100000'),
            nisa_type=NisaType.TSUMITATE
        ),
        NisaInvestment(
            symbol="1475.T",
            date=date(2024, 3, 5),
            amount=Decimal('200000'),
            nisa_type=NisaType.GROWTH
        )
    ]


class TestNisaManager:
    """NisaManagerクラスのテスト"""
    
    def test_init(self, nisa_manager):
        """初期化のテスト"""
        assert nisa_manager.config is not None
        assert nisa_manager.investments == []
        assert nisa_manager.nisa_limits is not None
        assert 2024 in nisa_manager.nisa_limits
    
    def test_get_nisa_limits(self, nisa_manager):
        """NISA限度額設定のテスト"""
        limits_2024 = nisa_manager.nisa_limits[2024]
        
        assert limits_2024.year == 2024
        assert limits_2024.growth_annual == 2400000    # 240万円
        assert limits_2024.tsumitate_annual == 1200000 # 120万円
        assert limits_2024.total_lifetime == 18000000  # 1800万円
        assert limits_2024.growth_lifetime == 12000000 # 1200万円
    
    def test_add_investment_success(self, nisa_manager):
        """NISA投資追加成功のテスト"""
        investment = NisaInvestment(
            symbol="1570.T",
            date=date(2024, 1, 15),
            amount=Decimal('300000'),
            nisa_type=NisaType.GROWTH
        )
        
        result = nisa_manager.add_investment(investment)
        
        assert result is True
        assert len(nisa_manager.investments) == 1
        assert nisa_manager.investments[0] == investment
    
    def test_add_investment_limit_exceeded(self, nisa_manager):
        """NISA投資限度額超過のテスト"""
        # 成長投資枠の限度額を超える投資
        investment = NisaInvestment(
            symbol="1570.T",
            date=date(2024, 1, 15),
            amount=Decimal('3000000'),  # 300万円（限度額240万円を超過）
            nisa_type=NisaType.GROWTH
        )
        
        result = nisa_manager.add_investment(investment)
        
        assert result is False
        assert len(nisa_manager.investments) == 0
    
    def test_get_nisa_status_empty(self, nisa_manager):
        """NISA利用状況取得（投資なし）のテスト"""
        status = nisa_manager.get_nisa_status(2024)
        
        assert status.year == 2024
        assert status.growth_used == Decimal('0')
        assert status.tsumitate_used == Decimal('0')
        assert status.growth_remaining == Decimal('2400000')
        assert status.tsumitate_remaining == Decimal('1200000')
        assert status.total_used == Decimal('0')
    
    def test_get_nisa_status_with_investments(self, nisa_manager, sample_investments):
        """NISA利用状況取得（投資あり）のテスト"""
        for investment in sample_investments:
            nisa_manager.add_investment(investment)
        
        status = nisa_manager.get_nisa_status(2024)
        
        # 成長投資枠: 300000 + 200000 = 500000
        # つみたて投資枠: 100000
        assert status.growth_used == Decimal('500000')
        assert status.tsumitate_used == Decimal('100000')
        assert status.growth_remaining == Decimal('1900000')  # 2400000 - 500000
        assert status.tsumitate_remaining == Decimal('1100000')  # 1200000 - 100000
        assert status.total_used == Decimal('600000')
    
    def test_calculate_tax_savings(self, nisa_manager, sample_investments):
        """NISA税務メリット計算のテスト"""
        for investment in sample_investments:
            nisa_manager.add_investment(investment)
        
        tax_savings = nisa_manager.calculate_tax_savings(2024)
        
        assert "nisa_investment" in tax_savings
        assert "assumed_profit" in tax_savings
        assert "tax_savings" in tax_savings
        assert "effective_return_rate" in tax_savings
        
        # 投資総額: 600000円
        assert tax_savings["nisa_investment"] == Decimal('600000')
        
        # 想定利益: 600000 * 0.05 = 30000円
        assert tax_savings["assumed_profit"] == Decimal('30000')
    
    def test_calculate_tax_savings_no_investment(self, nisa_manager):
        """投資なしでの税務メリット計算"""
        tax_savings = nisa_manager.calculate_tax_savings(2024)
        
        assert tax_savings["nisa_investment"] == Decimal('0')
        assert tax_savings["assumed_profit"] == Decimal('0')
        assert tax_savings["tax_savings"] == Decimal('0')
        assert tax_savings["effective_return_rate"] == Decimal('0')
    
    def test_suggest_optimal_allocation_long_term(self, nisa_manager):
        """最適NISA枠配分提案（長期投資）のテスト"""
        available_amount = Decimal('1000000')  # 100万円
        suggestions = nisa_manager.suggest_optimal_allocation(
            available_amount, 2024, investment_horizon=20
        )
        
        assert "total_available" in suggestions
        assert "recommendations" in suggestions
        assert "remaining_after_allocation" in suggestions
        
        assert suggestions["total_available"] == available_amount
        
        # 長期投資なのでつみたて投資枠が優先される
        recommendations = suggestions["recommendations"]
        assert len(recommendations) >= 1
        assert recommendations[0]["type"] == "つみたて投資枠"
    
    def test_suggest_optimal_allocation_short_term(self, nisa_manager):
        """最適NISA枠配分提案（短期投資）のテスト"""
        available_amount = Decimal('500000')  # 50万円
        suggestions = nisa_manager.suggest_optimal_allocation(
            available_amount, 2024, investment_horizon=5
        )
        
        # 短期投資なので成長投資枠のみ
        recommendations = suggestions["recommendations"]
        assert len(recommendations) >= 1
        assert recommendations[0]["type"] == "成長投資枠"
    
    def test_get_monthly_investment_plan(self, nisa_manager):
        """月次投資計画のテスト"""
        annual_budget = Decimal('1200000')  # 120万円
        plan = nisa_manager.get_monthly_investment_plan(annual_budget, 2024)
        
        assert "annual_budget" in plan
        assert "nisa_allocation" in plan
        assert "taxable_allocation" in plan
        assert "monthly_plan" in plan
        assert "recommendations" in plan
        
        assert plan["annual_budget"] == annual_budget
        assert plan["nisa_allocation"] <= Decimal('3600000')  # NISA年間限度額内
        
        monthly_plan = plan["monthly_plan"]
        assert monthly_plan["total"] == annual_budget / 12
    
    def test_generate_nisa_report(self, nisa_manager, sample_investments):
        """NISA年次レポート生成のテスト"""
        for investment in sample_investments:
            nisa_manager.add_investment(investment)
        
        report = nisa_manager.generate_nisa_report(2024)
        
        assert "year" in report
        assert "status" in report
        assert "tax_benefits" in report
        assert "investments" in report
        assert "recommendations" in report
        
        assert report["year"] == 2024
        
        status = report["status"]
        assert status["growth_used"] == 500000.0
        assert status["tsumitate_used"] == 100000.0
        assert status["total_used"] == 600000.0
        
        investments = report["investments"]
        assert "1570.T" in investments
        assert "VTI" in investments
        assert "1475.T" in investments


class TestNisaInvestment:
    """NisaInvestmentクラスのテスト"""
    
    def test_nisa_investment_creation(self):
        """NISA投資記録作成のテスト"""
        investment = NisaInvestment(
            symbol="1570.T",
            date=date(2024, 1, 15),
            amount=Decimal('300000'),
            nisa_type=NisaType.GROWTH
        )
        
        assert investment.symbol == "1570.T"
        assert investment.date == date(2024, 1, 15)
        assert investment.amount == Decimal('300000')
        assert investment.nisa_type == NisaType.GROWTH
        assert investment.year == 2024  # 自動設定


class TestNisaStatus:
    """NisaStatusクラスのテスト"""
    
    def test_nisa_status_creation(self):
        """NISA利用状況作成のテスト"""
        status = NisaStatus(
            year=2024,
            growth_used=Decimal('500000'),
            tsumitate_used=Decimal('100000'),
            growth_remaining=Decimal('1900000'),
            tsumitate_remaining=Decimal('1100000'),
            total_used=Decimal('600000'),
            total_remaining_lifetime=Decimal('17400000')
        )
        
        assert status.year == 2024
        assert status.growth_used == Decimal('500000')
        assert status.tsumitate_used == Decimal('100000')
        assert status.growth_remaining == Decimal('1900000')
        assert status.tsumitate_remaining == Decimal('1100000')
        assert status.total_used == Decimal('600000')
        assert status.total_remaining_lifetime == Decimal('17400000')


class TestNisaLimits:
    """NisaLimitsクラスのテスト"""
    
    def test_nisa_limits_creation(self):
        """NISA制度限度額作成のテスト"""
        limits = NisaLimits(
            year=2024,
            growth_annual=2400000,
            tsumitate_annual=1200000,
            total_lifetime=18000000,
            growth_lifetime=12000000
        )
        
        assert limits.year == 2024
        assert limits.growth_annual == 2400000
        assert limits.tsumitate_annual == 1200000
        assert limits.total_lifetime == 18000000
        assert limits.growth_lifetime == 12000000


class TestNisaType:
    """NisaTypeクラスのテスト"""
    
    def test_nisa_type_values(self):
        """NISA区分の値テスト"""
        assert NisaType.GROWTH.value == "growth"
        assert NisaType.TSUMITATE.value == "tsumitate"
        assert NisaType.OLD_NISA.value == "old_nisa"
        assert NisaType.OLD_TSUMITATE.value == "old_tsumitate"


class TestNisaManagerEdgeCases:
    """NisaManagerの異常ケース・エッジケーステスト"""
    
    def test_check_investment_limit_invalid_year(self):
        """対象外年度での投資限度額チェック"""
        nisa_manager = NisaManager()
        investment = NisaInvestment(
            symbol="TEST",
            date=date(2010, 1, 1),  # NISA制度対象外の年度
            amount=Decimal('100000'),
            nisa_type=NisaType.GROWTH
        )
        
        result = nisa_manager._check_investment_limit(investment)
        assert result is False
    
    def test_check_investment_limit_old_nisa_type(self):
        """旧NISA制度での投資限度額チェック"""
        nisa_manager = NisaManager()
        investment = NisaInvestment(
            symbol="TEST",
            date=date(2024, 1, 1),
            amount=Decimal('100000'),
            nisa_type=NisaType.OLD_NISA  # 旧NISA制度
        )
        
        result = nisa_manager._check_investment_limit(investment)
        assert result is True
    
    def test_get_nisa_status_invalid_year(self):
        """対象外年度でのNISA利用状況取得"""
        nisa_manager = NisaManager()
        status = nisa_manager.get_nisa_status(2010)  # NISA制度対象外の年度
        
        assert status.year == 2010
        assert status.growth_used == Decimal('0')
        assert status.tsumitate_used == Decimal('0')
        assert status.growth_remaining == Decimal('0')
        assert status.tsumitate_remaining == Decimal('0')
        assert status.total_used == Decimal('0')
        assert status.total_remaining_lifetime == Decimal('0')
    
    def test_suggest_optimal_allocation_no_tsumitate_for_short_term(self):
        """短期投資でつみたて投資枠が提案されないケース"""
        nisa_manager = NisaManager()
        suggestions = nisa_manager.suggest_optimal_allocation(
            Decimal('1000000'), 2024, investment_horizon=5  # 短期投資
        )
        
        # 短期投資なのでつみたて投資枠は提案されない
        recommendations = suggestions["recommendations"]
        tsumitate_recs = [r for r in recommendations if r["type"] == "つみたて投資枠"]
        assert len(tsumitate_recs) == 0
    
    def test_suggest_optimal_allocation_excess_amount(self):
        """NISA枠を超過する投資額での提案"""
        nisa_manager = NisaManager()
        suggestions = nisa_manager.suggest_optimal_allocation(
            Decimal('5000000'), 2024, investment_horizon=20  # NISA年間限度額超過
        )
        
        # 課税口座での投資が提案される
        recommendations = suggestions["recommendations"]
        taxable_recs = [r for r in recommendations if r["type"] == "課税口座"]
        assert len(taxable_recs) > 0
        assert suggestions["remaining_after_allocation"] > 0
    
    def test_get_monthly_investment_plan_with_existing_investments(self):
        """既存投資がある場合の月次投資計画"""
        nisa_manager = NisaManager()
        
        # 既存投資を追加
        existing_investment = NisaInvestment(
            symbol="EXISTING",
            date=date(2024, 1, 1),
            amount=Decimal('1000000'),
            nisa_type=NisaType.TSUMITATE
        )
        nisa_manager.add_investment(existing_investment)
        
        plan = nisa_manager.get_monthly_investment_plan(Decimal('1200000'), 2024)
        
        # つみたて投資枠に既存投資があるため残り枠が少ない
        assert plan["nisa_allocation"] <= Decimal('2600000')  # 3600000 - 1000000
    
    def test_generate_nisa_report_no_investments(self):
        """投資実績がない場合のレポート生成"""
        nisa_manager = NisaManager()
        report = nisa_manager.generate_nisa_report(2024)
        
        assert report["year"] == 2024
        assert report["status"]["total_used"] == 0.0
        assert report["investments"] == {}
        assert len(report["recommendations"]) > 0
    
    def test_generate_recommendations_low_usage(self):
        """NISA活用率が低い場合の推奨事項"""
        nisa_manager = NisaManager()
        status = NisaStatus(
            year=2024,
            growth_used=Decimal('100000'),
            tsumitate_used=Decimal('50000'),
            growth_remaining=Decimal('2300000'),
            tsumitate_remaining=Decimal('1150000'),
            total_used=Decimal('150000'),
            total_remaining_lifetime=Decimal('17850000')
        )
        
        recommendations = nisa_manager._generate_recommendations(status)
        
        # 活用率が50%未満なので追加投資の推奨が含まれる
        low_usage_recs = [r for r in recommendations if "50%未満" in r]
        assert len(low_usage_recs) > 0
    
    def test_generate_recommendations_tsumitate_surplus(self):
        """つみたて投資枠に余裕がある場合の推奨事項"""
        nisa_manager = NisaManager()
        status = NisaStatus(
            year=2024,
            growth_used=Decimal('2000000'),
            tsumitate_used=Decimal('200000'),
            growth_remaining=Decimal('400000'),
            tsumitate_remaining=Decimal('1000000'),  # つみたて枠に余裕
            total_used=Decimal('2200000'),
            total_remaining_lifetime=Decimal('15800000')
        )
        
        recommendations = nisa_manager._generate_recommendations(status)
        
        # つみたて投資枠の活用推奨が含まれる
        tsumitate_recs = [r for r in recommendations if "つみたて投資枠" in r]
        assert len(tsumitate_recs) > 0
    
    def test_generate_recommendations_growth_surplus(self):
        """成長投資枠に余裕がある場合の推奨事項"""
        nisa_manager = NisaManager()
        status = NisaStatus(
            year=2024,
            growth_used=Decimal('400000'),
            tsumitate_used=Decimal('1000000'),
            growth_remaining=Decimal('2000000'),  # 成長枠に余裕（100万円以上）
            tsumitate_remaining=Decimal('200000'),
            total_used=Decimal('1400000'),
            total_remaining_lifetime=Decimal('16600000')
        )
        
        recommendations = nisa_manager._generate_recommendations(status)
        
        # 成長投資枠の活用推奨が含まれる
        growth_recs = [r for r in recommendations if "成長投資枠" in r]
        assert len(growth_recs) > 0
    
    def test_generate_recommendations_optimal_usage(self):
        """NISA枠を効率的に活用している場合の推奨事項"""
        nisa_manager = NisaManager()
        status = NisaStatus(
            year=2024,
            growth_used=Decimal('2300000'),
            tsumitate_used=Decimal('1100000'),
            growth_remaining=Decimal('100000'),
            tsumitate_remaining=Decimal('100000'),
            total_used=Decimal('3400000'),
            total_remaining_lifetime=Decimal('14600000')
        )
        
        recommendations = nisa_manager._generate_recommendations(status)
        
        # 効率的活用の評価が含まれる
        optimal_recs = [r for r in recommendations if "効率的に活用" in r]
        assert len(optimal_recs) > 0