"""앱 빌드(todak-app/www) 미리보기 서버 — 배선 검증용"""
import os, http.server, socketserver
os.chdir(r'C:\Users\rudtn\todak-app\www')
class H(http.server.SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *a): pass
class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
with S(('127.0.0.1', int(os.environ.get('PORT', '8902'))), H) as s:
    print('serving www', flush=True)
    s.serve_forever()
