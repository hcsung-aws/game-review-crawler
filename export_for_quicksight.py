"""
QuickSight용 데이터 내보내기 스크립트

크롤링 결과를 QuickSight에서 사용할 수 있는 형식으로 변환한다.
- CSV 파일로 내보내기 (S3 업로드용)
- 게시글과 댓글을 별도 테이블로 분리
"""

import json
import csv
import os
from pathlib import Path
from datetime import datetime

DATA_DIR = Path('data')
OUTPUT_DIR = Path('quicksight_data')


def load_all_posts():
    """모든 크롤링 결과 로드"""
    all_posts = []
    
    for json_file in DATA_DIR.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if isinstance(data, list):
                    all_posts.extend(data)
                elif isinstance(data, dict) and 'url' in data:
                    all_posts.append(data)
        except Exception as e:
            print(f"파일 로드 실패: {json_file} - {e}")
    
    return all_posts


def export_posts_csv(posts, filename='posts.csv'):
    """게시글 데이터를 CSV로 내보내기"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    filepath = OUTPUT_DIR / filename
    
    fieldnames = [
        'post_id', 'url', 'title', 'site', 'author', 
        'created_at', 'view_count', 'like_count', 
        'body_length', 'comment_count', 'keyword'
    ]
    
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, post in enumerate(posts, 1):
            row = {
                'post_id': i,
                'url': post.get('url', ''),
                'title': post.get('title', ''),
                'site': post.get('site', ''),
                'author': post.get('author', ''),
                'created_at': post.get('created_at', '')[:10] if post.get('created_at') else '',
                'view_count': post.get('view_count', 0),
                'like_count': post.get('like_count', 0),
                'body_length': len(post.get('body', '')),
                'comment_count': len(post.get('comments', [])),
                'keyword': post.get('keyword', '')
            }
            writer.writerow(row)
    
    print(f"게시글 CSV 저장: {filepath} ({len(posts)}개)")
    return filepath


def export_comments_csv(posts, filename='comments.csv'):
    """댓글 데이터를 CSV로 내보내기"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    filepath = OUTPUT_DIR / filename
    
    fieldnames = [
        'comment_id', 'post_id', 'post_url', 'author',
        'content', 'created_at', 'like_count'
    ]
    
    comment_id = 0
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for post_id, post in enumerate(posts, 1):
            for comment in post.get('comments', []):
                comment_id += 1
                row = {
                    'comment_id': comment_id,
                    'post_id': post_id,
                    'post_url': post.get('url', ''),
                    'author': comment.get('author', ''),
                    'content': comment.get('content', '')[:500],  # 길이 제한
                    'created_at': comment.get('created_at', '')[:10] if comment.get('created_at') else '',
                    'like_count': comment.get('like_count', 0)
                }
                writer.writerow(row)
    
    print(f"댓글 CSV 저장: {filepath} ({comment_id}개)")
    return filepath


def export_summary_csv(posts, filename='summary.csv'):
    """요약 통계 CSV 내보내기"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    filepath = OUTPUT_DIR / filename
    
    # 사이트별 통계
    site_stats = {}
    for post in posts:
        site = post.get('site', 'unknown')
        if site not in site_stats:
            site_stats[site] = {
                'post_count': 0,
                'total_views': 0,
                'total_likes': 0,
                'total_comments': 0
            }
        site_stats[site]['post_count'] += 1
        site_stats[site]['total_views'] += post.get('view_count', 0)
        site_stats[site]['total_likes'] += post.get('like_count', 0)
        site_stats[site]['total_comments'] += len(post.get('comments', []))
    
    fieldnames = ['site', 'post_count', 'total_views', 'total_likes', 'total_comments']
    
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for site, stats in site_stats.items():
            row = {'site': site, **stats}
            writer.writerow(row)
    
    print(f"요약 CSV 저장: {filepath}")
    return filepath


def upload_to_s3(bucket_name, prefix='crawl_data'):
    """S3에 업로드 (boto3 필요)"""
    try:
        import boto3
        
        s3 = boto3.client('s3')
        
        for csv_file in OUTPUT_DIR.glob('*.csv'):
            key = f"{prefix}/{csv_file.name}"
            s3.upload_file(str(csv_file), bucket_name, key)
            print(f"S3 업로드 완료: s3://{bucket_name}/{key}")
        
        return True
    except ImportError:
        print("boto3가 설치되지 않았습니다. pip install boto3")
        return False
    except Exception as e:
        print(f"S3 업로드 실패: {e}")
        return False


def main():
    print("="*60)
    print("QuickSight용 데이터 내보내기")
    print("="*60)
    
    # 데이터 로드
    posts = load_all_posts()
    print(f"\n총 {len(posts)}개 게시글 로드됨")
    
    if not posts:
        print("내보낼 데이터가 없습니다.")
        return
    
    # CSV 내보내기
    print("\nCSV 파일 생성 중...")
    export_posts_csv(posts)
    export_comments_csv(posts)
    export_summary_csv(posts)
    
    print("\n" + "="*60)
    print("QuickSight 연동 방법")
    print("="*60)
    print("""
1. S3에 업로드:
   - quicksight_data/ 폴더의 CSV 파일들을 S3 버킷에 업로드
   - 또는 이 스크립트에서 upload_to_s3('your-bucket-name') 호출

2. QuickSight에서 데이터셋 생성:
   - QuickSight 콘솔 → 데이터셋 → 새 데이터셋
   - S3 선택 → 매니페스트 파일 또는 직접 S3 경로 지정
   - posts.csv, comments.csv 각각 데이터셋으로 추가

3. 분석 생성:
   - 새 분석 → 데이터셋 선택
   - 시각화 추가:
     * 사이트별 게시글 수 (파이 차트)
     * 날짜별 게시글 추이 (라인 차트)
     * 조회수/추천수 분포 (히스토그램)
     * 게시글 목록 (테이블)

4. 대시보드 게시:
   - 분석 → 대시보드 게시
   - 공유 설정
""")
    
    print(f"\n생성된 파일:")
    for f in OUTPUT_DIR.glob('*.csv'):
        print(f"  - {f}")


if __name__ == "__main__":
    main()
