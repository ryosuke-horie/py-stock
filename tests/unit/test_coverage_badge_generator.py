#!/usr/bin/env python3
"""
カバレッジバッジ生成機能のユニットテスト
"""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.utils.coverage_badge_generator import CoverageBadgeGenerator


class TestCoverageBadgeGenerator:
    """CoverageBadgeGeneratorクラスのテスト"""

    def setup_method(self):
        """テストメソッドの前処理"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        self.generator = CoverageBadgeGenerator(str(self.project_root))

    def teardown_method(self):
        """テストメソッドの後処理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_coverage_xml(self, line_rate: float = 0.85):
        """テスト用のcoverage.xmlファイルを作成"""
        coverage_xml = self.project_root / "coverage.xml"
        xml_content = f'''<?xml version="1.0" ?>
<coverage version="7.4.1" timestamp="1704067200000" lines-valid="1000" lines-covered="850" line-rate="{line_rate}" branches-valid="200" branches-covered="170" branch-rate="0.85" complexity="0">
    <sources>
        <source>src</source>
    </sources>
    <packages>
        <package name="src" line-rate="{line_rate}" branch-rate="0.85" complexity="0">
            <classes>
                <class name="src/test_module.py" filename="src/test_module.py" complexity="0" line-rate="{line_rate}" branch-rate="0.85">
                    <methods/>
                    <lines>
                        <line number="1" hits="1"/>
                        <line number="2" hits="1"/>
                        <line number="3" hits="0"/>
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>'''

        with open(coverage_xml, "w", encoding="utf-8") as f:
            f.write(xml_content)

        return coverage_xml

    def test_init(self):
        """初期化テスト"""
        assert self.generator.project_root == self.project_root
        assert self.generator.coverage_xml == self.project_root / "coverage.xml"
        assert self.generator.badges_dir == self.project_root / "badges"
        assert self.generator.badges_dir.exists()

    def test_get_coverage_percentage_success(self):
        """カバレッジ率取得成功テスト"""
        self.create_coverage_xml(0.85)
        coverage = self.generator.get_coverage_percentage()
        assert coverage == 85.0

    def test_get_coverage_percentage_no_file(self):
        """カバレッジファイルが存在しない場合のテスト"""
        coverage = self.generator.get_coverage_percentage()
        assert coverage is None

    def test_get_coverage_percentage_invalid_xml(self):
        """無効なXMLファイルの場合のテスト"""
        coverage_xml = self.project_root / "coverage.xml"
        with open(coverage_xml, "w", encoding="utf-8") as f:
            f.write("invalid xml content")

        coverage = self.generator.get_coverage_percentage()
        assert coverage is None

    def test_get_badge_color(self):
        """バッジ色判定テスト"""
        assert self.generator.get_badge_color(95) == "brightgreen"
        assert self.generator.get_badge_color(85) == "green"
        assert self.generator.get_badge_color(75) == "yellowgreen"
        assert self.generator.get_badge_color(65) == "yellow"
        assert self.generator.get_badge_color(55) == "orange"
        assert self.generator.get_badge_color(45) == "red"

    def test_generate_svg_badge(self):
        """SVGバッジ生成テスト"""
        coverage = 85.5
        svg = self.generator.generate_svg_badge(coverage)

        assert "85.5%" in svg
        assert "coverage" in svg
        assert "<svg" in svg
        assert "</svg>" in svg
        assert "97CA00" in svg  # green color

    def test_save_badge(self):
        """バッジ保存テスト"""
        coverage = 75.0
        badge_path = self.generator.save_badge(coverage)

        assert badge_path.exists()
        assert badge_path.name == "coverage.svg"

        with open(badge_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "75.0%" in content

    def test_generate_markdown_badge(self):
        """Markdownバッジ生成テスト"""
        coverage = 88.5

        # リンクなし
        markdown = self.generator.generate_markdown_badge(coverage)
        assert "![Coverage 88.5%]" in markdown
        assert "badges/coverage.svg" in markdown

        # リンクあり
        link_url = "https://example.com/coverage"
        markdown_with_link = self.generator.generate_markdown_badge(
            coverage, link_url
        )
        assert f"]({link_url})" in markdown_with_link

    def test_generate_shields_io_badge_url(self):
        """Shields.ioバッジURL生成テスト"""
        coverage = 92.3
        url = self.generator.generate_shields_io_badge_url(coverage)

        assert "https://img.shields.io/badge/coverage-" in url
        assert "92.3%25" in url  # URL encoded
        assert "brightgreen" in url

    def test_update_readme_with_badge_new_badge(self):
        """READMEに新しいバッジを追加するテスト"""
        readme_path = self.project_root / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("# Test Project\\n\\nThis is a test project.")

        success = self.generator.update_readme_with_badge(85.0, readme_path)
        assert success

        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "![Coverage]" in content
        assert "85.0%25" in content

    def test_update_readme_with_badge_update_existing(self):
        """READMEの既存バッジを更新するテスト"""
        readme_path = self.project_root / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(
                "# Test Project\\n\\n![Coverage](https://img.shields.io/badge/coverage-70.0%25-yellow)\\n\\nContent."
            )

        success = self.generator.update_readme_with_badge(90.0, readme_path)
        assert success

        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "90.0%25" in content
        assert "brightgreen" in content
        assert "70.0%25" not in content

    def test_update_readme_no_file(self):
        """READMEファイルが存在しない場合のテスト"""
        non_existent_path = self.project_root / "nonexistent.md"
        success = self.generator.update_readme_with_badge(85.0, non_existent_path)
        assert not success

    @patch("subprocess.run")
    def test_run_coverage_test_success(self, mock_run):
        """カバレッジテスト実行成功テスト"""
        # subprocess.runをモック
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # coverage.xmlを作成
        self.create_coverage_xml(0.78)

        coverage = self.generator.run_coverage_test()
        assert coverage == 78.0

        # 正しいコマンドが呼ばれたかチェック
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "uv" in args
        assert "pytest" in args
        assert "--cov=src" in args

    @patch("subprocess.run")
    def test_run_coverage_test_failure(self, mock_run):
        """カバレッジテスト実行失敗テスト"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Test failed"
        mock_run.return_value = mock_result

        coverage = self.generator.run_coverage_test()
        assert coverage is None

    @patch("subprocess.run")
    def test_run_coverage_test_timeout(self, mock_run):
        """カバレッジテスト実行タイムアウトテスト"""
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired("cmd", 300)

        coverage = self.generator.run_coverage_test()
        assert coverage is None

    @patch.object(CoverageBadgeGenerator, "run_coverage_test")
    @patch.object(CoverageBadgeGenerator, "save_badge")
    def test_generate_badge_info_success(self, mock_save_badge, mock_run_test):
        """バッジ情報生成成功テスト"""
        mock_run_test.return_value = 88.5
        mock_save_badge.return_value = Path("badges/coverage.svg")

        result = self.generator.generate_badge_info()

        assert result["success"] is True
        assert result["coverage"] == 88.5
        assert result["color"] == "green"
        assert "shields_io_url" in result
        assert "markdown_shields" in result

    @patch.object(CoverageBadgeGenerator, "run_coverage_test")
    @patch.object(CoverageBadgeGenerator, "get_coverage_percentage")
    def test_generate_badge_info_failure(self, mock_get_coverage, mock_run_test):
        """バッジ情報生成失敗テスト"""
        mock_run_test.return_value = None
        mock_get_coverage.return_value = None

        result = self.generator.generate_badge_info()

        assert result["success"] is False
        assert "error" in result

    def test_color_hex_conversion(self):
        """色名の16進数変換テスト"""
        assert self.generator._get_color_hex("brightgreen") == "4c1"
        assert self.generator._get_color_hex("green") == "97CA00"
        assert self.generator._get_color_hex("yellowgreen") == "a4a61d"
        assert self.generator._get_color_hex("yellow") == "dfb317"
        assert self.generator._get_color_hex("orange") == "fe7d37"
        assert self.generator._get_color_hex("red") == "e05d44"
        assert self.generator._get_color_hex("unknown") == "lightgrey"


if __name__ == "__main__":
    pytest.main([__file__])