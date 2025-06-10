"""
ウォッチリスト銘柄の価格・指標表示コンポーネント
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from typing import List, Dict, Any
import concurrent.futures
import time

from ..utils.dashboard_utils import DashboardUtils
from src.data_collector.symbol_manager import SymbolManager
from src.data_collector.watchlist_storage import WatchlistStorage


class WatchlistComponent:
    """ウォッチリストコンポーネント"""
    
    def __init__(self, data_collector, watchlist_storage: WatchlistStorage = None):
        """初期化"""
        self.data_collector = data_collector
        self.utils = DashboardUtils()
        self.symbol_manager = SymbolManager()
        self.watchlist_storage = watchlist_storage or WatchlistStorage()
    
    def display(self, symbols: List[str]):
        """ウォッチリスト表示"""
        if not symbols:
            st.info("ウォッチリストに銘柄が登録されていません。")
            return
        
        st.subheader("📋 ウォッチリスト")
        
        # データ取得プログレスバー
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 並列でデータ取得
        watchlist_data = self._fetch_watchlist_data(symbols, progress_bar, status_text)
        
        # プログレスバーをクリア
        progress_bar.empty()
        status_text.empty()
        
        if watchlist_data:
            # データテーブル表示
            self._display_watchlist_table(watchlist_data)
            
            # サマリー表示
            self._display_watchlist_summary(watchlist_data)
        else:
            st.error("ウォッチリストのデータを取得できませんでした。")
    
    def _fetch_watchlist_data(self, symbols: List[str], progress_bar, status_text) -> List[Dict[str, Any]]:
        """ウォッチリストデータを並列取得"""
        watchlist_data = []
        
        # WatchlistStorageからカスタム会社名を含む詳細情報を取得
        watchlist_items = self.watchlist_storage.get_watchlist_items()
        symbol_to_name = {item.symbol: item.name for item in watchlist_items}
        
        def fetch_symbol_data(symbol: str) -> Dict[str, Any]:
            """個別銘柄データ取得"""
            try:
                # リアルタイム価格データ取得
                data = self.data_collector.get_stock_data(symbol, period="5d", interval="1d")
                if data is None or data.empty:
                    return None
                
                # 基本情報計算
                current_price = data['close'].iloc[-1]
                prev_price = data['close'].iloc[-2] if len(data) > 1 else current_price
                change = current_price - prev_price
                change_pct = (change / prev_price) * 100 if prev_price != 0 else 0
                
                # テクニカル指標
                sma_5 = data['close'].rolling(5).mean().iloc[-1] if len(data) >= 5 else current_price
                sma_20 = data['close'].rolling(20).mean().iloc[-1] if len(data) >= 20 else current_price
                
                # RSI計算（簡易版）
                rsi = self._calculate_simple_rsi(data['close']) if len(data) >= 14 else 50
                
                # 出来高情報
                current_volume = data['volume'].iloc[-1] if 'volume' in data.columns else 0
                avg_volume = data['volume'].rolling(5).mean().iloc[-1] if 'volume' in data.columns and len(data) >= 5 else current_volume
                
                # トレンド判定
                trend = self._determine_trend(current_price, sma_5, sma_20)
                
                # カスタム会社名を優先して使用、なければSymbolManagerから取得
                custom_name = symbol_to_name.get(symbol)
                if custom_name and custom_name != "N/A":
                    company_name = custom_name
                else:
                    # フォールバック: SymbolManagerから取得
                    symbol_info = self.symbol_manager.get_symbol_info(symbol)
                    company_name = symbol_info['name']
                
                return {
                    'symbol': symbol,
                    'name': company_name,
                    'current_price': current_price,
                    'change': change,
                    'change_pct': change_pct,
                    'sma_5': sma_5,
                    'sma_20': sma_20,
                    'rsi': rsi,
                    'volume': current_volume,
                    'avg_volume': avg_volume,
                    'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 1,
                    'trend': trend,
                    'last_update': datetime.now()
                }
            except Exception as e:
                st.warning(f"データ取得エラー ({symbol}): {e}")
                return None
        
        # 並列処理でデータ取得
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_symbol = {executor.submit(fetch_symbol_data, symbol): symbol 
                              for symbol in symbols}
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_symbol)):
                symbol = future_to_symbol[future]
                status_text.text(f"データ取得中: {symbol}")
                progress_bar.progress((i + 1) / len(symbols))
                
                try:
                    result = future.result()
                    if result:
                        watchlist_data.append(result)
                except Exception as e:
                    st.warning(f"並列処理エラー ({symbol}): {e}")
        
        return watchlist_data
    
    def _display_watchlist_table(self, watchlist_data: List[Dict[str, Any]]):
        """ウォッチリストテーブル表示"""
        # DataFrame作成
        df_data = []
        for item in watchlist_data:
            # 銘柄表示：銘柄コード + 社名
            symbol_display = f"{item['symbol']}"
            if item['name'] != 'N/A':
                symbol_display = f"{item['symbol']} ({item['name']})"
            
            df_data.append({
                '銘柄': symbol_display,
                '現在価格': f"{item['current_price']:.2f}",
                '変動': f"{item['change']:+.2f}",
                '変動率(%)': f"{item['change_pct']:+.2f}",
                'RSI': f"{item['rsi']:.1f}",
                'トレンド': item['trend'],
                '出来高比': f"{item['volume_ratio']:.2f}x",
                '更新時刻': item['last_update'].strftime('%H:%M:%S')
            })
        
        df = pd.DataFrame(df_data)
        
        # スタイル適用
        def color_change(val):
            """変動率に応じた色付け"""
            try:
                value = float(val.replace('+', '').replace('%', ''))
                if value > 0:
                    return 'background-color: #e8f5e8; color: #2e7d32'
                elif value < 0:
                    return 'background-color: #ffebee; color: #c62828'
                else:
                    return 'background-color: #f5f5f5; color: #666'
            except:
                return ''
        
        def color_trend(val):
            """トレンドに応じた色付け"""
            if val == '上昇':
                return 'background-color: #e8f5e8; color: #2e7d32'
            elif val == '下降':
                return 'background-color: #ffebee; color: #c62828'
            else:
                return 'background-color: #fff3e0; color: #f57c00'
        
        def color_rsi(val):
            """RSIに応じた色付け"""
            try:
                value = float(val)
                if value > 70:
                    return 'background-color: #ffebee; color: #c62828'  # 過買い
                elif value < 30:
                    return 'background-color: #e8f5e8; color: #2e7d32'  # 過売り
                else:
                    return 'background-color: #f5f5f5; color: #666'
            except:
                return ''
        
        styled_df = df.style.applymap(color_change, subset=['変動', '変動率(%)']) \
                           .applymap(color_trend, subset=['トレンド']) \
                           .applymap(color_rsi, subset=['RSI'])
        
        st.dataframe(styled_df, use_container_width=True)
    
    def _display_watchlist_summary(self, watchlist_data: List[Dict[str, Any]]):
        """ウォッチリストサマリー表示"""
        if not watchlist_data:
            return
        
        st.subheader("📊 ウォッチリストサマリー")
        
        # 統計計算
        total_symbols = len(watchlist_data)
        positive_symbols = len([item for item in watchlist_data if item['change_pct'] > 0])
        negative_symbols = len([item for item in watchlist_data if item['change_pct'] < 0])
        neutral_symbols = total_symbols - positive_symbols - negative_symbols
        
        avg_change = np.mean([item['change_pct'] for item in watchlist_data])
        
        # メトリクス表示
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("総銘柄数", total_symbols)
        
        with col2:
            st.metric(
                "上昇銘柄", 
                positive_symbols,
                delta=f"{positive_symbols/total_symbols*100:.1f}%" if total_symbols > 0 else "0%"
            )
        
        with col3:
            st.metric(
                "下落銘柄", 
                negative_symbols,
                delta=f"-{negative_symbols/total_symbols*100:.1f}%" if total_symbols > 0 else "0%"
            )
        
        with col4:
            st.metric(
                "平均変動率", 
                f"{avg_change:+.2f}%",
                delta="全体平均"
            )
        
        with col5:
            st.metric("横ばい", neutral_symbols)
        
        # トレンド分布グラフ
        self._display_trend_distribution(watchlist_data)
    
    def _display_trend_distribution(self, watchlist_data: List[Dict[str, Any]]):
        """トレンド分布表示"""
        trends = [item['trend'] for item in watchlist_data]
        trend_counts = pd.Series(trends).value_counts()
        
        # 円グラフ作成
        fig = go.Figure(data=[go.Pie(
            labels=trend_counts.index,
            values=trend_counts.values,
            hole=0.4,
            marker_colors=['#2e7d32', '#c62828', '#f57c00']
        )])
        
        fig.update_layout(
            title="トレンド分布",
            height=300,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _calculate_simple_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """簡易RSI計算"""
        if len(prices) < period + 1:
            return 50.0
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
    
    def _determine_trend(self, current_price: float, sma_5: float, sma_20: float) -> str:
        """トレンド判定"""
        if current_price > sma_5 > sma_20:
            return "上昇"
        elif current_price < sma_5 < sma_20:
            return "下降"
        else:
            return "横ばい"