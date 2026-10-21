import importlib.util
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
        newer=SOURCE.read_bytes().replace(b"VERSION = '0.15.0'",b"VERSION = '9.0.0'")
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
        archive=blob.getvalue();name='use-v0.15.0.tar.gz'
        data={'tag_name':'use-v0.15.0','assets':[{'name':n,'browser_download_url':'https://github.com/leeguooooo/plugins/releases/download/use-v0.15.0/'+n} for n in (name,name+'.sha256')]}
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

if __name__=='__main__':unittest.main()
