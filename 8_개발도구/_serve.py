import os, http.server, socketserver, threading
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # 유방암 (2026-10-01 폴더 정리)
class H(http.server.SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self,*a): pass
class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
with S(('127.0.0.1', int(os.environ.get('PORT','8901'))), H) as s:
    print('serving', flush=True); s.serve_forever()
