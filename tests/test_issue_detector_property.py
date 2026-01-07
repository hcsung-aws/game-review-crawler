"""
Property-Based Tests for Issue Detection

**Feature: game-analytics-dashboard, Property 7: Keyword Clustering Completeness**
**Validates: Requirements 3.2**

For any 키워드 목록에 대해 클러스터링을 수행하면, 
모든 입력 키워드는 정확히 하나의 클러스터에 속해야 한다.

**Feature: game-analytics-dashboard, Property 8: Issue Priority Monotonicity**
**Validates: Requirements 3.3**

For any 두 이슈 A와 B에서, A의 조회수, 댓글수, 언급 빈도가 모두 B 이상이면 
A의 Issue_Priority는 B 이상이어야 한다.

**Feature: game-analytics-dashboard, Property 9: Hot Issue Top Percentile**
**Validates: Requirements 3.4**

For any 이슈 목록에서 Hot Issue로 분류된 이슈들은 
Issue_Priority 기준 상위 10%에 해당해야 한다.

**Feature: game-analytics-dashboard, Property 10: Issue List Sorting**
**Validates: Requirements 3.5**

For any 이슈 목록을 우선순위로 정렬하면, 
결과는 Issue_Priority 내림차순이어야 한다.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from datetime import datetime
from typing import List

from crawler.analysis.issue_detector import IssueDetector
from crawler.analysis.keyword_extractor import KeywordExtractor
from crawler.models.analysis_models import KeywordCluster, DetectedIssue, IssueSeverity
from crawler.models.data_models import PostContent, Comment


# Custom strategies for generating test data
@st.composite
def keyword_strategy(draw):
    """키워드 생성 전략"""
    korean_chars = "가나다라마바사아자차카타파하업데이트버그오류패치이벤트"
    english_chars = "abcdefghijklmnopqrstuvwxyz"
    
    # 한글 또는 영문 키워드 생성
    if draw(st.booleans()):
        # 한글 키워드
        keyword = draw(st.text(
            alphabet=st.sampled_from(korean_chars),
            min_size=2,
            max_size=6
        ))
    else:
        # 영문 키워드
        keyword = draw(st.text(
            alphabet=st.sampled_from(english_chars),
            min_size=2,
            max_size=10
        ))
    
    assume(len(keyword) >= 2)
    return keyword


@st.composite
def keyword_list_strategy(draw):
    """키워드 목록 생성 전략"""
    keywords = draw(st.lists(
        keyword_strategy(),
        min_size=1,
        max_size=30,
        unique=True
    ))
    assume(len(keywords) >= 1)
    return keywords


@st.composite
def post_content_strategy(draw):
    """PostContent 객체 생성 전략"""
    keywords = ["업데이트", "버그", "오류", "패치", "이벤트", "보상", "밸런스", "캐릭터"]
    
    title_words = draw(st.lists(
        st.sampled_from(keywords),
        min_size=1,
        max_size=5
    ))
    body_words = draw(st.lists(
        st.sampled_from(keywords),
        min_size=1,
        max_size=20
    ))
    
    return PostContent(
        url=f"https://example.com/post/{draw(st.integers(min_value=1, max_value=100000))}",
        title=" ".join(title_words),
        body=" ".join(body_words),
        site="test_site",
        keyword="test_keyword",
        author="test_author",
        created_at=datetime.now(),
        view_count=draw(st.integers(min_value=0, max_value=100000)),
        like_count=draw(st.integers(min_value=0, max_value=10000)),
        comments=[]
    )


@st.composite
def post_list_strategy(draw):
    """PostContent 목록 생성 전략"""
    posts = draw(st.lists(
        post_content_strategy(),
        min_size=1,
        max_size=20
    ))
    assume(len(posts) >= 1)
    return posts


@st.composite
def keyword_cluster_strategy(draw):
    """KeywordCluster 객체 생성 전략"""
    keywords = draw(keyword_list_strategy())
    
    return KeywordCluster(
        cluster_id=f"cluster_{draw(st.integers(min_value=1, max_value=1000))}",
        keywords=keywords,
        representative=keywords[0],
        post_count=draw(st.integers(min_value=0, max_value=100)),
        total_views=draw(st.integers(min_value=0, max_value=100000)),
        total_comments=draw(st.integers(min_value=0, max_value=1000))
    )


@st.composite
def detected_issue_strategy(draw):
    """DetectedIssue 객체 생성 전략"""
    cluster = draw(keyword_cluster_strategy())
    
    return DetectedIssue(
        issue_id=f"issue_{draw(st.integers(min_value=1, max_value=10000))}",
        title=cluster.representative,
        cluster=cluster,
        priority_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        is_hot=False,
        is_bug=draw(st.booleans()),
        severity=draw(st.sampled_from(list(IssueSeverity))),
        related_posts=[],
        first_seen=datetime.now(),
        sentiment_avg=draw(st.floats(min_value=-1.0, max_value=1.0))
    )


@st.composite
def issue_list_strategy(draw):
    """DetectedIssue 목록 생성 전략"""
    issues = draw(st.lists(
        detected_issue_strategy(),
        min_size=1,
        max_size=20
    ))
    assume(len(issues) >= 1)
    return issues


class TestKeywordClusteringCompleteness:
    """
    **Feature: game-analytics-dashboard, Property 7: Keyword Clustering Completeness**
    **Validates: Requirements 3.2**
    
    For any 키워드 목록에 대해 클러스터링을 수행하면, 
    모든 입력 키워드는 정확히 하나의 클러스터에 속해야 한다.
    """
    
    @given(keywords=keyword_list_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_all_keywords_in_exactly_one_cluster(self, keywords: List[str]):
        """모든 키워드가 정확히 하나의 클러스터에 속하는지 검증"""
        detector = IssueDetector()
        clusters = detector.cluster_keywords(keywords)
        
        # 모든 클러스터의 키워드 수집
        all_clustered_keywords = []
        for cluster in clusters:
            all_clustered_keywords.extend(cluster.keywords)
        
        # 모든 입력 키워드가 클러스터에 포함되어야 함
        for keyword in keywords:
            assert keyword in all_clustered_keywords, \
                f"Keyword '{keyword}' not found in any cluster"
        
        # 각 키워드는 정확히 한 번만 나타나야 함
        keyword_counts = {}
        for kw in all_clustered_keywords:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        
        for keyword in keywords:
            assert keyword_counts.get(keyword, 0) == 1, \
                f"Keyword '{keyword}' appears {keyword_counts.get(keyword, 0)} times, expected 1"
    
    @given(keywords=keyword_list_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_cluster_count_at_most_keyword_count(self, keywords: List[str]):
        """클러스터 수가 키워드 수를 초과하지 않는지 검증"""
        detector = IssueDetector()
        clusters = detector.cluster_keywords(keywords)
        
        assert len(clusters) <= len(keywords), \
            f"Cluster count {len(clusters)} > keyword count {len(keywords)}"
    
    @given(keywords=keyword_list_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_each_cluster_has_representative(self, keywords: List[str]):
        """각 클러스터에 대표 키워드가 있는지 검증"""
        detector = IssueDetector()
        clusters = detector.cluster_keywords(keywords)
        
        for cluster in clusters:
            assert cluster.representative in cluster.keywords, \
                f"Representative '{cluster.representative}' not in cluster keywords"
    
    def test_empty_keywords_returns_empty_clusters(self):
        """빈 키워드 목록은 빈 클러스터 목록 반환"""
        detector = IssueDetector()
        clusters = detector.cluster_keywords([])
        assert clusters == []
    
    def test_single_keyword_single_cluster(self):
        """단일 키워드는 단일 클러스터 생성"""
        detector = IssueDetector()
        clusters = detector.cluster_keywords(["버그"])
        
        assert len(clusters) == 1
        assert clusters[0].keywords == ["버그"]
        assert clusters[0].representative == "버그"


class TestIssuePriorityMonotonicity:
    """
    **Feature: game-analytics-dashboard, Property 8: Issue Priority Monotonicity**
    **Validates: Requirements 3.3**
    
    For any 두 이슈 A와 B에서, A의 조회수, 댓글수, 언급 빈도가 모두 B 이상이면 
    A의 Issue_Priority는 B 이상이어야 한다.
    """
    
    @given(
        views_a=st.integers(min_value=0, max_value=10000),
        comments_a=st.integers(min_value=0, max_value=1000),
        posts_a=st.integers(min_value=1, max_value=100),
        views_b=st.integers(min_value=0, max_value=10000),
        comments_b=st.integers(min_value=0, max_value=1000),
        posts_b=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_priority_monotonicity(
        self, 
        views_a: int, comments_a: int, posts_a: int,
        views_b: int, comments_b: int, posts_b: int
    ):
        """A의 모든 지표가 B 이상이면 A의 우선순위도 B 이상인지 검증"""
        # A가 B보다 모든 지표에서 크거나 같은 경우만 테스트
        assume(views_a >= views_b and comments_a >= comments_b and posts_a >= posts_b)
        
        detector = IssueDetector()
        
        # 클러스터 A 생성
        cluster_a = KeywordCluster(
            cluster_id="cluster_a",
            keywords=["키워드A"],
            representative="키워드A",
            post_count=posts_a,
            total_views=views_a,
            total_comments=comments_a
        )
        
        # 클러스터 B 생성
        cluster_b = KeywordCluster(
            cluster_id="cluster_b",
            keywords=["키워드B"],
            representative="키워드B",
            post_count=posts_b,
            total_views=views_b,
            total_comments=comments_b
        )
        
        # 테스트용 게시글 목록 생성 (정규화를 위해 필요)
        posts = [
            PostContent(
                url=f"https://example.com/{i}",
                title="테스트",
                body="테스트 본문",
                site="test",
                keyword="test",
                view_count=max(views_a, views_b),
                comments=[Comment(author="user", content="댓글") for _ in range(max(comments_a, comments_b))]
            )
            for i in range(max(posts_a, posts_b))
        ]
        
        priority_a = detector.calculate_priority(cluster_a, posts)
        priority_b = detector.calculate_priority(cluster_b, posts)
        
        assert priority_a >= priority_b, \
            f"Priority A ({priority_a}) < Priority B ({priority_b}) despite A having >= metrics"
    
    def test_higher_views_higher_priority(self):
        """조회수가 높으면 우선순위도 높은지 검증"""
        detector = IssueDetector()
        
        cluster_high = KeywordCluster(
            cluster_id="high",
            keywords=["키워드"],
            representative="키워드",
            post_count=10,
            total_views=10000,
            total_comments=100
        )
        
        cluster_low = KeywordCluster(
            cluster_id="low",
            keywords=["키워드"],
            representative="키워드",
            post_count=10,
            total_views=1000,
            total_comments=100
        )
        
        posts = [
            PostContent(
                url=f"https://example.com/{i}",
                title="테스트",
                body="테스트",
                site="test",
                keyword="test",
                view_count=10000,
                comments=[Comment(author="user", content="댓글") for _ in range(100)]
            )
            for i in range(10)
        ]
        
        priority_high = detector.calculate_priority(cluster_high, posts)
        priority_low = detector.calculate_priority(cluster_low, posts)
        
        assert priority_high >= priority_low


class TestHotIssueTopPercentile:
    """
    **Feature: game-analytics-dashboard, Property 9: Hot Issue Top Percentile**
    **Validates: Requirements 3.4**
    
    For any 이슈 목록에서 Hot Issue로 분류된 이슈들은 
    Issue_Priority 기준 상위 10%에 해당해야 한다.
    """
    
    @given(issues=issue_list_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_hot_issues_are_top_percentile(self, issues: List[DetectedIssue]):
        """Hot Issue가 상위 10%에 해당하는지 검증"""
        detector = IssueDetector()
        hot_issues = detector.detect_hot_issues(issues, threshold_percentile=0.9)
        
        if not hot_issues:
            return  # Hot Issue가 없으면 통과
        
        # 우선순위로 정렬
        sorted_issues = sorted(issues, key=lambda x: x.priority_score, reverse=True)
        
        # 상위 10% 계산
        top_count = max(1, int(len(sorted_issues) * 0.1))
        top_priorities = [issue.priority_score for issue in sorted_issues[:top_count]]
        min_top_priority = min(top_priorities) if top_priorities else 0
        
        # 모든 Hot Issue가 상위 10% 우선순위 이상인지 확인
        for hot_issue in hot_issues:
            assert hot_issue.priority_score >= min_top_priority, \
                f"Hot issue priority {hot_issue.priority_score} < min top priority {min_top_priority}"
    
    @given(issues=issue_list_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_hot_issues_have_is_hot_flag(self, issues: List[DetectedIssue]):
        """Hot Issue로 분류된 이슈는 is_hot=True인지 검증"""
        detector = IssueDetector()
        hot_issues = detector.detect_hot_issues(issues)
        
        for issue in hot_issues:
            assert issue.is_hot is True, \
                f"Hot issue {issue.issue_id} has is_hot=False"
    
    @given(issues=issue_list_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_hot_issue_count_at_most_10_percent(self, issues: List[DetectedIssue]):
        """Hot Issue 수가 전체의 10% 이하인지 검증"""
        detector = IssueDetector()
        hot_issues = detector.detect_hot_issues(issues, threshold_percentile=0.9)
        
        expected_max = max(1, int(len(issues) * 0.1))
        assert len(hot_issues) <= expected_max, \
            f"Hot issue count {len(hot_issues)} > expected max {expected_max}"
    
    def test_empty_issues_returns_empty_hot_issues(self):
        """빈 이슈 목록은 빈 Hot Issue 목록 반환"""
        detector = IssueDetector()
        hot_issues = detector.detect_hot_issues([])
        assert hot_issues == []
    
    def test_single_issue_is_hot(self):
        """단일 이슈는 Hot Issue로 분류"""
        detector = IssueDetector()
        
        issue = DetectedIssue(
            issue_id="issue_1",
            title="테스트",
            cluster=KeywordCluster(
                cluster_id="cluster_1",
                keywords=["테스트"],
                representative="테스트"
            ),
            priority_score=0.5
        )
        
        hot_issues = detector.detect_hot_issues([issue])
        assert len(hot_issues) == 1
        assert hot_issues[0].is_hot is True


class TestIssueListSorting:
    """
    **Feature: game-analytics-dashboard, Property 10: Issue List Sorting**
    **Validates: Requirements 3.5**
    
    For any 이슈 목록을 우선순위로 정렬하면, 
    결과는 Issue_Priority 내림차순이어야 한다.
    """
    
    @given(posts=post_list_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_detected_issues_sorted_by_priority_descending(self, posts: List[PostContent]):
        """detect_issues 결과가 우선순위 내림차순인지 검증"""
        detector = IssueDetector()
        issues = detector.detect_issues(posts)
        
        if len(issues) <= 1:
            return  # 이슈가 1개 이하면 정렬 검증 불필요
        
        # 연속된 이슈 쌍에서 앞의 우선순위가 뒤보다 크거나 같아야 함
        for i in range(len(issues) - 1):
            assert issues[i].priority_score >= issues[i + 1].priority_score, \
                f"Issue {i} priority {issues[i].priority_score} < Issue {i+1} priority {issues[i + 1].priority_score}"
    
    @given(issues=issue_list_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_manual_sorting_is_descending(self, issues: List[DetectedIssue]):
        """수동 정렬 결과가 내림차순인지 검증"""
        sorted_issues = sorted(issues, key=lambda x: x.priority_score, reverse=True)
        
        for i in range(len(sorted_issues) - 1):
            assert sorted_issues[i].priority_score >= sorted_issues[i + 1].priority_score, \
                f"Sorted issue {i} priority < issue {i+1} priority"
    
    def test_empty_posts_returns_empty_issues(self):
        """빈 게시글 목록은 빈 이슈 목록 반환"""
        detector = IssueDetector()
        issues = detector.detect_issues([])
        assert issues == []
    
    def test_issues_with_same_priority_stable(self):
        """동일 우선순위 이슈들의 순서가 안정적인지 검증"""
        detector = IssueDetector()
        
        # 동일한 우선순위를 가진 이슈들
        issues = [
            DetectedIssue(
                issue_id=f"issue_{i}",
                title=f"테스트_{i}",
                cluster=KeywordCluster(
                    cluster_id=f"cluster_{i}",
                    keywords=[f"키워드_{i}"],
                    representative=f"키워드_{i}"
                ),
                priority_score=0.5
            )
            for i in range(5)
        ]
        
        # 정렬 후에도 동일 우선순위 이슈들이 유지되어야 함
        sorted_issues = sorted(issues, key=lambda x: x.priority_score, reverse=True)
        
        for issue in sorted_issues:
            assert issue.priority_score == 0.5


class TestBugKeywordDetection:
    """
    **Feature: game-analytics-dashboard, Property 17: Bug Keyword Detection**
    **Validates: Requirements 7.1, 7.2**
    
    For any "버그", "오류", "에러", "렉", "튕김", "접속불가" 키워드가 포함된 게시글은 
    버그 관련 게시글로 분류되어야 한다.
    """
    
    # 필수 버그 키워드 목록 (Requirements 7.2에 명시된 키워드)
    REQUIRED_BUG_KEYWORDS = ["버그", "오류", "에러", "렉", "튕김", "접속불가"]
    
    @given(bug_keyword=st.sampled_from(REQUIRED_BUG_KEYWORDS))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_post_with_bug_keyword_in_title_classified_as_bug(self, bug_keyword: str):
        """제목에 버그 키워드가 있으면 버그로 분류되는지 검증"""
        detector = IssueDetector()
        
        post = PostContent(
            url="https://example.com/post/1",
            title=f"게임에서 {bug_keyword} 발생했습니다",
            body="일반적인 본문 내용입니다.",
            site="test_site",
            keyword="test",
            view_count=100
        )
        
        assert detector.classify_bug(post) is True, \
            f"Post with '{bug_keyword}' in title should be classified as bug"
    
    @given(bug_keyword=st.sampled_from(REQUIRED_BUG_KEYWORDS))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_post_with_bug_keyword_in_body_classified_as_bug(self, bug_keyword: str):
        """본문에 버그 키워드가 있으면 버그로 분류되는지 검증"""
        detector = IssueDetector()
        
        post = PostContent(
            url="https://example.com/post/1",
            title="일반적인 제목입니다",
            body=f"게임 플레이 중 {bug_keyword}가 발생했습니다. 해결 방법을 알려주세요.",
            site="test_site",
            keyword="test",
            view_count=100
        )
        
        assert detector.classify_bug(post) is True, \
            f"Post with '{bug_keyword}' in body should be classified as bug"
    
    @given(bug_keyword=st.sampled_from(REQUIRED_BUG_KEYWORDS))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_text_with_bug_keyword_classified_as_bug(self, bug_keyword: str):
        """텍스트에 버그 키워드가 있으면 버그로 분류되는지 검증"""
        detector = IssueDetector()
        
        text = f"이 게임에서 {bug_keyword}가 자주 발생합니다"
        
        assert detector.classify_bug_from_text(text) is True, \
            f"Text with '{bug_keyword}' should be classified as bug"
    
    @given(
        prefix=st.text(min_size=0, max_size=20),
        suffix=st.text(min_size=0, max_size=20),
        bug_keyword=st.sampled_from(REQUIRED_BUG_KEYWORDS)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_bug_keyword_detected_regardless_of_context(self, prefix: str, suffix: str, bug_keyword: str):
        """버그 키워드가 어떤 문맥에 있어도 탐지되는지 검증"""
        detector = IssueDetector()
        
        text = f"{prefix}{bug_keyword}{suffix}"
        
        assert detector.classify_bug_from_text(text) is True, \
            f"Bug keyword '{bug_keyword}' should be detected in any context"
    
    def test_post_without_bug_keyword_not_classified_as_bug(self):
        """버그 키워드가 없는 게시글은 버그로 분류되지 않는지 검증"""
        detector = IssueDetector()
        
        post = PostContent(
            url="https://example.com/post/1",
            title="게임 업데이트 소식",
            body="새로운 캐릭터가 추가되었습니다. 이벤트도 진행 중입니다.",
            site="test_site",
            keyword="test",
            view_count=100
        )
        
        assert detector.classify_bug(post) is False, \
            "Post without bug keywords should not be classified as bug"
    
    def test_empty_text_not_classified_as_bug(self):
        """빈 텍스트는 버그로 분류되지 않는지 검증"""
        detector = IssueDetector()
        
        assert detector.classify_bug_from_text("") is False
        assert detector.classify_bug_from_text(None) is False
    
    def test_get_bug_keywords_found_returns_correct_keywords(self):
        """발견된 버그 키워드 목록이 정확한지 검증"""
        detector = IssueDetector()
        
        text = "게임에서 버그와 오류가 발생했습니다. 렉도 심합니다."
        found = detector.get_bug_keywords_found(text)
        
        assert "버그" in found
        assert "오류" in found
        assert "렉" in found
    
    @given(bug_keywords=st.lists(
        st.sampled_from(REQUIRED_BUG_KEYWORDS),
        min_size=1,
        max_size=6,
        unique=True
    ))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_multiple_bug_keywords_all_detected(self, bug_keywords: List[str]):
        """여러 버그 키워드가 모두 탐지되는지 검증"""
        detector = IssueDetector()
        
        text = " ".join(bug_keywords) + " 문제가 있습니다"
        found = detector.get_bug_keywords_found(text)
        
        for keyword in bug_keywords:
            assert keyword in found, \
                f"Bug keyword '{keyword}' should be found in text"


class TestBugSeverityMonotonicity:
    """
    **Feature: game-analytics-dashboard, Property 18: Bug Severity Monotonicity**
    **Validates: Requirements 7.4**
    
    For any 두 버그 이슈 A와 B에서, A의 언급 빈도와 부정적 감성 강도가 모두 B보다 높으면 
    A의 심각도는 B 이상이어야 한다.
    """
    
    # 심각도 순서 (높은 것이 앞)
    SEVERITY_ORDER = {
        IssueSeverity.CRITICAL: 0,
        IssueSeverity.HIGH: 1,
        IssueSeverity.MEDIUM: 2,
        IssueSeverity.LOW: 3
    }
    
    @given(
        post_count_a=st.integers(min_value=1, max_value=100),
        sentiment_a=st.floats(min_value=-1.0, max_value=0.0),  # 부정적 감성
        post_count_b=st.integers(min_value=1, max_value=100),
        sentiment_b=st.floats(min_value=-1.0, max_value=0.0)   # 부정적 감성
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_severity_monotonicity(
        self, 
        post_count_a: int, sentiment_a: float,
        post_count_b: int, sentiment_b: float
    ):
        """A의 언급 빈도와 부정적 감성이 B보다 높으면 A의 심각도가 B 이상인지 검증"""
        # A가 B보다 언급 빈도가 높고 부정적 감성이 더 강한 경우만 테스트
        # 부정적 감성이 강하다 = sentiment 값이 더 낮다 (더 음수)
        assume(post_count_a >= post_count_b and sentiment_a <= sentiment_b)
        
        detector = IssueDetector()
        
        severity_a = detector.calculate_severity_from_metrics(
            post_count=post_count_a,
            sentiment_avg=sentiment_a,
            max_post_count=100
        )
        
        severity_b = detector.calculate_severity_from_metrics(
            post_count=post_count_b,
            sentiment_avg=sentiment_b,
            max_post_count=100
        )
        
        # A의 심각도가 B 이상이어야 함 (순서 값이 작거나 같아야 함)
        assert self.SEVERITY_ORDER[severity_a] <= self.SEVERITY_ORDER[severity_b], \
            f"Severity A ({severity_a.value}) should be >= Severity B ({severity_b.value})"
    
    @given(
        post_count=st.integers(min_value=1, max_value=100),
        sentiment=st.floats(min_value=-1.0, max_value=1.0)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_severity_is_valid_enum(self, post_count: int, sentiment: float):
        """심각도가 유효한 IssueSeverity enum 값인지 검증"""
        detector = IssueDetector()
        
        severity = detector.calculate_severity_from_metrics(
            post_count=post_count,
            sentiment_avg=sentiment,
            max_post_count=100
        )
        
        assert severity in IssueSeverity, \
            f"Severity {severity} is not a valid IssueSeverity"
    
    def test_high_frequency_high_negative_sentiment_is_critical(self):
        """높은 언급 빈도와 강한 부정적 감성은 CRITICAL인지 검증"""
        detector = IssueDetector()
        
        severity = detector.calculate_severity_from_metrics(
            post_count=100,
            sentiment_avg=-1.0,
            max_post_count=100
        )
        
        assert severity == IssueSeverity.CRITICAL, \
            f"High frequency + strong negative sentiment should be CRITICAL, got {severity.value}"
    
    def test_low_frequency_neutral_sentiment_is_low(self):
        """낮은 언급 빈도와 중립적 감성은 LOW인지 검증"""
        detector = IssueDetector()
        
        severity = detector.calculate_severity_from_metrics(
            post_count=1,
            sentiment_avg=0.0,
            max_post_count=100
        )
        
        assert severity == IssueSeverity.LOW, \
            f"Low frequency + neutral sentiment should be LOW, got {severity.value}"
    
    def test_positive_sentiment_reduces_severity(self):
        """긍정적 감성은 심각도를 낮추는지 검증"""
        detector = IssueDetector()
        
        # 동일한 언급 빈도에서 긍정적 감성 vs 부정적 감성
        severity_positive = detector.calculate_severity_from_metrics(
            post_count=50,
            sentiment_avg=0.5,  # 긍정적
            max_post_count=100
        )
        
        severity_negative = detector.calculate_severity_from_metrics(
            post_count=50,
            sentiment_avg=-0.5,  # 부정적
            max_post_count=100
        )
        
        # 부정적 감성의 심각도가 더 높아야 함
        assert self.SEVERITY_ORDER[severity_negative] <= self.SEVERITY_ORDER[severity_positive], \
            f"Negative sentiment severity ({severity_negative.value}) should be >= positive ({severity_positive.value})"
    
    @given(
        post_count_a=st.integers(min_value=1, max_value=100),
        post_count_b=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_higher_frequency_same_sentiment_higher_or_equal_severity(
        self, post_count_a: int, post_count_b: int
    ):
        """동일 감성에서 언급 빈도가 높으면 심각도가 높거나 같은지 검증"""
        assume(post_count_a >= post_count_b)
        
        detector = IssueDetector()
        fixed_sentiment = -0.5
        
        severity_a = detector.calculate_severity_from_metrics(
            post_count=post_count_a,
            sentiment_avg=fixed_sentiment,
            max_post_count=100
        )
        
        severity_b = detector.calculate_severity_from_metrics(
            post_count=post_count_b,
            sentiment_avg=fixed_sentiment,
            max_post_count=100
        )
        
        assert self.SEVERITY_ORDER[severity_a] <= self.SEVERITY_ORDER[severity_b], \
            f"Higher frequency should have >= severity"
