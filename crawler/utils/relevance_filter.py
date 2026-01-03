"""
RelevanceFilter - 검색 결과 관련성 필터링

Requirements: 3.1, 3.2, 3.3
- 키워드 출현 빈도 및 위치 기반 점수 계산
- threshold 기반 필터링
- 관련성 점수는 0.0 ~ 1.0 범위
"""

from typing import List
import re
from crawler.models.data_models import SearchResult


class RelevanceFilter:
    """검색 결과의 관련성을 평가하고 필터링하는 클래스
    
    Requirements: 3.1, 3.2, 3.3
    - calculate_score(): 키워드 출현 빈도 및 위치 기반 점수 계산
    - filter(): threshold 기반 필터링
    """
    
    # 제목에서 키워드가 발견될 때 가중치
    TITLE_WEIGHT = 0.6
    # 본문(snippet)에서 키워드가 발견될 때 가중치
    BODY_WEIGHT = 0.4
    # 키워드 빈도에 따른 최대 보너스
    FREQUENCY_BONUS_MAX = 0.3
    
    def calculate_score(self, content: str, keywords: List[str], title: str = "") -> float:
        """키워드 기반 관련성 점수 계산 (0.0 ~ 1.0)
        
        Args:
            content: 검색 결과의 본문 또는 snippet
            keywords: 검색 키워드 목록
            title: 검색 결과의 제목 (선택)
            
        Returns:
            0.0 ~ 1.0 범위의 관련성 점수
            
        Requirements: 3.1, 3.3
        - 제목과 본문에서 키워드 출현 빈도와 위치를 고려
        """
        if not keywords:
            return 0.0
        
        # 빈 키워드 제거
        keywords = [k.strip().lower() for k in keywords if k.strip()]
        if not keywords:
            return 0.0
        
        content_lower = content.lower() if content else ""
        title_lower = title.lower() if title else ""
        
        title_score = 0.0
        body_score = 0.0
        total_frequency = 0
        
        for keyword in keywords:
            # 제목에서 키워드 검색
            if keyword in title_lower:
                title_score += 1.0
            
            # 본문에서 키워드 검색
            if keyword in content_lower:
                body_score += 1.0
            
            # 키워드 빈도 계산 (제목 + 본문)
            title_count = len(re.findall(re.escape(keyword), title_lower))
            body_count = len(re.findall(re.escape(keyword), content_lower))
            total_frequency += title_count + body_count
        
        # 키워드 매칭 비율 계산
        keyword_count = len(keywords)
        title_match_ratio = title_score / keyword_count if keyword_count > 0 else 0.0
        body_match_ratio = body_score / keyword_count if keyword_count > 0 else 0.0
        
        # 기본 점수: 제목과 본문 가중치 적용
        base_score = (title_match_ratio * self.TITLE_WEIGHT) + (body_match_ratio * self.BODY_WEIGHT)
        
        # 빈도 보너스: 키워드가 많이 등장할수록 보너스 (최대 0.3)
        # log 스케일로 빈도 보너스 계산 (1회 이상일 때만)
        if total_frequency > 0:
            # 빈도가 높을수록 보너스 증가, 최대 FREQUENCY_BONUS_MAX
            frequency_bonus = min(self.FREQUENCY_BONUS_MAX, 
                                  self.FREQUENCY_BONUS_MAX * (1 - 1 / (1 + total_frequency * 0.1)))
        else:
            frequency_bonus = 0.0
        
        # 최종 점수 계산 (0.0 ~ 1.0 범위로 클램핑)
        final_score = min(1.0, max(0.0, base_score + frequency_bonus))
        
        return final_score
    
    def calculate_score_for_result(self, result: SearchResult, keywords: List[str]) -> float:
        """SearchResult 객체에 대한 관련성 점수 계산
        
        Args:
            result: SearchResult 객체
            keywords: 검색 키워드 목록
            
        Returns:
            0.0 ~ 1.0 범위의 관련성 점수
        """
        return self.calculate_score(result.snippet, keywords, result.title)
    
    def filter(self, results: List[SearchResult], keywords: List[str], 
               threshold: float = 0.5) -> List[SearchResult]:
        """threshold 이상의 관련성 점수를 가진 결과만 필터링
        
        Args:
            results: SearchResult 목록
            keywords: 검색 키워드 목록
            threshold: 최소 관련성 점수 (기본값 0.5)
            
        Returns:
            threshold 이상의 점수를 가진 SearchResult 목록
            
        Requirements: 3.2
        - Relevance_Score가 threshold 미만인 결과는 제외
        """
        filtered_results = []
        
        for result in results:
            score = self.calculate_score_for_result(result, keywords)
            # 점수 업데이트
            result.relevance_score = score
            
            if score >= threshold:
                filtered_results.append(result)
        
        return filtered_results
