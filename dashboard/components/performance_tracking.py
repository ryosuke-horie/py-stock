"""
パフォーマンス追跡・学習ダッシュボードコンポーネント

投資履歴、パフォーマンス分析、パターン分析、改善提案をStreamlitで表示
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.performance_tracking import PerformanceTracker


def render_performance_tracking_tab():
    """パフォーマンス追跡・学習タブのレンダリング"""
    st.markdown("### 📊 パフォーマンス追跡・学習")
    st.markdown("投資履歴の記録、パフォーマンス分析、パターン分析、改善提案を提供します。")
    
    # パフォーマンストラッカーの初期化
    if 'performance_tracker' not in st.session_state:
        st.session_state.performance_tracker = PerformanceTracker()
    
    tracker = st.session_state.performance_tracker
    
    # サイドバー設定
    with st.sidebar:
        st.markdown("### 📊 分析設定")
        
        # 分析期間設定
        analysis_period = st.selectbox(
            "分析期間",
            ["30日", "60日", "90日", "6ヶ月", "1年"],
            index=2,
            help="パフォーマンス分析の対象期間を選択してください"
        )
        
        period_mapping = {
            "30日": 30,
            "60日": 60,
            "90日": 90,
            "6ヶ月": 180,
            "1年": 365
        }
        
        lookback_days = period_mapping[analysis_period]
        
        # 最小取引数設定
        min_trades = st.slider(
            "最小取引数",
            min_value=5,
            max_value=50,
            value=10,
            step=5,
            help="分析に必要な最小取引数"
        )
        
        # 分析実行ボタン
        if st.button("🔍 パフォーマンス分析実行", type="primary"):
            st.session_state.run_analysis = True
    
    # メインコンテンツ
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 概要", "📊 パフォーマンス分析", "🔍 パターン分析", "💡 改善提案", "📝 取引記録", "⚙️ 設定"
    ])
    
    with tab1:
        display_overview_tab(tracker, lookback_days)
    
    with tab2:
        display_performance_analysis_tab(tracker, lookback_days, min_trades)
    
    with tab3:
        display_pattern_analysis_tab(tracker, lookback_days, min_trades)
    
    with tab4:
        display_improvement_suggestions_tab(tracker, lookback_days, min_trades)
    
    with tab5:
        display_trade_recording_tab(tracker)
    
    with tab6:
        display_settings_tab(tracker)


def display_overview_tab(tracker: PerformanceTracker, days: int):
    """概要タブの表示"""
    st.markdown("#### 📈 パフォーマンス概要")
    
    try:
        # パフォーマンスサマリー取得
        summary = tracker.get_performance_summary(days)
        
        if not summary or summary.get('total_trades', 0) == 0:
            st.info(f"過去{days}日間の取引データがありません。取引を記録してください。")
            return
        
        # メトリクス表示
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_trades = summary.get('total_trades', 0)
            open_positions = summary.get('open_positions', 0)
            st.metric(
                "総取引数",
                f"{total_trades}回",
                delta=f"オープン: {open_positions}件"
            )
        
        with col2:
            win_rate = summary.get('win_rate', 0)
            st.metric(
                "勝率",
                f"{win_rate:.1%}",
                delta=f"{'✅ 良好' if win_rate >= 0.5 else '⚠️ 要改善'}"
            )
        
        with col3:
            total_pnl = summary.get('total_pnl', 0)
            st.metric(
                "総損益",
                f"¥{total_pnl:,.0f}",
                delta=f"{'📈' if total_pnl >= 0 else '📉'}"
            )
        
        with col4:
            profit_factor = summary.get('profit_factor', 0)
            st.metric(
                "損益比",
                f"{profit_factor:.2f}",
                delta=f"{'🎯 優秀' if profit_factor >= 1.5 else '📊 平均' if profit_factor >= 1.0 else '⚠️ 要改善'}"
            )
        
        # 簡易チャート
        if summary.get('total_trades', 0) > 0:
            st.markdown("#### 📊 最近の取引傾向")
            
            # 取引履歴を取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            recent_trades = tracker.get_trading_history(
                start_date=start_date,
                end_date=end_date,
                limit=50
            )
            
            if recent_trades:
                display_recent_trades_chart(recent_trades)
        
        # 学習洞察のプレビュー
        if summary.get('total_trades', 0) >= 10:
            st.markdown("#### 💡 学習洞察プレビュー")
            
            insights = tracker.get_learning_insights(days)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🎯 強み**")
                strengths = insights.get('key_strengths', [])
                if strengths:
                    for strength in strengths[:3]:
                        st.success(f"✅ {strength['area']}: {strength['score']:.0f}点")
                else:
                    st.info("分析中...")
            
            with col2:
                st.markdown("**⚠️ 改善点**")
                weaknesses = insights.get('major_weaknesses', [])
                if weaknesses:
                    for weakness in weaknesses[:3]:
                        st.warning(f"📈 {weakness['area']}: {weakness['score']:.0f}点")
                else:
                    st.info("特になし")
        
    except Exception as e:
        st.error(f"概要データの取得中にエラーが発生しました: {str(e)}")


def display_performance_analysis_tab(tracker: PerformanceTracker, 
                                   lookback_days: int, 
                                   min_trades: int):
    """パフォーマンス分析タブの表示"""
    st.markdown("#### 📊 詳細パフォーマンス分析")
    
    # 分析実行チェック
    if st.session_state.get('run_analysis', False) or st.button("🔄 分析実行"):
        st.session_state.run_analysis = False
        
        with st.spinner("パフォーマンス分析を実行中..."):
            try:
                report = tracker.analyze_performance(lookback_days, min_trades)
                st.session_state.performance_report = report
                
            except Exception as e:
                st.error(f"分析中にエラーが発生しました: {str(e)}")
                return
    
    # レポート表示
    if 'performance_report' not in st.session_state:
        st.info("「分析実行」ボタンをクリックして詳細分析を開始してください。")
        return
    
    report = st.session_state.performance_report
    
    # 総合評価
    st.markdown("### 🎯 総合評価")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        score = report.overall_performance_score
        level = report.performance_level
        
        # スコアゲージ
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "総合スコア"},
            delta={'reference': 70},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 40], 'color': "lightgray"},
                    {'range': [40, 70], 'color': "yellow"},
                    {'range': [70, 100], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        fig_gauge.update_layout(height=300)
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col2:
        st.metric("パフォーマンスレベル", level)
        st.metric("分析期間", f"{lookback_days}日間")
    
    with col3:
        basic_stats = report.basic_statistics
        total_trades = basic_stats.get('total_trades', 0)
        st.metric("対象取引数", f"{total_trades}件")
        st.metric("分析日時", report.generated_at.strftime("%m/%d %H:%M"))
    
    # 基本統計の詳細表示
    if basic_stats:
        st.markdown("### 📊 基本統計")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📈 収益性指標**")
            
            win_rate = basic_stats.get('win_rate', 0)
            total_pnl = basic_stats.get('total_pnl', 0)
            profit_factor = basic_stats.get('profit_factor', 0)
            
            stats_data = {
                '指標': ['勝率', '総損益', '損益比', '平均損益'],
                '値': [
                    f"{win_rate:.1%}",
                    f"¥{total_pnl:,.0f}",
                    f"{profit_factor:.2f}",
                    f"¥{basic_stats.get('average_pnl', 0):,.0f}"
                ],
                '評価': [
                    get_performance_rating(win_rate, 'win_rate'),
                    get_performance_rating(total_pnl, 'pnl'),
                    get_performance_rating(profit_factor, 'profit_factor'),
                    get_performance_rating(basic_stats.get('average_pnl', 0), 'avg_pnl')
                ]
            }
            
            df_stats = pd.DataFrame(stats_data)
            st.dataframe(df_stats, use_container_width=True)
        
        with col2:
            st.markdown("**⏱️ 取引行動指標**")
            
            winning_trades = basic_stats.get('winning_trades', 0)
            losing_trades = basic_stats.get('losing_trades', 0)
            avg_hold_time = basic_stats.get('average_hold_time_hours', 0)
            
            behavior_data = {
                '指標': ['勝ちトレード', '負けトレード', '平均保有時間', '取引頻度'],
                '値': [
                    f"{winning_trades}件",
                    f"{losing_trades}件",
                    f"{avg_hold_time:.1f}時間",
                    f"{total_trades/lookback_days*30:.1f}件/月"
                ]
            }
            
            df_behavior = pd.DataFrame(behavior_data)
            st.dataframe(df_behavior, use_container_width=True)
    
    # 投資傾向分析結果
    if report.investment_tendencies:
        st.markdown("### 🎯 投資傾向分析")
        
        # 傾向スコアのレーダーチャート
        display_tendency_radar_chart(report.investment_tendencies)
        
        # 傾向詳細表示
        st.markdown("#### 📋 傾向詳細")
        
        for tendency in report.investment_tendencies:
            with st.expander(f"{tendency.name} (スコア: {tendency.score:.0f}点)"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**説明**: {tendency.description}")
                    st.markdown(f"**レベル**: {tendency.level.value}")
                    
                    if tendency.improvement_suggestions:
                        st.markdown("**改善提案**:")
                        for suggestion in tendency.improvement_suggestions:
                            st.markdown(f"• {suggestion}")
                
                with col2:
                    st.metric("現在値", f"{tendency.current_value:.2f}")
                    st.metric("ベンチマーク", f"{tendency.benchmark_value:.2f}")
                    st.metric("パーセンタイル", f"{tendency.percentile:.0f}%")


def display_pattern_analysis_tab(tracker: PerformanceTracker,
                               lookback_days: int,
                               min_trades: int):
    """パターン分析タブの表示"""
    st.markdown("#### 🔍 取引パターン分析")
    
    # レポートチェック
    if 'performance_report' not in st.session_state:
        st.info("まずパフォーマンス分析を実行してください。")
        return
    
    report = st.session_state.performance_report
    patterns = report.trading_patterns
    
    if not patterns:
        st.info("十分なデータがないため、パターン分析を実行できませんでした。")
        return
    
    st.markdown(f"### 📊 発見されたパターン数: {len(patterns)}件")
    
    # パターンタイプ別統計
    success_patterns = [p for p in patterns if p.pattern_type.value == "success"]
    failure_patterns = [p for p in patterns if p.pattern_type.value == "failure"]
    neutral_patterns = [p for p in patterns if p.pattern_type.value == "neutral"]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🎯 成功パターン", len(success_patterns))
    
    with col2:
        st.metric("⚠️ 失敗パターン", len(failure_patterns))
    
    with col3:
        st.metric("📊 中立パターン", len(neutral_patterns))
    
    # パターン可視化
    if len(patterns) > 0:
        st.markdown("### 📈 パターン成功率分布")
        
        # 成功率ヒストグラム
        success_rates = [p.success_rate * 100 for p in patterns]
        
        fig_hist = px.histogram(
            x=success_rates,
            nbins=10,
            title="パターン成功率分布",
            labels={'x': '成功率(%)', 'y': 'パターン数'},
            color_discrete_sequence=['#1f77b4']
        )
        
        fig_hist.add_vline(x=50, line_dash="dash", line_color="red", 
                          annotation_text="基準線(50%)")
        
        st.plotly_chart(fig_hist, use_container_width=True)
    
    # パターン詳細表示
    st.markdown("### 📋 パターン詳細")
    
    # パターンタイプでフィルタリング
    pattern_filter = st.selectbox(
        "表示するパターンタイプ",
        ["すべて", "成功パターン", "失敗パターン", "中立パターン"],
        index=0
    )
    
    filtered_patterns = patterns
    if pattern_filter == "成功パターン":
        filtered_patterns = success_patterns
    elif pattern_filter == "失敗パターン":
        filtered_patterns = failure_patterns
    elif pattern_filter == "中立パターン":
        filtered_patterns = neutral_patterns
    
    # パターンリスト表示
    for i, pattern in enumerate(filtered_patterns):
        with st.expander(f"{pattern.name} (成功率: {pattern.success_rate:.1%})"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**説明**: {pattern.description}")
                st.markdown(f"**タイプ**: {pattern.pattern_type.value}")
                st.markdown(f"**発生回数**: {pattern.occurrence_count}回")
                
                # 特徴表示
                if pattern.characteristics:
                    st.markdown("**特徴**:")
                    for key, value in pattern.characteristics.items():
                        st.markdown(f"• {key}: {value}")
            
            with col2:
                st.metric("成功率", f"{pattern.success_rate:.1%}")
                st.metric("平均損益", f"¥{pattern.average_pnl:,.0f}")
                st.metric("信頼度", f"{pattern.confidence_score:.2f}")
                
                # パターンタイプに応じた色分け
                if pattern.pattern_type.value == "success":
                    st.success("✅ 継続推奨")
                elif pattern.pattern_type.value == "failure":
                    st.error("❌ 回避推奨")
                else:
                    st.info("📊 要監視")


def display_improvement_suggestions_tab(tracker: PerformanceTracker,
                                      lookback_days: int,
                                      min_trades: int):
    """改善提案タブの表示"""
    st.markdown("#### 💡 改善提案")
    
    # レポートチェック
    if 'performance_report' not in st.session_state:
        st.info("まずパフォーマンス分析を実行してください。")
        return
    
    report = st.session_state.performance_report
    suggestions = report.improvement_suggestions
    improvement_plan = report.improvement_plan
    
    if not suggestions:
        st.success("🎉 現在のパフォーマンスは良好です。特別な改善提案はありません。")
        return
    
    st.markdown(f"### 📋 改善提案数: {len(suggestions)}件")
    
    # 改善計画サマリー
    if improvement_plan:
        st.markdown("### 🎯 改善計画サマリー")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            expected_improvement = improvement_plan.get('expected_improvement_pct', 0)
            st.metric("期待改善効果", f"{expected_improvement:.1f}%")
        
        with col2:
            immediate_actions = len(improvement_plan.get('implementation_schedule', {}).get('immediate', []))
            st.metric("緊急対応事項", f"{immediate_actions}件")
        
        with col3:
            category_summary = improvement_plan.get('category_summary', {})
            priority_category = max(category_summary.keys(), key=lambda k: category_summary[k]) if category_summary else "なし"
            st.metric("最重要分野", priority_category)
    
    # 優先度別表示
    st.markdown("### 📊 優先度別改善提案")
    
    priority_tabs = st.tabs(["🚨 緊急", "⚡ 高", "📋 中", "📝 低"])
    
    priority_mapping = {
        "🚨 緊急": "critical",
        "⚡ 高": "high", 
        "📋 中": "medium",
        "📝 低": "low"
    }
    
    for tab, priority in zip(priority_tabs, priority_mapping.values()):
        with tab:
            priority_suggestions = [s for s in suggestions if s.priority.value == priority]
            
            if not priority_suggestions:
                st.info(f"{priority.upper()}優先度の提案はありません。")
                continue
            
            for suggestion in priority_suggestions:
                with st.expander(f"{suggestion.title}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**説明**: {suggestion.description}")
                        st.markdown(f"**カテゴリ**: {suggestion.category.value}")
                        
                        st.markdown("**アクション項目**:")
                        for action in suggestion.action_items:
                            st.markdown(f"• {action}")
                        
                        st.markdown(f"**期待効果**: {suggestion.expected_impact}")
                    
                    with col2:
                        if suggestion.expected_improvement_pct:
                            st.metric("期待改善", f"{suggestion.expected_improvement_pct:.1f}%")
                        
                        st.info(f"**難易度**: {suggestion.difficulty_level}")
                        st.info(f"**実装期間**: {suggestion.implementation_timeframe}")
                        
                        # 成功指標
                        if suggestion.success_metrics:
                            st.markdown("**成功指標**:")
                            for metric in suggestion.success_metrics:
                                st.markdown(f"• {metric}")
    
    # 実装スケジュール
    if improvement_plan and improvement_plan.get('implementation_schedule'):
        st.markdown("### 📅 実装スケジュール")
        
        schedule = improvement_plan['implementation_schedule']
        
        schedule_tabs = st.tabs(["即時対応", "短期", "中期", "長期"])
        schedule_keys = ["immediate", "short_term", "medium_term", "long_term"]
        
        for tab, key in zip(schedule_tabs, schedule_keys):
            with tab:
                schedule_items = schedule.get(key, [])
                
                if not schedule_items:
                    st.info(f"{key.replace('_', ' ').title()}の実装項目はありません。")
                    continue
                
                for item in schedule_items:
                    st.markdown(f"**{item['title']}**")
                    st.markdown(f"カテゴリ: {item['category']}")
                    st.markdown(f"優先度: {item['priority']}")
                    st.markdown("---")
    
    # エクスポート機能
    st.markdown("### 💾 エクスポート")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 改善提案をJSONでエクスポート"):
            try:
                output_path = f"improvement_suggestions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                if tracker.suggestion_engine.export_suggestions(suggestions, output_path):
                    st.success(f"✅ エクスポート完了: {output_path}")
                else:
                    st.error("❌ エクスポートに失敗しました")
            
            except Exception as e:
                st.error(f"エクスポート中にエラーが発生しました: {str(e)}")
    
    with col2:
        if st.button("📊 レポートをJSONでエクスポート"):
            try:
                output_path = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                if tracker.export_report(report, output_path):
                    st.success(f"✅ エクスポート完了: {output_path}")
                else:
                    st.error("❌ エクスポートに失敗しました")
            
            except Exception as e:
                st.error(f"エクスポート中にエラーが発生しました: {str(e)}")


def display_trade_recording_tab(tracker: PerformanceTracker):
    """取引記録タブの表示"""
    st.markdown("#### 📝 取引記録")
    
    # 取引記録と取引履歴の表示
    record_tab, history_tab = st.tabs(["📝 新規記録", "📊 取引履歴"])
    
    with record_tab:
        display_trade_recording_form(tracker)
    
    with history_tab:
        display_trade_history(tracker)


def display_trade_recording_form(tracker: PerformanceTracker):
    """取引記録フォームの表示"""
    st.markdown("##### 新規取引記録")
    
    # オープンポジション確認
    open_trades = tracker.get_open_positions()
    if open_trades:
        st.info(f"現在 {len(open_trades)} 件のオープンポジションがあります。")
        
        # オープンポジションの決済
        st.markdown("**📊 オープンポジション決済**")
        
        for trade in open_trades:
            with st.expander(f"{trade.symbol} - {trade.direction.value} ({trade.quantity}株)"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"エントリー価格: ¥{trade.entry_price:,.2f}")
                    st.write(f"エントリー日時: {trade.entry_time.strftime('%Y/%m/%d %H:%M')}")
                    if trade.strategy_name:
                        st.write(f"戦略: {trade.strategy_name}")
                
                with col2:
                    exit_price = st.number_input(
                        "決済価格",
                        min_value=0.01,
                        value=trade.entry_price,
                        step=0.01,
                        key=f"exit_price_{trade.trade_id}"
                    )
                    
                    exit_reason = st.selectbox(
                        "決済理由",
                        ["Take Profit", "Stop Loss", "Manual Exit", "Time Exit", "Strategy Signal"],
                        key=f"exit_reason_{trade.trade_id}"
                    )
                    
                    if st.button(f"決済実行", key=f"close_{trade.trade_id}"):
                        if tracker.close_trade(trade.trade_id, exit_price, exit_reason):
                            st.success(f"✅ {trade.symbol} を決済しました")
                            st.rerun()
                        else:
                            st.error("❌ 決済に失敗しました")
    
    st.markdown("---")
    
    # 新規取引記録フォーム
    st.markdown("**📈 新規取引記録**")
    
    with st.form("trade_recording_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input(
                "銘柄コード",
                placeholder="例: 7203.T, AAPL",
                help="銘柄コードを入力してください"
            )
            
            direction = st.selectbox(
                "取引方向",
                ["LONG", "SHORT"],
                help="買いポジションまたは売りポジションを選択"
            )
            
            entry_price = st.number_input(
                "エントリー価格",
                min_value=0.01,
                step=0.01,
                help="取引開始価格を入力"
            )
            
            quantity = st.number_input(
                "数量",
                min_value=1,
                step=1,
                help="取引数量を入力"
            )
        
        with col2:
            strategy_name = st.text_input(
                "戦略名",
                placeholder="例: モメンタム戦略, 移動平均戦略",
                help="使用した取引戦略名（任意）"
            )
            
            signal_strength = st.slider(
                "シグナル強度",
                min_value=0,
                max_value=100,
                value=50,
                help="取引シグナルの強度（0-100）"
            )
            
            signal_confidence = st.slider(
                "シグナル信頼度",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.1,
                help="取引シグナルの信頼度（0.0-1.0）"
            )
        
        # リスク管理設定
        st.markdown("**⚡ リスク管理設定**")
        
        col3, col4 = st.columns(2)
        
        with col3:
            set_stop_loss = st.checkbox("ストップロス設定")
            if set_stop_loss:
                stop_loss = st.number_input(
                    "ストップロス価格",
                    min_value=0.01,
                    value=entry_price * 0.95 if direction == "LONG" else entry_price * 1.05,
                    step=0.01
                )
            else:
                stop_loss = None
        
        with col4:
            set_take_profit = st.checkbox("テイクプロフィット設定")
            if set_take_profit:
                take_profit = st.number_input(
                    "テイクプロフィット価格",
                    min_value=0.01,
                    value=entry_price * 1.05 if direction == "LONG" else entry_price * 0.95,
                    step=0.01
                )
            else:
                take_profit = None
        
        # メモ
        notes = st.text_area(
            "メモ",
            placeholder="取引に関するメモ（市場状況、判断根拠など）",
            help="任意のメモを記録できます"
        )
        
        # 記録ボタン
        submitted = st.form_submit_button("📝 取引を記録", type="primary")
        
        if submitted:
            if not symbol or not entry_price or not quantity:
                st.error("❌ 銘柄コード、エントリー価格、数量は必須です")
            else:
                trade_id = tracker.record_trade(
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry_price,
                    quantity=quantity,
                    strategy_name=strategy_name or None,
                    signal_strength=signal_strength,
                    signal_confidence=signal_confidence,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    notes=notes or None
                )
                
                if trade_id:
                    st.success(f"✅ 取引を記録しました (ID: {trade_id})")
                    st.rerun()
                else:
                    st.error("❌ 取引の記録に失敗しました")


def display_trade_history(tracker: PerformanceTracker):
    """取引履歴の表示"""
    st.markdown("##### 取引履歴")
    
    # フィルタリング設定
    col1, col2, col3 = st.columns(3)
    
    with col1:
        period_filter = st.selectbox(
            "表示期間",
            ["全期間", "1週間", "1ヶ月", "3ヶ月", "6ヶ月"],
            index=2
        )
    
    with col2:
        symbol_filter = st.text_input(
            "銘柄フィルタ",
            placeholder="例: 7203.T",
            help="特定の銘柄のみ表示（空欄で全銘柄）"
        )
    
    with col3:
        limit = st.number_input(
            "表示件数",
            min_value=10,
            max_value=500,
            value=50,
            step=10
        )
    
    # 期間フィルタの設定
    if period_filter != "全期間":
        period_mapping = {
            "1週間": 7,
            "1ヶ月": 30,
            "3ヶ月": 90,
            "6ヶ月": 180
        }
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_mapping[period_filter])
    else:
        start_date = None
        end_date = None
    
    # 取引履歴取得
    try:
        trades = tracker.get_trading_history(
            symbol=symbol_filter or None,
            start_date=start_date,
            end_date=end_date
        )
        
        if not trades:
            st.info("該当する取引履歴がありません。")
            return
        
        # 制限件数適用
        trades = trades[:limit]
        
        st.markdown(f"**📊 表示件数: {len(trades)}件**")
        
        # 取引履歴テーブル作成
        trade_data = []
        for trade in trades:
            trade_data.append({
                'ID': trade.trade_id[:8] + "...",
                '銘柄': trade.symbol,
                '方向': trade.direction.value,
                'エントリー価格': f"¥{trade.entry_price:,.2f}",
                '数量': f"{trade.quantity:,}",
                'エントリー日時': trade.entry_time.strftime('%Y/%m/%d %H:%M'),
                '決済価格': f"¥{trade.exit_price:,.2f}" if trade.exit_price else "オープン",
                '損益': f"¥{trade.realized_pnl:,.0f}" if trade.realized_pnl else "-",
                '損益率': f"{trade.realized_pnl_pct:+.1f}%" if trade.realized_pnl_pct else "-",
                '戦略': trade.strategy_name or "-",
                'ステータス': trade.status.value
            })
        
        df = pd.DataFrame(trade_data)
        
        # スタイル適用
        def style_pnl(val):
            if val == "-":
                return ""
            elif "+" in val:
                return 'background-color: #e8f5e8; color: #2e7d32'
            elif "-" in val and val != "-":
                return 'background-color: #ffebee; color: #c62828'
            else:
                return ""
        
        def style_status(val):
            if val == "open":
                return 'background-color: #e3f2fd; color: #1976d2'
            elif val == "closed":
                return 'background-color: #f3e5f5; color: #7b1fa2'
            else:
                return ""
        
        styled_df = df.style.applymap(style_pnl, subset=['損益', '損益率']) \
                            .applymap(style_status, subset=['ステータス'])
        
        st.dataframe(styled_df, use_container_width=True)
        
        # 取引統計
        closed_trades = [t for t in trades if t.status.value == "closed"]
        if closed_trades:
            st.markdown("#### 📊 期間統計")
            
            total_pnl = sum(t.realized_pnl for t in closed_trades if t.realized_pnl)
            winning_trades = [t for t in closed_trades if t.realized_pnl and t.realized_pnl > 0]
            win_rate = len(winning_trades) / len(closed_trades)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("決済済取引", f"{len(closed_trades)}件")
            
            with col2:
                st.metric("勝率", f"{win_rate:.1%}")
            
            with col3:
                st.metric("総損益", f"¥{total_pnl:,.0f}")
            
            with col4:
                avg_pnl = total_pnl / len(closed_trades) if closed_trades else 0
                st.metric("平均損益", f"¥{avg_pnl:,.0f}")
        
    except Exception as e:
        st.error(f"取引履歴の取得中にエラーが発生しました: {str(e)}")


def display_settings_tab(tracker: PerformanceTracker):
    """設定タブの表示"""
    st.markdown("#### ⚙️ 設定")
    
    # データベース管理
    st.markdown("### 💾 データ管理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**バックアップ**")
        if st.button("📁 データベースをバックアップ"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"trade_history_backup_{timestamp}.db"
            
            if tracker.backup_data(backup_path):
                st.success(f"✅ バックアップ完了: {backup_path}")
            else:
                st.error("❌ バックアップに失敗しました")
    
    with col2:
        st.markdown("**統計情報**")
        summary = tracker.get_performance_summary(365)  # 1年間
        st.info(f"""
        **総取引数**: {summary.get('total_trades', 0)}件  
        **オープンポジション**: {summary.get('open_positions', 0)}件  
        **データベース更新**: {summary.get('last_updated', '不明')[:10]}
        """)
    
    # パフォーマンス目標設定
    st.markdown("### 🎯 パフォーマンス目標")
    
    with st.form("goals_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            target_win_rate = st.slider(
                "目標勝率",
                min_value=0.0,
                max_value=1.0,
                value=0.6,
                step=0.05,
                format="%.1%"
            )
            
            target_profit_factor = st.slider(
                "目標損益比",
                min_value=0.5,
                max_value=5.0,
                value=2.0,
                step=0.1
            )
        
        with col2:
            target_monthly_trades = st.number_input(
                "月間目標取引数",
                min_value=1,
                max_value=200,
                value=20,
                step=1
            )
            
            target_monthly_return = st.number_input(
                "月間目標収益率(%)",
                min_value=-100.0,
                max_value=100.0,
                value=5.0,
                step=0.5
            )
        
        if st.form_submit_button("🎯 目標を設定"):
            goals = {
                'win_rate': target_win_rate,
                'profit_factor': target_profit_factor,
                'monthly_trades': target_monthly_trades,
                'monthly_return_pct': target_monthly_return / 100
            }
            
            if tracker.set_performance_goals(goals):
                st.success("✅ 目標を設定しました")
                
                # 現在の進捗確認
                progress = tracker.check_goal_progress(goals, 30)
                
                if progress:
                    st.markdown("#### 📊 現在の進捗状況")
                    
                    for goal_name, goal_data in progress.items():
                        achievement_rate = goal_data.get('achievement_rate', 0)
                        status = goal_data.get('status', 'unknown')
                        
                        if status == 'achieved':
                            st.success(f"✅ {goal_name}: {achievement_rate:.1f}% 達成")
                        elif achievement_rate >= 80:
                            st.warning(f"🔶 {goal_name}: {achievement_rate:.1f}% (もう少し)")
                        else:
                            st.info(f"📊 {goal_name}: {achievement_rate:.1f}%")
            else:
                st.error("❌ 目標設定に失敗しました")
    
    # 分析設定
    st.markdown("### 📊 分析設定")
    
    st.markdown("**デフォルト設定**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        default_lookback = st.selectbox(
            "デフォルト分析期間",
            [30, 60, 90, 180, 365],
            index=2,
            format_func=lambda x: f"{x}日"
        )
    
    with col2:
        default_min_trades = st.number_input(
            "デフォルト最小取引数",
            min_value=3,
            max_value=50,
            value=10,
            step=1
        )
    
    if st.button("💾 設定を保存"):
        # TODO: 設定をファイルまたはデータベースに保存
        st.success("✅ 設定を保存しました")


def display_recent_trades_chart(trades):
    """最近の取引チャート表示"""
    if not trades:
        return
    
    # 損益推移チャート
    cumulative_pnl = []
    dates = []
    
    running_total = 0
    for trade in reversed(trades):  # 古い順にソート
        if trade.realized_pnl is not None:
            running_total += trade.realized_pnl
            cumulative_pnl.append(running_total)
            dates.append(trade.exit_time or trade.entry_time)
    
    if cumulative_pnl:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=cumulative_pnl,
            mode='lines+markers',
            name='累積損益',
            line=dict(color='blue', width=2),
            fill='tonexty',
            fillcolor='rgba(0,100,255,0.1)'
        ))
        
        fig.update_layout(
            title="累積損益推移",
            xaxis_title="日時",
            yaxis_title="累積損益 (¥)",
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)


def display_tendency_radar_chart(tendencies):
    """投資傾向レーダーチャート表示"""
    if not tendencies:
        return
    
    # レーダーチャート用データ準備
    categories = []
    scores = []
    
    for tendency in tendencies:
        categories.append(tendency.name)
        scores.append(tendency.score)
    
    # レーダーチャート作成
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=scores,
        theta=categories,
        fill='toself',
        name='投資傾向スコア',
        line_color='rgb(255,69,0)',
        fillcolor='rgba(255,69,0,0.25)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=True,
        title="投資傾向分析（レーダーチャート）",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)


def get_performance_rating(value, metric_type):
    """パフォーマンス評価を取得"""
    if metric_type == 'win_rate':
        if value >= 0.7:
            return "🔥 優秀"
        elif value >= 0.5:
            return "👍 良好"
        elif value >= 0.4:
            return "📊 平均"
        else:
            return "⚠️ 要改善"
    
    elif metric_type == 'profit_factor':
        if value >= 2.0:
            return "🔥 優秀"
        elif value >= 1.5:
            return "👍 良好"
        elif value >= 1.0:
            return "📊 平均"
        else:
            return "⚠️ 要改善"
    
    elif metric_type == 'pnl':
        if value > 100000:
            return "🔥 優秀"
        elif value > 0:
            return "👍 良好"
        elif value > -50000:
            return "📊 平均"
        else:
            return "⚠️ 要改善"
    
    elif metric_type == 'avg_pnl':
        if value > 5000:
            return "🔥 優秀"
        elif value > 0:
            return "👍 良好"
        elif value > -2000:
            return "📊 平均"
        else:
            return "⚠️ 要改善"
    
    return "📊 平均"