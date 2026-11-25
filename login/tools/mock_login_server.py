#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学迹登录页 · 本地 mock 服务端。

只为本地验证 login/ 而存在：真实 POST /login 端点 + 可切换的四种返回，
用来驱动登录页的 200 / 401 / 429 / 500 / 网络错误 全部分支。

服务根目录 = 仓库根目录（即本脚本上两级），这样 /assets/fonts、/styles.css
都以与线上一致的根绝对路径可达；也可以用第一个参数之后的 --root 覆盖。

密码哨兵（在密码框里原样输入即可触发对应分支）：
  xueji  -> 200 + Set-Cookie，随后 / 可访问（成功路径）
  slow   -> 200，但延迟 1.6s（loading 态）
  其他   -> 401
  flood  -> 429
  boom   -> 500
  drop   -> 直接断开连接，不返回任何响应（真实网络错误）
"""
import http.server
import os
import socketserver
import sys
import time
import urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8902
OK_PASSWORD = 'xueji'


class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        sys.stderr.write('[mock] %s\n' % (fmt % args))

    # ---------- 工具 ----------
    def _send(self, code, body=b'', ctype='text/html; charset=utf-8', cookie=None):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _authed(self):
        ck = self.headers.get('Cookie', '')
        return 'xueji_session=ok' in ck

    # ---------- GET ----------
    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path

        if path == '/logout':
            self.send_response(302)
            self.send_header('Location', '/login/login.html')
            self.send_header('Set-Cookie',
                             'xueji_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return

        if path in ('/', '/index.html'):
            if not self._authed():
                self._send(401, '<h1>401 未认证</h1>'.encode('utf-8'))
                return
            return super().do_GET()

        if path.startswith('/login'):
            return super().do_GET()

        # /assets/** 与其余静态资源：线上是免认证可达的，这里同样放行
        return super().do_GET()

    # ---------- POST /login ----------
    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if path != '/login':
            self._send(404, b'not found', 'text/plain; charset=utf-8')
            return

        n = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(n).decode('utf-8', 'replace')
        form = urllib.parse.parse_qs(raw, keep_blank_values=True)
        pw = (form.get('password') or [''])[0]

        # 真实网络错误：断开连接，不给任何响应
        if pw == 'drop':
            self.close_connection = True
            try:
                self.connection.close()
            except OSError:
                pass
            return

        if pw == 'flood':
            self._send(429, '太多次'.encode('utf-8'))
            return
        if pw == 'boom':
            self._send(500, '炸了'.encode('utf-8'))
            return
        if pw not in (OK_PASSWORD, 'slow'):
            self._send(401, '密码不对'.encode('utf-8'))
            return

        if pw == 'slow':
            time.sleep(1.6)

        body = ('<!DOCTYPE html><title>ok</title><p>登录成功，正在进入…'
                ).encode('utf-8')
        self._send(200, body, cookie='xueji_session=ok; Path=/; HttpOnly')


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    with Server(('127.0.0.1', PORT), Handler) as httpd:
        sys.stderr.write('[mock] 学迹 mock 登录服务已启动：http://127.0.0.1:%d/\n' % PORT)
        sys.stderr.write('[mock] 登录页：http://127.0.0.1:%d/login/login.html\n' % PORT)
        httpd.serve_forever()
