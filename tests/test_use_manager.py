import importlib.util
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE=Path(__file__).resolve().parents[1]/'plugins/use-family/scripts/use.py'
spec=importlib.util.spec_from_file_location('use_manager',SOURCE)
u=importlib.util.module_from_spec(spec); spec.loader.exec_module(u)

class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.patches=[]
        for key,value in dict(HOME=self.root,STATE=self.root/'state',CONFIG=self.root/'state/config.json',BASE=self.root/'family',INSTALL=self.root/'install',BIN=self.root/'bin').items():
            p=patch.object(u,key,value);p.start();self.addCleanup(p.stop)
        patcher=patch.object(u,'codex_entries',return_value=[]);patcher.start();self.addCleanup(patcher.stop)
        patcher=patch.object(u,'canonical_sources',return_value={});patcher.start();self.addCleanup(patcher.stop)
        patcher=patch.object(u,'thermo_version',return_value=None);patcher.start();self.addCleanup(patcher.stop)
        patcher=patch.object(u,'github_limit_reached',return_value=False);patcher.start();self.addCleanup(patcher.stop)
        patcher=patch.object(u,'UI_LANG','zh');patcher.start();self.addCleanup(patcher.stop)
        self.real_auth=u.github_auth
        patcher=patch.object(u,'github_auth',side_effect=lambda:contextlib.nullcontext());patcher.start();self.addCleanup(patcher.stop)
        self.args=SimpleNamespace(automatic=False,check=False,json=True,names=['chrome-use','mail-use'])

    def test_real_install_version_readback_and_unknown_executable_preserved(self):
        launcher=u.install_bytes(SOURCE.read_bytes(),u.VERSION)
        self.assertIn(u.MARKER,Path(launcher).read_text())
        self.assertEqual(subprocess.check_output([sys.executable,str(u.INSTALL/'use.py'),'--version'],text=True).strip(),u.VERSION)
        if os.name=='nt': self.assertIn(b'\r\n',Path(launcher).read_bytes())
        Path(launcher).write_text('user program')
        with self.assertRaisesRegex(RuntimeError,'unmanaged'):u.install_bytes(SOURCE.read_bytes(),u.VERSION)
        self.assertEqual(Path(launcher).read_text(),'user program')

    def test_older_plugin_bootstrap_never_downgrades_manager(self):
        newer=SOURCE.read_bytes().replace(f"VERSION = '{u.VERSION}'".encode(),b"VERSION = '9.0.0'")
        u.install_bytes(newer,'9.0.0')
        u.install_bytes(SOURCE.read_bytes(),u.VERSION)
        self.assertEqual((u.INSTALL/'use.py').read_bytes(),newer)

    def test_partial_failure_continues_and_verifies_expected_target(self):
        calls=[];versions={'chrome-use':'1.0.0','mail-use':'1.0.0'}
        def run(args,cwd=None,timeout=240):
            calls.append([str(x) for x in args])
            if args[-1]=='--help':return 0,'Commands: upgrade'
            if args[-1]=='--version':return 0,versions[args[0]]
            if args[-1]=='--check':return 0,'1.0.0 -> 2.0.0'
            if args[-1]=='upgrade':
                if args[0]=='chrome-use':return 2,'failed'
                versions[args[0]]='2.0.0';return 0,'done'
            return 0,''
        with patch.object(u,'installed_cli',side_effect=lambda n:n),patch.object(u,'run',side_effect=run),patch.object(u,'git_roots',return_value=[]):
            result,code=u.upgrade(self.args)
        self.assertEqual(code,2)
        self.assertEqual([x['status'] for x in result['items']],['failed','updated'])
        self.assertIn(['mail-use','upgrade'],calls)
        self.assertTrue((u.STATE/'last-report.json').exists())

    def test_zero_exit_without_version_update_is_failure(self):
        report={'items':[],'json':True}
        with patch.object(u,'run',return_value=(0,'pretended success')):
            row=u.step(report,'test','cli',['test'],before='1.0.0',after=lambda:'1.0.0',target='2.0.0')
        self.assertEqual(row['status'],'failed')

    def test_check_never_upgrades_or_records_successful_run(self):
        self.args.check=True
        with patch.object(u,'installed_cli',side_effect=lambda n:n),patch.object(u,'run',return_value=(0,'Commands: upgrade')),patch.object(u,'cli_version',return_value='1.0.0'),patch.object(u,'expected_cli',return_value='2.0.0'),patch.object(u,'git_roots',return_value=[]),patch.object(u,'step') as step:
            result,code=u.upgrade(self.args)
        self.assertEqual(code,0);step.assert_not_called()
        self.assertEqual(result['items'][0]['status'],'available')
        self.assertFalse((u.STATE/'last-report.json').exists())

    def test_auto_consent_interval_and_disabled_state(self):
        self.args.automatic=True
        self.assertEqual(u.upgrade(self.args)[0]['skipped'],'automatic upgrades disabled')
        u.save(u.CONFIG,{'enabled':True,'intervalHours':24})
        u.save(u.STATE/'last-attempt.json',{'at':u.time.time()})
        with patch.dict(os.environ,{'CI':'','USE_NO_AUTO_UPGRADE':''}):
            self.assertEqual(u.upgrade(self.args)[0]['skipped'],'not due')

    def test_lock_is_released_and_concurrent_run_refused(self):
        # Windows locks are process-scoped; verify a separate process there and on POSIX.
        with u.lock():
            command=f"import importlib.util; s=importlib.util.spec_from_file_location('u',{str(SOURCE)!r});u=importlib.util.module_from_spec(s);s.loader.exec_module(u);print(u.busy())"
            e={**os.environ,'USE_MANAGER_STATE':str(u.STATE)}
            self.assertEqual(subprocess.check_output([sys.executable,'-c',command],env=e,text=True).strip(),'True')
        self.assertFalse(u.busy())

    def test_dirty_skill_does_not_pull_and_does_not_force(self):
        self.args.names=[]
        def run(args,cwd=None,timeout=240):return (0,' M SKILL.md') if 'status' in args else (0,'')
        with patch.object(u,'installed_cli',return_value=None),patch.object(u,'self_upgrade'),patch.object(u,'plugin_entries',return_value=[]),patch.object(u,'git_roots',return_value=[self.root/'dirty']),patch.object(u,'run',side_effect=run) as r:
            result,code=u.upgrade(self.args)
        self.assertEqual(code,2);self.assertEqual(result['items'][0]['status'],'manual')
        self.assertFalse(any('pull' in call.args[0] for call in r.call_args_list))

    def test_plugin_failure_propagates_and_no_missing_dependencies_installed(self):
        self.args.names=['mail-use']
        entries=[{'key':'mail-use@market','scope':'user','version':'1.0.0'},{'key':'other@market','scope':'user','version':'9.0.0'}]
        def run(args,cwd=None,timeout=240):return (2,'failed') if 'update' in args and 'mail-use@market' in args else (0,'')
        with patch.object(u,'installed_cli',return_value=None),patch.object(u,'plugin_entries',return_value=entries),patch.object(u,'git_roots',return_value=[]),patch.object(u.shutil,'which',return_value='claude'),patch.object(u,'run',side_effect=run) as r:
            result,code=u.upgrade(self.args)
        self.assertEqual(code,2)
        commands=[c.args[0] for c in r.call_args_list]
        self.assertFalse(any('install' in c or 'other@market' in c or '-y' in c for c in commands))

    def test_corrupt_plugin_registry_fails_before_any_upgrades(self):
        p=u.HOME/'.claude/plugins/installed_plugins.json';p.parent.mkdir(parents=True);p.write_text('{broken')
        with patch.object(u,'step') as step:
            with self.assertRaisesRegex(RuntimeError,'Cannot read'):u.upgrade(self.args)
        step.assert_not_called()

    def test_scheduler_failure_rolls_back_consent(self):
        with patch.object(u,'SCRIPT',u.INSTALL/'use.py'),patch.object(u,'schedule',side_effect=RuntimeError('unavailable')):
            with self.assertRaisesRegex(RuntimeError,'unavailable'):u.auto(SimpleNamespace(action='enable',hours=24))
        self.assertFalse(u.read(u.CONFIG).get('enabled',False))

    def test_thermo_owner_installer_supplies_app_and_alias(self):
        feed=b'<rss><channel><item><shortVersionString>1.2.3</shortVersionString></item></channel></rss>'
        report={'items':[],'json':True}
        with patch.object(u.platform,'system',return_value='Darwin'),patch.object(u,'fetch',side_effect=[feed,b'owner installer']),patch.object(u,'thermo_version',side_effect=[None,'1.2.3']),patch.object(u,'installed_cli',return_value=None),patch.object(u,'run',return_value=(0,'')) as r:
            u.thermo_upgrade(report,False)
        self.assertTrue(any(str(c.args[0][0])=='sh' for c in r.call_args_list))
        self.assertEqual(report['items'][0]['after'],'1.2.3')
        self.assertEqual(report['items'][0]['status'],'unverified') # absent alias is not a complete install


    def test_codex_refresh_preserves_enabled_state_and_scope(self):
        before={'pluginId':'motion-use@family','name':'motion-use','marketplaceName':'family','version':'1.0.0','enabled':False,'marketplaceSource':{'sourceType':'git'}}
        report={'items':[],'json':True}
        after=dict(before,version='2.0.0')
        with patch.object(u,'codex_entries',side_effect=[[before],[after]]),patch.object(u,'codex_targets',return_value={'motion-use@family':'2.0.0'}),patch.object(u.shutil,'which',return_value='codex'),patch.object(u,'run',return_value=(0,'{}')) as run:
            u.codex_upgrade(report,['motion-use'],False)
        self.assertEqual(report['items'][0]['status'],'updated')
        self.assertFalse(report['items'][0]['enabledAfter'])
        self.assertEqual(run.call_args.args[0],['codex','plugin','marketplace','upgrade','family','--json'])
        report={'items':[],'json':True}
        outsider=dict(before,pluginId='other@family',name='other')
        with patch.object(u,'codex_entries',return_value=[before,outsider]),patch.object(u,'run') as run:
            u.codex_upgrade(report,['motion-use'],False)
        run.assert_not_called();self.assertEqual(report['items'][0]['status'],'manual')

    def test_codex_noop_against_newer_target_is_not_success(self):
        row={'pluginId':'motion-use@family','name':'motion-use','marketplaceName':'family','version':'1.0.0','enabled':True,'marketplaceSource':{'sourceType':'git'}}
        report={'items':[],'json':True}
        with patch.object(u,'codex_entries',return_value=[row]),patch.object(u,'codex_targets',return_value={'motion-use@family':'2.0.0'}),patch.object(u.shutil,'which',return_value='codex'),patch.object(u,'run',return_value=(0,'{}')):
            u.codex_upgrade(report,['motion-use'],False)
        self.assertEqual(report['items'][0]['status'],'failed')

    def test_mac_scheduler_does_not_restart_an_active_job(self):
        launcher=u.BIN/'use';u.BIN.mkdir();launcher.write_text(u.MARKER)
        calls=[]
        def run(args,cwd=None,timeout=240):calls.append(list(map(str,args)));return (1,'not loaded') if 'print' in args else (0,'')
        with patch.object(u,'run',side_effect=run),patch.object(u.os,'getuid',return_value=501,create=True):
            u.schedule('Darwin',True)
        self.assertFalse(any('bootout' in c for c in calls))
        self.assertTrue(any('bootstrap' in c for c in calls))
        import plistlib
        data=plistlib.loads((u.HOME/'Library/LaunchAgents/com.leeguooooo.use-upgrade.plist').read_bytes())
        self.assertEqual(data['ProgramArguments'][0],str(launcher))
        self.assertEqual(data['StartInterval'],3600)


    def test_verified_copy_updates_with_backup_and_keeps_local_edits(self):
        old=self.root/'old';new=self.root/'new';target=self.root/'.agents/skills/ocs'
        for p in (old,new,target):p.mkdir(parents=True)
        (old/'SKILL.md').write_text('old');(target/'SKILL.md').write_text('old');(new/'SKILL.md').write_text('new')
        baseline={'ocs':[{'path':str(old),'hash':u.folder_hash(old),'version':'1.0.0'}]}
        latest={'ocs':[{'path':str(new),'hash':u.folder_hash(new),'version':'2.0.0'}]}
        item=dict(name='ocs',path=str(target),channel='skill',status='manual')
        report={'items':[],'json':True}
        with patch.object(u,'canonical_sources',return_value=latest):u.refresh_copies(report,[dict(item)],baseline,['ocs'],False)
        self.assertEqual((target/'SKILL.md').read_text(),'new')
        self.assertEqual(report['items'][0]['status'],'updated')
        self.assertEqual((Path(report['items'][0]['backup'])/'SKILL.md').read_text(),'old')
        (target/'SKILL.md').write_text('my own edits')
        report={'items':[],'json':True}
        with patch.object(u,'canonical_sources',return_value=latest):u.refresh_copies(report,[dict(item)],baseline,['ocs'],False)
        self.assertEqual(report['items'][0]['status'],'manual')
        self.assertEqual((target/'SKILL.md').read_text(),'my own edits')

    def test_release_checksum_is_required_before_install(self):
        import io,tarfile,hashlib
        blob=io.BytesIO()
        with tarfile.open(fileobj=blob,mode='w:gz') as tar:
            member=tarfile.TarInfo('use.py');content=SOURCE.read_bytes();member.size=len(content);tar.addfile(member,io.BytesIO(content))
        archive=blob.getvalue();name='use-v0.15.2.tar.gz'
        data={'tag_name':'use-v0.15.2','assets':[{'name':n,'browser_download_url':'https://github.com/leeguooooo/plugins/releases/download/use-v0.15.2/'+n} for n in (name,name+'.sha256')]}
        with patch.object(u,'fetch',side_effect=[archive,(hashlib.sha256(archive).hexdigest()+'  '+name).encode()]):self.assertEqual(u.release_script(data),SOURCE.read_bytes())
        with patch.object(u,'fetch',side_effect=[archive,('0'*64+'  '+name).encode()]):
            with self.assertRaisesRegex(RuntimeError,'checksum'):u.release_script(data)
        self.assertFalse(u.INSTALL.exists())


    def test_auto_member_optout_filters_every_channel(self):
        self.args.automatic=True
        u.save(u.CONFIG,{'enabled':True,'intervalHours':24})
        with patch.dict(os.environ,{'CI':'','USE_NO_AUTO_UPGRADE':'','MAIL_USE_NO_AUTO_UPGRADE':'1'}),patch.object(u,'installed_cli',return_value=None),patch.object(u,'git_roots',return_value=[]) as git,patch.object(u,'codex_upgrade') as codex,patch.object(u,'plugin_entries',return_value=[{'key':'mail-use@market','scope':'user','version':'1.0.0'}]),patch.object(u,'step') as step:
            u.upgrade(self.args)
        self.assertEqual(git.call_args.args[0],['chrome-use'])
        self.assertEqual(codex.call_args.args[1],['chrome-use'])
        step.assert_not_called()

    def test_unknown_target_and_any_downgrade_are_not_verified(self):
        report={'items':[],'json':True}
        with patch.object(u,'run',return_value=(0,'')):
            self.assertEqual(u.step(report,'x','cli',['x'],before='2.0.0',after=lambda:'1.0.0')['status'],'failed')
            self.assertEqual(u.step(report,'x','cli',['x'],before='2.0.0',after=lambda:'3.0.0')['status'],'unverified')

    def test_timeout_terminates_own_descendant_before_return(self):
        marker=self.root/'late';ready=self.root/'ready'
        child="from pathlib import Path;import time;Path(%r).write_text('ready');time.sleep(1.2);Path(%r).write_text('late')"%(str(ready),str(marker))
        parent="import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',%r]);time.sleep(8)"%child
        code,_=u.run([sys.executable,'-c',parent],timeout=.8)
        self.assertEqual(code,124);self.assertTrue(ready.exists())
        u.time.sleep(1.4);self.assertFalse(marker.exists())
        self.assertEqual(u.run([sys.executable,'-c','print(123)'])[0],0)

    def test_thermo_codex_plugin_without_cli_installs_its_app(self):
        self.args.names=['thermo-use']
        with patch.object(u,'installed_cli',return_value=None),patch.object(u,'thermo_version',return_value=None),patch.object(u,'codex_entries',return_value=[{'name':'thermo-use'}]),patch.object(u,'thermo_upgrade') as thermo,patch.object(u,'codex_upgrade'),patch.object(u,'git_roots',return_value=[]):
            u.upgrade(self.args)
        thermo.assert_called_once()

    def test_scheduler_context_preserves_custom_paths_and_optouts(self):
        u.BIN.mkdir();(u.BIN/'use').write_text(u.MARKER)
        with patch.dict(os.environ,{'MAIL_USE_NO_AUTO_UPGRADE':'1'}),patch.object(u,'run',return_value=(1,'not registered')):
            with self.assertRaises(RuntimeError):u.schedule('Windows',True)
        context=u.read(u.STATE/'scheduler-context.json')
        self.assertEqual(context['USE_MANAGER_STATE'],str(u.STATE))
        self.assertEqual(context['USE_MANAGER_HOME'],str(u.INSTALL))
        self.assertEqual(context['USE_FAMILY_DIR'],str(u.BASE))
        self.assertEqual(context['MAIL_USE_NO_AUTO_UPGRADE'],'1')
        with patch.dict(os.environ,{},clear=False):
            u.apply_context(u.STATE/'scheduler-context.json')
        self.assertEqual(u.CONFIG,u.STATE/'config.json')

    def test_installed_custom_state_is_remembered_without_environment(self):
        u.install_bytes(SOURCE.read_bytes(),u.VERSION)
        u.save(u.CONFIG,{'enabled':True,'intervalHours':24})
        u.save(u.STATE/'last-attempt.json',{'at':u.time.time()})
        e=dict(os.environ)
        for key in ('USE_MANAGER_STATE','USE_MANAGER_HOME','USE_MANAGER_BIN','USE_FAMILY_DIR'):e.pop(key,None)
        e.pop('CI',None);e.pop('USE_NO_AUTO_UPGRADE',None)
        result=json.loads(subprocess.check_output([sys.executable,str(u.INSTALL/'use.py'),'upgrade','--automatic','--json'],env=e,text=True))
        self.assertEqual(result['skipped'],'not due')

    def test_compact_report_groups_tools_and_preserved_copies(self):
        rows=[{'name':'chrome-use','channel':'cli','status':'current'} for _ in range(60)]
        rows += [dict(name='mail-use@market',channel=c,status='updated',before='1.0.0',after='2.0.0') for c in ('plugin','codex-plugin')]
        rows += [dict(name='android-use',channel='skill',status='manual',path='/skills/'+p,reason='local copy differs from known owner baseline; preserved') for p in ('a','b')]
        out=io.StringIO()
        with contextlib.redirect_stdout(out):u.print_report({'items':rows})
        text=out.getvalue()
        self.assertIn('1 个已更新',text);self.assertIn('1 个工具的 2 份技能副本',text)
        self.assertNotIn('chrome-use',text);self.assertLess(len(text.splitlines()),11)
        self.assertIn('Claude 插件',text);self.assertIn('Codex 插件',text)

    def test_problems_are_grouped_per_tool_with_next_steps(self):
        rows=[dict(name='wechat-use',channel='cli',status='failed',exitCode=2,reason='owner command failed; see private upgrade log'),
              dict(name='wechat-use',channel='skill',status='failed',exitCode=128,path=str(u.HOME/'family/wechat-use'),reason='Git history diverged; local checkout preserved'),
              dict(name='motion-use',channel='cli',status='unverified',exitCode=1,reason='CLI help could not be read; upgrade support not determined')]
        for lang in ('en','zh'):
            out=io.StringIO()
            with patch.object(u,'UI_LANG',lang),contextlib.redirect_stdout(out):u.print_report({'items':rows})
            text=out.getvalue()
            self.assertEqual(text.count('✗ wechat-use'),1);self.assertIn('! motion-use',text)
            self.assertIn('1 failed · 1 needs attention' if lang=='en' else '1 个失败 · 1 个需处理',text)
            self.assertIn('→ wechat-use upgrade',text);self.assertIn('→ motion-use --help',text)
            self.assertIn('→ git -C '+os.path.join('~','family','wechat-use')+' status -sb',text)
            self.assertNotIn(str(u.HOME),text)

    def test_colors_only_on_request_or_terminal(self):
        rows=[dict(name='mail-use',channel='cli',status='updated',before='1.0.0',after='2.0.0'),
              dict(name='wechat-use',channel='cli',status='failed',exitCode=2,reason='owner command failed; see private upgrade log')]
        for env,colored in (({'FORCE_COLOR':'1'},True),({'FORCE_COLOR':'1','NO_COLOR':'1'},False),({},False)):
            out=io.StringIO()
            with patch.dict(os.environ,env),contextlib.redirect_stdout(out):
                if 'NO_COLOR' not in env:os.environ.pop('NO_COLOR',None)
                if not env:os.environ.pop('FORCE_COLOR',None)
                u.print_report({'items':rows})
            text=out.getvalue()
            if colored:self.assertIn('\033[32;1m✓',text);self.assertIn('\033[31;1m✗',text)
            else:self.assertNotIn('\033[',text)

    def test_english_summary_uses_singular_forms(self):
        rows=[dict(name='mail-use',channel='cli',status='failed',exitCode=2,reason='owner command failed; see private upgrade log'),
              dict(name='android-use',channel='skill',status='manual',path='/skills/a',reason='local copy differs from known owner baseline; preserved')]
        out=io.StringIO()
        with patch.object(u,'UI_LANG','en'),contextlib.redirect_stdout(out):u.print_report({'items':rows})
        text=out.getvalue()
        self.assertIn('1 failed',text);self.assertIn('1 skill copy of 1 tool untouched',text)

    def test_host_and_installer_markers_do_not_change_skill_hash(self):
        a,b=self.root/'a',self.root/'b'
        for d in (a,b):d.mkdir();(d/'SKILL.md').write_text('---\nname: x\n---\n')
        (b/'.in_use').write_text('');(b/'.iphone-use-release').write_text('v1')
        self.assertEqual(u.folder_hash(a),u.folder_hash(b))
        (b/'notes.md').write_text('edit')
        self.assertNotEqual(u.folder_hash(a),u.folder_hash(b))

    def test_skill_pull_that_moves_head_is_reported_as_updated(self):
        (u.BASE/'chrome-use').mkdir(parents=True)
        heads=iter(['abc1234\n','def5678\n'])
        def run(args,cwd=None,timeout=240):
            if 'rev-parse' in args and '--show-toplevel' in args:return 0,str(u.BASE/'chrome-use')+'\n'
            if 'rev-parse' in args:return 0,next(heads)
            return 0,''
        with patch.object(u,'run',side_effect=run),patch.object(u,'installed_cli',return_value=None),patch.object(u,'plugin_entries',return_value=[]):
            report,code=u.upgrade(SimpleNamespace(automatic=False,check=False,json=True,names=['chrome-use']))
        row=next(i for i in report['items'] if i['channel']=='skill')
        self.assertEqual((row['status'],row['before'],row['after']),('updated','abc1234','def5678'));self.assertEqual(code,0)
        out=io.StringIO()
        with contextlib.redirect_stdout(out):u.print_report(report)
        self.assertIn('✓ chrome-use  技能 abc1234 → def5678',out.getvalue())

    def test_failure_keeps_safe_reason_and_repository_path(self):
        report={'items':[],'json':True}
        with patch.object(u,'run',return_value=(128,'private diagnostic\nfatal: Not possible to fast-forward, aborting.')):
            row=u.step(report,'wechat-use','skill',['git','pull','--ff-only'])
        self.assertEqual(row['reason'],'Git history diverged; local checkout preserved')
        self.assertNotIn('private diagnostic',json.dumps(report))
        self.assertIn('无法安全快进',u.human_reason(row))

    def test_report_is_read_only_and_json_preserves_saved_schema(self):
        report={'ok':False,'items':[{'name':'wechat-use','channel':'skill','status':'failed','exitCode':128}]}
        u.save(u.STATE/'last-report.json',report)
        before=(u.STATE/'last-report.json').read_bytes();out=io.StringIO()
        with patch.object(u,'upgrade') as upgrade,contextlib.redirect_stdout(out):code=u.main(['report','--json'])
        self.assertEqual(code,2);upgrade.assert_not_called()
        self.assertEqual(json.loads(out.getvalue()),report)
        self.assertEqual((u.STATE/'last-report.json').read_bytes(),before)

    def test_legacy_report_recovers_only_its_own_failure_entry(self):
        at=u.datetime.datetime(2026,10,21,20,8,45).timestamp()
        report={'started':at-10,'finished':at+10,'items':[dict(name='wechat-use',channel='skill',status='failed',exitCode=128)]}
        u.save(u.STATE/'last-report.json',report)
        (u.STATE/'upgrade.log').write_text('\n2026-10-20T20:08:45 skill wechat-use\nHTTP 403\n\n2026-10-21T20:08:45 skill wechat-use\nfatal: Not possible to fast-forward, aborting.\n')
        loaded=u.load_report()
        self.assertEqual(loaded['items'][0]['reason'],'Git history diverged; local checkout preserved')
        self.assertNotIn('reason',u.read(u.STATE/'last-report.json')['items'][0])

    def test_progress_is_tty_only_and_verbose_keeps_paths(self):
        out=io.StringIO()
        with contextlib.redirect_stderr(out),patch.object(out,'isatty',return_value=True):
            u.progress({'json':True},'hidden')
        self.assertEqual(out.getvalue(),'')
        row=dict(name='x',channel='skill',status='failed',exitCode=128,path='/test/checkout',reason='Git history diverged; local checkout preserved')
        with contextlib.redirect_stdout(out):u.print_report({'items':[row]},verbose=True)
        self.assertIn('/test/checkout',out.getvalue());self.assertIn('完整明细',out.getvalue())

    def test_language_precedence_and_english_fallback(self):
        with patch.dict(os.environ,{'USE_LANG':'zh','LANGUAGE':'','LC_ALL':'en_US.UTF-8','LC_MESSAGES':'','LANG':'zh_CN.UTF-8'},clear=True):
            self.assertEqual(u.choose_language(),'zh')
            self.assertEqual(u.choose_language('en'),'en')
            self.assertEqual(u.choose_language('auto'),'en')
        with patch.dict(os.environ,{'LANGUAGE':'zh_CN','LC_ALL':'C'},clear=True):
            self.assertEqual(u.choose_language(),'en');self.assertEqual(u.choose_language('zh'),'zh')
        for locale,expected in [('zh_CN.UTF-8','zh'),('zh-Hant','zh'),('en_GB.UTF-8','en'),('ja_JP.UTF-8','en'),('C','en'),('POSIX','en')]:
            with patch.dict(os.environ,{'LANG':locale},clear=True):self.assertEqual(u.choose_language(),expected)

    def test_both_report_languages_and_json_are_consistent(self):
        report={'ok':False,'items':[dict(name='mail-use',channel='cli',status='pending',reason='GitHub API rate limit reached; CLI upgrade deferred'),dict(name='wechat-use',channel='skill',status='failed',reason='Git history diverged; local checkout preserved'),dict(name='android-use',channel='skill',status='manual',reason='local copy differs from known owner baseline; preserved',path='/skills/a')]}
        u.save(u.STATE/'last-report.json',report)
        for lang in ('en','zh'):
            out=io.StringIO()
            with contextlib.redirect_stdout(out):self.assertEqual(u.main(['report','--lang',lang,'--verbose']),2)
            text=out.getvalue()
            self.assertIn('GitHub',text)
            if lang=='en':self.assertNotRegex(text,r'[\u4e00-\u9fff]');self.assertIn('rate limited',text)
            else:self.assertIn('限流',text);self.assertIn('历史已分叉',text)
            out=io.StringIO()
            with contextlib.redirect_stdout(out):u.main(['--lang',lang,'report','--json'])
            self.assertEqual(json.loads(out.getvalue()),report)

    def test_help_and_errors_have_both_languages(self):
        for lang,word in [('en','output language'),('zh','输出语言')]:
            out=io.StringIO()
            with contextlib.redirect_stdout(out),self.assertRaises(SystemExit) as raised:u.main(['--lang',lang,'--help'])
            self.assertEqual(raised.exception.code,0);self.assertIn(word,out.getvalue())
            with patch.object(u,'read',return_value={}):
                err=io.StringIO()
                with contextlib.redirect_stderr(err):self.assertEqual(u.main(['--lang',lang,'report']),2)
                self.assertIn('No upgrade report' if lang=='en' else '尚无升级报告',err.getvalue())

    def test_rate_limit_defers_all_clis_without_owner_requests(self):
        with patch.object(u,'github_limit_reached',return_value=True),patch.object(u,'installed_cli',side_effect=lambda n:n),patch.object(u,'cli_version',return_value='1.0.0'),patch.object(u,'run') as run,patch.object(u,'git_roots',return_value=[]):
            report,code=u.upgrade(self.args)
        self.assertEqual(code,2);run.assert_not_called()
        self.assertEqual([r['status'] for r in report['items']],['pending','pending'])

    def test_unknown_target_never_runs_installer_or_mislabels_wechat_support(self):
        self.args.names=['wechat-use']
        with patch.object(u,'installed_cli',return_value='wechat-use'),patch.object(u,'run',side_effect=lambda a,**kw:(0,'Commands: status') if a[-1]=='--help' else (1,'HTTP 403')),patch.object(u,'cli_version',return_value='1.19.1'),patch.object(u,'git_roots',return_value=[]),patch.object(u,'step') as step:
            report,code=u.upgrade(self.args)
        step.assert_not_called();self.assertEqual(code,2)
        self.assertEqual(report['items'][0]['status'],'unverified')
        self.assertEqual(report['items'][0]['reason'],'remote access denied (HTTP 403)')

    def test_current_cli_does_not_reinstall(self):
        with patch.object(u,'installed_cli',side_effect=lambda n:n),patch.object(u,'run',return_value=(0,'Commands: upgrade')),patch.object(u,'cli_version',return_value='1.0.0'),patch.object(u,'expected_cli',return_value='1.0.0'),patch.object(u,'git_roots',return_value=[]),patch.object(u,'step') as step:
            report,code=u.upgrade(self.args)
        step.assert_not_called();self.assertEqual(code,0)
        self.assertTrue(all(r['status']=='current' for r in report['items']))

    def test_gh_auth_is_ephemeral_and_never_enters_report(self):
        secret='gho_'+('test_credential_'*3)
        with patch.dict(os.environ,{},clear=True),patch.dict(u.UPGRADE_AUTH,{},clear=True),patch.object(u.shutil,'which',return_value='gh'),patch.object(u,'run',return_value=(0,secret)):
            with self.real_auth():
                self.assertEqual(u.env()['GH_TOKEN'],secret)
                self.assertEqual(u.env()['GITHUB_TOKEN'],secret)
                self.assertNotIn('GH_TOKEN',os.environ)
                u.write_log('owner echoed '+secret)
                self.assertNotIn(secret,(u.STATE/'upgrade.log').read_text())
                u.PROBES['fake']=(0,'cached '+secret)
            self.assertEqual(u.UPGRADE_AUTH,{})
            self.assertEqual(u.PROBES,{})
            with self.assertRaises(RuntimeError):
                with self.real_auth():raise RuntimeError('stop')
            self.assertEqual(u.UPGRADE_AUTH,{})

    def test_captured_subprocess_output_redacts_known_tokens(self):
        secret='test-token-not-a-real-credential'
        with patch.dict(u.UPGRADE_AUTH,{'GH_TOKEN':secret},clear=True):
            code,text=u.run([sys.executable,'-c',f'print({secret!r})'])
        self.assertEqual(code,0);self.assertEqual(text.strip(),'[redacted]')

    def test_utf8_state_and_unicode_install_paths(self):
        data={'path':'工具/安装目录','message':'中文 and English'}
        u.save(u.STATE/'unicode.json',data)
        self.assertEqual(json.loads((u.STATE/'unicode.json').read_bytes().decode('utf-8')),data)
        self.assertEqual(u.read(u.STATE/'unicode.json'),data)
        with patch.object(u,'INSTALL',self.root/'安装目录'):
            u.install_bytes(SOURCE.read_bytes(),u.VERSION)
            self.assertEqual(subprocess.check_output([sys.executable,str(u.INSTALL/'use.py'),'--version'],text=True).strip(),u.VERSION)

    def test_rate_limit_cache_is_validated_and_auth_does_not_use_anonymous_limit(self):
        # Read the original helper, not the default isolated-upgrade mock.
        # Restore only the function from source in a fresh isolated module.
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.STATE=u.STATE
        at=u.time.time()+300
        with patch.dict(os.environ,{},clear=True),patch.dict(module.UPGRADE_AUTH,{},clear=True),patch.object(module.urllib.request,'urlopen',return_value=io.StringIO(json.dumps({'resources':{'core':{'remaining':0,'reset':at}}}))) as request:
            self.assertTrue(module.github_limit_reached());self.assertTrue(module.github_limit_reached())
            self.assertEqual(request.call_count,1)
        with patch.dict(os.environ,{'GH_TOKEN':'test-token-not-a-secret'},clear=True),patch.object(module.urllib.request,'urlopen',return_value=io.StringIO(json.dumps({'resources':{'core':{'remaining':500,'reset':at}}}))):
            self.assertFalse(module.github_limit_reached())
        u.save(u.STATE/'github-api-limit.json',{'reset':'bad value'})
        with patch.dict(os.environ,{},clear=True),patch.object(module.urllib.request,'urlopen',side_effect=OSError('offline')):
            self.assertFalse(module.github_limit_reached())

if __name__=='__main__':unittest.main()
