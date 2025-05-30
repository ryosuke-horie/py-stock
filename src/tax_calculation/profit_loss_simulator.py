"""
損益通算シミュレーション機能

投資の損益通算と税務最適化のシミュレーションを行う。
- 損益の相殺計算
- 損失繰越の管理
- 税務最適化の提案
"""

from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from loguru import logger

from ..config.settings import settings_manager


@dataclass
class TradePosition:
    """取引ポジション"""
    symbol: str
    entry_date: date
    entry_price: Decimal
    quantity: int
    current_price: Optional[Decimal] = None
    exit_date: Optional[date] = None
    exit_price: Optional[Decimal] = None
    account_type: str = "taxable"  # 'taxable', 'nisa'
    
    @property
    def is_closed(self) -> bool:
        """ポジション決済済みかどうか"""
        return self.exit_date is not None and self.exit_price is not None
    
    @property
    def realized_pnl(self) -> Optional[Decimal]:
        """実現損益"""
        if not self.is_closed:
            return None
        return (self.exit_price - self.entry_price) * self.quantity
    
    @property
    def unrealized_pnl(self) -> Optional[Decimal]:
        """含み損益"""
        if self.is_closed or self.current_price is None:
            return None
        return (self.current_price - self.entry_price) * self.quantity


@dataclass
class LossCarryforward:
    """損失繰越"""
    year: int
    loss_amount: Decimal
    used_amount: Decimal = field(default=Decimal('0'))
    
    @property
    def remaining_amount(self) -> Decimal:
        """残存繰越損失額"""
        return self.loss_amount - self.used_amount
    
    @property
    def is_fully_used(self) -> bool:
        """繰越損失が完全に使用済みかどうか"""
        return self.remaining_amount <= 0


@dataclass
class TaxOptimizationResult:
    """税務最適化結果"""
    current_realized_profit: Decimal
    current_realized_loss: Decimal
    net_realized_pnl: Decimal
    applicable_tax: Decimal
    loss_carryforward_used: Decimal
    remaining_loss_carryforward: Decimal
    optimization_suggestions: List[str]


class ProfitLossSimulator:
    """損益通算シミュレーターイクラス"""
    
    def __init__(self):
        """初期化"""
        self.config = settings_manager.settings.tax_calculator
        self.positions: List[TradePosition] = []
        self.loss_carryforwards: List[LossCarryforward] = []
    
    def add_position(self, position: TradePosition) -> None:
        """ポジションを追加"""
        self.positions.append(position)
        logger.info(f"ポジション追加: {position.symbol} {position.quantity}株 @{position.entry_price}")
    
    def close_position(self, 
                      symbol: str, 
                      exit_date: date, 
                      exit_price: Decimal, 
                      quantity: Optional[int] = None) -> bool:
        """ポジション決済"""
        # 対象ポジションを検索（FIFO方式）
        target_positions = [p for p in self.positions 
                          if p.symbol == symbol and not p.is_closed]
        
        if not target_positions:
            logger.warning(f"決済対象のポジションが見つかりません: {symbol}")
            return False
        
        remaining_quantity = quantity or sum(p.quantity for p in target_positions)
        
        for position in target_positions:
            if remaining_quantity <= 0:
                break
            
            close_quantity = min(remaining_quantity, position.quantity)
            
            if close_quantity == position.quantity:
                # 全決済
                position.exit_date = exit_date
                position.exit_price = exit_price
            else:
                # 部分決済 - 新しいポジションを作成
                partial_position = TradePosition(
                    symbol=position.symbol,
                    entry_date=position.entry_date,
                    entry_price=position.entry_price,
                    quantity=close_quantity,
                    exit_date=exit_date,
                    exit_price=exit_price,
                    account_type=position.account_type
                )
                self.positions.append(partial_position)
                position.quantity -= close_quantity
            
            remaining_quantity -= close_quantity
            
            logger.info(f"ポジション決済: {symbol} {close_quantity}株 @{exit_price}")
        
        return True
    
    def calculate_realized_pnl(self, year: Optional[int] = None) -> Tuple[Decimal, Decimal]:
        """実現損益の計算"""
        realized_profit = Decimal('0')
        realized_loss = Decimal('0')
        
        for position in self.positions:
            if not position.is_closed:
                continue
            
            if year and position.exit_date.year != year:
                continue
            
            if position.account_type != "taxable":
                continue  # NISA等は課税対象外
            
            pnl = position.realized_pnl
            if pnl > 0:
                realized_profit += pnl
            else:
                realized_loss += abs(pnl)
        
        return realized_profit, realized_loss
    
    def calculate_unrealized_pnl(self) -> Tuple[Decimal, Decimal]:
        """含み損益の計算"""
        unrealized_profit = Decimal('0')
        unrealized_loss = Decimal('0')
        
        for position in self.positions:
            if position.is_closed or position.account_type != "taxable":
                continue
            
            pnl = position.unrealized_pnl
            if pnl is None:
                continue
            
            if pnl > 0:
                unrealized_profit += pnl
            else:
                unrealized_loss += abs(pnl)
        
        return unrealized_profit, unrealized_loss
    
    def add_loss_carryforward(self, year: int, loss_amount: Decimal) -> None:
        """損失繰越を追加"""
        carryforward = LossCarryforward(year=year, loss_amount=loss_amount)
        self.loss_carryforwards.append(carryforward)
        logger.info(f"損失繰越追加: {year}年 {loss_amount}円")
    
    def apply_loss_carryforward(self, current_year: int, profit: Decimal) -> Tuple[Decimal, Decimal]:
        """損失繰越の適用"""
        remaining_profit = profit
        total_used = Decimal('0')
        
        # 古い順に損失繰越を適用
        for carryforward in sorted(self.loss_carryforwards, key=lambda x: x.year):
            if carryforward.year < current_year - self.config.loss_carryforward_years:
                continue  # 繰越期限切れ
            
            if carryforward.is_fully_used or remaining_profit <= 0:
                continue
            
            # 適用可能な金額を計算
            applicable_amount = min(remaining_profit, carryforward.remaining_amount)
            carryforward.used_amount += applicable_amount
            remaining_profit -= applicable_amount
            total_used += applicable_amount
            
            logger.debug(f"損失繰越適用: {carryforward.year}年分 {applicable_amount}円")
        
        return remaining_profit, total_used
    
    def simulate_tax_optimization(self, current_year: int, target_profit: Optional[Decimal] = None) -> TaxOptimizationResult:
        """税務最適化シミュレーション"""
        realized_profit, realized_loss = self.calculate_realized_pnl(current_year)
        unrealized_profit, unrealized_loss = self.calculate_unrealized_pnl()
        
        # 当年の純損益
        net_realized_pnl = realized_profit - realized_loss
        
        # 損失繰越の適用
        taxable_profit = net_realized_pnl
        loss_carryforward_used = Decimal('0')
        
        if taxable_profit > 0:
            taxable_profit, loss_carryforward_used = self.apply_loss_carryforward(current_year, taxable_profit)
        
        # 税額計算
        tax_rate = Decimal(str(self.config.capital_gains_tax_rate))
        applicable_tax = max(Decimal('0'), taxable_profit * tax_rate)
        
        # 最適化提案の生成
        suggestions = self._generate_optimization_suggestions(
            realized_profit, realized_loss, unrealized_profit, unrealized_loss,
            net_realized_pnl, taxable_profit, current_year
        )
        
        # 残存損失繰越
        remaining_carryforward = sum(
            cf.remaining_amount for cf in self.loss_carryforwards
            if cf.year >= current_year - self.config.loss_carryforward_years and not cf.is_fully_used
        )
        
        return TaxOptimizationResult(
            current_realized_profit=realized_profit,
            current_realized_loss=realized_loss,
            net_realized_pnl=net_realized_pnl,
            applicable_tax=applicable_tax,
            loss_carryforward_used=loss_carryforward_used,
            remaining_loss_carryforward=remaining_carryforward,
            optimization_suggestions=suggestions
        )
    
    def _generate_optimization_suggestions(self, 
                                         realized_profit: Decimal,
                                         realized_loss: Decimal,
                                         unrealized_profit: Decimal,
                                         unrealized_loss: Decimal,
                                         net_realized_pnl: Decimal,
                                         taxable_profit: Decimal,
                                         current_year: int) -> List[str]:
        """最適化提案の生成"""
        suggestions = []
        
        # 含み損の実現による税務メリット
        if unrealized_loss > 0 and taxable_profit > 0:
            optimal_loss_realization = min(unrealized_loss, taxable_profit)
            tax_savings = optimal_loss_realization * Decimal(str(self.config.capital_gains_tax_rate))
            suggestions.append(
                f"含み損 {optimal_loss_realization:,.0f}円の実現により {tax_savings:,.0f}円の節税効果が期待できます"
            )
        
        # 利益確定のタイミング提案
        if unrealized_profit > 100000:  # 10万円以上の含み益
            if taxable_profit <= 0:
                suggestions.append("損失が発生している年内に含み益を実現することで税務負担を軽減できます")
            else:
                suggestions.append("含み益の実現タイミングを翌年に延期することで税務負担を分散できます")
        
        # 損失繰越の活用提案
        remaining_carryforward = sum(
            cf.remaining_amount for cf in self.loss_carryforwards
            if cf.year >= current_year - self.config.loss_carryforward_years and not cf.is_fully_used
        )
        
        if remaining_carryforward > 0 and unrealized_profit > 0:
            optimal_profit_realization = min(unrealized_profit, remaining_carryforward)
            suggestions.append(
                f"損失繰越 {remaining_carryforward:,.0f}円があります。含み益 {optimal_profit_realization:,.0f}円の実現により税負担なしで利益確定できます"
            )
        
        # 年末の税務戦略
        if datetime.now().month >= 11:  # 11月以降
            if net_realized_pnl > 0:
                suggestions.append("年末までに含み損の実現による損益通算を検討してください")
            elif net_realized_pnl < 0:
                suggestions.append("年内の含み益実現により損失の一部を相殺できます")
        
        # NISA活用の提案
        nisa_eligible_positions = [p for p in self.positions if p.account_type == "taxable" and not p.is_closed]
        if nisa_eligible_positions:
            suggestions.append("今後の投資はNISA口座の活用を検討し、税務負担を軽減してください")
        
        return suggestions
    
    def generate_year_end_report(self, year: int) -> Dict[str, Any]:
        """年末税務レポート生成"""
        optimization_result = self.simulate_tax_optimization(year)
        
        # ポジション別分析
        positions_analysis = {}
        for position in self.positions:
            if position.symbol not in positions_analysis:
                positions_analysis[position.symbol] = {
                    "total_quantity": 0,
                    "avg_entry_price": Decimal('0'),
                    "realized_pnl": Decimal('0'),
                    "unrealized_pnl": Decimal('0'),
                    "total_pnl": Decimal('0')
                }
            
            analysis = positions_analysis[position.symbol]
            
            if position.is_closed:
                analysis["realized_pnl"] += position.realized_pnl or Decimal('0')
            else:
                analysis["total_quantity"] += position.quantity
                analysis["unrealized_pnl"] += position.unrealized_pnl or Decimal('0')
            
            analysis["total_pnl"] = analysis["realized_pnl"] + analysis["unrealized_pnl"]
        
        # 損失繰越の状況
        carryforward_status = []
        for cf in self.loss_carryforwards:
            if cf.year >= year - self.config.loss_carryforward_years:
                carryforward_status.append({
                    "year": cf.year,
                    "original_amount": float(cf.loss_amount),
                    "used_amount": float(cf.used_amount),
                    "remaining_amount": float(cf.remaining_amount)
                })
        
        report = {
            "year": year,
            "profit_loss_summary": {
                "realized_profit": float(optimization_result.current_realized_profit),
                "realized_loss": float(optimization_result.current_realized_loss),
                "net_realized_pnl": float(optimization_result.net_realized_pnl),
                "applicable_tax": float(optimization_result.applicable_tax),
                "tax_rate": float(self.config.capital_gains_tax_rate) * 100
            },
            "loss_carryforward": {
                "used_this_year": float(optimization_result.loss_carryforward_used),
                "remaining_total": float(optimization_result.remaining_loss_carryforward),
                "details": carryforward_status
            },
            "positions_analysis": {
                symbol: {
                    "realized_pnl": float(data["realized_pnl"]),
                    "unrealized_pnl": float(data["unrealized_pnl"]),
                    "total_pnl": float(data["total_pnl"]),
                    "holding_quantity": data["total_quantity"]
                }
                for symbol, data in positions_analysis.items()
            },
            "optimization_suggestions": optimization_result.optimization_suggestions
        }
        
        return report
    
    def simulate_what_if_scenarios(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """What-ifシナリオシミュレーション"""
        results = {}
        
        for i, scenario in enumerate(scenarios):
            scenario_name = scenario.get("name", f"シナリオ{i+1}")
            
            # 現在の状態をバックアップ
            original_positions = [p for p in self.positions]
            
            # シナリオ実行
            try:
                if "close_positions" in scenario:
                    for close_info in scenario["close_positions"]:
                        self.close_position(
                            symbol=close_info["symbol"],
                            exit_date=close_info["exit_date"],
                            exit_price=Decimal(str(close_info["exit_price"])),
                            quantity=close_info.get("quantity")
                        )
                
                # 結果計算
                optimization_result = self.simulate_tax_optimization(scenario.get("year", datetime.now().year))
                
                results[scenario_name] = {
                    "net_pnl": float(optimization_result.net_realized_pnl),
                    "tax": float(optimization_result.applicable_tax),
                    "net_after_tax": float(optimization_result.net_realized_pnl - optimization_result.applicable_tax),
                    "suggestions": optimization_result.optimization_suggestions
                }
                
            finally:
                # 状態を復元
                self.positions = original_positions
        
        return results