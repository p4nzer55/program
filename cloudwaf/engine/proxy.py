import requests
from urllib.parse import unquote
from flask import request, Response, session
from engine.rules import rule_engine
from engine.access_control import access_control
from engine.rate_limiter import rate_limiter
from engine.logger import attack_logger
from config import Config
from models import Site


CATEGORY_NAMES = {
    'sql_injection': 'SQL注入',
    'xss': 'XSS攻击',
    'command_injection': '命令注入',
    'directory_traversal': '目录遍历',
    'file_upload': '恶意文件上传',
    'sensitive_path': '敏感路径访问',
}


class WAFProxy:
    def __init__(self):
        self.backend_url = Config.DEFAULT_BACKEND
        self.mode = Config.WAF_MODE

    def _get_client_ip(self):
        xff = request.headers.get('X-Forwarded-For', '')
        if xff:
            return xff.split(',')[0].strip()
        return request.remote_addr or '127.0.0.1'

    def _get_site_mode(self):
        host = request.host.split(':')[0]
        site = Site.query.filter_by(domain=host, status='enabled').first()
        if site:
            return site.mode, site.backend_url
        return self.mode, self.backend_url

    def _block_response(self, reason=''):
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>WAF 拦截</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: "Microsoft YaHei", Arial, sans-serif; background: #f5f7fa; margin: 0; padding: 50px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #fff; padding: 40px; border-radius: 8px;
                     box-shadow: 0 2px 12px rgba(0,0,0,.1); text-align: center; }}
        h1 {{ color: #e74c3c; margin: 0 0 20px; }}
        .code {{ color: #999; font-size: 14px; margin-bottom: 30px; }}
        .reason {{ background: #fdf0ef; color: #c0392b; padding: 15px; border-radius: 4px;
                   margin: 20px 0; text-align: left; word-break: break-all; }}
        .footer {{ margin-top: 30px; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>访问被拦截</h1>
        <div class="code">HTTP 403 - Forbidden</div>
        <p>您的请求被云WAF安全防护系统拦截</p>
        <div class="reason"><strong>拦截原因：</strong>{reason}</div>
        <div class="footer">CloudWAF 安全防护系统</div>
    </div>
</body>
</html>'''
        return Response(html, status=403, content_type='text/html; charset=utf-8')

    def _get_request_body(self):
        content_type = request.content_type or ''
        if 'multipart/form-data' in content_type:
            return '[FILE UPLOAD]'
        try:
            return request.get_data(as_text=True)[:5000]
        except Exception:
            return ''

    def process(self, path):
        client_ip = self._get_client_ip()
        mode, backend_url = self._get_site_mode()

        if mode == 'forward':
            return self._proxy_request(backend_url, path)

        if access_control.is_whitelisted(client_ip):
            return self._proxy_request(backend_url, path)

        if access_control.is_blacklisted(client_ip):
            attack_logger.log(
                client_ip=client_ip,
                method=request.method,
                path=request.full_path,
                user_agent=request.headers.get('User-Agent', ''),
                attack_type='blacklist',
                rule_name='IP黑名单',
                matched_content=client_ip,
                severity='high',
                action='block'
            )
            return self._block_response('IP在黑名单中')

        if rate_limiter.check_cc(
            client_ip,
            rate_limit=Config.CC_RATE_LIMIT,
            window=Config.CC_WINDOW,
            block_duration=Config.CC_BLOCK_DURATION
        ):
            attack_logger.log(
                client_ip=client_ip,
                method=request.method,
                path=request.full_path,
                user_agent=request.headers.get('User-Agent', ''),
                attack_type='cc_attack',
                rule_name='CC防护',
                matched_content=f'Request rate exceeded',
                severity='high',
                action='block'
            )
            return self._block_response('请求频率过高，已被临时封禁')

        query_string = unquote(request.query_string.decode('utf-8', errors='ignore'))
        decoded_path = unquote(path)
        body = self._get_request_body() if request.method in ('POST', 'PUT', 'PATCH') else ''
        headers = dict(request.headers)

        result = rule_engine.inspect_request(
            method=request.method,
            path=decoded_path,
            query_string=query_string,
            body=body,
            headers=headers
        )

        if result['detected']:
            category_name = CATEGORY_NAMES.get(result['category'], result['category'])
            attack_logger.log(
                client_ip=client_ip,
                method=request.method,
                path=request.full_path,
                user_agent=request.headers.get('User-Agent', ''),
                attack_type=result['category'],
                rule_name=result['rule_name'],
                matched_content=result['matched_content'],
                severity=result['severity'],
                action='block' if mode == 'protection' else 'detect',
                request_data=body or query_string
            )
            if mode == 'protection':
                return self._block_response(
                    f'{category_name} ({result["rule_name"]}) - {result["description"]}'
                )

        resp = self._proxy_request(backend_url, path)

        rate_limiter.check_scan(
            client_ip,
            status_code=resp.status_code,
            threshold=Config.SCAN_404_THRESHOLD,
            window=Config.SCAN_WINDOW,
            block_duration=Config.SCAN_BLOCK_DURATION
        )

        return resp

    def _proxy_request(self, backend_url, path):
        url = f"{backend_url.rstrip('/')}/{path.lstrip('/')}"
        if request.query_string:
            url += '?' + request.query_string.decode('utf-8', errors='ignore')

        headers = {}
        skip_headers = {'host', 'content-length', 'connection', 'accept-encoding'}
        for key, value in request.headers:
            if key.lower() not in skip_headers:
                headers[key] = value

        client_ip = self._get_client_ip()
        headers['X-Forwarded-For'] = client_ip
        headers['X-Real-IP'] = client_ip

        try:
            resp = requests.request(
                method=request.method,
                url=url,
                headers=headers,
                data=request.get_data(),
                allow_redirects=False,
                timeout=30,
                stream=True
            )
            excluded_headers = {'content-encoding', 'transfer-encoding', 'connection', 'keep-alive'}
            response_headers = {k: v for k, v in resp.headers.items()
                                if k.lower() not in excluded_headers}
            return Response(
                resp.iter_content(chunk_size=1024),
                status=resp.status_code,
                headers=response_headers,
                content_type=resp.headers.get('Content-Type')
            )
        except requests.exceptions.RequestException as e:
            return Response(
                f'Backend error: {str(e)}',
                status=502,
                content_type='text/plain; charset=utf-8'
            )


waf_proxy = WAFProxy()
