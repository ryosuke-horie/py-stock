"""
税務計算機能

投資に関わる税金計算を行う機能を提供する。
- 譲渡益税の計算
- 損益通算
- 税率の適用
"""

from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from datetime import datetime, date
from loguru import logger

from ..config.settings import settings_manager


@dataclass
class TradeRecord:
    """取引記録"""
    symbol: str
    date: date
    action: str  # 'buy' or 'sell'
    quantity: int
    price: Decimal
    fee: Decimal
    account_type: str = "taxable"  # 'taxable', 'nisa', 'tsumitate_nisa'


@dataclass
class TaxResult:
    """税務計算結果"""
    realized_profit: Decimal  # 実現利益
    unrealized_profit: Decimal  # 含み益
    capital_gains_tax: Decimal  # 譲渡益税
    total_fees: Decimal  # 総手数料
    net_profit: Decimal  # 税引き後利益
    nisa_used_amount: Decimal  # NISA利用額
    nisa_remaining: Decimal  # NISA残り枠


class TaxCalculator:
    """税務計算クラス"""
    
    def __init__(self):
        """初期化"""
        self.config = settings_manager.settings.tax_calculator
        self.trades: List[TradeRecord] = []
        self.holdings: Dict[str, List[TradeRecord]] = {}
        
    def add_trade(self, trade: TradeRecord) -> None:
        """取引を追加"""
        self.trades.append(trade)
        
        # 保有ポジション管理
        if trade.symbol not in self.holdings:
            self.holdings[trade.symbol] = []
        
        if trade.action == "buy":
            self.holdings[trade.symbol].append(trade)
        elif trade.action == "sell":
            self._process_sell_trade(trade)
            
        logger.info(f"取引追加: {trade.symbol} {trade.action} {trade.quantity}株 @{trade.price}")
    
    def _process_sell_trade(self, sell_trade: TradeRecord) -> None:
        """売却取引の処理（FIFO方式）"""
        remaining_quantity = sell_trade.quantity
        symbol = sell_trade.symbol
        
        # 古い順（FIFO）で売却処理
        for i, buy_trade in enumerate(self.holdings[symbol]):
            if remaining_quantity <= 0:
                break
                
            if buy_trade.quantity > 0:
                sell_quantity = min(remaining_quantity, buy_trade.quantity)
                buy_trade.quantity -= sell_quantity
                remaining_quantity -= sell_quantity
                
                # 売却分の損益計算
                profit = (sell_trade.price - buy_trade.price) * sell_quantity
                logger.debug(f"部分売却: {sell_quantity}株, 損益: {profit}")
        
        # 数量が0になった取引記録を削除
        self.holdings[symbol] = [trade for trade in self.holdings[symbol] if trade.quantity > 0]
    
    def calculate_realized_profit(self, year: Optional[int] = None) -> Decimal:
        """実現利益の計算"""
        realized_profit = Decimal('0')
        
        for trade in self.trades:
            if year and trade.date.year != year:
                continue
                
            if trade.action == "sell":
                # 売却時の利益計算（詳細な計算は_process_sell_tradeで実施済み）
                # ここでは簡易的に計算
                buy_trades = [t for t in self.trades 
                             if t.symbol == trade.symbol and t.action == "buy" and t.date < trade.date]
                
                if buy_trades:
                    # 平均取得単価で計算
                    total_cost = sum(t.price * t.quantity for t in buy_trades)
                    total_quantity = sum(t.quantity for t in buy_trades)
                    avg_price = total_cost / total_quantity if total_quantity > 0 else Decimal('0')
                    
                    profit = (trade.price - avg_price) * trade.quantity
                    realized_profit += profit
        
        return self._round_decimal(realized_profit)
    
    def calculate_unrealized_profit(self, current_prices: Dict[str, Decimal]) -> Decimal:
        """含み益の計算"""
        unrealized_profit = Decimal('0')
        
        for symbol, trades in self.holdings.items():
            if symbol not in current_prices:
                continue
                
            current_price = current_prices[symbol]
            total_quantity = sum(trade.quantity for trade in trades)
            
            if total_quantity > 0:
                # 平均取得単価計算
                total_cost = sum(trade.price * trade.quantity for trade in trades)
                avg_price = total_cost / total_quantity
                
                # 含み益計算
                profit = (current_price - avg_price) * total_quantity
                unrealized_profit += profit
        
        return self._round_decimal(unrealized_profit)
    
    def calculate_capital_gains_tax(self, realized_profit: Decimal) -> Decimal:
        """譲渡益税の計算"""
        if realized_profit <= 0:
            return Decimal('0')
        
        tax_rate = Decimal(str(self.config.capital_gains_tax_rate))
        tax_amount = realized_profit * tax_rate
        
        return self._round_decimal(tax_amount)
    
    def calculate_total_fees(self, year: Optional[int] = None) -> Decimal:
        """総手数料の計算"""
        total_fees = Decimal('0')
        
        for trade in self.trades:
            if year and trade.date.year != year:
                continue
            total_fees += trade.fee
        
        return self._round_decimal(total_fees)
    
    def calculate_nisa_usage(self, year: Optional[int] = None) -> Tuple[Decimal, Decimal]:
        """NISA利用状況の計算"""
        nisa_used = Decimal('0')
        
        for trade in self.trades:
            if year and trade.date.year != year:
                continue
                
            if trade.account_type in ['nisa', 'tsumitate_nisa'] and trade.action == "buy":
                nisa_used += trade.price * trade.quantity
        
        nisa_limit = Decimal(str(self.config.nisa_annual_limit))
        nisa_remaining = max(Decimal('0'), nisa_limit - nisa_used)
        
        return self._round_decimal(nisa_used), self._round_decimal(nisa_remaining)
    
    def get_tax_summary(self, current_prices: Dict[str, Decimal], year: Optional[int] = None) -> TaxResult:
        """税務サマリーの取得"""
        realized_profit = self.calculate_realized_profit(year)
        unrealized_profit = self.calculate_unrealized_profit(current_prices)
        capital_gains_tax = self.calculate_capital_gains_tax(realized_profit)
        total_fees = self.calculate_total_fees(year)
        nisa_used, nisa_remaining = self.calculate_nisa_usage(year)
        
        net_profit = realized_profit - capital_gains_tax - total_fees
        
        return TaxResult(
            realized_profit=realized_profit,
            unrealized_profit=unrealized_profit,
            capital_gains_tax=capital_gains_tax,
            total_fees=total_fees,
            net_profit=net_profit,
            nisa_used_amount=nisa_used,
            nisa_remaining=nisa_remaining
        )
    
    def simulate_tax_optimization(self, 
                                 potential_sales: List[Tuple[str, int, Decimal]], 
                                 current_prices: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """税務最適化シミュレーション"""
        optimization_results = {}
        
        for symbol, quantity, sell_price in potential_sales:
            if symbol not in self.holdings:
                continue
            
            # 現在の保有状況から利益/損失を計算
            holdings = self.holdings[symbol]
            if not holdings:
                continue
            
            # 平均取得単価計算
            total_cost = sum(trade.price * trade.quantity for trade in holdings)
            total_quantity = sum(trade.quantity for trade in holdings)
            
            if total_quantity < quantity:
                continue
            
            avg_price = total_cost / total_quantity
            estimated_profit = (sell_price - avg_price) * quantity
            estimated_tax = self.calculate_capital_gains_tax(estimated_profit)
            net_profit = estimated_profit - estimated_tax
            
            optimization_results[f"{symbol}_profit"] = estimated_profit
            optimization_results[f"{symbol}_tax"] = estimated_tax
            optimization_results[f"{symbol}_net"] = net_profit
        
        return optimization_results
    
    def _round_decimal(self, value: Decimal) -> Decimal:
        """小数点丸め処理"""
        places = self.config.decimal_places
        return value.quantize(Decimal(f'0.{"0" * places}'), rounding=ROUND_HALF_UP)
    
    def export_tax_report(self, year: int) -> Dict[str, Any]:
        """税務レポートの出力"""
        current_prices = {}  # 実際の実装では現在価格を取得
        tax_summary = self.get_tax_summary(current_prices, year)
        
        # 取引履歴（年間）
        year_trades = [trade for trade in self.trades if trade.date.year == year]
        
        report = {
            "year": year,
            "summary": {
                "realized_profit": float(tax_summary.realized_profit),
                "capital_gains_tax": float(tax_summary.capital_gains_tax),
                "total_fees": float(tax_summary.total_fees),
                "net_profit": float(tax_summary.net_profit),
                "nisa_used": float(tax_summary.nisa_used_amount),
                "nisa_remaining": float(tax_summary.nisa_remaining)
            },
            "trade_count": len(year_trades),
            "symbols_traded": list(set(trade.symbol for trade in year_trades))
        }
        
        return report