import time
import ipaddress
from datetime import datetime, timedelta
from models import IPBlacklist, IPWhitelist, db


class AccessControl:
    def __init__(self):
        self._blacklist_cache = {}
        self._whitelist_cache = {}
        self._cache_time = 0
        self._cache_ttl = 5

    def _refresh_cache(self):
        now = time.time()
        if now - self._cache_time < self._cache_ttl:
            return
        self._blacklist_cache = {}
        self._whitelist_cache = {}

        # 加载黑名单（支持CIDR）
        for item in IPBlacklist.query.all():
            if item.is_cidr:
                try:
                    self._blacklist_cache[item.ip] = {
                        'type': 'cidr',
                        'network': ipaddress.ip_network(item.ip, strict=False),
                        'expires_at': item.expires_at
                    }
                except ValueError:
                    continue
            else:
                self._blacklist_cache[item.ip] = {
                    'type': 'single',
                    'expires_at': item.expires_at
                }

        # 加载白名单（支持CIDR）
        for item in IPWhitelist.query.all():
            if item.is_cidr:
                try:
                    self._whitelist_cache[item.ip] = {
                        'type': 'cidr',
                        'network': ipaddress.ip_network(item.ip, strict=False)
                    }
                except ValueError:
                    continue
            else:
                self._whitelist_cache[item.ip] = {
                    'type': 'single'
                }

        self._cache_time = now

    def invalidate_cache(self):
        self._cache_time = 0

    def _is_in_list(self, ip, cache):
        """检查IP是否在列表中（支持CIDR）"""
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            return False

        # 先检查精确匹配
        if ip in cache:
            entry = cache[ip]
            if entry['type'] == 'single':
                return True
            # 如果是CIDR，也检查一下
            if entry['type'] == 'cidr' and ip_obj in entry['network']:
                return True

        # 检查CIDR匹配
        for key, entry in cache.items():
            if entry['type'] == 'cidr':
                if ip_obj in entry['network']:
                    return True

        return False

    def is_whitelisted(self, ip):
        self._refresh_cache()
        return self._is_in_list(ip, self._whitelist_cache)

    def is_blacklisted(self, ip):
        self._refresh_cache()

        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            return False

        # 检查黑名单（支持CIDR）
        for key, entry in self._blacklist_cache.items():
            if entry['type'] == 'single':
                if ip == key:
                    # 检查过期时间
                    expires = entry.get('expires_at')
                    if expires and expires < datetime.now():
                        continue
                    return True
            elif entry['type'] == 'cidr':
                if ip_obj in entry['network']:
                    # 检查过期时间
                    expires = entry.get('expires_at')
                    if expires and expires < datetime.now():
                        continue
                    return True

        return False

    def _is_cidr(self, ip_str):
        """检查是否为CIDR格式"""
        try:
            ipaddress.ip_network(ip_str, strict=False)
            return '/' in ip_str
        except ValueError:
            return False

    def add_blacklist(self, ip, reason=None, duration=None):
        expires = None
        if duration:
            expires = datetime.now() + timedelta(seconds=duration)
        is_cidr = self._is_cidr(ip)
        existing = IPBlacklist.query.filter_by(ip=ip).first()
        if existing:
            existing.reason = reason
            existing.expires_at = expires
            existing.is_cidr = is_cidr
        else:
            bl = IPBlacklist(ip=ip, reason=reason, expires_at=expires, is_cidr=is_cidr)
            db.session.add(bl)
        db.session.commit()
        self.invalidate_cache()

    def remove_blacklist(self, ip):
        IPBlacklist.query.filter_by(ip=ip).delete()
        db.session.commit()
        self.invalidate_cache()

    def add_whitelist(self, ip, remark=None):
        is_cidr = self._is_cidr(ip)
        existing = IPWhitelist.query.filter_by(ip=ip).first()
        if not existing:
            wl = IPWhitelist(ip=ip, remark=remark, is_cidr=is_cidr)
            db.session.add(wl)
            db.session.commit()
            self.invalidate_cache()

    def remove_whitelist(self, ip):
        IPWhitelist.query.filter_by(ip=ip).delete()
        db.session.commit()
        self.invalidate_cache()

    def list_blacklist(self):
        return [item.to_dict() for item in IPBlacklist.query.order_by(IPBlacklist.created_at.desc()).all()]

    def list_whitelist(self):
        return [item.to_dict() for item in IPWhitelist.query.order_by(IPWhitelist.created_at.desc()).all()]


access_control = AccessControl()
