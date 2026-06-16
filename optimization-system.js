/**
 * SaaS Helper 自优化系统
 * 基于用户反馈和访问频率自动优化回答
 */

const fs = require('fs');
const path = require('path');

// 数据库文件路径
const DB_PATH = path.join(__dirname, 'problem-database.json');
const FEEDBACK_PATH = path.join(__dirname, 'feedback-data.json');
const ANALYTICS_PATH = path.join(__dirname, 'analytics-data.json');

class OptimizationSystem {
  constructor() {
    this.problems = [];
    this.feedbacks = [];
    this.analytics = {
      queries: [],
      answerRatings: [],
      queryFrequency: {},
      problemUsage: {}
    };
    this.loadData();
  }

  // 加载数据
  loadData() {
    try {
      // 加载问题数据库
      if (fs.existsSync(DB_PATH)) {
        const dbData = fs.readFileSync(DB_PATH, 'utf8');
        this.problems = JSON.parse(dbData).problems || [];
      }

      // 加载反馈数据
      if (fs.existsSync(FEEDBACK_PATH)) {
        const feedbackData = fs.readFileSync(FEEDBACK_PATH, 'utf8');
        this.feedbacks = JSON.parse(feedbackData) || [];
      }

      // 加载分析数据
      if (fs.existsSync(ANALYTICS_PATH)) {
        const analyticsData = fs.readFileSync(ANALYTICS_PATH, 'utf8');
        this.analytics = JSON.parse(analyticsData) || this.analytics;
      }
    } catch (error) {
      console.error('加载数据失败:', error);
    }
  }

  // 保存数据
  saveData() {
    try {
      // 保存反馈数据
      fs.writeFileSync(FEEDBACK_PATH, JSON.stringify(this.feedbacks, null, 2));

      // 保存分析数据
      fs.writeFileSync(ANALYTICS_PATH, JSON.stringify(this.analytics, null, 2));

      // 更新问题数据库
      const dbData = {
        problems: this.problems,
        categories: this.getCategories(),
        metadata: {
          version: '1.0',
          created_at: '2024-06-16T00:00:00Z',
          last_updated: new Date().toISOString(),
          total_problems: this.problems.length,
          total_categories: this.getCategories().length
        }
      };
      fs.writeFileSync(DB_PATH, JSON.stringify(dbData, null, 2));
    } catch (error) {
      console.error('保存数据失败:', error);
    }
  }

  // 获取所有类别
  getCategories() {
    const categories = new Set();
    this.problems.forEach(p => {
      if (p.category) categories.add(p.category);
    });
    return Array.from(categories);
  }

  // 记录查询
  recordQuery(query, matchedProblemId, answer) {
    const queryRecord = {
      id: this.generateId(),
      query: query,
      matched_problem_id: matchedProblemId,
      answer: answer,
      timestamp: new Date().toISOString(),
      rating: null,
      feedback: null
    };

    this.analytics.queries.push(queryRecord);

    // 更新查询频率统计
    const normalizedQuery = this.normalizeQuery(query);
    this.analytics.queryFrequency[normalizedQuery] = (this.analytics.queryFrequency[normalizedQuery] || 0) + 1;

    // 更新问题使用统计
    if (matchedProblemId) {
      this.analytics.problemUsage[matchedProblemId] = (this.analytics.problemUsage[matchedProblemId] || 0) + 1;
      this.updateProblemFrequency(matchedProblemId);
    }

    this.saveData();
    return queryRecord.id;
  }

  // 记录用户反馈
  recordFeedback(queryId, rating, feedbackText = '') {
    const feedback = {
      id: this.generateId(),
      query_id: queryId,
      rating: rating, // 1=有用, -1=无用
      feedback: feedbackText,
      timestamp: new Date().toISOString()
    };

    this.feedbacks.push(feedback);

    // 更新查询记录
    const queryRecord = this.analytics.queries.find(q => q.id === queryId);
    if (queryRecord) {
      queryRecord.rating = rating;
      queryRecord.feedback = feedbackText;

      // 更新问题评分
      if (queryRecord.matched_problem_id) {
        this.updateProblemSuccessRate(queryRecord.matched_problem_id, rating);
      }
    }

    // 记录答案评分
    this.analytics.answerRatings.push({
      problem_id: queryRecord?.matched_problem_id,
      rating: rating,
      timestamp: new Date().toISOString()
    });

    this.saveData();
    return feedback.id;
  }

  // 记录建议的新答案
  recordSuggestedAnswer(queryId, suggestedAnswer) {
    const feedback = {
      id: this.generateId(),
      query_id: queryId,
      type: 'suggested_answer',
      suggested_answer: suggestedAnswer,
      timestamp: new Date().toISOString(),
      status: 'pending' // pending, approved, rejected
    };

    this.feedbacks.push(feedback);
    this.saveData();
    return feedback.id;
  }

  // 更新问题频率
  updateProblemFrequency(problemId) {
    const problem = this.problems.find(p => p.id === problemId);
    if (problem) {
      problem.frequency = (problem.frequency || 0) + 1;
      problem.updated_at = new Date().toISOString();
    }
  }

  // 更新问题成功率
  updateProblemSuccessRate(problemId, rating) {
    const problem = this.problems.find(p => p.id === problemId);
    if (problem) {
      problem.feedback.push({
        rating: rating,
        timestamp: new Date().toISOString()
      });

      // 计算新的成功率
      const total = problem.feedback.length;
      const positive = problem.feedback.filter(f => f.rating === 1).length;
      problem.success_rate = total > 0 ? (positive / total) : 0;
      problem.updated_at = new Date().toISOString();
    }
  }

  // 智能问题匹配
  findBestMatch(query) {
    const normalizedQuery = this.normalizeQuery(query);
    const matches = [];

    this.problems.forEach(problem => {
      let score = 0;

      // 关键词匹配
      problem.keywords.forEach(keyword => {
        const normalizedKeyword = keyword.toLowerCase();
        if (normalizedQuery.includes(normalizedKeyword)) {
          score += 10;
        }
      });

      // 问题标题匹配
      if (normalizedQuery.includes(this.normalizeQuery(problem.question))) {
        score += 15;
      }

      // 类别匹配
      const category = problem.category;
      if (this.queryMatchesCategory(query, category)) {
        score += 5;
      }

      // 使用频率加成（高频问题优先）
      if (problem.frequency > 10) {
        score += Math.min(5, Math.floor(problem.frequency / 20));
      }

      // 成功率加成（高成功率答案优先）
      if (problem.success_rate > 0.8) {
        score += 3;
      }

      if (score > 0) {
        matches.push({
          problem: problem,
          score: score
        });
      }
    });

    // 按分数排序
    matches.sort((a, b) => b.score - a.score);

    return matches.length > 0 ? matches[0].problem : null;
  }

  // 规范化查询
  normalizeQuery(query) {
    return query.toLowerCase()
      .replace(/[，。！？、；：""''（）【】]/g, '')
      .replace(/\s+/g, '')
      .trim();
  }

  // 检查查询是否匹配类别
  queryMatchesCategory(query, category) {
    const categoryKeywords = {
      'HTTP错误码': ['502', '503', '504', '500', '403', '404', '400', '401', '405', '422', '420', '421', '错误码'],
      '服务支持': ['电话', '400', '客服', '热线', '支持'],
      '访问问题': ['慢', '卡', '访问', '加载', '打不开'],
      '接入问题': ['接入', '添加站点', '新建站点', 'cname', 'dns', '解析'],
      '拦截问题': ['拦截', '黑名单', '被限制', '被封'],
      '告警问题': ['告警', '短信', '邮件', '通知'],
      '登录问题': ['登录', '账号', '密码', '看不到'],
      '功能操作': ['导出', '报告', '加白', '封禁', '放行', '防扫描', '防cc'],
      '账号管理': ['账号', '开通', '用户'],
      '合同管理': ['合同', '续保', '续签', '延期'],
      '配置管理': ['配置', '端口', '区域', '数量'],
      '报告管理': ['报告', '漏扫', '审核']
    };

    const keywords = categoryKeywords[category] || [];
    const normalizedQuery = query.toLowerCase();
    return keywords.some(k => normalizedQuery.includes(k.toLowerCase()));
  }

  // 获取优化建议
  getOptimizationSuggestions() {
    const suggestions = [];

    // 1. 低成功率问题建议
    this.problems.forEach(problem => {
      if (problem.feedback.length >= 5 && problem.success_rate < 0.5) {
        suggestions.push({
          type: 'low_success_rate',
          problem_id: problem.id,
          problem_question: problem.question,
          current_success_rate: problem.success_rate,
          suggestion: '该答案成功率较低，建议重新审核和优化答案内容'
        });
      }
    });

    // 2. 高频但低满意度问题
    this.problems.forEach(problem => {
      if (problem.frequency > 10 && problem.success_rate < 0.7) {
        suggestions.push({
          type: 'high_frequency_low_quality',
          problem_id: problem.id,
          problem_question: problem.question,
          frequency: problem.frequency,
          current_success_rate: problem.success_rate,
          suggestion: '该问题高频出现但答案满意度不高，建议优先优化'
        });
      }
    });

    // 3. 新增问题建议
    const queries = this.analytics.queries.filter(q => !q.matched_problem_id);
    const unmatchedQueries = this.groupUnmatchedQueries(queries);

    unmatchedQueries.forEach(group => {
      if (group.count >= 3) {
        suggestions.push({
          type: 'new_problem',
          query: group.query,
          count: group.count,
          suggestion: `该问题被多次查询但无匹配答案，建议添加到知识库`
        });
      }
    });

    return suggestions;
  }

  // 分组未匹配的查询
  groupUnmatchedQueries(queries) {
    const groups = {};

    queries.forEach(q => {
      const normalized = this.normalizeQuery(q.query);
      if (!groups[normalized]) {
        groups[normalized] = {
          query: q.query,
          count: 0,
          queries: []
        };
      }
      groups[normalized].count++;
      groups[normalized].queries.push(q);
    });

    return Object.values(groups).filter(g => g.count > 1);
  }

  // 获取分析报告
  getAnalyticsReport() {
    return {
      total_queries: this.analytics.queries.length,
      total_feedbacks: this.feedbacks.length,
      problem_usage: this.analytics.problemUsage,
      query_frequency: Object.entries(this.analytics.queryFrequency)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10),
      top_problems: this.problems
        .sort((a, b) => (b.frequency || 0) - (a.frequency || 0))
        .slice(0, 10)
        .map(p => ({
          id: p.id,
          question: p.question,
          category: p.category,
          frequency: p.frequency || 0,
          success_rate: p.success_rate || 0
        })),
      optimization_suggestions: this.getOptimizationSuggestions(),
      low_rated_answers: this.problems
        .filter(p => p.feedback.length >= 3 && p.success_rate < 0.6)
        .map(p => ({
          id: p.id,
          question: p.question,
          success_rate: p.success_rate
        }))
    };
  }

  // 生成唯一ID
  generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
  }

  // 添加新问题
  addProblem(problemData) {
    const newProblem = {
      id: this.generateId(),
      category: problemData.category || '其他',
      keywords: problemData.keywords || [],
      question: problemData.question,
      answer: problemData.answer,
      priority: problemData.priority || 3,
      frequency: 0,
      success_rate: 0,
      feedback: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    this.problems.push(newProblem);
    this.saveData();
    return newProblem;
  }

  // 更新问题答案
  updateProblemAnswer(problemId, newAnswer, reason = '') {
    const problem = this.problems.find(p => p.id === problemId);
    if (problem) {
      // 保存旧答案版本
      if (!problem.answer_history) {
        problem.answer_history = [];
      }
      problem.answer_history.push({
        answer: problem.answer,
        reason: reason,
        timestamp: new Date().toISOString()
      });

      // 更新新答案
      problem.answer = newAnswer;
      problem.updated_at = new Date().toISOString();

      this.saveData();
      return true;
    }
    return false;
  }

  // 获取问题详情
  getProblem(problemId) {
    return this.problems.find(p => p.id === problemId);
  }

  // 获取所有问题
  getAllProblems(options = {}) {
    let problems = [...this.problems];

    // 按类别筛选
    if (options.category) {
      problems = problems.filter(p => p.category === options.category);
    }

    // 按排序方式
    if (options.sortBy === 'frequency') {
      problems.sort((a, b) => (b.frequency || 0) - (a.frequency || 0));
    } else if (options.sortBy === 'success_rate') {
      problems.sort((a, b) => (b.success_rate || 0) - (a.success_rate || 0));
    } else if (options.sortBy === 'priority') {
      problems.sort((a, b) => b.priority - a.priority);
    }

    return problems;
  }
}

module.exports = OptimizationSystem;