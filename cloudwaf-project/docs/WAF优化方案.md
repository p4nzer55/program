# CloudWAF 优化方案

> 基于「玄武盾」云WAF产品的设计理念，对现有CloudWAF系统进行功能增强和架构优化

---

## 📋 优化概览

| 类别 | 玄武盾功能 | 现有状态 | 优化计划 |
|------|-----------|---------|---------|
| **基础防护** | 三种模式切换 | ✅ 已实现 | 无需改动 |
| **基础防护** | CC防护 | ✅ 已实现 | 增强可视化 |
| **基础防护** | 防扫描 | ✅ 已实现 | 增加误报处理 |
| **访问控制** | IP黑白名单 | ✅ 已实现 | 支持CIDR格式 |
| **访问控制** | 区域访问控制 | ❌ 未实现 | 新增功能 |
| **策略管理** | URL级策略 | ❌ 未实现 | 新增功能 |
| **运维功能** | 一键关停 | ❌ 未实现 | 新增功能 |
| **运维功能** | 回源/回切 | ❌ 未实现 | 新增功能 |
| **运维功能** | 定时开关站点 | ❌ 未实现 | 新增功能 |
| **日志分析** | 日志查询/下载 | ✅ 已实现 | 增强导出功能 |
| **日志分析** | 报告导出 | ❌ 未实现 | 新增功能 |
| **高级配置** | 端口管理 | ❌ 未实现 | 新增功能 |
| **高级配置** | XFF配置 | ✅ 已实现 | 增加配置界面 |
| **高级配置** | HTTP→HTTPS跳转 | ❌ 未实现 | 新增功能 |
| **高级配置** | 超时设置 | ❌ 未实现 | 新增功能 |
| **响应码** | 422端口错误 | ❌ 未实现 | 新增功能 |

---

## 🎯 优化方案详解

### 1. 访问控制增强

#### 1.1 支持CIDR格式的IP范围

**玄武盾设计：**
- 支持单IP：`1.2.3.4`
- 支持IP段：`1.2.3.0/24`
- 支持IPv6

**优化实现：**
```python
# engine/access_control.py 新增IP段匹配功能
import ipaddress

def is_ip_in_range(self, ip, cidr_list):
    ip_obj = ipaddress.ip_address(ip)
    for cidr in cidr_list:
        if ip_obj in ipaddress.ip_network(cidr, strict=False):
            return True
    return False
```

#### 1.2 区域访问控制（GeoIP）

**玄武盾设计：**
- 按国家/地区限制访问
- 支持白名单/黑名单模式

**优化实现：**
- 集成 `geoip2` 库实现IP归属地查询
- 支持按国家代码配置（如：CN、US、JP）
- 管理界面新增"区域控制"模块

---

### 2. 策略管理增强

#### 2.1 URL级防护策略

**玄武盾设计：**
- 站点级策略：影响整站
- URL级策略：仅影响指定URL路径
- 支持策略优先级覆盖

**优化实现：**
```python
# 新增 URLRule 模型
class URLRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'))
    path_pattern = db.Column(db.String(500))  # URL匹配模式
    rule_categories = db.Column(db.JSON)  # 启用的规则分类
    cc_enabled = db.Column(db.Boolean, default=True)
    cc_rate = db.Column(db.Integer, default=60)
    override_site_rule = db.Column(db.Boolean, default=False)
```

#### 2.2 端口管理

**玄武盾设计：**
- 站点需要显式添加端口才能访问
- 访问未配置端口返回422错误

**优化实现：**
```python
# 新增 SitePort 模型
class SitePort(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'))
    port = db.Column(db.Integer)
    protocol = db.Column(db.String(10))  # http/https
    status = db.Column(db.String(20), default='enabled')
```

---

### 3. 运维功能新增

#### 3.1 一键关停

**玄武盾设计：**
- 快速关闭站点防护，应对紧急情况
- 即时生效，秒级响应

**优化实现：**
```python
# Site 模型新增字段
class Site(db.Model):
    # ... 现有字段
    maintenance_mode = db.Column(db.Boolean, default=False)  # 维护模式
    maintenance_message = db.Column(db.Text)  # 维护提示信息
```

#### 3.2 回源/回切功能

**玄武盾设计：**
- **回源**：通过DNS修改，流量直接绕过WAF到源站
- **回切**：通过DNS修改，流量重新走WAF防护
- 用于源站故障或维护时的应急处理

**优化实现：**
```python
# Site 模型新增字段
class Site(db.Model):
    # ... 现有字段
    bypass_enabled = db.Column(db.Boolean, default=False)  # 绕过WAF
    bypass_original_dns = db.Column(db.String(500))  # 原DNS记录
```

#### 3.3 定时开关站点

**玄武盾设计：**
- 支持定时关闭站点（如夜间维护）
- 支持定时开启站点

**优化实现：**
```python
# 新增 ScheduleTask 模型
class ScheduleTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'))
    task_type = db.Column(db.String(20))  # shutdown/startup
    cron_expression = db.Column(db.String(100))
    enabled = db.Column(db.Boolean, default=True)
```

---

### 4. 日志分析增强

#### 4.1 报告导出功能

**玄武盾设计：**
- 支持导出日报、月报、年报
- 支持自定义模板（脱敏处理）
- 支持多站点汇总报告

**优化实现：**
```python
# 新增报告导出模块
class ReportGenerator:
    def generate_daily_report(self, site_id, date):
        """生成单站点日报"""

    def generate_monthly_report(self, site_id, year, month):
        """生成单站点月报"""

    def generate_summary_report(self, start_date, end_date, site_ids=None):
        """生成汇总报告"""

    def export_to_excel(self, report_data):
        """导出为Excel格式"""

    def export_to_pdf(self, report_data):
        """导出为PDF格式"""
```

#### 4.2 日志下载功能

**玄武盾设计：**
- 支持按时间范围下载日志
- 支持按筛选条件下载

**优化实现：**
- 后端新增日志流式下载接口
- 前端添加下载按钮

---

### 5. 高级配置新增

#### 5.1 HTTP→HTTPS自动跳转

**玄武盾设计：**
- 强制HTTP请求跳转到HTTPS
- 可针对单个站点配置

**优化实现：**
```python
# Site 模型新增字段
class Site(db.Model):
    # ... 现有字段
    force_https = db.Column(db.Boolean, default=False)
```

#### 5.2 超时设置

**玄武盾设计：**
- 可配置后端响应超时时间
- 可配置连接超时时间

**优化实现：**
```python
# Config 模块
class Config:
    # ... 现有配置
    CONNECT_TIMEOUT = 10  # 连接超时（秒）
    READ_TIMEOUT = 30     # 读取超时（秒）

# Site 模型新增字段
class Site(db.Model):
    # ... 现有字段
    connect_timeout = db.Column(db.Integer, default=10)
    read_timeout = db.Column(db.Integer, default=30)
```

#### 5.3 WebSocket支持

**玄武盾设计：**
- 支持WebSocket连接代理
- 自动处理协议升级

**优化实现：**
```python
# engine/proxy.py 增强
def _proxy_request(self, backend_url, path):
    # ... 现有代码
    if request.headers.get('Upgrade') == 'websocket':
        # WebSocket代理逻辑
        return self._proxy_websocket(backend_url, path)
```

---

### 6. 响应码优化

#### 6.1 422端口错误

**玄武盾设计：**
- 访问未配置端口时返回422错误
- 提示信息包含正确的端口列表

**优化实现：**
```python
def _port_unavailable_response(self, available_ports):
    return Response(
        json.dumps({
            'code': 422,
            'msg': '端口未配置',
            'available_ports': available_ports
        }),
        status=422,
        content_type='application/json'
    )
```

#### 6.2 拦截页面美化

**玄武盾设计：**
- 美观的403拦截页面
- 显示拦截原因和联系方式

**现有代码已实现，可进一步美化。**

---

## 🗂️ 数据库架构调整

```sql
-- 站点表新增字段
ALTER TABLE sites ADD COLUMN maintenance_mode BOOLEAN DEFAULT FALSE;
ALTER TABLE sites ADD COLUMN maintenance_message TEXT;
ALTER TABLE sites ADD COLUMN bypass_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE sites ADD COLUMN bypass_original_dns VARCHAR(500);
ALTER TABLE sites ADD COLUMN force_https BOOLEAN DEFAULT FALSE;
ALTER TABLE sites ADD COLUMN connect_timeout INTEGER DEFAULT 10;
ALTER TABLE sites ADD COLUMN read_timeout INTEGER DEFAULT 30;

-- URL级策略表
CREATE TABLE url_rules (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES sites(id),
    path_pattern VARCHAR(500),
    rule_categories JSON,
    cc_enabled BOOLEAN DEFAULT TRUE,
    cc_rate INTEGER DEFAULT 60,
    override_site_rule BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 站点端口表
CREATE TABLE site_ports (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES sites(id),
    port INTEGER,
    protocol VARCHAR(10),
    status VARCHAR(20) DEFAULT 'enabled',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 区域访问控制表
CREATE TABLE geo_rules (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES sites(id),
    rule_type VARCHAR(20),  -- whitelist/blacklist
    country_codes TEXT,     -- 逗号分隔的国家代码
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 定时任务表
CREATE TABLE schedule_tasks (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES sites(id),
    task_type VARCHAR(20),
    cron_expression VARCHAR(100),
    enabled BOOLEAN DEFAULT TRUE,
    last_run DATETIME,
    next_run DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🚀 实施优先级

### P0（高优先级 - 核心功能）
1. ✅ 三种模式切换（已有）
2. ✅ CC防护（已有）
3. ✅ 防扫描（已有）
4. ✅ 黑白名单（已有）
5. 🔲 **CIDR格式支持** - 增强访问控制

### P1（中优先级 - 重要功能）
6. 🔲 **区域访问控制** - 地理位置过滤
7. 🔲 **URL级策略** - 细粒度防护
8. 🔲 **端口管理** - 422错误处理
9. 🔲 **一键关停** - 应急响应
10. 🔲 **报告导出** - 毕业设计亮点

### P2（低优先级 - 增强功能）
11. 🔲 回源/回切功能
12. 🔲 定时开关站点
13. 🔲 HTTP→HTTPS跳转
14. 🔲 超时设置
15. 🔲 WebSocket支持

---

## 📝 实现建议

对于毕业设计，建议优先实现以下功能以确保答辩效果：

1. **CIDR格式支持** - 实现简单，功能实用
2. **区域访问控制** - 可以集成GeoIP库，展示地图可视化效果
3. **URL级策略** - 展示细粒度控制能力
4. **端口管理 + 422错误** - 展示严格的安全控制
5. **报告导出** - 生成PDF/Excel报告，答辩时可以直接展示
6. **一键关停** - 操作简单，演示效果好

这些功能代码量适中，且易于演示，非常适合毕业设计。