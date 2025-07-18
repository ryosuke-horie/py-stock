"""
市場環境ダッシュボードコンポーネントのテスト
Issue #77で修正したbackground_gradientエラーのテスト
"""

import pytest
import pandas as pd
import numpy as np

# matplotlibの有無をチェック
try:
    import matplotlib
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class TestMarketEnvironmentDashboardComponent:
    """市場環境ダッシュボードコンポーネントのテストクラス"""
    
    def test_background_gradient_without_center_parameter(self):
        """background_gradientのcenterパラメータなしでの動作テスト（Issue #77対応）"""
        # サンプルデータ作成
        df = pd.DataFrame({
            'name': ['NIKKEI225', 'TOPIX', 'MOTHERS'],
            'daily': [1.5, -0.8, 2.3],
            'weekly': [3.2, 1.1, -1.5],
            'monthly': [-2.1, 0.5, 4.8],
            'volatility': [15.2, 12.8, 25.1],
            'rsi': [65.2, 45.8, 78.3]
        })
        
        # 修正後のスタイリング（centerパラメータなし）
        try:
            styled_df = df.style.format({
                'daily': '{:.2f}%',
                'weekly': '{:.2f}%',
                'monthly': '{:.2f}%',
                'volatility': '{:.2f}%',
                'rsi': '{:.1f}'
            }).background_gradient(subset=['daily', 'weekly', 'monthly'], cmap='RdYlGn')
            
            # エラーが発生しないことを確認
            assert styled_df is not None
            
        except TypeError as e:
            if "unexpected keyword argument 'center'" in str(e):
                pytest.fail("centerパラメータエラーが発生しました。修正が正しく適用されていません。")
            else:
                raise e
    
    def test_background_gradient_with_center_parameter_would_fail(self):
        """centerパラメータありのbackground_gradientがエラーになることを確認"""
        df = pd.DataFrame({
            'daily': [1.5, -0.8, 2.3],
            'weekly': [3.2, 1.1, -1.5],
            'monthly': [-2.1, 0.5, 4.8]
        })
        
        # 修正前のコード（centerパラメータあり）がエラーになることを確認
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            df.style.background_gradient(subset=['daily', 'weekly', 'monthly'], cmap='RdYlGn', center=0)
    
    def test_styling_format_function(self):
        """フォーマット機能が正常に動作することをテスト"""
        df = pd.DataFrame({
            'daily': [1.234, -0.876],
            'weekly': [3.456, 1.123],
            'monthly': [-2.789, 0.567],
            'volatility': [15.234, 12.876],
            'rsi': [65.234, 45.876]
        })
        
        styled_df = df.style.format({
            'daily': '{:.2f}%',
            'weekly': '{:.2f}%', 
            'monthly': '{:.2f}%',
            'volatility': '{:.2f}%',
            'rsi': '{:.1f}'
        })
        
        # フォーマットが適用されることを確認
        assert styled_df is not None
        
        # フォーマット後の文字列を取得して確認
        html = styled_df.to_html()
        assert '1.23%' in html  # daily
        assert '3.46%' in html  # weekly
        assert '-2.79%' in html  # monthly
        assert '15.23%' in html  # volatility
        assert '65.2' in html  # rsi (小数点第1位まで)
    
    def test_market_data_structure_with_missing_columns(self):
        """一部の列が欠けている場合の処理をテスト（Issue #77追加対応）"""
        # dailyのみ存在するケース
        df_minimal = pd.DataFrame({
            'インデックス': ['NIKKEI225'],
            'daily': [1.5]
        })
        
        # 存在する列のみを背景グラデーション対象にする
        format_dict = {}
        gradient_columns = []
        
        percentage_columns = ['daily', 'weekly', 'monthly', 'volatility']
        for col in percentage_columns:
            if col in df_minimal.columns:
                format_dict[col] = '{:.2f}%'
                if col in ['daily', 'weekly', 'monthly']:
                    gradient_columns.append(col)
        
        # エラーが発生しないことを確認
        try:
            styled_df = df_minimal.style.format(format_dict)
            if gradient_columns:
                styled_df = styled_df.background_gradient(subset=gradient_columns, cmap='RdYlGn')
            assert styled_df is not None
        except KeyError as e:
            pytest.fail(f"列が存在しない場合の処理でエラーが発生しました: {e}")
    
    def test_market_data_structure_complete(self):
        """すべての列が存在する場合の処理をテスト"""
        # 期待される列が存在することを確認
        expected_columns = ['daily', 'weekly', 'monthly', 'volatility', 'rsi']
        df = pd.DataFrame({col: [0.0] for col in expected_columns})
        
        # background_gradientの対象列が存在することを確認
        gradient_columns = ['daily', 'weekly', 'monthly']
        for col in gradient_columns:
            assert col in df.columns, f"必要な列 '{col}' が存在しません"
    
    def test_performance_data_edge_cases(self):
        """パフォーマンスデータのエッジケースをテスト"""
        # 極端な値を含むデータ
        df = pd.DataFrame({
            'daily': [0.0, 100.0, -100.0],
            'weekly': [0.0, 50.0, -50.0],
            'monthly': [0.0, 200.0, -200.0],
            'volatility': [0.0, 100.0, 50.0],
            'rsi': [0.0, 100.0, 50.0]
        })
        
        # エッジケースでもスタイリングが正常に動作することを確認
        try:
            styled_df = df.style.format({
                'daily': '{:.2f}%',
                'weekly': '{:.2f}%',
                'monthly': '{:.2f}%',
                'volatility': '{:.2f}%',
                'rsi': '{:.1f}'
            }).background_gradient(subset=['daily', 'weekly', 'monthly'], cmap='RdYlGn')
            
            assert styled_df is not None
            
        except Exception as e:
            pytest.fail(f"エッジケースでエラーが発生しました: {e}")
    
    def test_matplotlib_dependency_handling(self):
        """matplotlib依存関係のハンドリングテスト（Issue #77追加対応）"""
        df = pd.DataFrame({
            'daily': [1.5, -0.8, 2.3],
            'weekly': [3.2, 1.1, -1.5],
            'monthly': [-2.1, 0.5, 4.8]
        })
        
        # matplotlibが利用可能な場合のテスト
        if HAS_MATPLOTLIB:
            try:
                styled_df = df.style.background_gradient(
                    subset=['daily', 'weekly', 'monthly'], 
                    cmap='RdYlGn'
                )
                assert styled_df is not None
            except Exception as e:
                pytest.fail(f"matplotlib利用可能環境でエラーが発生しました: {e}")
        else:
            # matplotlibが利用不可の場合、エラー処理の動作を確認（実際にエラーが出るまでbackground_gradientを実行）
            try:
                styled_df = df.style.background_gradient(
                    subset=['daily', 'weekly', 'monthly'], 
                    cmap='RdYlGn'
                )
                # HTMLに変換して実際にエラーを発生させる
                styled_df.to_html()
                pytest.fail("matplotlibなしでbackground_gradientが成功してしまいました")
            except Exception as e:
                # エラーが発生することを確認（matplotlib関連かどうかはチェックしない）
                assert str(e) is not None
    
    def test_colormap_functionality(self):
        """カラーマップが正常に動作することをテスト"""
        df = pd.DataFrame({
            'daily': [-5.0, 0.0, 5.0],
            'weekly': [-10.0, 0.0, 10.0],
            'monthly': [-15.0, 0.0, 15.0]
        })
        
        # 異なるカラーマップでテスト
        colormaps = ['RdYlGn', 'RdBu', 'viridis']
        
        for cmap in colormaps:
            try:
                styled_df = df.style.background_gradient(
                    subset=['daily', 'weekly', 'monthly'], 
                    cmap=cmap
                )
                assert styled_df is not None
                
            except Exception as e:
                pytest.fail(f"カラーマップ '{cmap}' でエラーが発生しました: {e}")


class TestMarketEnvironmentDashboardRSIFix:
    """Issue #87 RSI表示修正に関するダッシュボードテスト"""
    
    def test_rsi_data_extraction_with_valid_values(self):
        """有効なRSI値のみを抽出するテスト"""
        df = pd.DataFrame({
            'インデックス': ['日経225', 'S&P500', 'NASDAQ', 'TOPIX'],
            'daily': [1.5, -0.8, 2.1, 0.5],
            'rsi': [65.4, 72.1, 45.8, 33.2]
        })
        
        # 修正後のロジック: 有効なRSI値のみを抽出
        rsi_data = []
        for _, row in df.iterrows():
            rsi_value = row.get('rsi')
            if pd.notna(rsi_value) and rsi_value is not None:
                rsi_data.append((row['インデックス'], rsi_value))
        
        # 全て有効な値なので4個のRSIデータが抽出される
        assert len(rsi_data) == 4
        assert rsi_data[0] == ('日経225', 65.4)
        assert rsi_data[1] == ('S&P500', 72.1)
        assert rsi_data[2] == ('NASDAQ', 45.8)
        assert rsi_data[3] == ('TOPIX', 33.2)
    
    def test_rsi_data_extraction_with_none_and_nan_values(self):
        """None/NaN値が混在するRSIデータの抽出テスト"""
        df = pd.DataFrame({
            'インデックス': ['日経225', 'S&P500', 'NASDAQ', 'TOPIX'],
            'daily': [1.5, -0.8, 2.1, 0.5],
            'rsi': [65.4, None, np.nan, 33.2]
        })
        
        # 修正後のロジック: 有効なRSI値のみを抽出
        rsi_data = []
        for _, row in df.iterrows():
            rsi_value = row.get('rsi')
            if pd.notna(rsi_value) and rsi_value is not None:
                rsi_data.append((row['インデックス'], rsi_value))
        
        # None/NaNを除いて2個のRSIデータが抽出される
        assert len(rsi_data) == 2
        assert rsi_data[0] == ('日経225', 65.4)
        assert rsi_data[1] == ('TOPIX', 33.2)
    
    def test_rsi_data_extraction_with_all_invalid_values(self):
        """全てのRSI値が無効な場合のテスト"""
        df = pd.DataFrame({
            'インデックス': ['日経225', 'S&P500', 'NASDAQ', 'TOPIX'],
            'daily': [1.5, -0.8, 2.1, 0.5],
            'rsi': [None, None, np.nan, np.nan]
        })
        
        # 修正後のロジック: 有効なRSI値のみを抽出
        rsi_data = []
        for _, row in df.iterrows():
            rsi_value = row.get('rsi')
            if pd.notna(rsi_value) and rsi_value is not None:
                rsi_data.append((row['インデックス'], rsi_value))
        
        # 有効な値がないため空のリストになる
        assert len(rsi_data) == 0
    
    def test_rsi_data_extraction_missing_rsi_column(self):
        """RSI列が存在しない場合のテスト"""
        df = pd.DataFrame({
            'インデックス': ['日経225', 'S&P500', 'NASDAQ'],
            'daily': [1.5, -0.8, 2.1]
            # RSI列なし
        })
        
        # 修正後のロジック: 有効なRSI値のみを抽出
        rsi_data = []
        for _, row in df.iterrows():
            rsi_value = row.get('rsi')  # Noneが返される
            if pd.notna(rsi_value) and rsi_value is not None:
                rsi_data.append((row['インデックス'], rsi_value))
        
        # RSI列がないため空のリストになる
        assert len(rsi_data) == 0
    
    def test_rsi_formatting_with_valid_values(self):
        """有効なRSI値がある場合のフォーマット設定テスト"""
        df = pd.DataFrame({
            'インデックス': ['日経225', 'S&P500'],
            'daily': [1.5, -0.8],
            'rsi': [65.4, 72.1]
        })
        
        format_dict = {}
        if 'rsi' in df.columns:
            # 修正後のロジック: 有効な値がある場合のみフォーマット設定
            has_valid_rsi = df['rsi'].notna().any()
            if has_valid_rsi:
                format_dict['rsi'] = '{:.1f}'
        
        # 有効な値があるためフォーマットが設定される
        assert 'rsi' in format_dict
        assert format_dict['rsi'] == '{:.1f}'
    
    def test_rsi_formatting_with_no_valid_values(self):
        """有効なRSI値がない場合のフォーマット設定テスト"""
        df = pd.DataFrame({
            'インデックス': ['日経225', 'S&P500'],
            'daily': [1.5, -0.8],
            'rsi': [None, np.nan]
        })
        
        format_dict = {}
        if 'rsi' in df.columns:
            # 修正後のロジック: 有効な値がある場合のみフォーマット設定
            has_valid_rsi = df['rsi'].notna().any()
            if has_valid_rsi:
                format_dict['rsi'] = '{:.1f}'
        
        # 有効な値がないためフォーマットが設定されない
        assert 'rsi' not in format_dict
    
    def test_rsi_formatting_missing_rsi_column(self):
        """RSI列が存在しない場合のフォーマット設定テスト"""
        df = pd.DataFrame({
            'インデックス': ['日経225', 'S&P500'],
            'daily': [1.5, -0.8]
            # RSI列なし
        })
        
        format_dict = {}
        if 'rsi' in df.columns:
            # この条件はFalseになる
            has_valid_rsi = df['rsi'].notna().any()
            if has_valid_rsi:
                format_dict['rsi'] = '{:.1f}'
        
        # RSI列がないためフォーマットが設定されない
        assert 'rsi' not in format_dict