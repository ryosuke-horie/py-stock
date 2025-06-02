"""
インテリジェントアラート管理コンポーネント
市場状況に応じた動的アラート管理とノイズフィルタリング機能を提供
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import logging

# インテリジェントアラートシステムのインポート
try:
    from src.technical_analysis.intelligent_alert_system import (
        IntelligentAlertSystem,
        AlertPriority,
        MarketCondition
    )
    from src.data_collector.stock_data_collector import StockDataCollector
    from src.technical_analysis.indicators import TechnicalIndicators
    from src.technical_analysis.market_environment import MarketEnvironmentAnalyzer
except ImportError:
    st.error("必要なモジュールのインポートに失敗しました。")
    IntelligentAlertSystem = None

logger = logging.getLogger(__name__)


class IntelligentAlertComponent:
    """インテリジェントアラート管理コンポーネント"""
    
    def __init__(self):
        """初期化"""
        # セッション状態初期化
        if 'intelligent_alert_system' not in st.session_state:
            if IntelligentAlertSystem:
                st.session_state.intelligent_alert_system = IntelligentAlertSystem()
            else:
                st.session_state.intelligent_alert_system = None
        
        if 'alert_settings' not in st.session_state:
            st.session_state.alert_settings = {
                'enable_dynamic_adjustment': True,
                'enable_noise_filter': True,
                'enable_composite_alerts': True
            }
        
        # データ収集器とインジケーター
        self.data_collector = StockDataCollector() if 'StockDataCollector' in globals() else None
        self.indicators = None  # TechnicalIndicatorsは必要時にデータ付きで初期化
        self.market_analyzer = MarketEnvironmentAnalyzer() if 'MarketEnvironmentAnalyzer' in globals() else None
    
    def display(self):
        """インテリジェントアラート管理画面表示"""
        st.subheader("🚨 インテリジェントアラート管理")
        
        if not st.session_state.intelligent_alert_system:
            st.error("インテリジェントアラートシステムが初期化されていません")
            return
        
        # システム設定
        with st.expander("⚙️ システム設定", expanded=False):
            self._display_system_settings()
        
        # タブ構成
        alert_tabs = st.tabs([
            "📊 市場状況モニター",
            "🎯 複合アラート設定",
            "📋 アクティブアラート",
            "📜 アラート履歴・分析"
        ])
        
        with alert_tabs[0]:
            self._display_market_monitor()
        
        with alert_tabs[1]:
            self._display_composite_alert_settings()
        
        with alert_tabs[2]:
            self._display_active_alerts()
        
        with alert_tabs[3]:
            self._display_alert_analytics()
    
    def _display_system_settings(self):
        """システム設定表示"""
        col1, col2 = st.columns(2)
        
        with col1:
            st.session_state.alert_settings['enable_dynamic_adjustment'] = st.checkbox(
                "動的閾値調整を有効化",
                value=st.session_state.alert_settings['enable_dynamic_adjustment'],
                help="市場ボラティリティに応じてアラート閾値を自動調整"
            )
            
            st.session_state.alert_settings['enable_noise_filter'] = st.checkbox(
                "ノイズフィルターを有効化",
                value=st.session_state.alert_settings['enable_noise_filter'],
                help="重要でないアラートを自動的にフィルタリング"
            )
        
        with col2:
            st.session_state.alert_settings['enable_composite_alerts'] = st.checkbox(
                "複合条件アラートを有効化",
                value=st.session_state.alert_settings['enable_composite_alerts'],
                help="複数の条件を組み合わせた高度なアラート"
            )
            
            # ノイズフィルター設定
            if st.session_state.alert_settings['enable_noise_filter']:
                filter_window = st.slider(
                    "ノイズフィルター期間（秒）",
                    60, 600, 300,
                    help="同一アラートの最小間隔"
                )
                st.session_state.intelligent_alert_system.noise_filter_window = filter_window
    
    def _display_market_monitor(self):
        """市場状況モニター表示"""
        st.markdown("### 📊 リアルタイム市場状況")
        
        # ウォッチリスト銘柄の市場状況を表示
        if 'watchlist' not in st.session_state or not st.session_state.watchlist:
            st.info("ウォッチリストに銘柄を追加してください")
            return
        
        # 市場状況サマリー
        market_conditions = self._analyze_market_conditions()
        
        # 全体的な市場状況
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            extreme_count = sum(1 for c in market_conditions.values() 
                              if c == MarketCondition.EXTREME_VOLATILITY)
            st.metric("極端なボラティリティ", extreme_count, 
                     delta="警戒" if extreme_count > 0 else None,
                     delta_color="inverse" if extreme_count > 0 else "normal")
        
        with col2:
            high_count = sum(1 for c in market_conditions.values() 
                           if c == MarketCondition.HIGH_VOLATILITY)
            st.metric("高ボラティリティ", high_count)
        
        with col3:
            normal_count = sum(1 for c in market_conditions.values() 
                             if c == MarketCondition.NORMAL)
            st.metric("通常", normal_count)
        
        with col4:
            consolidation_count = sum(1 for c in market_conditions.values() 
                                    if c == MarketCondition.CONSOLIDATION)
            st.metric("レンジ相場", consolidation_count)
        
        # 個別銘柄の状況
        st.markdown("#### 📈 個別銘柄状況")
        
        market_data = []
        for symbol, condition in market_conditions.items():
            # 仮のデータ（実際にはリアルタイムデータを取得）
            current_price = np.random.uniform(1000, 3000)
            change_pct = np.random.uniform(-5, 5)
            
            market_data.append({
                '銘柄': symbol,
                '現在価格': f"¥{current_price:,.0f}",
                '変化率': f"{change_pct:+.2f}%",
                '市場状況': self._get_condition_display(condition),
                '閾値調整': self._get_adjustment_factor(condition)
            })
        
        if market_data:
            df = pd.DataFrame(market_data)
            
            # スタイル適用
            def style_change(val):
                if '+' in val:
                    return 'color: green'
                elif '-' in val and val != '-0.00%':
                    return 'color: red'
                return ''
            
            def style_condition(val):
                colors = {
                    '🔴 極端な変動': 'background-color: #ffcdd2',
                    '🟠 高変動': 'background-color: #ffe0b2',
                    '🟢 通常': 'background-color: #c8e6c9',
                    '🔵 低変動': 'background-color: #bbdefb',
                    '⚪ レンジ': 'background-color: #e0e0e0'
                }
                return colors.get(val, '')
            
            styled_df = df.style.applymap(style_change, subset=['変化率']) \
                               .applymap(style_condition, subset=['市場状況'])
            
            st.dataframe(styled_df, use_container_width=True)
        
        # 動的閾値調整の状態
        if st.session_state.alert_settings['enable_dynamic_adjustment']:
            st.markdown("#### 🎯 動的閾値調整状態")
            st.info("市場ボラティリティに基づいてアラート閾値が自動調整されています")
    
    def _display_composite_alert_settings(self):
        """複合アラート設定画面"""
        st.markdown("### 🎯 複合条件アラート設定")
        
        if not st.session_state.alert_settings['enable_composite_alerts']:
            st.warning("複合条件アラートが無効になっています。システム設定で有効化してください。")
            return
        
        # アラートテンプレート選択
        alert_template = st.selectbox(
            "アラートテンプレート",
            [
                "カスタム設定",
                "ブレイクアウトアラート（価格 + 出来高 + モメンタム）",
                "トレンド転換アラート（テクニカル + ファンダメンタル）",
                "ニュース連動アラート（センチメント + 価格変動）",
                "リスクアラート（ボラティリティ + 相関）"
            ]
        )
        
        if alert_template == "カスタム設定":
            self._create_custom_composite_alert()
        else:
            self._create_template_alert(alert_template)
    
    def _create_custom_composite_alert(self):
        """カスタム複合アラート作成"""
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input("銘柄コード", placeholder="例: 7203.T", key="intelligent_alerts_custom_symbol")
            min_conditions = st.number_input(
                "最小条件数",
                min_value=1,
                max_value=5,
                value=2,
                help="発火に必要な最小条件数"
            )
        
        with col2:
            alert_name = st.text_input("アラート名", placeholder="例: 強気ブレイクアウト", key="intelligent_alerts_custom_name")
        
        # 条件設定
        st.markdown("#### 📋 アラート条件")
        
        conditions = []
        num_conditions = st.number_input("条件数", min_value=1, max_value=5, value=3)
        
        for i in range(num_conditions):
            with st.expander(f"条件 {i+1}", expanded=True):
                cond_col1, cond_col2, cond_col3 = st.columns(3)
                
                with cond_col1:
                    condition_type = st.selectbox(
                        "指標",
                        ["price", "rsi", "macd", "volume_ratio", "volatility", 
                         "news_sentiment", "support_resistance"],
                        key=f"cond_type_{i}"
                    )
                
                with cond_col2:
                    operator = st.selectbox(
                        "条件",
                        ["greater", "less", "equal", "between"],
                        format_func=lambda x: {
                            "greater": "以上",
                            "less": "以下",
                            "equal": "等しい",
                            "between": "範囲内"
                        }[x],
                        key=f"operator_{i}"
                    )
                
                with cond_col3:
                    if operator == "between":
                        min_val = st.number_input("最小値", key=f"min_{i}")
                        max_val = st.number_input("最大値", key=f"max_{i}")
                        threshold = (min_val, max_val)
                    else:
                        threshold = st.number_input("閾値", key=f"threshold_{i}")
                
                weight = st.slider(
                    "重要度",
                    0.1, 2.0, 1.0,
                    help="この条件の重み（優先度計算に使用）",
                    key=f"weight_{i}"
                )
                
                conditions.append({
                    'type': condition_type,
                    'operator': operator,
                    'threshold': threshold,
                    'weight': weight
                })
        
        # 優先度マッピング
        st.markdown("#### 🎯 優先度設定")
        priority_mapping = {}
        
        for i in range(1, num_conditions + 1):
            priority = st.select_slider(
                f"{i}個の条件が満たされた場合",
                options=['info', 'low', 'medium', 'high', 'critical'],
                value='medium' if i < 3 else 'high',
                format_func=lambda x: {
                    'info': '情報',
                    'low': '低',
                    'medium': '中',
                    'high': '高',
                    'critical': '緊急'
                }[x],
                key=f"priority_{i}"
            )
            priority_mapping[i] = priority
        
        # アラート作成
        if st.button("複合アラートを作成", type="primary"):
            if symbol and alert_name:
                try:
                    alert_system = st.session_state.intelligent_alert_system
                    alert_id = alert_system.create_composite_alert(
                        symbol=symbol,
                        conditions=conditions,
                        min_conditions=min_conditions,
                        priority_rules=priority_mapping
                    )
                    
                    st.success(f"✅ 複合アラート '{alert_name}' を作成しました (ID: {alert_id})")
                    st.balloons()
                except Exception as e:
                    st.error(f"アラート作成エラー: {str(e)}")
            else:
                st.error("銘柄コードとアラート名を入力してください")
    
    def _create_template_alert(self, template: str):
        """テンプレートベースのアラート作成"""
        st.info(f"テンプレート: {template}")
        
        col1, col2 = st.columns(2)
        with col1:
            symbol = st.text_input("銘柄コード", placeholder="例: 7203.T", key="intelligent_alerts_template_symbol")
        with col2:
            alert_name = st.text_input("アラート名", value=template, key="intelligent_alerts_template_name")
        
        # テンプレート別の設定
        if "ブレイクアウト" in template:
            st.markdown("#### ブレイクアウトアラート設定")
            
            price_threshold = st.number_input(
                "価格ブレイクアウト率（%）",
                min_value=0.1, max_value=10.0, value=2.0
            )
            
            volume_multiplier = st.number_input(
                "出来高倍率",
                min_value=1.5, max_value=10.0, value=3.0
            )
            
            momentum_threshold = st.slider(
                "モメンタム強度",
                0, 100, 70
            )
            
            if st.button("ブレイクアウトアラートを作成", type="primary"):
                if symbol:
                    conditions = [
                        {
                            'type': 'price_change_pct',
                            'operator': 'greater',
                            'threshold': price_threshold,
                            'weight': 1.5
                        },
                        {
                            'type': 'volume_ratio',
                            'operator': 'greater',
                            'threshold': volume_multiplier,
                            'weight': 1.2
                        },
                        {
                            'type': 'rsi',
                            'operator': 'greater',
                            'threshold': momentum_threshold,
                            'weight': 1.0
                        }
                    ]
                    
                    try:
                        alert_system = st.session_state.intelligent_alert_system
                        alert_id = alert_system.create_composite_alert(
                            symbol=symbol,
                            conditions=conditions,
                            min_conditions=2,
                            priority_rules={2: 'high', 3: 'critical'}
                        )
                        st.success(f"✅ ブレイクアウトアラートを作成しました (ID: {alert_id})")
                    except Exception as e:
                        st.error(f"エラー: {str(e)}")
        
        elif "トレンド転換" in template:
            st.markdown("#### トレンド転換アラート設定")
            # トレンド転換アラートの設定UI
            st.info("実装予定: トレンド転換アラートの詳細設定")
        
        elif "ニュース連動" in template:
            st.markdown("#### ニュース連動アラート設定")
            # ニュース連動アラートの設定UI
            st.info("実装予定: ニュース連動アラートの詳細設定")
        
        elif "リスク" in template:
            st.markdown("#### リスクアラート設定")
            # リスクアラートの設定UI
            st.info("実装予定: リスクアラートの詳細設定")
    
    def _display_active_alerts(self):
        """アクティブアラート表示"""
        st.markdown("### 📋 アクティブアラート")
        
        alert_system = st.session_state.intelligent_alert_system
        summary = alert_system.get_active_alerts_summary()
        
        # サマリー表示
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("総アラート数", summary['total_active'])
        
        with col2:
            critical_count = sum(1 for a in alert_system.alerts.values() 
                               if a.is_active and any(
                                   p == AlertPriority.CRITICAL 
                                   for p in a.priority_mapping.values()
                               ))
            st.metric("緊急アラート", critical_count, 
                     delta="要確認" if critical_count > 0 else None,
                     delta_color="inverse" if critical_count > 0 else "normal")
        
        with col3:
            symbols_count = len(summary['by_symbol'])
            st.metric("監視銘柄数", symbols_count)
        
        with col4:
            recent_count = len(summary['recent_alerts'])
            st.metric("直近1時間", recent_count)
        
        # アクティブアラート一覧
        if summary['total_active'] > 0:
            st.markdown("#### 📄 アラート一覧")
            
            for alert_id, alert in alert_system.alerts.items():
                if alert.is_active:
                    self._display_intelligent_alert_card(alert_id, alert)
        else:
            st.info("アクティブなアラートがありません")
        
        # 一括操作
        if summary['total_active'] > 0:
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔇 全アラートを一時停止"):
                    for alert in alert_system.alerts.values():
                        alert.is_active = False
                    st.success("全アラートを一時停止しました")
                    st.rerun()
            
            with col2:
                if st.button("🔄 市場状況を更新"):
                    self._update_market_conditions()
                    st.success("市場状況を更新しました")
                    st.rerun()
            
            with col3:
                if st.button("🗑️ 履歴をクリア"):
                    alert_system.alert_history.clear()
                    st.success("アラート履歴をクリアしました")
                    st.rerun()
    
    def _display_intelligent_alert_card(self, alert_id: str, alert: 'CompositeAlert'):
        """インテリジェントアラートカード表示"""
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                # 優先度表示
                max_priority = max(alert.priority_mapping.values(), 
                                 key=lambda x: ['info', 'low', 'medium', 'high', 'critical'].index(x.value))
                priority_icons = {
                    AlertPriority.CRITICAL: '🔴',
                    AlertPriority.HIGH: '🟠',
                    AlertPriority.MEDIUM: '🟡',
                    AlertPriority.LOW: '🟢',
                    AlertPriority.INFO: '🔵'
                }
                
                st.markdown(f"**{priority_icons.get(max_priority, '⚪')} {alert.symbol}**")
                st.write(f"条件数: {len(alert.conditions)} (最小: {alert.min_conditions_met})")
                
                # 条件の概要
                condition_types = [c.condition_type for c in alert.conditions if c.enabled]
                st.write(f"監視項目: {', '.join(condition_types[:3])}" + 
                        ("..." if len(condition_types) > 3 else ""))
            
            with col2:
                st.write(f"作成: {alert.created_at.strftime('%m/%d %H:%M')}")
                
                # 市場状況
                alert_system = st.session_state.intelligent_alert_system
                market_condition = alert_system.market_conditions.get(
                    alert.symbol, MarketCondition.NORMAL
                )
                st.write(f"市場: {self._get_condition_display(market_condition)}")
            
            with col3:
                # 動的調整状態
                if st.session_state.alert_settings['enable_dynamic_adjustment']:
                    adjustment = self._get_adjustment_factor(market_condition)
                    st.write(f"閾値調整: {adjustment}")
                
                # 最新の評価結果（仮想）
                st.write("状態: 監視中")
            
            with col4:
                if st.button("📝", key=f"edit_{alert_id}", help="編集"):
                    st.info("編集機能は実装予定")
                
                if st.button("🗑️", key=f"delete_{alert_id}", help="削除"):
                    del alert_system.alerts[alert_id]
                    st.success("アラートを削除しました")
                    st.rerun()
        
        st.markdown("---")
    
    def _display_alert_analytics(self):
        """アラート分析画面"""
        st.markdown("### 📊 アラート履歴・分析")
        
        alert_system = st.session_state.intelligent_alert_system
        
        # フィルター
        col1, col2, col3 = st.columns(3)
        
        with col1:
            period = st.selectbox("期間", ["過去1時間", "過去24時間", "過去7日間"])
        
        with col2:
            priority_filter = st.selectbox(
                "優先度",
                ["全て", "緊急のみ", "高以上", "中以上"]
            )
        
        with col3:
            symbol_filter = st.selectbox(
                "銘柄",
                ["全て"] + list(set(a['symbol'] for a in alert_system.alert_history))
            )
        
        # 統計表示
        filtered_history = self._filter_alert_history(
            alert_system.alert_history, period, priority_filter, symbol_filter
        )
        
        if filtered_history:
            # 統計メトリクス
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("総発火数", len(filtered_history))
            
            with col2:
                critical_count = sum(1 for a in filtered_history 
                                   if a['priority'] == AlertPriority.CRITICAL)
                st.metric("緊急アラート", critical_count)
            
            with col3:
                # ノイズフィルタリング率
                if hasattr(alert_system, '_filtered_count'):
                    filter_rate = (alert_system._filtered_count / 
                                 (len(filtered_history) + alert_system._filtered_count) * 100)
                    st.metric("フィルタリング率", f"{filter_rate:.1f}%")
                else:
                    st.metric("フィルタリング率", "N/A")
            
            with col4:
                unique_symbols = len(set(a['symbol'] for a in filtered_history))
                st.metric("発火銘柄数", unique_symbols)
            
            # 時系列チャート
            self._display_alert_timeline_chart(filtered_history)
            
            # 優先度別分布
            self._display_priority_distribution(filtered_history)
            
            # 最近のアラート詳細
            self._display_recent_alert_details(filtered_history)
        else:
            st.info("指定された条件に一致するアラート履歴がありません")
    
    def _analyze_market_conditions(self) -> Dict[str, MarketCondition]:
        """市場状況を分析"""
        conditions = {}
        
        if not self.data_collector:
            # ダミーデータ
            for symbol in st.session_state.get('watchlist', []):
                conditions[symbol] = np.random.choice(list(MarketCondition))
        else:
            # 実際のデータ分析
            alert_system = st.session_state.intelligent_alert_system
            for symbol in st.session_state.get('watchlist', []):
                try:
                    # データ取得
                    data = self.data_collector.get_stock_data(symbol, period="1mo")
                    if data is not None and len(data) > 0:
                        condition = alert_system.analyze_market_condition(data, symbol)
                        conditions[symbol] = condition
                except Exception as e:
                    logger.error(f"Failed to analyze {symbol}: {str(e)}")
                    conditions[symbol] = MarketCondition.NORMAL
        
        return conditions
    
    def _get_condition_display(self, condition: MarketCondition) -> str:
        """市場状況の表示文字列を取得"""
        displays = {
            MarketCondition.EXTREME_VOLATILITY: "🔴 極端な変動",
            MarketCondition.HIGH_VOLATILITY: "🟠 高変動",
            MarketCondition.NORMAL: "🟢 通常",
            MarketCondition.LOW_VOLATILITY: "🔵 低変動",
            MarketCondition.CONSOLIDATION: "⚪ レンジ"
        }
        return displays.get(condition, "不明")
    
    def _get_adjustment_factor(self, condition: MarketCondition) -> str:
        """調整係数の表示文字列を取得"""
        factors = {
            MarketCondition.EXTREME_VOLATILITY: "×2.0",
            MarketCondition.HIGH_VOLATILITY: "×1.5",
            MarketCondition.NORMAL: "×1.0",
            MarketCondition.LOW_VOLATILITY: "×0.8",
            MarketCondition.CONSOLIDATION: "×0.6"
        }
        return factors.get(condition, "×1.0")
    
    def _update_market_conditions(self):
        """市場状況を更新"""
        alert_system = st.session_state.intelligent_alert_system
        market_conditions = self._analyze_market_conditions()
        
        # 各銘柄の閾値を調整
        for symbol, condition in market_conditions.items():
            if st.session_state.alert_settings['enable_dynamic_adjustment']:
                alert_system.adjust_thresholds(symbol, condition)
    
    def _filter_alert_history(self, history: List[Dict], 
                            period: str, priority: str, symbol: str) -> List[Dict]:
        """アラート履歴をフィルタリング"""
        # 期間フィルター
        period_map = {
            "過去1時間": timedelta(hours=1),
            "過去24時間": timedelta(days=1),
            "過去7日間": timedelta(days=7)
        }
        
        cutoff = datetime.now() - period_map.get(period, timedelta(days=1))
        filtered = [h for h in history if h['timestamp'] > cutoff]
        
        # 優先度フィルター
        if priority == "緊急のみ":
            filtered = [h for h in filtered if h['priority'] == AlertPriority.CRITICAL]
        elif priority == "高以上":
            filtered = [h for h in filtered if h['priority'] in 
                       [AlertPriority.CRITICAL, AlertPriority.HIGH]]
        elif priority == "中以上":
            filtered = [h for h in filtered if h['priority'] in 
                       [AlertPriority.CRITICAL, AlertPriority.HIGH, AlertPriority.MEDIUM]]
        
        # 銘柄フィルター
        if symbol != "全て":
            filtered = [h for h in filtered if h['symbol'] == symbol]
        
        return sorted(filtered, key=lambda x: x['timestamp'], reverse=True)
    
    def _display_alert_timeline_chart(self, history: List[Dict]):
        """アラートタイムラインチャート表示"""
        import plotly.graph_objects as go
        
        st.markdown("#### 📈 アラート発火推移")
        
        # 時間別集計
        hourly_counts = {}
        for alert in history:
            hour_key = alert['timestamp'].replace(minute=0, second=0, microsecond=0)
            if hour_key not in hourly_counts:
                hourly_counts[hour_key] = {'total': 0, 'critical': 0, 'high': 0}
            
            hourly_counts[hour_key]['total'] += 1
            if alert['priority'] == AlertPriority.CRITICAL:
                hourly_counts[hour_key]['critical'] += 1
            elif alert['priority'] == AlertPriority.HIGH:
                hourly_counts[hour_key]['high'] += 1
        
        if hourly_counts:
            hours = sorted(hourly_counts.keys())
            
            fig = go.Figure()
            
            # 総数
            fig.add_trace(go.Scatter(
                x=hours,
                y=[hourly_counts[h]['total'] for h in hours],
                mode='lines+markers',
                name='総アラート数',
                line=dict(color='blue', width=2)
            ))
            
            # 緊急アラート
            fig.add_trace(go.Scatter(
                x=hours,
                y=[hourly_counts[h]['critical'] for h in hours],
                mode='lines+markers',
                name='緊急アラート',
                line=dict(color='red', width=2, dash='dash')
            ))
            
            fig.update_layout(
                title="時間別アラート発火数",
                xaxis_title="時刻",
                yaxis_title="アラート数",
                height=300,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def _display_priority_distribution(self, history: List[Dict]):
        """優先度別分布表示"""
        import plotly.express as px
        
        st.markdown("#### 🎯 優先度別分布")
        
        # 優先度別集計
        priority_counts = {p.value: 0 for p in AlertPriority}
        for alert in history:
            priority_counts[alert['priority'].value] += 1
        
        # 0件を除外
        priority_counts = {k: v for k, v in priority_counts.items() if v > 0}
        
        if priority_counts:
            df = pd.DataFrame([
                {'優先度': k.upper(), '件数': v} 
                for k, v in priority_counts.items()
            ])
            
            fig = px.pie(df, values='件数', names='優先度', 
                        color_discrete_map={
                            'CRITICAL': '#ff1744',
                            'HIGH': '#ff6f00',
                            'MEDIUM': '#ffc107',
                            'LOW': '#4caf50',
                            'INFO': '#2196f3'
                        })
            
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=300)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.dataframe(df, use_container_width=True)
    
    def _display_recent_alert_details(self, history: List[Dict]):
        """最近のアラート詳細表示"""
        st.markdown("#### 📋 最近のアラート詳細")
        
        # 最新10件
        recent = history[:10]
        
        if recent:
            for alert in recent:
                with st.expander(
                    f"{alert['symbol']} - "
                    f"{alert['timestamp'].strftime('%H:%M:%S')} - "
                    f"優先度: {alert['priority'].value.upper()}"
                ):
                    # アラート詳細
                    st.write(f"**アラートID**: {alert['alert_id']}")
                    st.write(f"**市場状況**: {self._get_condition_display(alert.get('market_condition', MarketCondition.NORMAL))}")
                    
                    # 満たされた条件
                    st.write("**満たされた条件**:")
                    for cond in alert['conditions_met']:
                        st.write(f"- {cond['type']}: {cond['value']:.2f} "
                               f"(閾値: {cond['threshold']:.2f})")
                    
                    # データ
                    if 'data' in alert:
                        st.write("**データ**:")
                        data_df = pd.DataFrame([alert['data']])
                        st.dataframe(data_df, use_container_width=True)