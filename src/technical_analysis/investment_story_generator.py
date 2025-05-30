"""
投資シナリオ・ストーリー生成モジュール

分析結果を初心者にも理解しやすい自然言語のストーリー形式で提供し、
投資シナリオの自動生成（楽観・中立・悲観）、リスク要因の整理、
初心者向けの用語解説付きレポートを生成する
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger

from .fundamental_analysis import (
    FinancialMetrics,
    GrowthTrend,
    HealthScoreResult,
    ComparisonResult,
)


class ScenarioType(Enum):
    """投資シナリオの種類"""

    OPTIMISTIC = "楽観的"
    NEUTRAL = "中立的"
    PESSIMISTIC = "悲観的"


class RiskLevel(Enum):
    """リスクレベル"""

    LOW = "低リスク"
    MEDIUM = "中リスク"
    HIGH = "高リスク"
    VERY_HIGH = "非常に高いリスク"


@dataclass
class InvestmentScenario:
    """投資シナリオデータクラス"""

    scenario_type: ScenarioType
    title: str
    story: str
    key_points: List[str]
    price_target: Optional[float] = None
    time_horizon: str = "1年"
    probability: float = 0.0
    risk_level: RiskLevel = RiskLevel.MEDIUM


@dataclass
class RiskFactor:
    """リスク要因データクラス"""

    category: str
    description: str
    impact: str  # "高", "中", "低"
    likelihood: str  # "高", "中", "低"
    mitigation: str


@dataclass
class TechnicalAnalysisData:
    """テクニカル分析データ（簡略版）"""

    trend: str  # "上昇", "下降", "横ばい"
    momentum: str  # "強い", "普通", "弱い"
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    signal: str = "中立"  # "買い", "売り", "中立"


@dataclass
class GlossaryTerm:
    """用語解説データクラス"""

    term: str
    definition: str
    example: Optional[str] = None


@dataclass
class InvestmentReport:
    """投資レポートデータクラス"""

    symbol: str
    company_name: str
    current_price: float
    analysis_date: datetime

    # 分析結果サマリー
    overall_assessment: str
    recommendation: str  # "買い推奨", "保有", "売り推奨", "様子見"

    # シナリオ
    scenarios: List[InvestmentScenario]

    # リスク分析
    risk_factors: List[RiskFactor]
    overall_risk_level: RiskLevel

    # 自然言語での説明
    executive_summary: str
    detailed_analysis: str

    # 用語解説
    glossary: List[GlossaryTerm]


class FinancialGlossary:
    """金融用語解説クラス"""

    TERMS = {
        "PER": {
            "definition": "株価収益率。株価が1株あたり純利益の何倍かを示す指標",
            "example": "PERが15倍なら、その会社が今の利益を続けた場合、15年で投資額を回収できる計算になります",
        },
        "PBR": {
            "definition": "株価純資産倍率。株価が1株あたり純資産の何倍かを示す指標",
            "example": "PBRが1倍を下回ると、会社の資産価値より株価が安いことを意味します",
        },
        "ROE": {
            "definition": "自己資本利益率。株主が投資したお金でどれだけ効率的に利益を生み出しているかを示す",
            "example": "ROE15%なら、100万円投資すると年間15万円の利益を生み出している計算です",
        },
        "配当利回り": {
            "definition": "株価に対する年間配当金の割合",
            "example": "配当利回り3%なら、100万円投資すると年間3万円の配当を受け取れます",
        },
        "流動比率": {
            "definition": "短期的な支払い能力を示す指標。200%以上が理想的",
            "example": "流動比率200%なら、短期的な借金の2倍の現金・資産を持っていることを意味します",
        },
        "自己資本比率": {
            "definition": "総資産に占める自己資本の割合。財務の安定性を示す",
            "example": "自己資本比率50%なら、会社の資産の半分が借金ではなく自己資金ということです",
        },
        "CAGR": {
            "definition": "年平均成長率。複数年にわたる成長率の平均",
            "example": "売上のCAGR10%なら、毎年平均10%ずつ売上が成長していることを意味します",
        },
        "サポートライン": {
            "definition": "株価が下がりにくい価格帯。買い支えが入りやすいレベル",
            "example": "1000円のサポートラインなら、株価が1000円近くになると買いが入りやすくなります",
        },
        "レジスタンスライン": {
            "definition": "株価が上がりにくい価格帯。売り圧力が強くなるレベル",
            "example": "1200円のレジスタンスラインなら、株価が1200円近くになると売りが増えやすくなります",
        },
    }

    @classmethod
    def get_term(cls, term: str) -> Optional[GlossaryTerm]:
        """用語解説を取得"""
        if term in cls.TERMS:
            term_data = cls.TERMS[term]
            return GlossaryTerm(
                term=term,
                definition=term_data["definition"],
                example=term_data.get("example"),
            )
        return None

    @classmethod
    def get_relevant_terms(cls, content: str) -> List[GlossaryTerm]:
        """コンテンツに含まれる用語の解説を取得"""
        terms = []
        for term in cls.TERMS.keys():
            if term in content:
                glossary_term = cls.get_term(term)
                if glossary_term:
                    terms.append(glossary_term)
        return terms


class InvestmentStoryGenerator:
    """投資ストーリー生成メインクラス"""

    def __init__(self):
        """初期化"""
        self.glossary = FinancialGlossary()

    def generate_comprehensive_report(
        self,
        symbol: str,
        financial_metrics: Optional[FinancialMetrics] = None,
        growth_trend: Optional[GrowthTrend] = None,
        health_score: Optional[HealthScoreResult] = None,
        comparison: Optional[ComparisonResult] = None,
        technical_data: Optional[TechnicalAnalysisData] = None,
        current_price: Optional[float] = None,
    ) -> InvestmentReport:
        """包括的な投資レポートを生成"""
        try:
            company_name = (
                financial_metrics.company_name if financial_metrics else symbol
            )
            price = current_price or (
                financial_metrics.price if financial_metrics else 0.0
            )

            # 全体評価を決定
            overall_assessment, recommendation, risk_level = (
                self._assess_overall_investment(
                    financial_metrics, growth_trend, health_score, technical_data
                )
            )

            # シナリオ生成
            scenarios = self._generate_investment_scenarios(
                symbol,
                financial_metrics,
                growth_trend,
                health_score,
                technical_data,
                price,
            )

            # リスク要因分析
            risk_factors = self._analyze_risk_factors(
                financial_metrics, growth_trend, health_score, technical_data
            )

            # 自然言語での説明生成
            executive_summary = self._generate_executive_summary(
                symbol, company_name, overall_assessment, recommendation, scenarios
            )

            detailed_analysis = self._generate_detailed_analysis(
                financial_metrics,
                growth_trend,
                health_score,
                comparison,
                technical_data,
            )

            # 用語解説の抽出
            all_content = f"{executive_summary} {detailed_analysis}"
            glossary_terms = self.glossary.get_relevant_terms(all_content)

            report = InvestmentReport(
                symbol=symbol,
                company_name=company_name,
                current_price=price,
                analysis_date=datetime.now(),
                overall_assessment=overall_assessment,
                recommendation=recommendation,
                scenarios=scenarios,
                risk_factors=risk_factors,
                overall_risk_level=risk_level,
                executive_summary=executive_summary,
                detailed_analysis=detailed_analysis,
                glossary=glossary_terms,
            )

            logger.info(f"投資レポート生成完了: {symbol}")
            return report

        except Exception as e:
            logger.error(f"投資レポート生成エラー {symbol}: {str(e)}")
            # エラー時はデフォルトレポートを返す
            return self._create_default_report(symbol, company_name, price)

    def _assess_overall_investment(
        self,
        financial_metrics: Optional[FinancialMetrics],
        growth_trend: Optional[GrowthTrend],
        health_score: Optional[HealthScoreResult],
        technical_data: Optional[TechnicalAnalysisData],
    ) -> Tuple[str, str, RiskLevel]:
        """全体的な投資評価を決定"""

        # スコア計算
        fundamental_score = 0
        technical_score = 0

        if health_score:
            fundamental_score = health_score.total_score

        if technical_data:
            if technical_data.signal == "買い":
                technical_score = 80
            elif technical_data.signal == "売り":
                technical_score = 20
            else:
                technical_score = 50

        # 成長性ボーナス
        growth_bonus = 0
        if (
            growth_trend
            and growth_trend.revenue_cagr
            and growth_trend.revenue_cagr > 0.1
        ):
            growth_bonus = 10

        total_score = fundamental_score * 0.6 + technical_score * 0.4 + growth_bonus

        # 評価決定
        if total_score >= 80:
            assessment = "非常に魅力的な投資機会"
            recommendation = "買い推奨"
            risk_level = RiskLevel.LOW
        elif total_score >= 65:
            assessment = "魅力的な投資機会"
            recommendation = "買い推奨"
            risk_level = RiskLevel.MEDIUM
        elif total_score >= 50:
            assessment = "バランスの取れた投資"
            recommendation = "保有"
            risk_level = RiskLevel.MEDIUM
        elif total_score >= 35:
            assessment = "慎重な検討が必要"
            recommendation = "様子見"
            risk_level = RiskLevel.HIGH
        else:
            assessment = "リスクの高い投資"
            recommendation = "売り推奨"
            risk_level = RiskLevel.VERY_HIGH

        return assessment, recommendation, risk_level

    def _generate_investment_scenarios(
        self,
        symbol: str,
        financial_metrics: Optional[FinancialMetrics],
        growth_trend: Optional[GrowthTrend],
        health_score: Optional[HealthScoreResult],
        technical_data: Optional[TechnicalAnalysisData],
        current_price: float,
    ) -> List[InvestmentScenario]:
        """3つの投資シナリオを生成"""

        scenarios = []

        # 楽観シナリオ
        optimistic = self._create_optimistic_scenario(
            symbol, financial_metrics, growth_trend, current_price
        )
        scenarios.append(optimistic)

        # 中立シナリオ
        neutral = self._create_neutral_scenario(
            symbol, financial_metrics, growth_trend, current_price
        )
        scenarios.append(neutral)

        # 悲観シナリオ
        pessimistic = self._create_pessimistic_scenario(
            symbol, financial_metrics, growth_trend, current_price
        )
        scenarios.append(pessimistic)

        return scenarios

    def _create_optimistic_scenario(
        self,
        symbol: str,
        financial_metrics: Optional[FinancialMetrics],
        growth_trend: Optional[GrowthTrend],
        current_price: float,
    ) -> InvestmentScenario:
        """楽観的シナリオの作成"""

        growth_rate = 0.15  # デフォルト15%成長
        if growth_trend and growth_trend.revenue_cagr:
            growth_rate = max(
                growth_trend.revenue_cagr * 1.2, 0.1
            )  # 20%上乗せ、最低10%

        target_price = current_price * (1 + growth_rate)

        story = f"""
        【楽観シナリオ】
        
        {symbol}の事業が順調に拡大し、市場予想を上回る成長を実現するシナリオです。
        
        この場合、売上成長が加速し、利益率も改善することで、株価は大きく上昇する可能性があります。
        特に業界全体の追い風が続けば、同社の競争優位性が発揮され、
        市場シェアの拡大とともに収益性も向上することが期待されます。
        
        投資家の注目度も高まり、PERの上昇も相まって株価の大幅な上昇が見込まれます。
        """

        key_points = [
            f"売上成長率が{growth_rate:.1%}に加速",
            "利益率の改善による収益性向上",
            "市場シェア拡大による競争優位性の確立",
            "投資家の評価向上によるPER上昇",
        ]

        return InvestmentScenario(
            scenario_type=ScenarioType.OPTIMISTIC,
            title=f"{symbol} 楽観シナリオ：事業拡大による大幅成長",
            story=story.strip(),
            key_points=key_points,
            price_target=target_price,
            probability=0.25,
            risk_level=RiskLevel.MEDIUM,
        )

    def _create_neutral_scenario(
        self,
        symbol: str,
        financial_metrics: Optional[FinancialMetrics],
        growth_trend: Optional[GrowthTrend],
        current_price: float,
    ) -> InvestmentScenario:
        """中立的シナリオの作成"""

        growth_rate = 0.05  # 安定成長5%
        if growth_trend and growth_trend.revenue_cagr:
            growth_rate = max(
                growth_trend.revenue_cagr, 0.02
            )  # 現在の成長率を維持、最低2%

        target_price = current_price * (1 + growth_rate)

        story = f"""
        【中立シナリオ】
        
        {symbol}が現在の事業ペースを維持し、安定的な成長を続けるシナリオです。
        
        大きなサプライズはないものの、着実に業績を伸ばし、
        市場の期待に沿った成長を実現することが予想されます。
        
        この場合、株価は業績の成長に沿って緩やかに上昇し、
        配当利回りも安定的に維持されることが期待されます。
        
        リスクとリターンのバランスが取れた、堅実な投資となるでしょう。
        """

        key_points = [
            f"安定的な{growth_rate:.1%}の成長維持",
            "市場予想に沿った業績達成",
            "配当利回りの安定的な維持",
            "リスクバランスの取れた投資",
        ]

        return InvestmentScenario(
            scenario_type=ScenarioType.NEUTRAL,
            title=f"{symbol} 中立シナリオ：安定成長の継続",
            story=story.strip(),
            key_points=key_points,
            price_target=target_price,
            probability=0.50,
            risk_level=RiskLevel.MEDIUM,
        )

    def _create_pessimistic_scenario(
        self,
        symbol: str,
        financial_metrics: Optional[FinancialMetrics],
        growth_trend: Optional[GrowthTrend],
        current_price: float,
    ) -> InvestmentScenario:
        """悲観的シナリオの作成"""

        decline_rate = -0.15  # 15%下落
        target_price = current_price * (1 + decline_rate)

        story = f"""
        【悲観シナリオ】
        
        {symbol}の事業環境が悪化し、業績が市場予想を下回るシナリオです。
        
        競争激化や市場縮小、経済情勢の悪化などにより、
        売上成長が鈍化し、利益率も圧迫される可能性があります。
        
        この場合、投資家の信頼が低下し、株価は大きく下落するリスクがあります。
        特に高いPERで取引されている場合、評価の見直しにより
        株価下落が加速する可能性もあります。
        
        慎重な投資判断が求められる状況となるでしょう。
        """

        key_points = [
            "競争激化による売上成長の鈍化",
            "利益率圧迫による収益性悪化",
            "投資家信頼の低下によるPER下落",
            "市場環境悪化のリスク顕在化",
        ]

        return InvestmentScenario(
            scenario_type=ScenarioType.PESSIMISTIC,
            title=f"{symbol} 悲観シナリオ：事業環境悪化による下落",
            story=story.strip(),
            key_points=key_points,
            price_target=target_price,
            probability=0.25,
            risk_level=RiskLevel.HIGH,
        )

    def _analyze_risk_factors(
        self,
        financial_metrics: Optional[FinancialMetrics],
        growth_trend: Optional[GrowthTrend],
        health_score: Optional[HealthScoreResult],
        technical_data: Optional[TechnicalAnalysisData],
    ) -> List[RiskFactor]:
        """リスク要因の分析"""

        risk_factors = []

        # 財務リスクの分析
        if financial_metrics:
            if financial_metrics.per and financial_metrics.per > 25:
                risk_factors.append(
                    RiskFactor(
                        category="バリュエーションリスク",
                        description=f"PERが{financial_metrics.per:.1f}倍と高水準",
                        impact="高",
                        likelihood="中",
                        mitigation="業績成長による評価の正当化を確認",
                    )
                )

            if financial_metrics.debt_ratio and financial_metrics.debt_ratio > 0.6:
                risk_factors.append(
                    RiskFactor(
                        category="財務リスク",
                        description=f"負債比率が{financial_metrics.debt_ratio:.1%}と高水準",
                        impact="中",
                        likelihood="中",
                        mitigation="キャッシュフロー改善による負債削減を監視",
                    )
                )

        # 成長リスクの分析
        if growth_trend:
            if growth_trend.volatility and growth_trend.volatility > 0.3:
                risk_factors.append(
                    RiskFactor(
                        category="業績ボラティリティリスク",
                        description="利益の変動が大きく、予測が困難",
                        impact="中",
                        likelihood="高",
                        mitigation="四半期業績の動向を注意深く監視",
                    )
                )

        # 市場リスク
        risk_factors.append(
            RiskFactor(
                category="市場リスク",
                description="株式市場全体の下落による影響",
                impact="中",
                likelihood="中",
                mitigation="分散投資によるリスク軽減",
            )
        )

        # 流動性リスク
        risk_factors.append(
            RiskFactor(
                category="流動性リスク",
                description="取引量減少による売買の困難",
                impact="低",
                likelihood="低",
                mitigation="適切なポジションサイズでの投資",
            )
        )

        return risk_factors

    def _generate_executive_summary(
        self,
        symbol: str,
        company_name: str,
        overall_assessment: str,
        recommendation: str,
        scenarios: List[InvestmentScenario],
    ) -> str:
        """エグゼクティブサマリーの生成"""

        main_scenario = next(
            (s for s in scenarios if s.scenario_type == ScenarioType.NEUTRAL),
            scenarios[0],
        )

        summary = f"""
        【投資判断サマリー】
        
        {company_name}（{symbol}）は、{overall_assessment}と評価されます。
        
        推奨投資判断：{recommendation}
        
        中心的なシナリオでは、{main_scenario.key_points[0]}が予想され、
        株価は現在の水準から{main_scenario.probability:.0%}の確率で
        目標価格{main_scenario.price_target:.0f}円程度への上昇が期待されます。
        
        ただし、市場環境の変化や競争状況によっては、
        楽観・悲観シナリオへの展開も十分に考えられるため、
        定期的な業績モニタリングが重要です。
        
        投資を検討される際は、個人のリスク許容度と投資目的を
        十分に考慮した上で判断することをお勧めします。
        """

        return summary.strip()

    def _generate_detailed_analysis(
        self,
        financial_metrics: Optional[FinancialMetrics],
        growth_trend: Optional[GrowthTrend],
        health_score: Optional[HealthScoreResult],
        comparison: Optional[ComparisonResult],
        technical_data: Optional[TechnicalAnalysisData],
    ) -> str:
        """詳細分析の生成"""

        sections = []

        # ファンダメンタルズ分析
        if financial_metrics:
            fundamental_section = f"""
            【ファンダメンタルズ分析】
            
            財務指標の観点では、PER{financial_metrics.per:.1f}倍、PBR{financial_metrics.pbr:.1f}倍
            での取引となっており、"""

            if financial_metrics.per and financial_metrics.per < 15:
                fundamental_section += "バリュエーションは魅力的な水準にあります。"
            elif financial_metrics.per and financial_metrics.per > 25:
                fundamental_section += "やや割高な水準での取引となっています。"
            else:
                fundamental_section += "適正な水準での取引と考えられます。"

            if financial_metrics.roe:
                fundamental_section += f"\n\nROEは{financial_metrics.roe:.1%}であり、"
                if financial_metrics.roe > 0.15:
                    fundamental_section += "優れた資本効率を示しています。"
                elif financial_metrics.roe > 0.1:
                    fundamental_section += "良好な資本効率を維持しています。"
                else:
                    fundamental_section += "資本効率の改善が期待されます。"

            sections.append(fundamental_section)

        # 成長性分析
        if growth_trend:
            growth_section = "【成長性分析】\n\n"
            if growth_trend.revenue_cagr:
                growth_section += (
                    f"過去の売上成長率（CAGR）は{growth_trend.revenue_cagr:.1%}であり、"
                )
                if growth_trend.revenue_cagr > 0.1:
                    growth_section += "力強い成長を示しています。"
                elif growth_trend.revenue_cagr > 0.05:
                    growth_section += "安定的な成長を続けています。"
                else:
                    growth_section += "成長の鈍化が見られます。"

            if growth_trend.profit_cagr:
                growth_section += f"\n利益面では、CAGR{growth_trend.profit_cagr:.1%}の成長を実現しており、"
                if growth_trend.profit_cagr > growth_trend.revenue_cagr:
                    growth_section += "効率性の改善も伴った質の高い成長といえます。"
                else:
                    growth_section += "売上成長に見合った利益成長を達成しています。"

            sections.append(growth_section)

        # 健全性分析
        if health_score:
            health_section = f"""
            【財務健全性分析】
            
            財務健全性スコアは{health_score.total_score:.0f}点（{health_score.health_level.value}）
            となっており、"""

            if health_score.total_score >= 80:
                health_section += "非常に安定した財務基盤を有しています。"
            elif health_score.total_score >= 60:
                health_section += "良好な財務状況を維持しています。"
            else:
                health_section += "財務面での改善が期待されます。"

            if health_score.recommendations:
                health_section += "\n\n注意すべき点として、以下が挙げられます：\n"
                for rec in health_score.recommendations[:2]:  # 最大2個まで
                    health_section += f"・{rec}\n"

            sections.append(health_section)

        # テクニカル分析
        if technical_data:
            technical_section = f"""
            【テクニカル分析】
            
            チャート分析では、現在のトレンドは{technical_data.trend}傾向にあり、
            モメンタムは{technical_data.momentum}状態です。
            
            テクニカルシグナルは「{technical_data.signal}」を示しており、"""

            if technical_data.signal == "買い":
                technical_section += "短期的な上昇を示唆しています。"
            elif technical_data.signal == "売り":
                technical_section += "短期的な下落リスクを示唆しています。"
            else:
                technical_section += "明確な方向性は見られません。"

            if technical_data.support_level and technical_data.resistance_level:
                technical_section += (
                    f"\n\nサポートライン{technical_data.support_level:.0f}円、"
                )
                technical_section += (
                    f"レジスタンスライン{technical_data.resistance_level:.0f}円が"
                )
                technical_section += "重要な節目となります。"

            sections.append(technical_section)

        return "\n\n".join(sections)

    def _create_default_report(
        self, symbol: str, company_name: str, price: float
    ) -> InvestmentReport:
        """デフォルトレポートの作成（エラー時）"""

        default_scenario = InvestmentScenario(
            scenario_type=ScenarioType.NEUTRAL,
            title=f"{symbol} 基本シナリオ",
            story="データが不足しているため、詳細な分析を実施できませんでした。",
            key_points=["データ不足により分析困難"],
            price_target=price,
            probability=1.0,
            risk_level=RiskLevel.HIGH,
        )

        return InvestmentReport(
            symbol=symbol,
            company_name=company_name,
            current_price=price,
            analysis_date=datetime.now(),
            overall_assessment="データ不足により評価困難",
            recommendation="様子見",
            scenarios=[default_scenario],
            risk_factors=[
                RiskFactor(
                    category="データリスク",
                    description="分析に必要なデータが不足",
                    impact="高",
                    likelihood="高",
                    mitigation="データ取得後の再分析を実施",
                )
            ],
            overall_risk_level=RiskLevel.VERY_HIGH,
            executive_summary="データ不足により詳細な投資判断ができません。",
            detailed_analysis="十分なデータが取得でき次第、再度分析を実施してください。",
            glossary=[],
        )
