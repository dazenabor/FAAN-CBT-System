import sqlite3
import urllib.parse
import urllib.request
import http.cookiejar
import time

DB = 'cbt.db'
BASE = 'http://127.0.0.1:5000'

# Find an active user in the DB
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
user = cur.execute("SELECT user_id, pin FROM users WHERE active=1 LIMIT 1").fetchone()
conn.close()

if not user:
    print('No active user found in DB. Please create one in the users table.')
    raise SystemExit(1)

user_id = user['user_id']
pin = user['pin']
print(f'Using credentials: user_id={user_id}, pin={pin}')

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Helper to perform GET
def get(path):
    url = BASE + path
    resp = opener.open(url)
    return resp.read().decode('utf-8')

# Helper to perform POST form
def post(path, data):
    url = BASE + path
    encoded = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(url, data=encoded)
    resp = opener.open(req)
    return resp.read().decode('utf-8')

# 1) GET /login
print('Fetching /login...')
login_page = get('/login')
if 'Login' not in login_page and 'User Login' not in login_page:
    print('Warning: /login page may not contain expected content')

# 2) POST /login
print('Posting login form...')
resp = post('/login', {'user_id': user_id, 'pin': pin})
# After login, the server redirects to /exam; opener follows it

# 3) Check exam page for instructions modal
if 'Exam Instructions' in resp:
    print('Instructions modal is present (as expected).')
else:
    print('Instructions modal NOT present after login — unexpected.')

# 4) Click Start Exam (POST start_exam)
print('Clicking Start Exam...')
resp2 = post('/exam', {'action': 'start_exam'})

# 5) Verify instructions modal is gone
if 'Exam Instructions' not in resp2:
    print('Instructions modal is gone after Start Exam (OK).')
else:
    print('Instructions modal still present after Start Exam (FAIL).')

# 6) Look for totalSeconds JS var
if 'let totalSeconds = ' in resp2:
    idx = resp2.find('let totalSeconds = ')
    snippet = resp2[idx: idx+60]
    print('Found timer snippet:', snippet)
else:
    print('Timer snippet not found in exam page.')

print('Test completed.')
