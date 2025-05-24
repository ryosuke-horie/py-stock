"""
ダッシュボード用ユーティリティ関数
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import streamlit as st
from typing import Dict, List, Any, Optional
import json

class DashboardUtils:
    """ダッシュボード用ユーティリティクラス"""
    
    @staticmethod
    def format_currency(value: float, currency: str = "¥") -> str:
        """通貨フォーマット"""
        if pd.isna(value):
            return "N/A"
        
        if abs(value) >= 1e9:
            return f"{currency}{value/1e9:.2f}B"
        elif abs(value) >= 1e6:
            return f"{currency}{value/1e6:.2f}M"
        elif abs(value) >= 1e3:
            return f"{currency}{value/1e3:.1f}K"
        else:
            return f"{currency}{value:,.2f}"
    
    @staticmethod
    def format_percentage(value: float, decimal_places: int = 2) -> str:
        """パーセンテージフォーマット"""
        if pd.isna(value):
            return "N/A"
        return f"{value:.{decimal_places}f}%"
    
    @staticmethod
    def format_change(current: float, previous: float) -> tuple:
        """変動表示用フォーマット"""
        if pd.isna(current) or pd.isna(previous) or previous == 0:
            return "N/A", "neutral"
        
        change = current - previous
        change_pct = (change / previous) * 100
        
        if change > 0:
            return f"+{change:.2f} (+{change_pct:.2f}%)", "positive"
        elif change < 0:
            return f"{change:.2f} ({change_pct:.2f}%)", "negative"
        else:
            return "0.00 (0.00%)", "neutral"
    
    @staticmethod
    def create_metric_card(title: str, value: str, change: str = None, change_type: str = "neutral"):
        """メトリクスカード作成"""
        change_class = f"<span class='{change_type}'>{change}</span>" if change else ""
        
        return f"""
        <div class='metric-container'>
            <h4>{title}</h4>
            <h2>{value}</h2>
            {change_class}
        </div>
        """
    
    @staticmethod
    def create_alert_card(message: str, alert_type: str = "medium"):
        """アラートカード作成"""
        return f"""
        <div class='alert-{alert_type}'>
            {message}
        </div>
        """
    
    @staticmethod
    def calculate_technical_summary(data: pd.DataFrame) -> Dict[str, Any]:
        """テクニカル指標サマリー計算"""
        if data.empty:
            return {}
        
        current_price = data['close'].iloc[-1]
        prev_price = data['close'].iloc[-2] if len(data) > 1 else current_price
        
        # 基本統計
        high_52w = data['high'].rolling(252).max().iloc[-1] if len(data) >= 252 else data['high'].max()
        low_52w = data['low'].rolling(252).min().iloc[-1] if len(data) >= 252 else data['low'].min()
        
        # 移動平均
        sma_20 = data['close'].rolling(20).mean().iloc[-1] if len(data) >= 20 else current_price
        sma_50 = data['close'].rolling(50).mean().iloc[-1] if len(data) >= 50 else current_price
        
        # ボラティリティ
        volatility = data['close'].pct_change().std() * np.sqrt(252) * 100
        
        return {
            'current_price': current_price,
            'change': current_price - prev_price,
            'change_pct': ((current_price - prev_price) / prev_price) * 100 if prev_price != 0 else 0,
            'high_52w': high_52w,
            'low_52w': low_52w,
            'sma_20': sma_20,
            'sma_50': sma_50,
            'volatility': volatility,
            'volume': data['volume'].iloc[-1] if 'volume' in data.columns else 0,
            'avg_volume': data['volume'].rolling(20).mean().iloc[-1] if 'volume' in data.columns and len(data) >= 20 else 0
        }
    
    @staticmethod
    def create_candlestick_chart(data: pd.DataFrame, title: str = "株価チャート") -> go.Figure:
        """ローソク足チャート作成"""
        if data.empty:
            return go.Figure()
        
        fig = go.Figure(data=go.Candlestick(
            x=data.index,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name="OHLC"
        ))
        
        fig.update_layout(
            title=title,
            yaxis_title="価格",
            xaxis_title="日時",
            xaxis_rangeslider_visible=False,
            height=500
        )
        
        return fig
    
    @staticmethod
    def add_technical_indicators(fig: go.Figure, data: pd.DataFrame, indicators: List[str]):
        """テクニカル指標をチャートに追加"""
        colors = ['orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
        color_idx = 0
        
        for indicator in indicators:
            if indicator == 'SMA20' and len(data) >= 20:
                sma20 = data['close'].rolling(20).mean()
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=sma20,
                    mode='lines',
                    name='SMA(20)',
                    line=dict(color=colors[color_idx % len(colors)]),
                    opacity=0.7
                ))
                color_idx += 1
            
            elif indicator == 'SMA50' and len(data) >= 50:
                sma50 = data['close'].rolling(50).mean()
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=sma50,
                    mode='lines',
                    name='SMA(50)',
                    line=dict(color=colors[color_idx % len(colors)]),
                    opacity=0.7
                ))
                color_idx += 1
            
            elif indicator == 'EMA12' and len(data) >= 12:
                ema12 = data['close'].ewm(span=12).mean()
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=ema12,
                    mode='lines',
                    name='EMA(12)',
                    line=dict(color=colors[color_idx % len(colors)]),
                    opacity=0.7
                ))
                color_idx += 1
        
        return fig
    
    @staticmethod
    def create_volume_chart(data: pd.DataFrame) -> go.Figure:
        """出来高チャート作成"""
        if data.empty or 'volume' not in data.columns:
            return go.Figure()
        
        colors = ['green' if close >= open else 'red' 
                 for close, open in zip(data['close'], data['open'])]
        
        fig = go.Figure(data=go.Bar(
            x=data.index,
            y=data['volume'],
            marker_color=colors,
            name="出来高",
            opacity=0.7
        ))
        
        fig.update_layout(
            title="出来高",
            yaxis_title="出来高",
            xaxis_title="日時",
            height=200
        )
        
        return fig
    
    @staticmethod
    def create_rsi_chart(data: pd.DataFrame, period: int = 14) -> go.Figure:
        """RSIチャート作成"""
        if data.empty or len(data) < period + 1:
            return go.Figure()
        
        # RSI計算
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        fig = go.Figure()
        
        # RSIライン
        fig.add_trace(go.Scatter(
            x=data.index,
            y=rsi,
            mode='lines',
            name=f'RSI({period})',
            line=dict(color='blue')
        ))
        
        # 水平線
        fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="過買い")
        fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="過売り")
        fig.add_hline(y=50, line_dash="dot", line_color="gray")
        
        fig.update_layout(
            title=f"RSI({period})",
            yaxis_title="RSI",
            xaxis_title="日時",
            yaxis=dict(range=[0, 100]),
            height=200
        )
        
        return fig
    
    @staticmethod
    def save_user_settings(settings: Dict[str, Any]):
        """ユーザー設定保存"""
        try:
            with open('dashboard/user_settings.json', 'w') as f:
                json.dump(settings, f, default=str)
        except Exception as e:
            st.error(f"設定保存エラー: {e}")
    
    @staticmethod
    def load_user_settings() -> Dict[str, Any]:
        """ユーザー設定読込"""
        try:
            with open('dashboard/user_settings.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            st.error(f"設定読込エラー: {e}")
            return {}
    
    @staticmethod
    def calculate_portfolio_metrics(positions: List[Dict[str, Any]]) -> Dict[str, float]:
        """ポートフォリオメトリクス計算"""
        if not positions:
            return {}
        
        total_value = sum(pos.get('current_value', 0) for pos in positions)
        total_cost = sum(pos.get('cost_basis', 0) for pos in positions)
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        
        # 個別銘柄の損益
        winners = [pos for pos in positions if pos.get('pnl', 0) > 0]
        losers = [pos for pos in positions if pos.get('pnl', 0) < 0]
        
        return {
            'total_value': total_value,
            'total_cost': total_cost,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'winners_count': len(winners),
            'losers_count': len(losers),
            'win_rate': len(winners) / len(positions) * 100 if positions else 0
        }
    
    @staticmethod
    def format_datetime(dt: datetime, format_type: str = "short") -> str:
        """日時フォーマット"""
        if pd.isna(dt):
            return "N/A"
        
        if format_type == "short":
            return dt.strftime("%m/%d %H:%M")
        elif format_type == "long":
            return dt.strftime("%Y年%m月%d日 %H:%M:%S")
        elif format_type == "date":
            return dt.strftime("%Y/%m/%d")
        elif format_type == "time":
            return dt.strftime("%H:%M:%S")
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def create_performance_summary(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """パフォーマンスサマリー作成"""
        if not trades:
            return {}
        
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
        
        win_rate = len(winning_trades) / total_trades * 100
        
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # 最大ドローダウン計算
        cumulative_pnl = np.cumsum([t.get('pnl', 0) for t in trades])
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = (cumulative_pnl - running_max)
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades)
        }