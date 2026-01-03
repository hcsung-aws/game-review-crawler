"""
GenericParser - 범용 HTML 파서

Requirements: 4.3
- BeautifulSoup 기반 범용 HTML 파싱
- 제목, 본문, 날짜 추출 로직
- 등록되지 않은 사이트용 기본 파서
"""

import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from crawler.parsers.base import ContentParser
from crawler.models.data_models import PostContent, Comment


class GenericParser(ContentParser):
    """범용 HTML 파서
    
    Requirements: 4.3
    - BeautifulSoup 기반 범용 HTML 파싱
    - 제목, 본문, 날짜 추출
    - 등록되지 않은 사이트용 폴백 파서
    """
    
    # 제목 추출용 선택자 우선순위
    TITLE_SELECTORS = [
        'h1.title', 'h1.post-title', 'h1.entry-title', 'h1.article-title',
        '.title h1', '.post-title', '.entry-title', '.article-title',
        'article h1', '.content h1', 'main h1',
        'h1', 'title'
    ]
    
    # 본문 추출용 선택자 우선순위
    BODY_SELECTORS = [
        'article .content', 'article .body', 'article .post-content',
        '.post-content', '.entry-content', '.article-content', '.article-body',
        '.content-body', '.post-body', '.main-content',
        'article', 'main', '.content', '#content'
    ]
    
    # 날짜 추출용 선택자
    DATE_SELECTORS = [
        'time[datetime]', '.date', '.post-date', '.entry-date',
        '.published', '.created', '.timestamp', '.meta-date'
    ]
    
    # 작성자 추출용 선택자
    AUTHOR_SELECTORS = [
        '.author', '.writer', '.nickname', '.username',
        '.post-author', '.entry-author', '.byline'
    ]
    
    # 댓글 영역 선택자
    COMMENT_SELECTORS = [
        '.comments', '.comment-list', '#comments', '.comment-area',
        '.reply-list', '.comment-wrap'
    ]
    
    # 개별 댓글 선택자
    COMMENT_ITEM_SELECTORS = [
        '.comment', '.comment-item', '.reply', '.reply-item'
    ]
    
    def parse_post(self, html: str, url: str, keyword: str = "") -> PostContent:
        """게시글 파싱
        
        Args:
            html: HTML 문자열
            url: 게시글 URL
            keyword: 검색 키워드
            
        Returns:
            PostContent: 파싱된 게시글 데이터
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # 사이트 도메인 추출
        site = self._extract_site(url)
        
        # 제목 추출
        title = self._extract_title(soup)
        
        # 본문 추출
        body = self._extract_body(soup)
        
        # 작성자 추출
        author = self._extract_author(soup)
        
        # 날짜 추출
        created_at = self._extract_date(soup)
        
        # 조회수, 추천수 추출
        view_count = self._extract_count(soup, ['view', 'hit', '조회'])
        like_count = self._extract_count(soup, ['like', 'recommend', '추천', '좋아요'])
        
        # 댓글 추출
        comments = self.parse_comments(html)
        
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
    
    def parse_comments(self, html: str) -> List[Comment]:
        """댓글 파싱
        
        Args:
            html: HTML 문자열
            
        Returns:
            List[Comment]: 파싱된 댓글 목록
        """
        soup = BeautifulSoup(html, 'lxml')
        comments = []
        
        # 댓글 영역 찾기
        comment_area = None
        for selector in self.COMMENT_SELECTORS:
            comment_area = soup.select_one(selector)
            if comment_area:
                break
        
        if not comment_area:
            return comments
        
        # 개별 댓글 찾기
        comment_items = []
        for selector in self.COMMENT_ITEM_SELECTORS:
            comment_items = comment_area.select(selector)
            if comment_items:
                break
        
        for item in comment_items:
            comment = self._parse_comment_item(item)
            if comment:
                comments.append(comment)
        
        return comments
    
    def get_supported_domains(self) -> List[str]:
        """지원하는 도메인 목록 반환
        
        GenericParser는 모든 도메인을 지원하므로 빈 리스트 반환
        (ParserRegistry에서 폴백으로 사용)
        
        Returns:
            List[str]: 빈 리스트
        """
        return []
    
    def _extract_site(self, url: str) -> str:
        """URL에서 사이트 도메인 추출"""
        parsed = urlparse(url)
        return parsed.netloc or ""
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """제목 추출"""
        for selector in self.TITLE_SELECTORS:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        return ""
    
    def _extract_body(self, soup: BeautifulSoup) -> str:
        """본문 추출"""
        # 스크립트, 스타일 태그 제거
        for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()
        
        for selector in self.BODY_SELECTORS:
            element = soup.select_one(selector)
            if element:
                # 텍스트 추출 및 정리
                text = element.get_text(separator='\n', strip=True)
                if len(text) > 50:  # 최소 길이 체크
                    return self._clean_text(text)
        
        # 폴백: body 전체에서 추출
        body = soup.find('body')
        if body:
            return self._clean_text(body.get_text(separator='\n', strip=True))
        
        return ""
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """작성자 추출"""
        for selector in self.AUTHOR_SELECTORS:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        return None
    
    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """날짜 추출"""
        for selector in self.DATE_SELECTORS:
            element = soup.select_one(selector)
            if element:
                # datetime 속성 확인
                if element.has_attr('datetime'):
                    try:
                        return datetime.fromisoformat(element['datetime'].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        pass
                
                # 텍스트에서 날짜 파싱 시도
                text = element.get_text(strip=True)
                parsed_date = self._parse_date_string(text)
                if parsed_date:
                    return parsed_date
        
        return None
    
    def _parse_date_string(self, text: str) -> Optional[datetime]:
        """날짜 문자열 파싱"""
        # 다양한 날짜 형식 시도
        date_patterns = [
            r'(\d{4})[.-/](\d{1,2})[.-/](\d{1,2})',  # 2024-01-15, 2024.01.15
            r'(\d{1,2})[.-/](\d{1,2})[.-/](\d{4})',  # 01-15-2024
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                try:
                    if len(groups[0]) == 4:  # YYYY-MM-DD
                        return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                    else:  # MM-DD-YYYY
                        return datetime(int(groups[2]), int(groups[0]), int(groups[1]))
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _extract_count(self, soup: BeautifulSoup, keywords: List[str]) -> int:
        """조회수/추천수 등 숫자 추출"""
        for keyword in keywords:
            # 클래스명에 키워드가 포함된 요소 찾기
            elements = soup.find_all(class_=re.compile(keyword, re.I))
            for element in elements:
                text = element.get_text(strip=True)
                numbers = re.findall(r'\d+', text)
                if numbers:
                    return int(numbers[0])
            
            # 텍스트에 키워드가 포함된 요소 찾기
            elements = soup.find_all(string=re.compile(keyword, re.I))
            for element in elements:
                parent = element.parent
                if parent:
                    text = parent.get_text(strip=True)
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        return int(numbers[0])
        
        return 0
    
    def _parse_comment_item(self, item) -> Optional[Comment]:
        """개별 댓글 아이템 파싱"""
        # 작성자 추출
        author = ""
        for selector in ['.author', '.writer', '.nickname', '.name']:
            author_elem = item.select_one(selector)
            if author_elem:
                author = author_elem.get_text(strip=True)
                break
        
        if not author:
            author = "익명"
        
        # 내용 추출
        content = ""
        for selector in ['.content', '.text', '.body', '.comment-text']:
            content_elem = item.select_one(selector)
            if content_elem:
                content = content_elem.get_text(strip=True)
                break
        
        if not content:
            # 전체 텍스트에서 추출
            content = item.get_text(strip=True)
        
        if not content:
            return None
        
        # 날짜 추출
        created_at = None
        for selector in ['.date', '.time', 'time']:
            date_elem = item.select_one(selector)
            if date_elem:
                if date_elem.has_attr('datetime'):
                    try:
                        created_at = datetime.fromisoformat(date_elem['datetime'].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        pass
                else:
                    created_at = self._parse_date_string(date_elem.get_text(strip=True))
                break
        
        # 추천수 추출
        like_count = 0
        for selector in ['.like', '.recommend', '.vote']:
            like_elem = item.select_one(selector)
            if like_elem:
                numbers = re.findall(r'\d+', like_elem.get_text(strip=True))
                if numbers:
                    like_count = int(numbers[0])
                break
        
        return Comment(
            author=author,
            content=content,
            created_at=created_at,
            like_count=like_count
        )
    
    def _clean_text(self, text: str) -> str:
        """텍스트 정리"""
        # 연속된 공백/줄바꿈 정리
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()
