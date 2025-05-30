"""
投資事例学習機能
過去の成功・失敗事例から学習する教育コンテンツを提供
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class InvestmentCase:
    """投資事例クラス"""
    
    def __init__(self, case_id: str, title: str, case_type: str, difficulty: str, 
                 description: str, background: str, decision_points: List[str],
                 outcome: str, lessons: List[str], chart_data: Optional[Dict] = None):
        self.case_id = case_id
        self.title = title
        self.case_type = case_type  # "success" or "failure"
        self.difficulty = difficulty  # "初級", "中級", "上級"
        self.description = description
        self.background = background
        self.decision_points = decision_points
        self.outcome = outcome
        self.lessons = lessons
        self.chart_data = chart_data


class EducationCasesComponent:
    """投資事例学習コンポーネント"""
    
    def __init__(self):
        """初期化"""
        self.cases = self._load_case_studies()
    
    def _load_case_studies(self) -> List[InvestmentCase]:
        """事例データを読み込み"""
        return [
            InvestmentCase(
                case_id="success_001",
                title="トヨタ自動車の長期投資成功例",
                case_type="success",
                difficulty="初級",
                description="2020年3月のコロナショック時にトヨタ自動車株を購入し、2年間保有して大きな利益を得た事例",
                background="""
                2020年3月、新型コロナウイルスの影響で株式市場が大暴落。
                多くの投資家がパニック売りを行う中、ある投資家は以下の判断を行った：
                
                • トヨタの財務基盤の強さに注目
                • 電動化戦略の将来性を評価
                • 歴史的な割安水準での購入機会と判断
                """,
                decision_points=[
                    "株価が7000円台まで下落（通常時の約半額）",
                    "PER 10倍以下、PBR 0.8倍と割安指標が良好",
                    "自動車業界のリーダーとしての競争優位性",
                    "豊富な現金保有による財務安定性"
                ],
                outcome="""
                購入価格：7,200円（2020年3月）
                売却価格：10,500円（2022年3月）
                投資期間：2年間
                リターン：+45.8%
                
                年平均リターン：約20%の優秀な成果を達成
                """,
                lessons=[
                    "危機時こそ優良企業への投資機会",
                    "ファンダメンタル分析の重要性",
                    "長期視点での投資判断",
                    "市場の恐怖心に惑わされない冷静な判断"
                ],
                chart_data={
                    "dates": ["2020/03", "2020/06", "2020/09", "2020/12", "2021/03", "2021/06", "2021/09", "2021/12", "2022/03"],
                    "prices": [7200, 6800, 7500, 8200, 9100, 9800, 9200, 10200, 10500],
                    "events": {
                        "2020/03": "購入（コロナショック）",
                        "2020/12": "業績回復の兆し",
                        "2021/06": "電動化戦略発表",
                        "2022/03": "売却"
                    }
                }
            ),
            
            InvestmentCase(
                case_id="failure_001", 
                title="短期売買での損失拡大事例",
                case_type="failure",
                difficulty="初級",
                description="テクニカル分析に頼りすぎて短期売買を繰り返し、手数料と税金で損失が拡大した事例",
                background="""
                株式投資を始めたばかりの投資家が、YouTubeやSNSで見た「簡単に儲かる」手法に惹かれて実践。
                
                • デイトレードやスキャルピングを多用
                • 損切りルールを設定せず
                • 感情的な取引を繰り返し
                """,
                decision_points=[
                    "短期的な価格変動に一喜一憂",
                    "損失が出ても「必ず戻る」と根拠なく信じる",
                    "利益は小さく確定、損失は拡大させる",
                    "手数料や税金のコストを軽視"
                ],
                outcome="""
                投資元本：100万円
                取引回数：月50回（年間600回）
                平均手数料：取引あたり300円
                年間手数料：18万円
                
                最終結果：1年で30万円の損失
                実質的な損失率：-30%
                """,
                lessons=[
                    "短期売買は手数料負けしやすい",
                    "感情的な取引は避ける",
                    "損切りルールの設定が重要", 
                    "取引コストを考慮した戦略が必要"
                ],
                chart_data={
                    "dates": ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
                    "portfolio_value": [100, 105, 95, 110, 90, 85, 95, 80, 75, 80, 75, 70],
                    "trades_count": [45, 52, 48, 55, 60, 58, 52, 48, 45, 50, 55, 32]
                }
            ),
            
            InvestmentCase(
                case_id="success_002",
                title="分散投資による安定運用",
                case_type="success", 
                difficulty="中級",
                description="セクター分散とリバランシングを活用して、10年間で安定的なリターンを実現した事例",
                background="""
                30代会社員が老後資金形成を目的として開始した長期投資。
                
                • 毎月10万円の定額投資
                • 複数セクターへの分散投資
                • 年1回のリバランシング実施
                """,
                decision_points=[
                    "成長株（テクノロジー）40%",
                    "安定株（インフラ・公益）30%", 
                    "バリュー株（金融・素材）20%",
                    "海外ETF 10%"
                ],
                outcome="""
                投資期間：10年間
                総投資額：1,200万円（月10万円×120ヶ月）
                最終評価額：1,680万円
                総リターン：+40%（年平均3.5%）
                
                年間配当収入：約50万円
                """,
                lessons=[
                    "分散投資によるリスク軽減効果", 
                    "定期的なリバランシングの重要性",
                    "長期投資の複利効果",
                    "感情に左右されない機械的な投資"
                ]
            ),
            
            InvestmentCase(
                case_id="failure_002",
                title="集中投資による大損失",
                case_type="failure",
                difficulty="中級", 
                description="特定銘柄への集中投資で資産の大部分を失った事例",
                background="""
                ITベンチャー企業に勤める投資家が、業界の知識を過信して集中投資を実行。
                
                • 保有資産の80%を成長株1銘柄に投資
                • 企業の将来性を過度に楽観視
                • リスク管理を軽視
                """,
                decision_points=[
                    "「絶対に上がる」という根拠なき確信",
                    "分散投資は「リターンを下げる」と誤解",
                    "専門知識があるから大丈夫という油断",
                    "ストップロス設定なし"
                ],
                outcome="""
                投資金額：500万円（資産の80%）
                購入価格：平均2,500円
                最安値：400円（-84%）
                最終売却価格：600円（-76%）
                
                損失額：380万円
                """,
                lessons=[
                    "集中投資の危険性",
                    "専門知識の過信は禁物",
                    "リスク分散の重要性",
                    "損切りルール設定の必要性"
                ]
            ),
            
            InvestmentCase(
                case_id="success_003",
                title="逆張り投資での大成功",
                case_type="success",
                difficulty="上級",
                description="市場が悲観的な時期に逆張り投資を行い、大きなリターンを獲得した上級者事例",
                background="""
                2008年リーマンショック時、経験豊富な投資家が市場の過度な悲観を機会と捉えて投資。
                
                • 財務健全性の高い企業を厳選
                • 市場センチメントと企業価値の乖離に着目
                • 長期投資の覚悟で実行
                """,
                decision_points=[
                    "VIX指数が80超の極度の恐怖状態", 
                    "優良企業のPERが一桁台まで下落",
                    "市場参加者の大多数が悲観的",
                    "歴史的に見て大底圏と判断"
                ],
                outcome="""
                投資期間：2008年10月〜2013年10月（5年間）
                投資元本：1,000万円
                最終評価額：3,200万円
                リターン：+220%
                
                年平均リターン：約25%
                """,
                lessons=[
                    "逆張り投資のタイミング判断",
                    "市場の恐怖心を利用した投資機会の発見",
                    "ファンダメンタル分析の重要性",
                    "長期視点での投資判断力"
                ]
            )
        ]
    
    def display(self):
        """メイン表示"""
        st.header("📖 投資事例学習")
        
        # フィルタ機能
        col1, col2, col3 = st.columns(3)
        
        with col1:
            case_types = ["全て", "成功事例", "失敗事例"]
            selected_type = st.selectbox("📊 事例タイプ", case_types)
        
        with col2:
            difficulties = ["全て", "初級", "中級", "上級"]
            selected_difficulty = st.selectbox("📈 難易度", difficulties)
        
        with col3:
            if st.button("🔄 事例更新"):
                st.rerun()
        
        # 事例フィルタリング
        filtered_cases = self._filter_cases(selected_type, selected_difficulty)
        
        if not filtered_cases:
            st.warning("該当する事例がありません")
            return
        
        # 事例一覧表示
        st.markdown("---")
        self._display_case_overview(filtered_cases)
        
        # 詳細事例選択・表示
        st.markdown("---")
        selected_case_id = st.selectbox(
            "📚 詳細を見る事例を選択",
            [case.case_id for case in filtered_cases],
            format_func=lambda x: next(case.title for case in filtered_cases if case.case_id == x)
        )
        
        selected_case = next(case for case in filtered_cases if case.case_id == selected_case_id)
        self._display_case_detail(selected_case)
    
    def _filter_cases(self, case_type: str, difficulty: str) -> List[InvestmentCase]:
        """事例フィルタリング"""
        filtered = self.cases.copy()
        
        if case_type != "全て":
            type_map = {"成功事例": "success", "失敗事例": "failure"}
            filtered = [case for case in filtered if case.case_type == type_map[case_type]]
        
        if difficulty != "全て":
            filtered = [case for case in filtered if case.difficulty == difficulty]
        
        return filtered
    
    def _display_case_overview(self, cases: List[InvestmentCase]):
        """事例概要表示"""
        st.subheader("📋 事例一覧")
        
        # 事例サマリー
        success_count = len([c for c in cases if c.case_type == "success"])
        failure_count = len([c for c in cases if c.case_type == "failure"])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("総事例数", len(cases))
        
        with col2:
            st.metric("✅ 成功事例", success_count)
        
        with col3:
            st.metric("❌ 失敗事例", failure_count)
        
        with col4:
            if len(cases) > 0:
                success_rate = (success_count / len(cases)) * 100
                st.metric("成功率", f"{success_rate:.1f}%")
        
        # 事例テーブル
        case_data = []
        for case in cases:
            case_data.append({
                "タイトル": case.title,
                "タイプ": "✅ 成功" if case.case_type == "success" else "❌ 失敗",
                "難易度": case.difficulty,
                "概要": case.description[:50] + "..." if len(case.description) > 50 else case.description
            })
        
        df = pd.DataFrame(case_data)
        
        # スタイリング
        def style_type(val):
            if "成功" in val:
                return 'background-color: #e8f5e8; color: #2e7d32'
            else:
                return 'background-color: #ffebee; color: #c62828'
        
        styled_df = df.style.applymap(style_type, subset=["タイプ"])
        st.dataframe(styled_df, use_container_width=True)
    
    def _display_case_detail(self, case: InvestmentCase):
        """事例詳細表示"""
        st.subheader(f"📖 {case.title}")
        
        # 基本情報
        col1, col2, col3 = st.columns(3)
        
        with col1:
            type_color = "🟢" if case.case_type == "success" else "🔴"
            type_text = "成功事例" if case.case_type == "success" else "失敗事例"
            st.markdown(f"**タイプ**: {type_color} {type_text}")
        
        with col2:
            difficulty_color = {"初級": "🟢", "中級": "🟡", "上級": "🔴"}
            st.markdown(f"**難易度**: {difficulty_color.get(case.difficulty, '⚪')} {case.difficulty}")
        
        with col3:
            st.markdown(f"**事例ID**: {case.case_id}")
        
        # 説明
        st.markdown("### 📝 事例概要")
        st.info(case.description)
        
        # 背景
        st.markdown("### 🌅 背景")
        st.markdown(case.background)
        
        # 判断ポイント
        st.markdown("### 🎯 重要な判断ポイント")
        for i, point in enumerate(case.decision_points, 1):
            st.markdown(f"{i}. {point}")
        
        # チャート表示（データがある場合）
        if case.chart_data:
            st.markdown("### 📊 価格推移・パフォーマンス")
            self._display_case_chart(case)
        
        # 結果
        st.markdown("### 📈 投資結果")
        if case.case_type == "success":
            st.success(case.outcome)
        else:
            st.error(case.outcome)
        
        # 学習ポイント
        st.markdown("### 💡 学習ポイント")
        for i, lesson in enumerate(case.lessons, 1):
            st.markdown(f"**{i}. {lesson}**")
        
        # クイズ・振り返り
        st.markdown("---")
        st.markdown("### 🤔 振り返りクイズ")
        
        if case.case_type == "success":
            quiz_question = "この成功事例で最も重要だった要因は何だと思いますか？"
        else:
            quiz_question = "この失敗を避けるために最も重要なことは何だと思いますか？"
        
        user_answer = st.text_area(quiz_question, height=100)
        
        if st.button("💭 回答を送信"):
            st.info("回答ありがとうございます！他の事例も学習して投資スキルを向上させましょう。")
    
    def _display_case_chart(self, case: InvestmentCase):
        """事例チャート表示"""
        chart_data = case.chart_data
        
        if "prices" in chart_data:
            # 価格推移チャート
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=chart_data["dates"],
                y=chart_data["prices"],
                mode='lines+markers',
                name='株価',
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=8)
            ))
            
            # イベント注釈
            if "events" in chart_data:
                for date, event in chart_data["events"].items():
                    if date in chart_data["dates"]:
                        idx = chart_data["dates"].index(date)
                        fig.add_annotation(
                            x=date,
                            y=chart_data["prices"][idx],
                            text=event,
                            showarrow=True,
                            arrowhead=2,
                            arrowsize=1,
                            arrowwidth=2,
                            arrowcolor="#ff7f0e",
                            bgcolor="rgba(255,255,255,0.8)",
                            bordercolor="#ff7f0e",
                            borderwidth=1
                        )
            
            fig.update_layout(
                title="株価推移",
                xaxis_title="時期",
                yaxis_title="株価 (円)",
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        elif "portfolio_value" in chart_data:
            # ポートフォリオ価値推移
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=chart_data["dates"],
                y=chart_data["portfolio_value"],
                mode='lines+markers',
                name='ポートフォリオ価値',
                line=dict(color='#d62728', width=3),
                marker=dict(size=8)
            ))
            
            fig.update_layout(
                title="ポートフォリオ価値の推移",
                xaxis_title="月",
                yaxis_title="価値 (万円)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 取引回数チャート
            if "trades_count" in chart_data:
                fig2 = go.Figure()
                
                fig2.add_trace(go.Bar(
                    x=chart_data["dates"],
                    y=chart_data["trades_count"],
                    name='月間取引回数',
                    marker_color='#ff7f0e'
                ))
                
                fig2.update_layout(
                    title="月間取引回数",
                    xaxis_title="月",
                    yaxis_title="取引回数",
                    height=300
                )
                
                st.plotly_chart(fig2, use_container_width=True)


def render_education_cases_tab():
    """投資事例学習タブのレンダリング関数"""
    component = EducationCasesComponent()
    component.display()


if __name__ == "__main__":
    render_education_cases_tab()