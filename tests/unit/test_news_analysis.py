"""
ニュース・センチメント分析機能のテスト

このテストファイルは、Issue #8で実装されたニュース・センチメント分析機能の
動作を検証するためのユニットテストです。
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from pathlib import Path
import asyncio
from datetime import datetime, timedelta
import json

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

class TestNewsAnalysisIntegration(unittest.TestCase):
    """ニュース分析統合テスト"""

    def setUp(self):
        """テストセットアップ"""
        self.test_symbol = "AAPL"
        self.test_japanese_symbol = "7203.T"

    def test_news_analysis_module_import(self):
        """ニュース分析モジュールのインポートテスト"""
        try:
            # Streamlitがない環境では基本的なダッシュボード構造のみテスト
            with patch.dict('sys.modules', {'streamlit': MagicMock()}):
                from dashboard.components.news_sentiment import get_demo_analysis_data
                demo_data = get_demo_analysis_data()
                self.assertIsInstance(demo_data, dict)
                self.assertIn("newsCount", demo_data)
                self.assertIn("sentimentSummary", demo_data)
            
        except ImportError as e:
            # Streamlit依存でテストが失敗する場合はスキップ
            self.skipTest(f"Streamlit環境が必要なテスト: {e}")

    def test_demo_analysis_data_structure(self):
        """デモ分析データの構造テスト"""
        try:
            with patch.dict('sys.modules', {'streamlit': MagicMock()}):
                from dashboard.components.news_sentiment import get_demo_analysis_data
        except ImportError:
            self.skipTest("Streamlit環境が必要なテスト")
        
        # 基本的なデモデータテスト
        demo_data = get_demo_analysis_data()
        
        # 必須フィールドの確認
        required_fields = [
            "symbol", "analysisDate", "newsCount", 
            "sentimentSummary", "importanceStatistics", "topNews", "investmentInsights"
        ]
        
        for field in required_fields:
            self.assertIn(field, demo_data, f"必須フィールド '{field}' が不足")
        
        # センチメント要約の構造確認
        sentiment_summary = demo_data["sentimentSummary"]
        sentiment_fields = ["averageScore", "overallSentiment", "positiveCount", "negativeCount", "neutralCount"]
        
        for field in sentiment_fields:
            self.assertIn(field, sentiment_summary, f"センチメント要約フィールド '{field}' が不足")
        
        # 重要度統計の構造確認
        importance_stats = demo_data["importanceStatistics"]
        importance_fields = ["averageImportance", "highImportanceCount", "criticalNewsCount"]
        
        for field in importance_fields:
            self.assertIn(field, importance_stats, f"重要度統計フィールド '{field}' が不足")

    def test_demo_data_with_different_symbols(self):
        """異なる銘柄でのデモデータテスト"""
        try:
            with patch.dict('sys.modules', {'streamlit': MagicMock()}):
                from dashboard.components.news_sentiment import get_demo_analysis_data
        except ImportError:
            self.skipTest("Streamlit環境が必要なテスト")
        
        # 米国株のテスト
        us_data = get_demo_analysis_data("AAPL", 7, "both")
        self.assertEqual(us_data["symbol"], "AAPL")
        self.assertGreater(us_data["newsCount"], 0)
        
        # 日本株のテスト
        jp_data = get_demo_analysis_data("7203.T", 3, "ja")
        self.assertEqual(jp_data["symbol"], "7203.T")
        self.assertGreater(jp_data["newsCount"], 0)
        
        # トップニュースの確認
        for data in [us_data, jp_data]:
            top_news = data["topNews"]
            self.assertIsInstance(top_news, list)
            self.assertGreater(len(top_news), 0)
            
            # 最初のニュースアイテムの構造確認
            first_news = top_news[0]
            news_fields = ["id", "title", "content", "url", "publishedAt", "source", "language", "category", "sentiment", "importance"]
            
            for field in news_fields:
                self.assertIn(field, first_news, f"ニュースアイテムフィールド '{field}' が不足")

    def test_sentiment_score_ranges(self):
        """センチメントスコアの範囲テスト"""
        try:
            with patch.dict('sys.modules', {'streamlit': MagicMock()}):
                from dashboard.components.news_sentiment import get_demo_analysis_data
        except ImportError:
            self.skipTest("Streamlit環境が必要なテスト")
        
        demo_data = get_demo_analysis_data()
        
        # センチメントスコアの範囲確認 (-1.0 to 1.0)
        avg_score = demo_data["sentimentSummary"]["averageScore"]
        self.assertGreaterEqual(avg_score, -1.0, "センチメントスコアが下限を超えています")
        self.assertLessEqual(avg_score, 1.0, "センチメントスコアが上限を超えています")
        
        # 各ニュースアイテムのセンチメントスコア確認
        for news in demo_data["topNews"]:
            sentiment_score = news["sentiment"]["score"]
            self.assertGreaterEqual(sentiment_score, -1.0, f"ニュース '{news['title']}' のスコアが範囲外")
            self.assertLessEqual(sentiment_score, 1.0, f"ニュース '{news['title']}' のスコアが範囲外")

    def test_importance_score_ranges(self):
        """重要度スコアの範囲テスト"""
        try:
            with patch.dict('sys.modules', {'streamlit': MagicMock()}):
                from dashboard.components.news_sentiment import get_demo_analysis_data
        except ImportError:
            self.skipTest("Streamlit環境が必要なテスト")
        
        demo_data = get_demo_analysis_data()
        
        # 重要度スコアの範囲確認 (0 to 100)
        avg_importance = demo_data["importanceStatistics"]["averageImportance"]
        self.assertGreaterEqual(avg_importance, 0, "重要度スコアが下限を超えています")
        self.assertLessEqual(avg_importance, 100, "重要度スコアが上限を超えています")
        
        # 各ニュースアイテムの重要度スコア確認
        for news in demo_data["topNews"]:
            importance_score = news["importance"]["overallScore"]
            self.assertGreaterEqual(importance_score, 0, f"ニュース '{news['title']}' の重要度が範囲外")
            self.assertLessEqual(importance_score, 100, f"ニュース '{news['title']}' の重要度が範囲外")

    def test_investment_insights_generation(self):
        """投資判断示唆の生成テスト"""
        try:
            with patch.dict('sys.modules', {'streamlit': MagicMock()}):
                from dashboard.components.news_sentiment import get_demo_analysis_data
        except ImportError:
            self.skipTest("Streamlit環境が必要なテスト")
        
        demo_data = get_demo_analysis_data()
        
        insights = demo_data["investmentInsights"]
        self.assertIsInstance(insights, list, "投資判断示唆はリスト形式である必要があります")
        self.assertGreater(len(insights), 0, "少なくとも1つの投資判断示唆が必要です")
        
        # 各示唆が文字列であることを確認
        for insight in insights:
            self.assertIsInstance(insight, str, "投資判断示唆は文字列である必要があります")
            self.assertGreater(len(insight), 10, "投資判断示唆は十分な長さが必要です")

    def test_news_categories(self):
        """ニュースカテゴリの妥当性テスト"""
        try:
            with patch.dict('sys.modules', {'streamlit': MagicMock()}):
                from dashboard.components.news_sentiment import get_demo_analysis_data
        except ImportError:
            self.skipTest("Streamlit環境が必要なテスト")
        
        demo_data = get_demo_analysis_data()
        
        valid_categories = ["earnings", "ma", "dividend", "forecast", "partnership", "general"]
        
        for news in demo_data["topNews"]:
            category = news["category"]
            self.assertIn(category, valid_categories, f"無効なカテゴリ: {category}")

    def test_language_detection(self):
        """言語検出の妥当性テスト"""
        try:
            with patch.dict('sys.modules', {'streamlit': MagicMock()}):
                from dashboard.components.news_sentiment import get_demo_analysis_data
        except ImportError:
            self.skipTest("Streamlit環境が必要なテスト")
        
        demo_data = get_demo_analysis_data()
        
        valid_languages = ["ja", "en"]
        
        for news in demo_data["topNews"]:
            language = news["language"]
            self.assertIn(language, valid_languages, f"無効な言語: {language}")

    def test_timestamp_validity(self):
        """タイムスタンプの妥当性テスト"""
        try:
            with patch.dict('sys.modules', {'streamlit': MagicMock()}):
                from dashboard.components.news_sentiment import get_demo_analysis_data
        except ImportError:
            self.skipTest("Streamlit環境が必要なテスト")
        from datetime import datetime
        
        demo_data = get_demo_analysis_data()
        
        # 分析日時の確認
        analysis_date = demo_data["analysisDate"]
        try:
            datetime.fromisoformat(analysis_date.replace('Z', '+00:00'))
        except ValueError:
            self.fail(f"無効な分析日時フォーマット: {analysis_date}")
        
        # 各ニュースの公開日時確認
        for news in demo_data["topNews"]:
            published_at = news["publishedAt"]
            try:
                pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                # 公開日時が過去1週間以内であることを確認
                week_ago = datetime.now() - timedelta(days=7)
                self.assertGreater(pub_date, week_ago.replace(tzinfo=None), f"公開日時が古すぎます: {published_at}")
            except ValueError:
                self.fail(f"無効な公開日時フォーマット: {published_at}")

class TestNewsAnalysisFileStructure(unittest.TestCase):
    """ニュース分析ファイル構造テスト"""

    def setUp(self):
        """テストセットアップ"""
        self.project_root = Path(__file__).parent.parent.parent
        self.mcp_news_dir = self.project_root / "mcp-servers" / "news-analysis"

    def test_mcp_server_directory_structure(self):
        """MCPサーバーのディレクトリ構造テスト"""
        
        # 基本ディレクトリの存在確認
        self.assertTrue(self.mcp_news_dir.exists(), "news-analysis MCPサーバーディレクトリが存在しません")
        
        # 必須ファイルの存在確認
        required_files = [
            "package.json",
            "tsconfig.json", 
            "README.md",
            "src/index.ts"
        ]
        
        for file_path in required_files:
            full_path = self.mcp_news_dir / file_path
            self.assertTrue(full_path.exists(), f"必須ファイルが存在しません: {file_path}")

    def test_package_json_validity(self):
        """package.jsonの妥当性テスト"""
        package_json_path = self.mcp_news_dir / "package.json"
        
        if package_json_path.exists():
            try:
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                
                # 必須フィールドの確認
                required_fields = ["name", "version", "description", "main", "scripts", "dependencies"]
                for field in required_fields:
                    self.assertIn(field, package_data, f"package.jsonに必須フィールド '{field}' が不足")
                
                # 依存関係の確認
                dependencies = package_data.get("dependencies", {})
                required_deps = ["@modelcontextprotocol/sdk", "zod"]
                for dep in required_deps:
                    self.assertIn(dep, dependencies, f"必須依存関係 '{dep}' が不足")
                    
            except json.JSONDecodeError:
                self.fail("package.jsonのJSONフォーマットが無効です")

    def test_dashboard_component_exists(self):
        """ダッシュボードコンポーネントの存在テスト"""
        component_path = self.project_root / "dashboard" / "components" / "news_sentiment.py"
        self.assertTrue(component_path.exists(), "ニュース分析ダッシュボードコンポーネントが存在しません")

    def test_dashboard_integration(self):
        """ダッシュボード統合テスト"""
        app_path = self.project_root / "dashboard" / "app.py"
        
        if app_path.exists():
            with open(app_path, 'r', encoding='utf-8') as f:
                app_content = f.read()
            
            # ニュース分析コンポーネントのインポート確認
            self.assertIn("news_sentiment", app_content, "ダッシュボードにニュース分析のインポートが不足")
            self.assertIn("render_news_sentiment_analysis", app_content, "ニュース分析レンダリング関数が統合されていません")
            self.assertIn("ニュース分析", app_content, "ニュース分析タブが追加されていません")

if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)