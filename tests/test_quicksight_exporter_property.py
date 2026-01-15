"""
Property-Based Tests for GameQuickSightExporter

**Feature: game-analytics-dashboard, Property 15: QuickSight Export Files**
**Validates: Requirements 6.2**

For any 게임에 대해 QuickSight 내보내기를 수행하면, 
posts.csv, comments.csv, sentiment.csv, issues.csv 4개 파일이 모두 생성되어야 한다.

**Feature: game-analytics-dashboard, Property 16: CSV Format Compatibility**
**Validates: Requirements 6.3**

For any 생성된 CSV 파일은 UTF-8 인코딩이어야 하고, 
날짜 필드는 ISO 8601 형식(YYYY-MM-DD)이어야 한다.
"""

import os
import csv
import re
import tempfile
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime
from typing import List

from crawler.models.data_models import PostContent, Comment
from crawler.models.analysis_models import (
    SentimentResult,
    SentimentLabel,
    DetectedIssue,
    KeywordCluster,
    IssueSeverity
)
from crawler.exporters.quicksight_exporter import GameQuickSightExporter


# Custom strategies for generating test data
@st.composite
def comment_strategy(draw):
    """Comment 객체 생성 전략"""
    author = draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        whitelist_characters=' '
    )).filter(lambda x: x.strip()))
    content = draw(st.text(min_size=0, max_size=200))
    created_at = draw(st.one_of(
        st.none(),
        st.datetimes(
            min_value=datetime(2000, 1, 1),
            max_value=datetime(2030, 12, 31)
        )
    ))
    like_count = draw(st.integers(min_value=0, max_value=10000))
    
    return Comment(
        author=author,
        content=content,
        created_at=created_at,
        like_count=like_count
    )


@st.composite
def post_content_strategy(draw):
    """PostContent 객체 생성 전략"""
    url = draw(st.text(min_size=5, max_size=100, alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        whitelist_characters='/:.-_'
    )).filter(lambda x: x.strip()))
    title = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    body = draw(st.text(min_size=0, max_size=500))
    site = draw(st.sampled_from(["dcinside", "ruliweb", "inven", "fmkorea"]))
    keyword = draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    author = draw(st.one_of(
        st.none(),
        st.text(min_size=1, max_size=30, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters=' '
        )).filter(lambda x: x.strip())
    ))
    created_at = draw(st.one_of(
        st.none(),
        st.datetimes(
            min_value=datetime(2000, 1, 1),
            max_value=datetime(2030, 12, 31)
        )
    ))
    view_count = draw(st.integers(min_value=0, max_value=100000))
    like_count = draw(st.integers(min_value=0, max_value=10000))
    comments = draw(st.lists(comment_strategy(), min_size=0, max_size=5))
    
    return PostContent(
        url=url,
        title=title,
        body=body,
        site=site,
        keyword=keyword,
        author=author,
        created_at=created_at,
        view_count=view_count,
        like_count=like_count,
        comments=comments
    )


@st.composite
def keyword_cluster_strategy(draw):
    """KeywordCluster 객체 생성 전략"""
    cluster_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        whitelist_characters='-_'
    )).filter(lambda x: x.strip()))
    keywords = draw(st.lists(
        st.text(min_size=1, max_size=20).filter(lambda x: x.strip() and '|' not in x),
        min_size=1,
        max_size=5
    ))
    representative = keywords[0] if keywords else "keyword"
    post_count = draw(st.integers(min_value=0, max_value=1000))
    total_views = draw(st.integers(min_value=0, max_value=100000))
    total_comments = draw(st.integers(min_value=0, max_value=10000))
    
    return KeywordCluster(
        cluster_id=cluster_id,
        keywords=keywords,
        representative=representative,
        post_count=post_count,
        total_views=total_views,
        total_comments=total_comments
    )


@st.composite
def detected_issue_strategy(draw):
    """DetectedIssue 객체 생성 전략"""
    issue_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        whitelist_characters='-_'
    )).filter(lambda x: x.strip()))
    title = draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    cluster = draw(keyword_cluster_strategy())
    priority_score = draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False))
    is_hot = draw(st.booleans())
    is_bug = draw(st.booleans())
    severity = draw(st.sampled_from(list(IssueSeverity)))
    related_posts = draw(st.lists(
        st.text(min_size=5, max_size=50).filter(lambda x: x.strip()),
        min_size=0,
        max_size=3
    ))
    first_seen = draw(st.one_of(
        st.none(),
        st.datetimes(
            min_value=datetime(2000, 1, 1),
            max_value=datetime(2030, 12, 31)
        )
    ))
    sentiment_avg = draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False))
    
    return DetectedIssue(
        issue_id=issue_id,
        title=title,
        cluster=cluster,
        priority_score=priority_score,
        is_hot=is_hot,
        is_bug=is_bug,
        severity=severity,
        related_posts=related_posts,
        first_seen=first_seen,
        sentiment_avg=sentiment_avg
    )


@st.composite
def game_id_strategy(draw):
    """게임 ID 생성 전략 (kebab-case, ASCII only for filesystem compatibility)"""
    return draw(st.text(
        min_size=3,
        max_size=20,
        alphabet='abcdefghijklmnopqrstuvwxyz-'
    ).filter(lambda x: x.strip() and not x.startswith('-') and not x.endswith('-') and '--' not in x))


class TestQuickSightExportFiles:
    """
    **Feature: game-analytics-dashboard, Property 15: QuickSight Export Files**
    **Validates: Requirements 6.2**
    
    For any 게임에 대해 QuickSight 내보내기를 수행하면,
    posts.csv, comments.csv, sentiment.csv, issues.csv 4개 파일이 모두 생성되어야 한다.
    """
    
    @given(
        game_id=game_id_strategy(),
        posts=st.lists(post_content_strategy(), min_size=0, max_size=5)
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_all_four_files_created(self, game_id: str, posts: List[PostContent]):
        """QuickSight 내보내기 시 4개 파일이 모두 생성되어야 함"""
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = GameQuickSightExporter(base_output_dir=temp_dir)
            result = exporter.export_game_data(game_id=game_id, posts=posts)
            
            assert "posts" in result
            assert "comments" in result
            assert "sentiment" in result
            assert "issues" in result
            
            assert os.path.exists(result["posts"])
            assert os.path.exists(result["comments"])
            assert os.path.exists(result["sentiment"])
            assert os.path.exists(result["issues"])
            
            assert result["posts"].endswith("posts.csv")
            assert result["comments"].endswith("comments.csv")
            assert result["sentiment"].endswith("sentiment.csv")
            assert result["issues"].endswith("issues.csv")
    
    @given(
        game_id=game_id_strategy(),
        posts=st.lists(post_content_strategy(), min_size=1, max_size=3),
        issues=st.lists(detected_issue_strategy(), min_size=0, max_size=3)
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_files_created_with_issues(
        self,
        game_id: str,
        posts: List[PostContent],
        issues: List[DetectedIssue]
    ):
        """이슈 데이터가 있을 때도 4개 파일이 모두 생성되어야 함"""
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = GameQuickSightExporter(base_output_dir=temp_dir)
            result = exporter.export_game_data(
                game_id=game_id,
                posts=posts,
                issues=issues
            )
            
            assert os.path.exists(result["posts"])
            assert os.path.exists(result["comments"])
            assert os.path.exists(result["sentiment"])
            assert os.path.exists(result["issues"])



class TestCSVFormatCompatibility:
    """
    **Feature: game-analytics-dashboard, Property 16: CSV Format Compatibility**
    **Validates: Requirements 6.3**
    
    For any 생성된 CSV 파일은 UTF-8 인코딩이어야 하고,
    날짜 필드는 ISO 8601 형식(YYYY-MM-DD)이어야 한다.
    """
    
    # ISO 8601 날짜 형식 패턴 (YYYY-MM-DD)
    ISO_DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    
    @given(
        game_id=game_id_strategy(),
        posts=st.lists(post_content_strategy(), min_size=1, max_size=3)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_csv_utf8_encoding(self, game_id: str, posts: List[PostContent]):
        """CSV 파일이 UTF-8 인코딩이어야 함"""
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = GameQuickSightExporter(base_output_dir=temp_dir)
            result = exporter.export_game_data(game_id=game_id, posts=posts)
            
            # 모든 CSV 파일이 UTF-8로 읽을 수 있어야 함
            for file_key in ["posts", "comments", "sentiment", "issues"]:
                filepath = result[file_key]
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    assert content is not None
                except UnicodeDecodeError:
                    pytest.fail(f"{file_key}.csv is not UTF-8 encoded")
    
    @given(
        game_id=game_id_strategy(),
        posts=st.lists(post_content_strategy(), min_size=1, max_size=3)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_posts_csv_date_format(self, game_id: str, posts: List[PostContent]):
        """posts.csv의 날짜 필드가 ISO 8601 형식이어야 함"""
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = GameQuickSightExporter(base_output_dir=temp_dir)
            result = exporter.export_game_data(game_id=game_id, posts=posts)
            
            with open(result["posts"], "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_value = row.get("created_at", "")
                    if date_value:
                        assert self.ISO_DATE_PATTERN.match(date_value), \
                            f"Date '{date_value}' is not in ISO 8601 format (YYYY-MM-DD)"
    
    @given(
        game_id=game_id_strategy(),
        posts=st.lists(post_content_strategy(), min_size=1, max_size=3)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_comments_csv_date_format(self, game_id: str, posts: List[PostContent]):
        """comments.csv의 날짜 필드가 ISO 8601 형식이어야 함"""
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = GameQuickSightExporter(base_output_dir=temp_dir)
            result = exporter.export_game_data(game_id=game_id, posts=posts)
            
            with open(result["comments"], "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_value = row.get("created_at", "")
                    if date_value:
                        assert self.ISO_DATE_PATTERN.match(date_value), \
                            f"Date '{date_value}' is not in ISO 8601 format (YYYY-MM-DD)"
    
    @given(
        game_id=game_id_strategy(),
        posts=st.lists(post_content_strategy(), min_size=1, max_size=3),
        issues=st.lists(detected_issue_strategy(), min_size=1, max_size=3)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_issues_csv_date_format(
        self,
        game_id: str,
        posts: List[PostContent],
        issues: List[DetectedIssue]
    ):
        """issues.csv의 날짜 필드가 ISO 8601 형식이어야 함"""
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = GameQuickSightExporter(base_output_dir=temp_dir)
            result = exporter.export_game_data(
                game_id=game_id,
                posts=posts,
                issues=issues
            )
            
            with open(result["issues"], "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_value = row.get("first_seen", "")
                    if date_value:
                        assert self.ISO_DATE_PATTERN.match(date_value), \
                            f"Date '{date_value}' is not in ISO 8601 format (YYYY-MM-DD)"
    
    @given(
        game_id=game_id_strategy(),
        posts=st.lists(post_content_strategy(), min_size=1, max_size=3)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_csv_valid_structure(self, game_id: str, posts: List[PostContent]):
        """CSV 파일이 유효한 구조를 가져야 함"""
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = GameQuickSightExporter(base_output_dir=temp_dir)
            result = exporter.export_game_data(game_id=game_id, posts=posts)
            
            # posts.csv 구조 검증
            with open(result["posts"], "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                assert "post_id" in headers
                assert "url" in headers
                assert "title" in headers
                assert "created_at" in headers
                assert "game_id" in headers
            
            # comments.csv 구조 검증
            with open(result["comments"], "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                assert "comment_id" in headers
                assert "post_url" in headers
                assert "created_at" in headers
                assert "game_id" in headers
            
            # sentiment.csv 구조 검증
            with open(result["sentiment"], "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                assert "sentiment_id" in headers
                assert "sentiment_score" in headers
                assert "sentiment_label" in headers
                assert "game_id" in headers
            
            # issues.csv 구조 검증
            with open(result["issues"], "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                assert "issue_id" in headers
                assert "priority_score" in headers
                assert "game_id" in headers
