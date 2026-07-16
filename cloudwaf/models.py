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
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'domain': self.domain,
            'backend_url': self.backend_url,
            'mode': self.mode,
            'status': self.status,
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
    reason = db.Column(db.String(200))
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'reason': self.reason,
            'expires_at': self.expires_at.strftime('%Y-%m-%d %H:%M:%S') if self.expires_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class IPWhitelist(db.Model):
    __tablename__ = 'ip_whitelist'
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=False, unique=True)
    remark = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
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
