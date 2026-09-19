#!/usr/bin/env python3
"""Real Wings startup on disposable Linux/Docker state; no live panel or games."""
import http.server
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def request(url, token=None):
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=2) as res:
            return res.status, json.load(res)
    except urllib.error.HTTPError as err:
        return err.code, None


def run(binary, bad_panel=False):
    token = secrets.token_hex(32)
    token_id = secrets.token_hex(8)
    network = 'wings-smoke-' + secrets.token_hex(8)
    calls = []
    unexpected = []

    class Panel(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Never log request headers or generated credentials.

        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond()

        def respond(self):
            path = urllib.parse.urlsplit(self.path).path
            if self.headers.get('Authorization') != f'Bearer {token_id}.{token}':
                unexpected.append('incorrect panel authentication')
                self.send_error(401)
                return
            calls.append((self.command, path))
            if (self.command, path) == ('GET', '/api/remote/servers'):
                payload = b'not-json' if bad_panel else json.dumps({
                    'data': [], 'meta': {'current_page': 1, 'last_page': 1, 'total': 0},
                }).encode()
            elif (self.command, path) == ('POST', '/api/remote/servers/reset'):
                payload = b'{}'
            else:
                unexpected.append(f'{self.command} {path}')
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    with tempfile.TemporaryDirectory(prefix='wings-service-') as directory:
        root = Path(directory)
        api_port, sftp_port = port(), port()
        panel = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Panel)
        thread = threading.Thread(target=panel.serve_forever, daemon=True)
        thread.start()
        proc = None
        created_network = False
        try:
            subprocess.run(['docker', 'network', 'create', '--internal', network],
                           check=True, stdout=subprocess.DEVNULL, timeout=20)
            created_network = True
            cfg = {
                'uuid': 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee',
                'token_id': token_id, 'token': token,
                'remote': f'http://127.0.0.1:{panel.server_port}',
                'remote_query': {'timeout': 3},
                'api': {'host': '127.0.0.1', 'port': api_port, 'ssl': {'enabled': False}},
                'system': {
                    'root_directory': str(root / 'data'), 'data': str(root / 'volumes'),
                    'log_directory': str(root / 'logs'), 'tmp_directory': str(root / 'tmp'),
                    'archive_directory': str(root / 'archives'),
                    'backup_directory': str(root / 'backups'), 'timezone': 'UTC',
                    'enable_log_rotate': False,
                    'user': {'rootless': {'enabled': True},
                             'passwd': {'directory': str(root / 'passwd')}},
                    'machine_id': {'directory': str(root / 'machine-id')},
                    'sftp': {'bind_address': '127.0.0.1', 'bind_port': sftp_port},
                },
                'docker': {'network': {'name': network, 'network_mode': network, 'IPv6': False}},
            }
            config_path = root / 'config.yml'
            config_path.write_text(json.dumps(cfg))  # JSON is valid YAML.
            config_path.chmod(0o600)
            with (root / 'output').open('w') as log:
                proc = subprocess.Popen([binary, '--config', str(config_path)],
                                        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    if proc.poll() is not None:
                        break
                    try:
                        status, system = request(f'http://127.0.0.1:{api_port}/api/system', token)
                        if status == 200:
                            if bad_panel:
                                raise AssertionError('invalid panel data reached readiness')
                            assert system['os'] == 'linux', system
                            assert system['cpu_count'] > 0 and system['architecture'], system
                            break
                    except (OSError, urllib.error.URLError):
                        pass
                    time.sleep(0.1)
                text = (root / 'output').read_text()
                if bad_panel:
                    assert proc.poll() is not None and proc.returncode != 0, 'invalid panel did not fail startup'
                    assert 'failed to load server configurations' in text, 'wrong startup failure'
                else:
                    assert proc.poll() is None, 'service exited before readiness'
                    assert time.monotonic() < deadline, 'service readiness deadline exceeded'
                    assert request(f'http://127.0.0.1:{api_port}/api/system')[0] == 401
                    status, servers = request(f'http://127.0.0.1:{api_port}/api/servers', token)
                    assert status == 200 and servers == [], (status, servers)
                    with socket.create_connection(('127.0.0.1', sftp_port), timeout=3) as sock:
                        assert sock.recv(256).startswith(b'SSH-2.0-'), 'missing SSH banner'
                    while ('POST', '/api/remote/servers/reset') not in calls and time.monotonic() < deadline:
                        time.sleep(0.1)
                    assert ('POST', '/api/remote/servers/reset') in calls, 'panel reset missing'
                    assert 'configured system user successfully' in text
                    assert 'configuring internal webserver' in text
                assert ('GET', '/api/remote/servers') in calls
                assert not unexpected, unexpected
                assert token not in text and token_id not in text, 'credentials leaked to daemon log'
                print('invalid panel rejected' if bad_panel else 'authenticated API, empty inventory, panel reset and SFTP ready')
        except BaseException:
            if (root / 'output').exists():
                text = (root / 'output').read_text().replace(token, '[redacted]').replace(token_id, '[redacted]')
                print(text[-12000:], file=sys.stderr)
            raise
        finally:
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=5)
            panel.shutdown()
            panel.server_close()
            thread.join(timeout=3)
            if created_network:
                subprocess.run(['docker', 'network', 'rm', network], check=True,
                               stdout=subprocess.DEVNULL, timeout=20)
            for endpoint in (api_port, sftp_port):
                with socket.socket() as sock:
                    assert sock.connect_ex(('127.0.0.1', endpoint)) != 0, 'service listener survived cleanup'


if __name__ == '__main__':
    # Convert runner cancellation to ordinary unwinding so finally performs teardown.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    executable = str(Path(sys.argv[1]).resolve())
    run(executable)
    run(executable, bad_panel=True)
