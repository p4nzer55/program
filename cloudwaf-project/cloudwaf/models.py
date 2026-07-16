from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Site(db.Model):
    __tablename__ = 'sites'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(200), nullable=False)
    backend_url = db.Column(db.String(500), nullable=False)
    mode = db.Column(db.String(20), default='protection')
    status = db.Column(db.String(20), default='enabled')
    maintenance_mode = db.Column(db.Boolean, default=False)
    maintenance_message = db.Column(db.Text)
    bypass_enabled = db.Column(db.Boolean, default=False)
    bypass_original_dns = db.Column(db.String(500))
    force_https = db.Column(db.Boolean, default=False)
    connect_timeout = db.Column(db.Integer, default=10)
    read_timeout = db.Column(db.Integer, default=30)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'domain': self.domain,
            'backend_url': self.backend_url,
            'mode': self.mode,
            'status': self.status,
            'maintenance_mode': self.maintenance_mode,
            'maintenance_message': self.maintenance_message,
            'bypass_enabled': self.bypass_enabled,
            'bypass_original_dns': self.bypass_original_dns,
            'force_https': self.force_https,
            'connect_timeout': self.connect_timeout,
            'read_timeout': self.read_timeout,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class Rule(db.Model):
    __tablename__ = 'rules'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    pattern = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    severity = db.Column(db.String(20), default='medium')
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'pattern': self.pattern,
            'description': self.description,
            'severity': self.severity,
            'enabled': self.enabled,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class IPBlacklist(db.Model):
    __tablename__ = 'ip_blacklist'
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=False, unique=True)
    is_cidr = db.Column(db.Boolean, default=False)  # 是否为CIDR格式
    reason = db.Column(db.String(200))
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'is_cidr': self.is_cidr,
            'reason': self.reason,
            'expires_at': self.expires_at.strftime('%Y-%m-%d %H:%M:%S') if self.expires_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class IPWhitelist(db.Model):
    __tablename__ = 'ip_whitelist'
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=False, unique=True)
    is_cidr = db.Column(db.Boolean, default=False)  # 是否为CIDR格式
    remark = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'is_cidr': self.is_cidr,
            'remark': self.remark,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class AttackLog(db.Model):
    __tablename__ = 'attack_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    client_ip = db.Column(db.String(50))
    method = db.Column(db.String(10))
    path = db.Column(db.String(500))
    user_agent = db.Column(db.String(500))
    attack_type = db.Column(db.String(50))
    rule_name = db.Column(db.String(100))
    matched_content = db.Column(db.Text)
    severity = db.Column(db.String(20))
    action = db.Column(db.String(20))
    request_data = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'client_ip': self.client_ip,
            'method': self.method,
            'path': self.path,
            'user_agent': self.user_agent,
            'attack_type': self.attack_type,
            'rule_name': self.rule_name,
            'matched_content': self.matched_content,
            'severity': self.severity,
            'action': self.action
        }


class SystemConfig(db.Model):
    __tablename__ = 'system_config'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(200))

    def to_dict(self):
        return {
            'key': self.key,
            'value': self.value,
            'description': self.description
        }


class SitePort(db.Model):
    """站点端口管理"""
    __tablename__ = 'site_ports'
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    protocol = db.Column(db.String(10), default='http')
    status = db.Column(db.String(20), default='enabled')
    created_at = db.Column(db.DateTime, default=datetime.now)

    site = db.relationship('Site', backref=db.backref('ports', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'port': self.port,
            'protocol': self.protocol,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class URLRule(db.Model):
    """URL级防护策略"""
    __tablename__ = 'url_rules'
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    path_pattern = db.Column(db.String(500), nullable=False)
    rule_categories = db.Column(db.JSON, default=list)
    cc_enabled = db.Column(db.Boolean, default=True)
    cc_rate = db.Column(db.Integer, default=60)
    cc_window = db.Column(db.Integer, default=60)
    override_site_rule = db.Column(db.Boolean, default=False)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    site = db.relationship('Site', backref=db.backref('url_rules', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'path_pattern': self.path_pattern,
            'rule_categories': self.rule_categories or [],
            'cc_enabled': self.cc_enabled,
            'cc_rate': self.cc_rate,
            'cc_window': self.cc_window,
            'override_site_rule': self.override_site_rule,
            'enabled': self.enabled,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class GeoRule(db.Model):
    """区域访问控制"""
    __tablename__ = 'geo_rules'
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    rule_type = db.Column(db.String(20), nullable=False)  # whitelist/blacklist
    country_codes = db.Column(db.Text, nullable=False)  # 逗号分隔: CN,US,JP
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    site = db.relationship('Site', backref=db.backref('geo_rules', lazy=True))

    def get_country_list(self):
        """获取国家代码列表"""
        return [c.strip() for c in self.country_codes.split(',') if c.strip()]

    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'rule_type': self.rule_type,
            'country_codes': self.get_country_list(),
            'enabled': self.enabled,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class ScheduleTask(db.Model):
    """定时开关站点任务"""
    __tablename__ = 'schedule_tasks'
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    task_type = db.Column(db.String(20), nullable=False)  # shutdown/startup
    cron_expression = db.Column(db.String(100))
    enabled = db.Column(db.Boolean, default=True)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)

    site = db.relationship('Site', backref=db.backref('schedule_tasks', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'task_type': self.task_type,
            'cron_expression': self.cron_expression,
            'enabled': self.enabled,
            'last_run': self.last_run.strftime('%Y-%m-%d %H:%M:%S') if self.last_run else None,
            'next_run': self.next_run.strftime('%Y-%m-%d %H:%M:%S') if self.next_run else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class Report(db.Model):
    """防护报告记录"""
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(20), nullable=False)  # daily/weekly/monthly
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    data = db.Column(db.JSON, nullable=False)
    file_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.now)

    site = db.relationship('Site', backref=db.backref('reports', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'report_type': self.report_type,
            'site_id': self.site_id,
            'site_name': self.site.name if self.site else None,
            'start_date': self.start_date.strftime('%Y-%m-%d %H:%M:%S'),
            'end_date': self.end_date.strftime('%Y-%m-%d %H:%M:%S'),
            'file_path': self.file_path,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
