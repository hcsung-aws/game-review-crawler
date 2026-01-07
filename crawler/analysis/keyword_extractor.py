"""
키워드 추출기 모듈

Requirements: 3.1
- 형태소 분석 기반 키워드 추출
- 불용어 필터링
- 게시글에서 주요 키워드 추출
"""

import re
import os
from typing import List, Set, Dict, Optional
from collections import Counter
from pathlib import Path

from crawler.models.data_models import PostContent


class KeywordExtractor:
    """키워드 추출기
    
    Requirements: 3.1
    - 게시글에서 주요 키워드를 추출
    - 불용어 필터링 적용
    - 빈도 기반 키워드 순위화
    """
    
    # 기본 불용어 목록 (한국어)
    DEFAULT_STOPWORDS = {
        # 조사
        "이", "가", "은", "는", "을", "를", "의", "에", "에서", "로", "으로",
        "와", "과", "도", "만", "까지", "부터", "에게", "한테", "께",
        # 대명사
        "나", "너", "저", "우리", "그", "그녀", "이것", "저것", "그것",
        # 접속사/부사
        "그리고", "그러나", "하지만", "그래서", "따라서", "또한", "또",
        "그런데", "그러면", "그렇지만", "왜냐하면", "즉", "곧",
        # 일반 동사/형용사 어미
        "하다", "되다", "있다", "없다", "같다", "보다", "주다", "받다",
        "한다", "된다", "있는", "없는", "같은", "보는", "주는", "받는",
        "했다", "됐다", "있었다", "없었다", "같았다", "봤다", "줬다", "받았다",
        "합니다", "됩니다", "있습니다", "없습니다", "같습니다",
        "해요", "돼요", "있어요", "없어요", "같아요",
        # 일반적인 단어
        "것", "수", "등", "때", "중", "더", "잘", "못", "안", "좀",
        "정말", "진짜", "너무", "매우", "아주", "완전", "엄청",
        "이번", "다음", "지금", "오늘", "어제", "내일",
        "여기", "거기", "저기", "어디",
        # 게임 커뮤니티 일반 용어
        "게임", "유저", "플레이", "플레이어", "캐릭터", "캐릭",
        "ㅋㅋ", "ㅋㅋㅋ", "ㅋㅋㅋㅋ", "ㅎㅎ", "ㅎㅎㅎ",
        "ㅠㅠ", "ㅜㅜ", "ㅠㅠㅠ", "ㅜㅜㅜ",
        # 숫자/특수문자 관련
        "하나", "둘", "셋", "넷", "다섯",
    }
    
    def __init__(
        self, 
        stopwords: Optional[Set[str]] = None,
        min_word_length: int = 2,
        max_word_length: int = 20
    ):
        """키워드 추출기 초기화
        
        Args:
            stopwords: 불용어 집합 (None이면 기본 불용어 사용)
            min_word_length: 최소 단어 길이
            max_word_length: 최대 단어 길이
        """
        self.stopwords = stopwords if stopwords is not None else self.DEFAULT_STOPWORDS.copy()
        self.min_word_length = min_word_length
        self.max_word_length = max_word_length
    
    def add_stopwords(self, words: Set[str]) -> None:
        """불용어 추가
        
        Args:
            words: 추가할 불용어 집합
        """
        self.stopwords.update(words)
    
    def _preprocess_text(self, text: str) -> str:
        """텍스트 전처리
        
        Args:
            text: 원본 텍스트
            
        Returns:
            전처리된 텍스트
        """
        if not text:
            return ""
        
        # URL 제거
        text = re.sub(r'https?://\S+', '', text)
        
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)
        
        # 특수문자 제거 (한글, 영문, 숫자만 유지)
        text = re.sub(r'[^\w\s가-힣]', ' ', text)
        
        # 연속된 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip().lower()
    
    def _tokenize(self, text: str) -> List[str]:
        """텍스트 토큰화 (간단한 공백 기반 + 한국어 처리)
        
        Args:
            text: 전처리된 텍스트
            
        Returns:
            토큰 리스트
        """
        if not text:
            return []
        
        # 공백 기반 토큰화
        tokens = text.split()
        
        # 한국어 복합어 분리 (간단한 규칙 기반)
        expanded_tokens = []
        for token in tokens:
            # 길이 필터링
            if len(token) < self.min_word_length or len(token) > self.max_word_length:
                continue
            
            expanded_tokens.append(token)
            
            # 긴 한국어 단어는 2-gram, 3-gram으로 분리
            if len(token) >= 4 and self._is_korean(token):
                # 2-gram
                for i in range(len(token) - 1):
                    ngram = token[i:i+2]
                    if len(ngram) >= self.min_word_length:
                        expanded_tokens.append(ngram)
                # 3-gram
                for i in range(len(token) - 2):
                    ngram = token[i:i+3]
                    if len(ngram) >= self.min_word_length:
                        expanded_tokens.append(ngram)
        
        return expanded_tokens
    
    def _is_korean(self, text: str) -> bool:
        """한국어 포함 여부 확인
        
        Args:
            text: 확인할 텍스트
            
        Returns:
            한국어 포함 여부
        """
        return bool(re.search(r'[가-힣]', text))
    
    def _filter_stopwords(self, tokens: List[str]) -> List[str]:
        """불용어 필터링
        
        Args:
            tokens: 토큰 리스트
            
        Returns:
            필터링된 토큰 리스트
        """
        return [token for token in tokens if token not in self.stopwords]
    
    def extract_from_text(self, text: str, top_n: int = 20) -> List[str]:
        """텍스트에서 키워드 추출
        
        Args:
            text: 분석할 텍스트
            top_n: 반환할 상위 키워드 수
            
        Returns:
            키워드 리스트 (빈도순)
        """
        if not text or not text.strip():
            return []
        
        # 전처리
        processed_text = self._preprocess_text(text)
        
        # 토큰화
        tokens = self._tokenize(processed_text)
        
        # 불용어 필터링
        filtered_tokens = self._filter_stopwords(tokens)
        
        if not filtered_tokens:
            return []
        
        # 빈도 계산
        counter = Counter(filtered_tokens)
        
        # 상위 N개 반환
        return [word for word, _ in counter.most_common(top_n)]
    
    def extract_from_post(self, post: PostContent, top_n: int = 20) -> List[str]:
        """게시글에서 키워드 추출
        
        Args:
            post: 게시글 객체
            top_n: 반환할 상위 키워드 수
            
        Returns:
            키워드 리스트 (빈도순)
        """
        # 제목과 본문 결합 (제목에 가중치 부여)
        combined_text = f"{post.title} {post.title} {post.body}"
        
        # 댓글 내용도 포함
        for comment in post.comments:
            combined_text += f" {comment.content}"
        
        return self.extract_from_text(combined_text, top_n)
    
    def extract_from_posts(
        self, 
        posts: List[PostContent], 
        top_n: int = 50
    ) -> List[str]:
        """여러 게시글에서 키워드 추출
        
        Requirements: 3.1
        - 게시글 데이터를 분석하여 반복적으로 언급되는 키워드 추출
        
        Args:
            posts: 게시글 목록
            top_n: 반환할 상위 키워드 수
            
        Returns:
            키워드 리스트 (빈도순)
        """
        if not posts:
            return []
        
        all_keywords: Counter = Counter()
        
        for post in posts:
            # 각 게시글에서 키워드 추출
            keywords = self.extract_from_post(post, top_n=100)
            
            # 빈도 누적
            all_keywords.update(keywords)
        
        # 상위 N개 반환
        return [word for word, _ in all_keywords.most_common(top_n)]
    
    def get_keyword_frequencies(
        self, 
        posts: List[PostContent]
    ) -> Dict[str, int]:
        """키워드별 빈도 계산
        
        Args:
            posts: 게시글 목록
            
        Returns:
            키워드-빈도 딕셔너리
        """
        if not posts:
            return {}
        
        all_keywords: Counter = Counter()
        
        for post in posts:
            keywords = self.extract_from_post(post, top_n=100)
            all_keywords.update(keywords)
        
        return dict(all_keywords)
    
    def get_keyword_post_mapping(
        self, 
        posts: List[PostContent],
        top_n: int = 50
    ) -> Dict[str, List[str]]:
        """키워드별 관련 게시글 URL 매핑
        
        Args:
            posts: 게시글 목록
            top_n: 추출할 상위 키워드 수
            
        Returns:
            키워드-게시글URL 리스트 딕셔너리
        """
        if not posts:
            return {}
        
        # 먼저 상위 키워드 추출
        top_keywords = set(self.extract_from_posts(posts, top_n))
        
        # 키워드별 게시글 매핑
        keyword_posts: Dict[str, List[str]] = {kw: [] for kw in top_keywords}
        
        for post in posts:
            post_keywords = set(self.extract_from_post(post, top_n=100))
            
            for keyword in top_keywords:
                if keyword in post_keywords:
                    keyword_posts[keyword].append(post.url)
        
        return keyword_posts
