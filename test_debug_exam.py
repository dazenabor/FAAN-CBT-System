import sqlite3
import urllib.parse
import urllib.request
import http.cookiejar

DB = 'cbt.db'
BASE = 'http://127.0.0.1:5000'

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

# GET /login
resp = opener.open(BASE + '/login').read().decode('utf-8')
with open('resp_login_get.html', 'w', encoding='utf-8') as f:
    f.write(resp)
print('Saved resp_login_get.html')

# POST /login
data = urllib.parse.urlencode({'user_id': user_id, 'pin': pin}).encode('utf-8')
resp = opener.open(BASE + '/login', data=data).read().decode('utf-8')
with open('resp_after_login.html', 'w', encoding='utf-8') as f:
    f.write(resp)
print('Saved resp_after_login.html')

# POST start_exam
data = urllib.parse.urlencode({'action': 'start_exam'}).encode('utf-8')
resp2 = opener.open(BASE + '/exam', data=data).read().decode('utf-8')
with open('resp_after_start.html', 'w', encoding='utf-8') as f:
    f.write(resp2)
print('Saved resp_after_start.html')

print('Cookies:')
for c in cj:
    print(c)
