#!/usr/bin/env python3
# 취약점이 잔뜩 있는 Flask 애플리케이션 예제
# 주의: 이 코드는 교육 목적으로만 사용하세요! 실제 환경에 배포하지 마세요!

from flask import Flask, request, render_template_string, redirect, session
import sqlite3
import os
import logging
import hashlib
import base64

app = Flask(__name__)
app.secret_key = "mysupersecretkey"  # 하드코딩된 시크릿 키 (보안 취약점)
DATABASE = "users.db"
API_KEY = "myapikey1234"  # 하드코딩된 API 키 (보안 취약점)
PASSWORD = "admin123"  # 하드코딩된 패스워드 (보안 취약점)

# 안전하지 않은 로깅 설정 (보안 취약점)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT,
        email TEXT,
        credit_card TEXT
    )
    ''')
    
    # 평문 패스워드 사용 (보안 취약점)
    cursor.execute("INSERT OR IGNORE INTO users (id, username, password, email, credit_card) VALUES (1, 'admin', 'admin123', 'admin@example.com', '1234-5678-9012-3456')")
    conn.commit()
    conn.close()

@app.route('/')
def home():
    # XSS 취약점이 있는 템플릿 (보안 취약점)
    template = '''
    <html>
    <head><title>취약한 애플리케이션</title></head>
    <body>
        <h1>안녕하세요, 취약한 애플리케이션입니다!</h1>
        <p>이름을 입력하세요:</p>
        <form method="GET" action="/greet">
            <input type="text" name="name">
            <input type="submit" value="인사하기">
        </form>
        <a href="/login">로그인</a>
        <hr>
        <a href="/search">검색</a>
        <a href="/user_info">사용자 정보</a>
        <a href="/file">파일 다운로드</a>
    </body>
    </html>
    '''
    return render_template_string(template)

@app.route('/greet')
def greet():
    # XSS 취약점 - 사용자 입력이 직접 템플릿에 삽입됨 (보안 취약점)
    name = request.args.get('name', '')
    logger.info(f"사용자 이름: {name}")  # 안전하지 않은 로깅 (보안 취약점)
    
    template = f'''
    <html>
    <head><title>인사</title></head>
    <body>
        <h1>안녕하세요, {name}님!</h1>
        <a href="/">홈으로</a>
    </body>
    </html>
    '''
    return render_template_string(template)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # SQL 인젝션 취약점 (보안 취약점)
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        cursor.execute(query)
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['logged_in'] = True
            session['username'] = username
            return redirect('/dashboard')
        else:
            error = '잘못된 사용자명 또는 패스워드'
    
    template = '''
    <html>
    <head><title>로그인</title></head>
    <body>
        <h1>로그인</h1>
        {% if error %}
        <p style="color: red;">{{ error }}</p>
        {% endif %}
        <form method="POST">
            <p>사용자명: <input type="text" name="username"></p>
            <p>패스워드: <input type="password" name="password"></p>
            <input type="submit" value="로그인">
        </form>
        <a href="/">홈으로</a>
    </body>
    </html>
    '''
    return render_template_string(template, error=error)

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect('/login')
    
    # CSRF 취약점 - 토큰 없음 (보안 취약점)
    template = '''
    <html>
    <head><title>대시보드</title></head>
    <body>
        <h1>대시보드</h1>
        <p>환영합니다, {{ username }}님!</p>
        <form action="/update_profile" method="POST">
            <p>이메일 변경: <input type="text" name="email"></p>
            <input type="submit" value="업데이트">
        </form>
        <a href="/logout">로그아웃</a>
    </body>
    </html>
    '''
    return render_template_string(template, username=session.get('username'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if not session.get('logged_in'):
        return redirect('/login')
    
    email = request.form.get('email')
    username = session.get('username')
    
    # 이메일 검증 없음 (보안 취약점)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # SQL 인젝션 취약점 (보안 취약점)
    query = f"UPDATE users SET email = '{email}' WHERE username = '{username}'"
    cursor.execute(query)
    conn.commit()
    conn.close()
    
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect('/')

@app.route('/search')
def search():
    query = request.args.get('q', '')
    
    # 명령어 인젝션 취약점 (보안 취약점)
    if query:
        result = os.popen(f"find / -name '*{query}*' 2>/dev/null").read()
    else:
        result = ""
    
    template = '''
    <html>
    <head><title>검색</title></head>
    <body>
        <h1>파일 검색</h1>
        <form method="GET">
            <p>검색어: <input type="text" name="q" value="{{ query }}"></p>
            <input type="submit" value="검색">
        </form>
        <pre>{{ result }}</pre>
        <a href="/">홈으로</a>
    </body>
    </html>
    '''
    return render_template_string(template, query=query, result=result)

@app.route('/user_info')
def user_info():
    user_id = request.args.get('id')
    
    if not user_id:
        return redirect('/')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # SQL 인젝션 취약점 (보안 취약점)
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return "사용자를 찾을 수 없습니다."
    
    # 민감한 정보 노출 (보안 취약점)
    template = '''
    <html>
    <head><title>사용자 정보</title></head>
    <body>
        <h1>사용자 정보</h1>
        <p>ID: {{ user[0] }}</p>
        <p>사용자명: {{ user[1] }}</p>
        <p>패스워드: {{ user[2] }}</p>
        <p>이메일: {{ user[3] }}</p>
        <p>신용카드: {{ user[4] }}</p>
        <a href="/">홈으로</a>
    </body>
    </html>
    '''
    return render_template_string(template, user=user)

@app.route('/file')
def download_file():
    filename = request.args.get('filename')
    
    # 경로 순회 취약점 (보안 취약점)
    if filename:
        try:
            with open(filename, 'r') as f:
                content = f.read()
        except Exception as e:
            content = f"오류: {str(e)}"
    else:
        content = ""
    
    template = '''
    <html>
    <head><title>파일 다운로드</title></head>
    <body>
        <h1>파일 다운로드</h1>
        <form method="GET">
            <p>파일명: <input type="text" name="filename"></p>
            <input type="submit" value="다운로드">
        </form>
        <pre>{{ content }}</pre>
        <a href="/">홈으로</a>
    </body>
    </html>
    '''
    return render_template_string(template, content=content)

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.json
    
    if not data or 'username' not in data or 'password' not in data:
        return {"error": "유효하지 않은 데이터"}, 400
    
    username = data['username']
    password = data['password']
    email = data.get('email', '')
    
    # 안전하지 않은 패스워드 처리 (보안 취약점)
    # 단순 MD5 해시 사용 (보안 취약점)
    hashed_pw = hashlib.md5(password.encode()).hexdigest()
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # SQL 인젝션 취약점 (보안 취약점)
    query = f"INSERT INTO users (username, password, email) VALUES ('{username}', '{hashed_pw}', '{email}')"
    cursor.execute(query)
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    logger.info(f"새 사용자 생성: {username}, 패스워드: {password}")  # 로그에 패스워드 노출 (보안 취약점)
    
    return {"id": user_id, "username": username}, 201

@app.route('/admin')
def admin():
    # 하드코딩된 관리자 패스워드 확인 (보안 취약점)
    password = request.args.get('password')
    if password != PASSWORD:
        return "접근 거부", 403
    
    # 디버그 정보 노출 (보안 취약점)
    env_info = {}
    for key, value in os.environ.items():
        env_info[key] = value
    
    template = '''
    <html>
    <head><title>관리자 페이지</title></head>
    <body>
        <h1>관리자 페이지</h1>
        <h2>환경 변수:</h2>
        <pre>{{ env_info }}</pre>
        <a href="/">홈으로</a>
    </body>
    </html>
    '''
    return render_template_string(template, env_info=env_info)

if __name__ == '__main__':
    init_db()
    # 디버그 모드 켜짐 (보안 취약점)
    app.run(debug=True, host='0.0.0.0', port=5000) 