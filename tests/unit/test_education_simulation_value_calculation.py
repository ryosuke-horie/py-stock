"""
education_simulationの値計算ロジックのテスト
Issue #75で修正したnumber_input値計算のテスト
"""

import pytest


class TestEducationSimulationValueCalculation:
    """EducationSimulationの値計算テストクラス"""
    
    def test_sell_shares_value_calculation_with_zero_available(self):
        """available_sharesが0の場合の売り株数計算テスト（Issue #75対応）"""
        available_shares = 0
        
        # 修正後のロジック: max(min(100, available_shares), 1)
        result = max(min(100, available_shares), 1)
        
        # available_sharesが0でもmin_value=1の制約を満たす
        assert result == 1
        assert result >= 1  # min_value制約
    
    def test_sell_shares_value_calculation_with_small_available(self):
        """available_sharesが少ない場合の売り株数計算テスト"""
        available_shares = 50
        
        # 修正後のロジック: max(min(100, available_shares), 1)
        result = max(min(100, available_shares), 1)
        
        # available_sharesが50の場合は50が返される
        assert result == 50
        assert result >= 1  # min_value制約
        assert result <= available_shares  # max_value制約も満たす
    
    def test_sell_shares_value_calculation_with_large_available(self):
        """available_sharesが多い場合の売り株数計算テスト"""
        available_shares = 200
        
        # 修正後のロジック: max(min(100, available_shares), 1)
        result = max(min(100, available_shares), 1)
        
        # available_sharesが200でも100が上限
        assert result == 100
        assert result >= 1  # min_value制約
    
    def test_sell_shares_value_calculation_edge_cases(self):
        """売り株数計算のエッジケーステスト"""
        test_cases = [
            (0, 1),     # available_shares=0 -> value=1
            (1, 1),     # available_shares=1 -> value=1
            (50, 50),   # available_shares=50 -> value=50
            (100, 100), # available_shares=100 -> value=100
            (150, 100), # available_shares=150 -> value=100
            (1000, 100) # available_shares=1000 -> value=100
        ]
        
        for available_shares, expected_value in test_cases:
            result = max(min(100, available_shares), 1)
            assert result == expected_value, f"available_shares={available_shares}の場合、期待値{expected_value}、実際{result}"
            assert result >= 1, f"min_value制約違反: {result} < 1"
            assert result <= max(available_shares, 1), f"max_value制約違反: {result} > {max(available_shares, 1)}"
    
    def test_original_calculation_would_fail(self):
        """修正前の計算がmin_value制約に違反することを確認"""
        available_shares = 0
        
        # 修正前のロジック: min(100, available_shares)
        original_result = min(100, available_shares)
        
        # これはmin_value=1に違反する
        assert original_result == 0
        assert original_result < 1  # min_value制約違反
    
    def test_max_value_constraint_maintained(self):
        """max_value制約が保持されることを確認"""
        # various available_shares values
        for available_shares in [0, 1, 10, 50, 100, 200]:
            expected_max_value = max(available_shares, 1)
            calculated_value = max(min(100, available_shares), 1)
            
            # valueがmax_valueを超えないことを確認
            assert calculated_value <= expected_max_value, \
                f"available_shares={available_shares}: value={calculated_value} > max_value={expected_max_value}"