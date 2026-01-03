"""
빠른 크롤링 테스트 스크립트

특정 URL을 직접 크롤링하여 파서가 제대로 동작하는지 확인한다.
"""

import json
import logging
from crawler import CrawlerOrchestrator, CrawlerConfig
from crawler.content_crawler import ContentCrawler
from crawler.parsers.base import ParserRegistry
from crawler.parsers.inven import InvenParser
from crawler.parsers.ruliweb import RuliwebParser
from crawler.parsers.dcinside import DCInsideParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_single_url(url: str, keyword: str = "테스트"):
    """단일 URL 크롤링 테스트"""
    print(f"\n{'='*60}")
    print(f"URL 크롤링 테스트: {url}")
    print('='*60)
    
    config = CrawlerConfig(
        output_dir="data",
        default_delay=1.0,
        jitter_range=(0.1, 0.5)
    )
    
    crawler = ContentCrawler(config)
    
    try:
        post = crawler.crawl_post(url, keyword)
        
        if post:
            print(f"\n✓ 크롤링 성공!")
            print(f"\n[게시글 정보]")
            print(f"  제목: {post.title}")
            print(f"  URL: {post.url}")
            print(f"  사이트: {post.site}")
            print(f"  작성자: {post.author}")
            print(f"  작성일: {post.created_at}")
            print(f"  조회수: {post.view_count}")
            print(f"  추천수: {post.like_count}")
            print(f"\n[본문 미리보기]")
            body_preview = post.body[:500] + "..." if len(post.body) > 500 else post.body
            print(f"  {body_preview}")
            print(f"\n  (전체 본문 길이: {len(post.body)}자)")
            
            print(f"\n[댓글 정보]")
            print(f"  총 댓글 수: {len(post.comments)}")
            
            if post.comments:
                print(f"\n  댓글 미리보기 (최대 5개):")
                for i, comment in enumerate(post.comments[:5], 1):
                    content_preview = comment.content[:80] + "..." if len(comment.content) > 80 else comment.content
                    print(f"    {i}. [{comment.author}] {content_preview}")
                    if comment.created_at:
                        print(f"       작성일: {comment.created_at}, 추천: {comment.like_count}")
            
            # JSON으로 저장
            output_file = "data/test_crawl_result.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(post.to_dict(), f, ensure_ascii=False, indent=2, default=str)
            print(f"\n결과가 {output_file}에 저장되었습니다.")
            
        else:
            print(f"\n✗ 크롤링 실패: 게시글을 파싱할 수 없습니다.")
            
    except Exception as e:
        print(f"\n✗ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        crawler.close()


def test_parser_directly(url: str, html_content: str = None):
    """파서 직접 테스트 (HTML 내용이 있는 경우)"""
    from urllib.parse import urlparse
    import requests
    
    print(f"\n{'='*60}")
    print(f"파서 직접 테스트: {url}")
    print('='*60)
    
    # 파서 레지스트리 설정
    registry = ParserRegistry()
    registry.register("inven.co.kr", InvenParser())
    registry.register("m.inven.co.kr", InvenParser())
    registry.register("ruliweb.com", RuliwebParser())
    registry.register("dcinside.com", DCInsideParser())
    
    # 파서 선택
    parser = registry.get_parser(url)
    print(f"선택된 파서: {type(parser).__name__}")
    
    # HTML 가져오기
    if html_content is None:
        print("HTML 다운로드 중...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        html_content = response.text
        print(f"HTML 크기: {len(html_content)} bytes")
    
    # 파싱
    print("\n게시글 파싱 중...")
    post = parser.parse_post(html_content, url)
    
    if post:
        print(f"\n✓ 파싱 성공!")
        print(f"  제목: {post.title}")
        print(f"  작성자: {post.author}")
        print(f"  본문 길이: {len(post.body)}자")
    else:
        print(f"\n✗ 파싱 실패")
    
    print("\n댓글 파싱 중...")
    comments = parser.parse_comments(html_content)
    print(f"  파싱된 댓글 수: {len(comments)}")
    
    return post, comments


if __name__ == "__main__":
    print("="*60)
    print("크롤러 빠른 테스트")
    print("="*60)
    
    # 테스트할 URL 입력
    print("\n테스트할 URL을 입력하세요.")
    print("예시:")
    print("  - 인벤: https://www.inven.co.kr/board/mhw/5282/12345")
    print("  - 루리웹: https://bbs.ruliweb.com/game/12345")
    print("  - 디시: https://gall.dcinside.com/board/view/?id=game&no=12345")
    
    url = input("\nURL: ").strip()
    
    if url:
        test_single_url(url)
    else:
        print("\nURL이 입력되지 않았습니다.")
        print("\n기본 테스트로 인벤 메인 페이지 접근을 시도합니다...")
        
        # 간단한 연결 테스트
        import requests
        try:
            response = requests.get(
                "https://www.inven.co.kr",
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=10
            )
            print(f"인벤 접속 테스트: {response.status_code}")
        except Exception as e:
            print(f"접속 실패: {e}")
