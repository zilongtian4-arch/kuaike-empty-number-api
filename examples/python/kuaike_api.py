#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快客检测 空号检测 API 示例（Python 3，只用标准库）。

用法：
    export KUAIKE_API_KEY=您的密钥
    python3 kuaike_api.py balance
    python3 kuaike_api.py empty numbers.txt        # 空号检测（每行一个号码，至少 2000 个）
    python3 kuaike_api.py empty-plus numbers.txt   # 高级空号检测
    python3 kuaike_api.py realtime 13800138000     # 实时检测，即查即回（1~20 个）

接口文档：https://kuaikejiance.com/api-docs
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("KUAIKE_API_BASE", "https://kuaikejiance.com/open/v1")


class KuaikeError(Exception):
    def __init__(self, status, code, message):
        super().__init__("HTTP %s code=%s %s" % (status, code, message))
        self.status, self.code, self.message = status, code, message


class KuaikeClient:
    def __init__(self, api_key, base=BASE, timeout=30):
        if not api_key:
            raise ValueError("请先设置 KUAIKE_API_KEY")
        self.api_key, self.base, self.timeout = api_key, base.rstrip("/"), timeout

    def _request(self, method, path, body=None, retries=3):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        for attempt in range(retries + 1):
            req = urllib.request.Request(self.base + path, data=data, method=method, headers={
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json",
            })
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                    status = resp.status
            except urllib.error.HTTPError as e:
                status = e.code
                try:
                    payload = json.loads(e.read().decode("utf-8"))
                except Exception:
                    payload = {"code": e.code, "message": e.reason}
            except (urllib.error.URLError, TimeoutError) as e:
                # 网络问题：带同一个 requestId 重试，不会重复扣额度
                if attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                raise KuaikeError(0, -1, "网络异常：%s" % e)
            # 429 请求太频繁、5xx 临时故障：稍等再试
            if (status == 429 or status >= 500) and attempt < retries:
                time.sleep(1 + attempt)
                continue
            if status >= 400 or payload.get("code") != 0:
                raise KuaikeError(status, payload.get("code"), payload.get("message", ""))
            return payload["data"]

    # ---------- 额度 ----------
    def balance(self):
        return self._request("GET", "/balance")

    # ---------- 空号检测 / 高级空号检测 ----------
    def submit(self, phones, kind="empty", request_id=None):
        """kind: 'empty' 空号检测；'empty-plus' 高级空号检测。返回 taskId。"""
        body = {"phones": list(phones), "requestId": request_id or uuid.uuid4().hex}
        return self._request("POST", "/%s/tasks" % kind, body)["taskId"]

    def task(self, task_id, kind="empty"):
        return self._request("GET", "/%s/tasks/%s" % (kind, task_id))

    def wait(self, task_id, kind="empty", interval=8, max_wait=3600):
        start = time.time()
        while True:
            t = self.task(task_id, kind)
            print("  进度 %s/%s  状态 %s" % (t.get("done"), t.get("total"), t.get("status")), file=sys.stderr)
            if t.get("status") in ("done", "failed"):
                return t
            if time.time() - start > max_wait:
                raise TimeoutError("等待超时，任务编号 %s，可稍后再查" % task_id)
            time.sleep(interval)

    def result(self, task_id, which, kind="empty"):
        """which: active 实号 / empty 空号 / silent 沉默号 / risk 风险号 / stopped 停机（仅空号检测） / unknown 未知"""
        return self._request("GET", "/%s/tasks/%s/result?kind=%s" % (kind, task_id, which))["phones"]

    # ---------- 实时检测 ----------
    def realtime_check(self, phones, request_id=None):
        """即查即回，单次 1~20 个号码。"""
        body = {"phones": list(phones), "requestId": request_id or uuid.uuid4().hex}
        return self._request("POST", "/realtime/check", body)


def read_numbers(path):
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    client = KuaikeClient(os.environ.get("KUAIKE_API_KEY"))
    cmd = sys.argv[1]
    if cmd == "balance":
        print(json.dumps(client.balance(), ensure_ascii=False, indent=2))
    elif cmd in ("empty", "empty-plus"):
        phones = read_numbers(sys.argv[2])
        task_id = client.submit(phones, kind=cmd)
        print("已提交，任务编号", task_id, file=sys.stderr)
        t = client.wait(task_id, kind=cmd)
        print(json.dumps(t, ensure_ascii=False, indent=2))
        if t.get("status") == "done":
            for which, n in (t.get("counts") or {}).items():
                if n:
                    out = "%s_%s.txt" % (task_id, which)
                    with open(out, "w", encoding="utf-8") as f:
                        f.write("\n".join(client.result(task_id, which, kind=cmd)) + "\n")
                    print("  %s：%d 个 → %s" % (which, n, out), file=sys.stderr)
    elif cmd == "realtime":
        print(json.dumps(client.realtime_check(sys.argv[2:]), ensure_ascii=False, indent=2))
    else:
        print(__doc__)


if __name__ == "__main__":
    try:
        main()
    except KuaikeError as e:
        print("调用失败：", e, file=sys.stderr)
        sys.exit(1)
