"""
リスク管理システム
動的ストップロス、テイクプロフィット、ポジションサイジング、時間ベース決済を提供
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging

from ..technical_analysis.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class StopLossType(Enum):
    """ストップロスタイプ"""
    FIXED_PERCENTAGE = "fixed_percentage"
    ATR_BASED = "atr_based"
    TRAILING = "trailing"
    SUPPORT_RESISTANCE = "support_resistance"


class PositionSide(Enum):
    """ポジションサイド"""
    LONG = "long"
    SHORT = "short"


@dataclass
class RiskParameters:
    """リスク管理パラメータ"""
    max_position_size_pct: float = 2.0  # 最大ポジションサイズ（総資本の%）
    max_daily_loss_pct: float = 5.0     # 1日最大損失（総資本の%）
    stop_loss_pct: float = 2.0          # 固定ストップロス（%）
    atr_multiplier: float = 2.0         # ATRベースストップロス倍率
    trailing_stop_pct: float = 1.5      # トレイリングストップ（%）
    risk_reward_ratios: List[float] = None  # リスクリワード比率
    max_positions: int = 5              # 最大同時ポジション数
    force_close_time: time = time(15, 0)  # 強制決済時刻（15:00）
    
    def __post_init__(self):
        if self.risk_reward_ratios is None:
            self.risk_reward_ratios = [1.0, 1.5, 2.0, 3.0]


@dataclass
class Position:
    """ポジション情報"""
    symbol: str
    side: PositionSide
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: float
    take_profit: List[float]
    trailing_stop: Optional[float] = None
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    
    def update_price(self, price: float):
        """現在価格とPnLを更新"""
        self.current_price = price
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.entry_price - price) * self.quantity


class RiskManager:
    """リスク管理システム"""
    
    def __init__(self, risk_params: RiskParameters = None, initial_capital: float = 1000000):
        """
        初期化
        
        Args:
            risk_params: リスク管理パラメータ
            initial_capital: 初期資本（円）
        """
        self.risk_params = risk_params or RiskParameters()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.daily_pnl = 0.0
        self.trade_history = []
        self.technical_indicators = None  # 必要時に初期化
        
        logger.info(f"RiskManager initialized with capital: ¥{initial_capital:,.0f}")
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                              stop_loss: float, side: PositionSide) -> int:
        """
        ポジションサイズを計算
        
        Args:
            symbol: 銘柄コード
            entry_price: エントリー価格
            stop_loss: ストップロス価格
            side: ポジションサイド
            
        Returns:
            推奨ポジションサイズ（株数）
        """
        try:
            # リスク金額を計算（総資本の最大ポジションサイズ%）
            max_risk_amount = self.current_capital * (self.risk_params.max_position_size_pct / 100)
            
            # 1株あたりのリスクを計算
            if side == PositionSide.LONG:
                risk_per_share = entry_price - stop_loss
            else:
                risk_per_share = stop_loss - entry_price
            
            if risk_per_share <= 0:
                logger.warning(f"Invalid risk calculation for {symbol}: {risk_per_share}")
                return 0
            
            # ポジションサイズを計算
            position_size = int(max_risk_amount / risk_per_share)
            
            # 最大ポジション数制限
            if len(self.positions) >= self.risk_params.max_positions:
                logger.warning(f"Maximum positions ({self.risk_params.max_positions}) reached")
                return 0
            
            # 最小単位調整（100株単位）
            position_size = (position_size // 100) * 100
            
            logger.info(f"Position size for {symbol}: {position_size} shares (risk: ¥{max_risk_amount:,.0f})")
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            return 0
    
    def calculate_stop_loss(self, data: pd.DataFrame, entry_price: float,
                          side: PositionSide, stop_type: StopLossType = StopLossType.ATR_BASED) -> float:
        """
        ストップロス価格を計算
        
        Args:
            data: 株価データ
            entry_price: エントリー価格
            side: ポジションサイド
            stop_type: ストップロスタイプ
            
        Returns:
            ストップロス価格
        """
        try:
            if stop_type == StopLossType.FIXED_PERCENTAGE:
                if side == PositionSide.LONG:
                    return entry_price * (1 - self.risk_params.stop_loss_pct / 100)
                else:
                    return entry_price * (1 + self.risk_params.stop_loss_pct / 100)
            
            elif stop_type == StopLossType.ATR_BASED:
                try:
                    # TechnicalIndicatorsを動的に初期化
                    if self.technical_indicators is None:
                        self.technical_indicators = TechnicalIndicators(data)
                    
                    atr = self.technical_indicators.atr()
                    if atr.empty:
                        return self.calculate_stop_loss(data, entry_price, side, StopLossType.FIXED_PERCENTAGE)
                    
                    atr_value = atr.iloc[-1]
                    if side == PositionSide.LONG:
                        return entry_price - (atr_value * self.risk_params.atr_multiplier)
                    else:
                        return entry_price + (atr_value * self.risk_params.atr_multiplier)
                except Exception as e:
                    logger.warning(f"Error calculating ATR-based stop loss: {e}")
                    return self.calculate_stop_loss(data, entry_price, side, StopLossType.FIXED_PERCENTAGE)
            
            elif stop_type == StopLossType.SUPPORT_RESISTANCE:
                # サポート・レジスタンスレベルベース（簡易実装）
                if len(data) < 20:
                    return self.calculate_stop_loss(data, entry_price, side, StopLossType.ATR_BASED)
                
                if side == PositionSide.LONG:
                    # 直近のサポートレベル
                    support_level = data['low'].rolling(20).min().iloc[-1]
                    return max(support_level, entry_price * (1 - self.risk_params.stop_loss_pct / 100))
                else:
                    # 直近のレジスタンスレベル
                    resistance_level = data['high'].rolling(20).max().iloc[-1]
                    return min(resistance_level, entry_price * (1 + self.risk_params.stop_loss_pct / 100))
            
            else:
                return self.calculate_stop_loss(data, entry_price, side, StopLossType.FIXED_PERCENTAGE)
                
        except Exception as e:
            logger.error(f"Error calculating stop loss: {e}")
            return self.calculate_stop_loss(data, entry_price, side, StopLossType.FIXED_PERCENTAGE)
    
    def calculate_take_profit_levels(self, entry_price: float, stop_loss: float,
                                   side: PositionSide) -> List[float]:
        """
        テイクプロフィットレベルを計算
        
        Args:
            entry_price: エントリー価格
            stop_loss: ストップロス価格
            side: ポジションサイド
            
        Returns:
            テイクプロフィットレベルのリスト
        """
        try:
            risk_amount = abs(entry_price - stop_loss)
            take_profit_levels = []
            
            for ratio in self.risk_params.risk_reward_ratios:
                if side == PositionSide.LONG:
                    tp_level = entry_price + (risk_amount * ratio)
                else:
                    tp_level = entry_price - (risk_amount * ratio)
                take_profit_levels.append(tp_level)
            
            return take_profit_levels
            
        except Exception as e:
            logger.error(f"Error calculating take profit levels: {e}")
            return []
    
    def update_trailing_stop(self, symbol: str, current_price: float):
        """
        トレイリングストップを更新
        
        Args:
            symbol: 銘柄コード
            current_price: 現在価格
        """
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        trailing_pct = self.risk_params.trailing_stop_pct / 100
        
        try:
            if position.side == PositionSide.LONG:
                # ロングポジション：価格上昇時にストップロスを引き上げ
                new_trailing_stop = current_price * (1 - trailing_pct)
                if position.trailing_stop is None or new_trailing_stop > position.trailing_stop:
                    position.trailing_stop = new_trailing_stop
                    logger.info(f"Updated trailing stop for {symbol}: ¥{new_trailing_stop:.2f}")
            else:
                # ショートポジション：価格下落時にストップロスを引き下げ
                new_trailing_stop = current_price * (1 + trailing_pct)
                if position.trailing_stop is None or new_trailing_stop < position.trailing_stop:
                    position.trailing_stop = new_trailing_stop
                    logger.info(f"Updated trailing stop for {symbol}: ¥{new_trailing_stop:.2f}")
                    
        except Exception as e:
            logger.error(f"Error updating trailing stop for {symbol}: {e}")
    
    def check_exit_conditions(self, symbol: str, current_price: float,
                            current_time: datetime = None) -> Dict[str, Union[bool, str]]:
        """
        決済条件をチェック
        
        Args:
            symbol: 銘柄コード
            current_price: 現在価格
            current_time: 現在時刻
            
        Returns:
            決済判定結果
        """
        if symbol not in self.positions:
            return {"should_exit": False, "reason": "No position"}
        
        position = self.positions[symbol]
        current_time = current_time or datetime.now()
        
        try:
            # ストップロス判定
            if position.side == PositionSide.LONG:
                if current_price <= position.stop_loss:
                    return {"should_exit": True, "reason": "Stop loss hit", "exit_price": position.stop_loss}
                if position.trailing_stop and current_price <= position.trailing_stop:
                    return {"should_exit": True, "reason": "Trailing stop hit", "exit_price": position.trailing_stop}
            else:
                if current_price >= position.stop_loss:
                    return {"should_exit": True, "reason": "Stop loss hit", "exit_price": position.stop_loss}
                if position.trailing_stop and current_price >= position.trailing_stop:
                    return {"should_exit": True, "reason": "Trailing stop hit", "exit_price": position.trailing_stop}
            
            # テイクプロフィット判定
            for i, tp_level in enumerate(position.take_profit):
                if position.side == PositionSide.LONG and current_price >= tp_level:
                    return {"should_exit": True, "reason": f"Take profit {i+1} hit", "exit_price": tp_level}
                elif position.side == PositionSide.SHORT and current_price <= tp_level:
                    return {"should_exit": True, "reason": f"Take profit {i+1} hit", "exit_price": tp_level}
            
            # 時間ベース強制決済判定
            if current_time.time() >= self.risk_params.force_close_time:
                return {"should_exit": True, "reason": "Force close time", "exit_price": current_price}
            
            # 日次最大損失判定
            if self.daily_pnl <= -self.current_capital * (self.risk_params.max_daily_loss_pct / 100):
                return {"should_exit": True, "reason": "Daily loss limit", "exit_price": current_price}
            
            return {"should_exit": False, "reason": "No exit condition met"}
            
        except Exception as e:
            logger.error(f"Error checking exit conditions for {symbol}: {e}")
            return {"should_exit": False, "reason": f"Error: {e}"}
    
    def open_position(self, symbol: str, side: PositionSide, entry_price: float,
                     data: pd.DataFrame, quantity: int = None) -> bool:
        """
        ポジションを開く
        
        Args:
            symbol: 銘柄コード
            side: ポジションサイド
            entry_price: エントリー価格
            data: 株価データ
            quantity: ポジションサイズ（指定なしの場合は自動計算）
            
        Returns:
            ポジション開設成功可否
        """
        try:
            # ストップロス計算
            stop_loss = self.calculate_stop_loss(data, entry_price, side)
            
            # ポジションサイズ計算
            if quantity is None:
                quantity = self.calculate_position_size(symbol, entry_price, stop_loss, side)
            
            if quantity == 0:
                logger.warning(f"Cannot open position for {symbol}: quantity is 0")
                return False
            
            # テイクプロフィットレベル計算
            take_profit_levels = self.calculate_take_profit_levels(entry_price, stop_loss, side)
            
            # ポジション作成
            position = Position(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                quantity=quantity,
                entry_time=datetime.now(),
                stop_loss=stop_loss,
                take_profit=take_profit_levels
            )
            
            self.positions[symbol] = position
            
            # 取引記録
            trade_record = {
                "symbol": symbol,
                "action": "open",
                "side": side.value,
                "price": entry_price,
                "quantity": quantity,
                "timestamp": datetime.now(),
                "stop_loss": stop_loss,
                "take_profit": take_profit_levels
            }
            self.trade_history.append(trade_record)
            
            logger.info(f"Opened {side.value} position for {symbol}: {quantity} shares at ¥{entry_price:.2f}")
            logger.info(f"Stop loss: ¥{stop_loss:.2f}, Take profit: {[f'¥{tp:.2f}' for tp in take_profit_levels]}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error opening position for {symbol}: {e}")
            return False
    
    def close_position(self, symbol: str, exit_price: float, reason: str = "Manual close") -> bool:
        """
        ポジションを閉じる
        
        Args:
            symbol: 銘柄コード
            exit_price: 決済価格
            reason: 決済理由
            
        Returns:
            ポジション決済成功可否
        """
        try:
            if symbol not in self.positions:
                logger.warning(f"No position found for {symbol}")
                return False
            
            position = self.positions[symbol]
            
            # PnL計算
            if position.side == PositionSide.LONG:
                pnl = (exit_price - position.entry_price) * position.quantity
            else:
                pnl = (position.entry_price - exit_price) * position.quantity
            
            # 手数料計算（簡易：取引金額の0.1%）
            commission = (position.entry_price + exit_price) * position.quantity * 0.001
            net_pnl = pnl - commission
            
            # 資本とPnL更新
            self.current_capital += net_pnl
            self.daily_pnl += net_pnl
            
            # 取引記録
            trade_record = {
                "symbol": symbol,
                "action": "close",
                "side": position.side.value,
                "entry_price": position.entry_price,
                "exit_price": exit_price,
                "quantity": position.quantity,
                "pnl": net_pnl,
                "reason": reason,
                "timestamp": datetime.now(),
                "hold_time": datetime.now() - position.entry_time
            }
            self.trade_history.append(trade_record)
            
            # ポジション削除
            del self.positions[symbol]
            
            logger.info(f"Closed {position.side.value} position for {symbol}: "
                       f"PnL ¥{net_pnl:,.0f} ({reason})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return False
    
    def update_positions(self, price_data: Dict[str, float]):
        """
        全ポジションを更新
        
        Args:
            price_data: 銘柄別現在価格辞書
        """
        for symbol in list(self.positions.keys()):
            if symbol in price_data:
                current_price = price_data[symbol]
                
                # ポジション価格更新
                self.positions[symbol].update_price(current_price)
                
                # トレイリングストップ更新
                self.update_trailing_stop(symbol, current_price)
                
                # 決済条件チェック
                exit_condition = self.check_exit_conditions(symbol, current_price)
                if exit_condition["should_exit"]:
                    exit_price = exit_condition.get("exit_price", current_price)
                    reason = exit_condition.get("reason", "Unknown")
                    self.close_position(symbol, exit_price, reason)
    
    def get_portfolio_summary(self) -> Dict:
        """
        ポートフォリオサマリーを取得
        
        Returns:
            ポートフォリオ情報
        """
        total_unrealized_pnl = sum(pos.unrealized_pnl or 0 for pos in self.positions.values())
        
        return {
            "current_capital": self.current_capital,
            "initial_capital": self.initial_capital,
            "daily_pnl": self.daily_pnl,
            "total_pnl": self.current_capital - self.initial_capital,
            "unrealized_pnl": total_unrealized_pnl,
            "open_positions": len(self.positions),
            "max_positions": self.risk_params.max_positions,
            "position_details": {
                symbol: {
                    "side": pos.side.value,
                    "quantity": pos.quantity,
                    "entry_price": pos.entry_price,
                    "current_price": pos.current_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "stop_loss": pos.stop_loss,
                    "trailing_stop": pos.trailing_stop
                }
                for symbol, pos in self.positions.items()
            }
        }
    
    def reset_daily_pnl(self):
        """日次PnLをリセット"""
        self.daily_pnl = 0.0
        logger.info("Daily PnL reset")