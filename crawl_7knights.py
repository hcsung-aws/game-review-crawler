"""
세븐나이츠 리버스 크롤링 스크립트
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

def crawl_7knights_reverse():
    """세븐나이츠 리버스 관련 게시글 크롤링"""
    
    # 검색 키워드
    keywords = ['세븐나이츠 리버스 후기', '세나리버스 리뷰']
    
    # 대상 사이트
    sites = ['ruliweb.com', 'inven.co.kr', 'dcinside.com']
    
    config = CrawlerConfig(
        output_dir='data',
        default_delay=3.0,
        relevance_threshold=0.2,  # 관련성 임계값 낮춤
        jitter_range=(0.5, 1.5),
        max_comment_pages=3
    )
    
    print("="*60)
    print("세븐나이츠 리버스 크롤링 시작")
    print("="*60)
    print(f"검색 키워드: {keywords}")
    print(f"대상 사이트: {sites}")
    print()
    
    with CrawlerOrchestrator(config) as crawler:
        result = crawler.crawl(
            keywords=keywords,
            sites=sites,
            max_results_per_site=5,
            save_results=True,
            output_format='json'
        )
        
        print()
        print("="*60)
        print("크롤링 결과 요약")
        print("="*60)
        print(f"검색된 URL: {result.total_searched}개")
        print(f"크롤링 성공: {result.total_crawled}개")
        print(f"크롤링 실패: {result.total_failed}개")
        print(f"성공률: {result.success_rate*100:.1f}%")
        print(f"소요시간: {result.duration_seconds:.1f}초")
        
        if result.errors:
            print(f"\n에러 ({len(result.errors)}개):")
            for err in result.errors[:5]:
                print(f"  - {err[:80]}...")
        
        if result.posts:
            print()
            print("="*60)
            print(f"수집된 게시글 ({len(result.posts)}개)")
            print("="*60)
            
            total_comments = 0
            for i, post in enumerate(result.posts, 1):
                total_comments += len(post.comments)
                print(f"\n[{i}] {post.title}")
                print(f"    사이트: {post.site}")
                print(f"    작성자: {post.author}")
                print(f"    작성일: {post.created_at}")
                print(f"    조회수: {post.view_count}, 추천수: {post.like_count}")
                print(f"    본문 길이: {len(post.body)}자")
                print(f"    댓글 수: {len(post.comments)}")
                
                # 본문 미리보기
                body_preview = post.body[:150].replace('\n', ' ')
                if len(post.body) > 150:
                    body_preview += "..."
                print(f"    본문: {body_preview}")
                
                # 댓글 미리보기
                if post.comments:
                    print(f"    댓글 미리보기:")
                    for j, c in enumerate(post.comments[:2], 1):
                        content = c.content[:40].replace('\n', ' ')
                        if len(c.content) > 40:
                            content += "..."
                        print(f"      {j}. [{c.author}] {content}")
            
            print()
            print("="*60)
            print(f"총 {len(result.posts)}개 게시글, {total_comments}개 댓글 수집 완료")
            print("="*60)
            
            # 결과 파일 경로 출력
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/crawl_results_{timestamp}.json"
            print(f"\n결과 파일: {output_file}")
            print("\n결과 확인 방법:")
            print("  1. JSON 파일 직접 열기")
            print("  2. python check_results.py 실행")
            
            return result.posts
        else:
            print("\n수집된 게시글이 없습니다.")
            return []


if __name__ == "__main__":
    crawl_7knights_reverse()
