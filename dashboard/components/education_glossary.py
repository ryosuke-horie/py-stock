"""
投資用語集・教育支援機能
投資初心者向けの用語検索と解説機能を提供
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional


class EducationGlossaryComponent:
    """投資用語集コンポーネント"""
    
    def __init__(self):
        """初期化"""
        self.glossary_data = self._load_glossary_data()
    
    def _load_glossary_data(self) -> Dict[str, Dict]:
        """用語集データを読み込み"""
        return {
            # 基本用語
            "株式": {
                "definition": "企業の所有権を表す証券。株主は企業の部分的所有者となる。",
                "category": "基本用語",
                "difficulty": "初級",
                "related_terms": ["株主", "配当", "株価"],
                "example": "トヨタ自動車の株式を100株購入すると、トヨタの0.000003%の所有者になる。"
            },
            "配当": {
                "definition": "企業が株主に分配する利益の一部。通常年1-2回支払われる。",
                "category": "基本用語", 
                "difficulty": "初級",
                "related_terms": ["株式", "配当利回り", "株主"],
                "example": "年間配当100円、株価2000円の場合、配当利回りは5%。"
            },
            "PER": {
                "definition": "株価収益率。株価が1株当たり純利益の何倍かを示す指標。",
                "category": "財務指標",
                "difficulty": "中級", 
                "related_terms": ["PBR", "ROE", "EPS"],
                "example": "PER15倍の企業は、現在の利益水準が続けば15年で投資額を回収できる計算。"
            },
            "PBR": {
                "definition": "株価純資産倍率。株価が1株当たり純資産の何倍かを示す指標。",
                "category": "財務指標",
                "difficulty": "中級",
                "related_terms": ["PER", "ROE", "BPS"],
                "example": "PBR1倍以下の株は理論上、会社の解散価値以下で取引されている。"
            },
            
            # テクニカル分析用語
            "移動平均線": {
                "definition": "過去n日間の終値の平均値を線で結んだもの。トレンドを把握する基本指標。",
                "category": "テクニカル分析",
                "difficulty": "初級",
                "related_terms": ["ゴールデンクロス", "デッドクロス", "トレンド"],
                "example": "25日移動平均線が上向きなら上昇トレンド、下向きなら下降トレンド。"
            },
            "RSI": {
                "definition": "相対力指数。価格の上昇力と下降力を比較し、買われ過ぎ・売られ過ぎを判断。",
                "category": "テクニカル分析",
                "difficulty": "中級",
                "related_terms": ["オシレーター", "MACD", "ストキャスティクス"],
                "example": "RSI70以上で買われ過ぎ、30以下で売られ過ぎと判断される。"
            },
            "MACD": {
                "definition": "移動平均収束拡散。2本の移動平均線の差から売買タイミングを判断する指標。",
                "category": "テクニカル分析", 
                "difficulty": "中級",
                "related_terms": ["シグナル線", "ヒストグラム", "移動平均線"],
                "example": "MACDがシグナル線を上抜けると買いシグナル、下抜けると売りシグナル。"
            },
            "ゴールデンクロス": {
                "definition": "短期移動平均線が長期移動平均線を下から上に抜けること。買いシグナルとされる。",
                "category": "テクニカル分析",
                "difficulty": "初級", 
                "related_terms": ["デッドクロス", "移動平均線", "買いシグナル"],
                "example": "25日線が75日線を上抜けするとゴールデンクロス発生。"
            },
            "デッドクロス": {
                "definition": "短期移動平均線が長期移動平均線を上から下に抜けること。売りシグナルとされる。",
                "category": "テクニカル分析",
                "difficulty": "初級",
                "related_terms": ["ゴールデンクロス", "移動平均線", "売りシグナル"],
                "example": "25日線が75日線を下抜けするとデッドクロス発生。"
            },
            
            # リスク管理用語
            "損切り": {
                "definition": "損失拡大を防ぐため、含み損がある状態で株を売却すること。",
                "category": "リスク管理",
                "difficulty": "初級",
                "related_terms": ["ストップロス", "利確", "リスク管理"],
                "example": "購入価格から10%下落したら損切りするルールを設定。"
            },
            "利確": {
                "definition": "利益確定の略。含み益がある状態で株を売却し、利益を確定すること。",
                "category": "リスク管理", 
                "difficulty": "初級",
                "related_terms": ["損切り", "利食い", "プロフィットテイク"],
                "example": "購入価格から20%上昇したら利確するルールを設定。"
            },
            "ポートフォリオ": {
                "definition": "投資家が保有する株式や債券などの金融商品の組み合わせ。",
                "category": "リスク管理",
                "difficulty": "初級",
                "related_terms": ["分散投資", "アセットアロケーション", "リスク"],
                "example": "株式70%、債券30%のポートフォリオでリスクを分散。"
            },
            "分散投資": {
                "definition": "リスクを軽減するため、複数の異なる投資対象に資金を分散すること。",
                "category": "リスク管理",
                "difficulty": "初級", 
                "related_terms": ["ポートフォリオ", "リスク軽減", "相関"],
                "example": "異なる業種の株式や国内外の資産に投資してリスクを分散。"
            },
            
            # 市場用語
            "ボラティリティ": {
                "definition": "価格変動の激しさを表す指標。高いほど価格変動が大きい。",
                "category": "市場分析",
                "difficulty": "中級",
                "related_terms": ["リスク", "標準偏差", "VIX"],
                "example": "ボラティリティ20%の株は、年間で±20%程度の価格変動が期待される。"
            },
            "流動性": {
                "definition": "資産を現金に換えやすさ。取引量が多い銘柄ほど流動性が高い。",
                "category": "市場分析",
                "difficulty": "中級",
                "related_terms": ["出来高", "売買代金", "スプレッド"],
                "example": "大型株は流動性が高く、小型株は流動性が低い傾向。"
            },
            "時価総額": {
                "definition": "企業の株式価値の総額。株価×発行済株式数で計算。",
                "category": "基本用語",
                "difficulty": "初級",
                "related_terms": ["株価", "発行済株式数", "企業価値"],
                "example": "株価1000円、発行済株式数100万株なら時価総額は10億円。"
            }
        }
    
    def display(self):
        """メイン表示"""
        st.header("📚 投資用語集")
        
        # 検索・フィルタ機能
        search_col, filter_col, difficulty_col = st.columns([2, 1, 1])
        
        with search_col:
            search_term = st.text_input("🔍 用語を検索", placeholder="例: 移動平均線、PER、損切り", key="education_glossary_search")
        
        with filter_col:
            categories = ["全て"] + list(set(term["category"] for term in self.glossary_data.values()))
            selected_category = st.selectbox("📂 カテゴリ", categories)
        
        with difficulty_col:
            difficulties = ["全て", "初級", "中級", "上級"]
            selected_difficulty = st.selectbox("📊 難易度", difficulties)
        
        # フィルタリング
        filtered_terms = self._filter_terms(search_term, selected_category, selected_difficulty)
        
        if not filtered_terms:
            st.warning("該当する用語が見つかりませんでした。")
            return
        
        # 用語表示
        st.markdown("---")
        
        # 用語一覧をタブで表示
        if len(filtered_terms) > 0:
            # 詳細表示エリア
            selected_term = st.selectbox("📖 詳細を見る用語を選択", list(filtered_terms.keys()))
            
            if selected_term:
                self._display_term_detail(selected_term, filtered_terms[selected_term])
            
            st.markdown("---")
            
            # 用語一覧表
            self._display_terms_table(filtered_terms)
    
    def _filter_terms(self, search_term: str, category: str, difficulty: str) -> Dict[str, Dict]:
        """用語をフィルタリング"""
        filtered = {}
        
        for term, data in self.glossary_data.items():
            # 検索条件チェック
            if search_term and search_term.lower() not in term.lower() and search_term.lower() not in data["definition"].lower():
                continue
            
            # カテゴリフィルタ
            if category != "全て" and data["category"] != category:
                continue
            
            # 難易度フィルタ
            if difficulty != "全て" and data["difficulty"] != difficulty:
                continue
            
            filtered[term] = data
        
        return filtered
    
    def _display_term_detail(self, term: str, data: Dict):
        """用語の詳細表示"""
        # タイトルと基本情報
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.subheader(f"📖 {term}")
        
        with col2:
            difficulty_color = {
                "初級": "🟢",
                "中級": "🟡", 
                "上級": "🔴"
            }
            st.write(f"**難易度**: {difficulty_color.get(data['difficulty'], '⚪')} {data['difficulty']}")
        
        with col3:
            st.write(f"**カテゴリ**: {data['category']}")
        
        # 定義
        st.markdown(f"**💡 定義**")
        st.info(data["definition"])
        
        # 実例
        if "example" in data:
            st.markdown("**📝 実例**")
            st.success(data["example"])
        
        # 関連用語
        if "related_terms" in data and data["related_terms"]:
            st.markdown("**🔗 関連用語**")
            related_cols = st.columns(min(len(data["related_terms"]), 4))
            for i, related_term in enumerate(data["related_terms"]):
                with related_cols[i % len(related_cols)]:
                    if related_term in self.glossary_data:
                        if st.button(f"📎 {related_term}", key=f"related_{term}_{i}"):
                            st.session_state.selected_related_term = related_term
                    else:
                        st.write(f"• {related_term}")
    
    def _display_terms_table(self, terms: Dict[str, Dict]):
        """用語一覧表の表示"""
        st.subheader("📋 用語一覧")
        
        # データフレーム作成
        table_data = []
        for term, data in terms.items():
            table_data.append({
                "用語": term,
                "カテゴリ": data["category"],
                "難易度": data["difficulty"],
                "概要": data["definition"][:50] + "..." if len(data["definition"]) > 50 else data["definition"]
            })
        
        df = pd.DataFrame(table_data)
        
        # スタイリング
        def style_difficulty(val):
            colors = {
                "初級": "background-color: #e8f5e8; color: #2e7d32",
                "中級": "background-color: #fff3e0; color: #f57c00", 
                "上級": "background-color: #ffebee; color: #c62828"
            }
            return colors.get(val, "")
        
        styled_df = df.style.applymap(style_difficulty, subset=["難易度"])
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        # 統計情報
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("総用語数", len(terms))
        
        with col2:
            categories = [data["category"] for data in terms.values()]
            st.metric("カテゴリ数", len(set(categories)))
        
        with col3:
            difficulties = [data["difficulty"] for data in terms.values()]
            beginner_count = difficulties.count("初級")
            st.metric("初級用語", f"{beginner_count}/{len(terms)}")
    
    def get_term_definition(self, term: str) -> Optional[str]:
        """特定用語の定義を取得"""
        return self.glossary_data.get(term, {}).get("definition")
    
    def search_terms(self, query: str) -> List[str]:
        """用語検索"""
        results = []
        query_lower = query.lower()
        
        for term, data in self.glossary_data.items():
            if query_lower in term.lower() or query_lower in data["definition"].lower():
                results.append(term)
        
        return results


def render_education_glossary_tab():
    """投資用語集タブのレンダリング関数"""
    component = EducationGlossaryComponent()
    component.display()


if __name__ == "__main__":
    render_education_glossary_tab()