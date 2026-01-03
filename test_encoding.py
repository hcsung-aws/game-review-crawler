"""인코딩 테스트"""
import requests
from bs4 import BeautifulSoup

url = 'https://bbs.ruliweb.com/ps/board/300007/read/2339632'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

response = requests.get(url, headers=headers, timeout=30)

print(f'Status: {response.status_code}')
print(f'Content-Type: {response.headers.get("Content-Type")}')
print(f'apparent_encoding: {response.apparent_encoding}')
print(f'encoding: {response.encoding}')

# 강제로 utf-8 설정
response.encoding = 'utf-8'
html = response.text

soup = BeautifulSoup(html, 'lxml')

# 제목 찾기
print("\n=== 제목 찾기 ===")
title_selectors = [
    '.board_main .subject_text',
    '.subject_inner_text', 
    'h1.subject',
    '.view_title',
    '.article_title',
    'h1',
    '.subject',
    '.board_main_top .subject',
    'span.subject_text'
]

for selector in title_selectors:
    elem = soup.select_one(selector)
    if elem:
        text = elem.get_text(strip=True)
        if text:
            print(f'{selector}: {text[:100]}')

# 본문 찾기
print("\n=== 본문 찾기 ===")
body_selectors = [
    '.board_main .view_content',
    '.board_main_view .content',
    '.article_content',
    '.view_content',
    '.source_url + div'
]

for selector in body_selectors:
    elem = soup.select_one(selector)
    if elem:
        text = elem.get_text(strip=True)
        if text:
            print(f'{selector}: {text[:200]}...')
            break

# 작성자 찾기
print("\n=== 작성자 찾기 ===")
author_selectors = [
    '.board_main .user_info .nick',
    '.board_main_top .nick',
    '.user_view .nick',
    '.writer .nick',
    '.nickname',
    '.user_info a'
]

for selector in author_selectors:
    elem = soup.select_one(selector)
    if elem:
        text = elem.get_text(strip=True)
        if text:
            print(f'{selector}: {text}')
