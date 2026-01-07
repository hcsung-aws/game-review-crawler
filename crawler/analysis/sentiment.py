"""
감성 분석 모듈

Requirements: 2.1, 2.2, 2.5
- 한국어 텍스트의 감성을 분석
- -1.0 ~ 1.0 범위의 감성 점수 반환
- 게시글 및 댓글 감성 분석 지원
"""

import os
import re
from typing import List, Set, Optional
from pathlib import Path

from crawler.models.analysis_models import SentimentResult, SentimentLabel
from crawler.models.data_models import PostContent, Comment


class SentimentAnalyzer:
    """한국어 감성 분석기
    
    Requirements: 2.1, 2.2, 2.5
    - 사전 기반 한국어 감성 분석
    - 긍정/부정/중립 분류 및 점수 계산
    """
    
    def __init__(self, lexicon_dir: Optional[str] = None):
        """감성 분석기 초기화
        
        Args:
            lexicon_dir: 감성 사전 디렉토리 경로 (기본값: 모듈 내 lexicon 디렉토리)
        """
        self.positive_words: Set[str] = set()
        self.negative_words: Set[str] = set()
        
        if lexicon_dir is None:
            # 기본 경로: 현재 모듈의 lexicon 디렉토리
            lexicon_dir = os.path.join(os.path.dirname(__file__), "lexicon")
        
        self.lexicon_dir = lexicon_dir
        self._load_lexicon()
    
    def _load_lexicon(self) -> None:
        """한국어 감성 사전 로드"""
        positive_path = os.path.join(self.lexicon_dir, "positive.txt")
        negative_path = os.path.join(self.lexicon_dir, "negative.txt")
        
        self.positive_words = self._load_word_file(positive_path)
        self.negative_words = self._load_word_file(negative_path)
    
    def _load_word_file(self, filepath: str) -> Set[str]:
        """단어 파일 로드
        
        Args:
            filepath: 단어 파일 경로
            
        Returns:
            단어 집합
        """
        words = set()
        if not os.path.exists(filepath):
            return words
        
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 빈 줄이나 주석 무시
                if not line or line.startswith("#"):
                    continue
                words.add(line)
        
        return words
    
    def _preprocess_text(self, text: str) -> str:
        """텍스트 전처리
        
        Args:
            text: 원본 텍스트
            
        Returns:
            전처리된 텍스트
        """
        if not text:
            return ""
        
        # 소문자 변환 (영어 포함 텍스트 대응)
        text = text.lower()
        
        # 연속된 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _calculate_score(self, text: str) -> float:
        """감성 점수 계산
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            감성 점수 (-1.0 ~ 1.0)
        """
        if not text:
            return 0.0
        
        processed_text = self._preprocess_text(text)
        
        positive_count = 0
        negative_count = 0
        
        # 긍정 단어 카운트
        for word in self.positive_words:
            if word in processed_text:
                positive_count += processed_text.count(word)
        
        # 부정 단어 카운트
        for word in self.negative_words:
            if word in processed_text:
                negative_count += processed_text.count(word)
        
        total_count = positive_count + negative_count
        
        if total_count == 0:
            return 0.0
        
        # 점수 계산: (긍정 - 부정) / 전체
        raw_score = (positive_count - negative_count) / total_count
        
        # -1.0 ~ 1.0 범위로 클램핑
        return max(-1.0, min(1.0, raw_score))
    
    def _determine_label(self, score: float) -> SentimentLabel:
        """감성 레이블 결정
        
        Args:
            score: 감성 점수
            
        Returns:
            감성 레이블
        """
        if score > 0.1:
            return SentimentLabel.POSITIVE
        elif score < -0.1:
            return SentimentLabel.NEGATIVE
        else:
            return SentimentLabel.NEUTRAL
    
    def _calculate_confidence(self, text: str) -> float:
        """신뢰도 계산
        
        Args:
            text: 분석한 텍스트
            
        Returns:
            신뢰도 (0.0 ~ 1.0)
        """
        if not text:
            return 0.5
        
        processed_text = self._preprocess_text(text)
        
        # 감성 단어 총 개수
        sentiment_word_count = 0
        for word in self.positive_words:
            if word in processed_text:
                sentiment_word_count += processed_text.count(word)
        for word in self.negative_words:
            if word in processed_text:
                sentiment_word_count += processed_text.count(word)
        
        # 텍스트 길이 대비 감성 단어 비율로 신뢰도 계산
        text_length = len(processed_text.split())
        if text_length == 0:
            return 0.5
        
        # 감성 단어가 많을수록 신뢰도 증가 (최대 1.0)
        confidence = min(1.0, 0.5 + (sentiment_word_count / text_length) * 0.5)
        
        return confidence
    
    def analyze(self, text: str) -> SentimentResult:
        """텍스트 감성 분석
        
        Requirements: 2.1, 2.2
        - 텍스트의 감성을 분석하여 SentimentResult 반환
        - 점수는 -1.0 ~ 1.0 범위
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            SentimentResult 객체
        """
        if not text or not text.strip():
            # 빈 텍스트는 중립으로 처리
            return SentimentResult(
                score=0.0,
                label=SentimentLabel.NEUTRAL,
                confidence=0.5
            )
        
        score = self._calculate_score(text)
        label = self._determine_label(score)
        confidence = self._calculate_confidence(text)
        
        return SentimentResult(
            score=score,
            label=label,
            confidence=confidence
        )
    
    def analyze_post(self, post: PostContent) -> SentimentResult:
        """게시글 전체 감성 분석
        
        Requirements: 2.1, 2.2
        - 제목과 본문을 합쳐서 감성 분석
        - 제목에 가중치 부여 (2배)
        
        Args:
            post: 게시글 객체
            
        Returns:
            SentimentResult 객체
        """
        # 제목에 가중치 부여 (2배)
        combined_text = f"{post.title} {post.title} {post.body}"
        
        return self.analyze(combined_text)
    
    def analyze_comments(self, comments: List[Comment]) -> List[SentimentResult]:
        """댓글 목록 감성 분석
        
        Requirements: 2.1, 2.2
        - 각 댓글의 감성을 개별 분석
        
        Args:
            comments: 댓글 목록
            
        Returns:
            SentimentResult 목록
        """
        results = []
        for comment in comments:
            result = self.analyze(comment.content)
            results.append(result)
        
        return results
    
    def analyze_post_with_comments(self, post: PostContent) -> SentimentResult:
        """게시글과 댓글 통합 감성 분석
        
        Args:
            post: 게시글 객체 (댓글 포함)
            
        Returns:
            통합 SentimentResult 객체
        """
        # 게시글 분석
        post_result = self.analyze_post(post)
        
        if not post.comments:
            return post_result
        
        # 댓글 분석
        comment_results = self.analyze_comments(post.comments)
        
        if not comment_results:
            return post_result
        
        # 가중 평균 계산 (게시글 70%, 댓글 30%)
        comment_avg_score = sum(r.score for r in comment_results) / len(comment_results)
        combined_score = post_result.score * 0.7 + comment_avg_score * 0.3
        
        # -1.0 ~ 1.0 범위로 클램핑
        combined_score = max(-1.0, min(1.0, combined_score))
        
        label = self._determine_label(combined_score)
        
        # 신뢰도는 게시글과 댓글 신뢰도의 평균
        comment_avg_confidence = sum(r.confidence for r in comment_results) / len(comment_results)
        combined_confidence = (post_result.confidence + comment_avg_confidence) / 2
        
        return SentimentResult(
            score=combined_score,
            label=label,
            confidence=combined_confidence
        )
    
    def filter_negative_posts(
        self, 
        posts: List[PostContent], 
        threshold: float = -0.3
    ) -> List[PostContent]:
        """부정적 게시글 필터링
        
        Requirements: 2.4
        - Sentiment_Score가 threshold 미만인 게시글만 반환
        
        Args:
            posts: 게시글 목록
            threshold: 부정 판단 임계값 (기본값: -0.3)
            
        Returns:
            부정적 게시글 목록
        """
        negative_posts = []
        for post in posts:
            result = self.analyze_post(post)
            if result.score < threshold:
                negative_posts.append(post)
        
        return negative_posts
    
    def get_sentiment_distribution(
        self, 
        posts: List[PostContent]
    ) -> dict:
        """게시글 목록의 감성 분포 계산
        
        Args:
            posts: 게시글 목록
            
        Returns:
            감성 분포 딕셔너리 {"positive": n, "negative": n, "neutral": n}
        """
        distribution = {
            "positive": 0,
            "negative": 0,
            "neutral": 0
        }
        
        for post in posts:
            result = self.analyze_post(post)
            distribution[result.label.value] += 1
        
        return distribution
    
    def get_average_sentiment(self, posts: List[PostContent]) -> float:
        """게시글 목록의 평균 감성 점수 계산
        
        Args:
            posts: 게시글 목록
            
        Returns:
            평균 감성 점수
        """
        if not posts:
            return 0.0
        
        total_score = 0.0
        for post in posts:
            result = self.analyze_post(post)
            total_score += result.score
        
        return total_score / len(posts)
