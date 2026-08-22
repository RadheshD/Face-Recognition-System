import urllib.request
import urllib.error

try:
    urllib.request.urlopen('http://127.0.0.1:8000/login').read()
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}")
    print(e.read().decode())
except Exception as e:
    print(e)
