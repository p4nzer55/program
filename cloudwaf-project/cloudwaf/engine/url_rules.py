"""
URL级防护策略模块
用于针对特定URL路径配置独立的防护规则
"""
import re
from models import db, URLRule


class URLRuleManager:
    """URL规则管理器"""

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
        rules = URLRule.query.filter_by(enabled=True).all()
        for rule in rules:
            if rule.site_id not in self._cache:
                self._cache[rule.site_id] = []

            try:
                compiled_pattern = re.compile(rule.path_pattern)
                self._cache[rule.site_id].append({
                    'id': rule.id,
                    'pattern': compiled_pattern,
                    'pattern_str': rule.path_pattern,
                    'rule_categories': rule.rule_categories or [],
                    'cc_enabled': rule.cc_enabled,
                    'cc_rate': rule.cc_rate,
                    'cc_window': rule.cc_window,
                    'override_site_rule': rule.override_site_rule
                })
            except re.error:
                continue

        self._cache_time = now

    def invalidate_cache(self):
        """使缓存失效"""
        self._cache_time = 0

    def get_matched_rules(self, site_id, path):
        """
        获取匹配路径的URL规则

        返回: 匹配的规则列表（按创建时间倒序）
        """
        self._refresh_cache()

        if site_id not in self._cache:
            return []

        matched = []
        for rule in self._cache[site_id]:
            if rule['pattern'].search(path):
                matched.append(rule)

        return matched

    def get_effective_config(self, site_id, path):
        """
        获取路径的有效配置

        返回: {
            'rule_categories': [...],  # 启用的规则分类
            'cc_rate': 60,
            'cc_window': 60,
            'override_site_rule': False
        }
        """
        rules = self.get_matched_rules(site_id, path)

        # 找到第一个override_site_rule=True的规则
        override_rule = None
        for rule in rules:
            if rule['override_site_rule']:
                override_rule = rule
                break

        if override_rule:
            return {
                'rule_categories': override_rule['rule_categories'],
                'cc_rate': override_rule['cc_rate'],
                'cc_window': override_rule['cc_window'],
                'override_site_rule': True
            }

        # 没有覆盖规则，返回空配置（使用站点默认配置）
        return {
            'rule_categories': [],
            'cc_rate': None,
            'cc_window': None,
            'override_site_rule': False
        }

    def add_rule(self, site_id, path_pattern, rule_categories=None, cc_enabled=True,
                 cc_rate=60, cc_window=60, override_site_rule=False):
        """添加URL规则"""
        rule = URLRule(
            site_id=site_id,
            path_pattern=path_pattern,
            rule_categories=rule_categories or [],
            cc_enabled=cc_enabled,
            cc_rate=cc_rate,
            cc_window=cc_window,
            override_site_rule=override_site_rule,
            enabled=True
        )
        db.session.add(rule)
        db.session.commit()
        self.invalidate_cache()
        return rule

    def update_rule(self, rule_id, **kwargs):
        """更新URL规则"""
        rule = URLRule.query.get_or_404(rule_id)

        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        db.session.commit()
        self.invalidate_cache()
        return rule

    def delete_rule(self, rule_id):
        """删除URL规则"""
        rule = URLRule.query.get_or_404(rule_id)
        db.session.delete(rule)
        db.session.commit()
        self.invalidate_cache()

    def get_site_rules(self, site_id):
        """获取站点所有URL规则"""
        return URLRule.query.filter_by(site_id=site_id).order_by(
            URLRule.created_at.desc()
        ).all()


url_rule_manager = URLRuleManager()