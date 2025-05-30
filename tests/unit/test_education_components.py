"""
教育・学習支援機能のユニットテスト
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import streamlit as st

from dashboard.components.education_glossary import EducationGlossaryComponent
from dashboard.components.education_simulation import (
    SimulationPosition, SimulationAccount, EducationSimulationComponent
)
from dashboard.components.education_cases import InvestmentCase, EducationCasesComponent
from dashboard.components.education_tutorial import TutorialStep, EducationTutorialComponent


class TestEducationGlossaryComponent:
    """投資用語集コンポーネントのテスト"""
    
    def test_glossary_initialization(self):
        """用語集の初期化テスト"""
        component = EducationGlossaryComponent()
        
        assert isinstance(component.glossary_data, dict)
        assert len(component.glossary_data) > 0
        
        # 基本的な用語が含まれているかチェック
        assert "株式" in component.glossary_data
        assert "PER" in component.glossary_data
        assert "移動平均線" in component.glossary_data
    
    def test_get_term_definition(self):
        """用語定義取得テスト"""
        component = EducationGlossaryComponent()
        
        # 存在する用語
        definition = component.get_term_definition("株式")
        assert definition is not None
        assert "企業の所有権" in definition
        
        # 存在しない用語
        definition = component.get_term_definition("存在しない用語")
        assert definition is None
    
    def test_search_terms(self):
        """用語検索テスト"""
        component = EducationGlossaryComponent()
        
        # 完全一致検索
        results = component.search_terms("株式")
        assert "株式" in results
        
        # 部分一致検索
        results = component.search_terms("平均")
        assert any("移動平均線" in term for term in results)
        
        # 存在しない用語
        results = component.search_terms("存在しない検索語")
        assert len(results) == 0
    
    def test_filter_terms(self):
        """用語フィルタリングテスト"""
        component = EducationGlossaryComponent()
        
        # カテゴリフィルタ
        filtered = component._filter_terms("", "基本用語", "全て")
        assert all(data["category"] == "基本用語" for data in filtered.values())
        
        # 難易度フィルタ
        filtered = component._filter_terms("", "全て", "初級")
        assert all(data["difficulty"] == "初級" for data in filtered.values())
        
        # 検索とフィルタの組み合わせ
        filtered = component._filter_terms("株式", "基本用語", "初級")
        assert len(filtered) >= 0


class TestSimulationComponents:
    """シミュレーション練習モードコンポーネントのテスト"""
    
    def test_simulation_position_creation(self):
        """ポジション作成テスト"""
        position = SimulationPosition(
            symbol="7203.T",
            shares=100,
            entry_price=1000.0,
            entry_time=datetime.now(),
            position_type="long"
        )
        
        assert position.symbol == "7203.T"
        assert position.shares == 100
        assert position.entry_price == 1000.0
        assert position.position_type == "long"
        assert position.is_open is True
    
    def test_position_pnl_calculation(self):
        """損益計算テスト"""
        position = SimulationPosition(
            symbol="7203.T",
            shares=100,
            entry_price=1000.0,
            entry_time=datetime.now(),
            position_type="long"
        )
        
        # ロングポジションの利益
        pnl = position.get_pnl(1200.0)
        assert pnl == 20000.0  # (1200-1000) * 100
        
        # ロングポジションの損失
        pnl = position.get_pnl(800.0)
        assert pnl == -20000.0  # (800-1000) * 100
        
        # リターン率
        return_rate = position.get_return_rate(1200.0)
        assert return_rate == 20.0  # 20%
    
    def test_position_close(self):
        """ポジションクローズテスト"""
        position = SimulationPosition(
            symbol="7203.T",
            shares=100,
            entry_price=1000.0,
            entry_time=datetime.now(),
            position_type="long"
        )
        
        exit_time = datetime.now()
        position.close_position(1200.0, exit_time)
        
        assert position.is_open is False
        assert position.exit_price == 1200.0
        assert position.exit_time == exit_time
    
    def test_simulation_account_initialization(self):
        """シミュレーション口座初期化テスト"""
        account = SimulationAccount(initial_balance=1000000)
        
        assert account.initial_balance == 1000000
        assert account.cash_balance == 1000000
        assert len(account.positions) == 0
        assert len(account.trade_history) == 0
    
    def test_buy_order(self):
        """買い注文テスト"""
        account = SimulationAccount(initial_balance=1000000)
        
        # 正常な買い注文
        success = account.buy("7203.T", 100, 1000.0, datetime.now())
        assert success is True
        assert len(account.positions) == 1
        assert account.cash_balance < 1000000  # 手数料込みで減少
        assert len(account.trade_history) == 1
        
        # 残高不足での買い注文
        success = account.buy("7203.T", 10000, 1000.0, datetime.now())
        assert success is False
    
    def test_sell_order(self):
        """売り注文テスト"""
        account = SimulationAccount(initial_balance=1000000)
        
        # まず買い注文
        account.buy("7203.T", 100, 1000.0, datetime.now())
        initial_balance = account.cash_balance
        
        # 売り注文
        success = account.sell("7203.T", 50, 1200.0, datetime.now())
        assert success is True
        assert account.cash_balance > initial_balance  # 売却代金受取
        
        # 保有株数以上の売り注文
        success = account.sell("7203.T", 100, 1200.0, datetime.now())
        assert success is False
    
    def test_commission_calculation(self):
        """手数料計算テスト"""
        account = SimulationAccount()
        
        # 小額取引
        commission = account._calculate_commission(30000)
        assert commission == 55
        
        # 中額取引
        commission = account._calculate_commission(150000)
        assert commission == 115
        
        # 高額取引
        commission = account._calculate_commission(1000000)
        assert commission == 1000000 * 0.0385 / 100
    
    def test_portfolio_value_calculation(self):
        """ポートフォリオ評価額計算テスト"""
        account = SimulationAccount(initial_balance=1000000)
        
        # ポジションなしの場合
        portfolio_value = account.get_portfolio_value({})
        assert portfolio_value == 1000000
        
        # ポジションありの場合
        account.buy("7203.T", 100, 1000.0, datetime.now())
        current_prices = {"7203.T": 1200.0}
        portfolio_value = account.get_portfolio_value(current_prices)
        
        expected_value = account.cash_balance + (100 * 1200.0)
        assert portfolio_value == expected_value


class TestEducationCasesComponent:
    """投資事例学習コンポーネントのテスト"""
    
    def test_investment_case_creation(self):
        """投資事例作成テスト"""
        case = InvestmentCase(
            case_id="test_001",
            title="テスト事例",
            case_type="success",
            difficulty="初級",
            description="テスト用の投資事例",
            background="テスト背景",
            decision_points=["判断1", "判断2"],
            outcome="成功結果",
            lessons=["学習1", "学習2"]
        )
        
        assert case.case_id == "test_001"
        assert case.title == "テスト事例"
        assert case.case_type == "success"
        assert case.difficulty == "初級"
        assert len(case.decision_points) == 2
        assert len(case.lessons) == 2
    
    def test_cases_component_initialization(self):
        """事例学習コンポーネント初期化テスト"""
        component = EducationCasesComponent()
        
        assert isinstance(component.cases, list)
        assert len(component.cases) > 0
        
        # 成功・失敗事例の両方が含まれているかチェック
        success_cases = [case for case in component.cases if case.case_type == "success"]
        failure_cases = [case for case in component.cases if case.case_type == "failure"]
        
        assert len(success_cases) > 0
        assert len(failure_cases) > 0
    
    def test_filter_cases(self):
        """事例フィルタリングテスト"""
        component = EducationCasesComponent()
        
        # 成功事例フィルタ
        filtered = component._filter_cases("成功事例", "全て")
        assert all(case.case_type == "success" for case in filtered)
        
        # 失敗事例フィルタ
        filtered = component._filter_cases("失敗事例", "全て")
        assert all(case.case_type == "failure" for case in filtered)
        
        # 難易度フィルタ
        filtered = component._filter_cases("全て", "初級")
        assert all(case.difficulty == "初級" for case in filtered)


class TestEducationTutorialComponent:
    """インタラクティブチュートリアルコンポーネントのテスト"""
    
    def test_tutorial_step_creation(self):
        """チュートリアルステップ作成テスト"""
        step = TutorialStep(
            step_id="test_001",
            title="テストステップ",
            description="テスト説明",
            content="テストコンテンツ",
            interactive_element="quiz",
            next_step="test_002"
        )
        
        assert step.step_id == "test_001"
        assert step.title == "テストステップ"
        assert step.description == "テスト説明"
        assert step.content == "テストコンテンツ"
        assert step.interactive_element == "quiz"
        assert step.next_step == "test_002"
    
    def test_tutorial_component_initialization(self):
        """チュートリアルコンポーネント初期化テスト"""
        # session_stateのモックを適切に設定
        with patch('streamlit.session_state', create=True) as mock_session_state:
            # session_stateを辞書のように動作させる
            mock_session_state.__contains__ = lambda self, key: False
            mock_session_state.__setitem__ = lambda self, key, value: None
            mock_session_state.__getitem__ = lambda self, key: {}
            
            component = EducationTutorialComponent()
            
            assert isinstance(component.tutorials, dict)
            assert len(component.tutorials) > 0
            
            # 基本的なチュートリアルが含まれているかチェック
            assert "basic_investment" in component.tutorials
            assert "technical_analysis" in component.tutorials
            assert "risk_management" in component.tutorials
    
    def test_tutorial_structure(self):
        """チュートリアル構造テスト"""
        component = EducationTutorialComponent()
        
        for tutorial_id, tutorial_data in component.tutorials.items():
            # 必須フィールドのチェック
            assert "title" in tutorial_data
            assert "description" in tutorial_data
            assert "difficulty" in tutorial_data
            assert "duration" in tutorial_data
            assert "steps" in tutorial_data
            
            # ステップが正しく定義されているかチェック
            assert len(tutorial_data["steps"]) > 0
            for step in tutorial_data["steps"]:
                assert isinstance(step, TutorialStep)
                assert step.step_id is not None
                assert step.title is not None
                assert step.content is not None


class TestIntegrationEducationComponents:
    """教育コンポーネント統合テスト"""
    
    def test_components_work_together(self):
        """コンポーネント間の連携テスト"""
        # 各コンポーネントの初期化
        glossary_component = EducationGlossaryComponent()
        simulation_component = EducationSimulationComponent()
        cases_component = EducationCasesComponent()
        tutorial_component = EducationTutorialComponent()
        
        # 用語集からシミュレーションで使用する用語を検索
        risk_terms = glossary_component.search_terms("リスク")
        assert len(risk_terms) > 0
        
        # シミュレーションでのポジション作成
        account = SimulationAccount()
        success = account.buy("7203.T", 100, 1000.0, datetime.now())
        assert success is True
        
        # 事例学習で関連ケースを検索
        success_cases = cases_component._filter_cases("成功事例", "全て")
        assert len(success_cases) > 0
        
        # チュートリアルの存在確認
        basic_tutorial = tutorial_component.tutorials.get("basic_investment")
        assert basic_tutorial is not None
        assert len(basic_tutorial["steps"]) > 0
    
    def test_session_state_management(self):
        """セッション状態管理テスト"""
        # session_stateのモックを適切に設定
        with patch('streamlit.session_state', create=True) as mock_session_state:
            # session_stateを辞書のように動作させる
            mock_session_state.__contains__ = lambda self, key: False
            mock_session_state.__setitem__ = lambda self, key, value: None
            mock_session_state.__getitem__ = lambda self, key: {}
            
            simulation_component = EducationSimulationComponent()
            tutorial_component = EducationTutorialComponent()
            
            # session_stateがモックされているため、エラーが出ないことを確認
            assert simulation_component is not None
            assert tutorial_component is not None


if __name__ == "__main__":
    pytest.main([__file__])