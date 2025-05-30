"""
NISA枠管理機能

NISA（少額投資非課税制度）の枠管理と最適化提案を行う。
- 新NISA（成長投資枠、つみたて投資枠）
- 旧NISA制度との併用管理
"""

from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from loguru import logger

from ..config.settings import settings_manager


class NisaType(Enum):
    """NISA区分"""
    GROWTH = "growth"  # 成長投資枠
    TSUMITATE = "tsumitate"  # つみたて投資枠
    OLD_NISA = "old_nisa"  # 一般NISA（旧制度）
    OLD_TSUMITATE = "old_tsumitate"  # つみたてNISA（旧制度）


@dataclass
class NisaLimits:
    """NISA制度の投資限度額"""
    year: int
    growth_annual: int  # 成長投資枠年間限度額
    tsumitate_annual: int  # つみたて投資枠年間限度額
    total_lifetime: int  # 生涯投資枠
    growth_lifetime: int  # 成長投資枠生涯限度額


@dataclass
class NisaInvestment:
    """NISA投資記録"""
    symbol: str
    date: date
    amount: Decimal
    nisa_type: NisaType
    year: int = field(init=False)
    
    def __post_init__(self):
        self.year = self.date.year


@dataclass
class NisaStatus:
    """NISA利用状況"""
    year: int
    growth_used: Decimal
    tsumitate_used: Decimal
    growth_remaining: Decimal
    tsumitate_remaining: Decimal
    total_used: Decimal
    total_remaining_lifetime: Decimal


class NisaManager:
    """NISA枠管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.config = settings_manager.settings.tax_calculator
        self.investments: List[NisaInvestment] = []
        self.nisa_limits = self._get_nisa_limits()
    
    def _get_nisa_limits(self) -> Dict[int, NisaLimits]:
        """年度別NISA限度額設定"""
        limits = {}
        
        # 2024年からの新NISA制度
        for year in range(2024, 2030):  # 2030年まで設定
            limits[year] = NisaLimits(
                year=year,
                growth_annual=2400000,  # 240万円
                tsumitate_annual=1200000,  # 120万円
                total_lifetime=18000000,  # 1800万円
                growth_lifetime=12000000  # 1200万円
            )
        
        # 旧制度（参考）
        for year in range(2018, 2024):
            limits[year] = NisaLimits(
                year=year,
                growth_annual=1200000,  # 一般NISA 120万円
                tsumitate_annual=400000,  # つみたてNISA 40万円
                total_lifetime=6000000,  # 参考値
                growth_lifetime=6000000  # 参考値
            )
        
        return limits
    
    def add_investment(self, investment: NisaInvestment) -> bool:
        """NISA投資を追加"""
        year = investment.date.year
        
        # 投資限度額チェック
        if not self._check_investment_limit(investment):
            logger.warning(f"NISA投資限度額超過: {investment.symbol} {investment.amount}")
            return False
        
        self.investments.append(investment)
        logger.info(f"NISA投資追加: {investment.symbol} {investment.amount} ({investment.nisa_type.value})")
        return True
    
    def _check_investment_limit(self, investment: NisaInvestment) -> bool:
        """投資限度額チェック"""
        year = investment.date.year
        
        if year not in self.nisa_limits:
            logger.warning(f"NISA制度対象外の年度: {year}")
            return False
        
        limits = self.nisa_limits[year]
        current_status = self.get_nisa_status(year)
        
        if investment.nisa_type == NisaType.GROWTH:
            return (current_status.growth_used + investment.amount) <= limits.growth_annual
        elif investment.nisa_type == NisaType.TSUMITATE:
            return (current_status.tsumitate_used + investment.amount) <= limits.tsumitate_annual
        
        return True
    
    def get_nisa_status(self, year: int) -> NisaStatus:
        """指定年のNISA利用状況を取得"""
        if year not in self.nisa_limits:
            return NisaStatus(
                year=year,
                growth_used=Decimal('0'),
                tsumitate_used=Decimal('0'),
                growth_remaining=Decimal('0'),
                tsumitate_remaining=Decimal('0'),
                total_used=Decimal('0'),
                total_remaining_lifetime=Decimal('0')
            )
        
        limits = self.nisa_limits[year]
        
        # 年間利用状況
        year_investments = [inv for inv in self.investments if inv.year == year]
        
        growth_used = sum(
            inv.amount for inv in year_investments 
            if inv.nisa_type == NisaType.GROWTH
        )
        
        tsumitate_used = sum(
            inv.amount for inv in year_investments 
            if inv.nisa_type == NisaType.TSUMITATE
        )
        
        # 残り枠計算
        growth_remaining = Decimal(str(limits.growth_annual)) - growth_used
        tsumitate_remaining = Decimal(str(limits.tsumitate_annual)) - tsumitate_used
        
        # 生涯投資枠の利用状況
        total_used_all_years = sum(inv.amount for inv in self.investments)
        total_remaining_lifetime = Decimal(str(limits.total_lifetime)) - total_used_all_years
        
        return NisaStatus(
            year=year,
            growth_used=growth_used,
            tsumitate_used=tsumitate_used,
            growth_remaining=max(Decimal('0'), growth_remaining),
            tsumitate_remaining=max(Decimal('0'), tsumitate_remaining),
            total_used=growth_used + tsumitate_used,
            total_remaining_lifetime=max(Decimal('0'), total_remaining_lifetime)
        )
    
    def calculate_tax_savings(self, year: int) -> Dict[str, Decimal]:
        """NISA による税務メリット計算"""
        year_investments = [inv for inv in self.investments if inv.year == year]
        total_nisa_amount = sum(inv.amount for inv in year_investments)
        
        # 仮想的な税率を適用して節税効果を計算
        tax_rate = Decimal(str(self.config.capital_gains_tax_rate))
        
        # 想定利回り（年5%で計算）
        assumed_return_rate = Decimal('0.05')
        assumed_profit = total_nisa_amount * assumed_return_rate
        
        # 節税額（課税口座なら支払うべき税金）
        tax_savings = assumed_profit * tax_rate
        
        return {
            "nisa_investment": total_nisa_amount,
            "assumed_profit": assumed_profit,
            "tax_savings": tax_savings,
            "effective_return_rate": (assumed_profit / total_nisa_amount * 100) if total_nisa_amount > 0 else Decimal('0')
        }
    
    def suggest_optimal_allocation(self, 
                                  available_amount: Decimal, 
                                  year: int,
                                  investment_horizon: int = 20) -> Dict[str, Any]:
        """最適なNISA枠配分の提案"""
        status = self.get_nisa_status(year)
        
        suggestions = {
            "total_available": available_amount,
            "recommendations": [],
            "remaining_after_allocation": available_amount
        }
        
        remaining = available_amount
        
        # つみたて投資枠優先（長期投資向け）
        if status.tsumitate_remaining > 0 and investment_horizon >= 10:
            tsumitate_allocation = min(remaining, status.tsumitate_remaining)
            if tsumitate_allocation > 0:
                suggestions["recommendations"].append({
                    "type": "つみたて投資枠",
                    "amount": tsumitate_allocation,
                    "reason": "長期積立投資に最適、手数料が低い商品が対象",
                    "priority": 1
                })
                remaining -= tsumitate_allocation
        
        # 成長投資枠
        if status.growth_remaining > 0 and remaining > 0:
            growth_allocation = min(remaining, status.growth_remaining)
            suggestions["recommendations"].append({
                "type": "成長投資枠",
                "amount": growth_allocation,
                "reason": "個別株や投資信託等、幅広い商品に投資可能",
                "priority": 2
            })
            remaining -= growth_allocation
        
        suggestions["remaining_after_allocation"] = remaining
        
        # 課税口座での投資が必要な場合
        if remaining > 0:
            suggestions["recommendations"].append({
                "type": "課税口座",
                "amount": remaining,
                "reason": "NISA枠を超過した分",
                "priority": 3
            })
        
        return suggestions
    
    def get_monthly_investment_plan(self, 
                                   annual_budget: Decimal, 
                                   year: int) -> Dict[str, Any]:
        """月次投資計画の作成"""
        status = self.get_nisa_status(year)
        
        # 利用可能なNISA枠
        available_nisa = status.growth_remaining + status.tsumitate_remaining
        nisa_budget = min(annual_budget, available_nisa)
        
        # 月次配分
        monthly_nisa = nisa_budget / 12
        monthly_total = annual_budget / 12
        monthly_taxable = (annual_budget - nisa_budget) / 12
        
        plan = {
            "annual_budget": annual_budget,
            "nisa_allocation": nisa_budget,
            "taxable_allocation": annual_budget - nisa_budget,
            "monthly_plan": {
                "total": monthly_total,
                "nisa": monthly_nisa,
                "taxable": monthly_taxable
            },
            "recommendations": []
        }
        
        # つみたて投資枠の活用提案
        if status.tsumitate_remaining > 0:
            monthly_tsumitate = min(monthly_nisa, status.tsumitate_remaining / 12)
            plan["recommendations"].append({
                "type": "つみたて投資枠",
                "monthly_amount": monthly_tsumitate,
                "annual_amount": monthly_tsumitate * 12,
                "products": ["投資信託", "ETF（つみたて対象）"]
            })
        
        # 成長投資枠の活用提案
        if status.growth_remaining > 0:
            remaining_monthly = monthly_nisa - (monthly_tsumitate if 'monthly_tsumitate' in locals() else Decimal('0'))
            if remaining_monthly > 0:
                plan["recommendations"].append({
                    "type": "成長投資枠",
                    "monthly_amount": remaining_monthly,
                    "annual_amount": remaining_monthly * 12,
                    "products": ["個別株", "投資信託", "ETF", "REIT"]
                })
        
        return plan
    
    def generate_nisa_report(self, year: int) -> Dict[str, Any]:
        """NISA年次レポート生成"""
        status = self.get_nisa_status(year)
        tax_savings = self.calculate_tax_savings(year)
        
        year_investments = [inv for inv in self.investments if inv.year == year]
        
        # 投資先別集計
        investment_by_symbol = {}
        for inv in year_investments:
            if inv.symbol not in investment_by_symbol:
                investment_by_symbol[inv.symbol] = {
                    "growth": Decimal('0'),
                    "tsumitate": Decimal('0'),
                    "total": Decimal('0')
                }
            
            if inv.nisa_type == NisaType.GROWTH:
                investment_by_symbol[inv.symbol]["growth"] += inv.amount
            elif inv.nisa_type == NisaType.TSUMITATE:
                investment_by_symbol[inv.symbol]["tsumitate"] += inv.amount
            
            investment_by_symbol[inv.symbol]["total"] += inv.amount
        
        report = {
            "year": year,
            "status": {
                "growth_used": float(status.growth_used),
                "growth_remaining": float(status.growth_remaining),
                "tsumitate_used": float(status.tsumitate_used),
                "tsumitate_remaining": float(status.tsumitate_remaining),
                "total_used": float(status.total_used),
                "usage_rate": float(status.total_used / (status.growth_remaining + status.tsumitate_remaining + status.total_used) * 100) if (status.growth_remaining + status.tsumitate_remaining + status.total_used) > 0 else 0
            },
            "tax_benefits": {
                "investment_amount": float(tax_savings["nisa_investment"]),
                "estimated_tax_savings": float(tax_savings["tax_savings"]),
                "effective_return": float(tax_savings["effective_return_rate"])
            },
            "investments": {
                symbol: {
                    "growth": float(data["growth"]),
                    "tsumitate": float(data["tsumitate"]),
                    "total": float(data["total"])
                }
                for symbol, data in investment_by_symbol.items()
            },
            "recommendations": self._generate_recommendations(status)
        }
        
        return report
    
    def _generate_recommendations(self, status: NisaStatus) -> List[str]:
        """NISA活用の推奨事項生成"""
        recommendations = []
        
        total_limit = status.growth_remaining + status.tsumitate_remaining
        usage_rate = status.total_used / (status.total_used + total_limit) if total_limit > 0 else 0
        
        if usage_rate < 0.5:
            recommendations.append("NISA枠の活用率が50%未満です。年内の追加投資を検討してください。")
        
        if status.tsumitate_remaining > status.growth_remaining:
            recommendations.append("つみたて投資枠に余裕があります。長期積立投資の活用を検討してください。")
        
        if status.growth_remaining > 1000000:  # 100万円以上
            recommendations.append("成長投資枠に十分な余裕があります。個別株投資やアクティブファンドへの投資を検討してください。")
        
        if len(recommendations) == 0:
            recommendations.append("NISA枠を効率的に活用されています。")
        
        return recommendations