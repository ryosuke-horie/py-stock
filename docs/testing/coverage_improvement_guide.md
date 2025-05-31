# テストカバレッジ向上ガイド

## 📋 概要

このドキュメントは、py-stockプロジェクトのテストカバレッジを向上させるための具体的なガイドラインと推奨事項をまとめています。

現在のカバレッジ状況：**70.80%** （目標：75%以上）

## 🎯 優先度別改善戦略

### 1. 🟢 簡単改善対象（80%以上のカバレッジ）

**対象ファイル**: 28ファイル

これらのファイルは既に高いカバレッジを達成しており、比較的簡単に100%に近づけることができます。

#### 改善手法
- **エッジケースの追加**: 境界値テストの追加
- **エラーハンドリングテスト**: 例外処理のテスト追加
- **条件分岐の完全カバー**: if-else文の全パターンテスト

#### 具体例
```python
# テスト不足例
def calculate_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:  # ← この分岐がテストされていない
        raise ValueError("Division by zero")
    return numerator / denominator

# 追加すべきテスト
def test_calculate_ratio_zero_division():
    with pytest.raises(ValueError, match="Division by zero"):
        calculate_ratio(10, 0)
```

### 2. 🟡 中程度改善対象（60-79%のカバレッジ）

**対象ファイル**: 7ファイル

#### 改善手法
- **設定パターンの多様化**: 異なる設定値でのテストケース追加
- **モックの活用**: 外部依存関係のモック化
- **パラメータ化テスト**: 複数パターンを効率的にテスト

#### 具体例
```python
# パラメータ化テストの活用
@pytest.mark.parametrize("input_value,expected", [
    (100, True),
    (0, False),
    (-50, False),
    (None, False),
])
def test_is_positive(input_value, expected):
    assert is_positive(input_value) == expected
```

### 3. 📚 examplesディレクトリの特殊処理

**対象ファイル**: 7ファイル（平均カバレッジ: 低）

examplesディレクトリは教育・デモ用途のため、低カバレッジは許容されますが、以下の点で改善可能です：

#### 改善手法
- **基本動作の確認テスト**: main関数が正常に実行できることの確認
- **重要ロジックの抽出**: 再利用可能な部分をライブラリ化してテスト
- **設定ファイルの検証**: 必要な設定項目が揃っているかの確認

## 🛠️ 具体的改善手順

### Step 1: 簡単改善対象から開始

1. カバレッジレポートで80%以上のファイルを特定
2. 未カバーライン（red lines）を確認
3. 不足しているテストパターンを特定
4. テストケースを追加

### Step 2: テストツールの活用

#### pytest-cov のオプション活用
```bash
# 未カバー行の詳細表示
uv run pytest --cov=src --cov-report=term-missing

# HTML レポートで視覚的確認
uv run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

#### coverage.py の活用
```bash
# 特定ファイルのみの詳細分析
uv run coverage report --show-missing src/technical_analysis/indicators.py
```

### Step 3: テストパターンの標準化

#### エラーハンドリングテストの標準パターン
```python
def test_function_with_invalid_input():
    """無効な入力に対するエラーハンドリングをテスト"""
    with pytest.raises(ValueError, match="Expected error message"):
        target_function(invalid_input)

def test_function_with_none_input():
    """None入力に対するエラーハンドリングをテスト"""
    with pytest.raises(TypeError):
        target_function(None)
```

#### 条件分岐テストの標準パターン
```python
def test_conditional_logic_all_branches():
    """すべての条件分岐をテスト"""
    # True分岐
    result_true = target_function(condition_true_input)
    assert result_true == expected_true_result
    
    # False分岐
    result_false = target_function(condition_false_input)
    assert result_false == expected_false_result
    
    # エッジケース
    result_edge = target_function(edge_case_input)
    assert result_edge == expected_edge_result
```

## 🎨 テスト作成のベストプラクティス

### 1. テストの命名規則
```python
def test_[function_name]_[scenario]_[expected_result]():
    """明確で説明的なテスト名を使用"""
    pass

# 良い例
def test_calculate_moving_average_with_valid_data_returns_correct_values():
    pass

def test_calculate_moving_average_with_insufficient_data_raises_value_error():
    pass
```

### 2. AAA パターンの活用
```python
def test_example():
    # Arrange: テストデータの準備
    input_data = [1, 2, 3, 4, 5]
    expected_result = 3.0
    
    # Act: テスト対象の実行
    result = calculate_average(input_data)
    
    # Assert: 結果の検証
    assert result == expected_result
```

### 3. フィクスチャの活用
```python
@pytest.fixture
def sample_stock_data():
    """テスト用の株価データを提供"""
    return pd.DataFrame({
        'close': [100, 105, 102, 108, 110],
        'volume': [1000, 1200, 800, 1500, 900]
    })

def test_technical_indicator(sample_stock_data):
    result = calculate_rsi(sample_stock_data)
    assert len(result) == len(sample_stock_data)
```

## 🚫 カバレッジ向上を困難にする要因

### 1. 外部依存関係
- **問題**: APIコール、ファイルアクセス、ネットワーク通信
- **解決策**: モックとスタブの活用

```python
@patch('module.external_api_call')
def test_function_with_external_dependency(mock_api):
    mock_api.return_value = mock_response
    result = function_under_test()
    assert result == expected_result
```

### 2. 複雑な設定依存
- **問題**: 多数の設定項目に依存する処理
- **解決策**: 設定のパラメータ化とデフォルト値の活用

### 3. 時間依存処理
- **問題**: 現在時刻や日付に依存する処理
- **解決策**: 時間のモック化

```python
@patch('module.datetime')
def test_time_dependent_function(mock_datetime):
    mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
    result = time_dependent_function()
    assert result == expected_result
```

## 📊 継続的改善

### 1. カバレッジモニタリング
- CI/CDでのカバレッジチェック
- 新機能追加時のカバレッジ要件設定
- 定期的なカバレッジレポート確認

### 2. カバレッジ目標設定
- **短期目標**: 75% (現在70.80%から+4.2%向上)
- **中期目標**: 80% 
- **長期目標**: 85% (examplesディレクトリ除く)

### 3. チーム内での共有
- カバレッジレポートの定期的なレビュー
- 低カバレッジファイルの優先的な改善
- テスト作成のナレッジ共有

## 🔧 自動化ツール

### カバレッジ分析スクリプトの活用
```bash
# 分析レポート生成
uv run python docs/testing/coverage_analyzer.py

# 生成されるファイル
# - docs/testing/coverage_analysis_report.md
# - docs/testing/coverage_data.json
```

### 継続的な監視
```bash
# カバレッジチェックの自動化
uv run pytest --cov=src --cov-fail-under=70
```

## 📝 チェックリスト

新しいテストを作成する際のチェックリスト：

- [ ] 正常系のテストケースが含まれている
- [ ] 異常系（エラーケース）のテストケースが含まれている
- [ ] 境界値のテストケースが含まれている
- [ ] すべての条件分岐がカバーされている
- [ ] 外部依存関係が適切にモック化されている
- [ ] テスト名が説明的である
- [ ] AAA パターンに従っている
- [ ] アサーションが明確である

このガイドラインに従って継続的にテストカバレッジを改善していくことで、より品質の高いソフトウェアを開発できます。