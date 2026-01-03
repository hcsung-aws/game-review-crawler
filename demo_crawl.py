"""
크롤러 데모 스크립트

실제 크롤링을 테스트하기 위한 간단한 스크립트.
AWS Bedrock 없이도 직접 키워드를 지정하여 테스트할 수 있다.
"""

import json
import logging
from datetime import datetime

from crawler import CrawlerOrchestrator, CrawlerConfig

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def demo_crawl_urls():
    """URL 직접 크롤링 데모
    
    특정 URL을 직접 크롤링하여 결과를 확인한다.
    """
    print("\n" + "="*60)
    print("URL 직접 크롤링 데모")
    print("="*60)
    
    # 테스트할 URL 목록 (실제 게시글 URL로 교체 필요)
    test_urls = [
        # 인벤 예시 (실제 URL로 교체)
        # "https://www.inven.co.kr/board/mhw/5282/12345",
        # 루리웹 예시
        # "https://bbs.ruliweb.com/game/12345",
        # 디시인사이드 예시
        # "https://gall.dcinside.com/board/view/?id=game&no=12345",
    ]
    
    if not test_urls:
        print("\n테스트할 URL이 없습니다.")
        print("test_urls 리스트에 크롤링할 URL을 추가하세요.")
        return
    
    config = CrawlerConfig(
        output_dir="data",
        default_delay=3.0,
        jitter_range=(0.5, 1.5)
    )
    
    with CrawlerOrchestrator(config) as crawler:
        result = crawler.crawl_urls(
            urls=test_urls,
            keyword="게임 리뷰",
            save_results=True,
            output_format="json"
        )
        
        print(f"\n크롤링 결과:")
        print(f"  - 총 URL: {result.total_searched}")
        print(f"  - 성공: {result.total_crawled}")
        print(f"  - 실패: {result.total_failed}")
        print(f"  - 소요시간: {result.duration_seconds:.1f}초")
        
        if result.posts:
            print(f"\n수집된 게시글:")
            for i, post in enumerate(result.posts, 1):
                print(f"\n  [{i}] {post.title}")
                print(f"      URL: {post.url}")
                print(f"      작성자: {post.author}")
                print(f"      작성일: {post.created_at}")
                print(f"      조회수: {post.view_count}, 추천수: {post.like_count}")
                print(f"      본문 길이: {len(post.body)}자")
                print(f"      댓글 수: {len(post.comments)}")
                
                if post.comments:
                    print(f"      댓글 미리보기:")
                    for j, comment in enumerate(post.comments[:3], 1):
                        content_preview = comment.content[:50] + "..." if len(comment.content) > 50 else comment.content
                        print(f"        {j}. [{comment.author}] {content_preview}")


def demo_search_and_crawl():
    """검색 후 크롤링 데모
    
    키워드로 검색한 후 결과를 크롤링한다.
    """
    print("\n" + "="*60)
    print("검색 + 크롤링 데모")
    print("="*60)
    
    # 검색 키워드
    keywords = ["몬스터헌터 와일즈 리뷰"]
    
    # 대상 사이트
    sites = ["inven.co.kr", "ruliweb.com"]
    
    config = CrawlerConfig(
        output_dir="data",
        default_delay=3.0,
        relevance_threshold=0.3,  # 관련성 임계값
        jitter_range=(0.5, 1.5)
    )
    
    with CrawlerOrchestrator(config) as crawler:
        print(f"\n검색 키워드: {keywords}")
        print(f"대상 사이트: {sites}")
        
        result = crawler.crawl(
            keywords=keywords,
            sites=sites,
            max_results_per_site=5,
            save_results=True,
            output_format="json"
        )
        
        print(f"\n크롤링 결과:")
        print(f"  - 검색된 URL: {result.total_searched}")
        print(f"  - 크롤링 성공: {result.total_crawled}")
        print(f"  - 크롤링 실패: {result.total_failed}")
        print(f"  - 성공률: {result.success_rate*100:.1f}%")
        print(f"  - 소요시간: {result.duration_seconds:.1f}초")
        
        if result.errors:
            print(f"\n에러 목록:")
            for error in result.errors[:5]:
                print(f"  - {error}")
        
        if result.posts:
            print(f"\n수집된 게시글 ({len(result.posts)}개):")
            for i, post in enumerate(result.posts[:5], 1):
                print(f"\n  [{i}] {post.title}")
                print(f"      사이트: {post.site}")
                print(f"      작성일: {post.created_at}")
                print(f"      댓글 수: {len(post.comments)}")


def demo_search_only():
    """검색만 수행 (크롤링 없이)
    
    검색 결과만 확인하고 싶을 때 사용한다.
    """
    print("\n" + "="*60)
    print("검색만 수행 데모 (크롤링 없이)")
    print("="*60)
    
    keywords = ["몬스터헌터 와일즈 후기"]
    sites = ["inven.co.kr"]
    
    config = CrawlerConfig(
        relevance_threshold=0.3
    )
    
    with CrawlerOrchestrator(config) as crawler:
        print(f"\n검색 키워드: {keywords}")
        print(f"대상 사이트: {sites}")
        
        results = crawler.search_only(
            keywords=keywords,
            sites=sites,
            max_results_per_site=10
        )
        
        print(f"\n검색 결과 ({len(results)}개):")
        for i, result in enumerate(results, 1):
            print(f"\n  [{i}] {result.title}")
            print(f"      URL: {result.url}")
            print(f"      관련성 점수: {result.relevance_score:.2f}")
            snippet_preview = result.snippet[:100] + "..." if len(result.snippet) > 100 else result.snippet
            print(f"      스니펫: {snippet_preview}")


def main():
    """메인 함수"""
    print("="*60)
    print("커뮤니티 크롤러 데모")
    print("="*60)
    
    print("\n사용 가능한 데모:")
    print("  1. URL 직접 크롤링")
    print("  2. 검색 + 크롤링")
    print("  3. 검색만 수행")
    print("  4. 모두 실행")
    
    choice = input("\n선택 (1-4): ").strip()
    
    if choice == "1":
        demo_crawl_urls()
    elif choice == "2":
        demo_search_and_crawl()
    elif choice == "3":
        demo_search_only()
    elif choice == "4":
        demo_search_only()
        demo_search_and_crawl()
        demo_crawl_urls()
    else:
        print("잘못된 선택입니다.")


if __name__ == "__main__":
    main()
