"""
チャート表示（ローソク足 + 指標オーバーレイ）コンポーネント
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.technical_analysis.indicators import TechnicalIndicators
from src.technical_analysis.support_resistance import SupportResistanceDetector
from ..utils.dashboard_utils import DashboardUtils


class ChartComponent:
    """チャート表示コンポーネント"""
    
    def __init__(self, data_collector):
        """初期化"""
        self.data_collector = data_collector
        self.utils = DashboardUtils()
    
    def display(self, symbol: str, period: str = "1mo", interval: str = "1d"):
        """チャート表示"""
        st.subheader(f"📈 {symbol} - 詳細チャート分析")
        
        # データ取得
        with st.spinner(f"{symbol} のデータを取得中..."):
            data = self.data_collector.get_stock_data(symbol, period=period, interval=interval)
        
        if data is None or data.empty:
            st.error(f"{symbol} のデータを取得できませんでした。")
            return
        
        # チャート設定パネル
        self._display_chart_controls()
        
        # メインチャート表示
        self._display_main_chart(data, symbol)
        
        # サブチャート表示
        if st.session_state.get('show_subcharts', True):
            self._display_sub_charts(data, symbol)
        
        # テクニカル分析サマリー
        self._display_technical_summary(data, symbol)
    
    def _display_chart_controls(self):
        """チャート設定コントロール"""
        st.markdown("### ⚙️ チャート設定")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.session_state.chart_type = st.selectbox(
                "チャートタイプ",
                ["ローソク足", "ラインチャート", "エリアチャート"],
                index=0,
                key="chart_type_select"
            )
        
        with col2:
            # 移動平均線設定
            ma_options = st.multiselect(
                "移動平均線",
                ["SMA5", "SMA20", "SMA50", "EMA9", "EMA21"],
                default=["SMA20", "EMA21"],
                key="ma_select"
            )
            st.session_state.selected_ma = ma_options
        
        with col3:
            # テクニカル指標設定
            indicator_options = st.multiselect(
                "オーバーレイ指標",
                ["ボリンジャーバンド", "一目均衡表", "VWAP", "パラボリック"],
                default=["ボリンジャーバンド"],
                key="indicator_select"
            )
            st.session_state.selected_indicators = indicator_options
        
        with col4:
            # サブチャート設定
            subchart_options = st.multiselect(
                "サブチャート",
                ["出来高", "RSI", "MACD", "ストキャスティクス"],
                default=["出来高", "RSI"],
                key="subchart_select"
            )
            st.session_state.selected_subcharts = subchart_options
        
        # 詳細設定
        with st.expander("🔧 詳細設定"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.session_state.show_volume = st.checkbox("出来高表示", value=True)
                st.session_state.show_support_resistance = st.checkbox("サポレジ表示", value=True)
            
            with col2:
                st.session_state.chart_height = st.slider("チャート高さ", 300, 800, 600)
                st.session_state.show_crosshair = st.checkbox("クロスヘア表示", value=True)
            
            with col3:
                st.session_state.show_subcharts = st.checkbox("サブチャート表示", value=True)
                st.session_state.sync_axes = st.checkbox("軸同期", value=True)
    
    def _display_main_chart(self, data: pd.DataFrame, symbol: str):
        """メインチャート表示"""
        # サブプロット作成（メイン + 出来高）
        subplot_count = 1
        if st.session_state.get('show_volume', True):
            subplot_count += 1
        
        row_heights = [0.8, 0.2] if subplot_count > 1 else [1.0]
        
        fig = make_subplots(
            rows=subplot_count,
            cols=1,
            row_heights=row_heights,
            vertical_spacing=0.03,
            subplot_titles=[f"{symbol} 株価チャート", "出来高"] if subplot_count > 1 else [f"{symbol} 株価チャート"],
            shared_xaxes=True
        )
        
        # メインチャート（価格）
        if st.session_state.get('chart_type', 'ローソク足') == "ローソク足":
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name="OHLC",
                    increasing_line_color='#00c851',
                    decreasing_line_color='#ff4444'
                ),
                row=1, col=1
            )
        elif st.session_state.get('chart_type', 'ローソク足') == "ラインチャート":
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['close'],
                    mode='lines',
                    name="終値",
                    line=dict(color='#1f77b4', width=2)
                ),
                row=1, col=1
            )
        else:  # エリアチャート
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['close'],
                    mode='lines',
                    name="終値",
                    fill='tonexty',
                    line=dict(color='#1f77b4', width=2)
                ),
                row=1, col=1
            )
        
        # 移動平均線追加
        self._add_moving_averages(fig, data)
        
        # テクニカル指標追加
        self._add_technical_overlays(fig, data)
        
        # サポート・レジスタンス追加
        if st.session_state.get('show_support_resistance', True):
            self._add_support_resistance(fig, data)
        
        # 出来高チャート
        if st.session_state.get('show_volume', True) and 'volume' in data.columns:
            colors = ['green' if close >= open else 'red' 
                     for close, open in zip(data['close'], data['open'])]
            
            fig.add_trace(
                go.Bar(
                    x=data.index,
                    y=data['volume'],
                    name="出来高",
                    marker_color=colors,
                    opacity=0.7
                ),
                row=2, col=1
            )
        
        # レイアウト設定
        fig.update_layout(
            height=st.session_state.get('chart_height', 600),
            showlegend=True,
            xaxis_rangeslider_visible=False,
            hovermode='x unified' if st.session_state.get('show_crosshair', True) else 'closest'
        )
        
        # Y軸設定
        fig.update_yaxes(title_text="価格", row=1, col=1)
        if subplot_count > 1:
            fig.update_yaxes(title_text="出来高", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _add_moving_averages(self, fig: go.Figure, data: pd.DataFrame):
        """移動平均線追加"""
        selected_ma = st.session_state.get('selected_ma', [])
        colors = ['orange', 'purple', 'brown', 'pink', 'gray']
        
        for i, ma_type in enumerate(selected_ma):
            color = colors[i % len(colors)]
            
            if ma_type == "SMA5" and len(data) >= 5:
                sma5 = data['close'].rolling(5).mean()
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=sma5,
                        mode='lines',
                        name='SMA(5)',
                        line=dict(color=color, width=1),
                        opacity=0.8
                    ),
                    row=1, col=1
                )
            
            elif ma_type == "SMA20" and len(data) >= 20:
                sma20 = data['close'].rolling(20).mean()
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=sma20,
                        mode='lines',
                        name='SMA(20)',
                        line=dict(color=color, width=2),
                        opacity=0.8
                    ),
                    row=1, col=1
                )
            
            elif ma_type == "SMA50" and len(data) >= 50:
                sma50 = data['close'].rolling(50).mean()
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=sma50,
                        mode='lines',
                        name='SMA(50)',
                        line=dict(color=color, width=2),
                        opacity=0.8
                    ),
                    row=1, col=1
                )
            
            elif ma_type == "EMA9" and len(data) >= 9:
                ema9 = data['close'].ewm(span=9).mean()
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=ema9,
                        mode='lines',
                        name='EMA(9)',
                        line=dict(color=color, width=1, dash='dash'),
                        opacity=0.8
                    ),
                    row=1, col=1
                )
            
            elif ma_type == "EMA21" and len(data) >= 21:
                ema21 = data['close'].ewm(span=21).mean()
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=ema21,
                        mode='lines',
                        name='EMA(21)',
                        line=dict(color=color, width=2, dash='dash'),
                        opacity=0.8
                    ),
                    row=1, col=1
                )
    
    def _add_technical_overlays(self, fig: go.Figure, data: pd.DataFrame):
        """テクニカル指標オーバーレイ追加"""
        selected_indicators = st.session_state.get('selected_indicators', [])
        
        if not selected_indicators:
            return
        
        try:
            # TechnicalIndicatorsインスタンス作成
            indicators = TechnicalIndicators(data)
            
            for indicator in selected_indicators:
                if indicator == "ボリンジャーバンド":
                    self._add_bollinger_bands(fig, data, indicators)
                elif indicator == "VWAP":
                    self._add_vwap(fig, data, indicators)
                elif indicator == "パラボリック":
                    self._add_parabolic_sar(fig, data)
                # elif indicator == "一目均衡表":
                #     self._add_ichimoku(fig, data)
        
        except Exception as e:
            st.warning(f"テクニカル指標の追加でエラーが発生しました: {e}")
    
    def _add_bollinger_bands(self, fig: go.Figure, data: pd.DataFrame, indicators: TechnicalIndicators):
        """ボリンジャーバンド追加"""
        try:
            bb_data = indicators.calculate_bollinger_bands()
            if bb_data.empty:
                return
            
            # 上位バンド
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=bb_data['bb_upper'],
                    mode='lines',
                    name='BB Upper',
                    line=dict(color='gray', width=1, dash='dot'),
                    opacity=0.5
                ),
                row=1, col=1
            )
            
            # 中央線（SMA）
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=bb_data['bb_middle'],
                    mode='lines',
                    name='BB Middle',
                    line=dict(color='blue', width=1),
                    opacity=0.7
                ),
                row=1, col=1
            )
            
            # 下位バンド
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=bb_data['bb_lower'],
                    mode='lines',
                    name='BB Lower',
                    line=dict(color='gray', width=1, dash='dot'),
                    fill='tonexty',
                    fillcolor='rgba(0,100,80,0.1)',
                    opacity=0.5
                ),
                row=1, col=1
            )
        
        except Exception as e:
            st.warning(f"ボリンジャーバンドの追加でエラー: {e}")
    
    def _add_vwap(self, fig: go.Figure, data: pd.DataFrame, indicators: TechnicalIndicators):
        """VWAP追加"""
        try:
            vwap = indicators.calculate_vwap()
            if vwap.empty:
                return
            
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=vwap,
                    mode='lines',
                    name='VWAP',
                    line=dict(color='yellow', width=2),
                    opacity=0.8
                ),
                row=1, col=1
            )
        
        except Exception as e:
            st.warning(f"VWAPの追加でエラー: {e}")
    
    def _add_parabolic_sar(self, fig: go.Figure, data: pd.DataFrame):
        """パラボリックSAR追加（簡易実装）"""
        try:
            if len(data) < 10:
                return
            
            # 簡易パラボリックSAR計算
            sar = []
            acceleration = 0.02
            max_acceleration = 0.2
            
            for i in range(len(data)):
                if i < 2:
                    sar.append(data['low'].iloc[i])
                else:
                    # 簡易計算（実際のパラボリックSARはより複雑）
                    sar.append(data['low'].rolling(3).min().iloc[i])
            
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=sar,
                    mode='markers',
                    name='Parabolic SAR',
                    marker=dict(color='red', size=3),
                    opacity=0.7
                ),
                row=1, col=1
            )
        
        except Exception as e:
            st.warning(f"パラボリックSARの追加でエラー: {e}")
    
    def _add_support_resistance(self, fig: go.Figure, data: pd.DataFrame):
        """サポート・レジスタンスレベル追加"""
        try:
            if len(data) < 30:
                return
            
            detector = SupportResistanceDetector(data)
            analysis = detector.comprehensive_analysis()
            
            if 'support_resistance_levels' in analysis:
                levels = analysis['support_resistance_levels'][:5]  # 上位5レベルのみ表示
                
                for level in levels:
                    color = 'green' if level.level_type == 'support' else 'red'
                    dash = 'solid' if level.strength > 0.7 else 'dash'
                    
                    fig.add_hline(
                        y=level.price,
                        line_dash=dash,
                        line_color=color,
                        opacity=0.6,
                        annotation_text=f"{level.level_type.upper()}: {level.price:.2f}",
                        annotation_position="right"
                    )
        
        except Exception as e:
            st.warning(f"サポート・レジスタンスの追加でエラー: {e}")
    
    def _display_sub_charts(self, data: pd.DataFrame, symbol: str):
        """サブチャート表示"""
        selected_subcharts = st.session_state.get('selected_subcharts', [])
        
        if not selected_subcharts:
            return
        
        st.markdown("### 📊 テクニカル指標")
        
        # 各サブチャートを作成
        for subchart in selected_subcharts:
            if subchart == "RSI":
                self._display_rsi_chart(data)
            elif subchart == "MACD":
                self._display_macd_chart(data)
            elif subchart == "ストキャスティクス":
                self._display_stochastic_chart(data)
            elif subchart == "出来高" and 'volume' in data.columns:
                self._display_volume_chart(data)
    
    def _display_rsi_chart(self, data: pd.DataFrame):
        """RSIチャート表示"""
        try:
            indicators = TechnicalIndicators(data)
            rsi = indicators.calculate_rsi()
            
            if rsi.empty:
                st.warning("RSIの計算に十分なデータがありません")
                return
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=data.index,
                y=rsi,
                mode='lines',
                name='RSI(14)',
                line=dict(color='blue', width=2)
            ))
            
            # RSI水平線
            fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="過買い")
            fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="過売り")
            fig.add_hline(y=50, line_dash="dot", line_color="gray")
            
            fig.update_layout(
                title="RSI (Relative Strength Index)",
                yaxis_title="RSI",
                yaxis=dict(range=[0, 100]),
                height=200,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        except Exception as e:
            st.warning(f"RSIチャートの表示でエラー: {e}")
    
    def _display_macd_chart(self, data: pd.DataFrame):
        """MACDチャート表示"""
        try:
            indicators = TechnicalIndicators(data)
            macd_data = indicators.calculate_macd()
            
            if macd_data.empty:
                st.warning("MACDの計算に十分なデータがありません")
                return
            
            fig = go.Figure()
            
            # MACDライン
            fig.add_trace(go.Scatter(
                x=data.index,
                y=macd_data['macd'],
                mode='lines',
                name='MACD',
                line=dict(color='blue', width=2)
            ))
            
            # シグナルライン
            fig.add_trace(go.Scatter(
                x=data.index,
                y=macd_data['signal'],
                mode='lines',
                name='Signal',
                line=dict(color='red', width=2)
            ))
            
            # ヒストグラム
            fig.add_trace(go.Bar(
                x=data.index,
                y=macd_data['histogram'],
                name='Histogram',
                marker_color='gray',
                opacity=0.7
            ))
            
            fig.update_layout(
                title="MACD (Moving Average Convergence Divergence)",
                yaxis_title="MACD",
                height=200
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        except Exception as e:
            st.warning(f"MACDチャートの表示でエラー: {e}")
    
    def _display_stochastic_chart(self, data: pd.DataFrame):
        """ストキャスティクスチャート表示"""
        try:
            indicators = TechnicalIndicators(data)
            stoch_data = indicators.calculate_stochastic()
            
            if stoch_data.empty:
                st.warning("ストキャスティクスの計算に十分なデータがありません")
                return
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=data.index,
                y=stoch_data['stoch_k'],
                mode='lines',
                name='%K',
                line=dict(color='blue', width=2)
            ))
            
            fig.add_trace(go.Scatter(
                x=data.index,
                y=stoch_data['stoch_d'],
                mode='lines',
                name='%D',
                line=dict(color='red', width=2)
            ))
            
            # 水平線
            fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="過買い")
            fig.add_hline(y=20, line_dash="dash", line_color="green", annotation_text="過売り")
            
            fig.update_layout(
                title="ストキャスティクス",
                yaxis_title="値",
                yaxis=dict(range=[0, 100]),
                height=200
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        except Exception as e:
            st.warning(f"ストキャスティクスチャートの表示でエラー: {e}")
    
    def _display_volume_chart(self, data: pd.DataFrame):
        """出来高チャート表示"""
        try:
            colors = ['green' if close >= open else 'red' 
                     for close, open in zip(data['close'], data['open'])]
            
            fig = go.Figure(data=go.Bar(
                x=data.index,
                y=data['volume'],
                marker_color=colors,
                name="出来高",
                opacity=0.7
            ))
            
            # 移動平均出来高
            if len(data) >= 20:
                avg_volume = data['volume'].rolling(20).mean()
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=avg_volume,
                    mode='lines',
                    name='平均出来高(20)',
                    line=dict(color='orange', width=2)
                ))
            
            fig.update_layout(
                title="出来高",
                yaxis_title="出来高",
                height=200
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        except Exception as e:
            st.warning(f"出来高チャートの表示でエラー: {e}")
    
    def _display_technical_summary(self, data: pd.DataFrame, symbol: str):
        """テクニカル分析サマリー表示"""
        st.markdown("### 📊 テクニカル分析サマリー")
        
        try:
            indicators = TechnicalIndicators(data)
            analysis = indicators.comprehensive_analysis()
            
            # メトリクス表示
            col1, col2, col3, col4 = st.columns(4)
            
            current_values = analysis.get('current_values', {})
            
            with col1:
                rsi_val = current_values.get('rsi_current', 0)
                rsi_status = "過買い" if rsi_val > 70 else "過売り" if rsi_val < 30 else "中立"
                st.metric("RSI", f"{rsi_val:.1f}", rsi_status)
            
            with col2:
                macd_val = current_values.get('macd_current', 0)
                st.metric("MACD", f"{macd_val:.4f}")
            
            with col3:
                bb_pos = current_values.get('bb_percent_b_current', 0.5)
                bb_status = "上限付近" if bb_pos > 0.8 else "下限付近" if bb_pos < 0.2 else "中央"
                st.metric("BB Position", f"{bb_pos:.2f}", bb_status)
            
            with col4:
                atr_val = current_values.get('atr_current', 0)
                st.metric("ATR", f"{atr_val:.2f}")
            
            # シグナル表示
            if 'signals' in analysis:
                self._display_signal_summary(analysis['signals'])
        
        except Exception as e:
            st.warning(f"テクニカル分析サマリーの表示でエラー: {e}")
    
    def _display_signal_summary(self, signals: Dict[str, bool]):
        """シグナルサマリー表示"""
        st.markdown("#### 🎯 テクニカルシグナル")
        
        buy_signals = []
        sell_signals = []
        
        signal_mapping = {
            'rsi_oversold': ('RSI過売り', 'buy'),
            'rsi_overbought': ('RSI過買い', 'sell'),
            'macd_bullish': ('MACD強気', 'buy'),
            'macd_bearish': ('MACD弱気', 'sell'),
            'price_above_vwap': ('VWAP上抜け', 'buy'),
            'price_below_vwap': ('VWAP下抜け', 'sell'),
            'bb_lower_return': ('BB下限反発', 'buy'),
            'bb_upper_return': ('BB上限反発', 'sell')
        }
        
        for signal_key, active in signals.items():
            if active and signal_key in signal_mapping:
                signal_name, signal_type = signal_mapping[signal_key]
                if signal_type == 'buy':
                    buy_signals.append(signal_name)
                else:
                    sell_signals.append(signal_name)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🟢 買いシグナル:**")
            if buy_signals:
                for signal in buy_signals:
                    st.success(f"✓ {signal}")
            else:
                st.info("買いシグナルなし")
        
        with col2:
            st.markdown("**🔴 売りシグナル:**")
            if sell_signals:
                for signal in sell_signals:
                    st.error(f"✓ {signal}")
            else:
                st.info("売りシグナルなし")