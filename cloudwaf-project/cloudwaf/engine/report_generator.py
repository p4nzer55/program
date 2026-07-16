"""
防护报告生成模块
用于生成日报、月报、年报等防护统计报告
"""
from datetime import datetime, timedelta
from models import db, AttackLog, Site, Report
from sqlalchemy import func
import json
import os


class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        self.report_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
        os.makedirs(self.report_dir, exist_ok=True)

    def _get_date_range(self, report_type, date=None):
        """
        根据报告类型获取日期范围

        report_type: daily/weekly/monthly/yearly
        date: 基准日期（默认为今天）
        """
        if not date:
            date = datetime.now()

        if report_type == 'daily':
            start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif report_type == 'weekly':
            start = date - timedelta(days=date.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
        elif report_type == 'monthly':
            start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # 获取下个月第一天
            if date.month == 12:
                end = datetime(date.year + 1, 1, 1)
            else:
                end = datetime(date.year, date.month + 1, 1)
        elif report_type == 'yearly':
            start = date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = datetime(date.year + 1, 1, 1)
        else:
            start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)

        return start, end

    def generate_daily_report(self, site_id, date=None):
        """生成单站点日报"""
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        start, end = self._get_date_range('daily', date)

        return self._generate_report_data(site_id, start, end, 'daily')

    def generate_weekly_report(self, site_id, date=None):
        """生成单站点周报"""
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        start, end = self._get_date_range('weekly', date)

        return self._generate_report_data(site_id, start, end, 'weekly')

    def generate_monthly_report(self, site_id, year=None, month=None):
        """生成单站点月报"""
        if year and month:
            date = datetime(year, month, 1)
        else:
            date = datetime.now()
        start, end = self._get_date_range('monthly', date)

        return self._generate_report_data(site_id, start, end, 'monthly')

    def generate_yearly_report(self, site_id, year=None):
        """生成单站点年报"""
        if year:
            date = datetime(year, 1, 1)
        else:
            date = datetime.now()
        start, end = self._get_date_range('yearly', date)

        return self._generate_report_data(site_id, start, end, 'yearly')

    def generate_summary_report(self, start_date, end_date, site_ids=None):
        """
        生成汇总报告（多站点）

        start_date: 开始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        site_ids: 站点ID列表，None表示全部站点
        """
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        return self._generate_report_data(None, start_date, end_date, 'summary', site_ids)

    def _generate_report_data(self, site_id, start_date, end_date, report_type, site_ids=None):
        """生成报告数据"""
        query = AttackLog.query.filter(
            AttackLog.timestamp >= start_date,
            AttackLog.timestamp < end_date
        )

        if site_id:
            site = Site.query.get(site_id)
            if not site:
                return None
            query = query.filter(AttackLog.path.contains(site.domain))
            site_name = site.name
        elif site_ids:
            # 多站点过滤
            sites = Site.query.filter(Site.id.in_(site_ids)).all()
            domains = [s.domain for s in sites]
            site_name = '汇总报告'
            # 这里简化处理，实际应该根据site关联查询
        else:
            site_name = '全局报告'

        total_attacks = query.count()

        # 按攻击类型统计
        type_stats = db.session.query(
            AttackLog.attack_type,
            func.count(AttackLog.id)
        ).filter(
            AttackLog.timestamp >= start_date,
            AttackLog.timestamp < end_date
        ).group_by(AttackLog.attack_type).all()

        type_distribution = {t: c for t, c in type_stats}

        # 按严重程度统计
        severity_stats = db.session.query(
            AttackLog.severity,
            func.count(AttackLog.id)
        ).filter(
            AttackLog.timestamp >= start_date,
            AttackLog.timestamp < end_date
        ).group_by(AttackLog.severity).all()

        severity_distribution = {s: c for s, c in severity_stats}

        # 按操作统计（拦截/放行）
        action_stats = db.session.query(
            AttackLog.action,
            func.count(AttackLog.id)
        ).filter(
            AttackLog.timestamp >= start_date,
            AttackLog.timestamp < end_date
        ).group_by(AttackLog.action).all()

        action_distribution = {a: c for a, c in action_stats}

        # Top攻击IP
        top_ips = db.session.query(
            AttackLog.client_ip,
            func.count(AttackLog.id).label('cnt')
        ).filter(
            AttackLog.timestamp >= start_date,
            AttackLog.timestamp < end_date
        ).group_by(AttackLog.client_ip).order_by(
            func.count(AttackLog.id).desc()
        ).limit(20).all()

        top_attackers = [{'ip': ip, 'count': cnt} for ip, cnt in top_ips]

        # 时间趋势（按小时/天）
        time_trend = self._get_time_trend(start_date, end_date, report_type)

        # 保存报告记录
        report = Report(
            report_type=report_type,
            site_id=site_id,
            start_date=start_date,
            end_date=end_date,
            data={
                'site_name': site_name,
                'total_attacks': total_attacks,
                'type_distribution': type_distribution,
                'severity_distribution': severity_distribution,
                'action_distribution': action_distribution,
                'top_attackers': top_attackers,
                'time_trend': time_trend
            }
        )
        db.session.add(report)
        db.session.commit()

        return report

    def _get_time_trend(self, start_date, end_date, report_type):
        """获取时间趋势数据"""
        trend = []

        if report_type in ['daily', 'summary']:
            # 按小时统计
            current = start_date
            hour = 0
            while current < end_date and hour < 24:
                hour_end = current + timedelta(hours=1)
                count = AttackLog.query.filter(
                    AttackLog.timestamp >= current,
                    AttackLog.timestamp < hour_end
                ).count()
                trend.append({
                    'time': f"{hour:02d}:00",
                    'count': count
                })
                current = hour_end
                hour += 1

        elif report_type == 'weekly':
            # 按天统计
            current = start_date
            day = 0
            while current < end_date and day < 7:
                day_end = current + timedelta(days=1)
                count = AttackLog.query.filter(
                    AttackLog.timestamp >= current,
                    AttackLog.timestamp < day_end
                ).count()
                trend.append({
                    'time': current.strftime('%Y-%m-%d'),
                    'count': count
                })
                current = day_end
                day += 1

        elif report_type == 'monthly':
            # 按天统计
            current = start_date
            while current < end_date:
                day_end = current + timedelta(days=1)
                count = AttackLog.query.filter(
                    AttackLog.timestamp >= current,
                    AttackLog.timestamp < day_end
                ).count()
                trend.append({
                    'time': current.strftime('%m-%d'),
                    'count': count
                })
                current = day_end

        elif report_type == 'yearly':
            # 按月统计
            current = start_date
            while current < end_date:
                if current.month == 12:
                    month_end = datetime(current.year + 1, 1, 1)
                else:
                    month_end = datetime(current.year, current.month + 1, 1)

                count = AttackLog.query.filter(
                    AttackLog.timestamp >= current,
                    AttackLog.timestamp < month_end
                ).count()

                trend.append({
                    'time': current.strftime('%Y-%m'),
                    'count': count
                })

                current = month_end

        return trend

    def get_reports(self, report_type=None, site_id=None, limit=50):
        """获取报告列表"""
        query = Report.query
        if report_type:
            query = query.filter_by(report_type=report_type)
        if site_id:
            query = query.filter_by(site_id=site_id)
        return query.order_by(Report.created_at.desc()).limit(limit).all()

    def export_to_json(self, report_id):
        """导出为JSON格式"""
        report = Report.query.get_or_404(report_id)
        return report.data

    def export_to_csv(self, report_id):
        """导出为CSV格式"""
        report = Report.query.get_or_404(report_id)
        data = report.data

        csv_lines = []

        # 基本信息
        csv_lines.append(f"CloudWAF 防护报告")
        csv_lines.append(f"报告类型: {report.report_type}")
        csv_lines.append(f"时间范围: {report.start_date} ~ {report.end_date}")
        if data.get('site_name'):
            csv_lines.append(f"站点: {data['site_name']}")
        csv_lines.append(f"总攻击数: {data['total_attacks']}")
        csv_lines.append("")

        # 攻击类型分布
        csv_lines.append("攻击类型分布,数量")
        for attack_type, count in data.get('type_distribution', {}).items():
            csv_lines.append(f"{attack_type},{count}")
        csv_lines.append("")

        # 严重程度分布
        csv_lines.append("严重程度,数量")
        for severity, count in data.get('severity_distribution', {}).items():
            csv_lines.append(f"{severity},{count}")
        csv_lines.append("")

        # Top攻击IP
        csv_lines.append("Top攻击IP,攻击次数")
        for attacker in data.get('top_attackers', []):
            csv_lines.append(f"{attacker['ip']},{attacker['count']}")

        return '\n'.join(csv_lines)


report_generator = ReportGenerator()