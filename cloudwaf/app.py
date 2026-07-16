import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from config import Config
from models import db, Site, Rule
from engine.rules import rule_engine
from engine.access_control import access_control
from engine.rate_limiter import rate_limiter
from engine.logger import attack_logger
from engine.proxy import waf_proxy

app = Flask(__name__, template_folder='templates')
app.config.from_object(Config)
db.init_app(app)


def init_db():
    with app.app_context():
        db.create_all()
        from engine.rules import RuleEngine
        RuleEngine.init_default_rules()
        if not Site.query.first():
            demo = Site(
                name='示例站点',
                domain='localhost',
                backend_url=Config.DEFAULT_BACKEND,
                mode='protection',
                status='enabled'
            )
            db.session.add(demo)
            db.session.commit()


def login_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('admin_logged_in'):
            if request.path.startswith('/api/'):
                return jsonify({'code': 401, 'msg': '未登录'}), 401
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '')
        password = data.get('password', '')
        if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return jsonify({'code': 0, 'msg': '登录成功'})
        return jsonify({'code': 401, 'msg': '用户名或密码错误'})
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    return render_template('login.html')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


@app.route('/admin')
@login_required
def admin_dashboard():
    return render_template('dashboard.html', active='dashboard')


@app.route('/admin/logs')
@login_required
def admin_logs():
    return render_template('logs.html', active='logs')


@app.route('/admin/rules')
@login_required
def admin_rules():
    return render_template('rules.html', active='rules')


@app.route('/admin/sites')
@login_required
def admin_sites():
    return render_template('sites.html', active='sites')


@app.route('/admin/access')
@login_required
def admin_access():
    return render_template('access.html', active='access')


@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    stats = attack_logger.get_dashboard_stats()
    sites_count = Site.query.count()
    rules_count = Rule.query.filter_by(enabled=True).count()
    blacklist_count = len(access_control.list_blacklist())
    stats['sites_count'] = sites_count
    stats['rules_count'] = rules_count
    stats['blacklist_count'] = blacklist_count
    return jsonify({'code': 0, 'data': stats})


@app.route('/api/logs')
@login_required
def api_logs():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    attack_type = request.args.get('attack_type') or None
    client_ip = request.args.get('client_ip') or None
    severity = request.args.get('severity') or None
    result = attack_logger.query_logs(
        page=page, per_page=per_page,
        attack_type=attack_type, client_ip=client_ip,
        severity=severity
    )
    return jsonify({'code': 0, 'data': result})


@app.route('/api/rules')
@login_required
def api_list_rules():
    category = request.args.get('category')
    query = Rule.query
    if category:
        query = query.filter_by(category=category)
    rules = query.order_by(Rule.category, Rule.id).all()
    return jsonify({'code': 0, 'data': [r.to_dict() for r in rules]})


@app.route('/api/rules/<int:rule_id>/toggle', methods=['POST'])
@login_required
def api_toggle_rule(rule_id):
    rule = Rule.query.get_or_404(rule_id)
    rule.enabled = not rule.enabled
    db.session.commit()
    rule_engine.invalidate_cache()
    return jsonify({'code': 0, 'data': {'enabled': rule.enabled}})


@app.route('/api/rules/<int:rule_id>', methods=['PUT'])
@login_required
def api_update_rule(rule_id):
    rule = Rule.query.get_or_404(rule_id)
    data = request.get_json()
    if 'pattern' in data:
        rule.pattern = data['pattern']
    if 'description' in data:
        rule.description = data['description']
    if 'severity' in data:
        rule.severity = data['severity']
    db.session.commit()
    rule_engine.invalidate_cache()
    return jsonify({'code': 0, 'data': rule.to_dict()})


@app.route('/api/rules', methods=['POST'])
@login_required
def api_add_rule():
    data = request.get_json()
    rule = Rule(
        name=data['name'],
        category=data['category'],
        pattern=data['pattern'],
        description=data.get('description', ''),
        severity=data.get('severity', 'medium'),
        enabled=True
    )
    db.session.add(rule)
    db.session.commit()
    rule_engine.invalidate_cache()
    return jsonify({'code': 0, 'data': rule.to_dict()})


@app.route('/api/rules/<int:rule_id>', methods=['DELETE'])
@login_required
def api_delete_rule(rule_id):
    rule = Rule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()
    rule_engine.invalidate_cache()
    return jsonify({'code': 0})


@app.route('/api/sites')
@login_required
def api_list_sites():
    sites = Site.query.order_by(Site.id.desc()).all()
    return jsonify({'code': 0, 'data': [s.to_dict() for s in sites]})


@app.route('/api/sites', methods=['POST'])
@login_required
def api_add_site():
    data = request.get_json()
    site = Site(
        name=data['name'],
        domain=data['domain'],
        backend_url=data['backend_url'],
        mode=data.get('mode', 'protection'),
        status=data.get('status', 'enabled')
    )
    db.session.add(site)
    db.session.commit()
    return jsonify({'code': 0, 'data': site.to_dict()})


@app.route('/api/sites/<int:site_id>', methods=['PUT'])
@login_required
def api_update_site(site_id):
    site = Site.query.get_or_404(site_id)
    data = request.get_json()
    for field in ['name', 'domain', 'backend_url', 'mode', 'status']:
        if field in data:
            setattr(site, field, data[field])
    db.session.commit()
    return jsonify({'code': 0, 'data': site.to_dict()})


@app.route('/api/sites/<int:site_id>', methods=['DELETE'])
@login_required
def api_delete_site(site_id):
    site = Site.query.get_or_404(site_id)
    db.session.delete(site)
    db.session.commit()
    return jsonify({'code': 0})


@app.route('/api/sites/<int:site_id>/mode', methods=['POST'])
@login_required
def api_site_mode(site_id):
    site = Site.query.get_or_404(site_id)
    data = request.get_json()
    site.mode = data.get('mode', 'protection')
    db.session.commit()
    return jsonify({'code': 0, 'data': {'mode': site.mode}})


@app.route('/api/access/blacklist')
@login_required
def api_blacklist():
    return jsonify({'code': 0, 'data': access_control.list_blacklist()})


@app.route('/api/access/blacklist', methods=['POST'])
@login_required
def api_add_blacklist():
    data = request.get_json()
    ip = data['ip']
    reason = data.get('reason', '')
    duration = data.get('duration')
    if duration:
        duration = int(duration)
    access_control.add_blacklist(ip, reason=reason, duration=duration)
    return jsonify({'code': 0})


@app.route('/api/access/blacklist/<ip>', methods=['DELETE'])
@login_required
def api_remove_blacklist(ip):
    access_control.remove_blacklist(ip)
    return jsonify({'code': 0})


@app.route('/api/access/whitelist')
@login_required
def api_whitelist():
    return jsonify({'code': 0, 'data': access_control.list_whitelist()})


@app.route('/api/access/whitelist', methods=['POST'])
@login_required
def api_add_whitelist():
    data = request.get_json()
    access_control.add_whitelist(data['ip'], data.get('remark', ''))
    return jsonify({'code': 0})


@app.route('/api/access/whitelist/<ip>', methods=['DELETE'])
@login_required
def api_remove_whitelist(ip):
    access_control.remove_whitelist(ip)
    return jsonify({'code': 0})


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def waf_handler(path):
    if path.startswith('admin') or path.startswith('api/'):
        return jsonify({'code': 404, 'msg': 'Not Found'}), 404
    return waf_proxy.process(path)


if __name__ == '__main__':
    init_db()
    print("=" * 60)
    print("  CloudWAF - 云Web应用防火墙系统")
    print("=" * 60)
    print(f"  WAF代理入口:  http://localhost:5000")
    print(f"  管理后台:     http://localhost:5000/admin")
    print(f"  默认账号:     admin / admin123")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
