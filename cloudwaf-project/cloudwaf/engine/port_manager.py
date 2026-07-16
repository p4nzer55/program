"""
端口管理模块
用于管理站点端口配置，访问未配置端口返回422错误
"""
from models import db, Site, SitePort


class PortManager:
    """端口管理器"""

    def __init__(self):
        self._cache = {}
        self._cache_time = 0
        self._cache_ttl = 30

    def _refresh_cache(self):
        """刷新缓存"""
        import time
        now = time.time()
        if now - self._cache_time < self._cache_ttl:
            return

        self._cache = {}
        for port in SitePort.query.filter_by(status='enabled').all():
            key = (port.site_id, port.port, port.protocol)
            self._cache[key] = port

        self._cache_time = now

    def invalidate_cache(self):
        """使缓存失效"""
        self._cache_time = 0

    def is_port_available(self, site_id, port, protocol='http'):
        """
        检查端口是否可用

        返回: (是否可用, 可用端口列表)
        """
        self._refresh_cache()

        available_ports = []
        for (sid, p, proto) in self._cache.keys():
            if sid == site_id and proto == protocol:
                available_ports.append(p)

        # 如果没有配置端口，允许所有端口访问（向后兼容）
        if not available_ports:
            return True, []

        return port in available_ports, available_ports

    def add_port(self, site_id, port, protocol='http'):
        """添加端口"""
        existing = SitePort.query.filter_by(
            site_id=site_id, port=port, protocol=protocol
        ).first()

        if existing:
            if existing.status != 'enabled':
                existing.status = 'enabled'
                db.session.commit()
                self.invalidate_cache()
            return existing

        port_entry = SitePort(
            site_id=site_id,
            port=port,
            protocol=protocol,
            status='enabled'
        )
        db.session.add(port_entry)
        db.session.commit()
        self.invalidate_cache()
        return port_entry

    def remove_port(self, site_id, port, protocol='http'):
        """删除端口"""
        SitePort.query.filter_by(
            site_id=site_id, port=port, protocol=protocol
        ).delete()
        db.session.commit()
        self.invalidate_cache()

    def get_site_ports(self, site_id):
        """获取站点所有端口"""
        return SitePort.query.filter_by(site_id=site_id).order_by(
            SitePort.protocol, SitePort.port
        ).all()

    def update_port_status(self, site_id, port, protocol, status):
        """更新端口状态"""
        port_entry = SitePort.query.filter_by(
            site_id=site_id, port=port, protocol=protocol
        ).first()

        if port_entry:
            port_entry.status = status
            db.session.commit()
            self.invalidate_cache()
            return port_entry

        return None


port_manager = PortManager()