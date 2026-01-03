"""
Enhanced Search Review - 개선된 게임 리뷰 크롤러

기존 search_review.py의 기능을 유지하면서 새로운 CrawlerOrchestrator를 통합한다.

Requirements: 1.1
- Bedrock 키워드 생성 기능 연동
- 기존 인터페이스 유지하면서 새 기능 적용
"""

import os
import json
import re
import logging
from typing import List, Optional, Dict, Any

import boto3
from dotenv import load_dotenv

from crawler import (
    CrawlerOrchestrator, 
    CrawlerConfig, 
    CrawlResult,
    PostContent
)


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 환경 변수 로드
load_dotenv()


class BedrockKeywordGenerator:
    """Bedrock을 사용한 키워드 생성기
    
    AWS Bedrock의 Nova 모델을 사용하여 게임 리뷰 검색 키워드를 생성한다.
    """
    
    def __init__(
        self, 
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region: str = "us-east-1"
    ):
        """BedrockKeywordGenerator 초기화
        
        Args:
            aws_access_key_id: AWS Access Key ID (없으면 환경변수 사용)
            aws_secret_access_key: AWS Secret Access Key (없으면 환경변수 사용)
            aws_region: AWS 리전
        """
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            raise ValueError(
                "AWS 자격 증명이 필요합니다. "
                "환경 변수(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)를 설정하거나 "
                "생성자에 직접 전달하세요."
            )
        
        self.client = boto3.client(
            service_name='bedrock-runtime',
            region_name=self.aws_region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )
    
    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """텍스트에서 JSON 추출
        
        Args:
            text: 원본 텍스트
            
        Returns:
            추출된 JSON 문자열 또는 None
        """
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)
        return None
    
    def generate_keywords(
        self, 
        game_name: str, 
        num_keywords: int = 5
    ) -> List[str]:
        """게임 리뷰 검색 키워드 생성
        
        Args:
            game_name: 게임 이름
            num_keywords: 생성할 키워드 수
            
        Returns:
            생성된 키워드 목록
            
        Raises:
            ValueError: Bedrock 응답에서 JSON을 찾을 수 없는 경우
        """
        prompt = f"""
        다음 게임 '{game_name}'에 대한 리뷰를 검색하려고 하는데 한국 웹사이트에서 어떤 검색 키워드로 검색하면 잘 나올 지 {num_keywords}개 생성해줘. 반드시 {num_keywords}개를 생성해
        참고로 해당 게임의 은어로 쓰이는 단어도 고려해줘. 리뷰라는 단어 뿐 아니라 후기, 비평 등의 단어도 섞어서 생성해줘 
        결과를 반드시 JSON 형식으로 반환해줘:
        {{
          "keywords": ["키워드1", "키워드2", ...]
        }}
        """
        
        response = self.client.invoke_model(
            modelId='amazon.nova-pro-v1:0',
            body=json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}]
            }),
            contentType='application/json',
            accept='application/json'
        )
        
        result = json.loads(response['body'].read().decode('utf-8'))
        raw_text = result["output"]["message"]["content"][0]["text"]
        
        json_text = self._extract_json_from_text(raw_text)
        if json_text:
            return json.loads(json_text).get("keywords", [])
        
        raise ValueError("Bedrock 응답에서 JSON 데이터를 찾을 수 없음.")


class EnhancedGameReviewCrawler:
    """개선된 게임 리뷰 크롤러
    
    기존 search_review.py의 기능을 유지하면서 새로운 기능을 추가한다.
    
    새로운 기능:
    - 실제 게시글 본문 수집
    - 댓글 데이터 수집
    - 관련성 필터링
    - 사이트별 맞춤 파싱
    - Rate limiting 및 봇 탐지 회피
    """
    
    # 기본 대상 사이트
    DEFAULT_SITES = ["inven.co.kr", "ruliweb.com", "dcinside.com"]
    
    def __init__(
        self, 
        config: Optional[CrawlerConfig] = None,
        keyword_generator: Optional[BedrockKeywordGenerator] = None
    ):
        """EnhancedGameReviewCrawler 초기화
        
        Args:
            config: 크롤러 설정
            keyword_generator: 키워드 생성기 (없으면 필요 시 생성)
        """
        self.config = config or CrawlerConfig()
        self.orchestrator = CrawlerOrchestrator(self.config)
        self._keyword_generator = keyword_generator
    
    @property
    def keyword_generator(self) -> BedrockKeywordGenerator:
        """키워드 생성기 (지연 초기화)"""
        if self._keyword_generator is None:
            self._keyword_generator = BedrockKeywordGenerator()
        return self._keyword_generator
    
    def generate_keywords(
        self, 
        game_name: str, 
        num_keywords: int = 5
    ) -> List[str]:
        """게임 리뷰 검색 키워드 생성
        
        Args:
            game_name: 게임 이름
            num_keywords: 생성할 키워드 수
            
        Returns:
            생성된 키워드 목록
        """
        return self.keyword_generator.generate_keywords(game_name, num_keywords)
    
    def crawl_game_reviews(
        self,
        keywords: List[str],
        sites: Optional[List[str]] = None,
        num_results_per_site: int = 10,
        output_format: str = "json",
        save_results: bool = True
    ) -> CrawlResult:
        """게임 리뷰 크롤링
        
        Requirements: 1.1, 1.2, 2.1
        - 검색 결과 URL에 접속하여 실제 게시글 본문 수집
        - 댓글 데이터 함께 수집
        - 관련성 필터링 적용
        
        Args:
            keywords: 검색 키워드 목록
            sites: 대상 사이트 목록 (없으면 기본 사이트 사용)
            num_results_per_site: 사이트당 최대 결과 수
            output_format: 출력 형식 ("json" 또는 "csv")
            save_results: 결과 저장 여부
            
        Returns:
            CrawlResult: 크롤링 결과
        """
        if sites is None:
            sites = self.DEFAULT_SITES.copy()
        
        logger.info(f"게임 리뷰 크롤링 시작: keywords={keywords}, sites={sites}")
        
        result = self.orchestrator.crawl(
            keywords=keywords,
            sites=sites,
            max_results_per_site=num_results_per_site,
            save_results=save_results,
            output_format=output_format
        )
        
        logger.info(
            f"크롤링 완료: {result.total_crawled}개 게시글, "
            f"{sum(len(p.comments) for p in result.posts)}개 댓글 수집"
        )
        
        return result
    
    def crawl_with_auto_keywords(
        self,
        game_name: str,
        num_keywords: int = 5,
        sites: Optional[List[str]] = None,
        num_results_per_site: int = 10,
        output_format: str = "json"
    ) -> CrawlResult:
        """키워드 자동 생성 후 크롤링
        
        Bedrock을 사용하여 키워드를 자동 생성한 후 크롤링을 수행한다.
        
        Args:
            game_name: 게임 이름
            num_keywords: 생성할 키워드 수
            sites: 대상 사이트 목록
            num_results_per_site: 사이트당 최대 결과 수
            output_format: 출력 형식
            
        Returns:
            CrawlResult: 크롤링 결과
        """
        logger.info(f"'{game_name}' 키워드 자동 생성 중...")
        keywords = self.generate_keywords(game_name, num_keywords)
        logger.info(f"생성된 키워드: {keywords}")
        
        return self.crawl_game_reviews(
            keywords=keywords,
            sites=sites,
            num_results_per_site=num_results_per_site,
            output_format=output_format
        )
    
    def get_posts(self) -> List[PostContent]:
        """수집된 게시글 목록 반환"""
        return self.orchestrator.get_data_store().get_posts()
    
    def export_results(
        self, 
        output_format: str = "json",
        filename: Optional[str] = None
    ) -> str:
        """결과 내보내기
        
        Args:
            output_format: 출력 형식
            filename: 파일명
            
        Returns:
            저장된 파일 경로
        """
        return self.orchestrator.export_results(output_format, filename)
    
    def close(self) -> None:
        """리소스 정리"""
        self.orchestrator.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# 기존 인터페이스 호환 함수들
def generate_keywords(game_name: str = "몬스터헌터") -> List[str]:
    """키워드 생성 (기존 인터페이스 호환)
    
    Args:
        game_name: 게임 이름
        
    Returns:
        생성된 키워드 목록
    """
    generator = BedrockKeywordGenerator()
    return generator.generate_keywords(game_name)


def crawl_game_reviews(
    keywords: List[str],
    num_results_per_query: int = 5,
    additional_sites: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """게임 리뷰 크롤링 (기존 인터페이스 호환)
    
    기존 search_review.py의 crawl_game_reviews 함수와 동일한 인터페이스를 제공한다.
    
    Args:
        keywords: 검색 키워드 목록
        num_results_per_query: 쿼리당 최대 결과 수
        additional_sites: 추가 사이트 목록
        
    Returns:
        리뷰 데이터 목록 (기존 형식)
    """
    default_sites = ["inven.co.kr", "ruliweb.com", "dcinside.com"]
    sites = default_sites + (additional_sites if additional_sites else [])
    sites = list(dict.fromkeys(sites))[:5]  # 중복 제거 및 최대 5개
    
    crawler = EnhancedGameReviewCrawler()
    
    try:
        result = crawler.crawl_game_reviews(
            keywords=keywords,
            sites=sites,
            num_results_per_site=num_results_per_query,
            save_results=True
        )
        
        # 기존 형식으로 변환
        reviews = []
        for post in result.posts:
            review = {
                "url": post.url,
                "date": post.created_at.isoformat() if post.created_at else "날짜 없음",
                "title": post.title,
                "content": post.body,
                "comment": [c.content for c in post.comments] if post.comments else None,
                "source": "enhanced_crawler",
                "keyword": post.keyword,
                "site": post.site,
                # 새로운 필드들
                "author": post.author,
                "view_count": post.view_count,
                "like_count": post.like_count,
                "comment_count": len(post.comments)
            }
            reviews.append(review)
        
        # 결과 저장 (기존 형식)
        output_file = "data/game_reviews_keywords_with_sites.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(reviews, f, ensure_ascii=False, indent=2)
        
        print(f"검색 완료! 결과가 {output_file}에 저장되었습니다.")
        print(f"총 {len(reviews)}개의 리뷰 수집됨.")
        
        return reviews
        
    finally:
        crawler.close()


if __name__ == "__main__":
    try:
        # 키워드 생성
        keywords = generate_keywords("몬스터헌터")[:5]
        print("기본 사이트:", ["inven.co.kr", "ruliweb.com", "dcinside.com"])
        print("생성된 키워드:", keywords)
        
        # 추가 사이트
        additional_sites = ["gamemeca.com"]
        
        # 크롤링 수행
        crawl_game_reviews(
            keywords, 
            num_results_per_query=10, 
            additional_sites=additional_sites
        )
        
    except Exception as e:
        print(f"메인 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
