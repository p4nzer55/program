import requests
from urllib.parse import unquote
from flask import request, Response, session
from engine.rules import rule_engine
from engine.access_control import access_control
from engine.rate_limiter import rate_limiter
from engine.logger import attack_logger
from engine.geo_access import geo_access_control
from engine.port_manager import port_manager
from engine.url_rules import url_rule_manager
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
            return site.mode, site.backend_url, site
        return self.mode, self.backend_url, None

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

    def _maintenance_response(self, message):
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>站点维护中</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: "Microsoft YaHei", Arial, sans-serif; background: #f0f4f8; margin: 0; padding: 50px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #fff; padding: 50px; border-radius: 12px;
                     box-shadow: 0 4px 20px rgba(0,0,0,.1); text-align: center; }}
        .icon {{ font-size: 64px; margin-bottom: 20px; }}
        h1 {{ color: #3498db; margin: 0 0 20px; font-size: 28px; }}
        .message {{ color: #666; font-size: 16px; line-height: 1.6; margin: 20px 0; }}
        .footer {{ margin-top: 40px; color: #999; font-size: 12px; border-top: 1px solid #eee; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">🔧</div>
        <h1>站点维护中</h1>
        <div class="message">
            <p>{message or '系统正在维护升级中，请稍后再访问'}</p>
            <p>如有疑问，请联系站点管理员</p>
        </div>
        <div class="footer">CloudWAF 安全防护系统 - 维护模式</div>
    </div>
</body>
</html>'''
        return Response(html, status=503, content_type='text/html; charset=utf-8')

    def _port_unavailable_response(self, available_ports, protocol):
        ports_str = ', '.join([f'{p}({protocol})' for p in available_ports]) if available_ports else '无'
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>端口未配置</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: "Microsoft YaHei", Arial, sans-serif; background: #f5f7fa; margin: 0; padding: 50px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #fff; padding: 40px; border-radius: 8px;
                     box-shadow: 0 2px 12px rgba(0,0,0,.1); text-align: center; }}
        h1 {{ color: #f39c12; margin: 0 0 20px; }}
        .code {{ color: #999; font-size: 14px; margin-bottom: 30px; }}
        .reason {{ background: #fef5e7; color: #d68910; padding: 15px; border-radius: 4px;
                   margin: 20px 0; text-align: left; word-break: break-all; }}
        .available {{ background: #f8f9fa; color: #666; padding: 15px; border-radius: 4px;
                     margin: 20px 0; text-align: left; }}
        .footer {{ margin-top: 30px; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>端口未配置</h1>
        <div class="code">HTTP 422 - Unprocessable Entity</div>
        <p>您访问的端口未在WAF中配置</p>
        <div class="reason"><strong>访问端口：</strong>{request.environ.get('SERVER_PORT', 80)}</div>
        <div class="available"><strong>可用端口：</strong>{ports_str}</div>
        <p>请联系管理员添加端口配置</p>
        <div class="footer">CloudWAF 安全防护系统</div>
    </div>
</body>
</html>'''
        return Response(html, status=422, content_type='text/html; charset=utf-8')

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
        mode, backend_url, site = self._get_site_mode()

        # 检查是否启用回源模式（绕过WAF）
        if site and site.bypass_enabled:
            return self._proxy_request(backend_url, path)

        # 转发模式直接转发
        if mode == 'forward' or (site and site.mode == 'forward'):
            return self._proxy_request(backend_url, path)

        # 白名单直接放行
        if access_control.is_whitelisted(client_ip):
            return self._proxy_request(backend_url, path)

        # 黑名单拦截
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

        # 维护模式拦截
        if site and site.maintenance_mode:
            return self._maintenance_response(site.maintenance_message or '站点维护中')

        # 端口检查（如果站点配置了端口）
        if site:
            # 获取请求端口
            request_port = request.environ.get('SERVER_PORT', 80)
            if ':' in request.host:
                request_port = int(request.host.split(':')[1])

            is_https = request.is_secure
            protocol = 'https' if is_https else 'http'

            port_available, available_ports = port_manager.is_port_available(
                site.id, int(request_port), protocol
            )

            if not port_available:
                return self._port_unavailable_response(available_ports, protocol)

            # 区域访问控制检查
            geo_allowed, geo_reason = geo_access_control.check_access(site.id, client_ip)
            if not geo_allowed:
                attack_logger.log(
                    client_ip=client_ip,
                    method=request.method,
                    path=request.full_path,
                    user_agent=request.headers.get('User-Agent', ''),
                    attack_type='geo_block',
                    rule_name='区域访问控制',
                    matched_content=geo_reason,
                    severity='medium',
                    action='block'
                )
                return self._block_response(f'区域访问限制: {geo_reason}')

        # URL级策略检查
        cc_rate_limit = Config.CC_RATE_LIMIT
        cc_window = Config.CC_WINDOW

        if site:
            url_config = url_rule_manager.get_effective_config(site.id, path)

            # 如果URL规则覆盖了站点规则
            if url_config['override_site_rule']:
                # 如果指定了规则分类，只检查这些分类
                effective_categories = url_config['rule_categories']

            # CC防护配置
            if url_config['cc_rate']:
                cc_rate_limit = url_config['cc_rate']
            if url_config['cc_window']:
                cc_window = url_config['cc_window']

        if rate_limiter.check_cc(
            client_ip,
            rate_limit=cc_rate_limit,
            window=cc_window,
            block_duration=Config.CC_BLOCK_DURATION
        ):
            attack_logger.log(
                client_ip=client_ip,
                method=request.method,
                path=request.full_path,
                user_agent=request.headers.get('User-Agent', ''),
                attack_type='cc_attack',
                rule_name='CC防护',
                matched_content=f'Request rate exceeded ({cc_rate_limit}req/{cc_window}s)',
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
