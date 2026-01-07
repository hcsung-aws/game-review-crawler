"""
크롤링 결과 대시보드 - Flask 웹 애플리케이션

Requirements: 1.2, 2.3, 5.1, 5.2
- 게임 선택 인터페이스 제공
- 게임별 요약 카드 표시
- 감성 분석 결과 표시
"""

import json
import os
import sys
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from pathlib import Path
from collections import defaultdict

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawler.analysis.sentiment import SentimentAnalyzer
from crawler.analysis.issue_detector import IssueDetector
from crawler.models.data_models import PostContent, Comment
from crawler.models.analysis_models import SentimentResult, SentimentLabel

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


def extract_games_from_posts(posts):
    """게시글에서 게임 목록 추출
    
    Requirements: 1.2
    - 게임 선택 인터페이스 제공을 위한 게임 목록 추출
    
    Args:
        posts: 게시글 목록
        
    Returns:
        게임별 정보 딕셔너리 {game_keyword: {name, post_count, latest_date, total_views, total_comments}}
    """
    games = defaultdict(lambda: {
        'name': '',
        'post_count': 0,
        'latest_date': None,
        'total_views': 0,
        'total_comments': 0,
        'sites': set()
    })
    
    for post in posts:
        keyword = post.get('keyword', '')
        if not keyword:
            continue
        
        # 게임 정보 업데이트
        game = games[keyword]
        if not game['name']:
            game['name'] = keyword
        
        game['post_count'] += 1
        game['total_views'] += post.get('view_count', 0) or 0
        game['total_comments'] += len(post.get('comments', []))
        
        # 사이트 추가
        site = post.get('site', '')
        if site:
            game['sites'].add(site)
        
        # 최신 날짜 업데이트
        created_at = post.get('created_at', '')
        if created_at:
            if game['latest_date'] is None or created_at > game['latest_date']:
                game['latest_date'] = created_at
    
    # set을 list로 변환
    for game_id, game in games.items():
        game['sites'] = list(game['sites'])
        game['game_id'] = game_id.lower().replace(' ', '-')
    
    return dict(games)


def get_game_summary_list(posts):
    """게임별 요약 목록 생성
    
    Requirements: 5.1
    - 게임별 요약 카드 표시 (게임명, 총 게시글 수, 최근 업데이트)
    
    Args:
        posts: 게시글 목록
        
    Returns:
        게임 요약 목록 [{game_id, name, post_count, latest_date, total_views, total_comments, sites}]
    """
    games = extract_games_from_posts(posts)
    
    result = []
    for keyword, game in games.items():
        result.append({
            'game_id': game['game_id'],
            'keyword': keyword,
            'name': game['name'],
            'post_count': game['post_count'],
            'latest_date': game['latest_date'][:10] if game['latest_date'] else None,
            'total_views': game['total_views'],
            'total_comments': game['total_comments'],
            'sites': game['sites']
        })
    
    # 게시글 수 기준 내림차순 정렬
    result.sort(key=lambda x: x['post_count'], reverse=True)
    
    return result


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
    """메인 대시보드 페이지 - 게임 선택 인터페이스
    
    Requirements: 1.2, 5.1
    - 게임 선택 인터페이스 제공
    - 게임별 요약 카드 표시
    """
    posts = load_crawl_data()
    stats = get_statistics(posts)
    games = get_game_summary_list(posts)
    
    # 최근 게시글 정렬
    posts_sorted = sorted(
        posts, 
        key=lambda x: x.get('created_at', '') or '', 
        reverse=True
    )
    
    return render_template('index.html', posts=posts_sorted, stats=stats, games=games)


@app.route('/api/games')
def api_games():
    """게임 목록 API
    
    Requirements: 1.2
    - 게임 선택 인터페이스를 위한 게임 목록 조회
    
    Returns:
        JSON: 게임 목록 [{game_id, keyword, name, post_count, latest_date, total_views, total_comments, sites}]
    """
    posts = load_crawl_data()
    games = get_game_summary_list(posts)
    return jsonify(games)


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


def filter_posts_by_game(posts, game_id):
    """게임 ID로 게시글 필터링
    
    Requirements: 1.3
    - 특정 게임을 선택하면 해당 게임의 데이터만 필터링하여 표시
    
    Args:
        posts: 전체 게시글 목록
        game_id: 게임 ID (kebab-case)
        
    Returns:
        필터링된 게시글 목록
    """
    result = []
    for post in posts:
        keyword = post.get('keyword', '')
        if keyword:
            # keyword를 kebab-case로 변환하여 비교
            post_game_id = keyword.lower().replace(' ', '-')
            if post_game_id == game_id.lower():
                result.append(post)
    return result


def filter_posts_by_date_range(posts, start_date=None, end_date=None):
    """기간별 게시글 필터링
    
    Requirements: 4.3, 5.5
    - 특정 기간을 선택하면 해당 기간의 데이터만 필터링
    
    Args:
        posts: 게시글 목록
        start_date: 시작일 (YYYY-MM-DD 형식 문자열)
        end_date: 종료일 (YYYY-MM-DD 형식 문자열)
        
    Returns:
        필터링된 게시글 목록
    """
    if not start_date and not end_date:
        return posts
    
    result = []
    for post in posts:
        created_at = post.get('created_at', '')
        if not created_at:
            continue
        
        post_date = created_at[:10]  # YYYY-MM-DD 부분만 추출
        
        if start_date and post_date < start_date:
            continue
        if end_date and post_date > end_date:
            continue
        
        result.append(post)
    
    return result


def filter_posts_by_site(posts, sites):
    """사이트별 게시글 필터링
    
    Requirements: 5.5
    - 특정 사이트의 게시글만 필터링
    
    Args:
        posts: 게시글 목록
        sites: 사이트 목록 (리스트)
        
    Returns:
        필터링된 게시글 목록
    """
    if not sites:
        return posts
    
    sites_lower = [s.lower() for s in sites]
    result = []
    for post in posts:
        site = post.get('site', '').lower()
        if site in sites_lower:
            result.append(post)
    
    return result


def get_game_info(posts, game_id):
    """게임 정보 조회
    
    Args:
        posts: 전체 게시글 목록
        game_id: 게임 ID
        
    Returns:
        게임 정보 딕셔너리 또는 None
    """
    games = extract_games_from_posts(posts)
    for keyword, game in games.items():
        if game['game_id'] == game_id:
            return {
                'game_id': game_id,
                'keyword': keyword,
                'name': game['name'],
                'post_count': game['post_count'],
                'total_views': game['total_views'],
                'total_comments': game['total_comments'],
                'sites': game['sites'],
                'latest_date': game['latest_date']
            }
    return None


def get_available_sites(posts):
    """게시글에서 사용 가능한 사이트 목록 추출
    
    Args:
        posts: 게시글 목록
        
    Returns:
        사이트 목록
    """
    sites = set()
    for post in posts:
        site = post.get('site', '')
        if site:
            sites.add(site)
    return sorted(list(sites))


@app.route('/game/<game_id>')
def game_dashboard(game_id):
    """게임별 상세 대시보드 페이지
    
    Requirements: 1.3, 5.2
    - 게임별 게시글 목록 표시
    - 기본 필터 UI (기간, 사이트)
    
    Args:
        game_id: 게임 ID (kebab-case)
    """
    posts = load_crawl_data()
    
    # 게임 정보 조회
    game_info = get_game_info(posts, game_id)
    if not game_info:
        return "게임을 찾을 수 없습니다.", 404
    
    # 게임별 게시글 필터링
    game_posts = filter_posts_by_game(posts, game_id)
    
    # 쿼리 파라미터에서 필터 조건 추출
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    site_filter = request.args.getlist('site')
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    # 필터 적용
    filtered_posts = game_posts
    if start_date or end_date:
        filtered_posts = filter_posts_by_date_range(filtered_posts, start_date, end_date)
    if site_filter:
        filtered_posts = filter_posts_by_site(filtered_posts, site_filter)
    
    # 정렬
    if sort_by == 'view_count':
        filtered_posts = sorted(filtered_posts, key=lambda x: x.get('view_count', 0) or 0, reverse=(sort_order == 'desc'))
    elif sort_by == 'comment_count':
        filtered_posts = sorted(filtered_posts, key=lambda x: len(x.get('comments', [])), reverse=(sort_order == 'desc'))
    else:  # created_at
        filtered_posts = sorted(filtered_posts, key=lambda x: x.get('created_at', '') or '', reverse=(sort_order == 'desc'))
    
    # 사용 가능한 사이트 목록
    available_sites = get_available_sites(game_posts)
    
    # 통계 계산
    stats = {
        'total_posts': len(filtered_posts),
        'total_views': sum(p.get('view_count', 0) or 0 for p in filtered_posts),
        'total_comments': sum(len(p.get('comments', [])) for p in filtered_posts)
    }
    
    return render_template(
        'game_dashboard.html',
        game=game_info,
        posts=filtered_posts,
        stats=stats,
        available_sites=available_sites,
        filters={
            'start_date': start_date,
            'end_date': end_date,
            'sites': site_filter,
            'sort_by': sort_by,
            'sort_order': sort_order
        }
    )


@app.route('/api/game/<game_id>/posts')
def api_game_posts(game_id):
    """게임별 게시글 목록 API
    
    Requirements: 1.3, 5.2
    - 게임별 게시글 목록 조회
    - 기간, 사이트 필터링 지원
    
    Args:
        game_id: 게임 ID (kebab-case)
        
    Query Parameters:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        site: 사이트 필터 (복수 가능)
        sort: 정렬 필드 (created_at, view_count, comment_count)
        order: 정렬 순서 (asc, desc)
        limit: 결과 제한 수
        offset: 시작 위치
        
    Returns:
        JSON: {posts: [...], total: n, game: {...}}
    """
    posts = load_crawl_data()
    
    # 게임 정보 조회
    game_info = get_game_info(posts, game_id)
    if not game_info:
        return jsonify({'error': 'Game not found'}), 404
    
    # 게임별 게시글 필터링
    game_posts = filter_posts_by_game(posts, game_id)
    
    # 쿼리 파라미터에서 필터 조건 추출
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    site_filter = request.args.getlist('site')
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # 필터 적용
    filtered_posts = game_posts
    if start_date or end_date:
        filtered_posts = filter_posts_by_date_range(filtered_posts, start_date, end_date)
    if site_filter:
        filtered_posts = filter_posts_by_site(filtered_posts, site_filter)
    
    # 정렬
    if sort_by == 'view_count':
        filtered_posts = sorted(filtered_posts, key=lambda x: x.get('view_count', 0) or 0, reverse=(sort_order == 'desc'))
    elif sort_by == 'comment_count':
        filtered_posts = sorted(filtered_posts, key=lambda x: len(x.get('comments', [])), reverse=(sort_order == 'desc'))
    else:  # created_at
        filtered_posts = sorted(filtered_posts, key=lambda x: x.get('created_at', '') or '', reverse=(sort_order == 'desc'))
    
    total = len(filtered_posts)
    
    # 페이지네이션
    if limit:
        filtered_posts = filtered_posts[offset:offset + limit]
    elif offset:
        filtered_posts = filtered_posts[offset:]
    
    # 응답 데이터 구성
    response_posts = []
    for post in filtered_posts:
        response_posts.append({
            'url': post.get('url', ''),
            'title': post.get('title', ''),
            'author': post.get('author', ''),
            'created_at': post.get('created_at', ''),
            'view_count': post.get('view_count', 0),
            'like_count': post.get('like_count', 0),
            'comment_count': len(post.get('comments', [])),
            'site': post.get('site', ''),
            'keyword': post.get('keyword', '')
        })
    
    return jsonify({
        'posts': response_posts,
        'total': total,
        'game': game_info,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'sites': site_filter,
            'sort_by': sort_by,
            'sort_order': sort_order
        }
    })


# 감성 분석기 인스턴스 (싱글톤)
_sentiment_analyzer = None

def get_sentiment_analyzer():
    """감성 분석기 인스턴스 반환 (싱글톤 패턴)"""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    return _sentiment_analyzer


def convert_post_dict_to_postcontent(post_dict: dict) -> PostContent:
    """딕셔너리 형태의 게시글을 PostContent 객체로 변환
    
    Args:
        post_dict: 게시글 딕셔너리
        
    Returns:
        PostContent 객체
    """
    # 날짜 파싱
    created_at = None
    if post_dict.get('created_at'):
        try:
            created_at = datetime.fromisoformat(post_dict['created_at'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
    
    # 댓글 변환
    comments = []
    for c in post_dict.get('comments', []):
        comment_created_at = None
        if c.get('created_at'):
            try:
                comment_created_at = datetime.fromisoformat(c['created_at'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        comments.append(Comment(
            author=c.get('author', ''),
            content=c.get('content', ''),
            created_at=comment_created_at,
            like_count=c.get('like_count', 0)
        ))
    
    return PostContent(
        url=post_dict.get('url', ''),
        title=post_dict.get('title', ''),
        body=post_dict.get('body', ''),
        site=post_dict.get('site', ''),
        keyword=post_dict.get('keyword', ''),
        author=post_dict.get('author'),
        created_at=created_at,
        view_count=post_dict.get('view_count', 0) or 0,
        like_count=post_dict.get('like_count', 0) or 0,
        comments=comments
    )


@app.route('/api/game/<game_id>/sentiment')
def api_game_sentiment(game_id):
    """게임별 감성 분석 API
    
    Requirements: 2.3
    - 감성 분포, 평균 점수, 부정적 게시글 목록 반환
    
    Args:
        game_id: 게임 ID (kebab-case)
        
    Query Parameters:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        site: 사이트 필터 (복수 가능)
        negative_threshold: 부정 판단 임계값 (기본값: -0.3)
        limit: 부정적 게시글 최대 개수 (기본값: 20)
        
    Returns:
        JSON: {
            game: {...},
            sentiment_distribution: {positive: n, negative: n, neutral: n},
            sentiment_avg: float,
            total_analyzed: int,
            negative_posts: [{url, title, score, label, ...}, ...]
        }
    """
    posts = load_crawl_data()
    
    # 게임 정보 조회
    game_info = get_game_info(posts, game_id)
    if not game_info:
        return jsonify({'error': 'Game not found'}), 404
    
    # 게임별 게시글 필터링
    game_posts = filter_posts_by_game(posts, game_id)
    
    # 쿼리 파라미터에서 필터 조건 추출
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    site_filter = request.args.getlist('site')
    negative_threshold = request.args.get('negative_threshold', -0.3, type=float)
    limit = request.args.get('limit', 20, type=int)
    
    # 필터 적용
    filtered_posts = game_posts
    if start_date or end_date:
        filtered_posts = filter_posts_by_date_range(filtered_posts, start_date, end_date)
    if site_filter:
        filtered_posts = filter_posts_by_site(filtered_posts, site_filter)
    
    # 감성 분석 수행
    analyzer = get_sentiment_analyzer()
    
    sentiment_distribution = {
        'positive': 0,
        'negative': 0,
        'neutral': 0
    }
    total_score = 0.0
    negative_posts = []
    posts_with_sentiment = []
    
    for post_dict in filtered_posts:
        # 딕셔너리를 PostContent로 변환
        post_content = convert_post_dict_to_postcontent(post_dict)
        
        # 감성 분석
        result = analyzer.analyze_post(post_content)
        
        # 분포 업데이트
        sentiment_distribution[result.label.value] += 1
        total_score += result.score
        
        # 게시글과 감성 결과 저장
        posts_with_sentiment.append({
            'post': post_dict,
            'sentiment': result
        })
        
        # 부정적 게시글 수집
        if result.score < negative_threshold:
            negative_posts.append({
                'url': post_dict.get('url', ''),
                'title': post_dict.get('title', ''),
                'author': post_dict.get('author', ''),
                'created_at': post_dict.get('created_at', ''),
                'view_count': post_dict.get('view_count', 0),
                'comment_count': len(post_dict.get('comments', [])),
                'site': post_dict.get('site', ''),
                'sentiment_score': round(result.score, 3),
                'sentiment_label': result.label.value,
                'confidence': round(result.confidence, 3)
            })
    
    # 평균 점수 계산
    total_analyzed = len(filtered_posts)
    sentiment_avg = round(total_score / total_analyzed, 3) if total_analyzed > 0 else 0.0
    
    # 부정적 게시글 정렬 (점수 오름차순 - 가장 부정적인 것 먼저)
    negative_posts.sort(key=lambda x: x['sentiment_score'])
    
    # 제한 적용
    negative_posts = negative_posts[:limit]
    
    return jsonify({
        'game': game_info,
        'sentiment_distribution': sentiment_distribution,
        'sentiment_avg': sentiment_avg,
        'total_analyzed': total_analyzed,
        'negative_posts': negative_posts,
        'negative_threshold': negative_threshold,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'sites': site_filter
        }
    })


# 이슈 탐지기 인스턴스 (싱글톤)
_issue_detector = None

def get_issue_detector():
    """이슈 탐지기 인스턴스 반환 (싱글톤 패턴)"""
    global _issue_detector
    if _issue_detector is None:
        _issue_detector = IssueDetector(sentiment_analyzer=get_sentiment_analyzer())
    return _issue_detector


@app.route('/api/game/<game_id>/issues')
def api_game_issues(game_id):
    """게임별 이슈 목록 API
    
    Requirements: 3.5, 3.6
    - 이슈 목록을 우선순위 순으로 반환
    - Hot Issue 표시
    
    Args:
        game_id: 게임 ID (kebab-case)
        
    Query Parameters:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        site: 사이트 필터 (복수 가능)
        limit: 반환할 이슈 최대 개수 (기본값: 20)
        include_bugs_only: 버그 이슈만 반환 (기본값: false)
        
    Returns:
        JSON: {
            game: {...},
            issues: [{issue_id, title, priority_score, is_hot, is_bug, severity, ...}, ...],
            total_issues: int,
            hot_issue_count: int,
            bug_issue_count: int
        }
    """
    posts = load_crawl_data()
    
    # 게임 정보 조회
    game_info = get_game_info(posts, game_id)
    if not game_info:
        return jsonify({'error': 'Game not found'}), 404
    
    # 게임별 게시글 필터링
    game_posts = filter_posts_by_game(posts, game_id)
    
    # 쿼리 파라미터에서 필터 조건 추출
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    site_filter = request.args.getlist('site')
    limit = request.args.get('limit', 20, type=int)
    include_bugs_only = request.args.get('include_bugs_only', 'false').lower() == 'true'
    
    # 필터 적용
    filtered_posts = game_posts
    if start_date or end_date:
        filtered_posts = filter_posts_by_date_range(filtered_posts, start_date, end_date)
    if site_filter:
        filtered_posts = filter_posts_by_site(filtered_posts, site_filter)
    
    # PostContent 객체로 변환
    post_contents = [convert_post_dict_to_postcontent(p) for p in filtered_posts]
    
    # 이슈 탐지
    detector = get_issue_detector()
    issues = detector.detect_issues(post_contents)
    
    # Hot Issue 탐지 (상위 10%)
    hot_issues = detector.detect_hot_issues(issues, threshold_percentile=0.9)
    
    # 버그 이슈만 필터링 (옵션)
    if include_bugs_only:
        issues = [issue for issue in issues if issue.is_bug]
    
    # 통계 계산
    total_issues = len(issues)
    hot_issue_count = len([i for i in issues if i.is_hot])
    bug_issue_count = len([i for i in issues if i.is_bug])
    
    # 제한 적용
    issues = issues[:limit]
    
    # 응답 데이터 구성
    response_issues = []
    for issue in issues:
        response_issues.append({
            'issue_id': issue.issue_id,
            'title': issue.title,
            'priority_score': round(issue.priority_score, 4),
            'is_hot': issue.is_hot,
            'is_bug': issue.is_bug,
            'severity': issue.severity.value,
            'sentiment_avg': round(issue.sentiment_avg, 3),
            'post_count': issue.cluster.post_count,
            'total_views': issue.cluster.total_views,
            'total_comments': issue.cluster.total_comments,
            'keywords': issue.cluster.keywords[:5],  # 상위 5개 키워드만
            'related_post_count': len(issue.related_posts),
            'first_seen': issue.first_seen.isoformat() if issue.first_seen else None
        })
    
    return jsonify({
        'game': game_info,
        'issues': response_issues,
        'total_issues': total_issues,
        'hot_issue_count': hot_issue_count,
        'bug_issue_count': bug_issue_count,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'sites': site_filter,
            'include_bugs_only': include_bugs_only
        }
    })


@app.route('/api/game/<game_id>/issues/hot')
def api_game_hot_issues(game_id):
    """게임별 Hot Issue 목록 API
    
    Requirements: 3.4, 3.6
    - Hot Issue만 반환 (우선순위 상위 10%)
    - 시각적 강조를 위한 상세 정보 포함
    
    Args:
        game_id: 게임 ID (kebab-case)
        
    Query Parameters:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        site: 사이트 필터 (복수 가능)
        threshold_percentile: Hot Issue 임계 백분위 (기본값: 0.9)
        
    Returns:
        JSON: {
            game: {...},
            hot_issues: [{issue_id, title, priority_score, ...}, ...],
            total_hot_issues: int,
            alert_message: str (Hot Issue가 있을 경우 알림 메시지)
        }
    """
    posts = load_crawl_data()
    
    # 게임 정보 조회
    game_info = get_game_info(posts, game_id)
    if not game_info:
        return jsonify({'error': 'Game not found'}), 404
    
    # 게임별 게시글 필터링
    game_posts = filter_posts_by_game(posts, game_id)
    
    # 쿼리 파라미터에서 필터 조건 추출
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    site_filter = request.args.getlist('site')
    threshold_percentile = request.args.get('threshold_percentile', 0.9, type=float)
    
    # 필터 적용
    filtered_posts = game_posts
    if start_date or end_date:
        filtered_posts = filter_posts_by_date_range(filtered_posts, start_date, end_date)
    if site_filter:
        filtered_posts = filter_posts_by_site(filtered_posts, site_filter)
    
    # PostContent 객체로 변환
    post_contents = [convert_post_dict_to_postcontent(p) for p in filtered_posts]
    
    # 이슈 탐지
    detector = get_issue_detector()
    issues = detector.detect_issues(post_contents)
    
    # Hot Issue 탐지
    hot_issues = detector.detect_hot_issues(issues, threshold_percentile=threshold_percentile)
    
    # 응답 데이터 구성
    response_hot_issues = []
    for issue in hot_issues:
        # 관련 게시글 URL에서 제목 찾기
        related_posts_info = []
        for url in issue.related_posts[:5]:  # 상위 5개만
            for post in filtered_posts:
                if post.get('url') == url:
                    related_posts_info.append({
                        'url': url,
                        'title': post.get('title', '')[:50],
                        'view_count': post.get('view_count', 0),
                        'comment_count': len(post.get('comments', []))
                    })
                    break
        
        response_hot_issues.append({
            'issue_id': issue.issue_id,
            'title': issue.title,
            'priority_score': round(issue.priority_score, 4),
            'is_bug': issue.is_bug,
            'severity': issue.severity.value,
            'sentiment_avg': round(issue.sentiment_avg, 3),
            'post_count': issue.cluster.post_count,
            'total_views': issue.cluster.total_views,
            'total_comments': issue.cluster.total_comments,
            'keywords': issue.cluster.keywords[:5],
            'related_posts': related_posts_info,
            'first_seen': issue.first_seen.isoformat() if issue.first_seen else None
        })
    
    # 알림 메시지 생성
    alert_message = None
    if hot_issues:
        top_issue = hot_issues[0]
        alert_message = f"🔥 긴급 이슈 발생: '{top_issue.title}' - {top_issue.cluster.post_count}개 게시글에서 언급됨"
    
    return jsonify({
        'game': game_info,
        'hot_issues': response_hot_issues,
        'total_hot_issues': len(hot_issues),
        'alert_message': alert_message,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'sites': site_filter,
            'threshold_percentile': threshold_percentile
        }
    })


@app.route('/api/game/<game_id>/hot-posts')
def api_game_hot_posts(game_id):
    """게임별 Hot Post 목록 API (게시글 기반)
    
    게시글 단위로 조회수, 댓글수, 감성 점수를 기반으로 Hot Score를 계산하여
    상위 게시글을 Hot Post로 반환
    
    Args:
        game_id: 게임 ID (kebab-case)
        
    Query Parameters:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        site: 사이트 필터 (복수 가능)
        limit: 반환할 Hot Post 최대 개수 (기본값: 20)
        view_weight: 조회수 가중치 (기본값: 0.4)
        comment_weight: 댓글수 가중치 (기본값: 0.3)
        sentiment_weight: 감성 가중치 (기본값: 0.3)
        
    Returns:
        JSON: {
            game: {...},
            hot_posts: [{post_url, title, hot_score, view_count, comment_count, ...}, ...],
            total_hot_posts: int,
            bug_count: int,
            critical_count: int,
            alert_message: str
        }
    """
    posts = load_crawl_data()
    
    # 게임 정보 조회
    game_info = get_game_info(posts, game_id)
    if not game_info:
        return jsonify({'error': 'Game not found'}), 404
    
    # 게임별 게시글 필터링
    game_posts = filter_posts_by_game(posts, game_id)
    
    # 쿼리 파라미터에서 필터 조건 추출
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    site_filter = request.args.getlist('site')
    limit = request.args.get('limit', 20, type=int)
    view_weight = request.args.get('view_weight', 0.4, type=float)
    comment_weight = request.args.get('comment_weight', 0.3, type=float)
    sentiment_weight = request.args.get('sentiment_weight', 0.3, type=float)
    
    # 필터 적용
    filtered_posts = game_posts
    if start_date or end_date:
        filtered_posts = filter_posts_by_date_range(filtered_posts, start_date, end_date)
    if site_filter:
        filtered_posts = filter_posts_by_site(filtered_posts, site_filter)
    
    # PostContent 객체로 변환
    post_contents = [convert_post_dict_to_postcontent(p) for p in filtered_posts]
    
    # Hot Post 탐지
    detector = get_issue_detector()
    hot_posts = detector.detect_hot_posts(
        post_contents, 
        top_n=limit,
        view_weight=view_weight,
        comment_weight=comment_weight,
        sentiment_weight=sentiment_weight
    )
    
    # 통계 계산
    bug_count = sum(1 for p in hot_posts if p.is_bug)
    critical_count = sum(1 for p in hot_posts if p.severity.value == 'critical')
    
    # 알림 메시지 생성
    alert_message = None
    if hot_posts:
        top_post = hot_posts[0]
        title_preview = top_post.title[:50] + '...' if len(top_post.title) > 50 else top_post.title
        if top_post.hot_score >= 0.7:
            alert_message = f"🔥 긴급: '{title_preview}' - 조회수 {top_post.view_count:,}, 댓글 {top_post.comment_count}개"
        elif top_post.hot_score >= 0.5:
            alert_message = f"⚠️ 주목: '{title_preview}' - 조회수 {top_post.view_count:,}"
    
    # 응답 데이터 구성
    response_hot_posts = []
    for hp in hot_posts:
        response_hot_posts.append({
            'post_url': hp.post_url,
            'title': hp.title,
            'author': hp.author,
            'site': hp.site,
            'created_at': hp.created_at.isoformat() if hp.created_at else None,
            'view_count': hp.view_count,
            'comment_count': hp.comment_count,
            'like_count': hp.like_count,
            'hot_score': round(hp.hot_score, 4),
            'sentiment_score': round(hp.sentiment_score, 3),
            'is_bug': hp.is_bug,
            'severity': hp.severity.value,
            'keywords': hp.keywords
        })
    
    return jsonify({
        'game': game_info,
        'hot_posts': response_hot_posts,
        'total_hot_posts': len(hot_posts),
        'bug_count': bug_count,
        'critical_count': critical_count,
        'alert_message': alert_message,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'sites': site_filter,
            'limit': limit,
            'view_weight': view_weight,
            'comment_weight': comment_weight,
            'sentiment_weight': sentiment_weight
        }
    })


@app.route('/api/game/<game_id>/bugs')
def api_game_bugs(game_id):
    """게임별 버그 이슈 목록 API
    
    Requirements: 7.3
    - 버그/오류 관련 이슈만 필터링하여 반환
    - 심각도 순으로 정렬
    
    Args:
        game_id: 게임 ID (kebab-case)
        
    Query Parameters:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        site: 사이트 필터 (복수 가능)
        limit: 반환할 버그 이슈 최대 개수 (기본값: 50)
        severity: 심각도 필터 (critical, high, medium, low)
        
    Returns:
        JSON: {
            game: {...},
            bug_issues: [{issue_id, title, severity, priority_score, ...}, ...],
            total_bug_issues: int,
            severity_distribution: {critical: n, high: n, medium: n, low: n},
            alert_message: str
        }
    """
    posts = load_crawl_data()
    
    # 게임 정보 조회
    game_info = get_game_info(posts, game_id)
    if not game_info:
        return jsonify({'error': 'Game not found'}), 404
    
    # 게임별 게시글 필터링
    game_posts = filter_posts_by_game(posts, game_id)
    
    # 쿼리 파라미터에서 필터 조건 추출
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    site_filter = request.args.getlist('site')
    limit = request.args.get('limit', 50, type=int)
    severity_filter = request.args.get('severity', '')
    
    # 필터 적용
    filtered_posts = game_posts
    if start_date or end_date:
        filtered_posts = filter_posts_by_date_range(filtered_posts, start_date, end_date)
    if site_filter:
        filtered_posts = filter_posts_by_site(filtered_posts, site_filter)
    
    # PostContent 객체로 변환
    post_contents = [convert_post_dict_to_postcontent(p) for p in filtered_posts]
    
    # 이슈 탐지
    detector = get_issue_detector()
    all_issues = detector.detect_issues(post_contents)
    
    # 버그 이슈만 필터링
    bug_issues = detector.get_bug_issues(all_issues)
    
    # 심각도 필터 적용
    if severity_filter:
        bug_issues = [issue for issue in bug_issues if issue.severity.value == severity_filter.lower()]
    
    # 심각도 분포 계산
    severity_distribution = {
        'critical': 0,
        'high': 0,
        'medium': 0,
        'low': 0
    }
    for issue in bug_issues:
        severity_distribution[issue.severity.value] += 1
    
    total_bug_issues = len(bug_issues)
    
    # 제한 적용
    bug_issues = bug_issues[:limit]
    
    # 응답 데이터 구성
    response_bug_issues = []
    for issue in bug_issues:
        # 관련 게시글 정보 수집
        related_posts_info = []
        for url in issue.related_posts[:5]:  # 상위 5개만
            for post in filtered_posts:
                if post.get('url') == url:
                    related_posts_info.append({
                        'url': url,
                        'title': post.get('title', '')[:50],
                        'view_count': post.get('view_count', 0),
                        'comment_count': len(post.get('comments', []))
                    })
                    break
        
        response_bug_issues.append({
            'issue_id': issue.issue_id,
            'title': issue.title,
            'severity': issue.severity.value,
            'priority_score': round(issue.priority_score, 4),
            'sentiment_avg': round(issue.sentiment_avg, 3),
            'post_count': issue.cluster.post_count,
            'total_views': issue.cluster.total_views,
            'total_comments': issue.cluster.total_comments,
            'keywords': issue.cluster.keywords[:5],
            'related_posts': related_posts_info,
            'first_seen': issue.first_seen.isoformat() if issue.first_seen else None
        })
    
    # 알림 메시지 생성
    alert_message = None
    critical_count = severity_distribution['critical']
    high_count = severity_distribution['high']
    
    if critical_count > 0:
        alert_message = f"🚨 심각한 버그 {critical_count}건 발견! 즉시 확인이 필요합니다."
    elif high_count > 0:
        alert_message = f"⚠️ 높은 심각도 버그 {high_count}건 발견. 확인이 필요합니다."
    
    return jsonify({
        'game': game_info,
        'bug_issues': response_bug_issues,
        'total_bug_issues': total_bug_issues,
        'severity_distribution': severity_distribution,
        'alert_message': alert_message,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'sites': site_filter,
            'severity': severity_filter
        }
    })


@app.route('/game/<game_id>/bugs')
def game_bugs_page(game_id):
    """게임별 버그 리포트 페이지
    
    Requirements: 7.3
    - 버그 이슈 목록 및 심각도 표시
    
    Args:
        game_id: 게임 ID (kebab-case)
    """
    posts = load_crawl_data()
    
    # 게임 정보 조회
    game_info = get_game_info(posts, game_id)
    if not game_info:
        return "게임을 찾을 수 없습니다.", 404
    
    # 게임별 게시글 필터링
    game_posts = filter_posts_by_game(posts, game_id)
    
    # 쿼리 파라미터에서 필터 조건 추출
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    site_filter = request.args.getlist('site')
    severity_filter = request.args.get('severity', '')
    
    # 필터 적용
    filtered_posts = game_posts
    if start_date or end_date:
        filtered_posts = filter_posts_by_date_range(filtered_posts, start_date, end_date)
    if site_filter:
        filtered_posts = filter_posts_by_site(filtered_posts, site_filter)
    
    # PostContent 객체로 변환
    post_contents = [convert_post_dict_to_postcontent(p) for p in filtered_posts]
    
    # 이슈 탐지
    detector = get_issue_detector()
    all_issues = detector.detect_issues(post_contents)
    
    # 버그 이슈만 필터링
    bug_issues = detector.get_bug_issues(all_issues)
    
    # 심각도 필터 적용
    if severity_filter:
        bug_issues = [issue for issue in bug_issues if issue.severity.value == severity_filter.lower()]
    
    # 심각도 분포 계산
    severity_distribution = {
        'critical': 0,
        'high': 0,
        'medium': 0,
        'low': 0
    }
    for issue in all_issues:
        if issue.is_bug:
            severity_distribution[issue.severity.value] += 1
    
    # 사용 가능한 사이트 목록
    available_sites = get_available_sites(game_posts)
    
    # 버그 관련 게시글 수집
    bug_posts = []
    for issue in bug_issues:
        for url in issue.related_posts[:3]:  # 이슈당 상위 3개 게시글
            for post in filtered_posts:
                if post.get('url') == url:
                    bug_posts.append({
                        'url': url,
                        'title': post.get('title', ''),
                        'author': post.get('author', ''),
                        'created_at': post.get('created_at', ''),
                        'view_count': post.get('view_count', 0),
                        'comment_count': len(post.get('comments', [])),
                        'site': post.get('site', ''),
                        'issue_title': issue.title,
                        'severity': issue.severity.value
                    })
                    break
    
    return render_template(
        'bug_report.html',
        game=game_info,
        bug_issues=bug_issues,
        bug_posts=bug_posts,
        severity_distribution=severity_distribution,
        available_sites=available_sites,
        filters={
            'start_date': start_date,
            'end_date': end_date,
            'sites': site_filter,
            'severity': severity_filter
        }
    )


# 트렌드 분석기 인스턴스 (싱글톤)
_trend_analyzer = None

def get_trend_analyzer():
    """트렌드 분석기 인스턴스 반환 (싱글톤 패턴)"""
    global _trend_analyzer
    if _trend_analyzer is None:
        from crawler.analysis.trend_analyzer import TrendAnalyzer
        _trend_analyzer = TrendAnalyzer(sentiment_analyzer=get_sentiment_analyzer())
    return _trend_analyzer


@app.route('/api/game/<game_id>/sentiment/trend')
def api_game_sentiment_trend(game_id):
    """게임별 감성 트렌드 API
    
    Requirements: 4.1, 4.2
    - 일별/주별 감성 점수 추이 반환
    - 시계열 차트 데이터 제공
    
    Args:
        game_id: 게임 ID (kebab-case)
        
    Query Parameters:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        site: 사이트 필터 (복수 가능)
        period: 기간 단위 (daily, weekly) - 기본값: daily
        
    Returns:
        JSON: {
            game: {...},
            trend: {
                metric_name: str,
                period: str,
                data_points: [{date, value, count}, ...]
            },
            summary: {
                avg_value: float,
                min_value: float,
                max_value: float,
                total_points: int,
                total_count: int
            },
            spikes: [{date, value, count}, ...],  # 부정적 감성 급증 포인트
            filters: {...}
        }
    """
    posts = load_crawl_data()
    
    # 게임 정보 조회
    game_info = get_game_info(posts, game_id)
    if not game_info:
        return jsonify({'error': 'Game not found'}), 404
    
    # 게임별 게시글 필터링
    game_posts = filter_posts_by_game(posts, game_id)
    
    # 쿼리 파라미터에서 필터 조건 추출
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    site_filter = request.args.getlist('site')
    period = request.args.get('period', 'daily')
    
    # 필터 적용
    filtered_posts = game_posts
    if start_date_str or end_date_str:
        filtered_posts = filter_posts_by_date_range(filtered_posts, start_date_str, end_date_str)
    if site_filter:
        filtered_posts = filter_posts_by_site(filtered_posts, site_filter)
    
    # PostContent 객체로 변환
    post_contents = [convert_post_dict_to_postcontent(p) for p in filtered_posts]
    
    # 날짜 파싱 (TrendAnalyzer용)
    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            pass
    
    # 트렌드 분석
    analyzer = get_trend_analyzer()
    trend_data = analyzer.analyze_sentiment_trend(
        post_contents,
        period=period,
        start_date=start_date,
        end_date=end_date
    )
    
    # 부정적 감성 급증 탐지
    spikes = analyzer.detect_sentiment_spike(trend_data, threshold=-0.3)
    
    # 요약 정보 생성
    summary = analyzer.get_trend_summary(trend_data)
    
    # 응답 데이터 구성
    response_data_points = []
    for point in trend_data.data_points:
        response_data_points.append({
            'date': point.date.strftime('%Y-%m-%d'),
            'value': round(point.value, 3),
            'count': point.count
        })
    
    response_spikes = []
    for spike in spikes:
        response_spikes.append({
            'date': spike.date.strftime('%Y-%m-%d'),
            'value': round(spike.value, 3),
            'count': spike.count
        })
    
    return jsonify({
        'game': game_info,
        'trend': {
            'metric_name': trend_data.metric_name,
            'period': trend_data.period,
            'data_points': response_data_points
        },
        'summary': {
            'avg_value': round(summary['avg_value'], 3) if summary['total_points'] > 0 else 0,
            'min_value': round(summary['min_value'], 3) if summary['total_points'] > 0 else 0,
            'max_value': round(summary['max_value'], 3) if summary['total_points'] > 0 else 0,
            'total_points': summary['total_points'],
            'total_count': summary['total_count'],
            'start_date': summary['start_date'],
            'end_date': summary['end_date']
        },
        'spikes': response_spikes,
        'filters': {
            'start_date': start_date_str,
            'end_date': end_date_str,
            'sites': site_filter,
            'period': period
        }
    })


@app.route('/api/game/<game_id>/issues/<issue_id>/trend')
def api_game_issue_trend(game_id, issue_id):
    """게임별 이슈 트렌드 API
    
    Requirements: 4.4
    - 특정 이슈의 언급 빈도 추이 반환
    - 시계열 차트 데이터 제공
    
    Args:
        game_id: 게임 ID (kebab-case)
        issue_id: 이슈 ID
        
    Query Parameters:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        site: 사이트 필터 (복수 가능)
        period: 기간 단위 (daily, weekly) - 기본값: daily
        
    Returns:
        JSON: {
            game: {...},
            issue: {...},
            trend: {
                metric_name: str,
                period: str,
                data_points: [{date, value, count}, ...]
            },
            summary: {...},
            filters: {...}
        }
    """
    posts = load_crawl_data()
    
    # 게임 정보 조회
    game_info = get_game_info(posts, game_id)
    if not game_info:
        return jsonify({'error': 'Game not found'}), 404
    
    # 게임별 게시글 필터링
    game_posts = filter_posts_by_game(posts, game_id)
    
    # 쿼리 파라미터에서 필터 조건 추출
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    site_filter = request.args.getlist('site')
    period = request.args.get('period', 'daily')
    
    # 필터 적용
    filtered_posts = game_posts
    if start_date_str or end_date_str:
        filtered_posts = filter_posts_by_date_range(filtered_posts, start_date_str, end_date_str)
    if site_filter:
        filtered_posts = filter_posts_by_site(filtered_posts, site_filter)
    
    # PostContent 객체로 변환
    post_contents = [convert_post_dict_to_postcontent(p) for p in filtered_posts]
    
    # 이슈 탐지하여 해당 이슈 찾기
    detector = get_issue_detector()
    issues = detector.detect_issues(post_contents)
    
    # 이슈 ID 또는 제목으로 이슈 찾기
    target_issue = None
    for issue in issues:
        # ID로 찾기
        if issue.issue_id == issue_id:
            target_issue = issue
            break
        # 제목(대표 키워드)으로 찾기 (URL 인코딩된 경우 대비)
        if issue.title == issue_id or issue.title.lower() == issue_id.lower():
            target_issue = issue
            break
        # 클러스터 대표 키워드로 찾기
        if issue.cluster and issue.cluster.representative == issue_id:
            target_issue = issue
            break
    
    if not target_issue:
        # 이슈를 찾지 못한 경우, 키워드 트렌드로 대체
        # issue_id를 키워드로 사용하여 트렌드 분석
        analyzer = get_trend_analyzer()
        
        # 날짜 파싱
        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            except ValueError:
                pass
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            except ValueError:
                pass
        
        trend_data = analyzer.analyze_keyword_trend(
            post_contents,
            keyword=issue_id,
            period=period,
            start_date=start_date,
            end_date=end_date
        )
        
        summary = analyzer.get_trend_summary(trend_data)
        
        response_data_points = []
        for point in trend_data.data_points:
            response_data_points.append({
                'date': point.date.strftime('%Y-%m-%d'),
                'value': round(point.value, 3),
                'count': point.count
            })
        
        return jsonify({
            'game': game_info,
            'issue': {
                'issue_id': issue_id,
                'title': issue_id,
                'keywords': [issue_id],
                'post_count': summary['total_count'],
                'is_hot': False,
                'is_bug': False,
                'severity': 'low',
                'priority_score': 0
            },
            'trend': {
                'metric_name': trend_data.metric_name,
                'period': trend_data.period,
                'data_points': response_data_points
            },
            'summary': {
                'avg_value': round(summary['avg_value'], 3) if summary['total_points'] > 0 else 0,
                'min_value': round(summary['min_value'], 3) if summary['total_points'] > 0 else 0,
                'max_value': round(summary['max_value'], 3) if summary['total_points'] > 0 else 0,
                'total_points': summary['total_points'],
                'total_count': summary['total_count'],
                'start_date': summary['start_date'],
                'end_date': summary['end_date']
            },
            'filters': {
                'start_date': start_date_str,
                'end_date': end_date_str,
                'sites': site_filter,
                'period': period
            }
        })
    
    # 날짜 파싱 (TrendAnalyzer용)
    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            pass
    
    # 트렌드 분석
    analyzer = get_trend_analyzer()
    trend_data = analyzer.analyze_issue_trend(
        post_contents,
        issue=target_issue,
        period=period,
        start_date=start_date,
        end_date=end_date
    )
    
    # 요약 정보 생성
    summary = analyzer.get_trend_summary(trend_data)
    
    # 응답 데이터 구성
    response_data_points = []
    for point in trend_data.data_points:
        response_data_points.append({
            'date': point.date.strftime('%Y-%m-%d'),
            'value': round(point.value, 3),
            'count': point.count
        })
    
    # 이슈 정보
    issue_info = {
        'issue_id': target_issue.issue_id,
        'title': target_issue.title,
        'keywords': target_issue.cluster.keywords[:5] if target_issue.cluster else [],
        'post_count': target_issue.cluster.post_count if target_issue.cluster else 0,
        'is_hot': target_issue.is_hot,
        'is_bug': target_issue.is_bug,
        'severity': target_issue.severity.value,
        'priority_score': round(target_issue.priority_score, 4)
    }
    
    return jsonify({
        'game': game_info,
        'issue': issue_info,
        'trend': {
            'metric_name': trend_data.metric_name,
            'period': trend_data.period,
            'data_points': response_data_points
        },
        'summary': {
            'avg_value': round(summary['avg_value'], 3) if summary['total_points'] > 0 else 0,
            'min_value': round(summary['min_value'], 3) if summary['total_points'] > 0 else 0,
            'max_value': round(summary['max_value'], 3) if summary['total_points'] > 0 else 0,
            'total_points': summary['total_points'],
            'total_count': summary['total_count'],
            'start_date': summary['start_date'],
            'end_date': summary['end_date']
        },
        'filters': {
            'start_date': start_date_str,
            'end_date': end_date_str,
            'sites': site_filter,
            'period': period
        }
    })


@app.route('/api/game/<game_id>/keyword/<keyword>/trend')
def api_game_keyword_trend(game_id, keyword):
    """게임별 키워드 트렌드 API
    
    특정 키워드의 언급 빈도 추이 반환
    
    Args:
        game_id: 게임 ID (kebab-case)
        keyword: 검색할 키워드
        
    Query Parameters:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        site: 사이트 필터 (복수 가능)
        period: 기간 단위 (daily, weekly) - 기본값: daily
        
    Returns:
        JSON: {
            game: {...},
            keyword: str,
            trend: {...},
            summary: {...},
            filters: {...}
        }
    """
    posts = load_crawl_data()
    
    # 게임 정보 조회
    game_info = get_game_info(posts, game_id)
    if not game_info:
        return jsonify({'error': 'Game not found'}), 404
    
    # 게임별 게시글 필터링
    game_posts = filter_posts_by_game(posts, game_id)
    
    # 쿼리 파라미터에서 필터 조건 추출
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    site_filter = request.args.getlist('site')
    period = request.args.get('period', 'daily')
    
    # 필터 적용
    filtered_posts = game_posts
    if start_date_str or end_date_str:
        filtered_posts = filter_posts_by_date_range(filtered_posts, start_date_str, end_date_str)
    if site_filter:
        filtered_posts = filter_posts_by_site(filtered_posts, site_filter)
    
    # PostContent 객체로 변환
    post_contents = [convert_post_dict_to_postcontent(p) for p in filtered_posts]
    
    # 날짜 파싱 (TrendAnalyzer용)
    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            pass
    
    # 트렌드 분석
    analyzer = get_trend_analyzer()
    trend_data = analyzer.analyze_keyword_trend(
        post_contents,
        keyword=keyword,
        period=period,
        start_date=start_date,
        end_date=end_date
    )
    
    # 요약 정보 생성
    summary = analyzer.get_trend_summary(trend_data)
    
    # 응답 데이터 구성
    response_data_points = []
    for point in trend_data.data_points:
        response_data_points.append({
            'date': point.date.strftime('%Y-%m-%d'),
            'value': round(point.value, 3),
            'count': point.count
        })
    
    return jsonify({
        'game': game_info,
        'keyword': keyword,
        'trend': {
            'metric_name': trend_data.metric_name,
            'period': trend_data.period,
            'data_points': response_data_points
        },
        'summary': {
            'avg_value': round(summary['avg_value'], 3) if summary['total_points'] > 0 else 0,
            'min_value': round(summary['min_value'], 3) if summary['total_points'] > 0 else 0,
            'max_value': round(summary['max_value'], 3) if summary['total_points'] > 0 else 0,
            'total_points': summary['total_points'],
            'total_count': summary['total_count'],
            'start_date': summary['start_date'],
            'end_date': summary['end_date']
        },
        'filters': {
            'start_date': start_date_str,
            'end_date': end_date_str,
            'sites': site_filter,
            'period': period
        }
    })


if __name__ == '__main__':
    print("="*50)
    print("크롤링 결과 대시보드")
    print("="*50)
    print(f"데이터 디렉토리: {DATA_DIR}")
    print("브라우저에서 http://localhost:5000 접속")
    print("="*50)
    app.run(debug=True, port=5000)
