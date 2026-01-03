"""세션 테스트"""
import requests

url = 'https://bbs.ruliweb.com/ps/board/300007/read/2339632'

# 세션 사용
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
})

response = session.get(url, timeout=30)
print(f'Status: {response.status_code}')
print(f'Content-Encoding: {response.headers.get("Content-Encoding")}')
print(f'encoding: {response.encoding}')
print(f'Content length: {len(response.content)}')
print(f'Text length: {len(response.text)}')
print(f'First 200 chars: {response.text[:200]}')
