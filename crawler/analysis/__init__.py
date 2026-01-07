"""
분석 모듈

감성 분석, 이슈 탐지, 트렌드 분석 기능을 제공한다.
"""

# Lazy imports to avoid circular import issues
def __getattr__(name):
    if name == "SentimentAnalyzer":
        from crawler.analysis.sentiment import SentimentAnalyzer
        return SentimentAnalyzer
    elif name == "KeywordExtractor":
        from crawler.analysis.keyword_extractor import KeywordExtractor
        return KeywordExtractor
    elif name == "IssueDetector":
        from crawler.analysis.issue_detector import IssueDetector
        return IssueDetector
    elif name == "TrendAnalyzer":
        from crawler.analysis.trend_analyzer import TrendAnalyzer
        return TrendAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "SentimentAnalyzer",
    "KeywordExtractor",
    "IssueDetector",
    "TrendAnalyzer",
]

# 편의를 위한 함수
def create_sentiment_analyzer(lexicon_dir: str = None):
    """SentimentAnalyzer 인스턴스 생성
    
    Args:
        lexicon_dir: 감성 사전 디렉토리 경로 (선택)
        
    Returns:
        SentimentAnalyzer 인스턴스
    """
    from crawler.analysis.sentiment import SentimentAnalyzer
    return SentimentAnalyzer(lexicon_dir=lexicon_dir)


def create_keyword_extractor():
    """KeywordExtractor 인스턴스 생성
    
    Returns:
        KeywordExtractor 인스턴스
    """
    from crawler.analysis.keyword_extractor import KeywordExtractor
    return KeywordExtractor()


def create_issue_detector(
    sentiment_analyzer=None,
    keyword_extractor=None
):
    """IssueDetector 인스턴스 생성
    
    Args:
        sentiment_analyzer: 감성 분석기 (선택)
        keyword_extractor: 키워드 추출기 (선택)
        
    Returns:
        IssueDetector 인스턴스
    """
    from crawler.analysis.issue_detector import IssueDetector
    return IssueDetector(
        sentiment_analyzer=sentiment_analyzer,
        keyword_extractor=keyword_extractor
    )


def create_trend_analyzer(
    sentiment_analyzer=None
):
    """TrendAnalyzer 인스턴스 생성
    
    Args:
        sentiment_analyzer: 감성 분석기 (선택)
        
    Returns:
        TrendAnalyzer 인스턴스
    """
    from crawler.analysis.trend_analyzer import TrendAnalyzer
    return TrendAnalyzer(sentiment_analyzer=sentiment_analyzer)
