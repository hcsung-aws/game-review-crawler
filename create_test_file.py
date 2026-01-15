#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Create test file for exporters unit tests"""

test_content = '''"""
Unit tests for Exporter classes

Requirements: 6.2
- JSON and CSV export format validation
"""

import os
import json
import csv
import tempfile
import shutil
from datetime import datetime
from typing import List

import pytest

from crawler.models.data_models import PostContent, Comment
from crawler.exporters.exporters import JSONExporter, CSVExporter, ExporterFactory


@pytest.fixture
def temp_dir():
    """Create and cleanup temporary directory"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_posts() -> List[PostContent]:
    """Create sample posts for testing"""
    comment1 = Comment(
        author="commenter1",
        content="First comment",
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        like_count=5
    )
    comment2 = Comment(
        author="commenter2",
        content="Second comment",
        created_at=datetime(2024, 1, 15, 11, 0, 0),
        like_count=3
    )
    
    post1 = PostContent(
        url="https://example.com/post/1",
        title="Test Post 1",
        body="Post body content here.",
        site="example.com",
        keyword="test",
        author="author1",
        created_at=datetime(2024, 1, 15, 9, 0, 0),
        view_count=100,
        like_count=10,
        comments=[comment1, comment2]
    )
    
    post2 = PostContent(
        url="https://example.com/post/2",
        title="Test Post 2",
        body="Second post body.",
        site="example.com",
        keyword="test",
        author="author2",
        created_at=datetime(2024, 1, 16, 14, 0, 0),
        view_count=50,
        like_count=5,
        comments=[]
    )
    
    return [post1, post2]


class TestJSONExporter:
    """JSONExporter test class"""
    
    def test_export_creates_json_file(self, temp_dir, sample_posts):
        """Verify JSON file is created correctly"""
        exporter = JSONExporter()
        filepath = os.path.join(temp_dir, "test_output")
        
        result_path = exporter.export(sample_posts, filepath)
        
        assert os.path.exists(result_path)
        assert result_path.endswith(".json")
    
    def test_export_json_structure(self, temp_dir, sample_posts):
        """Verify JSON file structure is correct"""
        exporter = JSONExporter()
        filepath = os.path.join(temp_dir, "test_output.json")
        
        exporter.export(sample_posts, filepath)
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert isinstance(data, list)
        assert len(data) == 2
        
        post_data = data[0]
        assert "url" in post_data
        assert "title" in post_data
        assert "body" in post_data
        assert "site" in post_data
        assert "keyword" in post_data
        assert "author" in post_data
        assert "created_at" in post_data
        assert "view_count" in post_data
        assert "like_count" in post_data
        assert "comments" in post_data
    
    def test_export_json_content_values(self, temp_dir, sample_posts):
        """Verify JSON content matches original data"""
        exporter = JSONExporter()
        filepath = os.path.join(temp_dir, "test_output.json")
        
        exporter.export(sample_posts, filepath)
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        post_data = data[0]
        assert post_data["url"] == "https://example.com/post/1"
        assert post_data["title"] == "Test Post 1"
        assert post_data["body"] == "Post body content here."
        assert post_data["site"] == "example.com"
        assert post_data["view_count"] == 100
        assert post_data["like_count"] == 10
        
        assert len(post_data["comments"]) == 2
        assert post_data["comments"][0]["author"] == "commenter1"
        assert post_data["comments"][0]["content"] == "First comment"
    
    def test_export_empty_posts(self, temp_dir):
        """Verify empty posts list export"""
        exporter = JSONExporter()
        filepath = os.path.join(temp_dir, "empty.json")
        
        exporter.export([], filepath)
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert data == []
    
    def test_get_extension(self):
        """Verify extension return"""
        exporter = JSONExporter()
        assert exporter.get_extension() == ".json"


class TestCSVExporter:
    """CSVExporter test class"""
    
    def test_export_creates_csv_files(self, temp_dir, sample_posts):
        """Verify CSV files are created correctly"""
        exporter = CSVExporter(include_comments=True)
        filepath = os.path.join(temp_dir, "test_output")
        
        result_path = exporter.export(sample_posts, filepath)
        
        assert os.path.exists(result_path)
        assert result_path.endswith(".csv")
        
        comments_path = result_path.replace(".csv", "_comments.csv")
        assert os.path.exists(comments_path)
    
    def test_export_csv_posts_structure(self, temp_dir, sample_posts):
        """Verify posts CSV file structure"""
        exporter = CSVExporter()
        filepath = os.path.join(temp_dir, "test_output.csv")
        
        exporter.export(sample_posts, filepath)
        
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 2
        
        expected_fields = [
            "url", "title", "body", "site", "keyword",
            "author", "created_at", "view_count", "like_count", "comment_count"
        ]
        assert all(field in rows[0] for field in expected_fields)
    
    def test_export_csv_posts_content(self, temp_dir, sample_posts):
        """Verify posts CSV content is correct"""
        exporter = CSVExporter()
        filepath = os.path.join(temp_dir, "test_output.csv")
        
        exporter.export(sample_posts, filepath)
        
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        row = rows[0]
        assert row["url"] == "https://example.com/post/1"
        assert row["title"] == "Test Post 1"
        assert row["site"] == "example.com"
        assert row["view_count"] == "100"
        assert row["comment_count"] == "2"
    
    def test_export_csv_comments_structure(self, temp_dir, sample_posts):
        """Verify comments CSV file structure"""
        exporter = CSVExporter(include_comments=True)
        filepath = os.path.join(temp_dir, "test_output.csv")
        
        exporter.export(sample_posts, filepath)
        
        comments_path = filepath.replace(".csv", "_comments.csv")
        with open(comments_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 2
        
        expected_fields = ["post_url", "author", "content", "created_at", "like_count"]
        assert all(field in rows[0] for field in expected_fields)
    
    def test_export_csv_comments_content(self, temp_dir, sample_posts):
        """Verify comments CSV content is correct"""
        exporter = CSVExporter(include_comments=True)
        filepath = os.path.join(temp_dir, "test_output.csv")
        
        exporter.export(sample_posts, filepath)
        
        comments_path = filepath.replace(".csv", "_comments.csv")
        with open(comments_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        row = rows[0]
        assert row["post_url"] == "https://example.com/post/1"
        assert row["author"] == "commenter1"
        assert row["content"] == "First comment"
        assert row["like_count"] == "5"
    
    def test_export_without_comments(self, temp_dir, sample_posts):
        """Verify comments file is not created when disabled"""
        exporter = CSVExporter(include_comments=False)
        filepath = os.path.join(temp_dir, "test_output.csv")
        
        exporter.export(sample_posts, filepath)
        
        assert os.path.exists(filepath)
        comments_path = filepath.replace(".csv", "_comments.csv")
        assert not os.path.exists(comments_path)
    
    def test_export_empty_posts(self, temp_dir):
        """Verify empty posts list export"""
        exporter = CSVExporter()
        filepath = os.path.join(temp_dir, "empty.csv")
        
        exporter.export([], filepath)
        
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 0
    
    def test_get_extension(self):
        """Verify extension return"""
        exporter = CSVExporter()
        assert exporter.get_extension() == ".csv"


class TestExporterFactory:
    """ExporterFactory test class"""
    
    def test_create_json_exporter(self):
        """Verify JSON Exporter creation"""
        exporter = ExporterFactory.create("json")
        assert isinstance(exporter, JSONExporter)
    
    def test_create_csv_exporter(self):
        """Verify CSV Exporter creation"""
        exporter = ExporterFactory.create("csv")
        assert isinstance(exporter, CSVExporter)
    
    def test_create_case_insensitive(self):
        """Verify case insensitive creation"""
        exporter1 = ExporterFactory.create("JSON")
        exporter2 = ExporterFactory.create("Json")
        
        assert isinstance(exporter1, JSONExporter)
        assert isinstance(exporter2, JSONExporter)
    
    def test_create_unsupported_format(self):
        """Verify unsupported format raises exception"""
        with pytest.raises(ValueError) as exc_info:
            ExporterFactory.create("xml")
        
        assert "Unsupported format" in str(exc_info.value)
    
    def test_get_supported_formats(self):
        """Verify supported formats list"""
        formats = ExporterFactory.get_supported_formats()
        
        assert "json" in formats
        assert "csv" in formats
    
    def test_create_with_kwargs(self):
        """Verify kwargs are passed correctly"""
        exporter = ExporterFactory.create("json", indent=4, ensure_ascii=True)
        
        assert isinstance(exporter, JSONExporter)
        assert exporter.indent == 4
        assert exporter.ensure_ascii is True
'''

if __name__ == "__main__":
    with open("tests/test_exporters_unit.py", "w", encoding="utf-8") as f:
        f.write(test_content)
    print("Test file created successfully!")
