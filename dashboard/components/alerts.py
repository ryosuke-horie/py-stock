"""
アラート設定とステータス管理コンポーネント
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json


class AlertComponent:
    """アラート管理コンポーネント"""
    
    def __init__(self):
        """初期化"""
        # セッション状態初期化
        if 'alerts' not in st.session_state:
            st.session_state.alerts = []
        
        if 'alert_history' not in st.session_state:
            st.session_state.alert_history = []
    
    def display(self):
        """アラート管理画面表示"""
        st.subheader("🚨 アラート管理")
        
        # タブ構成
        alert_tab1, alert_tab2, alert_tab3 = st.tabs([
            "⚙️ アラート設定", "📋 アクティブアラート", "📜 アラート履歴"
        ])
        
        with alert_tab1:
            self._display_alert_settings()
        
        with alert_tab2:
            self._display_active_alerts()
        
        with alert_tab3:
            self._display_alert_history()
    
    def _display_alert_settings(self):
        """アラート設定画面"""
        st.markdown("### ⚙️ 新しいアラートを作成")
        
        # アラートタイプ選択
        alert_type = st.selectbox(
            "アラートタイプ",
            ["価格アラート", "シグナルアラート", "ボラティリティアラート", "出来高アラート"],
            help="設定するアラートの種類を選択"
        )
        
        if alert_type == "価格アラート":
            self._create_price_alert()
        elif alert_type == "シグナルアラート":
            self._create_signal_alert()
        elif alert_type == "ボラティリティアラート":
            self._create_volatility_alert()
        elif alert_type == "出来高アラート":
            self._create_volume_alert()
        
        # 通知設定
        st.markdown("---")
        st.markdown("### 📢 通知設定")
        
        col1, col2 = st.columns(2)
        
        with col1:
            notification_sound = st.checkbox("サウンド通知", value=True)
            popup_notification = st.checkbox("ポップアップ通知", value=True)
        
        with col2:
            email_notification = st.checkbox("メール通知", value=False)
            if email_notification:
                email_address = st.text_input("メールアドレス", placeholder="example@email.com")
        
        # 通知頻度設定
        notification_frequency = st.selectbox(
            "通知頻度",
            ["即座", "1分ごと", "5分ごと", "15分ごと"],
            help="同じアラートの通知間隔"
        )
    
    def _create_price_alert(self):
        """価格アラート作成"""
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input("銘柄コード", placeholder="例: 7203.T")
            target_price = st.number_input("目標価格", min_value=0.0, step=1.0)
        
        with col2:
            condition = st.selectbox("条件", ["以上", "以下", "到達"])
            priority = st.selectbox("優先度", ["高", "中", "低"], index=1)
        
        comment = st.text_area("コメント（任意）", placeholder="このアラートの目的や注意事項")
        
        if st.button("価格アラートを作成", type="primary"):
            if symbol and target_price > 0:
                alert = {
                    'id': len(st.session_state.alerts) + 1,
                    'type': '価格アラート',
                    'symbol': symbol.upper(),
                    'target_price': target_price,
                    'condition': condition,
                    'priority': priority,
                    'comment': comment,
                    'created_at': datetime.now(),
                    'is_active': True,
                    'triggered_count': 0
                }
                st.session_state.alerts.append(alert)
                st.success(f"✅ {symbol} の価格アラートを作成しました")
                st.rerun()
            else:
                st.error("銘柄コードと目標価格を入力してください")
    
    def _create_signal_alert(self):
        """シグナルアラート作成"""
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input("銘柄コード", placeholder="例: 7203.T", key="signal_symbol")
            signal_type = st.selectbox("シグナルタイプ", ["BUY", "SELL", "両方"])
        
        with col2:
            min_strength = st.slider("最小強度", 0, 100, 70, key="signal_strength")
            min_confidence = st.slider("最小信頼度", 0.0, 1.0, 0.7, key="signal_confidence")
        
        strategy_filter = st.multiselect(
            "戦略フィルター（任意）",
            ["RSI戦略", "MACD戦略", "ボリンジャー戦略", "複合戦略"],
            help="特定の戦略のシグナルのみアラート"
        )
        
        if st.button("シグナルアラートを作成", type="primary"):
            if symbol:
                alert = {
                    'id': len(st.session_state.alerts) + 1,
                    'type': 'シグナルアラート',
                    'symbol': symbol.upper(),
                    'signal_type': signal_type,
                    'min_strength': min_strength,
                    'min_confidence': min_confidence,
                    'strategy_filter': strategy_filter,
                    'created_at': datetime.now(),
                    'is_active': True,
                    'triggered_count': 0
                }
                st.session_state.alerts.append(alert)
                st.success(f"✅ {symbol} のシグナルアラートを作成しました")
                st.rerun()
            else:
                st.error("銘柄コードを入力してください")
    
    def _create_volatility_alert(self):
        """ボラティリティアラート作成"""
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input("銘柄コード", placeholder="例: 7203.T", key="vol_symbol")
            volatility_threshold = st.number_input("ボラティリティ閾値（%）", min_value=0.0, max_value=50.0, value=5.0, step=0.5)
        
        with col2:
            timeframe = st.selectbox("時間枠", ["1時間", "4時間", "1日"])
            condition = st.selectbox("条件", ["以上", "以下"], key="vol_condition")
        
        if st.button("ボラティリティアラートを作成", type="primary"):
            if symbol:
                alert = {
                    'id': len(st.session_state.alerts) + 1,
                    'type': 'ボラティリティアラート',
                    'symbol': symbol.upper(),
                    'volatility_threshold': volatility_threshold,
                    'timeframe': timeframe,
                    'condition': condition,
                    'created_at': datetime.now(),
                    'is_active': True,
                    'triggered_count': 0
                }
                st.session_state.alerts.append(alert)
                st.success(f"✅ {symbol} のボラティリティアラートを作成しました")
                st.rerun()
            else:
                st.error("銘柄コードを入力してください")
    
    def _create_volume_alert(self):
        """出来高アラート作成"""
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input("銘柄コード", placeholder="例: 7203.T", key="volume_symbol")
            volume_multiplier = st.number_input("平均出来高の何倍", min_value=1.0, max_value=10.0, value=2.0, step=0.1)
        
        with col2:
            reference_period = st.selectbox("基準期間", ["5日平均", "10日平均", "20日平均"])
            priority = st.selectbox("優先度", ["高", "中", "低"], index=1, key="volume_priority")
        
        if st.button("出来高アラートを作成", type="primary"):
            if symbol:
                alert = {
                    'id': len(st.session_state.alerts) + 1,
                    'type': '出来高アラート',
                    'symbol': symbol.upper(),
                    'volume_multiplier': volume_multiplier,
                    'reference_period': reference_period,
                    'priority': priority,
                    'created_at': datetime.now(),
                    'is_active': True,
                    'triggered_count': 0
                }
                st.session_state.alerts.append(alert)
                st.success(f"✅ {symbol} の出来高アラートを作成しました")
                st.rerun()
            else:
                st.error("銘柄コードを入力してください")
    
    def _display_active_alerts(self):
        """アクティブアラート表示"""
        st.markdown("### 📋 アクティブアラート")
        
        active_alerts = [alert for alert in st.session_state.alerts if alert.get('is_active', True)]
        
        if not active_alerts:
            st.info("アクティブなアラートがありません")
            return
        
        # アラート統計
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("総アラート数", len(active_alerts))
        
        with col2:
            high_priority = len([a for a in active_alerts if a.get('priority') == '高'])
            st.metric("高優先度", high_priority)
        
        with col3:
            price_alerts = len([a for a in active_alerts if a.get('type') == '価格アラート'])
            st.metric("価格アラート", price_alerts)
        
        with col4:
            signal_alerts = len([a for a in active_alerts if a.get('type') == 'シグナルアラート'])
            st.metric("シグナルアラート", signal_alerts)
        
        # アラート一覧
        st.markdown("#### 📄 アラート一覧")
        
        for i, alert in enumerate(active_alerts):
            self._display_alert_card(alert, i)
        
        # 一括操作
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔇 全てのアラートを無効化"):
                for alert in st.session_state.alerts:
                    alert['is_active'] = False
                st.success("全てのアラートを無効化しました")
                st.rerun()
        
        with col2:
            if st.button("🗑️ 無効なアラートを削除"):
                st.session_state.alerts = [a for a in st.session_state.alerts if a.get('is_active', True)]
                st.success("無効なアラートを削除しました")
                st.rerun()
        
        with col3:
            # アラート設定のエクスポート
            if st.button("📥 設定をエクスポート"):
                export_data = json.dumps(st.session_state.alerts, default=str, indent=2)
                st.download_button(
                    label="設定ファイルをダウンロード",
                    data=export_data,
                    file_name=f"alerts_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    
    def _display_alert_card(self, alert: Dict[str, Any], index: int):
        """アラートカード表示"""
        # 優先度に応じた色設定
        priority_colors = {
            '高': '🔴',
            '中': '🟡', 
            '低': '🟢'
        }
        
        priority_icon = priority_colors.get(alert.get('priority', '中'), '🟡')
        
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                st.markdown(f"**{priority_icon} {alert['type']}**")
                st.write(f"銘柄: {alert['symbol']}")
                
                if alert['type'] == '価格アラート':
                    st.write(f"目標: ¥{alert['target_price']:.2f} {alert['condition']}")
                elif alert['type'] == 'シグナルアラート':
                    st.write(f"タイプ: {alert['signal_type']}, 強度≥{alert['min_strength']}")
                elif alert['type'] == 'ボラティリティアラート':
                    st.write(f"閾値: {alert['volatility_threshold']}% {alert['condition']}")
                elif alert['type'] == '出来高アラート':
                    st.write(f"倍率: {alert['volume_multiplier']}x {alert['reference_period']}")
            
            with col2:
                st.write(f"作成: {alert['created_at'].strftime('%m/%d %H:%M')}")
                st.write(f"発火回数: {alert.get('triggered_count', 0)}回")
            
            with col3:
                # 現在の状況表示（仮想データ）
                if alert['type'] == '価格アラート':
                    current_price = 2150.0  # 仮の現在価格
                    diff = abs(current_price - alert['target_price'])
                    diff_pct = (diff / alert['target_price']) * 100
                    st.write(f"現在価格: ¥{current_price:.2f}")
                    st.write(f"差額: {diff_pct:.1f}%")
                else:
                    st.write("ステータス: 監視中")
            
            with col4:
                # アラート操作ボタン
                if st.button("🔇", key=f"disable_{index}", help="無効化"):
                    st.session_state.alerts[self._find_alert_index(alert['id'])]['is_active'] = False
                    st.success("アラートを無効化しました")
                    st.rerun()
                
                if st.button("🗑️", key=f"delete_{index}", help="削除"):
                    st.session_state.alerts = [a for a in st.session_state.alerts if a['id'] != alert['id']]
                    st.success("アラートを削除しました")
                    st.rerun()
        
        st.markdown("---")
    
    def _display_alert_history(self):
        """アラート履歴表示"""
        st.markdown("### 📜 アラート発火履歴")
        
        # フィルター設定
        col1, col2, col3 = st.columns(3)
        
        with col1:
            history_period = st.selectbox(
                "表示期間",
                ["今日", "過去3日", "過去7日", "過去30日"],
                index=1
            )
        
        with col2:
            alert_type_filter = st.selectbox(
                "アラートタイプ",
                ["全て", "価格アラート", "シグナルアラート", "ボラティリティアラート", "出来高アラート"],
                index=0
            )
        
        with col3:
            priority_filter = st.selectbox(
                "優先度",
                ["全て", "高", "中", "低"],
                index=0
            )
        
        # ダミーの履歴データ生成（実際の実装では実データを使用）
        if not st.session_state.alert_history:
            self._generate_dummy_alert_history()
        
        # フィルタリング
        filtered_history = self._filter_alert_history(
            st.session_state.alert_history,
            history_period,
            alert_type_filter,
            priority_filter
        )
        
        if not filtered_history:
            st.info("条件に一致するアラート履歴がありません")
            return
        
        # 履歴統計
        self._display_history_statistics(filtered_history)
        
        # 履歴テーブル
        self._display_history_table(filtered_history)
        
        # 履歴チャート
        self._display_history_chart(filtered_history)
    
    def _generate_dummy_alert_history(self):
        """ダミーアラート履歴生成"""
        import random
        
        alert_types = ['価格アラート', 'シグナルアラート', 'ボラティリティアラート', '出来高アラート']
        priorities = ['高', '中', '低']
        symbols = ['7203.T', '6758.T', '9984.T', 'AAPL', 'MSFT']
        
        history = []
        for i in range(50):
            triggered_time = datetime.now() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            history.append({
                'id': i + 1,
                'alert_type': random.choice(alert_types),
                'symbol': random.choice(symbols),
                'priority': random.choice(priorities),
                'triggered_time': triggered_time,
                'message': f"アラート発火: {random.choice(symbols)}",
                'resolved': random.choice([True, False]),
                'resolution_time': triggered_time + timedelta(minutes=random.randint(1, 60)) if random.choice([True, False]) else None
            })
        
        st.session_state.alert_history = history
    
    def _filter_alert_history(self, history: List[Dict], period: str, alert_type: str, priority: str) -> List[Dict]:
        """アラート履歴フィルタリング"""
        # 期間フィルター
        period_days = {
            "今日": 1,
            "過去3日": 3,
            "過去7日": 7,
            "過去30日": 30
        }
        
        cutoff_date = datetime.now() - timedelta(days=period_days[period])
        filtered = [h for h in history if h['triggered_time'] >= cutoff_date]
        
        # タイプフィルター
        if alert_type != "全て":
            filtered = [h for h in filtered if h['alert_type'] == alert_type]
        
        # 優先度フィルター
        if priority != "全て":
            filtered = [h for h in filtered if h['priority'] == priority]
        
        return sorted(filtered, key=lambda x: x['triggered_time'], reverse=True)
    
    def _display_history_statistics(self, history: List[Dict]):
        """履歴統計表示"""
        total_alerts = len(history)
        resolved_alerts = len([h for h in history if h.get('resolved', False)])
        high_priority = len([h for h in history if h['priority'] == '高'])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("総発火数", total_alerts)
        
        with col2:
            resolution_rate = (resolved_alerts / total_alerts * 100) if total_alerts > 0 else 0
            st.metric("解決率", f"{resolution_rate:.1f}%")
        
        with col3:
            st.metric("高優先度", high_priority)
        
        with col4:
            avg_resolution_time = self._calculate_avg_resolution_time(history)
            st.metric("平均解決時間", avg_resolution_time)
    
    def _display_history_table(self, history: List[Dict]):
        """履歴テーブル表示"""
        st.markdown("#### 📄 発火履歴")
        
        # DataFrame作成
        df_data = []
        for h in history[:20]:  # 最新20件
            df_data.append({
                '日時': h['triggered_time'].strftime('%m/%d %H:%M'),
                'タイプ': h['alert_type'],
                '銘柄': h['symbol'],
                '優先度': h['priority'],
                'メッセージ': h['message'],
                '状態': '解決済み' if h.get('resolved', False) else '未解決'
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            
            # スタイル適用
            def style_priority(val):
                colors = {
                    '高': 'background-color: #ffebee; color: #c62828',
                    '中': 'background-color: #fff3e0; color: #f57c00',
                    '低': 'background-color: #e8f5e8; color: #2e7d32'
                }
                return colors.get(val, '')
            
            def style_status(val):
                if val == '解決済み':
                    return 'background-color: #e8f5e8; color: #2e7d32'
                else:
                    return 'background-color: #ffebee; color: #c62828'
            
            styled_df = df.style.applymap(style_priority, subset=['優先度']) \
                               .applymap(style_status, subset=['状態'])
            
            st.dataframe(styled_df, use_container_width=True)
    
    def _display_history_chart(self, history: List[Dict]):
        """履歴チャート表示"""
        st.markdown("#### 📊 発火頻度推移")
        
        # 日別発火数集計
        daily_counts = {}
        for h in history:
            date_key = h['triggered_time'].date()
            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        
        if daily_counts:
            dates = sorted(daily_counts.keys())
            counts = [daily_counts[date] for date in dates]
            
            import plotly.graph_objects as go
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates,
                y=counts,
                mode='lines+markers',
                name='アラート発火数',
                line=dict(color='red', width=2),
                marker=dict(size=8)
            ))
            
            fig.update_layout(
                title="日別アラート発火数",
                xaxis_title="日付",
                yaxis_title="発火数",
                height=300
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def _calculate_avg_resolution_time(self, history: List[Dict]) -> str:
        """平均解決時間計算"""
        resolution_times = []
        for h in history:
            if h.get('resolved', False) and h.get('resolution_time'):
                duration = h['resolution_time'] - h['triggered_time']
                resolution_times.append(duration.total_seconds() / 60)  # 分単位
        
        if resolution_times:
            avg_minutes = sum(resolution_times) / len(resolution_times)
            if avg_minutes > 60:
                return f"{avg_minutes/60:.1f}時間"
            else:
                return f"{avg_minutes:.0f}分"
        else:
            return "N/A"
    
    def _find_alert_index(self, alert_id: int) -> int:
        """アラートIDからインデックス検索"""
        for i, alert in enumerate(st.session_state.alerts):
            if alert['id'] == alert_id:
                return i
        return -1
    
    def trigger_alert(self, alert_data: Dict[str, Any]):
        """アラート発火（外部から呼び出し）"""
        # アラート履歴に追加
        history_entry = {
            'id': len(st.session_state.alert_history) + 1,
            'alert_type': alert_data.get('type', 'Unknown'),
            'symbol': alert_data.get('symbol', 'Unknown'),
            'priority': alert_data.get('priority', '中'),
            'triggered_time': datetime.now(),
            'message': alert_data.get('message', 'アラートが発火しました'),
            'resolved': False,
            'resolution_time': None
        }
        
        st.session_state.alert_history.append(history_entry)
        
        # 該当アラートの発火回数更新
        alert_id = alert_data.get('alert_id')
        if alert_id:
            for alert in st.session_state.alerts:
                if alert['id'] == alert_id:
                    alert['triggered_count'] = alert.get('triggered_count', 0) + 1
                    break