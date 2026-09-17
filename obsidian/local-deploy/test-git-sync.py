#!/usr/bin/env python3
"""Integration tests against disposable local repositories, no network/services."""
import json, os, subprocess, tempfile
from pathlib import Path

script=Path(__file__).with_name('git-sync.py')
def git(cwd,*args):
 return subprocess.check_output(['git','-C',str(cwd),*args],stderr=subprocess.DEVNULL).decode().strip()
with tempfile.TemporaryDirectory(prefix='obsidian-sync-test-') as tmp:
 root=Path(tmp); remote=root/'remote.git'; local=root/'local'; peer=root/'peer'; state=root/'state'
 subprocess.run(['git','init','--bare',str(remote)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 subprocess.run(['git','clone',str(remote),str(local)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 git(local,'checkout','-b','master')
 for repo in [local]:
  git(repo,'config','user.name','Sync Test');git(repo,'config','user.email','sync@example.invalid')
 (local/'note.md').write_text('initial\n');(local/'.gitignore').write_text('ignored.txt\n')
 git(local,'add','.');git(local,'commit','-m','initial');git(local,'push','-u','origin','master')
 subprocess.run(['git','clone',str(remote),str(peer)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 git(peer,'config','user.name','Sync Test');git(peer,'config','user.email','sync@example.invalid')
 env={**os.environ,'OBSIDIAN_SYNC_VAULT':str(local),'OBSIDIAN_SYNC_STATE':str(state),'OBSIDIAN_SYNC_MANAGE_SERVICES':'0','OBSIDIAN_SYNC_OWNER':''}
 def sync(success=True):
  result=subprocess.run(['python3',str(script)],env=env,capture_output=True)
  assert (result.returncode==0)==success,result.stderr.decode()
  return json.loads((state/'status.json').read_text())
 def peer_commit(name,content):
  git(peer,'pull','--ff-only');(peer/name).write_text(content);git(peer,'add','.');git(peer,'commit','-m','peer change');git(peer,'push')
 (local/'note.md').write_text('local edit\n');assert sync()['state']=='synced'
 assert git(local,'rev-parse','HEAD')==git(remote,'rev-parse','master')
 print('PASS local edit push')
 peer_commit('remote.md','remote note\n');sync();assert (local/'remote.md').read_text()=='remote note\n'
 print('PASS remote pull')
 (local/'local.md').write_text('local concurrent\n');peer_commit('remote.md','remote concurrent\n');sync()
 assert (local/'local.md').exists() and (local/'remote.md').read_text()=='remote concurrent\n'
 print('PASS nonconflicting concurrent edits merge')
 (local/'ignored.txt').write_text('ignored');head=git(local,'rev-parse','HEAD');sync();assert git(local,'rev-parse','HEAD')==head
 (local/'local.md').unlink();sync();assert 'local.md' not in git(remote,'ls-tree','--name-only','master').splitlines()
 print('PASS ignored files and deletion sync')
 (local/'note.md').write_text('local conflict\n');peer_commit('note.md','remote conflict\n');report=sync(False)
 assert report['state']=='blocked' and 'Merge conflict' in report['reason']
 assert (local/'note.md').read_text()=='local conflict\n' and not (local/'.git/MERGE_HEAD').exists()
 assert git(peer,'show','HEAD:note.md')=='remote conflict'
 assert len(git(local,'worktree','list').splitlines())==1
 print('PASS conflicts preserve both versions and leave worktree intact')
