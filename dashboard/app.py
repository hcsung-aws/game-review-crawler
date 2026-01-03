"""
크롤링 결과 대시보드 - Flask 웹 애플리케이션
"""

import json
import os
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from pathlib import Path

app = Flask(__name__)

# 데이터 디렉토리
DATA_DIR = Path(__file__).parent.parent / 'data'


def load_crawl_data():
    """크롤링 결과 데이터 로드"""
    all_posts = []
    
    # data 디렉토리의 모든 JSON 파일 읽기
    if DATA_DIR.exists():
        for json_file in DATA_DIR.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 리스트인 경우 (게시글 목록)
                    if isinstance(data, list):
                        for post in data:
                            post['_source_file'] = json_file.name
                            all_posts.append(post)
                    # 딕셔너리인 경우 (단일 게시글)
                    elif isinstance(data, dict) and 'url' in data:
                        data['_source_file'] = json_file.name
                        all_posts.append(data)
            except Exception as e:
                print(f"파일 로드 실패: {json_file} - {e}")
    
    return all_posts


def get_statistics(posts):
    """통계 데이터 계산"""
    if not posts:
        return {
            'total_posts': 0,
            'total_comments': 0,
            'total_views': 0,
            'total_likes': 0,
            'sites': {},
            'dates': {}
        }
    
    total_comments = sum(len(p.get('comments', [])) for p in posts)
    total_views = sum(p.get('view_count', 0) for p in posts)
    total_likes = sum(p.get('like_count', 0) for p in posts)
    
    # 사이트별 통계
    sites = {}
    for post in posts:
        site = post.get('site', 'unknown')
        if site not in sites:
            sites[site] = {'count': 0, 'views': 0, 'likes': 0}
        sites[site]['count'] += 1
        sites[site]['views'] += post.get('view_count', 0)
        sites[site]['likes'] += post.get('like_count', 0)
    
    # 날짜별 통계
    dates = {}
    for post in posts:
        created_at = post.get('created_at', '')
        if created_at:
            date_str = created_at[:10] if len(created_at) >= 10 else created_at
            if date_str not in dates:
                dates[date_str] = 0
            dates[date_str] += 1
    
    return {
        'total_posts': len(posts),
        'total_comments': total_comments,
        'total_views': total_views,
        'total_likes': total_likes,
        'sites': sites,
        'dates': dict(sorted(dates.items()))
    }


@app.route('/')
def index():
    """메인 대시보드 페이지"""
    posts = load_crawl_data()
    stats = get_statistics(posts)
    
    # 최근 게시글 정렬
    posts_sorted = sorted(
        posts, 
        key=lambda x: x.get('created_at', '') or '', 
        reverse=True
    )
    
    return render_template('index.html', posts=posts_sorted, stats=stats)


@app.route('/api/posts')
def api_posts():
    """게시글 API"""
    posts = load_crawl_data()
    return jsonify(posts)


@app.route('/api/stats')
def api_stats():
    """통계 API"""
    posts = load_crawl_data()
    stats = get_statistics(posts)
    return jsonify(stats)


@app.route('/post/<path:url>')
def post_detail(url):
    """게시글 상세 페이지"""
    posts = load_crawl_data()
    
    # URL로 게시글 찾기
    post = None
    for p in posts:
        if p.get('url') == url:
            post = p
            break
    
    if not post:
        return "게시글을 찾을 수 없습니다.", 404
    
    return render_template('post_detail.html', post=post)


if __name__ == '__main__':
    print("="*50)
    print("크롤링 결과 대시보드")
    print("="*50)
    print(f"데이터 디렉토리: {DATA_DIR}")
    print("브라우저에서 http://localhost:5000 접속")
    print("="*50)
    app.run(debug=True, port=5000)
