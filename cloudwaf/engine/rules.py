import re
from models import Rule, db


DEFAULT_RULES = [
    {'name': 'SQLi-001', 'category': 'sql_injection', 'pattern': r"(?i)(\b(UNION(?:\s+ALL)?\s+SELECT)\b)", 'description': 'UNION SELECT 注入', 'severity': 'high'},
    {'name': 'SQLi-002', 'category': 'sql_injection', 'pattern': r"(?i)(\bOR\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+)", 'description': 'OR 1=1 恒真注入', 'severity': 'high'},
    {'name': 'SQLi-003', 'category': 'sql_injection', 'pattern': r"(?i)(\bAND\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+)", 'description': 'AND 1=1 注入', 'severity': 'high'},
    {'name': 'SQLi-004', 'category': 'sql_injection', 'pattern': r"(?i)(\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b.*\b(FROM|INTO|TABLE|DATABASE)\b)", 'description': 'SQL关键字组合', 'severity': 'high'},
    {'name': 'SQLi-005', 'category': 'sql_injection', 'pattern': r"(?i)(--\s|#\s|\/\*|\*\/)", 'description': 'SQL注释符', 'severity': 'medium'},
    {'name': 'SQLi-006', 'category': 'sql_injection', 'pattern': r"(?i)(\b(EXEC|EXECUTE|xp_cmdshell|sp_|xp_)\w*)", 'description': 'SQL存储过程/命令执行', 'severity': 'high'},
    {'name': 'SQLi-007', 'category': 'sql_injection', 'pattern': r"(?i)(['\"]\s*(OR|AND)\s+['\"].*['\"]\s*=\s*['\"])", 'description': '字符型SQL注入', 'severity': 'high'},
    {'name': 'SQLi-008', 'category': 'sql_injection', 'pattern': r"(?i)(\bWHERE\b.*\b(=|>|<|>=|<=|!=|LIKE)\b.*['\"])", 'description': 'WHERE子句注入', 'severity': 'medium'},
    {'name': 'SQLi-009', 'category': 'sql_injection', 'pattern': r"(?i)(\b(INFORMATION_SCHEMA|sys\.|mysql\.)\w*)", 'description': '系统表/库访问', 'severity': 'high'},
    {'name': 'SQLi-010', 'category': 'sql_injection', 'pattern': r"(?i)(\b(SLEEP|BENCHMARK|WAITFOR\s+DELAY)\s*\()", 'description': '时间盲注', 'severity': 'high'},
    {'name': 'SQLi-011', 'category': 'sql_injection', 'pattern': r"(?i)(\b(LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b)", 'description': '文件读写注入', 'severity': 'high'},
    {'name': 'XSS-001', 'category': 'xss', 'pattern': r"(?i)(<script[^>]*>.*?<\/script>)", 'description': 'Script标签注入', 'severity': 'high'},
    {'name': 'XSS-002', 'category': 'xss', 'pattern': r"(?i)(javascript\s*:)", 'description': 'JavaScript伪协议', 'severity': 'high'},
    {'name': 'XSS-003', 'category': 'xss', 'pattern': r"(?i)(on\w+\s*=)", 'description': '事件处理器注入', 'severity': 'high'},
    {'name': 'XSS-004', 'category': 'xss', 'pattern': r"(?i)(<iframe[^>]*>)", 'description': 'Iframe标签注入', 'severity': 'medium'},
    {'name': 'XSS-005', 'category': 'xss', 'pattern': r"(?i)(<img[^>]*\bonerror\b)", 'description': 'Img onerror注入', 'severity': 'high'},
    {'name': 'XSS-006', 'category': 'xss', 'pattern': r"(?i)(eval\s*\(|expression\s*\()", 'description': '代码执行函数', 'severity': 'high'},
    {'name': 'XSS-007', 'category': 'xss', 'pattern': r"(?i)(<[^>]+(?:src|href|action|data)\s*=\s*['\"]?[^>'\"]*(?:script|vbscript|data:))", 'description': '属性注入', 'severity': 'high'},
    {'name': 'CMD-001', 'category': 'command_injection', 'pattern': r"(?i)([;&|`$]\s*(?:ls|cat|whoami|id|uname|pwd|netstat|ps|kill|rm|cp|mv|wget|curl|nc|bash|sh|cmd|powershell)\b)", 'description': '命令注入运算符', 'severity': 'high'},
    {'name': 'CMD-002', 'category': 'command_injection', 'pattern': r"(?i)(\|\s*\||&&|\$\(|`[^`]+`)", 'description': '命令管道/替换', 'severity': 'high'},
    {'name': 'TRAV-001', 'category': 'directory_traversal', 'pattern': r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|\.\.%2f)", 'description': '目录遍历', 'severity': 'high'},
    {'name': 'TRAV-002', 'category': 'directory_traversal', 'pattern': r"(?i)(/etc/passwd|/etc/shadow|/etc/hosts|win\.ini|system32|boot\.ini)", 'description': '系统敏感文件', 'severity': 'high'},
    {'name': 'UPLOAD-001', 'category': 'file_upload', 'pattern': r"(?i)(\.(php|jsp|asp|aspx|exe|sh|py|pl|rb|bat|cmd)\s*$)", 'description': '危险文件类型上传', 'severity': 'high'},
    {'name': 'SENS-001', 'category': 'sensitive_path', 'pattern': r"(?i)(/(?:\.git|\.svn|\.hg|\.env|\.bash_history|\.ssh|web\.config|config\.inc|database\.yml|wp-config|phpinfo|adminer|phpmyadmin|mysql-admin)\b)", 'description': '敏感路径/文件访问', 'severity': 'medium'},
    {'name': 'SENS-002', 'category': 'sensitive_path', 'pattern': r"(?i)(/backup|\.bak|\.old|\.sql\s*$|\.zip\s*$|\.tar\s*$|\.rar\s*$|\.7z\s*$)", 'description': '备份/压缩文件', 'severity': 'medium'},
]


class RuleEngine:
    def __init__(self):
        self._rules_cache = None
        self._cache_valid = False

    def invalidate_cache(self):
        self._cache_valid = False

    def _load_rules(self):
        if self._cache_valid and self._rules_cache is not None:
            return self._rules_cache
        rules = Rule.query.filter_by(enabled=True).all()
        compiled = []
        for r in rules:
            try:
                compiled.append({
                    'id': r.id,
                    'name': r.name,
                    'category': r.category,
                    'pattern': re.compile(r.pattern, re.IGNORECASE | re.DOTALL),
                    'severity': r.severity,
                    'description': r.description
                })
            except re.error:
                continue
        self._rules_cache = compiled
        self._cache_valid = True
        return compiled

    def inspect_request(self, method, path, query_string, body, headers):
        targets = []
        targets.append(('path', path))
        if query_string:
            targets.append(('query', query_string))
        if body and isinstance(body, str):
            targets.append(('body', body))
        for key, value in headers.items():
            if key.lower() in ('user-agent', 'referer', 'cookie', 'x-forwarded-for'):
                targets.append((f'header:{key}', str(value)))
        rules = self._load_rules()
        for rule in rules:
            for source, content in targets:
                if not content:
                    continue
                m = rule['pattern'].search(content)
                if m:
                    return {
                        'detected': True,
                        'rule_name': rule['name'],
                        'category': rule['category'],
                        'severity': rule['severity'],
                        'description': rule['description'],
                        'matched_content': m.group(0),
                        'source': source
                    }
        return {'detected': False}

    @staticmethod
    def init_default_rules():
        existing = {r.name for r in Rule.query.all()}
        for r in DEFAULT_RULES:
            if r['name'] not in existing:
                rule = Rule(
                    name=r['name'],
                    category=r['category'],
                    pattern=r['pattern'],
                    description=r['description'],
                    severity=r['severity'],
                    enabled=True
                )
                db.session.add(rule)
        db.session.commit()


rule_engine = RuleEngine()
