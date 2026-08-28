#!/usr/bin/env python3
"""庄周 · 系统资源监控 + 服务端运行日志

优先使用 psutil（信息最全）。在未安装 psutil 的 Windows 环境中，
回退到 ctypes 调用原生 API：PDH 取 CPU、GlobalMemoryStatusEx 取内存、
GetDiskFreeSpaceExW 取磁盘、GetIfTable 取网络、Toolhelp32 取进程 Top。
"""

import os
import subprocess
import sys
import threading
import time
from typing import Any

from config import SERVER_LOG

_SYSMON_NET_PREV = {"ts": 0.0, "sent": 0, "recv": 0}


def _server_log(line):
    """追加一行到服务端日志文件（终端流数据源）。"""
    try:
        ts = time.strftime("%H:%M:%S")
        with open(SERVER_LOG, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (ts, line))
    except Exception:
        pass


def get_logs(lines=200):
    """返回服务端日志尾部，供终端流面板展示。"""
    try:
        with open(SERVER_LOG, encoding="utf-8", errors="replace") as f:
            all_lines = f.read().splitlines()
        return {"ok": True, "lines": all_lines[-lines:], "total": len(all_lines)}
    except FileNotFoundError:
        return {"ok": True, "lines": ["(暂无日志)"], "total": 0}
    except Exception as e:
        return {"ok": False, "error": str(e), "lines": []}


# ---------- Windows 原生 fallback（无 psutil 时使用）----------
class _WinSysmon:
    """通过 ctypes 调用 Windows 原生 API 获取系统资源。"""

    _PDH_FMT_DOUBLE = 0x00000200

    def __init__(self):
        self._is_win = sys.platform == "win32"
        if not self._is_win:
            return
        try:
            import ctypes
            from ctypes import wintypes

            self._ctypes = ctypes
            self._wintypes = wintypes
            self._pdh = ctypes.windll.pdh
            self._kernel = ctypes.windll.kernel32
            self._iphlpapi = ctypes.windll.iphlpapi
            self._psapi = ctypes.windll.psapi

            class _PDH_FMT_COUNTERVALUE(ctypes.Structure):
                _fields_ = [("CStatus", wintypes.DWORD), ("DoubleValue", ctypes.c_double)]

            self._PDH_FMT_COUNTERVALUE = _PDH_FMT_COUNTERVALUE
        except Exception as e:
            self._is_win = False
            self._init_err = str(e)

    # ---- CPU ----
    def cpu_percent(self, interval=0.3):
        if not self._is_win:
            return None
        try:
            ctypes, wintypes = self._ctypes, self._wintypes
            query = wintypes.HANDLE()
            counter = wintypes.HANDLE()
            self._pdh.PdhOpenQueryW(None, 0, ctypes.byref(query))
            # 使用英文计数器路径，避免中文系统本地化问题
            if hasattr(self._pdh, "PdhAddEnglishCounterW"):
                self._pdh.PdhAddEnglishCounterW(
                    query, r"\Processor(_Total)\% Processor Time", 0, ctypes.byref(counter)
                )
            else:
                self._pdh.PdhAddCounterW(
                    query, r"\Processor(_Total)\% Processor Time", 0, ctypes.byref(counter)
                )
            self._pdh.PdhCollectQueryData(query)
            time.sleep(interval)
            self._pdh.PdhCollectQueryData(query)
            value = self._PDH_FMT_COUNTERVALUE()
            self._pdh.PdhGetFormattedCounterValue(
                counter, self._PDH_FMT_DOUBLE, None, ctypes.byref(value)
            )
            self._pdh.PdhCloseQuery(query)
            return round(value.DoubleValue, 1)
        except Exception:
            return None

    # ---- 内存 ----
    def memory(self):
        if not self._is_win:
            return None
        try:
            ctypes = self._ctypes
            wintypes = self._wintypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", wintypes.DWORD),
                    ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            self._kernel.GlobalMemoryStatusEx(ctypes.byref(mem))
            total = mem.ullTotalPhys
            avail = mem.ullAvailPhys
            used = total - avail
            return {
                "percent": round((used / total) * 100, 1) if total else 0.0,
                "usedGB": round(used / 1024**3, 1),
                "totalGB": round(total / 1024**3, 1),
                "availableGB": round(avail / 1024**3, 1),
            }
        except Exception:
            return None

    # ---- 磁盘 ----
    def disks(self, paths=None):
        if not self._is_win:
            return []
        if paths is None:
            paths = ["C:\\", "D:\\", "G:\\"]
        ctypes, wintypes = self._ctypes, self._wintypes
        disks = []
        for p in paths:
            try:
                free = ctypes.c_ulonglong()
                total = ctypes.c_ulonglong()
                total_free = ctypes.c_ulonglong()
                ok = self._kernel.GetDiskFreeSpaceExW(
                    p, ctypes.byref(free), ctypes.byref(total), ctypes.byref(total_free)
                )
                if not ok:
                    continue
                used = total.value - free.value
                disks.append(
                    {
                        "mount": p,
                        "percent": round((used / total.value) * 100, 1) if total.value else 0.0,
                        "usedGB": round(used / 1024**3, 1),
                        "totalGB": round(total.value / 1024**3, 1),
                    }
                )
            except Exception:
                pass
        return disks

    # ---- 网络 ----
    def net_io_counters(self):
        if not self._is_win:
            return None
        try:
            ctypes = self._ctypes
            wintypes = self._wintypes

            class MIB_IFROW(ctypes.Structure):
                _fields_ = [
                    ("wszName", wintypes.WCHAR * 256),
                    ("dwIndex", wintypes.DWORD),
                    ("dwType", wintypes.DWORD),
                    ("dwMtu", wintypes.DWORD),
                    ("dwSpeed", wintypes.DWORD),
                    ("dwPhysAddrLen", wintypes.DWORD),
                    ("bPhysAddr", wintypes.BYTE * 8),
                    ("dwAdminStatus", wintypes.DWORD),
                    ("dwOperStatus", wintypes.DWORD),
                    ("dwLastChange", wintypes.DWORD),
                    ("dwInOctets", wintypes.DWORD),
                    ("dwInUcastPkts", wintypes.DWORD),
                    ("dwInNUcastPkts", wintypes.DWORD),
                    ("dwInDiscards", wintypes.DWORD),
                    ("dwInErrors", wintypes.DWORD),
                    ("dwInUnknownProtos", wintypes.DWORD),
                    ("dwOutOctets", wintypes.DWORD),
                    ("dwOutUcastPkts", wintypes.DWORD),
                    ("dwOutNUcastPkts", wintypes.DWORD),
                    ("dwOutDiscards", wintypes.DWORD),
                    ("dwOutErrors", wintypes.DWORD),
                    ("dwOutQLen", wintypes.DWORD),
                    ("dwDescrLen", wintypes.DWORD),
                    ("bDescr", wintypes.BYTE * 256),
                ]

            class MIB_IFTABLE(ctypes.Structure):
                _fields_ = [("dwNumEntries", wintypes.DWORD), ("table", MIB_IFROW * 512)]

            # 先取表大小
            size = wintypes.DWORD(ctypes.sizeof(MIB_IFTABLE))
            buf = ctypes.create_string_buffer(size.value)
            r = self._iphlpapi.GetIfTable(ctypes.byref(buf), ctypes.byref(size), 0)
            if r != 0:
                return None
            table = ctypes.cast(buf, ctypes.POINTER(MIB_IFTABLE)).contents
            sent = recv = 0
            for i in range(table.dwNumEntries):
                row = table.table[i]
                # 排除 loopback (24) 和 tunnel 等虚拟接口，只累加以太网/Wi-Fi
                if row.dwType in (6, 71):  # MIB_IF_TYPE_ETHERNET / IF_TYPE_IEEE80211
                    sent += row.dwOutOctets
                    recv += row.dwInOctets
            return {"bytes_sent": sent, "bytes_recv": recv}
        except Exception:
            return None

    # ---- 运行时间 ----
    def uptime(self):
        if not self._is_win:
            return None
        try:
            return int(self._kernel.GetTickCount64() / 1000)
        except Exception:
            return None

    # ---- 进程 Top ----
    def top_procs(self, n=6):
        if not self._is_win:
            return [], []
        try:
            ctypes, wintypes = self._ctypes, self._wintypes
            TH32CS_SNAPPROCESS = 0x00000002
            hSnap = self._kernel.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if not hSnap:
                return [], []

            class PROCESSENTRY32(ctypes.Structure):
                _fields_ = [
                    ("dwSize", wintypes.DWORD),
                    ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_void_p),
                    ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD),
                    ("szExeFile", wintypes.CHAR * 260),
                ]

            pe = PROCESSENTRY32()
            pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
            procs = []
            if self._kernel.Process32First(hSnap, ctypes.byref(pe)):
                while True:
                    pid = pe.th32ProcessID
                    name = pe.szExeFile.decode("gbk", "replace") if pe.szExeFile else "?"
                    if name and pid not in (0, 4):
                        mem_mb = self._proc_mem(pid)
                        procs.append({"pid": pid, "name": name, "cpu": 0.0, "mem_mb": mem_mb})
                    if not self._kernel.Process32Next(hSnap, ctypes.byref(pe)):
                        break
            self._kernel.CloseHandle(hSnap)
            procs.sort(key=lambda x: x["mem_mb"], reverse=True)
            top_mem = procs[:n]
            # CPU 需要两次采样，这里只按内存近似；返回 mem 字段保持与 psutil 统一百分比
            total_mem = (self.memory() or {}).get("totalGB", 1) * 1024
            return (
                [{"pid": p["pid"], "name": p["name"], "cpu": 0.0, "mem": round(p["mem_mb"] / total_mem * 100, 1)} for p in top_mem],
                [{"pid": p["pid"], "name": p["name"], "cpu": 0.0, "mem": round(p["mem_mb"] / total_mem * 100, 1)} for p in top_mem],
            )
        except Exception:
            return [], []

    def _proc_mem(self, pid):
        try:
            ctypes, wintypes = self._ctypes, self._wintypes
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010
            h = self._kernel.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
            if not h:
                return 0
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]
            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            self._psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)
            self._kernel.CloseHandle(h)
            return pmc.WorkingSetSize / (1024 * 1024)
        except Exception:
            return 0


# ---------- 公共接口 ----------
def get_sysmon():
    """采集本机系统资源快照，返回前端 sysmon 面板所需结构。"""
    snap = {"ok": True, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "fallback": False}
    try:
        import psutil
    except Exception as e:
        psutil = None
        snap["psutil_missing"] = str(e)

    if psutil:
        _fill_with_psutil(snap)
    else:
        snap["fallback"] = True
        _fill_with_winapi(snap)

    # GPU 两种路径都用 nvidia-smi 子进程
    snap["gpu"] = _gpu_nvidia()
    return snap


def _fill_with_psutil(snap):
    import psutil

    cpu_per_core = psutil.cpu_percent(interval=0.3, percpu=True)
    cpu_freq = psutil.cpu_freq()
    snap["cpu"] = {
        "percent": round(sum(cpu_per_core) / max(len(cpu_per_core), 1), 1),
        "perCore": [round(x, 1) for x in cpu_per_core],
        "cores": len(cpu_per_core),
        "freqMHz": int(cpu_freq.current) if cpu_freq else 0,
    }

    vm = psutil.virtual_memory()
    snap["mem"] = {
        "percent": round(vm.percent, 1),
        "usedGB": round(vm.used / 1024**3, 1),
        "totalGB": round(vm.total / 1024**3, 1),
        "availableGB": round(vm.available / 1024**3, 1),
    }

    disks = []
    for p in ("C:\\", "D:\\", "G:\\"):
        try:
            du = psutil.disk_usage(p)
            disks.append(
                {
                    "mount": p,
                    "percent": round(du.percent, 1),
                    "usedGB": round(du.used / 1024**3, 1),
                    "totalGB": round(du.total / 1024**3, 1),
                }
            )
        except Exception:
            pass
    snap["disks"] = disks

    global _SYSMON_NET_PREV
    now_ts = time.time()
    net = psutil.net_io_counters()
    prev = _SYSMON_NET_PREV
    dt = now_ts - prev["ts"]
    if dt > 0 and prev["ts"] > 0:
        up = max(0.0, (net.bytes_sent - prev["sent"]) / dt)
        down = max(0.0, (net.bytes_recv - prev["recv"]) / dt)
    else:
        up = down = 0.0
    _SYSMON_NET_PREV.update({"ts": now_ts, "sent": net.bytes_sent, "recv": net.bytes_recv})
    snap["net"] = {
        "upBps": int(up),
        "downBps": int(down),
        "sentGB": round(net.bytes_sent / 1024**3, 2),
        "recvGB": round(net.bytes_recv / 1024**3, 2),
    }

    procs = []
    for pr in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            nm = pr.info["name"] or "?"
            if nm in ("System Idle Process", "System") or pr.info["pid"] in (0, 4):
                continue
            procs.append(
                {
                    "pid": pr.info["pid"],
                    "name": nm,
                    "cpu": round(pr.info["cpu_percent"] or 0, 1),
                    "mem": round(pr.info["memory_percent"] or 0, 1),
                }
            )
        except Exception:
            pass
    procs.sort(key=lambda x: x["cpu"], reverse=True)
    snap["topCpu"] = procs[:6]
    procs.sort(key=lambda x: x["mem"], reverse=True)
    snap["topMem"] = procs[:6]

    bt = psutil.boot_time()
    snap["uptimeSec"] = int(time.time() - bt)


def _fill_with_winapi(snap):
    win = _WinSysmon()
    if not win._is_win:
        snap.update({"ok": False, "error": "非 Windows 平台且未安装 psutil，无法采集资源"})
        return

    cpu = win.cpu_percent(interval=0.3)
    snap["cpu"] = {
        "percent": cpu if cpu is not None else 0.0,
        "perCore": [cpu if cpu is not None else 0.0],
        "cores": os.cpu_count() or 1,
        "freqMHz": 0,
    }

    mem = win.memory() or {"percent": 0, "usedGB": 0, "totalGB": 0, "availableGB": 0}
    snap["mem"] = mem

    snap["disks"] = win.disks()

    global _SYSMON_NET_PREV
    now_ts = time.time()
    net = win.net_io_counters() or {"bytes_sent": 0, "bytes_recv": 0}
    prev = _SYSMON_NET_PREV
    dt = now_ts - prev["ts"]
    if dt > 0 and prev["ts"] > 0:
        up = max(0.0, (net["bytes_sent"] - prev["sent"]) / dt)
        down = max(0.0, (net["bytes_recv"] - prev["recv"]) / dt)
    else:
        up = down = 0.0
    _SYSMON_NET_PREV.update({"ts": now_ts, "sent": net["bytes_sent"], "recv": net["bytes_recv"]})
    snap["net"] = {
        "upBps": int(up),
        "downBps": int(down),
        "sentGB": round(net["bytes_sent"] / 1024**3, 2),
        "recvGB": round(net["bytes_recv"] / 1024**3, 2),
    }

    top_cpu, top_mem = win.top_procs(6)
    snap["topCpu"] = top_cpu
    snap["topMem"] = top_mem
    snap["uptimeSec"] = win.uptime() or 0


def _gpu_nvidia():
    gpu = {"available": False}
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            parts = [x.strip() for x in out.stdout.strip().split(",")]
            gpu = {
                "available": True,
                "name": parts[0],
                "util": int(float(parts[1])),
                "memUsedMB": int(float(parts[2])),
                "memTotalMB": int(float(parts[3])),
                "tempC": int(float(parts[4])),
            }
    except Exception as e:
        gpu["error"] = str(e)
    return gpu
