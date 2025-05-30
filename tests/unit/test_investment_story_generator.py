"""
投資ストーリー生成モジュールのユニットテスト
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.technical_analysis.investment_story_generator import (
    InvestmentStoryGenerator,
    FinancialGlossary,
    ScenarioType,
    RiskLevel,
    InvestmentScenario,
    RiskFactor,
    GlossaryTerm,
    InvestmentReport,
    TechnicalAnalysisData
)
from src.technical_analysis.fundamental_analysis import (
    FinancialMetrics,
    GrowthTrend,
    HealthScoreResult,
    HealthScore
)


class TestFinancialGlossary:
    """FinancialGlossaryクラスのテスト"""
    
    def test_get_term_existing(self):
        """既存用語の取得テスト"""
        term = FinancialGlossary.get_term("PER")
        
        assert isinstance(term, GlossaryTerm)
        assert term.term == "PER"
        assert "株価収益率" in term.definition
        assert term.example is not None
    
    def test_get_term_non_existing(self):
        """存在しない用語の取得テスト"""
        term = FinancialGlossary.get_term("UNKNOWN_TERM")
        assert term is None
    
    def test_get_relevant_terms(self):
        """コンテンツから関連用語抽出テスト"""
        content = "PERは15倍で、ROEは18%です。配当利回りも魅力的です。"
        terms = FinancialGlossary.get_relevant_terms(content)
        
        assert len(terms) == 3
        term_names = [t.term for t in terms]
        assert "PER" in term_names
        assert "ROE" in term_names
        assert "配当利回り" in term_names
    
    def test_get_relevant_terms_empty(self):
        """関連用語がないコンテンツのテスト"""
        content = "これは普通の文章です。"
        terms = FinancialGlossary.get_relevant_terms(content)
        
        assert len(terms) == 0


class TestInvestmentStoryGenerator:
    """InvestmentStoryGeneratorクラスのテスト"""
    
    @pytest.fixture
    def generator(self):
        """ジェネレーターのフィクスチャ"""
        return InvestmentStoryGenerator()
    
    @pytest.fixture
    def sample_financial_metrics(self):
        """サンプル財務指標"""
        return FinancialMetrics(
            symbol="TEST",
            company_name="Test Company",
            per=15.0,
            pbr=1.2,
            roe=0.18,
            dividend_yield=0.03,
            current_ratio=2.0,
            equity_ratio=0.5,
            debt_ratio=0.3,
            price=1000.0,
            market_cap=100000000000
        )
    
    @pytest.fixture
    def sample_growth_trend(self):
        """サンプル成長トレンド"""
        return GrowthTrend(
            symbol="TEST",
            revenue_trend=[100, 110, 121, 133, 146],
            profit_trend=[10, 12, 14, 16, 18],
            years=["2020", "2021", "2022", "2023", "2024"],
            revenue_cagr=0.10,
            profit_cagr=0.15,
            volatility=0.2
        )
    
    @pytest.fixture
    def sample_health_score(self):
        """サンプル健全性スコア"""
        return HealthScoreResult(
            symbol="TEST",
            total_score=85.0,
            score_breakdown={
                'per': 90,
                'pbr': 85,
                'roe': 95,
                'liquidity': 80,
                'stability': 85,
                'dividend': 75
            },
            health_level=HealthScore.GOOD,
            recommendations=[]
        )
    
    @pytest.fixture
    def sample_technical_data(self):
        """サンプルテクニカルデータ"""
        return TechnicalAnalysisData(
            trend="上昇",
            momentum="強い",
            support_level=950.0,
            resistance_level=1100.0,
            signal="買い"
        )
    
    def test_initialization(self, generator):
        """初期化テスト"""
        assert generator.glossary is not None
        assert isinstance(generator.glossary, FinancialGlossary)
    
    def test_assess_overall_investment_high_score(self, generator, sample_financial_metrics, sample_health_score, sample_technical_data):
        """高スコア投資評価テスト"""
        assessment, recommendation, risk_level = generator._assess_overall_investment(
            sample_financial_metrics, None, sample_health_score, sample_technical_data
        )
        
        assert "魅力的" in assessment
        assert recommendation == "買い推奨"
        assert risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
    
    def test_assess_overall_investment_low_score(self, generator):
        """低スコア投資評価テスト"""
        # 低スコアの健全性データ
        low_health_score = HealthScoreResult(
            symbol="TEST",
            total_score=25.0,
            score_breakdown={'per': 20, 'pbr': 30},
            health_level=HealthScore.CRITICAL,
            recommendations=["多くの改善が必要"]
        )
        
        # 弱いテクニカルデータ
        weak_technical = TechnicalAnalysisData(
            trend="下降",
            momentum="弱い",
            signal="売り"
        )
        
        assessment, recommendation, risk_level = generator._assess_overall_investment(
            None, None, low_health_score, weak_technical
        )
        
        assert "リスク" in assessment
        assert recommendation in ["売り推奨", "様子見"]
        assert risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]
    
    def test_generate_investment_scenarios(self, generator, sample_financial_metrics, sample_growth_trend):
        """投資シナリオ生成テスト"""
        scenarios = generator._generate_investment_scenarios(
            "TEST", sample_financial_metrics, sample_growth_trend, None, None, 1000.0
        )
        
        assert len(scenarios) == 3
        
        scenario_types = [s.scenario_type for s in scenarios]
        assert ScenarioType.OPTIMISTIC in scenario_types
        assert ScenarioType.NEUTRAL in scenario_types
        assert ScenarioType.PESSIMISTIC in scenario_types
        
        # シナリオの内容チェック
        for scenario in scenarios:
            assert scenario.title
            assert scenario.story
            assert len(scenario.key_points) > 0
            assert scenario.price_target is not None
            assert 0 <= scenario.probability <= 1
    
    def test_create_optimistic_scenario(self, generator, sample_financial_metrics, sample_growth_trend):
        """楽観シナリオ作成テスト"""
        scenario = generator._create_optimistic_scenario(
            "TEST", sample_financial_metrics, sample_growth_trend, 1000.0
        )
        
        assert scenario.scenario_type == ScenarioType.OPTIMISTIC
        assert "楽観" in scenario.title
        assert scenario.price_target > 1000.0  # 株価上昇を想定
        assert len(scenario.key_points) > 0
        assert "成長" in scenario.story or "拡大" in scenario.story
    
    def test_create_neutral_scenario(self, generator, sample_financial_metrics, sample_growth_trend):
        """中立シナリオ作成テスト"""
        scenario = generator._create_neutral_scenario(
            "TEST", sample_financial_metrics, sample_growth_trend, 1000.0
        )
        
        assert scenario.scenario_type == ScenarioType.NEUTRAL
        assert "中立" in scenario.title
        assert scenario.price_target >= 1000.0  # 安定成長を想定
        assert scenario.probability == 0.50  # 中立シナリオは50%
    
    def test_create_pessimistic_scenario(self, generator, sample_financial_metrics, sample_growth_trend):
        """悲観シナリオ作成テスト"""
        scenario = generator._create_pessimistic_scenario(
            "TEST", sample_financial_metrics, sample_growth_trend, 1000.0
        )
        
        assert scenario.scenario_type == ScenarioType.PESSIMISTIC
        assert "悲観" in scenario.title
        assert scenario.price_target < 1000.0  # 株価下落を想定
        assert scenario.risk_level == RiskLevel.HIGH
    
    def test_analyze_risk_factors(self, generator, sample_financial_metrics, sample_growth_trend, sample_health_score):
        """リスク要因分析テスト"""
        risk_factors = generator._analyze_risk_factors(
            sample_financial_metrics, sample_growth_trend, sample_health_score, None
        )
        
        assert len(risk_factors) > 0
        
        for risk in risk_factors:
            assert isinstance(risk, RiskFactor)
            assert risk.category
            assert risk.description
            assert risk.impact in ["高", "中", "低"]
            assert risk.likelihood in ["高", "中", "低"]
            assert risk.mitigation
    
    def test_analyze_risk_factors_high_per(self, generator):
        """高PERのリスク要因分析テスト"""
        high_per_metrics = FinancialMetrics(
            symbol="TEST",
            company_name="Test Company",
            per=30.0,  # 高いPER
            pbr=1.2,
            price=1000.0
        )
        
        risk_factors = generator._analyze_risk_factors(high_per_metrics, None, None, None)
        
        # バリュエーションリスクが含まれるかチェック
        risk_categories = [r.category for r in risk_factors]
        assert "バリュエーションリスク" in risk_categories
    
    def test_generate_executive_summary(self, generator):
        """エグゼクティブサマリー生成テスト"""
        scenarios = [
            InvestmentScenario(
                scenario_type=ScenarioType.NEUTRAL,
                title="中立シナリオ",
                story="テストストーリー",
                key_points=["安定成長"],
                price_target=1050.0,
                probability=0.5
            )
        ]
        
        summary = generator._generate_executive_summary(
            "TEST", "Test Company", "魅力的な投資機会", "買い推奨", scenarios
        )
        
        assert "Test Company" in summary
        assert "TEST" in summary
        assert "魅力的な投資機会" in summary
        assert "買い推奨" in summary
    
    def test_generate_detailed_analysis(self, generator, sample_financial_metrics, sample_growth_trend, sample_health_score, sample_technical_data):
        """詳細分析生成テスト"""
        analysis = generator._generate_detailed_analysis(
            sample_financial_metrics, sample_growth_trend, sample_health_score, None, sample_technical_data
        )
        
        assert len(analysis) > 0
        assert "ファンダメンタルズ分析" in analysis
        assert "成長性分析" in analysis
        assert "財務健全性分析" in analysis
        assert "テクニカル分析" in analysis
    
    def test_generate_comprehensive_report(self, generator, sample_financial_metrics, sample_growth_trend, sample_health_score, sample_technical_data):
        """包括的レポート生成テスト"""
        report = generator.generate_comprehensive_report(
            symbol="TEST",
            financial_metrics=sample_financial_metrics,
            growth_trend=sample_growth_trend,
            health_score=sample_health_score,
            technical_data=sample_technical_data,
            current_price=1000.0
        )
        
        assert isinstance(report, InvestmentReport)
        assert report.symbol == "TEST"
        assert report.company_name == "Test Company"
        assert report.current_price == 1000.0
        assert len(report.scenarios) == 3
        assert len(report.risk_factors) > 0
        assert report.executive_summary
        assert report.detailed_analysis
        assert isinstance(report.glossary, list)
    
    def test_generate_comprehensive_report_minimal_data(self, generator):
        """最小データでの包括的レポート生成テスト"""
        report = generator.generate_comprehensive_report(
            symbol="TEST",
            current_price=1000.0
        )
        
        assert isinstance(report, InvestmentReport)
        assert report.symbol == "TEST"
        assert report.current_price == 1000.0
        assert len(report.scenarios) == 3  # デフォルトシナリオが生成される
    
    def test_create_default_report(self, generator):
        """デフォルトレポート作成テスト"""
        report = generator._create_default_report("TEST", "Test Company", 1000.0)
        
        assert isinstance(report, InvestmentReport)
        assert report.symbol == "TEST"
        assert report.company_name == "Test Company"
        assert report.current_price == 1000.0
        assert report.overall_risk_level == RiskLevel.VERY_HIGH
        assert len(report.scenarios) == 1
        assert len(report.risk_factors) == 1


class TestDataClasses:
    """データクラスのテスト"""
    
    def test_investment_scenario_creation(self):
        """InvestmentScenarioデータクラステスト"""
        scenario = InvestmentScenario(
            scenario_type=ScenarioType.OPTIMISTIC,
            title="テストシナリオ",
            story="テストストーリー",
            key_points=["ポイント1", "ポイント2"],
            price_target=1200.0,
            probability=0.3,
            risk_level=RiskLevel.MEDIUM
        )
        
        assert scenario.scenario_type == ScenarioType.OPTIMISTIC
        assert scenario.title == "テストシナリオ"
        assert scenario.story == "テストストーリー"
        assert len(scenario.key_points) == 2
        assert scenario.price_target == 1200.0
        assert scenario.probability == 0.3
        assert scenario.risk_level == RiskLevel.MEDIUM
    
    def test_risk_factor_creation(self):
        """RiskFactorデータクラステスト"""
        risk = RiskFactor(
            category="市場リスク",
            description="市場全体の下落リスク",
            impact="中",
            likelihood="中",
            mitigation="分散投資"
        )
        
        assert risk.category == "市場リスク"
        assert risk.description == "市場全体の下落リスク"
        assert risk.impact == "中"
        assert risk.likelihood == "中"
        assert risk.mitigation == "分散投資"
    
    def test_glossary_term_creation(self):
        """GlossaryTermデータクラステスト"""
        term = GlossaryTerm(
            term="PER",
            definition="株価収益率",
            example="PER15倍の例"
        )
        
        assert term.term == "PER"
        assert term.definition == "株価収益率"
        assert term.example == "PER15倍の例"
    
    def test_technical_analysis_data_creation(self):
        """TechnicalAnalysisDataデータクラステスト"""
        technical = TechnicalAnalysisData(
            trend="上昇",
            momentum="強い",
            support_level=950.0,
            resistance_level=1100.0,
            signal="買い"
        )
        
        assert technical.trend == "上昇"
        assert technical.momentum == "強い"
        assert technical.support_level == 950.0
        assert technical.resistance_level == 1100.0
        assert technical.signal == "買い"
    
    def test_investment_report_creation(self):
        """InvestmentReportデータクラステスト"""
        scenario = InvestmentScenario(
            scenario_type=ScenarioType.NEUTRAL,
            title="テスト",
            story="テスト",
            key_points=["テスト"]
        )
        
        risk = RiskFactor(
            category="テスト",
            description="テスト",
            impact="中",
            likelihood="中",
            mitigation="テスト"
        )
        
        term = GlossaryTerm(term="テスト", definition="テスト")
        
        report = InvestmentReport(
            symbol="TEST",
            company_name="Test Company",
            current_price=1000.0,
            analysis_date=datetime.now(),
            overall_assessment="テスト評価",
            recommendation="買い推奨",
            scenarios=[scenario],
            risk_factors=[risk],
            overall_risk_level=RiskLevel.MEDIUM,
            executive_summary="テストサマリー",
            detailed_analysis="テスト詳細",
            glossary=[term]
        )
        
        assert report.symbol == "TEST"
        assert report.company_name == "Test Company"
        assert report.current_price == 1000.0
        assert report.overall_assessment == "テスト評価"
        assert report.recommendation == "買い推奨"
        assert len(report.scenarios) == 1
        assert len(report.risk_factors) == 1
        assert report.overall_risk_level == RiskLevel.MEDIUM
        assert report.executive_summary == "テストサマリー"
        assert report.detailed_analysis == "テスト詳細"
        assert len(report.glossary) == 1


class TestEnums:
    """Enumクラスのテスト"""
    
    def test_scenario_type_enum(self):
        """ScenarioTypeEnumテスト"""
        assert ScenarioType.OPTIMISTIC.value == "楽観的"
        assert ScenarioType.NEUTRAL.value == "中立的"
        assert ScenarioType.PESSIMISTIC.value == "悲観的"
    
    def test_risk_level_enum(self):
        """RiskLevelEnumテスト"""
        assert RiskLevel.LOW.value == "低リスク"
        assert RiskLevel.MEDIUM.value == "中リスク"
        assert RiskLevel.HIGH.value == "高リスク"
        assert RiskLevel.VERY_HIGH.value == "非常に高いリスク"


if __name__ == "__main__":
    pytest.main([__file__])