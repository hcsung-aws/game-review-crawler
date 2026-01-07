"""
DataFilter Property-Based Tests

**Feature: game-analytics-dashboard, Property 2: Game Data Filtering**
**Validates: Requirements 1.3**

For any 게임 ID와 여러 게임의 데이터가 혼합된 목록에서, 
특정 게임으로 필터링하면 결과의 모든 데이터는 해당 게임 ID에 속해야 한다.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timedelta
from typing import List
import uuid

from crawler.models.data_models import PostContent, Comment
from crawler.models.analysis_models import SentimentResult, SentimentLabel
from crawler.utils.data_filter import DataFilter, FilterCriteria, SortField, SortOrder


# Strategies for generating test data
@st.composite
def post_content_strategy(draw, keyword: str = None, site: str = None, unique_url: bool = False):
    """PostContent 생성 전략"""
    if unique_url:
        url = f"https://example.com/{uuid.uuid4()}"
    else:
        url = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))).map(lambda x: f"https://example.com/{x}"))
    title = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    body = draw(st.text(min_size=0, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    site_val = site or draw(st.sampled_from(["ruliweb", "inven", "dcinside", "fmkorea"]))
    keyword_val = keyword or draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    author = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    
    # 날짜 생성 (최근 1년 이내)
    days_ago = draw(st.integers(min_value=0, max_value=365))
    created_at = datetime.now() - timedelta(days=days_ago)
    
    view_count = draw(st.integers(min_value=0, max_value=100000))
    like_count = draw(st.integers(min_value=0, max_value=10000))
    
    return PostContent(
        url=url,
        title=title,
        body=body,
        site=site_val,
        keyword=keyword_val,
        author=author,
        created_at=created_at,
        view_count=view_count,
        like_count=like_count,
        comments=[]
    )


@st.composite
def unique_url_post_strategy(draw, keyword: str = None, site: str = None):
    """고유 URL을 가진 PostContent 생성 전략"""
    return draw(post_content_strategy(keyword=keyword, site=site, unique_url=True))


@st.composite
def mixed_game_posts_strategy(draw):
    """여러 게임의 게시글이 혼합된 목록 생성"""
    games = ["세븐나이츠", "몬스터헌터", "원신", "로스트아크", "메이플스토리"]
    posts = []
    
    # 각 게임별로 1-3개의 게시글 생성 (속도 개선을 위해 줄임)
    for game in games:
        num_posts = draw(st.integers(min_value=1, max_value=3))
        for _ in range(num_posts):
            post = draw(unique_url_post_strategy(keyword=game))
            posts.append(post)
    
    return posts, games


class TestDataFilterProperty:
    """DataFilter Property-Based Tests"""
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(data=mixed_game_posts_strategy())
    def test_game_filter_returns_only_matching_posts(self, data):
        """
        **Feature: game-analytics-dashboard, Property 2: Game Data Filtering**
        **Validates: Requirements 1.3**
        
        For any 게임 ID와 여러 게임의 데이터가 혼합된 목록에서,
        특정 게임으로 필터링하면 결과의 모든 데이터는 해당 게임 ID에 속해야 한다.
        """
        posts, games = data
        data_filter = DataFilter()
        
        # 각 게임에 대해 필터링 테스트
        for target_game in games:
            filtered = data_filter.filter_by_game(posts, [target_game])
            
            # 필터링된 모든 게시글은 해당 게임 키워드를 포함해야 함
            for post in filtered:
                assert post.keyword.lower() == target_game.lower() or \
                       target_game.lower() in post.title.lower() or \
                       target_game.lower() in post.body.lower(), \
                       f"Post with keyword '{post.keyword}' should not be in filtered results for '{target_game}'"
    
    @settings(max_examples=100)
    @given(posts=st.lists(post_content_strategy(), min_size=1, max_size=20))
    def test_date_range_filter_returns_posts_within_range(self, posts):
        """
        **Feature: game-analytics-dashboard, Property 12: Date Range Filtering**
        **Validates: Requirements 4.3**
        
        For any 시작일과 종료일로 필터링하면, 
        결과의 모든 데이터는 해당 기간 내의 날짜를 가져야 한다.
        """
        data_filter = DataFilter()
        
        # 30일 전부터 오늘까지의 기간 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        filtered = data_filter.filter_by_date_range(posts, start_date, end_date)
        
        # 필터링된 모든 게시글은 기간 내에 있어야 함
        for post in filtered:
            if post.created_at is not None:
                assert start_date <= post.created_at <= end_date, \
                    f"Post date {post.created_at} is outside range [{start_date}, {end_date}]"
    
    @settings(max_examples=100)
    @given(posts=st.lists(post_content_strategy(), min_size=1, max_size=20))
    def test_site_filter_returns_only_matching_sites(self, posts):
        """
        **Feature: game-analytics-dashboard, Property 14: Multi-Filter Application**
        **Validates: Requirements 5.5**
        
        사이트 필터를 적용하면 결과의 모든 데이터는 해당 사이트에 속해야 한다.
        """
        data_filter = DataFilter()
        target_sites = ["ruliweb", "inven"]
        
        filtered = data_filter.filter_by_site(posts, target_sites)
        
        # 필터링된 모든 게시글은 지정된 사이트에 속해야 함
        for post in filtered:
            assert post.site.lower() in [s.lower() for s in target_sites], \
                f"Post from site '{post.site}' should not be in filtered results"
    
    @settings(max_examples=100)
    @given(posts=st.lists(post_content_strategy(), min_size=1, max_size=20))
    def test_sort_by_view_count_is_ordered(self, posts):
        """
        **Feature: game-analytics-dashboard, Property 13: Post Sorting Options**
        **Validates: Requirements 5.4**
        
        For any 게시글 목록에 대해 조회수로 정렬하면, 
        결과는 해당 필드 기준으로 올바르게 정렬되어야 한다.
        """
        data_filter = DataFilter()
        
        # 내림차순 정렬
        sorted_desc = data_filter.sort_posts(posts, SortField.VIEW_COUNT, SortOrder.DESC)
        for i in range(len(sorted_desc) - 1):
            assert sorted_desc[i].view_count >= sorted_desc[i + 1].view_count, \
                "Posts should be sorted by view_count in descending order"
        
        # 오름차순 정렬
        sorted_asc = data_filter.sort_posts(posts, SortField.VIEW_COUNT, SortOrder.ASC)
        for i in range(len(sorted_asc) - 1):
            assert sorted_asc[i].view_count <= sorted_asc[i + 1].view_count, \
                "Posts should be sorted by view_count in ascending order"
    
    @settings(max_examples=100)
    @given(posts=st.lists(post_content_strategy(), min_size=1, max_size=20))
    def test_sort_by_created_at_is_ordered(self, posts):
        """
        **Feature: game-analytics-dashboard, Property 13: Post Sorting Options**
        **Validates: Requirements 5.4**
        
        For any 게시글 목록에 대해 작성일로 정렬하면,
        결과는 해당 필드 기준으로 올바르게 정렬되어야 한다.
        """
        data_filter = DataFilter()
        
        # 내림차순 정렬 (최신순)
        sorted_desc = data_filter.sort_posts(posts, SortField.CREATED_AT, SortOrder.DESC)
        for i in range(len(sorted_desc) - 1):
            date_i = sorted_desc[i].created_at or datetime.min
            date_j = sorted_desc[i + 1].created_at or datetime.min
            assert date_i >= date_j, \
                "Posts should be sorted by created_at in descending order"
    
    @settings(max_examples=100)
    @given(posts=st.lists(post_content_strategy(), min_size=1, max_size=20))
    def test_multi_filter_satisfies_all_conditions(self, posts):
        """
        **Feature: game-analytics-dashboard, Property 14: Multi-Filter Application**
        **Validates: Requirements 5.5**
        
        For any 필터 조건(기간, 사이트, 감성, 이슈 유형)을 적용하면,
        결과의 모든 데이터는 모든 필터 조건을 만족해야 한다.
        """
        data_filter = DataFilter()
        
        # 복합 필터 조건 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        target_sites = ["ruliweb", "inven"]
        min_views = 100
        
        criteria = FilterCriteria(
            start_date=start_date,
            end_date=end_date,
            sites=target_sites,
            min_view_count=min_views
        )
        
        filtered = data_filter.apply_filters(posts, criteria)
        
        # 모든 필터 조건을 만족하는지 확인
        for post in filtered:
            # 기간 조건
            if post.created_at is not None:
                assert start_date <= post.created_at <= end_date, \
                    f"Post date {post.created_at} is outside range"
            
            # 사이트 조건
            assert post.site.lower() in [s.lower() for s in target_sites], \
                f"Post from site '{post.site}' should not be in filtered results"
            
            # 조회수 조건
            assert post.view_count >= min_views, \
                f"Post view_count {post.view_count} is below minimum {min_views}"
    
    @settings(max_examples=100)
    @given(posts=st.lists(post_content_strategy(), min_size=0, max_size=20))
    def test_empty_filter_returns_all_posts(self, posts):
        """빈 필터 조건은 모든 게시글을 반환해야 한다."""
        data_filter = DataFilter()
        
        # 빈 필터 조건
        criteria = FilterCriteria()
        filtered = data_filter.apply_filters(posts, criteria)
        
        assert len(filtered) == len(posts), \
            "Empty filter should return all posts"
    
    @settings(max_examples=100)
    @given(posts=st.lists(unique_url_post_strategy(), min_size=1, max_size=20))
    def test_filter_preserves_post_data(self, posts):
        """필터링 후에도 게시글 데이터가 보존되어야 한다."""
        data_filter = DataFilter()
        
        # 사이트 필터 적용
        sites = list(set(p.site for p in posts))
        if sites:
            filtered = data_filter.filter_by_site(posts, [sites[0]])
            
            # 필터링된 게시글의 데이터가 원본과 동일한지 확인
            # 필터링은 원본 객체를 그대로 반환하므로 identity 체크
            for post in filtered:
                assert post in posts, "Filtered post should exist in original list"


class TestNegativePostFiltering:
    """부정적 게시글 필터링 테스트"""
    
    @settings(max_examples=100)
    @given(
        scores=st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=20
        )
    )
    def test_negative_filter_returns_only_negative_posts(self, scores):
        """
        **Feature: game-analytics-dashboard, Property 5: Negative Post Filtering**
        **Validates: Requirements 2.4**
        
        For any 게시글 목록에서 부정적 게시글 필터링을 적용하면,
        결과의 모든 게시글은 Sentiment_Score가 -0.3 미만이어야 한다.
        """
        data_filter = DataFilter()
        
        # 테스트 데이터 생성
        posts_with_sentiment = []
        for i, score in enumerate(scores):
            post = PostContent(
                url=f"https://example.com/{i}",
                title=f"Test Post {i}",
                body="Test body",
                site="ruliweb",
                keyword="test"
            )
            
            # 레이블 결정
            if score < -0.3:
                label = SentimentLabel.NEGATIVE
            elif score > 0.3:
                label = SentimentLabel.POSITIVE
            else:
                label = SentimentLabel.NEUTRAL
            
            sentiment = SentimentResult(score=score, label=label)
            posts_with_sentiment.append((post, sentiment))
        
        # 부정적 게시글 필터링
        threshold = -0.3
        filtered = data_filter.filter_negative_posts(posts_with_sentiment, threshold)
        
        # 모든 필터링된 게시글은 threshold 미만이어야 함
        for post, sentiment in filtered:
            assert sentiment.score < threshold, \
                f"Sentiment score {sentiment.score} should be below threshold {threshold}"
    
    @settings(max_examples=100)
    @given(
        scores=st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=20
        )
    )
    def test_sentiment_sort_is_ordered(self, scores):
        """
        **Feature: game-analytics-dashboard, Property 13: Post Sorting Options**
        **Validates: Requirements 5.4**
        
        감성 점수로 정렬하면 결과는 올바르게 정렬되어야 한다.
        """
        data_filter = DataFilter()
        
        # 테스트 데이터 생성
        posts_with_sentiment = []
        for i, score in enumerate(scores):
            post = PostContent(
                url=f"https://example.com/{i}",
                title=f"Test Post {i}",
                body="Test body",
                site="ruliweb",
                keyword="test"
            )
            sentiment = SentimentResult(score=score, label=SentimentLabel.NEUTRAL)
            posts_with_sentiment.append((post, sentiment))
        
        # 내림차순 정렬
        sorted_desc = data_filter.sort_by_sentiment(posts_with_sentiment, SortOrder.DESC)
        for i in range(len(sorted_desc) - 1):
            assert sorted_desc[i][1].score >= sorted_desc[i + 1][1].score, \
                "Posts should be sorted by sentiment score in descending order"
        
        # 오름차순 정렬
        sorted_asc = data_filter.sort_by_sentiment(posts_with_sentiment, SortOrder.ASC)
        for i in range(len(sorted_asc) - 1):
            assert sorted_asc[i][1].score <= sorted_asc[i + 1][1].score, \
                "Posts should be sorted by sentiment score in ascending order"
