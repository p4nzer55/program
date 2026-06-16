-- ============================================
-- WAF/Security Chatbot Database Schema
-- Compatible with SQLite and MySQL
-- ============================================

-- Enable foreign key constraints (SQLite specific, ignored by MySQL)
PRAGMA foreign_keys = ON;

-- ============================================
-- 1. PROBLEM DATABASE
-- Stores all WAF/security related problems
-- ============================================

-- Problems table - Main storage for problems
CREATE TABLE IF NOT EXISTS problems (
  -- Primary identification
  problem_id VARCHAR(64) PRIMARY KEY,
  slug VARCHAR(128) UNIQUE NOT NULL,  -- URL-friendly identifier

  -- Content
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  category_id VARCHAR(64),

  -- Search optimization
  keywords TEXT,  -- JSON array of keywords
  embedding_vector BLOB,  -- For semantic search (SQLite: BLOB, MySQL: VARBINARY)

  -- Priority and status
  priority INTEGER DEFAULT 3,  -- 1=low, 2=medium, 3=normal, 4=high, 5=critical
  status VARCHAR(20) DEFAULT 'active',  -- active, deprecated, draft, archived

  -- Performance metrics
  frequency INTEGER DEFAULT 0,  -- Number of times matched
  success_rate DECIMAL(3,2) DEFAULT 0.00,  -- Calculated from feedback

  -- Metadata
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(64),
  updated_by VARCHAR(64),

  -- Full-text search (MySQL specific, will be handled separately for SQLite)
  content_search TEXT GENERATED ALWAYS AS (question || ' ' || answer) STORED
);

-- Categories table - Problem categorization
CREATE TABLE IF NOT EXISTS categories (
  category_id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  description TEXT,
  parent_id VARCHAR(64),  -- For hierarchical categories
  sort_order INTEGER DEFAULT 0,
  icon VARCHAR(50),  -- Icon identifier for UI

  FOREIGN KEY (parent_id) REFERENCES categories(category_id) ON DELETE SET NULL
);

-- Problem versions table - Track answer history
CREATE TABLE IF NOT EXISTS problem_versions (
  version_id INTEGER PRIMARY KEY AUTOINCREMENT,
  problem_id VARCHAR(64) NOT NULL,
  version_number INTEGER NOT NULL,

  -- Version content
  question TEXT,
  answer TEXT NOT NULL,
  keywords TEXT,
  change_reason TEXT,
  change_type VARCHAR(20) DEFAULT 'update',  -- create, update, rollback

  -- Version metadata
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(64),

  -- Approval workflow
  status VARCHAR(20) DEFAULT 'approved',  -- draft, pending, approved, rejected
  approved_by VARCHAR(64),
  approved_at DATETIME,

  FOREIGN KEY (problem_id) REFERENCES problems(problem_id) ON DELETE CASCADE
);

-- Problem tags table - Flexible tagging system
CREATE TABLE IF NOT EXISTS problem_tags (
  tag_id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  color VARCHAR(7) DEFAULT '#3B82F6',  -- Hex color for UI
  description TEXT
);

-- Problem-tag junction table
CREATE TABLE IF NOT EXISTS problem_tag_relations (
  problem_id VARCHAR(64) NOT NULL,
  tag_id VARCHAR(64) NOT NULL,
  tagged_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (problem_id, tag_id),
  FOREIGN KEY (problem_id) REFERENCES problems(problem_id) ON DELETE CASCADE,
  FOREIGN KEY (tag_id) REFERENCES problem_tags(tag_id) ON DELETE CASCADE
);

-- Related problems table - Link related issues
CREATE TABLE IF NOT EXISTS related_problems (
  problem_id VARCHAR(64) NOT NULL,
  related_problem_id VARCHAR(64) NOT NULL,
  relationship_type VARCHAR(20) DEFAULT 'related',  -- related, prerequisite, followup
  strength INTEGER DEFAULT 1,  -- 1-5, strength of relationship

  PRIMARY KEY (problem_id, related_problem_id),
  FOREIGN KEY (problem_id) REFERENCES problems(problem_id) ON DELETE CASCADE,
  FOREIGN KEY (related_problem_id) REFERENCES problems(problem_id) ON DELETE CASCADE
);

-- ============================================
-- 2. ANSWER DATABASE
-- Stores solutions with version history
-- ============================================

-- Answer templates table - Reusable answer components
CREATE TABLE IF NOT EXISTS answer_templates (
  template_id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  content TEXT NOT NULL,
  variables TEXT,  -- JSON array of variable names
  category_id VARCHAR(64),

  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(64),

  FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL
);

-- Answer history detailed tracking
CREATE TABLE IF NOT EXISTS answer_history (
  history_id INTEGER PRIMARY KEY AUTOINCREMENT,
  problem_id VARCHAR(64) NOT NULL,
  version_id INTEGER NOT NULL,

  old_answer TEXT,
  new_answer TEXT,
  diff_summary TEXT,  -- Summary of changes
  word_count_change INTEGER,
  estimated_reading_time INTEGER,  -- seconds

  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(64),
  approval_status VARCHAR(20) DEFAULT 'pending',

  FOREIGN KEY (problem_id) REFERENCES problems(problem_id) ON DELETE CASCADE,
  FOREIGN KEY (version_id) REFERENCES problem_versions(version_id)
);

-- Answer quality metrics
CREATE TABLE IF NOT EXISTS answer_quality_metrics (
  metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
  problem_id VARCHAR(64) NOT NULL,
  version_id INTEGER NOT NULL,

  -- Quality indicators
  clarity_score DECIMAL(3,2),  -- 0-1, calculated from text analysis
  completeness_score DECIMAL(3,2),
  accuracy_score DECIMAL(3,2),  -- Based on user feedback
  technical_depth_score DECIMAL(3,2),

  -- Readability metrics
  flesch_reading_ease DECIMAL(5,2),
  flesch_kincaid_grade DECIMAL(4,2),
  average_sentence_length DECIMAL(5,2),
  average_word_length DECIMAL(3,2),

  calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (problem_id) REFERENCES problems(problem_id) ON DELETE CASCADE,
  FOREIGN KEY (version_id) REFERENCES problem_versions(version_id)
);

-- ============================================
-- 3. FEEDBACK DATABASE
-- Stores user feedback for continuous improvement
-- ============================================

-- Query logs table - Track all user queries
CREATE TABLE IF NOT EXISTS query_logs (
  query_id VARCHAR(64) PRIMARY KEY,
  user_session_id VARCHAR(64),  -- Track conversation context
  user_id VARCHAR(64),  -- Optional user identification

  -- Query details
  query_text TEXT NOT NULL,
  normalized_query TEXT,  -- For frequency analysis

  -- Matching details
  matched_problem_id VARCHAR(64),
  match_score DECIMAL(5,2),  -- 0-100, confidence score
  match_method VARCHAR(20),  -- keyword, semantic, hybrid, fallback
  answer_provided TEXT,

  -- Response details
  response_time_ms INTEGER,  -- Performance metric
  response_source VARCHAR(20),  -- database, cache, fallback

  -- Query metadata
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  ip_address VARCHAR(45),  -- IPv4 or IPv6
  user_agent TEXT,
  referrer TEXT,

  FOREIGN KEY (matched_problem_id) REFERENCES problems(problem_id) ON DELETE SET NULL
);

-- Feedback table - User ratings and comments
CREATE TABLE IF NOT EXISTS feedback (
  feedback_id VARCHAR(64) PRIMARY KEY,
  query_id VARCHAR(64) NOT NULL,

  -- Rating
  rating INTEGER NOT NULL,  -- -1=negative, 0=neutral, 1=positive, 2=very_positive
  rating_type VARCHAR(20),  -- thumbs_up_down, stars, helpful

  -- Comments
  feedback_text TEXT,
  feedback_type VARCHAR(20),  -- correction, suggestion, praise, complaint

  -- Action taken
  action_required BOOLEAN DEFAULT FALSE,
  action_status VARCHAR(20) DEFAULT 'pending',  -- pending, in_progress, resolved, ignored
  action_taken_by VARCHAR(64),
  action_taken_at DATETIME,
  action_notes TEXT,

  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (query_id) REFERENCES query_logs(query_id) ON DELETE CASCADE
);

-- Answer suggestions table - User-proposed corrections
CREATE TABLE IF NOT EXISTS answer_suggestions (
  suggestion_id VARCHAR(64) PRIMARY KEY,
  query_id VARCHAR(64) NOT NULL,
  problem_id VARCHAR(64) NOT NULL,

  -- Suggestion details
  suggested_answer TEXT NOT NULL,
  suggested_keywords TEXT,  -- JSON array
  reason TEXT,

  -- Workflow
  status VARCHAR(20) DEFAULT 'pending',  -- pending, reviewing, approved, rejected
  reviewed_by VARCHAR(64),
  reviewed_at DATETIME,
  review_notes TEXT,

  -- Impact if approved
  estimated_impact VARCHAR(20),  -- low, medium, high

  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (query_id) REFERENCES query_logs(query_id) ON DELETE CASCADE,
  FOREIGN KEY (problem_id) REFERENCES problems(problem_id) ON DELETE CASCADE
);

-- Feedback aggregation table - Pre-computed metrics
CREATE TABLE IF NOT EXISTS feedback_aggregates (
  aggregate_id VARCHAR(64) PRIMARY KEY,
  problem_id VARCHAR(64) NOT NULL,

  -- Aggregated metrics
  total_feedbacks INTEGER DEFAULT 0,
  positive_count INTEGER DEFAULT 0,
  negative_count INTEGER DEFAULT 0,
  neutral_count INTEGER DEFAULT 0,
  average_rating DECIMAL(3,2),
  confidence_interval DECIMAL(5,2),

  -- Recent trends
  last_7_day_avg DECIMAL(3,2),
  last_30_day_avg DECIMAL(3,2),

  calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (problem_id) REFERENCES problems(problem_id) ON DELETE CASCADE
);

-- ============================================
-- 4. ANALYTICS DATABASE
-- Track question frequency, success rate, etc.
-- ============================================

-- Query frequency table - Track how often questions are asked
CREATE TABLE IF NOT EXISTS query_frequency (
  frequency_id INTEGER PRIMARY KEY AUTOINCREMENT,
  normalized_query TEXT NOT NULL,
  original_query TEXT NOT NULL,  -- Most common original form

  -- Frequency metrics
  total_count INTEGER DEFAULT 0,
  unique_users INTEGER DEFAULT 0,
  last_7_days INTEGER DEFAULT 0,
  last_30_days INTEGER DEFAULT 0,

  -- Match status
  matched_problem_id VARCHAR(64),
  match_rate DECIMAL(5,2),  -- Percentage of queries that got matched

  -- Trending
  trending_score DECIMAL(5,2),  -- Calculated trending score
  is_trending BOOLEAN DEFAULT FALSE,

  -- Time windows
  first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (matched_problem_id) REFERENCES problems(problem_id) ON DELETE SET NULL
);

-- Problem usage analytics
CREATE TABLE IF NOT EXISTS problem_usage_analytics (
  usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
  problem_id VARCHAR(64) NOT NULL,
  date DATE NOT NULL,

  -- Daily metrics
  query_count INTEGER DEFAULT 0,
  unique_sessions INTEGER DEFAULT 0,
  avg_match_score DECIMAL(5,2),

  -- User engagement
  avg_response_time_ms INTEGER,
  follow_up_rate DECIMAL(3,2),  -- Percentage of queries that led to follow-up

  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (problem_id) REFERENCES problems(problem_id) ON DELETE CASCADE,
  UNIQUE(problem_id, date)
);

-- Performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
  metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
  metric_type VARCHAR(50) NOT NULL,  -- response_time, match_rate, user_satisfaction, etc.
  metric_name VARCHAR(100) NOT NULL,
  metric_value DECIMAL(10,4),

  -- Dimensions
  dimension_key VARCHAR(100),
  dimension_value VARCHAR(100),

  -- Time period
  period_start DATETIME NOT NULL,
  period_end DATETIME NOT NULL,

  -- Metadata
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- System health table - Track overall system performance
CREATE TABLE IF NOT EXISTS system_health (
  health_id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

  -- Query metrics
  total_queries INTEGER DEFAULT 0,
  matched_queries INTEGER DEFAULT 0,
  unmatched_queries INTEGER DEFAULT 0,
  match_rate DECIMAL(5,2),

  -- Response metrics
  avg_response_time_ms INTEGER,
  p50_response_time_ms INTEGER,
  p95_response_time_ms INTEGER,
  p99_response_time_ms INTEGER,

  -- Satisfaction metrics
  total_feedback INTEGER DEFAULT 0,
  positive_feedback_rate DECIMAL(3,2),
  active_issues INTEGER DEFAULT 0
);

-- Search analytics - Understand how users search
CREATE TABLE IF NOT EXISTS search_analytics (
  search_id INTEGER PRIMARY KEY AUTOINCREMENT,
  query_id VARCHAR(64) NOT NULL,

  -- Search terms
  search_terms TEXT NOT NULL,
  normalized_terms TEXT,

  -- Results
  results_count INTEGER DEFAULT 0,
  clicked_result_id VARCHAR(64),
  click_position INTEGER,

  -- User behavior
  time_to_first_click_ms INTEGER,
  refined BOOLEAN DEFAULT FALSE,  -- Did user refine their search?
  abandoned BOOLEAN DEFAULT FALSE,  -- Did user abandon without clicking?

  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (query_id) REFERENCES query_logs(query_id) ON DELETE CASCADE
);

-- ============================================
-- 5. INTEGRATION TABLES
-- Support for integration with chatbot system
-- ============================================

-- User sessions table - Track conversation context
CREATE TABLE IF NOT EXISTS user_sessions (
  session_id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64),
  started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  ended_at DATETIME,

  -- Session metrics
  query_count INTEGER DEFAULT 0,
  unique_problems_accessed INTEGER DEFAULT 0,
  avg_satisfaction DECIMAL(3,2),

  -- Metadata
  platform VARCHAR(50),  -- web, mobile, api
  device_info TEXT
);

-- Session problems junction - Track problems accessed in session
CREATE TABLE IF NOT EXISTS session_problems (
  session_id VARCHAR(64) NOT NULL,
  problem_id VARCHAR(64) NOT NULL,
  access_order INTEGER NOT NULL,
  access_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  was_helpful BOOLEAN,

  PRIMARY KEY (session_id, problem_id, access_order),
  FOREIGN KEY (session_id) REFERENCES user_sessions(session_id) ON DELETE CASCADE,
  FOREIGN KEY (problem_id) REFERENCES problems(problem_id) ON DELETE CASCADE
);

-- Integration logs - For external system integration
CREATE TABLE IF NOT EXISTS integration_logs (
  log_id INTEGER PRIMARY KEY AUTOINCREMENT,
  integration_name VARCHAR(50) NOT NULL,
  event_type VARCHAR(50) NOT NULL,

  -- Event data
  event_data TEXT,  -- JSON
  correlation_id VARCHAR(64),

  -- Status
  status VARCHAR(20) DEFAULT 'success',  -- success, failure, retrying
  error_message TEXT,

  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Problem table indexes
CREATE INDEX IF NOT EXISTS idx_problems_category ON problems(category_id);
CREATE INDEX IF NOT EXISTS idx_problems_status ON problems(status);
CREATE INDEX IF NOT EXISTS idx_problems_priority ON problems(priority);
CREATE INDEX IF NOT EXISTS idx_problems_slug ON problems(slug);
CREATE INDEX IF NOT EXISTS idx_problems_updated ON problems(updated_at);

-- Problem versions indexes
CREATE INDEX IF NOT EXISTS idx_problem_versions_problem ON problem_versions(problem_id);
CREATE INDEX IF NOT EXISTS idx_problem_versions_status ON problem_versions(status);

-- Query logs indexes
CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_query_logs_problem ON query_logs(matched_problem_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_session ON query_logs(user_session_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_normalized ON query_logs(normalized_query);

-- Feedback indexes
CREATE INDEX IF NOT EXISTS idx_feedback_query ON feedback(query_id);
CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(action_status);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating);

-- Query frequency indexes
CREATE INDEX IF NOT EXISTS idx_query_frequency_normalized ON query_frequency(normalized_query);
CREATE INDEX IF NOT EXISTS idx_query_frequency_trending ON query_frequency(is_trending);
CREATE INDEX IF NOT EXISTS idx_query_frequency_last_seen ON query_frequency(last_seen);

-- Problem usage analytics indexes
CREATE INDEX IF NOT EXISTS idx_problem_usage_problem ON problem_usage_analytics(problem_id);
CREATE INDEX IF NOT EXISTS idx_problem_usage_date ON problem_usage_analytics(date);

-- Performance metrics indexes
CREATE INDEX IF NOT EXISTS idx_performance_metrics_type ON performance_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_period ON performance_metrics(period_start, period_end);

-- System health indexes
CREATE INDEX IF NOT EXISTS idx_system_health_timestamp ON system_health(timestamp);

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- View: Problems with feedback summary
CREATE VIEW IF NOT EXISTS v_problems_with_feedback AS
SELECT
  p.*,
  c.name as category_name,
  fa.total_feedbacks,
  fa.average_rating,
  fa.last_7_day_avg as recent_rating
FROM problems p
LEFT JOIN categories c ON p.category_id = c.category_id
LEFT JOIN feedback_aggregates fa ON p.problem_id = fa.problem_id;

-- View: High frequency problems
CREATE VIEW IF NOT EXISTS v_high_frequency_problems AS
SELECT
  p.*,
  pu.query_count,
  pu.date as last_query_date
FROM problems p
INNER JOIN problem_usage_analytics pu ON p.problem_id = pu.problem_id
WHERE pu.query_count > 5
ORDER BY pu.query_count DESC;

-- View: Low performing problems
CREATE VIEW IF NOT EXISTS v_low_performing_problems AS
SELECT
  p.*,
  pu.query_count,
  fa.average_rating
FROM problems p
INNER JOIN problem_usage_analytics pu ON p.problem_id = pu.problem_id
LEFT JOIN feedback_aggregates fa ON p.problem_id = fa.problem_id
WHERE (fa.average_rating < 0.5 OR fa.average_rating IS NULL) AND pu.query_count >= 3;

-- View: Recent queries
CREATE VIEW IF NOT EXISTS v_recent_queries AS
SELECT
  ql.*,
  p.question as matched_question,
  p.category_id,
  f.rating as user_rating,
  f.feedback_text as user_feedback
FROM query_logs ql
LEFT JOIN problems p ON ql.matched_problem_id = p.problem_id
LEFT JOIN feedback f ON ql.query_id = f.query_id
ORDER BY ql.timestamp DESC;

-- View: Optimization suggestions
CREATE VIEW IF NOT EXISTS v_optimization_suggestions AS
SELECT
  p.problem_id,
  p.question,
  p.success_rate,
  p.frequency,
  pu.query_count as recent_queries,
  fa.average_rating,
  CASE
    WHEN p.frequency > 10 AND p.success_rate < 0.7 THEN 'High frequency, low success rate'
    WHEN pu.query_count > 5 AND (fa.average_rating < 0.5 OR fa.average_rating IS NULL) THEN 'Frequently used, low rating'
    WHEN p.frequency = 0 AND p.updated_at < datetime('now', '-30 days') THEN 'Unused for 30+ days'
    WHEN p.status = 'draft' THEN 'Draft needs review'
    ELSE 'Monitor'
  END as suggestion_type,
  CASE
    WHEN p.frequency > 10 AND p.success_rate < 0.7 THEN 3
    WHEN pu.query_count > 5 AND (fa.average_rating < 0.5 OR fa.average_rating IS NULL) THEN 2
    WHEN p.frequency = 0 AND p.updated_at < datetime('now', '-30 days') THEN 1
    ELSE 0
  END as priority_score
FROM problems p
LEFT JOIN problem_usage_analytics pu ON p.problem_id = pu.problem_id AND pu.date = date('now')
LEFT JOIN feedback_aggregates fa ON p.problem_id = fa.problem_id
WHERE (p.frequency > 10 AND p.success_rate < 0.7)
   OR (pu.query_count > 5 AND (fa.average_rating < 0.5 OR fa.average_rating IS NULL))
   OR (p.frequency = 0 AND p.updated_at < datetime('now', '-30 days'))
   OR p.status = 'draft'
ORDER BY priority_score DESC;

-- ============================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================

-- Trigger: Update problem timestamp on update
CREATE TRIGGER IF NOT EXISTS trg_problems_updated_at
AFTER UPDATE ON problems
FOR EACH ROW
BEGIN
  UPDATE problems SET updated_at = CURRENT_TIMESTAMP WHERE problem_id = OLD.problem_id;
END;

-- Trigger: Update query frequency on new query
CREATE TRIGGER IF NOT EXISTS trg_query_frequency_update
AFTER INSERT ON query_logs
FOR EACH ROW
BEGIN
  INSERT OR REPLACE INTO query_frequency (
    frequency_id, normalized_query, original_query, total_count,
    last_seen, matched_problem_id
  )
  SELECT
    COALESCE((SELECT frequency_id FROM query_frequency WHERE normalized_query = NEW.normalized_query), NULL),
    NEW.normalized_query,
    COALESCE(
      (SELECT original_query FROM query_frequency WHERE normalized_query = NEW.normalized_query),
      NEW.query_text
    ),
    COALESCE((SELECT total_count FROM query_frequency WHERE normalized_query = NEW.normalized_query), 0) + 1,
    CURRENT_TIMESTAMP,
    NEW.matched_problem_id
  WHERE NEW.normalized_query IS NOT NULL;
END;

-- Trigger: Update problem metrics on query
CREATE TRIGGER IF NOT EXISTS trg_problem_metrics_update
AFTER INSERT ON query_logs
FOR EACH ROW
BEGIN
  UPDATE problems
  SET frequency = frequency + 1
  WHERE problem_id = NEW.matched_problem_id;

  INSERT OR IGNORE INTO problem_usage_analytics (problem_id, date, query_count)
  VALUES (NEW.matched_problem_id, date(CURRENT_TIMESTAMP), 0);

  UPDATE problem_usage_analytics
  SET query_count = query_count + 1
  WHERE problem_id = NEW.matched_problem_id AND date = date(CURRENT_TIMESTAMP);
END;

-- Trigger: Update feedback aggregates on new feedback
CREATE TRIGGER IF NOT EXISTS trg_feedback_aggregates_update
AFTER INSERT ON feedback
FOR EACH ROW
BEGIN
  INSERT OR IGNORE INTO feedback_aggregates (aggregate_id, problem_id, total_feedbacks)
  VALUES (
    'agg_' || (SELECT problem_id FROM query_logs WHERE query_id = NEW.query_id),
    (SELECT problem_id FROM query_logs WHERE query_id = NEW.query_id),
    0
  );

  UPDATE feedback_aggregates
  SET total_feedbacks = total_feedbacks + 1,
      positive_count = positive_count + CASE WHEN NEW.rating > 0 THEN 1 ELSE 0 END,
      negative_count = negative_count + CASE WHEN NEW.rating < 0 THEN 1 ELSE 0 END,
      neutral_count = neutral_count + CASE WHEN NEW.rating = 0 THEN 1 ELSE 0 END,
      calculated_at = CURRENT_TIMESTAMP
  WHERE problem_id = (SELECT problem_id FROM query_logs WHERE query_id = NEW.query_id);
END;

-- ============================================
-- SAMPLE DATA INSERTION
-- ============================================

-- Insert categories
INSERT OR IGNORE INTO categories (category_id, name, description, sort_order) VALUES
('cat_http_errors', 'HTTP错误码', '各类HTTP状态码问题', 1),
('cat_service_support', '服务支持', '客服电话、服务流程等', 2),
('cat_access_issues', '访问问题', '网站访问缓慢、无法访问等', 3),
('cat_integration', '接入问题', '站点接入、DNS配置等', 4),
('cat_blocking', '拦截问题', '误拦截、黑名单等', 5),
('cat_alerts', '告警问题', '可用性告警、短信邮件等', 6),
('cat_login', '登录问题', '账号登录、权限等', 7),
('cat_operations', '功能操作', '报告导出、加白封禁等', 8),
('cat_accounts', '账号管理', '账号开通、用户管理等', 9),
('cat_contracts', '合同管理', '合同续签、延期等', 10),
('cat_configuration', '配置管理', '端口配置、区域控制等', 11),
('cat_reports', '报告管理', '云漏扫报告等', 12);

-- Insert sample problems (based on existing data)
INSERT OR IGNORE INTO problems (
  problem_id, slug, question, answer, category_id,
  keywords, priority, status, frequency, success_rate
) VALUES
(
  'error_504',
  '504-gateway-timeout-error',
  '出现504错误怎么办？',
  '【504错误排查】

含义：无法连接到源站，由Nginx发出响应码

原因：
- telnet不可达，如IP被源站屏蔽，或源站业务自身异常
- 网络异常
- 源站IP被玄武盾防火墙丢包（小概率事件）
- 连通性没有问题，但请求过大导致的超时（默认60秒）
- HTTPS握手阶段出现问题（仅HTTPS）

处理方法：
1)源站TCP连接故障，如端口不通
2)源站TCP连接正常，但部分请求（常见为POST请求）耗时过长导致的504
3)源站TCP连接正常，但因对端安全设备丢弃连接导致的504
4)网络异常

防护模式：
- 白名单IP地址或URL，HAProxy无法连接到源站
- 源站多个地址均不可达

转发模式：
- HAProxy无法连接到源站，和防护模式下的504同义

其他场景：
- Nginx配置未下发，或已下发但未生效
- 请在对应节点查看nginx进程启动时间，如出现较为明显的时间差，请升级到二线处理',
  'cat_http_errors',
  '["504", "超时", "网关超时", "无法连接"]',
  5,
  'active',
  1,
  0.00
),
(
  'error_403',
  '403-forbidden-error',
  '出现403错误怎么办？',
  '【403错误排查】

被云防护安全策略拦截

建议用户点击下方的反馈误报。

在【运营工具】-【误报反馈】中查看分析对应误报：
- 如果疑似攻击则继续拦截，点【不处理】并添加继续拦截的备注
- 如果分析是误报，则做【url规则禁用】或【站点级规则禁用】

如果无法通过误报反馈的方式提交误报：
1. 查询对应站点的攻击日志，被拦截响应码为403
2. 在【安全运营】-【防护策略】中搜索对应策略ID
3. 配置站点级或者url级禁用

若攻击日志对应的策略ID为15010052，则在【站点配置】-【webshell白名单】进行添加处理。',
  'cat_http_errors',
  '["403", "禁止访问", "拦截"]',
  5,
  'active',
  1,
  0.00
),
(
  'add_site',
  'how-to-add-site',
  '如何添加站点？',
  '【添加站点流程】

处理步骤：

1. 提供一下ssl证书（nginx版本的）
2. 站点建立后，发送客户cname
3. 本地电脑测试在自己电脑的hosts文件写一条解析记录
4. DNS解析页面刷新

站点改为https加密：
- 查看端口是否在白名单中，如果不在找相关地区人员

玄武盾临时关闭（DNS改为A记录）：
- 同理做cname解析需要将原来的A记录删除

已经改回源站：需要重新添加站点（端口）

【端口说明】
- http默认80，https默认443
- 证书pem改为crt
- 没有特殊要求都是默认

【注意事项】
- IPV6授权不允许
- 源站是否有v6地址，是否有购买云防护v6转换服务',
  'cat_integration',
  '["添加站点", "新建站点"]',
  5,
  'active',
  1,
  0.00
);

-- Insert answer templates
INSERT OR IGNORE INTO answer_templates (
  template_id, name, content, category_id
) VALUES
(
  'tmpl_error_investigation',
  '错误码调查模板',
  '【{{error_code}}错误排查】

含义：{{error_meaning}}

可能原因：
{{reasons_list}}

处理方法：
{{steps_list}}

如果问题仍未解决，请检查：
{{additional_checks}}',
  'cat_http_errors'
),
(
  'tmpl_contact_support',
  '联系技术支持模板',
  '如果问题仍未解决，请联系技术支持：

1. 工号：{{staff_id}}
2. 联系方式：{{contact_method}}
3. 工作时间：{{work_hours}}

请提供以下信息：
- 问题发生的准确时间
- 受影响的域名/IP
- 错误截图或日志',
  'cat_service_support'
);

-- ============================================
-- END OF SCHEMA
-- ============================================