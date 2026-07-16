import json
from datetime import datetime, timedelta
from models import AttackLog, db
from sqlalchemy import func


class AttackLogger:
    def log(self, client_ip, method, path, user_agent, attack_type,
            rule_name, matched_content, severity, action, request_data=None):
        log = AttackLog(
            timestamp=datetime.now(),
            client_ip=client_ip,
            method=method,
            path=path,
            user_agent=user_agent,
            attack_type=attack_type,
            rule_name=rule_name,
            matched_content=matched_content,
            severity=severity,
            action=action,
            request_data=request_data
        )
        db.session.add(log)
        db.session.commit()
        return log.id

    def query_logs(self, page=1, per_page=20, attack_type=None,
                   client_ip=None, start_time=None, end_time=None,
                   severity=None):
        query = AttackLog.query
        if attack_type:
            query = query.filter(AttackLog.attack_type == attack_type)
        if client_ip:
            query = query.filter(AttackLog.client_ip.like(f'%{client_ip}%'))
        if severity:
            query = query.filter(AttackLog.severity == severity)
        if start_time:
            query = query.filter(AttackLog.timestamp >= start_time)
        if end_time:
            query = query.filter(AttackLog.timestamp <= end_time)
        total = query.count()
        logs = query.order_by(AttackLog.timestamp.desc()) \
            .offset((page - 1) * per_page).limit(per_page).all()
        return {
            'total': total,
            'page': page,
            'per_page': per_page,
            'list': [log.to_dict() for log in logs]
        }

    def get_dashboard_stats(self):
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_today = AttackLog.query.filter(AttackLog.timestamp >= today).count()
        total_all = AttackLog.query.count()

        type_stats = db.session.query(
            AttackLog.attack_type,
            func.count(AttackLog.id)
        ).filter(AttackLog.timestamp >= today).group_by(AttackLog.attack_type).all()
        type_dist = {t: c for t, c in type_stats}

        sev_stats = db.session.query(
            AttackLog.severity,
            func.count(AttackLog.id)
        ).filter(AttackLog.timestamp >= today).group_by(AttackLog.severity).all()
        sev_dist = {s: c for s, c in sev_stats}

        hourly = []
        for h in range(24):
            hour_start = today + timedelta(hours=h)
            hour_end = today + timedelta(hours=h + 1)
            count = AttackLog.query.filter(
                AttackLog.timestamp >= hour_start,
                AttackLog.timestamp < hour_end
            ).count()
            hourly.append({'hour': f'{h:02d}:00', 'count': count})

        top_ips = db.session.query(
            AttackLog.client_ip,
            func.count(AttackLog.id).label('cnt')
        ).filter(AttackLog.timestamp >= today).group_by(AttackLog.client_ip) \
            .order_by(func.count(AttackLog.id).desc()).limit(10).all()
        top_ip_list = [{'ip': ip, 'count': cnt} for ip, cnt in top_ips]

        recent_attacks = [log.to_dict() for log in AttackLog.query
                          .order_by(AttackLog.timestamp.desc()).limit(10).all()]

        return {
            'total_today': total_today,
            'total_all': total_all,
            'type_distribution': type_dist,
            'severity_distribution': sev_dist,
            'hourly_trend': hourly,
            'top_ips': top_ip_list,
            'recent_attacks': recent_attacks
        }


attack_logger = AttackLogger()
