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
    elif name == "AlertManager":
        from crawler.analysis.alert_manager import AlertManager
        return AlertManager
    elif name == "Alert":
        from crawler.analysis.alert_manager import Alert
        return Alert
    elif name == "AlertType":
        from crawler.analysis.alert_manager import AlertType
        return AlertType
    elif name == "AlertPriority":
        from crawler.analysis.alert_manager import AlertPriority
        return AlertPriority
    elif name == "GameAnalyzer":
        from crawler.analysis.game_analyzer import GameAnalyzer
        return GameAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "SentimentAnalyzer",
    "KeywordExtractor",
    "IssueDetector",
    "TrendAnalyzer",
    "AlertManager",
    "Alert",
    "AlertType",
    "AlertPriority",
    "GameAnalyzer",
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



def create_alert_manager(
    sentiment_analyzer=None,
    issue_detector=None,
    trend_analyzer=None
):
    """AlertManager 인스턴스 생성
    
    Args:
        sentiment_analyzer: 감성 분석기 (선택)
        issue_detector: 이슈 탐지기 (선택)
        trend_analyzer: 트렌드 분석기 (선택)
        
    Returns:
        AlertManager 인스턴스
    """
    from crawler.analysis.alert_manager import AlertManager
    return AlertManager(
        sentiment_analyzer=sentiment_analyzer,
        issue_detector=issue_detector,
        trend_analyzer=trend_analyzer
    )


def create_game_analyzer(
    sentiment_analyzer=None,
    issue_detector=None,
    trend_analyzer=None,
    alert_manager=None,
    analysis_store=None,
    profile_manager=None
):
    """GameAnalyzer 인스턴스 생성
    
    Args:
        sentiment_analyzer: 감성 분석기 (선택)
        issue_detector: 이슈 탐지기 (선택)
        trend_analyzer: 트렌드 분석기 (선택)
        alert_manager: 알림 관리자 (선택)
        analysis_store: 분석 결과 저장소 (선택)
        profile_manager: 게임 프로필 관리자 (선택)
        
    Returns:
        GameAnalyzer 인스턴스
    """
    from crawler.analysis.game_analyzer import GameAnalyzer
    return GameAnalyzer(
        sentiment_analyzer=sentiment_analyzer,
        issue_detector=issue_detector,
        trend_analyzer=trend_analyzer,
        alert_manager=alert_manager,
        analysis_store=analysis_store,
        profile_manager=profile_manager
    )
