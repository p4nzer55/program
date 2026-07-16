import time
from datetime import datetime, timedelta
from models import IPBlacklist, IPWhitelist, db


class AccessControl:
    def __init__(self):
        self._blacklist_cache = {}
        self._whitelist_cache = set()
        self._cache_time = 0
        self._cache_ttl = 5

    def _refresh_cache(self):
        now = time.time()
        if now - self._cache_time < self._cache_ttl:
            return
        self._blacklist_cache = {}
        self._whitelist_cache = set()
        bl = IPBlacklist.query.all()
        for item in bl:
            self._blacklist_cache[item.ip] = item.expires_at
        wl = IPWhitelist.query.all()
        for item in wl:
            self._whitelist_cache.add(item.ip)
        self._cache_time = now

    def invalidate_cache(self):
        self._cache_time = 0

    def is_whitelisted(self, ip):
        self._refresh_cache()
        return ip in self._whitelist_cache

    def is_blacklisted(self, ip):
        self._refresh_cache()
        if ip not in self._blacklist_cache:
            return False
        expires = self._blacklist_cache[ip]
        if expires and expires < datetime.now():
            return False
        return True

    def add_blacklist(self, ip, reason=None, duration=None):
        expires = None
        if duration:
            expires = datetime.now() + timedelta(seconds=duration)
        existing = IPBlacklist.query.filter_by(ip=ip).first()
        if existing:
            existing.reason = reason
            existing.expires_at = expires
        else:
            bl = IPBlacklist(ip=ip, reason=reason, expires_at=expires)
            db.session.add(bl)
        db.session.commit()
        self.invalidate_cache()

    def remove_blacklist(self, ip):
        IPBlacklist.query.filter_by(ip=ip).delete()
        db.session.commit()
        self.invalidate_cache()

    def add_whitelist(self, ip, remark=None):
        existing = IPWhitelist.query.filter_by(ip=ip).first()
        if not existing:
            wl = IPWhitelist(ip=ip, remark=remark)
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
