"""
区域访问控制模块 - GeoIP
用于根据IP的地理位置进行访问控制
"""
import re
from models import db, Site, GeoRule
from datetime import datetime


# 简化的IP归属地映射（实际项目中应使用geoip2等库）
# 这里为了演示使用内置的IP段映射
# 格式: {ip网络: 国家代码}
PRIVATE_IP_COUNTRY_MAP = {
    '10.0.0.0/8': 'CN',
    '172.16.0.0/12': 'CN',
    '192.168.0.0/16': 'CN',
    '127.0.0.0/8': 'CN',
}


# 中国大陆常见IP段（示例）
CHINA_IP_RANGES = [
    '1.0.0.0/8',
    '14.0.0.0/8',
    '27.0.0.0/8',
    '36.0.0.0/8',
    '39.0.0.0/8',
    '42.0.0.0/8',
    '49.0.0.0/8',
    '58.0.0.0/8',
    '59.0.0.0/8',
    '60.0.0.0/8',
    '61.0.0.0/8',
    '101.0.0.0/8',
    '103.0.0.0/8',
    '106.0.0.0/8',
    '110.0.0.0/8',
    '111.0.0.0/8',
    '112.0.0.0/8',
    '113.0.0.0/8',
    '114.0.0.0/8',
    '115.0.0.0/8',
    '116.0.0.0/8',
    '117.0.0.0/8',
    '118.0.0.0/8',
    '119.0.0.0/8',
    '120.0.0.0/8',
    '121.0.0.0/8',
    '122.0.0.0/8',
    '123.0.0.0/8',
    '124.0.0.0/8',
    '125.0.0.0/8',
]


class GeoAccessControl:
    """区域访问控制"""

    def __init__(self):
        self._cache = {}
        self._cache_time = 0
        self._cache_ttl = 10

    def _refresh_cache(self):
        """刷新缓存"""
        import time
        now = time.time()
        if now - self._cache_time < self._cache_ttl:
            return

        self._cache = {}
        rules = GeoRule.query.filter_by(enabled=True).all()
        for rule in rules:
            if rule.site_id not in self._cache:
                self._cache[rule.site_id] = {'whitelist': [], 'blacklist': []}

            countries = rule.get_country_list()
            if rule.rule_type == 'whitelist':
                self._cache[rule.site_id]['whitelist'].extend(countries)
            else:
                self._cache[rule.site_id]['blacklist'].extend(countries)

        self._cache_time = now

    def invalidate_cache(self):
        """使缓存失效"""
        self._cache_time = 0

    def get_ip_country(self, ip):
        """
        获取IP归属国家代码
        返回: 国家代码 (如 'CN', 'US', 'JP') 或 'UNKNOWN'
        """
        try:
            import ipaddress
            ip_obj = ipaddress.ip_address(ip)

            # 检查私有IP
            for network, country in PRIVATE_IP_COUNTRY_MAP.items():
                if ip_obj in ipaddress.ip_network(network, strict=False):
                    return country

            # 检查是否在中国IP段
            for network in CHINA_IP_RANGES:
                if ip_obj in ipaddress.ip_network(network, strict=False):
                    return 'CN'

            # 检查特定IP（用于演示）
            demo_ips = {
                '8.8.8.8': 'US',      # Google DNS
                '1.1.1.1': 'US',      # Cloudflare DNS
                '208.67.222.222': 'US',  # OpenDNS
                '13.107.21.200': 'US',  # Microsoft
            }

            if str(ip) in demo_ips:
                return demo_ips[str(ip)]

            # 其他IP根据第一段判断（简化处理）
            first_octet = int(str(ip).split('.')[0])
            if 1 <= first_octet <= 100:
                return 'US'  # 假设大部分是北美
            elif 101 <= first_octet <= 126:
                return 'CN'
            elif 128 <= first_octet <= 191:
                return 'US'
            elif 192 <= first_octet <= 223:
                return 'EU'

            return 'UNKNOWN'

        except Exception:
            return 'UNKNOWN'

    def check_access(self, site_id, ip):
        """
        检查IP是否允许访问

        返回: (是否允许, 原因)
        """
        self._refresh_cache()

        # 站点未配置区域控制，默认允许
        if site_id not in self._cache:
            return True, None

        site_rules = self._cache[site_id]
        country = self.get_ip_country(ip)

        # 白名单模式：只允许白名单中的国家
        if site_rules['whitelist']:
            if country not in site_rules['whitelist']:
                return False, f"IP所在地区 ({country}) 不在白名单中"

        # 黑名单模式：阻止黑名单中的国家
        if site_rules['blacklist']:
            if country in site_rules['blacklist']:
                return False, f"IP所在地区 ({country}) 在黑名单中"

        return True, None

    def add_rule(self, site_id, rule_type, country_codes):
        """添加区域访问规则"""
        rule = GeoRule(
            site_id=site_id,
            rule_type=rule_type,
            country_codes=','.join(country_codes),
            enabled=True
        )
        db.session.add(rule)
        db.session.commit()
        self.invalidate_cache()
        return rule

    def update_rule(self, rule_id, rule_type=None, country_codes=None, enabled=None):
        """更新区域访问规则"""
        rule = GeoRule.query.get_or_404(rule_id)
        if rule_type:
            rule.rule_type = rule_type
        if country_codes:
            rule.country_codes = ','.join(country_codes)
        if enabled is not None:
            rule.enabled = enabled
        db.session.commit()
        self.invalidate_cache()
        return rule

    def delete_rule(self, rule_id):
        """删除区域访问规则"""
        rule = GeoRule.query.get_or_404(rule_id)
        db.session.delete(rule)
        db.session.commit()
        self.invalidate_cache()

    def get_site_rules(self, site_id):
        """获取站点的区域访问规则"""
        return GeoRule.query.filter_by(site_id=site_id).order_by(GeoRule.created_at.desc()).all()


geo_access_control = GeoAccessControl()