"""
세븐나이츠 리버스 직접 크롤링 스크립트
인벤 게시판에서 직접 URL을 수집하여 크롤링
"""

import json
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from crawler import CrawlerOrchestrator, CrawlerConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_inven_posts(board_url: str, max_posts: int = 10):
    """인벤 게시판에서 게시글 URL 수집"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    response = requests.get(board_url, headers=headers, timeout=30)
    response.encoding = 'utf-8'
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 게시글 링크 찾기
    links = soup.select('a.subject-link')[:max_posts]
    
    urls = []
    for link in links:
        href = link.get('href', '')
        if href:
            full_url = 'https://www.inven.co.kr' + href if href.startswith('/') else href
            urls.append(full_url)
    
    return urls


def crawl_7knights_direct():
    """세븐나이츠 리버스 직접 크롤링"""
    
    print("="*60)
    print("세븐나이츠 리버스 직접 크롤링")
    print("="*60)
    
    # 인벤 세븐나이츠 리버스 게시판에서 URL 수집
    board_url = 'https://www.inven.co.kr/board/sena/6379'
    print(f"\n게시판 URL: {board_url}")
    print("게시글 URL 수집 중...")
    
    urls = get_inven_posts(board_url, max_posts=5)
    
    if not urls:
        print("게시글을 찾을 수 없습니다.")
        return
    
    print(f"수집된 URL: {len(urls)}개")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")
    
    # 크롤링 설정
    config = CrawlerConfig(
        output_dir='data',
        default_delay=3.0,
        jitter_range=(0.5, 1.5),
        max_comment_pages=3
    )
    
    print("\n크롤링 시작...")
    
    with CrawlerOrchestrator(config) as crawler:
        result = crawler.crawl_urls(
            urls=urls,
            keyword='세븐나이츠 리버스',
            save_results=True,
            output_format='json'
        )
        
        print()
        print("="*60)
        print("크롤링 결과")
        print("="*60)
        print(f"총 URL: {result.total_searched}개")
        print(f"성공: {result.total_crawled}개")
        print(f"실패: {result.total_failed}개")
        print(f"소요시간: {result.duration_seconds:.1f}초")
        
        if result.posts:
            print()
            print("="*60)
            print(f"수집된 게시글 ({len(result.posts)}개)")
            print("="*60)
            
            total_comments = 0
            for i, post in enumerate(result.posts, 1):
                total_comments += len(post.comments)
                print(f"\n{'='*50}")
                print(f"[{i}] {post.title}")
                print(f"{'='*50}")
                print(f"URL: {post.url}")
                print(f"사이트: {post.site}")
                print(f"작성자: {post.author}")
                print(f"작성일: {post.created_at}")
                print(f"조회수: {post.view_count}, 추천수: {post.like_count}")
                print(f"본문 길이: {len(post.body)}자")
                print(f"댓글 수: {len(post.comments)}")
                
                # 본문 미리보기
                print(f"\n[본문 미리보기]")
                body_preview = post.body[:300].replace('\n', '\n  ')
                if len(post.body) > 300:
                    body_preview += "\n  ..."
                print(f"  {body_preview}")
                
                # 댓글 미리보기
                if post.comments:
                    print(f"\n[댓글 ({len(post.comments)}개)]")
                    for j, c in enumerate(post.comments[:5], 1):
                        content = c.content[:60].replace('\n', ' ')
                        if len(c.content) > 60:
                            content += "..."
                        print(f"  {j}. [{c.author}] {content}")
                    if len(post.comments) > 5:
                        print(f"  ... 외 {len(post.comments) - 5}개 댓글")
            
            print()
            print("="*60)
            print(f"총 {len(result.posts)}개 게시글, {total_comments}개 댓글 수집 완료")
            print("="*60)
            
            # 결과 파일 저장
            output_file = 'data/7knights_reverse_crawl.json'
            posts_data = [post.to_dict() for post in result.posts]
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(posts_data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"\n결과 저장: {output_file}")
            print("\n결과 확인 방법:")
            print(f"  1. {output_file} 파일 열기")
            print("  2. python -c \"import json; data=json.load(open('data/7knights_reverse_crawl.json', encoding='utf-8')); print(json.dumps(data[0], ensure_ascii=False, indent=2))\"")
            
            return result.posts
        else:
            print("\n수집된 게시글이 없습니다.")
            return []


if __name__ == "__main__":
    crawl_7knights_direct()
