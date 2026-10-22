#!/usr/bin/env python3
# use-family managed CLI
"""Upgrade the installed use family. Python 3 standard library; no shell execution."""
import argparse
import contextlib
import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import io
import hashlib
import tarfile
import urllib.request
import tempfile
import plistlib
import xml.etree.ElementTree as ET
from pathlib import Path

VERSION = '0.15.4'
MARKER = '# use-family managed CLI'
NAMES = 'android-use chrome-use cookie-use iphone-use mail-use wechat-use discord-use profile-use bitwarden-use chatgpt-use image-use memory-use ocs sflow message-use paste-use motion-use thermo-use switch-use'.split()
ALIASES = {'thermo-use':['thermo-use','thermo'], 'bitwarden-use':['bitwarden-use','bwu']}
HOME = Path.home()
SCRIPT = Path(__file__).resolve()
try:
    _metadata=json.loads((SCRIPT.parent/'installed.json').read_text(encoding='utf-8-sig'))
    _paths=_metadata.get('paths',{}) if _metadata.get('installPath')==str(SCRIPT.parent) else {}
except (OSError,ValueError): _paths={}
def setting(key,default):
    value=os.environ.get(key,_paths.get(key,default))
    return Path(value).expanduser().resolve()
STATE = setting('USE_MANAGER_STATE',HOME/'.local/state/use-family')
BASE = setting('USE_FAMILY_DIR',HOME/'.agents/use-family')
CONFIG = STATE/'config.json'
INSTALL = setting('USE_MANAGER_HOME',HOME/'.local/share/use-family')
BIN = setting('USE_MANAGER_BIN',HOME/'.local/bin')


def choose_language(explicit=None):
    value=explicit or os.environ.get('USE_LANG') or 'auto'
    if value=='auto':
        locale=next((os.environ[k] for k in ('LC_ALL','LC_MESSAGES','LANG') if os.environ.get(k)), '')
        if locale.split('.')[0] in ('C','POSIX'):return 'en'
        value=os.environ.get('LANGUAGE') or locale or 'en'
    return 'zh' if value.lower().startswith('zh') else 'en'


UI_LANG=choose_language()
TEXT={
    'description':('Upgrade installed use tools and plugins.','升级已安装的 use 工具和插件。'),
    'scan':('Reading installed tools…','读取已安装的工具…'),
    'copies':('Checking skill copies…','核对技能副本…'),
    'check_tool':('Checking {name}…','检查 {name}…'),
    'upgrade_tool':('Checking and upgrading {name}…','检查并升级 {name}…'),
    'skill_progress':('Updating skill: {name}…','更新技能：{name}…'),
    'codex_progress':('Updating Codex plugins: {name}…','更新 Codex 插件：{name}…'),
    'claude_progress':('Updating Claude plugin: {name}…','更新 Claude 插件：{name}…'),
    'verify':('Verifying results and retained skill copies…','核对升级结果和保留的技能副本…'),
    'not_due':('The next automatic upgrade is not due yet.','尚未到下次自动升级时间。'),
    'disabled':('Automatic upgrades are disabled or suppressed by the environment.','自动升级未启用或已被环境设置暂停。'),
    'checked':('Checked {count} tools','已检查 {count} 个工具'),
    'updated':('{count} updated','{count} 个已更新'),
    'available':('{count} updates available','{count} 个可更新'),
    'failed_count':('{count} failed','{count} 个失败'),
    'attention':('{count} need attention','{count} 个需处理'),
    'deferred':('{count} deferred','{count} 个暂缓'),
    'no_updates':('No updates needed','暂无更新'),
    'preserved':('Left {copies} skill copies of {tools} tools untouched; they differ from every known release','{tools} 个工具的 {copies} 份技能副本与已知发布版都不同，未覆盖'),
    'details':('Details: {command} · log: {path}','详情：{command} · 日志：{path}'),
    'reason_owner_failed':('upgrade command failed','升级命令失败'),
    'reason_cli_broken':('does not start','无法启动'),
    'reason_diverged':('local commits diverged from upstream; checkout kept','本地提交与上游历史已分叉，无法安全快进；已保留本地内容'),
    'reason_dirty':('checkout has local changes or is unreadable; not pulled','仓库有未提交改动或无法读取；未拉取'),
    'exit_code':(' (exit {code})','（退出码 {code}）'),
    'new_session':('Plugin updates take effect in a new session.','插件更新在新会话中生效。'),
    'full_details':('Full details:','完整明细：'),
    'no_report':('No upgrade report yet; run use upgrade first','尚无升级报告，请先运行 use upgrade'),
    'fallback_reason':('Further inspection is required','需要进一步检查'),
    'failed_reason':('Command failed; see the private log','命令失败，详见私有日志'),
    'rate_group':('GitHub version checks are rate limited; {count} CLI upgrades deferred:','GitHub 版本检查被限流，暂缓 {count} 个 CLI 升级：'),
    'rate_tip':('Installed versions were preserved. Retry after GitHub resets the limit.','已保留安装版本，等待 GitHub 限额恢复后再试。'),
    'blocked_group':('Remote version checks unavailable for {count} CLIs:','{count} 个 CLI 的远端版本检查不可用：'),
    'cli':('CLI','CLI'),'app':('App','App'),'manager':('manager','管理器'),
    'plugin':('Claude plugin','Claude 插件'),'codex-plugin':('Codex plugin','Codex 插件'),
    'skill':('skill','技能'),'marketplace':('marketplace','插件市场'),
    'status_updated':('updated','已更新'),'status_available':('update available','可更新'),
    'status_current':('up to date','已是最新'),'status_completed':('completed','已完成'),
    'status_failed':('failed','失败'),'status_manual':('retained; review required','已保留，需检查'),
    'status_unverified':('not verified','未确认'),'status_pending':('pending','等待完成'),
    'status_owner-managed':('installer managed','由安装器维护'),'status_installed':('installed','已安装'),
    'help':('show this help message and exit','显示帮助并退出'),
    'help_version':('show the manager version and exit','显示管理器版本并退出'),
    'help_lang':('output language (default: USE_LANG or terminal locale)','输出语言（默认跟随 USE_LANG 或终端语言）'),
    'help_install':('install the manager without installing missing family tools','安装管理器，不补装其他家族工具'),
    'help_local':('install from this trusted checkout or plugin','从这个可信工作区或插件安装'),
    'help_auto_flag':('enable daily automatic upgrades after installation','安装后开启每日自动升级'),
    'help_upgrade':('upgrade installed family CLIs, skills and plugins','升级已安装的家族 CLI、技能和插件'),
    'help_names':('optional family members; default: all installed members','可选的成员名称，默认处理所有已安装成员'),
    'help_check':('check versions without running upgrades','仅检查版本，不执行升级'),
    'help_json':('write stable machine-readable JSON','输出字段稳定的机器可读 JSON'),
    'help_verbose':('show every channel result and preserved path','显示各渠道结果和保留目录'),
    'help_report':('read the last result without running another upgrade','查看上次结果，不重新执行升级'),
    'help_status':('show installed versions and recorded state as JSON','以 JSON 显示已安装版本和记录状态'),
    'help_auto':('enable, disable or inspect daily background upgrades','开启、关闭或查看每日后台升级'),
    'help_hours':('minimum hours between automatic attempts (default: 24)','自动升级的最短间隔小时数（默认 24）'),
    'help_action':('enable, disable or status','enable 开启，disable 关闭，status 查看'),
    'error':('Error: {message}','错误：{message}'),
}


def tr(key,**values):
    text=TEXT[key][UI_LANG=='zh'].format(**values)
    if UI_LANG=='en':
        if values.get('count')==1:
            for plural,singular in (('tools','tool'),('updates available','update available'),('need attention','needs attention'),('CLI upgrades','CLI upgrade'),('CLIs','CLI')):text=text.replace(plural,singular)
        if values.get('copies')==1:text=text.replace('skill copies','skill copy')
        if values.get('tools')==1:text=text.replace('tools untouched','tool untouched')
    return text


class Parser(argparse.ArgumentParser):
    def __init__(self,*args,**kwargs):
        kwargs['add_help']=False
        super().__init__(*args,**kwargs)
        self.add_argument('-h','--help',action='help',help=tr('help'))
        if UI_LANG=='zh':self._positionals.title='命令和参数';self._optionals.title='选项'
    def format_usage(self):return super().format_usage().replace('usage:', '用法:' if UI_LANG=='zh' else 'usage:')
    def format_help(self):return super().format_help().replace('usage:', '用法:' if UI_LANG=='zh' else 'usage:')
    def error(self,message):
        self.print_usage(sys.stderr)
        self.exit(2,tr('error',message=human_error(message))+'\n')


def human_error(message):
    if UI_LANG=='en':return message
    translations={
        'No upgrade report yet; run use upgrade first':tr('no_report'),
        'No stable use manager release found':'未找到稳定版管理器发布包',
        'Use archive checksum mismatch; nothing installed':'发布包校验失败，未安装任何内容',
        'Use archive version/owner mismatch':'发布包版本或来源不符',
        'Cannot read installed Claude plugins; no plugin changes attempted':'无法读取 Claude 已安装插件，未修改插件',
        'Unsupported Codex plugin inventory schema':'无法识别 Codex 插件清单格式',
        'Invalid scheduler context':'后台任务上下文无效',
        'Invalid scheduler environment':'后台任务环境无效',
        'Cannot read the use release metadata':'无法读取管理器发布信息',
        'Use release is missing its archive/checksum':'发布包缺少文件或校验值',
        'Invalid use archive member':'发布包内容格式无效',
        'Another unmanaged use command is already on PATH; left it untouched':'PATH 中已有其他来源的 use 命令，未覆盖',
        'Refusing to replace an unmanaged use executable: ':'已保留非本管理器维护的程序：',
        'Codex plugin inventory unavailable; native refresh not attempted':'无法读取 Codex 插件清单，未执行刷新',
        'Another use upgrade is running; no second upgrade started':'已有升级任务正在运行，未重复启动',
        'Thermo appcast has no release version':'Thermo 更新源未提供版本',
        'Unknown family member: ':'未知的家族成员：',
        'Install use before enabling a persistent schedule':'请先安装 use，再开启后台任务',
        'Scheduler context requires absolute manager paths':'后台任务的管理器路径必须是绝对路径',
        'Thermo App needs its owner update path; CLI is unavailable':'Thermo App 需要官方更新入口，但未找到 CLI',
        'Registered scheduler belongs to another installation; disable it there before changing paths':'已有后台任务属于另一套安装，请先在那套安装中关闭',
        'Cannot enable launch agent: ':'无法启用 launchd 任务：',
        'Automatic scheduling is unsupported on ':'此系统不支持自动调度：',
        'Scheduler context is only for automatic runs':'后台任务上下文仅供自动升级使用',
        'Cannot reload user systemd: ':'无法重新加载用户 systemd：',
        'Installed use, but automatic scheduling failed: ':'use 已安装，但后台任务注册失败：',
        'Scheduler operation failed; configuration is not enabled: ':'后台任务操作失败，未开启配置：',
        '--automatic cannot be combined with --check':'--automatic 不能与 --check 一起使用',
        '--hours must be at least 1':'--hours 必须至少为 1',
        'unrecognized arguments: ':'无法识别的参数：',
        'the following arguments are required: ':'缺少必需参数：',
    }
    for source,target in translations.items():
        if message.startswith(source):return target+message[len(source):]
    return message


def fetch(url):
    request=urllib.request.Request(url,headers={'User-Agent':'use-family/'+VERSION})
    with urllib.request.urlopen(request,timeout=30) as response: return response.read()


def release():
    url='https://api.github.com/repos/leeguooooo/plugins/releases/latest'
    if shutil.which('gh'):
        code,text=run(['gh','api','repos/leeguooooo/plugins/releases/latest'],timeout=30)
        if code: raise RuntimeError('Cannot read the use release metadata')
        data=json.loads(text)
    else: data=json.loads(fetch(url))
    match=re.fullmatch(r'use-v(\d+\.\d+\.\d+)',data.get('tag_name',''))
    if not match or data.get('draft') or data.get('prerelease'): raise RuntimeError('No stable use manager release found')
    return match.group(1),data


def release_script(data):
    tag=data['tag_name']; name=tag+'.tar.gz'
    assets={a['name']:a['browser_download_url'] for a in data.get('assets',[])}
    for n in (name,name+'.sha256'):
        if n not in assets or not assets[n].startswith('https://github.com/leeguooooo/plugins/releases/download/'+tag+'/'):
            raise RuntimeError('Use release is missing its archive/checksum')
    archive=fetch(assets[name]); checksum=fetch(assets[name+'.sha256']).decode().split()
    if len(checksum)!=2 or checksum[1]!=name or hashlib.sha256(archive).hexdigest()!=checksum[0]: raise RuntimeError('Use archive checksum mismatch; nothing installed')
    with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
        member=tar.getmember('use.py')
        if not member.isfile() or member.size>2_000_000: raise RuntimeError('Invalid use archive member')
        return tar.extractfile(member).read()


def _install_bytes(content,expected):
    text=content.decode('utf-8')
    if MARKER not in text or not re.search(r"^VERSION = ['\"]"+re.escape(expected)+r"['\"]\r?$",text,re.M): raise RuntimeError('Use archive version/owner mismatch')
    compile(text,'use.py','exec')
    target=INSTALL/'use.py'
    launcher=BIN/('use.cmd' if os.name=='nt' else 'use')
    existing=shutil.which('use')
    if existing and Path(existing).resolve()!=launcher.resolve():
        with open(existing,'rb') as f: owned=MARKER.encode() in f.read(512)
        if not owned: raise RuntimeError('Another unmanaged use command is already on PATH; left it untouched')
    for f in (target,launcher):
        if f.exists() and MARKER not in f.read_text(encoding='utf-8',errors='replace'): raise RuntimeError('Refusing to replace an unmanaged use executable: '+str(f))
    if target.exists():
        old=re.search(r"^VERSION = ['\"](\d+\.\d+\.\d+)['\"]$",target.read_text(encoding='utf-8-sig'),re.M)
        if old and tuple(map(int,old.group(1).split('.')))>tuple(map(int,expected.split('.'))):
            content=target.read_bytes(); expected=old.group(1)
    INSTALL.mkdir(parents=True,exist_ok=True); BIN.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix('.partial'); temp.write_bytes(content); os.replace(temp,target)
    if os.name=='nt':
        # cmd.exe requires CRLF. Never run the scheduler through cmd; it uses Python directly.
        wrapper='@echo off\r\nREM '+MARKER+'\r\n"'+sys.executable.replace('%','%%')+'" "'+str(target).replace('%','%%')+'" %*\r\n'
    else: wrapper='#!/usr/bin/env python3\n'+MARKER+'\nimport runpy\nrunpy.run_path('+repr(str(target))+',run_name="__main__")\n'
    temp=launcher.with_name(launcher.name+'.partial'); temp.write_bytes(wrapper.encode())
    if os.name!='nt': temp.chmod(0o755)
    os.replace(temp,launcher)
    save(INSTALL/'installed.json',dict(version=expected,sha256=hashlib.sha256(content).hexdigest(),installPath=str(INSTALL),paths=dict(USE_MANAGER_STATE=str(STATE),USE_MANAGER_HOME=str(INSTALL),USE_MANAGER_BIN=str(BIN),USE_FAMILY_DIR=str(BASE))))
    return str(launcher)


def self_upgrade(report,check):
    if SCRIPT != INSTALL/'use.py': return  # source checkout/plugin bootstrap; do not edit development code.
    try:
        latest,data=release()
        if check: status='available' if tuple(map(int,latest.split('.')))>tuple(map(int,VERSION.split('.'))) else 'current'
        elif tuple(map(int,latest.split('.')))>tuple(map(int,VERSION.split('.'))):
            install_bytes(release_script(data),latest); status='updated'
        else: status='current'
        report['items'].append(dict(name='use',channel='manager',status=status,before=VERSION,target=latest))
    except Exception as e:
        report['items'].append(dict(name='use',channel='manager',status='failed',reason=str(e)))


def install_bytes(content,expected):
    with lock('install'): return _install_bytes(content,expected)


def read(path, default=None):
    try: return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError): return {} if default is None else default


def save(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.partial')
    with open(temp,'w',encoding='utf-8',newline='\n') as out:
        if os.name != 'nt': os.chmod(temp,0o600)
        json.dump(data,out,ensure_ascii=False,indent=2); out.write('\n')
    os.replace(temp,path)


def version(text):
    m = re.search(r'(?<!\d)(\d+\.\d+\.\d+)(?!\d)',str(text))
    return m.group(1) if m else None


UPGRADE_AUTH={}


def github_token():return os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN') or UPGRADE_AUTH.get('GH_TOKEN')


def redact(text):
    secrets=set(UPGRADE_AUTH.values())|{os.environ.get(k,'') for k in ('GH_TOKEN','GITHUB_TOKEN')}
    for secret in sorted((s for s in secrets if s),key=len,reverse=True):text=text.replace(secret,'[redacted]')
    return text


@contextlib.contextmanager
def github_auth():
    previous=dict(UPGRADE_AUTH)
    try:
        token=github_token()
        if not token and shutil.which('gh'):
            code,text=run([shutil.which('gh'),'auth','token','--hostname','github.com'],timeout=5)
            candidate=text.strip()
            if code==0 and re.fullmatch(r'[A-Za-z0-9_]{20,256}',candidate):token=candidate
        if token:UPGRADE_AUTH.update(GH_TOKEN=token,GITHUB_TOKEN=token)
        yield
    finally:
        PROBES.clear()
        UPGRADE_AUTH.clear();UPGRADE_AUTH.update(previous)


def env():
    e = dict(os.environ, USE_NO_UPDATE_CHECK='1', USE_MANAGER_RUNNING='1', GIT_TERMINAL_PROMPT='0')
    for key,value in UPGRADE_AUTH.items():e.setdefault(key,value)
    for n in NAMES: e[n.upper().replace('-','_')+'_NO_UPDATE_CHECK']='1'
    return e


class WindowsJob:
    # Start suspended, assign a private job, then resume. Existing services are never members.
    def __init__(self,process):
        import ctypes as c
        from ctypes import wintypes as w
        class Basic(c.Structure):
            _fields_=[('processTime',c.c_longlong),('jobTime',c.c_longlong),('flags',w.DWORD),('minWorking',c.c_size_t),('maxWorking',c.c_size_t),('active',w.DWORD),('affinity',c.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
        class IO(c.Structure): _fields_=[(x,c.c_ulonglong) for x in ('readOps','writeOps','otherOps','readBytes','writeBytes','otherBytes')]
        class Extended(c.Structure): _fields_=[('basic',Basic),('io',IO),('processMemory',c.c_size_t),('jobMemory',c.c_size_t),('peakProcess',c.c_size_t),('peakJob',c.c_size_t)]
        self.c=c; self.info=Extended(); self.kernel=c.WinDLL('kernel32',use_last_error=True)
        k=self.kernel
        k.CreateJobObjectW.argtypes=[c.c_void_p,w.LPCWSTR]; k.CreateJobObjectW.restype=w.HANDLE
        k.SetInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD]; k.SetInformationJobObject.restype=w.BOOL
        k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]; k.AssignProcessToJobObject.restype=w.BOOL
        k.TerminateJobObject.argtypes=[w.HANDLE,w.UINT]; k.TerminateJobObject.restype=w.BOOL
        k.CloseHandle.argtypes=[w.HANDLE]; k.CloseHandle.restype=w.BOOL
        self.handle=k.CreateJobObjectW(None,None)
        if not self.handle: raise c.WinError(c.get_last_error())
        try:
            self.info.basic.flags=0x2000  # KILL_ON_JOB_CLOSE on failure/crash
            if not k.SetInformationJobObject(self.handle,9,c.byref(self.info),c.sizeof(self.info)): raise c.WinError(c.get_last_error())
            if not k.AssignProcessToJobObject(self.handle,int(process._handle)): raise c.WinError(c.get_last_error())
            resume=c.WinDLL('ntdll').NtResumeProcess
            resume.argtypes=[w.HANDLE];resume.restype=w.LONG
            if resume(int(process._handle))!=0: raise OSError('Cannot resume private upgrade job')
        except Exception:
            k.CloseHandle(self.handle);self.handle=None;raise
    def terminate(self): self.kernel.TerminateJobObject(self.handle,124)
    def close(self,success=False):
        if self.handle:
            if success:
                self.info.basic.flags=0  # completed installers may own intentionally detached services
                if not self.kernel.SetInformationJobObject(self.handle,9,self.c.byref(self.info),self.c.sizeof(self.info)): raise self.c.WinError(self.c.get_last_error())
            self.kernel.CloseHandle(self.handle);self.handle=None


def signal_group(group,signum):
    try: os.killpg(group,signum)
    except ProcessLookupError: pass
    except PermissionError:
        # macOS can return EPERM for an already exited group. Inspect only our
        # private group; never infer ownership from a daemon's name or command.
        rows=subprocess.check_output(['ps','-axo','pid=,pgid=,stat='],text=True).splitlines()
        for row in rows:
            fields=row.split()
            if len(fields)<3 or int(fields[1])!=group or fields[2].startswith('Z'): continue
            pid=int(fields[0])
            try:
                if os.getpgid(pid)==group: os.kill(pid,signum)
            except ProcessLookupError: pass


def run(argv,cwd=None,timeout=240):
    process=None;job=None
    try:
        options=dict(cwd=cwd,env=env(),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
        if os.name=='nt': options['creationflags']=0x4  # CREATE_SUSPENDED: no child can escape assignment
        else: options['start_new_session']=True
        process=subprocess.Popen([str(a) for a in argv],**options)
        if os.name=='nt': job=WindowsJob(process)
        try:
            output,_=process.communicate(timeout=timeout)
            if job: job.close(success=True)
            return process.returncode,redact(output)
        except subprocess.TimeoutExpired:
            if job: job.terminate()
            else:
                import signal
                # The unreaped child owns this new process group; no shared pre-existing PID is used.
                signal_group(process.pid,signal.SIGTERM)
                time.sleep(.15)
                signal_group(process.pid,signal.SIGKILL)
            try: process.communicate(timeout=5)
            except subprocess.TimeoutExpired: process.kill();process.wait()
            return 124,'Timed out; private command process tree terminated; inspect the tool before retrying.'
    except OSError as e:
        if process and process.poll() is None: process.kill();process.wait()
        return 127,type(e).__name__
    finally:
        if job: job.close()
        if process and process.stdout: process.stdout.close()


def installed_cli(name):
    return next((p for n in ALIASES.get(name,[name]) if (p:=shutil.which(n))),None)


def cli_version(exe):
    code,text=run([exe,'--version'],timeout=12)
    return version(text) if code==0 else None


def plugin_entries():
    p=HOME/'.claude/plugins/installed_plugins.json'
    if not p.exists(): return []
    try: data=json.loads(p.read_text(encoding='utf-8-sig'))
    except (OSError,ValueError): raise RuntimeError('Cannot read installed Claude plugins; no plugin changes attempted')
    if not isinstance(data,dict) or not isinstance(data.get('plugins',data),dict):
        raise RuntimeError('Cannot read installed Claude plugins; no plugin changes attempted')
    result=[]
    for key,rows in data.get('plugins',data).items():
        if key.split('@')[0] not in NAMES+['use-family']: continue
        for row in rows if isinstance(rows,list) else [rows]:
            if isinstance(row,dict): result.append(dict(key=key,**{k:row.get(k) for k in ('scope','version','projectPath') if row.get(k) is not None}))
    return result


def codex_entries():
    exe=shutil.which('codex')
    if not exe: return []
    code,text=run([exe,'plugin','list','--json'],timeout=30)
    if code:
        if (HOME/'.codex/plugins/cache').exists(): raise RuntimeError('Codex plugin inventory unavailable; native refresh not attempted')
        return []
    data=json.loads(text)
    if not isinstance(data,dict) or not isinstance(data.get('installed'),list): raise RuntimeError('Unsupported Codex plugin inventory schema')
    return [{k:p.get(k) for k in ('pluginId','name','marketplaceName','version','enabled','marketplaceSource')} for p in data['installed']]


def codex_targets(market):
    code,text=run([shutil.which('codex'),'plugin','marketplace','list','--json'],timeout=30)
    if code: return {}
    try:
        root=next(Path(m['root']) for m in json.loads(text).get('marketplaces',[]) if m.get('name')==market)
        for rel in ('.claude-plugin/marketplace.json','.agents/plugins/marketplace.json'):
            file=root/rel
            if file.is_file():
                return {p['name']+'@'+market:p.get('version') for p in read(file).get('plugins',[])}
    except (KeyError,ValueError,StopIteration): pass
    return {}


def codex_upgrade(report,names,check):
    try: entries=codex_entries()
    except (OSError,ValueError,RuntimeError):
        report['items'].append(dict(name='codex',channel='codex-plugin',status='manual',reason='native Codex plugin inventory unavailable')); return
    allowed=set(names+(['use-family'] if set(names)==set(NAMES) else []))
    selected=[p for p in entries if p['name'] in allowed]
    for market in sorted({p['marketplaceName'] for p in selected}):
        progress(report,tr('codex_progress',name=market))
        group=[p for p in entries if p['marketplaceName']==market]
        chosen=[p for p in selected if p['marketplaceName']==market]
        if check:
            report['items'].extend(dict(name=p['pluginId'],channel='codex-plugin',status='installed',before=p['version'],enabled=p['enabled']) for p in chosen); continue
        if any(p['name'] not in allowed for p in group):
            report['items'].append(dict(name=market,channel='codex-plugin',status='manual',reason='native marketplace refresh would include plugins outside the requested family scope')); continue
        if any(p.get('marketplaceSource',{}).get('sourceType')!='git' for p in chosen):
            report['items'].append(dict(name=market,channel='codex-plugin',status='manual',reason='local/managed marketplace is owned by its host; no Git upgrade path')); continue
        code,text=run([shutil.which('codex'),'plugin','marketplace','upgrade',market,'--json'])
        write_log('\nCodex marketplace '+str(market)+'\n'+text)
        try: observed={p['pluginId']:p for p in codex_entries() if p['marketplaceName']==market}
        except (ValueError,RuntimeError): observed={}
        targets=codex_targets(market)
        installed_set={p['pluginId'] for p in group}
        for p in chosen:
            after=observed.get(p['pluginId'],{})
            ok=code==0 and set(observed)==installed_set and after.get('enabled')==p['enabled'] and bool(after.get('version'))
            if version(after.get('version')) and version(p.get('version')) and tuple(map(int,version(after['version']).split('.')))<tuple(map(int,version(p['version']).split('.'))): ok=False
            target=version(targets.get(p['pluginId']))
            if target and (not version(after.get('version')) or tuple(map(int,version(after['version']).split('.')))<tuple(map(int,target.split('.')))): ok=False
            row=dict(name=p['pluginId'],channel='codex-plugin',status=(('updated' if after.get('version')!=p['version'] else 'current') if target else 'unverified') if ok else 'failed',before=p['version'],after=after.get('version'),target=target,enabledBefore=p['enabled'],enabledAfter=after.get('enabled'),exitCode=code)
            if not ok: row['reason']=failure_reason(code,text,'codex-plugin') if code else 'plugin version, installed set or enabled state could not be verified'
            report['items'].append(row)


@contextlib.contextmanager
def lock(kind='upgrade'):
    STATE.mkdir(parents=True,exist_ok=True)
    f=open(STATE/(kind+'.lock'),'a+b')
    try:
        if os.name=='nt':
            import msvcrt
            if f.tell()==0: f.write(b'0'); f.flush()
            f.seek(0); msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        f.close(); raise RuntimeError('Another use upgrade is running; no second upgrade started')
    try: yield
    finally: f.close()  # OS releases the lock even after a crash; never kill by PID or unlink a live lock.


def busy():
    try:
        with lock(): pass
        return False
    except RuntimeError: return True


def write_log(text):
    text=redact(text)
    STATE.mkdir(parents=True,exist_ok=True)
    p=STATE/'upgrade.log'
    if p.exists() and p.stat().st_size>5_000_000: os.replace(p,STATE/'upgrade.previous.log')
    with open(p,'a',encoding='utf-8') as f:
        if os.name!='nt': os.chmod(p,0o600)
        f.write(text+'\n')


def color_enabled(stream):
    if os.environ.get('NO_COLOR') or os.environ.get('TERM')=='dumb':return False
    if os.environ.get('FORCE_COLOR'):return True
    if not stream.isatty():return False
    if os.name!='nt':return True
    try:  # Windows consoles render ANSI only after virtual terminal processing is enabled.
        import ctypes
        kernel=ctypes.windll.kernel32;handle=kernel.GetStdHandle(-11);mode=ctypes.c_uint32()
        return bool(kernel.GetConsoleMode(handle,ctypes.byref(mode)) and kernel.SetConsoleMode(handle,mode.value|4))
    except (AttributeError,OSError):return False


STYLES={'bold':'1','dim':'2','red':'31','green':'32','yellow':'33','cyan':'36'}


def paint(text,*styles,stream=None):
    if not text or not color_enabled(stream or sys.stdout):return text
    return '\033['+';'.join(STYLES[s] for s in styles)+'m'+text+'\033[0m'


def progress(report,label=''):
    if not report.get('json') and sys.stderr.isatty():
        print('\r\033[2K'+(paint('› ','cyan',stream=sys.stderr)+paint(label,'dim',stream=sys.stderr) if label else ''),end='',file=sys.stderr,flush=True)


def failure_reason(code,text,channel):
    if code==124: return 'command timed out; inspect before retrying'
    if channel=='skill' and re.search(r'fast.forward|diverging branches|divergent branches',text,re.I):
        return 'Git history diverged; local checkout preserved'
    if re.search(r'rate.limit|rate_limit',text,re.I): return 'GitHub API rate limit reached; CLI upgrade deferred'
    if re.search(r'403',text,re.I): return 'remote access denied (HTTP 403)'
    if re.search(r'authentication failed|permission denied|could not read.*[Uu]sername',text,re.I): return 'repository authentication required'
    return 'owner command failed; see private upgrade log'


def step(report,name,channel,argv,cwd=None,before=None,after=None,target=None):
    code,text=run(argv,cwd)
    write_log(f'\n{datetime.datetime.now().isoformat()} {channel} {name}\n{text}')
    try: observed=after() if after else None
    except (OSError,ValueError,RuntimeError): observed=None; code=code or 3
    status='failed' if code else 'completed'
    if code==0 and after:
        if target and (not version(observed or '') or not version(target) or tuple(map(int,version(observed).split('.')))<tuple(map(int,version(target).split('.')))): status='failed'
        elif version(before) and version(observed) and tuple(map(int,version(observed).split('.')))<tuple(map(int,version(before).split('.'))): status='failed'
        elif not target: status='unverified'
        elif observed!=before: status='updated'
        elif observed: status='current' if target else 'unverified'
        else: status='unverified'
    row=dict(name=name,channel=channel,status=status,exitCode=code,before=before,after=observed,target=target)
    if status=='failed': row['reason']=failure_reason(code,text,channel) if code else 'installed version did not reach the expected target'
    report['items'].append(row)
    return row


PROBES={}


def github_limit_reached():
    authenticated=bool(github_token())
    cache=STATE/'github-api-limit.json'
    cached=read(cache).get('reset',0)
    if not authenticated and isinstance(cached,(int,float)) and time.time()<cached<time.time()+86400:return True
    try:
        headers={'User-Agent':'use-family/'+VERSION}
        token=github_token()
        if token:headers['Authorization']='Bearer '+token
        request=urllib.request.Request('https://api.github.com/rate_limit',headers=headers)
        with urllib.request.urlopen(request,timeout=5) as response:data=json.load(response)
        core=data.get('resources',{}).get('core',{})
        reset=core.get('reset',0)
        limited=core.get('remaining')==0 and isinstance(reset,(int,float)) and time.time()<reset<time.time()+86400
        if limited and not authenticated:save(cache,{'reset':reset})
        return limited
    except (OSError,ValueError):return False  # Unknown is not a confirmed rate limit.


def upgrade_probe(exe):
    code,text=run([exe,'upgrade','--check'],timeout=40)
    PROBES[str(exe)]=(code,redact(text))
    if code: return None,None
    try:
        d=json.loads(text)
        if isinstance(d,dict):
            have=d.get('current') or d.get('current_version')
            want=d.get('latest') or d.get('latest_version')
            if want: return version(have),version(want)
    except ValueError: pass
    m=re.search(r'v?(\d+\.\d+\.\d+)\s*(?:->|→)\s*v?(\d+\.\d+\.\d+)',text)
    if m: return m.group(1),m.group(2)
    if re.search(r'up.to.date|already.*(?:latest|current)|已是最新|已.*最新',text,re.I):
        have=cli_version(exe); return have,have
    return None,None


def expected_cli(exe):
    return upgrade_probe(exe)[1]


def thermo_version():
    for app in (Path('/Applications/Thermo.app'), HOME/'Applications/Thermo.app'):
        info=app/'Contents/Info.plist'
        if info.exists():
            try: return str(plistlib.loads(info.read_bytes()).get('CFBundleShortVersionString'))
            except (OSError,ValueError): pass
    return None


def thermo_upgrade(report,check):
    if platform.system()!='Darwin': return
    try:
        feed=ET.fromstring(fetch('https://app.leeguoo.com/thermo/appcast.xml'))
        versions=[n.text for n in feed.iter() if n.tag.endswith('shortVersionString') and n.text and re.fullmatch(r'\d+\.\d+\.\d+',n.text)]
        if not versions: raise RuntimeError('Thermo appcast has no release version')
        target=max(versions,key=lambda v:tuple(map(int,v.split('.'))))
        before=thermo_version()
        if check:
            report['items'].append(dict(name='thermo-use',channel='app',status='current' if before==target else 'available',before=before,target=target)); return
        if before and tuple(map(int,before.split('.')))>tuple(map(int,target.split('.'))):
            report['items'].append(dict(name='thermo-use',channel='app',status='current',before=before,target=target,reason='newer installed app retained')); return
        cli=installed_cli('thermo-use')
        have=cli_version(cli) if cli else None
        if have and tuple(map(int,have.split('.')))>tuple(map(int,target.split('.'))):
            report['items'].append(dict(name='thermo-use',channel='app',status='manual',reason='newer CLI retained; owner installer would replace its alias',before=have,target=target)); return
        if not before or before==target:
            # The official owner installer verifies the signed App and supplies the CLI aliases.
            # Never substitute the private/source thermo repo installer that only installs CLI binaries.
            with tempfile.TemporaryDirectory(prefix='use-thermo-') as tmp:
                script=Path(tmp)/'install.sh'
                script.write_bytes(fetch('https://raw.githubusercontent.com/leeguooooo/thermo-use/main/install.sh'))
                row=step(report,'thermo-use','app',['sh',script],before=before,after=thermo_version,target=target)
                if row['status']!='failed' and not installed_cli('thermo-use'): row['status']='unverified'
        else:
            exe=installed_cli('thermo-use')
            if not exe: raise RuntimeError('Thermo App needs its owner update path; CLI is unavailable')
            row=step(report,'thermo-use','app',[exe,'app-control','updates','check','--yes','--json'],before=before,after=thermo_version,target=target)
            if row['exitCode']==0 and row['after']!=target:
                row['status']='pending'; row['reason']='Thermo update requested; installed App has not reached the target version yet'
    except Exception:
        report['items'].append(dict(name='thermo-use',channel='app',status='manual',reason='Thermo owner installer/update could not be verified; see official thermo-use installation guide'))


def plugin_target(key):
    name,market=key.split('@',1)
    data=read(HOME/'.claude/plugins/marketplaces'/market/'.claude-plugin/marketplace.json')
    return next((p.get('version') for p in data.get('plugins',[]) if p.get('name')==name),None)


def git_roots(only,unmanaged=None):
    paths=[]
    for n in only+(['use-family'] if set(only)==set(NAMES) else []):
        paths.extend([BASE/n,HOME/'.agents/skills'/n,HOME/'.claude/skills'/n,HOME/'.codex/skills'/n])
    if set(only)==set(NAMES) or 'use-family' in only: paths.append(BASE/'plugins')
    seen=set()
    for p in paths:
        if not p.exists(): continue
        real=p.resolve()
        if real in seen: continue
        seen.add(real)
        code,text=run(['git','-C',str(real),'rev-parse','--show-toplevel'],timeout=10)
        if code:
            if unmanaged is not None and (p/'SKILL.md').is_file():
                managed=str(p.resolve()).startswith(str(HOME/'.local/share')+os.sep)
                unmanaged.append(dict(name=p.name,channel='skill',status='owner-managed' if managed else 'manual',path=str(p),reason='installer-owned skill' if managed else 'copied/unmanaged skill preserved; no ownership baseline for automatic overwrite'))
            continue
        root=Path(text.strip())
        if root!=real and root in seen: continue
        seen.add(root); yield root


# Markers that hosts and installers write beside an unchanged skill: Claude Code's plugin cache lock
# and the iphone-use installer's release stamp. They are not skill content.
HASH_IGNORED=('.git','node_modules','__pycache__','.DS_Store','.in_use','.iphone-use-release')


def folder_hash(root):
    h=hashlib.sha256()
    for p in sorted(Path(root).rglob('*')):
        rel=p.relative_to(root)
        if any(part in HASH_IGNORED for part in rel.parts): continue
        if p.is_symlink(): value=b'link:'+os.readlink(p).encode()
        elif p.is_file(): value=p.read_bytes()+str(p.stat().st_mode & 0o111).encode()
        else: continue
        h.update(str(rel).replace(os.sep,'/').encode()+b'\0'+value+b'\0')
    return h.hexdigest()


def canonical_sources(names):
    # Read only the known skill locations in installed immutable plugin caches.
    allowed=set(names+(['use-family'] if set(names)==set(NAMES) else [])); result={}
    roots=[]
    raw=read(HOME/'.claude/plugins/installed_plugins.json')
    for key,entries in raw.get('plugins',raw).items():
        name=key.split('@')[0]
        if name not in allowed: continue
        for e in entries if isinstance(entries,list) else [entries]:
            if isinstance(e,dict) and e.get('installPath'): roots.append((name,str(e.get('version','0.0.0')),Path(e['installPath'])))
    try:
        for e in codex_entries():
            if e['name'] in allowed:
                roots.append((e['name'],str(e.get('version','0.0.0')),HOME/'.codex/plugins/cache'/e['marketplaceName']/e['name']/str(e['version'])))
    except (OSError,ValueError,RuntimeError): pass
    for name,v,root in roots:
        trusted=False
        for cache in (HOME/'.claude/plugins/cache',HOME/'.codex/plugins/cache'):
            try: root.resolve().relative_to(cache.resolve()); trusted=True
            except ValueError: pass
        if not trusted: continue
        for p in (root/'skills'/name,root,root/'plugins/use-family/skills/use-family'):
            skill=p/'SKILL.md'
            if not skill.is_file(): continue
            if not re.search(r'^name:\s*[\"\']?'+re.escape(name)+r'[\"\']?\s*$',skill.read_text(encoding='utf-8',errors='replace'),re.M): continue
            try: sig=folder_hash(p)
            except OSError: continue
            result.setdefault(name,[]).append(dict(path=str(p),hash=sig,version=v)); break
    return result


def refresh_copies(report,items,baseline,names,check):
    import uuid
    records=read(STATE/'copied-skills.json')
    latest=canonical_sources(names) if not check else {}
    for item in items:
        if item['status']!='manual' or check:
            report['items'].append(item); continue
        path=Path(item['path']).resolve()
        try:
            current=folder_hash(path)
            candidates=latest.get(item['name'],[])
            if not candidates: report['items'].append(item); continue
            selected=max(candidates,key=lambda c:tuple(map(int,(version(c['version']) or '0.0.0').split('.'))))
            known={c['hash'] for c in baseline.get(item['name'],[])}
            if records.get(str(path),{}).get('hash'): known.add(records[str(path)]['hash'])
            if current==selected['hash']:
                item['status']='current'; item['reason']='matches installed owner skill'; records[str(path)]={'hash':current,'version':selected['version']};report['items'].append(item);continue
            old_version=version(records.get(str(path),{}).get('version'))
            selected_version=version(selected.get('version'))
            if old_version and selected_version and tuple(map(int,old_version.split('.')))>tuple(map(int,selected_version.split('.'))):
                item['reason']='newer managed skill retained';report['items'].append(item);continue
            if current not in known:
                item['reason']='local copy differs from known owner baseline; preserved';report['items'].append(item);continue
            STATE.mkdir(parents=True,exist_ok=True)
            if path.parent.stat().st_dev!=STATE.stat().st_dev:
                item['reason']='cross-filesystem skill replacement needs manual review';report['items'].append(item);continue
            stage=STATE/'staging'/uuid.uuid4().hex; stage.parent.mkdir(parents=True,exist_ok=True)
            backup=STATE/'skill-backups'/(item['name']+'-'+uuid.uuid4().hex);backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copytree(selected['path'],stage,symlinks=True,ignore=shutil.ignore_patterns('.git','node_modules','__pycache__','.DS_Store'))
            if folder_hash(stage)!=selected['hash'] or folder_hash(path)!=current:
                shutil.rmtree(stage);item['reason']='skill changed while preparing update; preserved';report['items'].append(item);continue
            os.replace(path,backup)
            try: os.replace(stage,path)
            except OSError:
                if not path.exists(): os.replace(backup,path)
                raise
            records[str(path)]={'hash':selected['hash'],'version':selected['version']}
            item.update(status='updated',reason='verified owner baseline refreshed',backup=str(backup))
        except (OSError,ValueError): item.update(status='manual',reason='copy update could not be completed; original/backup retained')
        report['items'].append(item)
    if not check and records: save(STATE/'copied-skills.json',records)


def upgrade(args):
    automatic=args.automatic
    config=read(CONFIG)
    if automatic:
        if os.environ.get('CI') or os.environ.get('USE_NO_AUTO_UPGRADE') or not config.get('enabled'):
            return dict(ok=True,skipped='automatic upgrades disabled'),0
        last=read(STATE/'last-attempt.json').get('at',0)
        last=last if isinstance(last,(int,float)) else 0
        hours=config.get('intervalHours',24)
        hours=hours if isinstance(hours,(int,float)) and hours>=1 else 24
        if time.time()-last < hours*3600:
            return dict(ok=True,skipped='not due'),0
    report=dict(ok=False,started=time.time(),automatic=automatic,check=args.check,json=args.json,items=[])
    with lock(),github_auth():
        progress(report,tr('scan'))
        if automatic: save(STATE/'last-attempt.json',{'at':time.time()})
        names=list(args.names) if args.names else NAMES+['use-family']
        if automatic: names=[n for n in names if not os.environ.get(n.upper().replace('-','_')+'_NO_AUTO_UPGRADE')]
        initial_plugins=plugin_entries()  # reject a corrupt registry before touching any tool
        try: initial_codex=codex_entries()
        except (OSError,ValueError,RuntimeError): initial_codex=[]
        unknown=set(names)-set(NAMES+['use-family'])
        if unknown: raise RuntimeError('Unknown family member: '+', '.join(sorted(unknown)))
        progress(report,tr('copies'))
        copy_baselines=canonical_sources(names) if not args.check else {}
        if 'use-family' in names: self_upgrade(report,args.check)
        limited=github_limit_reached() if any(installed_cli(n) for n in names if n not in ('thermo-use','use-family')) else False
        PROBES.clear()
        # Each installed CLI owns its installer, native apps and skill refresh. Do not install missing tools.
        for name in names:
            progress(report,tr('check_tool' if args.check else 'upgrade_tool',name=name))
            if automatic and not read(CONFIG).get('enabled'): break
            if automatic and os.environ.get(name.upper().replace('-','_')+'_NO_AUTO_UPGRADE'): continue
            if name=='thermo-use':
                skill_installed=any((p/'SKILL.md').is_file() for p in (BASE/name,HOME/'.agents/skills'/name,HOME/'.claude/skills'/name,HOME/'.codex/skills'/name))
                if installed_cli(name) or thermo_version() or skill_installed or any(e['key'].split('@')[0]==name for e in initial_plugins) or any(e['name']==name for e in initial_codex): thermo_upgrade(report,args.check)
                continue
            exe=installed_cli(name)
            if not exe: continue
            if limited:
                report['items'].append(dict(name=name,channel='cli',status='pending',before=cli_version(exe),target=None,reason='GitHub API rate limit reached; CLI upgrade deferred'));continue
            code,help_text=run([exe,'--help'],timeout=15)
            if code:
                report['items'].append(dict(name=name,channel='cli',status='unverified',exitCode=code,reason='CLI help could not be read; upgrade support not determined'));continue
            probe=upgrade_probe(exe) if name=='wechat-use' else (None,None)
            if not re.search(r'\bupgrade\b',help_text) and name!='wechat-use':
                report['items'].append(dict(name=name,channel='cli',status='manual',reason='installed version has no upgrade command')); continue
            before=probe[0] or cli_version(exe)
            target=probe[1] if name=='wechat-use' else expected_cli(exe)
            if not target:
                probe_code,probe_text=PROBES.get(str(exe),(0,''))
                reason=failure_reason(probe_code,probe_text,'cli') if probe_code else 'latest version could not be checked; installer not run'
                if reason=='owner command failed; see private upgrade log':reason='latest version could not be checked; installer not run'
                if 'GitHub API rate limit' in reason:limited=True
                report['items'].append(dict(name=name,channel='cli',status='pending' if limited else 'unverified',before=before,target=None,reason=reason));continue
            if not args.check and before and target and tuple(map(int,before.split('.')))>tuple(map(int,target.split('.'))):
                report['items'].append(dict(name=name,channel='cli',status='current',before=before,target=target,reason='newer installed version retained')); continue
            if args.check:
                newer=not before or tuple(map(int,target.split('.')))>tuple(map(int,before.split('.')))
                report['items'].append(dict(name=name,channel='cli',status='available' if newer else 'current',before=before,target=target)); continue
            if before==target:
                report['items'].append(dict(name=name,channel='cli',status='current',before=before,target=target));continue
            step(report,name,'cli',[exe,'upgrade'],before=before,after=(lambda e=exe:upgrade_probe(e)[0] or cli_version(e)) if name=='wechat-use' else (lambda e=exe:cli_version(e)),target=target)
        unmanaged=[]
        for root in git_roots(names,unmanaged):
            progress(report,tr('skill_progress',name=root.name))
            code,dirty=run(['git','-C',root,'status','--porcelain'],timeout=15)
            if code or dirty.strip():
                report['items'].append(dict(name=root.name,channel='skill',status='manual',reason='checkout is dirty or unreadable',path=str(root))); continue
            if args.check:
                report['items'].append(dict(name=root.name,channel='skill',status='installed',path=str(root))); continue
            head=lambda:(lambda r:r[1].strip() if r[0]==0 and re.fullmatch(r'[0-9a-f]{7,40}',r[1].strip()) else None)(run(['git','-C',root,'rev-parse','--short','HEAD'],timeout=10))
            before=head()
            row=step(report,root.name,'skill',['git','-C',root,'pull','--ff-only']);row['path']=str(root)
            after=head() if row['status']=='completed' and before else None
            if after and after!=before: row.update(status='updated',before=before,after=after)
        codex_upgrade(report,names,args.check)
        if not args.check:
            entries=[e for e in plugin_entries() if e['key'].split('@')[0] in names]
            claude=shutil.which('claude')
            if entries and not claude: report['items'].append(dict(name='claude',channel='plugin',status='manual',reason='Claude CLI not installed'))
            if claude:
                markets=sorted({e['key'].split('@',1)[1] for e in entries if '@' in e['key']})
                for market in markets: step(report,market,'marketplace',[claude,'plugin','marketplace','update',market])
                for e in entries:
                    progress(report,tr('claude_progress',name=e['key'].split('@')[0]))
                    if automatic and not read(CONFIG).get('enabled'): break
                    scope=e.get('scope','user'); cwd=e.get('projectPath') if scope in ('project','local') else None
                    if scope in ('project','local') and (not cwd or not Path(cwd).is_dir()):
                        report['items'].append(dict(name=e['key'],channel='plugin',status='manual',reason='project directory unavailable')); continue
                    def after(entry=e):
                        return next((r.get('version') for r in plugin_entries() if r['key']==entry['key'] and r.get('scope','user')==entry.get('scope','user') and r.get('projectPath')==entry.get('projectPath')),None)
                    step(report,e['key'],'plugin',[claude,'plugin','update',e['key'],'--scope',scope],cwd=cwd,before=e.get('version'),after=after,target=plugin_target(e['key']))
        else:
            report['items'].extend(dict(name=e['key'],channel='plugin',status='installed',before=e.get('version')) for e in plugin_entries() if e['key'].split('@')[0] in names)
        progress(report,tr('verify'))
        refresh_copies(report,unmanaged,copy_baselines,names,args.check)
        report['ok']=all(i['status'] not in ('failed','manual','unverified','pending') for i in report['items'])
        report['finished']=time.time(); report.pop('json')
        if not args.check: save(STATE/'last-report.json',report)
        progress(report)
        return report,0 if report['ok'] else 2


def tool_name(item):
    name=item.get('name','').split('@')[0]
    return 'use-family' if name=='use' else name


def human_reason(item):
    reason=item.get('reason','')
    messages={
        'command timed out; inspect before retrying':'命令超时，请检查工具状态后再重试',
        'remote access denied or rate limited':'远端拒绝访问或触发限流，请稍后重试',
        'remote access denied (HTTP 403)':'远端拒绝访问（HTTP 403），请检查访问权限或服务限制',
        'repository authentication required':'仓库需要认证，请先检查 Git 登录',
        'installed version did not reach the expected target':'实际安装版本未达到目标版本',
        'local copy differs from known owner baseline; preserved':'技能副本与已知原版不同，已保留',
        'installed version has no upgrade command':'当前 CLI 没有自动升级入口',
        'Thermo update requested; installed App has not reached the target version yet':'已请求更新 Thermo，等待 App 完成更新',
        'native marketplace refresh would include plugins outside the requested family scope':'市场更新会涉及所选范围以外的插件，已跳过',
        'native Codex plugin inventory unavailable':'无法读取 Codex 已安装插件，已跳过',
        'plugin version, installed set or enabled state could not be verified':'无法确认插件版本、安装列表或启用状态',
        'latest version could not be checked; installer not run':'无法获取最新版本，未运行安装器；现有版本已保留',
        'GitHub API rate limit reached; CLI upgrade deferred':'GitHub API 被限流，已暂缓 CLI 升级',
        'latest version could not be checked; installed version retained':'无法获取最新版本，现有安装版本未变',
        'Claude CLI not installed':'未安装 Claude CLI，插件暂未更新',
        'Thermo owner installer/update could not be verified; see official thermo-use installation guide':'无法确认 Thermo 官方安装或更新结果，请查看 thermo-use 安装说明',
        'copy update could not be completed; original/backup retained':'未能完成技能副本更新，原目录或备份已保留',
        'local/managed marketplace is owned by its host; no Git upgrade path':'本地或托管市场由宿主管理，没有 Git 自动升级路径',
        'newer CLI retained; owner installer would replace its alias':'现有 CLI 版本较新，已保留；官方安装器会替换它的别名',
        'newer installed app retained':'现有 App 版本较新，已保留',
        'newer installed version retained':'现有版本较新，已保留',
        'project directory unavailable':'项目目录不可用，已跳过',
        'verified owner baseline refreshed':'已核对原版并刷新技能',
        'cross-filesystem skill replacement needs manual review':'技能目录跨文件系统，需确认后再替换',
        'skill changed while preparing update; preserved':'准备更新时技能内容发生变化，已保留',
        'newer managed skill retained':'现有技能版本较新，已保留',
        'matches installed owner skill':'与已安装的原版技能一致',
        'copied/unmanaged skill preserved; no ownership baseline for automatic overwrite':'无法核对来源的技能副本已保留，未自动覆盖',
    }
    if not reason and item.get('status')=='unverified' and not item.get('target'):
        reason='latest version could not be checked; installed version retained'
    short={'owner command failed; see private upgrade log':'reason_owner_failed','CLI help could not be read; upgrade support not determined':'reason_cli_broken',
        'Git history diverged; local checkout preserved':'reason_diverged','checkout is dirty or unreadable':'reason_dirty'}.get(reason)
    if short:
        code=item.get('exitCode')
        return tr(short)+(tr('exit_code',code=code) if code and short in ('reason_owner_failed','reason_cli_broken') else '')
    if UI_LANG=='en':return reason or tr('failed_reason' if item.get('exitCode') else 'fallback_reason')
    return messages.get(reason,reason or tr('failed_reason' if item.get('exitCode') else 'fallback_reason'))


def home_path(path):
    path=str(path)
    return '~'+path[len(str(HOME)):] if path==str(HOME) or path.startswith(str(HOME)+os.sep) else path


def next_step(item):
    # Commands that reproduce or inspect a problem; never the owner's captured output.
    reason,channel,name,path=item.get('reason',''),item.get('channel'),tool_name(item),item.get('path')
    if channel=='cli' and reason=='owner command failed; see private upgrade log':return name+' upgrade'
    if channel=='cli' and reason=='CLI help could not be read; upgrade support not determined':return name+' --help'
    if channel=='skill' and path and reason in ('Git history diverged; local checkout preserved','checkout is dirty or unreadable'):
        return 'git -C '+home_path(path)+' status'+(' -sb' if 'diverged' in reason else ' --short')
    if channel=='plugin' and reason=='owner command failed; see private upgrade log':return 'claude plugin update '+item.get('name','')
    return None


def load_report():
    report=read(STATE/'last-report.json')
    if not report:raise RuntimeError('No upgrade report yet; run use upgrade first')
    # Older reports omitted failure reasons. Recover only a matching log entry
    # from this report's time interval, never echoing raw owner output.
    missing=[i for i in report.get('items',[]) if i['status']=='failed' and not i.get('reason')]
    log=STATE/'upgrade.log'
    if missing and log.is_file():
        entries=re.split(r'\n(\d{4}-\d\d-\d\dT[^\n]+)\n',log.read_text(encoding='utf-8',errors='replace'))
        for header,text in zip(entries[1::2],entries[2::2]):
            fields=header.split(' ',2)
            if len(fields)!=3:continue
            try:at=datetime.datetime.fromisoformat(fields[0]).timestamp()
            except ValueError:continue
            if not report.get('started',0)<=at<=report.get('finished',0):continue
            for item in missing:
                if fields[1:]==[item.get('channel'),item.get('name')]:item['reason']=failure_reason(item.get('exitCode'),text,item.get('channel'))
    return report


def print_report(report,verbose=False):
    items=report.get('items',[])
    if report.get('skipped'):
        print({'not due':tr('not_due'),'automatic upgrades disabled':tr('disabled')}.get(report['skipped'],report['skipped'])); return
    known=set(NAMES+['use-family'])
    tools={tool_name(i) for i in items if tool_name(i) in known}
    changes={}
    wanted='available' if report.get('check') else 'updated'
    for i in items:
        if i['status']==wanted: changes.setdefault(tool_name(i),[]).append(i)
    problems=[i for i in items if i['status'] in ('failed','pending','unverified')]
    limited=[i for i in problems if i.get('channel')=='cli' and i.get('reason')=='GitHub API rate limit reached; CLI upgrade deferred']
    blocked=[i for i in problems if i.get('channel')=='cli' and i.get('reason') in ('remote access denied or rate limited','remote access denied (HTTP 403)')]
    manuals=[i for i in items if i['status']=='manual']
    copied=[i for i in manuals if i.get('channel')=='skill' and i.get('path') and ('baseline' in i.get('reason','') or 'copied/unmanaged' in i.get('reason',''))]
    other_manual=[i for i in manuals if i not in copied]
    parts=[tr('checked',count=len(tools))]
    if changes: parts.append(tr('available' if report.get('check') else 'updated',count=len(changes)))
    issues={}
    for i in problems+other_manual:
        if i not in limited and i not in blocked:issues.setdefault(tool_name(i),[]).append(i)
    deferred={tool_name(i) for i in limited if i['status']=='pending'}
    failed={n for n,rows in issues.items() if any(i['status']=='failed' for i in rows)}
    if failed:parts.append(paint(tr('failed_count',count=len(failed)),'red','bold'))
    if len(issues)>len(failed):parts.append(paint(tr('attention',count=len(issues)-len(failed)),'yellow','bold'))
    if deferred:parts.append(paint(tr('deferred',count=len(deferred)),'yellow'))
    if not changes and not problems and not manuals: parts.append(paint(tr('no_updates'),'green'))
    if changes:parts[1]=paint(parts[1],'cyan' if report.get('check') else 'green','bold')
    print(paint(parts[0],'bold')+paint(' · ','dim')+paint(' · ','dim').join(parts[1:]) if len(parts)>1 else paint(parts[0],'bold'))
    channels={k:tr(k) for k in ('cli','app','manager','plugin','codex-plugin','skill','marketplace')}
    sep='、' if UI_LANG=='zh' else ', '
    width=min(max([len(n) for n in list(changes)+list(issues)]+[0]),20)
    indent=' '*(4+width+2)
    def row(mark,styles,name,text):
        print('  '+paint(mark,*styles)+' '+paint(name.ljust(width),'bold')+'  '+text)
    def hint(command):
        if command:print(indent+paint('→ ','dim')+paint(command,'cyan'))
    if changes or issues or limited or blocked or copied:print()
    for name,rows in changes.items():
        versions=[]
        for i in rows:
            after=i.get('after') or i.get('target')
            label=(paint(str(i.get('before')),'dim')+paint(' → ','dim')+paint(str(after),'green' if not report.get('check') else 'cyan')) if i.get('before') and after else str(after or '')
            text=paint(channels.get(i.get('channel'),i.get('channel','')),'dim')+(' '+label if label else '')
            if text not in versions:versions.append(text)
        if report.get('check'):row('↑',('cyan','bold'),name,versions[0])
        else:row('✓',('green','bold'),name,versions[0])
        for text in versions[1:]:print(indent+text)
    for name,rows in sorted(issues.items(),key=lambda kv:kv[0] not in failed):
        styles=('red','bold') if name in failed else ('yellow','bold')
        lines=list(dict.fromkeys((channels.get(i.get('channel'),i.get('channel','')),human_reason(i),next_step(i),i['status']=='failed') for i in rows))
        for n,(channel,reason,command,bad) in enumerate(lines):
            text=paint(channel,'dim')+'  '+(paint(reason,'red') if bad else reason)
            if n==0:row('✗' if name in failed else '!',styles,name,text)
            else:print(indent+text)
            hint(command)
    for group,title,tip in ((limited,'rate_group',tr('rate_tip')),(blocked,'blocked_group',human_reason(blocked[0]) if blocked else '')):
        if not group:continue
        names=list(dict.fromkeys(tool_name(i) for i in group))
        print('  '+paint('!','yellow','bold')+' '+tr(title,count=len(names)).rstrip(':：'))
        print('    '+paint(sep.join(names),'dim'))
        print('    '+paint(tip,'dim'))
    if copied:
        names=list(dict.fromkeys(tool_name(i) for i in copied))
        print('  '+paint('·','dim')+' '+tr('preserved',tools=len(names),copies=len(copied)))
        print('    '+paint(sep.join(names),'dim'))
    if problems or manuals:
        print('\n'+paint(tr('details',command='use upgrade --check --verbose' if report.get('check') else 'use report --verbose',path=home_path(STATE/'upgrade.log')),'dim'))
    if not report.get('check') and any(i['status']=='updated' and i.get('channel') in ('plugin','codex-plugin') for i in items):
        print(paint(tr('new_session'),'dim'))
    if verbose:
        labels={k:tr('status_'+k) for k in ('updated','available','current','completed','failed','manual','unverified','pending','owner-managed','installed')}
        print('\n'+tr('full_details'))
        for i in items:
            tone={'updated':('green',),'available':('cyan',),'failed':('red',),'manual':('yellow',),'unverified':('yellow',),'pending':('yellow',)}.get(i['status'],('dim',))
            print('  '+i.get('name','')+paint(' ['+channels.get(i.get('channel'),i.get('channel',''))+'] ','dim')+paint(labels.get(i['status'],i['status']),*tone))
            if i.get('path'):print('    '+paint(home_path(i['path']),'dim'))
            if i['status'] in ('failed','manual','unverified','pending'):print('    '+human_reason(i))


def schedule(kind,enable):
    label='com.leeguooooo.use-upgrade'
    context=STATE/'scheduler-context.json'
    values=dict(USE_MANAGER_STATE=str(STATE),USE_MANAGER_HOME=str(INSTALL),USE_MANAGER_BIN=str(BIN),USE_FAMILY_DIR=str(BASE),PATH=os.environ.get('PATH',''))
    for key in ['USE_NO_AUTO_UPGRADE']+[n.upper().replace('-','_')+'_NO_AUTO_UPGRADE' for n in NAMES+['use-family']]:
        if os.environ.get(key): values[key]='1'
    command=([str(BIN/'use')] if kind in ('Darwin','Linux') else [sys.executable,str(SCRIPT)])+['upgrade','--automatic','--json','--context',str(context)]
    if kind=='Darwin':
        import plistlib
        p=HOME/'Library/LaunchAgents'/f'{label}.plist'
        if enable:
            loaded,_=run(['launchctl','print',f'gui/{os.getuid()}/{label}'],timeout=10)
            old=plistlib.loads(p.read_bytes()).get('ProgramArguments') if p.exists() else None
            if loaded==0 and old!=command: raise RuntimeError('Registered scheduler belongs to another installation; disable it there before changing paths')
            save(context,values)
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(plistlib.dumps(dict(Label=label,ProgramArguments=command,RunAtLoad=True,StartInterval=3600,Umask=63,
                EnvironmentVariables={'PATH':os.environ.get('PATH','')},StandardOutPath=str(STATE/'scheduler.log'),StandardErrorPath=str(STATE/'scheduler-error.log'))))
            code,text=run(['launchctl','enable',f'gui/{os.getuid()}/{label}'])
            if code: raise RuntimeError('Cannot enable launch agent: '+text)
            if loaded==0: return
            code,text=run(['launchctl','bootstrap',f'gui/{os.getuid()}',p])
        else:
            code,text=run(['launchctl','disable',f'gui/{os.getuid()}/{label}'])
            if code==0 and not busy(): run(['launchctl','bootout',f'gui/{os.getuid()}/{label}'])
    elif kind=='Linux':
        p=HOME/'.config/systemd/user'; p.mkdir(parents=True,exist_ok=True)
        if enable:
            save(context,values)
            quoted=' '.join(json.dumps(x.replace('%','%%'),ensure_ascii=False) for x in command)
            (p/'use-upgrade.service').write_text('[Unit]\nDescription=Upgrade installed use family\n[Service]\nType=oneshot\nUMask=0077\nExecStart=:'+quoted+'\nEnvironment="PATH='+os.environ.get('PATH','').replace('"','\\"')+'"\n')
            (p/'use-upgrade.timer').write_text('[Unit]\nDescription=Check use family hourly (upgrade daily)\n[Timer]\nOnCalendar=hourly\nPersistent=true\n[Install]\nWantedBy=timers.target\n')
            code,text=run(['systemctl','--user','daemon-reload'])
            if code: raise RuntimeError('Cannot reload user systemd: '+text)
            code,text=run(['systemctl','--user','enable','--now','use-upgrade.timer'])
        else: code,text=run(['systemctl','--user','disable','--now','use-upgrade.timer'])
    elif kind=='Windows':
        if enable:
            save(context,values)
            code,text=run(['schtasks','/Create','/TN','UseFamilyUpgrade','/SC','HOURLY','/MO','1','/TR',subprocess.list2cmdline(command),'/F'])
        else: code,text=run(['schtasks','/Delete','/TN','UseFamilyUpgrade','/F'])
    else: raise RuntimeError('Automatic scheduling is unsupported on '+kind)
    if code: raise RuntimeError('Scheduler operation failed; configuration is not enabled: '+text[:500])


def auto(args):
    config=read(CONFIG)
    if args.action=='status':
        kind=platform.system()
        query=['launchctl','print',f'gui/{os.getuid()}/com.leeguooooo.use-upgrade'] if kind=='Darwin' else ['systemctl','--user','is-enabled','use-upgrade.timer'] if kind=='Linux' else ['schtasks','/Query','/TN','UseFamilyUpgrade'] if kind=='Windows' else []
        registered=bool(query) and run(query,timeout=10)[0]==0
        return dict(config=config,busy=busy(),registered=registered,lastAttempt=read(STATE/'last-attempt.json'),lastRun=read(STATE/'last-report.json'),scheduler='hourly trigger; upgrades at most every configured interval')
    if args.action=='enable':
        if SCRIPT != INSTALL/'use.py': raise RuntimeError('Install use before enabling a persistent schedule')
        # Persist consent before RunAtLoad starts; roll back on registration failure.
        desired=dict(enabled=True,intervalHours=args.hours)
        save(CONFIG,desired)
        try: schedule(platform.system(),True)
        except Exception:
            save(CONFIG,config); raise
        return dict(ok=True,config=desired)
    save(CONFIG,dict(config,enabled=False))
    schedule(platform.system(),False)  # disable future starts; never kill a running upgrader.
    return dict(ok=True,config=read(CONFIG))


def apply_context(file):
    global STATE,CONFIG,INSTALL,BIN,BASE
    data=read(Path(file))
    keys={'USE_MANAGER_STATE','USE_MANAGER_HOME','USE_MANAGER_BIN','USE_FAMILY_DIR','PATH','USE_NO_AUTO_UPGRADE'}|{n.upper().replace('-','_')+'_NO_AUTO_UPGRADE' for n in NAMES+['use-family']}
    if not isinstance(data,dict) or set(data)-keys: raise RuntimeError('Invalid scheduler context')
    for key in ('USE_MANAGER_STATE','USE_MANAGER_HOME','USE_MANAGER_BIN','USE_FAMILY_DIR'):
        if not isinstance(data.get(key),str) or not Path(data[key]).is_absolute(): raise RuntimeError('Scheduler context requires absolute manager paths')
    if any(not isinstance(v,str) for v in data.values()): raise RuntimeError('Invalid scheduler environment')
    os.environ.update(data)
    STATE=Path(data['USE_MANAGER_STATE']);CONFIG=STATE/'config.json';INSTALL=Path(data['USE_MANAGER_HOME']);BIN=Path(data['USE_MANAGER_BIN']);BASE=Path(data['USE_FAMILY_DIR'])


def main(argv=None):
    if os.name=='nt':
        for stream in (sys.stdout,sys.stderr):
            if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',errors='backslashreplace')
    global UI_LANG
    language=argparse.ArgumentParser(add_help=False)
    language.add_argument('--lang',choices=['en','zh','auto'])
    preference,remaining=language.parse_known_args(argv)
    UI_LANG=choose_language(preference.lang)
    parser=Parser(prog='use',description=tr('description'))
    parser.add_argument('--lang',choices=['en','zh','auto'],help=tr('help_lang'))
    parser.add_argument('--version',action='version',version=VERSION,help=tr('help_version'))
    commands=parser.add_subparsers(dest='command',required=True)
    ins=commands.add_parser('install',help=tr('help_install'))
    ins.add_argument('--local',action='store_true',help=tr('help_local'))
    ins.add_argument('--auto',action='store_true',help=tr('help_auto_flag')); ins.add_argument('--json',action='store_true',help=tr('help_json'))
    up=commands.add_parser('upgrade',help=tr('help_upgrade'))
    up.add_argument('names',nargs='*',help=tr('help_names'))
    up.add_argument('--check',action='store_true',help=tr('help_check'));up.add_argument('--json',action='store_true',help=tr('help_json'))
    up.add_argument('--automatic',action='store_true',help=argparse.SUPPRESS);up.add_argument('--context',help=argparse.SUPPRESS)
    up.add_argument('--verbose',action='store_true',help=tr('help_verbose'))
    rp=commands.add_parser('report',help=tr('help_report'))
    rp.add_argument('--json',action='store_true',help=tr('help_json'));rp.add_argument('--verbose',action='store_true',help=tr('help_verbose'))
    st=commands.add_parser('status',help=tr('help_status'));st.add_argument('--json',action='store_true',help=tr('help_json'))
    au=commands.add_parser('auto',help=tr('help_auto'))
    au.add_argument('action',choices=['enable','disable','status'],help=tr('help_action'))
    au.add_argument('--hours',type=int,default=24,help=tr('help_hours'));au.add_argument('--json',action='store_true',help=tr('help_json'))
    args=parser.parse_args(remaining)
    try:
        if args.command=='upgrade' and args.context:
            if not args.automatic: raise RuntimeError('Scheduler context is only for automatic runs')
            apply_context(args.context)
        if args.command=='install':
            if args.local: latest,content=VERSION,SCRIPT.read_bytes()
            else:
                latest,data=release(); content=release_script(data)
            launcher=install_bytes(content,latest)
            result,code=dict(ok=True,version=latest,launcher=launcher),0
            if args.auto:
                rc,text=run([sys.executable,INSTALL/'use.py','auto','enable','--json'])
                if rc: raise RuntimeError('Installed use, but automatic scheduling failed: '+text[:500])
                result['auto']=json.loads(text)
        elif args.command=='upgrade':
            if args.automatic and args.check: raise RuntimeError('--automatic cannot be combined with --check')
            result,code=upgrade(args)
        elif args.command=='report':
            result=read(STATE/'last-report.json') if args.json else load_report()
            if not result:raise RuntimeError('No upgrade report yet; run use upgrade first')
            code=0 if result.get('ok') else 2
        elif args.command=='auto':
            if args.hours<1: raise RuntimeError('--hours must be at least 1')
            result,code=auto(args),0
        else:
            result,code=dict(version=VERSION,clis=[dict(name=n,path=p,version=cli_version(p)) for n in NAMES if (p:=installed_cli(n))],plugins=plugin_entries(),codexPlugins=[p for p in codex_entries() if p['name'] in NAMES+['use-family']],auto=read(CONFIG),lastRun=read(STATE/'last-report.json')),0
        if args.json or args.command=='status' or (args.command=='auto' and args.action=='status'):
            print(json.dumps(result,ensure_ascii=False,indent=2))
        elif args.command in ('upgrade','report'):
            print_report(result,args.verbose)
        else: print(json.dumps(result,ensure_ascii=False))
        return code
    except (RuntimeError,OSError,ValueError) as e:
        progress({'json':args.json})
        print(json.dumps(dict(ok=False,error=str(e)),ensure_ascii=False) if args.json else tr('error',message=human_error(str(e))),file=sys.stdout if args.json else sys.stderr); return 2

if __name__=='__main__': sys.exit(main())
