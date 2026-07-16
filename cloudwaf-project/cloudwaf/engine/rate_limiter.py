import time
from collections import defaultdict
from datetime import datetime
from engine.access_control import access_control


class RateLimiter:
    def __init__(self):
        self._request_counts = defaultdict(list)
        self._not_found_counts = defaultdict(list)
        self._scan_blocked = set()

    def check_cc(self, ip, rate_limit=60, window=60, block_duration=300):
        now = time.time()
        window_start = now - window
        counts = self._request_counts[ip]
        counts = [t for t in counts if t > window_start]
        counts.append(now)
        self._request_counts[ip] = counts
        if len(counts) > rate_limit:
            access_control.add_blacklist(ip, reason=f"CC攻击防护: {len(counts)}次/{window}秒", duration=block_duration)
            return True
        return False

    def check_scan(self, ip, status_code, threshold=20, window=60, block_duration=600):
        if status_code != 404:
            return False
        now = time.time()
        window_start = now - window
        counts = self._not_found_counts[ip]
        counts = [t for t in counts if t > window_start]
        counts.append(now)
        self._not_found_counts[ip] = counts
        if len(counts) >= threshold:
            access_control.add_blacklist(ip, reason=f"扫描行为检测: {len(counts)}次404/{window}秒", duration=block_duration)
            self._scan_blocked.add(ip)
            return True
        return False

    def get_stats(self, ip):
        now = time.time()
        req_1min = len([t for t in self._request_counts.get(ip, []) if t > now - 60])
        req_5min = len([t for t in self._request_counts.get(ip, []) if t > now - 300])
        nf_1min = len([t for t in self._not_found_counts.get(ip, []) if t > now - 60])
        return {
            'ip': ip,
            'requests_1min': req_1min,
            'requests_5min': req_5min,
            'not_found_1min': nf_1min,
            'scan_blocked': ip in self._scan_blocked
        }

    def cleanup_old_entries(self):
        now = time.time()
        cutoff = now - 600
        for ip in list(self._request_counts.keys()):
            self._request_counts[ip] = [t for t in self._request_counts[ip] if t > cutoff]
            if not self._request_counts[ip]:
                del self._request_counts[ip]
        for ip in list(self._not_found_counts.keys()):
            self._not_found_counts[ip] = [t for t in self._not_found_counts[ip] if t > cutoff]
            if not self._not_found_counts[ip]:
                del self._not_found_counts[ip]


rate_limiter = RateLimiter()
