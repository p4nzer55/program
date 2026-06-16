const http = require('http');
const fs = require('fs');
const path = require('path');
const OptimizationSystem = require('./optimization-system');

// 创建优化系统实例
const optimizer = new OptimizationSystem();

// 知识库（与优化系统联动）
const knowledgeBase = {};

// 从优化系统初始化知识库
function initKnowledgeBase() {
  const problems = optimizer.getAllProblems();

  problems.forEach(problem => {
    const key = problem.id;
    knowledgeBase[key] = {
      keywords: problem.keywords,
      response: problem.answer,
      category: problem.category,
      problemId: problem.id
    };
  });

  // 保留原有的问候语、感谢语等
  knowledgeBase.greetings = {
    keywords: ['你好', '您好', 'hi', 'hello', '嗨', '在吗'],
    response: '您好！我是 SaaS 安全运营客服机器人，很高兴为您服务。\n\n我可以帮您解答以下问题：\n1. HTTP错误码（502、503、504、500、403、404等）\n2. 玄武盾防护管理\n3. 云防护接入流程\n4. 访问问题排查\n5. 功能操作（报告导出、加白、封禁等）\n6. 账号和合同管理\n\n请告诉我您需要什么帮助？',
    category: '问候',
    problemId: null
  };

  knowledgeBase.thanks = {
    keywords: ['谢谢', '感谢', 'thanks', 'thank you'],
    response: '不客气！很高兴能帮到您。如果还有其他问题，随时可以问我。\n\n如果您对我的回答有意见或建议，可以点击下方的反馈按钮。',
    category: '感谢',
    problemId: null
  };

  knowledgeBase.bye = {
    keywords: ['再见', '拜拜', 'bye', 'goodbye'],
    response: '再见！祝您工作顺利，有问题随时再来咨询！',
    category: '告别',
    problemId: null
  };

  console.log(`✓ 已加载 ${problems.length} 个问题到知识库`);
}

// 获取回复（使用优化系统）
function getResponse(userInput) {
  const input = userInput.toLowerCase();

  // 1. 首先使用优化系统进行智能匹配
  const matchedProblem = optimizer.findBestMatch(userInput);

  if (matchedProblem) {
    // 记录查询
    const queryId = optimizer.recordQuery(userInput, matchedProblem.id, matchedProblem.answer);

    return {
      response: matchedProblem.answer,
      queryId: queryId,
      problemId: matchedProblem.id,
      category: matchedProblem.category,
      hasFeedback: true,
      source: 'optimized_database'
    };
  }

  // 2. 如果没有匹配到，使用原始关键词匹配
  for (const [key, item] of Object.entries(knowledgeBase)) {
    if (item.keywords.some(keyword => input.includes(keyword.toLowerCase()))) {
      const queryId = optimizer.recordQuery(userInput, item.problemId, item.response);
      return {
        response: item.response,
        queryId: queryId,
        problemId: item.problemId,
        category: item.category,
        hasFeedback: true,
        source: 'legacy_keywords'
      };
    }
  }

  // 3. 记录未匹配的查询
  const queryId = optimizer.recordQuery(userInput, null, null);

  return {
    response: '抱歉，我暂时无法理解您的问题。您可以尝试询问以下方面：\n\n- HTTP错误码（502、503、504、500、403、404、400等）\n- 玄武盾防护管理\n- 云防护接入流程\n- 网站访问问题\n- 工单处理\n- 功能操作\n\n或者重新描述您的问题，我会尽力为您解答！',
    queryId: queryId,
    problemId: null,
    category: null,
    hasFeedback: false,
    source: 'fallback'
  };
}

// 记录用户反馈
function recordFeedback(queryId, rating, feedbackText = '') {
  return optimizer.recordFeedback(queryId, rating, feedbackText);
}

// 记录建议的新答案
function recordSuggestedAnswer(queryId, suggestedAnswer) {
  return optimizer.recordSuggestedAnswer(queryId, suggestedAnswer);
}

// 获取分析报告
function getAnalyticsReport() {
  return optimizer.getAnalyticsReport();
}

// 获取优化建议
function getOptimizationSuggestions() {
  return optimizer.getOptimizationSuggestions();
}

// 添加新问题
function addProblem(problemData) {
  return optimizer.addProblem(problemData);
}

// 更新问题答案
function updateProblemAnswer(problemId, newAnswer, reason = '') {
  return optimizer.updateProblemAnswer(problemId, newAnswer, reason);
}

// 获取文件类型
function getContentType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const types = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
  };
  return types[ext] || 'application/octet-stream';
}

// 创建服务器
const server = http.createServer((req, res) => {
  // 处理 CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // 处理 API 请求
  if (req.url.startsWith('/api/')) {
    handleAPI(req, res);
    return;
  }

  // 处理静态文件
  let filePath = '.' + (req.url === '/' ? '/index.html' : req.url);
  const fullPath = path.join(__dirname, filePath);

  // 检查文件是否存在
  fs.access(fullPath, fs.constants.F_OK, (err) => {
    if (err) {
      // 404 - 返回 index.html（支持 SPA 路由）
      const indexPath = path.join(__dirname, 'index.html');
      fs.readFile(indexPath, (err, content) => {
        if (err) {
          res.writeHead(404);
          res.end('Not Found');
          return;
        }
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(content);
      });
      return;
    }

    fs.readFile(fullPath, (err, content) => {
      if (err) {
        res.writeHead(500);
        res.end('Server Error');
        return;
      }
      res.writeHead(200, { 'Content-Type': getContentType(fullPath) });
      res.end(content);
    });
  });
});

// 处理 API 请求
function handleAPI(req, res) {
  const url = req.url;

  if (url === '/api/chat' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });
    req.on('end', () => {
      try {
        const data = JSON.parse(body);
        const result = getResponse(data.message || '');
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify(result));
      } catch (error) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ error: '无效的请求格式' }));
      }
    });
    return;
  }

  if (url === '/api/feedback' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });
    req.on('end', () => {
      try {
        const data = JSON.parse(body);
        const feedbackId = recordFeedback(
          data.queryId,
          data.rating,
          data.feedback || ''
        );
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: true, feedbackId }));
      } catch (error) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ error: '无效的请求格式' }));
      }
    });
    return;
  }

  if (url === '/api/suggest-answer' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });
    req.on('end', () => {
      try {
        const data = JSON.parse(body);
        const suggestionId = recordSuggestedAnswer(
          data.queryId,
          data.suggestedAnswer
        );
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: true, suggestionId }));
      } catch (error) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ error: '无效的请求格式' }));
      }
    });
    return;
  }

  if (url === '/api/analytics' && req.method === 'GET') {
    const report = getAnalyticsReport();
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(report));
    return;
  }

  if (url === '/api/suggestions' && req.method === 'GET') {
    const suggestions = getOptimizationSuggestions();
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ suggestions }));
    return;
  }

  if (url === '/api/problems' && req.method === 'GET') {
    const { category, sort } = new URL(req.url, `http://${req.headers.host}`).searchParams;
    const problems = optimizer.getAllProblems({
      category,
      sortBy: sort
    });
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ problems }));
    return;
  }

  if (url === '/api/problems' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });
    req.on('end', () => {
      try {
        const data = JSON.parse(body);
        const newProblem = addProblem(data);
        initKnowledgeBase(); // 重新初始化知识库
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: true, problem: newProblem }));
      } catch (error) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ error: '无效的请求格式' }));
      }
    });
    return;
  }

  if (url.match(/^\/api\/problems\/[^/]+$/) && req.method === 'GET') {
    const problemId = url.split('/')[3];
    const problem = optimizer.getProblem(problemId);
    if (problem) {
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(problem));
    } else {
      res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: '问题不存在' }));
    }
    return;
  }

  if (url.match(/^\/api\/problems\/[^/]+$/) && req.method === 'PATCH') {
    const problemId = url.split('/')[3];
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });
    req.on('end', () => {
      try {
        const data = JSON.parse(body);
        const success = updateProblemAnswer(
          problemId,
          data.answer,
          data.reason || ''
        );
        initKnowledgeBase(); // 重新初始化知识库
        if (success) {
          res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
          res.end(JSON.stringify({ success: true }));
        } else {
          res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
          res.end(JSON.stringify({ error: '问题不存在' }));
        }
      } catch (error) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ error: '无效的请求格式' }));
      }
    });
    return;
  }

  // 未知 API
  res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify({ error: 'API 不存在' }));
}

// 初始化知识库
initKnowledgeBase();

const PORT = process.env.PORT || 3000;

server.listen(PORT, () => {
  console.log(`🛡️ SaaS Helper 服务器已启动`);
  console.log(`📱 访问地址: http://localhost:${PORT}`);
  console.log(`🔌 API 地址: http://localhost:${PORT}/api/chat`);
  console.log(`📊 分析报告: http://localhost:${PORT}/api/analytics`);
  console.log(`💡 优化建议: http://localhost:${PORT}/api/suggestions`);
  console.log(``);
  console.log('✓ 已启用自优化系统');
  console.log('✓ 已加载 35+ 个问题到知识库');
  console.log('');
  console.log('按 Ctrl+C 停止服务器');
});