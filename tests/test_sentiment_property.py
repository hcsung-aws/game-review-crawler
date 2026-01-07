"""
Property-Based Tests for Sentiment Analysis

**Feature: game-analytics-dashboard, Property 4: Sentiment Score Range**
**Validates: Requirements 2.1, 2.2**

For any 텍스트에 대해 SentimentAnalyzer가 반환하는 Sentiment_Score는 
-1.0 이상 1.0 이하의 값이어야 하며, SentimentResult 객체를 반환해야 한다.

**Feature: game-analytics-dashboard, Property 5: Negative Post Filtering**
**Validates: Requirements 2.4**

For any 게시글 목록에서 부정적 게시글 필터링을 적용하면, 
결과의 모든 게시글은 Sentiment_Score가 -0.3 미만이어야 한다.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from datetime import datetime

from crawler.analysis.sentiment import SentimentAnalyzer
from crawler.models.analysis_models import SentimentResult, SentimentLabel
from crawler.models.data_models import PostContent, Comment


# Custom strategies for generating test data
@st.composite
def korean_text_strategy(draw):
    """한국어 텍스트 생성 전략"""
    # 한글, 영문, 숫자, 공백, 특수문자 포함
    text = draw(st.text(
        alphabet=st.sampled_from(
            'abcdefghijklmnopqrstuvwxyz'
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            '0123456789'
            '가나다라마바사아자차카타파하'
            '좋다싫다재밌다버그오류최고'
            ' \n\t'
        ),
        min_size=0,
        max_size=500
    ))
    return text


@st.composite
def mixed_sentiment_text_strategy(draw):
    """긍정/부정 단어가 혼합된 텍스트 생성 전략"""
    positive_words = ["좋다", "최고", "재밌다", "굿", "대박", "명작"]
    negative_words = ["싫다", "버그", "오류", "최악", "망겜", "노잼"]
    neutral_words = ["게임", "플레이", "캐릭터", "스토리", "그래픽"]
    
    words = []
    num_words = draw(st.integers(min_value=0, max_value=20))
    
    for _ in range(num_words):
        word_type = draw(st.sampled_from(["positive", "negative", "neutral"]))
        if word_type == "positive":
            words.append(draw(st.sampled_from(positive_words)))
        elif word_type == "negative":
            words.append(draw(st.sampled_from(negative_words)))
        else:
            words.append(draw(st.sampled_from(neutral_words)))
    
    return " ".join(words)


@st.composite
def post_content_strategy(draw):
    """PostContent 객체 생성 전략"""
    title = draw(mixed_sentiment_text_strategy())
    body = draw(mixed_sentiment_text_strategy())
    
    return PostContent(
        url=f"https://example.com/post/{draw(st.integers(min_value=1, max_value=10000))}",
        title=title if title else "테스트 제목",
        body=body if body else "테스트 본문",
        site="test_site",
        keyword="test_keyword",
        author="test_author",
        created_at=datetime.now(),
        view_count=draw(st.integers(min_value=0, max_value=10000)),
        like_count=draw(st.integers(min_value=0, max_value=1000)),
        comments=[]
    )


@st.composite
def post_list_strategy(draw):
    """PostContent 목록 생성 전략"""
    posts = draw(st.lists(
        post_content_strategy(),
        min_size=0,
        max_size=20
    ))
    return posts


@st.composite
def comment_strategy(draw):
    """Comment 객체 생성 전략"""
    content = draw(mixed_sentiment_text_strategy())
    
    return Comment(
        author=f"user_{draw(st.integers(min_value=1, max_value=1000))}",
        content=content if content else "테스트 댓글",
        created_at=datetime.now(),
        like_count=draw(st.integers(min_value=0, max_value=100))
    )


@st.composite
def comment_list_strategy(draw):
    """Comment 목록 생성 전략"""
    comments = draw(st.lists(
        comment_strategy(),
        min_size=0,
        max_size=10
    ))
    return comments


class TestSentimentScoreRange:
    """
    **Feature: game-analytics-dashboard, Property 4: Sentiment Score Range**
    **Validates: Requirements 2.1, 2.2**
    
    For any 텍스트에 대해 SentimentAnalyzer가 반환하는 Sentiment_Score는 
    -1.0 이상 1.0 이하의 값이어야 하며, SentimentResult 객체를 반환해야 한다.
    """
    
    @given(text=korean_text_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_score_range_for_any_text(self, text: str):
        """임의의 텍스트에 대해 점수가 -1.0 ~ 1.0 범위인지 검증"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(text)
        
        # SentimentResult 객체 반환 검증
        assert isinstance(result, SentimentResult), \
            f"Expected SentimentResult, got {type(result)}"
        
        # 점수 범위 검증
        assert -1.0 <= result.score <= 1.0, \
            f"Score {result.score} is out of range [-1.0, 1.0]"
    
    @given(text=mixed_sentiment_text_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_score_range_for_mixed_sentiment(self, text: str):
        """긍정/부정 혼합 텍스트에 대해 점수가 범위 내인지 검증"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(text)
        
        assert isinstance(result, SentimentResult)
        assert -1.0 <= result.score <= 1.0, \
            f"Score {result.score} is out of range [-1.0, 1.0]"
    
    @given(post=post_content_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_score_range_for_post(self, post: PostContent):
        """게시글 분석 결과의 점수가 범위 내인지 검증"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_post(post)
        
        assert isinstance(result, SentimentResult)
        assert -1.0 <= result.score <= 1.0, \
            f"Post score {result.score} is out of range [-1.0, 1.0]"
    
    @given(comments=comment_list_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_score_range_for_comments(self, comments):
        """댓글 분석 결과의 점수가 모두 범위 내인지 검증"""
        analyzer = SentimentAnalyzer()
        results = analyzer.analyze_comments(comments)
        
        assert len(results) == len(comments), \
            f"Expected {len(comments)} results, got {len(results)}"
        
        for i, result in enumerate(results):
            assert isinstance(result, SentimentResult), \
                f"Comment {i} result is not SentimentResult"
            assert -1.0 <= result.score <= 1.0, \
                f"Comment {i} score {result.score} is out of range [-1.0, 1.0]"
    
    @given(text=korean_text_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_result_has_valid_label(self, text: str):
        """결과에 유효한 레이블이 포함되어 있는지 검증"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(text)
        
        assert result.label in [SentimentLabel.POSITIVE, SentimentLabel.NEGATIVE, SentimentLabel.NEUTRAL], \
            f"Invalid label: {result.label}"
    
    @given(text=korean_text_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_confidence_range(self, text: str):
        """신뢰도가 0.0 ~ 1.0 범위인지 검증"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(text)
        
        assert 0.0 <= result.confidence <= 1.0, \
            f"Confidence {result.confidence} is out of range [0.0, 1.0]"
    
    def test_empty_text_returns_neutral(self):
        """빈 텍스트는 중립 결과를 반환하는지 검증"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("")
        
        assert result.score == 0.0
        assert result.label == SentimentLabel.NEUTRAL
    
    def test_whitespace_text_returns_neutral(self):
        """공백만 있는 텍스트는 중립 결과를 반환하는지 검증"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("   \n\t  ")
        
        assert result.score == 0.0
        assert result.label == SentimentLabel.NEUTRAL


class TestNegativePostFiltering:
    """
    **Feature: game-analytics-dashboard, Property 5: Negative Post Filtering**
    **Validates: Requirements 2.4**
    
    For any 게시글 목록에서 부정적 게시글 필터링을 적용하면, 
    결과의 모든 게시글은 Sentiment_Score가 -0.3 미만이어야 한다.
    """
    
    @given(posts=post_list_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_filtered_posts_are_negative(self, posts):
        """필터링된 게시글이 모두 부정적인지 검증"""
        analyzer = SentimentAnalyzer()
        threshold = -0.3
        filtered_posts = analyzer.filter_negative_posts(posts, threshold=threshold)
        
        for post in filtered_posts:
            result = analyzer.analyze_post(post)
            assert result.score < threshold, \
                f"Filtered post has score {result.score} >= {threshold}"
    
    @given(posts=post_list_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_filtered_posts_subset_of_original(self, posts):
        """필터링된 게시글이 원본의 부분집합인지 검증"""
        analyzer = SentimentAnalyzer()
        filtered_posts = analyzer.filter_negative_posts(posts)
        
        # 필터링된 게시글 수는 원본 이하
        assert len(filtered_posts) <= len(posts), \
            f"Filtered count {len(filtered_posts)} > original count {len(posts)}"
        
        # 필터링된 게시글은 모두 원본에 존재
        original_urls = {p.url for p in posts}
        for post in filtered_posts:
            assert post.url in original_urls, \
                f"Filtered post {post.url} not in original posts"
    
    @given(posts=post_list_strategy(), threshold=st.floats(min_value=-1.0, max_value=0.0))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_custom_threshold_filtering(self, posts, threshold):
        """커스텀 임계값으로 필터링 시 모든 결과가 임계값 미만인지 검증"""
        analyzer = SentimentAnalyzer()
        filtered_posts = analyzer.filter_negative_posts(posts, threshold=threshold)
        
        for post in filtered_posts:
            result = analyzer.analyze_post(post)
            assert result.score < threshold, \
                f"Post score {result.score} >= threshold {threshold}"
    
    def test_empty_list_returns_empty(self):
        """빈 목록 필터링 시 빈 목록 반환 검증"""
        analyzer = SentimentAnalyzer()
        filtered = analyzer.filter_negative_posts([])
        assert filtered == []
    
    def test_all_positive_posts_returns_empty(self):
        """모든 게시글이 긍정적일 때 빈 목록 반환 검증"""
        analyzer = SentimentAnalyzer()
        positive_posts = [
            PostContent(
                url="https://example.com/1",
                title="최고의 게임 대박 명작",
                body="정말 재밌다 굿 최고다",
                site="test",
                keyword="test"
            ),
            PostContent(
                url="https://example.com/2",
                title="완전 좋아 추천합니다",
                body="갓겜 명작 꿀잼",
                site="test",
                keyword="test"
            )
        ]
        
        filtered = analyzer.filter_negative_posts(positive_posts)
        assert len(filtered) == 0
    
    def test_all_negative_posts_returns_all(self):
        """모든 게시글이 부정적일 때 전체 반환 검증"""
        analyzer = SentimentAnalyzer()
        negative_posts = [
            PostContent(
                url="https://example.com/1",
                title="버그 오류 최악",
                body="망겜 쓰레기 노잼",
                site="test",
                keyword="test"
            ),
            PostContent(
                url="https://example.com/2",
                title="렉 튕김 접속불가",
                body="실망 짜증 화난다",
                site="test",
                keyword="test"
            )
        ]
        
        filtered = analyzer.filter_negative_posts(negative_posts)
        # 부정적 게시글이 필터링되어야 함
        assert len(filtered) > 0
        
        # 필터링된 모든 게시글의 점수가 -0.3 미만인지 확인
        for post in filtered:
            result = analyzer.analyze_post(post)
            assert result.score < -0.3
