
const knowledgeBase = {
  greetings: {
    keywords: ['你好', '您好', 'hi', 'hello', '嗨', '在吗'],
    response: '您好！我是 SaaS 安全运营客服机器人，很高兴为您服务。\n\n我可以帮您解答以下问题：\n1. 云监测接入流程\n2. 玄武盾防护管理\n3. 工单处理规范\n4. 问题排查\n\n请告诉我您需要什么帮助？'
  },
  cloudMonitoring: {
    keywords: ['云监测', '监测', '监控', '接入', '添加站点'],
    response: '【云监测接入流程】\n\n1. 接入前准备：\n   - 需要客户填写《云监测网站环境调查表》\n   - 确认扫描授权书（若需要）\n   - 收集备案 IP 信息\n\n2. 接入流程：\n   - 申请阶段：客户提交云监测服务接入申请\n   - 配置阶段：在管理端添加监测站点、配置参数、确认合同\n   - 验证阶段：确认监测正常运行\n\n3. 功能操作：\n   - 导出监测自定义汇总报告（日报、月报、年报）\n   - 导出任意时间单站点监测报告\n   - 导出实时报告\n   - 制作脱敏报告模板\n   - 查看可视化大屏\n   - 平台登录密码修改/重置\n   - 安全事件告警查看\n   - 通过 URL/用户手机号码查询合同'
  },
  xuanwudun: {
    keywords: ['玄武盾', 'waf', '防护', '防火墙', '云防护'],
    response: '【玄武盾防护管理】\n\n防护模式：\n- 防护模式：开启全量防护\n- 检测模式：仅记录日志不拦截\n- 转发模式：仅转发流量不防护\n\n核心功能：\n1. 一键关停\n2. 永久在线（需先学习3天）\n3. 回源/回切\n4. 防扫描、防CC、访问控制\n\n更多功能详情请咨询具体问题。'
  },
  modeSwitch: {
    keywords: ['模式', '切换', '防护模式', '检测模式', '转发模式'],
    response: '【防护模式说明】\n\n- **防护模式**：开启全量防护，拦截恶意攻击\n- **检测模式**：仅记录日志不拦截，用于观察流量\n- **转发模式**：仅转发流量不防护，相当于透明代理\n\n您可以根据实际需求在平台中切换相应模式。'
  },
  error403: {
    keywords: ['403', '拦截', '误拦截', '禁止访问'],
    response: '【403 拦截排查】\n\n出现 403 拦截时的处理步骤：\n1. 确认拦截时间点\n2. 查看访问日志\n3. 检查防护规则\n\n如果是正常业务被误拦截：\n1. 确认正常业务被误拦截\n2. 在 URL 级别或站点级别解封该防护策略\n3. 验证恢复正常访问\n4. 删除策略限制，恢复正常拦截功能'
  },
  error422: {
    keywords: ['422', '端口', '未添加', '配置未生效'],
    response: '【422 错误排查】\n\n422 错误表示访问了未添加的端口或端口配置未生效。\n\n解决方法：\n1. 检查站点配置的端口列表\n2. 确认端口是否已添加\n3. 如未添加，添加该端口或联系首席重新下发配置'
  },
  error5xx: {
    keywords: ['500', '501', '502', '503', '504', '5xx', '服务器错误'],
    response: '【5XX 错误排查】\n\n常见 5XX 错误原因：\n- 源站服务器故障\n- 网络连接问题\n- 配置错误\n\n建议参考《玄武盾 5XX 响应码及常见快速排障措施》文档进行详细排查。'
  },
  siteDown: {
    keywords: ['无法访问', '站点打不开', '网站挂了', '访问不了'],
    response: '【站点无法访问排查】\n\n1. 检查 DNS 解析是否正确\n2. 确认防护模式设置\n3. 查看访问日志\n4. 检查源站状态\n5. 如需临时回源，可开启回源站点功能\n\n如果问题仍未解决，请联系技术支持。'
  },
  ticket: {
    keywords: ['工单', 'udesk', '400', '邮件', '投诉', '反馈'],
    response: '【工单处理规范】\n\nUDESK 工单记录标准：\n- 记录工单时需包含完整的问题描述\n- 记录处理过程和结果\n- 分类标记工单类型\n\n400 坐席接听指南：\n- 按照标准话术接听电话\n- 详细记录客户问题\n- 及时跟进处理进度\n\n邮件告警服务器：\n- 地址：http://172.16.5.153:8089/web/sms/manual\n- 需连接萧山 VPN'
  },
  vpn: {
    keywords: ['vpn', '萧山', 'vpn账号', 'vpn密码'],
    response: '【萧山 VPN 信息】\n\n- 用户名：stormcenter\n- 密码：ujKqX34oM60DO8Gh\n\n⚠️ 注意：严禁外传！'
  },
  platform: {
    keywords: ['平台', '网址', '网站', '链接', '地址', '登录'],
    response: '【平台访问信息】\n\n- 公司官网：https://www.dbappsecurity.com.cn/\n- 云监测/云防护平台：https://www.websaas.cn\n- 邮件告警服务器：http://172.16.5.153:8089/web/sms/manual (需连接萧山 VPN)'
  },
  permanentOnline: {
    keywords: ['永久在线', '学习模式', '镜像'],
    response: '【永久在线功能】\n\n开启永久在线需要：\n1. 先开启学习模式\n2. 学习 3 天创建好镜像\n3. 然后才可打开永久在线功能\n\n开启后请观察站点状态并分析原因。'
  },
  backToSource: {
    keywords: ['回源', '回切', '绕过', 'dns'],
    response: '【回源/回切说明】\n\n- **回源站点**：通过 DNS 完全绕过玄武盾，直接访问源站\n- **回切站点**：通过 DNS 接入玄武盾，恢复防护\n\n注意：删除站点将引起业务故障，真实环境中需和客户得到有痕迹的确定方可删除。'
  },
  thanks: {
    keywords: ['谢谢', '感谢', 'thanks', 'thank you'],
    response: '不客气！很高兴能帮到您。如果还有其他问题，随时可以问我。'
  },
  bye: {
    keywords: ['再见', '拜拜', 'bye', 'goodbye'],
    response: '再见！祝您工作顺利，有问题随时再来咨询！'
  }
};

function getResponse(userInput) {
  const input = userInput.toLowerCase();
  
  for (const [key, item] of Object.entries(knowledgeBase)) {
    if (item.keywords.some(keyword =&gt; input.includes(keyword.toLowerCase()))) {
      return item.response;
    }
  }
  
  return '抱歉，我暂时无法理解您的问题。您可以尝试询问以下方面：\n\n- 云监测接入流程\n- 玄武盾防护管理\n- 403/422/5XX 错误排查\n- 工单处理\n- 平台访问\n\n或者重新描述您的问题，我会尽力为您解答！';
}

module.exports = {
  knowledgeBase,
  getResponse
};
