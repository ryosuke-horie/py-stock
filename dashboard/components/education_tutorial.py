"""
インタラクティブチュートリアル機能
初心者向けのステップバイステップ投資学習ガイド
"""

import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime


class TutorialStep:
    """チュートリアルステップクラス"""
    
    def __init__(self, step_id: str, title: str, description: str, content: str,
                 interactive_element: Optional[str] = None, next_step: Optional[str] = None):
        self.step_id = step_id
        self.title = title
        self.description = description
        self.content = content
        self.interactive_element = interactive_element
        self.next_step = next_step


class EducationTutorialComponent:
    """インタラクティブチュートリアルコンポーネント"""
    
    def __init__(self):
        """初期化"""
        self.tutorials = self._load_tutorials()
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """セッション状態初期化"""
        if 'tutorial_progress' not in st.session_state:
            st.session_state.tutorial_progress = {}
        
        if 'current_tutorial' not in st.session_state:
            st.session_state.current_tutorial = None
        
        if 'current_step' not in st.session_state:
            st.session_state.current_step = 0
    
    def _load_tutorials(self) -> Dict[str, Dict]:
        """チュートリアルデータを読み込み"""
        return {
            "basic_investment": {
                "title": "🌱 投資の基本",
                "description": "投資の基礎知識から実践まで",
                "difficulty": "初級",
                "duration": "約30分",
                "steps": [
                    TutorialStep(
                        "basic_001",
                        "投資とは何か？",
                        "投資の基本概念を理解しよう",
                        """
                        ### 💡 投資とは？
                        
                        投資とは、**将来のリターンを期待してお金を資産に投入すること**です。
                        
                        #### 投資と貯金の違い
                        
                        | 項目 | 貯金 | 投資 |
                        |------|------|------|
                        | リスク | 低い | 高い |
                        | リターン | 低い（年0.01%程度） | 高い（年5-10%も可能） |
                        | 流動性 | 高い | 中〜低 |
                        | 元本保証 | あり | なし |
                        
                        #### なぜ投資が必要なのか？
                        
                        1. **インフレ対策**: 物価上昇に対抗
                        2. **資産増加**: 長期的な資産形成
                        3. **老後資金**: 年金だけでは不十分
                        
                        💡 **重要**: 投資は余裕資金で行うことが鉄則です！
                        """,
                        "quiz",
                        "basic_002"
                    ),
                    TutorialStep(
                        "basic_002", 
                        "株式投資の仕組み",
                        "株式とは何か、どう利益を得るかを学ぼう",
                        """
                        ### 📈 株式投資とは？
                        
                        株式投資は**企業の一部を所有すること**です。
                        
                        #### 株式で利益を得る2つの方法
                        
                        1. **キャピタルゲイン（値上がり益）**
                           - 株価の上昇による利益
                           - 例：1000円で買った株が1200円になったら200円の利益
                        
                        2. **インカムゲイン（配当金）**
                           - 企業が株主に分配する利益
                           - 例：年間50円の配当をもらう
                        
                        #### 株価が動く理由
                        
                        - 📊 **業績**: 企業の売上・利益
                        - 🌍 **経済情勢**: 金利、為替、経済成長
                        - 😨 **市場心理**: 投資家の期待と不安
                        - 📰 **ニュース**: 企業発表、社会情勢
                        
                        #### リスクについて
                        
                        ⚠️ **株価は下がることもあります**
                        - 企業業績の悪化
                        - 市場全体の下落
                        - 予期せぬ事件・事故
                        """,
                        "calculation",
                        "basic_003"
                    ),
                    TutorialStep(
                        "basic_003",
                        "証券口座の開設",
                        "実際に投資を始めるための準備",
                        """
                        ### 🏦 証券口座を開設しよう
                        
                        株式投資を始めるには**証券口座**が必要です。
                        
                        #### 主な証券会社の特徴
                        
                        **ネット証券（おすすめ）**
                        - 🌟 **SBI証券**: 最大手、商品豊富
                        - 🌟 **楽天証券**: 楽天ポイント活用
                        - 🌟 **マネックス証券**: 米国株に強い
                        
                        **手数料比較（1回の取引）**
                        
                        | 取引金額 | SBI証券 | 楽天証券 | 大手対面証券 |
                        |----------|---------|----------|--------------|
                        | 10万円以下 | 99円 | 99円 | 1,000円以上 |
                        | 50万円以下 | 275円 | 275円 | 5,000円以上 |
                        
                        #### 口座開設の流れ
                        
                        1. **🌐 Webサイトから申込み**
                        2. **📋 必要書類の提出**
                           - 本人確認書類（免許証など）
                           - マイナンバー書類
                        3. **📞 簡単な審査**
                        4. **📮 口座開設通知の受取り**
                        
                        #### NISA口座も一緒に開設
                        
                        💰 **つみたてNISA**: 年40万円まで非課税
                        💰 **一般NISA**: 年120万円まで非課税
                        
                        ⭐ **初心者にはつみたてNISAがおすすめ**
                        """,
                        "checklist",
                        "basic_004"
                    ),
                    TutorialStep(
                        "basic_004",
                        "投資資金の準備",
                        "いくらから始める？資金管理の基本",
                        """
                        ### 💰 投資資金をどう準備する？
                        
                        #### 投資に回せる資金の目安
                        
                        **3つの資金に分けて考えよう**
                        
                        1. **生活費** (月収の6ヶ月分)
                           - 緊急時に必要な資金
                           - 普通預金で保管
                        
                        2. **短期資金** (1-3年以内に使う予定)
                           - 結婚、車購入、旅行など
                           - 定期預金や低リスク投資
                        
                        3. **長期資金** (3年以上使わない)
                           - 老後資金、教育資金
                           - **この部分を投資に回す**
                        
                        #### 投資金額の例
                        
                        **月収30万円の場合**
                        - 生活費確保：180万円
                        - 短期資金：100万円
                        - 投資可能額：**毎月3-5万円**
                        
                        #### 少額から始めよう
                        
                        📊 **月1万円から始められます**
                        
                        | 月額 | 10年後 | 20年後 | 30年後 |
                        |------|--------|--------|--------|
                        | 1万円 | 156万円 | 411万円 | 849万円 |
                        | 3万円 | 468万円 | 1,233万円 | 2,547万円 |
                        | 5万円 | 780万円 | 2,055万円 | 4,245万円 |
                        
                        *年利5%で計算（複利効果含む）
                        
                        ⚠️ **借金をして投資は絶対NG！**
                        """,
                        "calculator",
                        "basic_005"
                    ),
                    TutorialStep(
                        "basic_005",
                        "初回投資の実践",
                        "実際に株を買ってみよう",
                        """
                        ### 🛒 初めての株式購入
                        
                        #### 初心者におすすめの投資方法
                        
                        **1. インデックス投資（最推奨）**
                        - 📊 全体に分散投資
                        - 🏆 商品例：「eMAXIS Slim 全世界株式」
                        - 💡 毎月定額購入（積立投資）
                        
                        **2. 日本の大型株**
                        - 🏢 安定した大企業
                        - 🏆 例：トヨタ(7203)、NTT(9432)
                        - 💡 100株単位での購入
                        
                        #### 注文の流れ
                        
                        **📱 証券会社アプリ・サイトで操作**
                        
                        1. **銘柄検索**: 「トヨタ」「7203」など
                        2. **注文方法選択**
                           - 📊 **成行注文**: すぐに買える
                           - 🎯 **指値注文**: 価格を指定
                        3. **数量入力**: 100株、200株など
                        4. **注文確認**: 内容を確認して実行
                        
                        #### 初回購入のポイント
                        
                        ✅ **少額から始める**: 10-30万円程度
                        ✅ **有名企業を選ぶ**: よく知っている会社
                        ✅ **一度に買わない**: 3-4回に分けて購入
                        ✅ **長期保有の覚悟**: 短期売買は避ける
                        
                        #### よくある失敗
                        
                        ❌ **いきなり高額投資**
                        ❌ **知らない会社の株を購入**
                        ❌ **値動きに一喜一憂**
                        ❌ **借金して投資**
                        """,
                        "simulation",
                        None
                    )
                ]
            },
            
            "technical_analysis": {
                "title": "📊 テクニカル分析入門",
                "description": "チャートの読み方と分析手法",
                "difficulty": "中級",
                "duration": "約45分",
                "steps": [
                    TutorialStep(
                        "tech_001",
                        "チャートの基本",
                        "ローソク足とトレンドの見方",
                        """
                        ### 📊 株価チャートを読もう
                        
                        #### ローソク足の見方
                        
                        ローソク足は**1日の値動きを表現**します。
                        
                        **🕯️ ローソク足の構成**
                        - **始値**: その日の最初の価格
                        - **高値**: その日の最高価格
                        - **安値**: その日の最安価格
                        - **終値**: その日の最後の価格
                        
                        **色の意味**
                        - 🟢 **陽線**: 終値 > 始値（上昇）
                        - 🔴 **陰線**: 終値 < 始値（下落）
                        
                        #### トレンドの種類
                        
                        📈 **上昇トレンド**: 高値・安値が切り上がる
                        📉 **下降トレンド**: 高値・安値が切り下がる
                        ➡️ **横ばいトレンド**: 一定の範囲で推移
                        
                        #### 重要なパターン
                        
                        **🔄 反転パターン**
                        - ダブルトップ・ダブルボトム
                        - ヘッド&ショルダー
                        
                        **➡️ 継続パターン**
                        - 三角保ち合い
                        - フラッグ・ペナント
                        """,
                        "chart_reading",
                        "tech_002"
                    ),
                    TutorialStep(
                        "tech_002",
                        "移動平均線",
                        "トレンドを把握する基本指標",
                        """
                        ### 📈 移動平均線とは？
                        
                        移動平均線は**過去n日間の終値の平均**を線で結んだものです。
                        
                        #### よく使われる期間
                        
                        - **25日線**: 短期トレンド
                        - **75日線**: 中期トレンド  
                        - **200日線**: 長期トレンド
                        
                        #### 移動平均線の使い方
                        
                        **📊 トレンド判断**
                        - 移動平均線が上向き → 上昇トレンド
                        - 移動平均線が下向き → 下降トレンド
                        
                        **🎯 売買シグナル**
                        - 株価が移動平均線を上抜け → 買いシグナル
                        - 株価が移動平均線を下抜け → 売りシグナル
                        
                        #### ゴールデンクロス・デッドクロス
                        
                        **🌟 ゴールデンクロス（買いシグナル）**
                        - 短期線が長期線を下から上に抜ける
                        - 例：25日線が75日線を上抜け
                        
                        **💀 デッドクロス（売りシグナル）**
                        - 短期線が長期線を上から下に抜ける
                        - 例：25日線が75日線を下抜け
                        
                        #### 注意点
                        
                        ⚠️ **だましがある**
                        - 短期的な上抜け・下抜けに注意
                        - 複数の指標で確認することが重要
                        """,
                        "ma_practice",
                        "tech_003"
                    ),
                    TutorialStep(
                        "tech_003",
                        "RSIとMACDの活用",
                        "オシレーター系指標で売買タイミングを判断",
                        """
                        ### 📊 RSI（相対力指数）
                        
                        RSIは**買われ過ぎ・売られ過ぎを判断**する指標です。
                        
                        #### RSIの見方
                        
                        **数値の意味**
                        - 0-100の値で推移
                        - 70以上：買われ過ぎ（売りシグナル）
                        - 30以下：売られ過ぎ（買いシグナル）
                        
                        **🎯 売買シグナル**
                        - RSI > 70 → 売り検討
                        - RSI < 30 → 買い検討
                        
                        ### 📊 MACD
                        
                        MACDは**トレンドの変化を捉える**指標です。
                        
                        #### MACDの構成
                        
                        - **MACDライン**: 短期EMA - 長期EMA
                        - **シグナルライン**: MACDの移動平均
                        - **ヒストグラム**: MACD - シグナル
                        
                        #### 売買シグナル
                        
                        **🌟 買いシグナル**
                        - MACDがシグナル線を上抜け
                        - ヒストグラムがプラス転換
                        
                        **💀 売りシグナル**
                        - MACDがシグナル線を下抜け
                        - ヒストグラムがマイナス転換
                        
                        #### 組み合わせて使う
                        
                        📊 **複数指標での確認**
                        1. トレンド方向（移動平均線）
                        2. 買われ過ぎ・売られ過ぎ（RSI）
                        3. 転換点（MACD）
                        
                        **例：買いの条件**
                        - 25日線が上向き
                        - RSI < 30から回復
                        - MACDがゴールデンクロス
                        """,
                        "oscillator_practice",
                        None
                    )
                ]
            },
            
            "risk_management": {
                "title": "⚖️ リスク管理",
                "description": "損失を抑える投資戦略",
                "difficulty": "中級",
                "duration": "約20分",
                "steps": [
                    TutorialStep(
                        "risk_001",
                        "リスクの種類",
                        "投資にはどんなリスクがあるか",
                        """
                        ### ⚠️ 投資のリスクを理解しよう
                        
                        投資には様々なリスクがあります。**リスクを知ることがリスク管理の第一歩**です。
                        
                        #### 主なリスクの種類
                        
                        **1. 🏢 信用リスク**
                        - 企業の倒産・業績悪化
                        - 対策：財務健全性をチェック
                        
                        **2. 🌍 市場リスク**
                        - 全体的な株価下落
                        - 対策：分散投資、長期投資
                        
                        **3. 💱 為替リスク**
                        - 外国株投資時の為替変動
                        - 対策：通貨分散
                        
                        **4. 💧 流動性リスク**
                        - 売りたい時に売れない
                        - 対策：出来高の多い銘柄選択
                        
                        **5. 📈 ボラティリティリスク**
                        - 価格変動の激しさ
                        - 対策：リスク許容度に応じた投資
                        
                        #### リスクとリターンの関係
                        
                        💡 **基本原則：ハイリスク・ハイリターン**
                        
                        | 投資対象 | リスク | 期待リターン |
                        |----------|--------|--------------|
                        | 預金 | 極低 | 0.01% |
                        | 国債 | 低 | 0.5-1% |
                        | 投資信託 | 中 | 3-7% |
                        | 個別株 | 高 | 5-15% |
                        | 新興株 | 極高 | -50%〜+100% |
                        """,
                        "risk_assessment",
                        "risk_002"
                    ),
                    TutorialStep(
                        "risk_002",
                        "分散投資",
                        "「卵は一つのカゴに盛るな」",
                        """
                        ### 🗂️ 分散投資でリスクを軽減
                        
                        分散投資は**投資の基本中の基本**です。
                        
                        #### 分散の種類
                        
                        **1. 🏢 銘柄分散**
                        - 複数の会社に投資
                        - 1つの会社が悪くなっても影響を限定
                        
                        **2. 🏭 業種分散**
                        - 異なる業界に投資
                        - IT、金融、製造業、小売など
                        
                        **3. 🌍 地域分散**
                        - 国内外に投資
                        - 日本、米国、欧州、新興国
                        
                        **4. ⏰ 時間分散**
                        - 購入時期を分散
                        - 毎月定額購入（ドルコスト平均法）
                        
                        #### 分散投資の効果
                        
                        **例：3銘柄への分散投資**
                        
                        | シナリオ | A社 | B社 | C社 | 平均 |
                        |----------|-----|-----|-----|------|
                        | 好調時 | +30% | +10% | +5% | +15% |
                        | 不調時 | -20% | -5% | +2% | -7.7% |
                        
                        集中投資ならA社だけで-20%の損失
                        分散投資なら-7.7%に損失を抑制
                        
                        #### 簡単な分散投資方法
                        
                        **🌟 投資信託・ETF活用**
                        - 1つの商品で数百〜数千銘柄に分散
                        - 例：日経225、S&P500連動商品
                        - 少額から始められる
                        
                        **🎯 目安：最低でも10銘柄以上**
                        """,
                        "diversification_game",
                        "risk_003"
                    ),
                    TutorialStep(
                        "risk_003",
                        "損切りと利確",
                        "感情に惑わされない売買ルール",
                        """
                        ### ✂️ 損切り（ストップロス）
                        
                        損切りは**損失の拡大を防ぐ重要な手法**です。
                        
                        #### 損切りの基本ルール
                        
                        **📉 価格ベース**
                        - 購入価格の-10%で損切り
                        - 例：1000円で購入 → 900円で売却
                        
                        **📊 テクニカルベース**
                        - サポートライン割れで損切り
                        - 移動平均線割れで損切り
                        
                        **⏰ 時間ベース**
                        - 3ヶ月経っても利益が出ない場合
                        
                        #### 損切りができない心理
                        
                        😰 **よくある心理**
                        - 「もう少し待てば戻るかも」
                        - 「損を確定させたくない」
                        - 「今売ったら負けを認めることになる」
                        
                        💡 **対策**
                        - 購入時に損切り価格を決める
                        - 自動売買注文を活用
                        - 投資日記で感情を記録
                        
                        ### 📈 利確（利益確定）
                        
                        #### 利確の方法
                        
                        **🎯 目標価格設定**
                        - 購入価格の+20%で半分売却
                        - +50%で残り半分売却
                        
                        **📊 段階的利確**
                        - 利益の出ている部分を徐々に売却
                        - リスクを段階的に軽減
                        
                        **⏰ 期間ベース**
                        - 1年保有で一部利確
                        - 年末の税務調整
                        
                        #### 利確・損切りの実例
                        
                        **例：1000円で100株購入**
                        - 900円（-10%）: 全株損切り
                        - 1200円（+20%）: 50株利確
                        - 1500円（+50%）: 残り50株利確
                        
                        💡 **重要**: ルールを決めたら感情に左右されず実行！
                        """,
                        "stop_loss_game",
                        None
                    )
                ]
            }
        }
    
    def display(self):
        """メイン表示"""
        st.header("🎓 インタラクティブチュートリアル")
        
        # チュートリアル選択
        if st.session_state.current_tutorial is None:
            self._display_tutorial_selection()
        else:
            self._display_tutorial_content()
    
    def _display_tutorial_selection(self):
        """チュートリアル選択画面"""
        st.subheader("📚 学習コースを選択してください")
        
        for tutorial_id, tutorial_data in self.tutorials.items():
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.markdown(f"### {tutorial_data['title']}")
                    st.write(tutorial_data['description'])
                
                with col2:
                    difficulty_color = {
                        "初級": "🟢",
                        "中級": "🟡", 
                        "上級": "🔴"
                    }
                    st.write(f"**難易度**")
                    st.write(f"{difficulty_color.get(tutorial_data['difficulty'], '⚪')} {tutorial_data['difficulty']}")
                
                with col3:
                    st.write(f"**所要時間**")
                    st.write(tutorial_data['duration'])
                
                with col4:
                    # 進捗表示
                    progress = st.session_state.tutorial_progress.get(tutorial_id, 0)
                    total_steps = len(tutorial_data['steps'])
                    st.write(f"**進捗**")
                    st.write(f"{progress}/{total_steps}")
                    
                    if st.button(f"📖 開始", key=f"start_{tutorial_id}"):
                        st.session_state.current_tutorial = tutorial_id
                        st.session_state.current_step = st.session_state.tutorial_progress.get(tutorial_id, 0)
                        st.rerun()
                
                st.markdown("---")
    
    def _display_tutorial_content(self):
        """チュートリアル内容表示"""
        tutorial_id = st.session_state.current_tutorial
        tutorial_data = self.tutorials[tutorial_id]
        current_step_index = st.session_state.current_step
        
        # ヘッダー
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.subheader(f"📖 {tutorial_data['title']}")
        
        with col2:
            progress = (current_step_index + 1) / len(tutorial_data['steps'])
            st.progress(progress, text=f"進捗: {current_step_index + 1}/{len(tutorial_data['steps'])}")
        
        with col3:
            if st.button("📚 コース一覧に戻る"):
                st.session_state.current_tutorial = None
                st.session_state.current_step = 0
                st.rerun()
        
        # 現在のステップ
        if current_step_index < len(tutorial_data['steps']):
            current_step = tutorial_data['steps'][current_step_index]
            
            st.markdown("---")
            st.markdown(f"## ステップ {current_step_index + 1}: {current_step.title}")
            st.info(current_step.description)
            
            # コンテンツ表示
            st.markdown(current_step.content)
            
            # インタラクティブ要素
            if current_step.interactive_element:
                st.markdown("---")
                self._display_interactive_element(current_step.interactive_element, current_step)
            
            # ナビゲーション
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if current_step_index > 0:
                    if st.button("⬅️ 前のステップ"):
                        st.session_state.current_step -= 1
                        st.rerun()
            
            with col2:
                if st.button("💾 進捗を保存"):
                    st.session_state.tutorial_progress[tutorial_id] = current_step_index + 1
                    st.success("進捗を保存しました！")
            
            with col3:
                if current_step_index < len(tutorial_data['steps']) - 1:
                    if st.button("➡️ 次のステップ"):
                        st.session_state.current_step += 1
                        st.session_state.tutorial_progress[tutorial_id] = st.session_state.current_step
                        st.rerun()
                else:
                    if st.button("🎉 完了"):
                        st.balloons()
                        st.success("🎉 チュートリアル完了！お疲れ様でした！")
                        st.session_state.tutorial_progress[tutorial_id] = len(tutorial_data['steps'])
                        st.session_state.current_tutorial = None
                        st.session_state.current_step = 0
                        st.rerun()
        
        else:
            st.success("🎉 このチュートリアルは完了しています！")
    
    def _display_interactive_element(self, element_type: str, step: TutorialStep):
        """インタラクティブ要素表示"""
        st.markdown("### 🎮 実践練習")
        
        if element_type == "quiz":
            self._display_quiz(step)
        elif element_type == "calculation":
            self._display_calculation(step)
        elif element_type == "checklist":
            self._display_checklist(step)
        elif element_type == "calculator":
            self._display_calculator(step)
        elif element_type == "simulation":
            self._display_simulation(step)
        elif element_type == "chart_reading":
            self._display_chart_reading(step)
        elif element_type == "ma_practice":
            self._display_ma_practice(step)
        elif element_type == "oscillator_practice":
            self._display_oscillator_practice(step)
        elif element_type == "risk_assessment":
            self._display_risk_assessment(step)
        elif element_type == "diversification_game":
            self._display_diversification_game(step)
        elif element_type == "stop_loss_game":
            self._display_stop_loss_game(step)
    
    def _display_quiz(self, step: TutorialStep):
        """クイズ表示"""
        st.markdown("#### 💡 理解度チェック")
        
        if step.step_id == "basic_001":
            question = "投資と貯金の最も大きな違いは何ですか？"
            options = [
                "投資の方が金額が大きい",
                "投資にはリスクがあるが、リターンも期待できる", 
                "投資は男性がするもの",
                "投資の方が手続きが簡単"
            ]
            
            answer = st.radio(question, options)
            
            if st.button("回答確認"):
                if answer == options[1]:
                    st.success("✅ 正解！投資はリスクを取る代わりに、より高いリターンを期待できます。")
                else:
                    st.error("❌ 不正解。投資の最大の特徴は「リスクとリターンのトレードオフ」です。")
    
    def _display_calculation(self, step: TutorialStep):
        """計算練習"""
        st.markdown("#### 🧮 計算してみよう")
        
        if step.step_id == "basic_002":
            st.write("**問題**: 1000円で100株買った株が1200円になりました。")
            st.write("1. キャピタルゲインはいくらですか？")
            st.write("2. 年間配当が1株50円の場合、インカムゲインはいくらですか？")
            
            col1, col2 = st.columns(2)
            
            with col1:
                capital_gain = st.number_input("キャピタルゲイン（円）", min_value=0)
            
            with col2:
                income_gain = st.number_input("インカムゲイン（円）", min_value=0)
            
            if st.button("計算結果確認"):
                if capital_gain == 20000 and income_gain == 5000:
                    st.success("✅ 正解！キャピタルゲイン: (1200-1000)×100 = 20,000円、インカムゲイン: 50×100 = 5,000円")
                else:
                    st.error("❌ 再計算してみてください。キャピタルゲイン = (新価格-旧価格)×株数、インカムゲイン = 配当×株数")
    
    def _display_checklist(self, step: TutorialStep):
        """チェックリスト"""
        st.markdown("#### ✅ 準備チェックリスト")
        
        if step.step_id == "basic_003":
            items = [
                "本人確認書類（免許証・保険証など）を準備した",
                "マイナンバー書類を準備した",
                "メールアドレスを確認した",
                "銀行口座情報を準備した",
                "NISAについて調べた"
            ]
            
            checked_items = []
            for item in items:
                if st.checkbox(item):
                    checked_items.append(item)
            
            progress = len(checked_items) / len(items)
            st.progress(progress, text=f"準備完了度: {len(checked_items)}/{len(items)}")
            
            if len(checked_items) == len(items):
                st.success("🎉 口座開設の準備が整いました！")
    
    def _display_calculator(self, step: TutorialStep):
        """投資計算機"""
        st.markdown("#### 💰 投資シミュレーション")
        
        if step.step_id == "basic_004":
            col1, col2 = st.columns(2)
            
            with col1:
                monthly_amount = st.slider("月投資額（万円）", 1, 10, 3)
                annual_return = st.slider("年利（%）", 1, 10, 5)
                years = st.slider("投資期間（年）", 5, 30, 20)
            
            with col2:
                # 複利計算
                total_invested = monthly_amount * 10000 * 12 * years
                future_value = monthly_amount * 10000 * 12 * (((1 + annual_return/100)**(years) - 1) / (annual_return/100))
                profit = future_value - total_invested
                
                st.metric("総投資額", f"{total_invested:,.0f}円")
                st.metric("最終資産額", f"{future_value:,.0f}円")
                st.metric("利益", f"{profit:,.0f}円", delta=f"+{(profit/total_invested)*100:.1f}%")
    
    def _display_simulation(self, step: TutorialStep):
        """投資シミュレーション"""
        st.markdown("#### 🎮 投資体験ゲーム")
        st.info("シミュレーション練習モードタブで実際の取引を体験してみましょう！")
    
    def _display_chart_reading(self, step: TutorialStep):
        """チャート読解練習"""
        st.markdown("#### 📊 チャート読解練習")
        st.info("実際のチャート分析はチャート分析タブで練習できます。")
    
    def _display_ma_practice(self, step: TutorialStep):
        """移動平均線練習"""
        st.markdown("#### 📈 移動平均線判定練習")
        st.info("シグナル分析タブで移動平均線の実践的な使い方を学べます。")
    
    def _display_oscillator_practice(self, step: TutorialStep):
        """オシレーター練習"""
        st.markdown("#### 📊 オシレーター判定練習")
        st.info("テクニカル指標の詳細な使い方はシグナル分析タブで実践できます。")
    
    def _display_risk_assessment(self, step: TutorialStep):
        """リスク評価"""
        st.markdown("#### ⚖️ リスク許容度診断")
        
        questions = [
            ("年齢は？", ["20代", "30代", "40代", "50代以上"]),
            ("投資経験は？", ["なし", "1年未満", "1-5年", "5年以上"]),
            ("投資目標は？", ["短期利益", "中期成長", "長期資産形成", "老後資金"]),
            ("損失許容度は？", ["絶対に損したくない", "5%まで", "20%まで", "50%まで"])
        ]
        
        answers = []
        for i, (question, options) in enumerate(questions):
            answer = st.radio(f"{i+1}. {question}", options, key=f"risk_q_{i}")
            answers.append(answer)
        
        if st.button("リスク許容度判定"):
            # 簡易的な判定ロジック
            risk_score = 0
            if "20代" in answers[0]: risk_score += 3
            elif "30代" in answers[0]: risk_score += 2
            elif "40代" in answers[0]: risk_score += 1
            
            if "5年以上" in answers[1]: risk_score += 3
            elif "1-5年" in answers[1]: risk_score += 2
            elif "1年未満" in answers[1]: risk_score += 1
            
            if "長期資産形成" in answers[2]: risk_score += 3
            elif "中期成長" in answers[2]: risk_score += 2
            
            if "50%まで" in answers[3]: risk_score += 3
            elif "20%まで" in answers[3]: risk_score += 2
            elif "5%まで" in answers[3]: risk_score += 1
            
            if risk_score >= 8:
                st.success("🔴 高リスク許容型：成長株投資や個別株投資に適しています")
            elif risk_score >= 5:
                st.info("🟡 中リスク許容型：バランス型投資信託やETFがおすすめ")
            else:
                st.warning("🟢 低リスク許容型：債券中心やインデックス投資から始めましょう")
    
    def _display_diversification_game(self, step: TutorialStep):
        """分散投資ゲーム"""
        st.markdown("#### 🎯 分散投資シミュレーション")
        
        st.write("100万円を以下の投資先に配分してください：")
        
        allocations = {}
        categories = ["日本大型株", "日本小型株", "米国株", "欧州株", "新興国株", "債券", "現金"]
        
        total_allocation = 0
        for category in categories:
            allocation = st.slider(f"{category}（%）", 0, 100, 0, key=f"alloc_{category}")
            allocations[category] = allocation
            total_allocation += allocation
        
        st.write(f"総配分: {total_allocation}%")
        
        if total_allocation == 100:
            st.success("✅ 配分完了！")
            
            # 簡易的なリスク・リターン計算
            risk_weights = {"日本大型株": 0.8, "日本小型株": 1.2, "米国株": 0.9, "欧州株": 0.9, "新興国株": 1.5, "債券": 0.3, "現金": 0}
            return_weights = {"日本大型株": 0.06, "日本小型株": 0.08, "米国株": 0.07, "欧州株": 0.06, "新興国株": 0.09, "債券": 0.02, "現金": 0}
            
            portfolio_risk = sum(allocations[cat] * risk_weights[cat] for cat in categories) / 100
            portfolio_return = sum(allocations[cat] * return_weights[cat] for cat in categories) / 100
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("ポートフォリオリスク", f"{portfolio_risk:.2f}")
            with col2:
                st.metric("期待リターン", f"{portfolio_return:.1%}")
        
        elif total_allocation != 100:
            st.warning(f"⚠️ 配分が{total_allocation}%です。100%になるよう調整してください。")
    
    def _display_stop_loss_game(self, step: TutorialStep):
        """損切りゲーム"""
        st.markdown("#### ✂️ 損切り判断ゲーム")
        
        st.write("**シナリオ**: 1000円で購入した株が以下のように推移しています。")
        
        scenarios = [
            ("購入翌日", 950, "5%下落"),
            ("1週間後", 900, "10%下落"),
            ("1ヶ月後", 850, "15%下落"),
            ("3ヶ月後", 800, "20%下落")
        ]
        
        for time, price, change in scenarios:
            with st.expander(f"{time}: {price}円 ({change})"):
                st.write(f"現在価格: {price}円")
                st.write(f"含み損: {1000-price}円 ({change})")
                
                action = st.radio(
                    "あなたの行動は？",
                    ["保有継続", "損切り売却", "追加購入"],
                    key=f"action_{price}"
                )
                
                if action == "保有継続":
                    st.info("💭 「まだ戻る可能性がある」")
                elif action == "損切り売却":
                    st.warning("✂️ 損切り実行。損失を限定しました。")
                elif action == "追加購入":
                    st.error("⚠️ ナンピン買い。さらにリスクが増加します。")
        
        st.markdown("---")
        st.info("💡 **学習ポイント**: 事前に損切りルールを決めて、感情に左右されずに実行することが重要です。")


def render_education_tutorial_tab():
    """インタラクティブチュートリアルタブのレンダリング関数"""
    component = EducationTutorialComponent()
    component.display()


if __name__ == "__main__":
    render_education_tutorial_tab()