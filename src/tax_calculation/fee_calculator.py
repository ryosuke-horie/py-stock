"""
手数料計算機能

証券会社別の手数料体系に基づいた取引手数料の計算を行う。
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from ..config.settings import settings_manager


class MarketType(Enum):
    """市場区分"""
    TOKYO_STOCK = "tokyo"  # 東京証券取引所
    US_STOCK = "us"  # 米国株
    FOREIGN_STOCK = "foreign"  # その他外国株


@dataclass
class FeeStructure:
    """手数料体系"""
    broker_name: str
    market_type: MarketType
    fee_type: str  # 'fixed', 'percentage', 'tiered'
    
    # 固定手数料
    fixed_fee: Optional[Decimal] = None
    
    # 比例手数料
    percentage_rate: Optional[Decimal] = None
    min_fee: Optional[Decimal] = None
    max_fee: Optional[Decimal] = None
    
    # 段階手数料（段階別設定）
    tiers: Optional[Dict[int, Decimal]] = None  # {上限金額: 手数料}


class FeeCalculator:
    """手数料計算クラス"""
    
    def __init__(self):
        """初期化"""
        self.config = settings_manager.settings.tax_calculator
        self.fee_structures = self._load_fee_structures()
    
    def _load_fee_structures(self) -> Dict[str, Dict[MarketType, FeeStructure]]:
        """手数料体系の読み込み"""
        fee_structures = {
            "sbi": {
                MarketType.TOKYO_STOCK: FeeStructure(
                    broker_name="SBI証券",
                    market_type=MarketType.TOKYO_STOCK,
                    fee_type="tiered",
                    tiers={
                        50000: Decimal('55'),      # 5万円以下: 55円
                        100000: Decimal('99'),     # 10万円以下: 99円
                        200000: Decimal('115'),    # 20万円以下: 115円
                        500000: Decimal('275'),    # 50万円以下: 275円
                        1000000: Decimal('535'),   # 100万円以下: 535円
                        3000000: Decimal('640'),   # 300万円以下: 640円
                        float('inf'): Decimal('1013')  # 300万円超: 1013円
                    }
                ),
                MarketType.US_STOCK: FeeStructure(
                    broker_name="SBI証券",
                    market_type=MarketType.US_STOCK,
                    fee_type="percentage",
                    percentage_rate=Decimal('0.00495'),  # 0.495%
                    min_fee=Decimal('0'),
                    max_fee=Decimal('2200')  # 22米ドル相当（100円/ドル）
                )
            },
            "rakuten": {
                MarketType.TOKYO_STOCK: FeeStructure(
                    broker_name="楽天証券",
                    market_type=MarketType.TOKYO_STOCK,
                    fee_type="tiered",
                    tiers={
                        50000: Decimal('55'),      # 5万円以下: 55円
                        100000: Decimal('99'),     # 10万円以下: 99円
                        200000: Decimal('115'),    # 20万円以下: 115円
                        500000: Decimal('275'),    # 50万円以下: 275円
                        1000000: Decimal('535'),   # 100万円以下: 535円
                        3000000: Decimal('640'),   # 300万円以下: 640円
                        float('inf'): Decimal('1013')  # 300万円超: 1013円
                    }
                ),
                MarketType.US_STOCK: FeeStructure(
                    broker_name="楽天証券",
                    market_type=MarketType.US_STOCK,
                    fee_type="percentage",
                    percentage_rate=Decimal('0.00495'),  # 0.495%
                    min_fee=Decimal('0'),
                    max_fee=Decimal('2200')  # 22米ドル相当（100円/ドル）
                )
            },
            "matsui": {
                MarketType.TOKYO_STOCK: FeeStructure(
                    broker_name="松井証券",
                    market_type=MarketType.TOKYO_STOCK,
                    fee_type="tiered",
                    tiers={
                        500000: Decimal('0'),      # 50万円以下: 0円
                        1000000: Decimal('1100'),  # 100万円以下: 1100円
                        2000000: Decimal('2200'),  # 200万円以下: 2200円
                        float('inf'): Decimal('1100')  # 以降100万円毎に1100円追加
                    }
                )
            }
        }
        
        return fee_structures
    
    def calculate_fee(self, 
                     amount: Decimal, 
                     broker: str, 
                     market_type: MarketType = MarketType.TOKYO_STOCK) -> Decimal:
        """手数料計算"""
        
        if broker not in self.fee_structures:
            logger.warning(f"未対応の証券会社: {broker}")
            return Decimal('0')
        
        broker_fees = self.fee_structures[broker]
        
        if market_type not in broker_fees:
            logger.warning(f"未対応の市場タイプ: {market_type}")
            return Decimal('0')
        
        fee_structure = broker_fees[market_type]
        
        if fee_structure.fee_type == "fixed":
            return fee_structure.fixed_fee or Decimal('0')
        
        elif fee_structure.fee_type == "percentage":
            fee = amount * (fee_structure.percentage_rate or Decimal('0'))
            
            # 最小・最大手数料の適用
            if fee_structure.min_fee:
                fee = max(fee, fee_structure.min_fee)
            if fee_structure.max_fee:
                fee = min(fee, fee_structure.max_fee)
            
            return self._round_fee(fee)
        
        elif fee_structure.fee_type == "tiered":
            return self._calculate_tiered_fee(amount, fee_structure.tiers or {})
        
        return Decimal('0')
    
    def _calculate_tiered_fee(self, amount: Decimal, tiers: Dict[int, Decimal]) -> Decimal:
        """段階手数料の計算"""
        for threshold, fee in sorted(tiers.items()):
            if amount <= threshold:
                return fee
        
        # 最上位の手数料を返す
        return max(tiers.values())
    
    def calculate_round_trip_fee(self, 
                                amount: Decimal, 
                                broker: str, 
                                market_type: MarketType = MarketType.TOKYO_STOCK) -> Decimal:
        """往復手数料（売買両方）の計算"""
        single_fee = self.calculate_fee(amount, broker, market_type)
        return single_fee * 2
    
    def compare_brokers(self, 
                       amount: Decimal, 
                       market_type: MarketType = MarketType.TOKYO_STOCK) -> Dict[str, Decimal]:
        """証券会社別手数料比較"""
        comparison = {}
        
        for broker in self.fee_structures.keys():
            fee = self.calculate_fee(amount, broker, market_type)
            comparison[broker] = fee
        
        return comparison
    
    def get_cheapest_broker(self, 
                           amount: Decimal, 
                           market_type: MarketType = MarketType.TOKYO_STOCK) -> tuple[str, Decimal]:
        """最安手数料の証券会社を取得"""
        comparison = self.compare_brokers(amount, market_type)
        
        if not comparison:
            return "", Decimal('0')
        
        cheapest_broker = min(comparison.items(), key=lambda x: x[1])
        return cheapest_broker[0], cheapest_broker[1]
    
    def calculate_fee_impact(self, 
                           amount: Decimal, 
                           broker: str, 
                           market_type: MarketType = MarketType.TOKYO_STOCK) -> Dict[str, Decimal]:
        """手数料が投資に与える影響を分析"""
        fee = self.calculate_fee(amount, broker, market_type)
        round_trip_fee = self.calculate_round_trip_fee(amount, broker, market_type)
        
        # 手数料率
        fee_rate = (fee / amount * 100) if amount > 0 else Decimal('0')
        round_trip_rate = (round_trip_fee / amount * 100) if amount > 0 else Decimal('0')
        
        # 損益分岐点（手数料を回収するのに必要な値上がり率）
        breakeven_rate = round_trip_rate
        
        return {
            "single_fee": fee,
            "round_trip_fee": round_trip_fee,
            "fee_rate": self._round_fee(fee_rate),
            "round_trip_rate": self._round_fee(round_trip_rate),
            "breakeven_rate": self._round_fee(breakeven_rate)
        }
    
    def suggest_optimal_amount(self, 
                              broker: str, 
                              market_type: MarketType = MarketType.TOKYO_STOCK) -> List[Dict[str, Any]]:
        """手数料効率の良い投資金額の提案"""
        suggestions = []
        
        if broker not in self.fee_structures:
            return suggestions
        
        broker_fees = self.fee_structures[broker]
        
        if market_type not in broker_fees:
            return suggestions
        
        fee_structure = broker_fees[market_type]
        
        if fee_structure.fee_type == "tiered" and fee_structure.tiers:
            # 段階手数料の境界値で効率的な金額を提案
            for threshold, fee in sorted(fee_structure.tiers.items()):
                if threshold == float('inf'):
                    continue
                
                amount = Decimal(str(threshold))
                fee_rate = (fee / amount * 100) if amount > 0 else Decimal('0')
                
                suggestions.append({
                    "amount": amount,
                    "fee": fee,
                    "fee_rate": self._round_fee(fee_rate),
                    "description": f"{threshold:,}円：手数料{fee}円（{fee_rate:.3f}%）"
                })
        
        return suggestions
    
    def _round_fee(self, fee: Decimal) -> Decimal:
        """手数料の丸め処理"""
        places = self.config.decimal_places
        return fee.quantize(Decimal(f'0.{"0" * places}'), rounding=ROUND_HALF_UP)
    
    def get_fee_structure_info(self, broker: str) -> Dict[str, Any]:
        """証券会社の手数料体系情報を取得"""
        if broker not in self.fee_structures:
            return {}
        
        broker_info = {}
        for market_type, fee_structure in self.fee_structures[broker].items():
            market_name = market_type.value
            broker_info[market_name] = {
                "broker_name": fee_structure.broker_name,
                "fee_type": fee_structure.fee_type,
                "fixed_fee": float(fee_structure.fixed_fee) if fee_structure.fixed_fee else None,
                "percentage_rate": float(fee_structure.percentage_rate) if fee_structure.percentage_rate else None,
                "min_fee": float(fee_structure.min_fee) if fee_structure.min_fee else None,
                "max_fee": float(fee_structure.max_fee) if fee_structure.max_fee else None,
                "tiers": {k: float(v) for k, v in fee_structure.tiers.items()} if fee_structure.tiers else None
            }
        
        return broker_info