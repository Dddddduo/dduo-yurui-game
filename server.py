#!/usr/bin/env python3
"""
北华大学 · 接接乐 游戏服务器
- 静态文件服务
- 共享排行榜 API (所有设备共享同一份数据)
"""
import http.server
import json
import os
import socketserver
from urllib.parse import urlparse, parse_qs

PORT = 8080
DIR = os.path.dirname(os.path.abspath(__file__))
LB_FILE = os.path.join(DIR, 'leaderboard.json')
MAX_LB = 10

def load_leaderboard():
    if os.path.exists(LB_FILE):
        try:
            with open(LB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_leaderboard(data):
    with open(LB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class GameHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/leaderboard':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            data = load_leaderboard()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            return
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/leaderboard':
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len)
            try:
                entry = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error":"invalid json"}')
                return

            # 必填字段
            name = str(entry.get('name', '匿名'))[:10]
            score = int(entry.get('score', 0))
            time_sec = int(entry.get('time', 0))
            max_combo = int(entry.get('maxCombo', 1))
            pops = int(entry.get('pops', 0))

            new_entry = {
                'name': name,
                'score': score,
                'time': time_sec,
                'maxCombo': max_combo,
                'pops': pops,
                'date': entry.get('date', ''),
            }

            data = load_leaderboard()
            data.append(new_entry)
            data.sort(key=lambda x: x['score'], reverse=True)
            data = data[:MAX_LB]
            save_leaderboard(data)

            # 找到排名
            rank = -1
            for i, e in enumerate(data):
                if e is new_entry or (
                    e['name'] == new_entry['name'] and
                    e['score'] == new_entry['score'] and
                    e['date'] == new_entry['date']
                ):
                    rank = i + 1
                    break
            # 用内容匹配更可靠
            rank = -1
            for i, e in enumerate(data):
                if (e['name'] == name and e['score'] == score and
                    e['time'] == time_sec and e['date'] == new_entry['date']):
                    rank = i + 1
                    break

            resp = {'ok': True, 'rank': rank, 'leaderboard': data}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")

if __name__ == '__main__':
    print(f"""
╔══════════════════════════════════════╗
║   北华大学 · 接接乐 游戏服务器        ║
║   端口: {PORT}                         ║
║   目录: {DIR} ║
║                                      ║
║   手机访问: http://<本机IP>:{PORT}     ║
║   排行榜API: /api/leaderboard         ║
║   排行榜文件: leaderboard.json        ║
╚══════════════════════════════════════╝
""")
    with socketserver.TCPServer(("0.0.0.0", PORT), GameHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已关闭")
