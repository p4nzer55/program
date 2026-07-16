"""
CloudWAF 新功能测试脚本
演示CIDR支持、区域访问控制、端口管理、URL级策略等功能
"""
import requests
import json
import time


class CloudWAFTester:
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
        self.api_url = f'{base_url}/api'
        self.session = requests.Session()
        # 登录
        self._login()

    def _login(self, username='admin', password='admin123'):
        """登录管理后台"""
        resp = self.session.post(
            f'{self.base_url}/admin/login',
            json={'username': username, 'password': password}
        )
        if resp.status_code == 200:
            print('✓ 登录成功')
        else:
            print(f'✗ 登录失败: {resp.text}')

    # ==================== CIDR格式支持测试 ====================

    def test_cidr_whitelist(self):
        """测试CIDR格式白名单"""
        print('\n' + '='*50)
        print('测试CIDR格式白名单')
        print('='*50)

        # 添加CIDR白名单
        data = {
            'ip': '192.168.1.0/24',
            'remark': '测试CIDR白名单'
        }
        resp = self.session.post(f'{self.api_url}/access/whitelist', json=data)
        print(f'✓ 添加CIDR白名单 192.168.1.0/24: {resp.status_code}')

        # 查看白名单
        resp = self.session.get(f'{self.api_url}/access/whitelist')
        whitelist = resp.json().get('data', [])
        cidr_items = [item for item in whitelist if item.get('is_cidr')]
        print(f'✓ 当前CIDR白名单数量: {len(cidr_items)}')
        for item in cidr_items:
            print(f'  - {item["ip"]}: {item["remark"]}')

    def test_cidr_blacklist(self):
        """测试CIDR格式黑名单"""
        print('\n' + '='*50)
        print('测试CIDR格式黑名单')
        print('='*50)

        # 添加CIDR黑名单
        data = {
            'ip': '10.0.0.0/8',
            'reason': '测试CIDR黑名单',
            'duration': 3600
        }
        resp = self.session.post(f'{self.api_url}/access/blacklist', json=data)
        print(f'✓ 添加CIDR黑名单 10.0.0.0/8: {resp.status_code}')

        # 查看黑名单
        resp = self.session.get(f'{self.api_url}/access/blacklist')
        blacklist = resp.json().get('data', [])
        cidr_items = [item for item in blacklist if item.get('is_cidr')]
        print(f'✓ 当前CIDR黑名单数量: {len(cidr_items)}')
        for item in cidr_items:
            print(f'  - {item["ip"]}: {item["reason"]}')

    # ==================== 区域访问控制测试 ====================

    def test_geo_access_control(self):
        """测试区域访问控制"""
        print('\n' + '='*50)
        print('测试区域访问控制')
        print('='*50)

        # 获取站点ID
        resp = self.session.get(f'{self.api_url}/sites')
        sites = resp.json().get('data', [])
        if not sites:
            print('✗ 没有找到站点')
            return

        site_id = sites[0]['id']
        print(f'✓ 使用站点: {sites[0]["name"]} (ID: {site_id})')

        # 添加区域黑名单
        data = {
            'rule_type': 'blacklist',
            'country_codes': ['US', 'UK', 'JP']
        }
        resp = self.session.post(f'{self.api_url}/sites/{site_id}/geo-rules', json=data)
        print(f'✓ 添加区域黑名单 (US, UK, JP): {resp.status_code}')

        # 添加区域白名单
        data = {
            'rule_type': 'whitelist',
            'country_codes': ['CN']
        }
        resp = self.session.post(f'{self.api_url}/sites/{site_id}/geo-rules', json=data)
        print(f'✓ 添加区域白名单 (CN): {resp.status_code}')

        # 查看区域规则
        resp = self.session.get(f'{self.api_url}/sites/{site_id}/geo-rules')
        rules = resp.json().get('data', [])
        print(f'✓ 当前区域规则数量: {len(rules)}')
        for rule in rules:
            print(f'  - {rule["rule_type"]}: {", ".join(rule["country_codes"])}')

        # 测试IP归属地查询
        test_ips = ['8.8.8.8', '114.114.114.114', '127.0.0.1']
        for ip in test_ips:
            resp = self.session.get(f'{self.api_url}/geo/country/{ip}')
            country = resp.json().get('data', {}).get('country', 'UNKNOWN')
            print(f'✓ IP {ip} 归属地: {country}')

    # ==================== 端口管理测试 ====================

    def test_port_management(self):
        """测试端口管理"""
        print('\n' + '='*50)
        print('测试端口管理')
        print('='*50)

        # 获取站点ID
        resp = self.session.get(f'{self.api_url}/sites')
        sites = resp.json().get('data', [])
        if not sites:
            print('✗ 没有找到站点')
            return

        site_id = sites[0]['id']

        # 添加端口
        ports = [80, 443, 8080]
        for port in ports:
            data = {'port': port, 'protocol': 'http'}
            resp = self.session.post(f'{self.api_url}/sites/{site_id}/ports', json=data)
            print(f'✓ 添加端口 {port}: {resp.status_code}')

        # 添加HTTPS端口
        data = {'port': 443, 'protocol': 'https'}
        resp = self.session.post(f'{self.api_url}/sites/{site_id}/ports', json=data)
        print(f'✓ 添加HTTPS端口 443: {resp.status_code}')

        # 查看站点端口
        resp = self.session.get(f'{self.api_url}/sites/{site_id}/ports')
        ports_data = resp.json().get('data', [])
        print(f'✓ 当前端口数量: {len(ports_data)}')
        for port in ports_data:
            print(f'  - {port["port"]} ({port["protocol"]}): {port["status"]}')

    # ==================== URL级策略测试 ====================

    def test_url_rules(self):
        """测试URL级防护策略"""
        print('\n' + '='*50)
        print('测试URL级防护策略')
        print('='*50)

        # 获取站点ID
        resp = self.session.get(f'{self.api_url}/sites')
        sites = resp.json().get('data', [])
        if not sites:
            print('✗ 没有找到站点')
            return

        site_id = sites[0]['id']

        # 添加URL规则
        url_rules = [
            {
                'path_pattern': r'^/api/.*',
                'rule_categories': ['sql_injection', 'xss'],
                'cc_enabled': True,
                'cc_rate': 100,
                'override_site_rule': False
            },
            {
                'path_pattern': r'^/admin/.*',
                'rule_categories': ['sql_injection', 'xss', 'command_injection'],
                'cc_enabled': True,
                'cc_rate': 30,
                'override_site_rule': True
            }
        ]

        for rule in url_rules:
            resp = self.session.post(
                f'{self.api_url}/sites/{site_id}/url-rules',
                json=rule
            )
            pattern = rule['path_pattern']
            print(f'✓ 添加URL规则 {pattern}: {resp.status_code}')

        # 查看URL规则
        resp = self.session.get(f'{self.api_url}/sites/{site_id}/url-rules')
        rules = resp.json().get('data', [])
        print(f'✓ 当前URL规则数量: {len(rules)}')
        for rule in rules:
            print(f'  - {rule["path_pattern"]}: {len(rule["rule_categories"])}个规则分类')

    # ==================== 维护模式测试 ====================

    def test_maintenance_mode(self):
        """测试维护模式"""
        print('\n' + '='*50)
        print('测试维护模式（一键关停）')
        print('='*50)

        # 获取站点ID
        resp = self.session.get(f'{self.api_url}/sites')
        sites = resp.json().get('data', [])
        if not sites:
            print('✗ 没有找到站点')
            return

        site_id = sites[0]['id']

        # 开启维护模式
        data = {
            'enabled': True,
            'message': '系统维护中，预计30分钟后恢复'
        }
        resp = self.session.post(
            f'{self.api_url}/sites/{site_id}/maintenance',
            json=data
        )
        print(f'✓ 开启维护模式: {resp.status_code}')

        # 关闭维护模式
        data = {'enabled': False}
        resp = self.session.post(
            f'{self.api_url}/sites/{site_id}/maintenance',
            json=data
        )
        print(f'✓ 关闭维护模式: {resp.status_code}')

    # ==================== 报告生成测试 ====================

    def test_report_generation(self):
        """测试报告生成"""
        print('\n' + '='*50)
        print('测试报告生成')
        print('='*50)

        # 获取站点ID
        resp = self.session.get(f'{self.api_url}/sites')
        sites = resp.json().get('data', [])
        if not sites:
            print('✗ 没有找到站点')
            return

        site_id = sites[0]['id']

        # 生成日报
        from datetime import datetime, timedelta

        # 生成今天的报告
        today = datetime.now().strftime('%Y-%m-%d')
        data = {
            'report_type': 'daily',
            'site_id': site_id,
            'date': today
        }
        resp = self.session.post(f'{self.api_url}/reports/generate', json=data)
        print(f'✓ 生成日报 ({today}): {resp.status_code}')

        # 获取报告列表
        resp = self.session.get(f'{self.api_url}/reports')
        reports = resp.json().get('data', [])
        print(f'✓ 当前报告数量: {len(reports)}')
        for report in reports[:3]:  # 只显示前3个
            print(f'  - {report["report_type"]}: {report["start_date"]}')

    # ==================== 运行所有测试 ====================

    def run_all_tests(self):
        """运行所有测试"""
        print('\n' + '='*60)
        print('CloudWAF 新功能测试')
        print('='*60)

        self.test_cidr_whitelist()
        self.test_cidr_blacklist()
        self.test_geo_access_control()
        self.test_port_management()
        self.test_url_rules()
        self.test_maintenance_mode()
        self.test_report_generation()

        print('\n' + '='*60)
        print('测试完成')
        print('='*60)


if __name__ == '__main__':
    try:
        tester = CloudWAFTester()
        tester.run_all_tests()
    except Exception as e:
        print(f'\n✗ 测试失败: {e}')
        print('请确保WAF服务已启动 (python cloudwaf/app.py)')