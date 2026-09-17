#!/usr/bin/env python3
"""One safe bidirectional Git sync; called by a one-minute systemd timer.
Preview merges in a private temporary worktree. Never force-push or reset notes.
"""
import fcntl
import json
import logging
import os
from pathlib import Path
import pwd
import subprocess
import tempfile
import time

VAULT = Path(os.environ.get('OBSIDIAN_SYNC_VAULT', '/data/obsidian_library'))
STATE = Path(os.environ.get('OBSIDIAN_SYNC_STATE', '/var/lib/obsidian-git-sync'))
MANAGE = os.environ.get('OBSIDIAN_SYNC_MANAGE_SERVICES', '1') == '1'
OWNER = os.environ.get('OBSIDIAN_SYNC_OWNER', 'obsidian-mcp')
UNITS = ('obsidian-mcp.service', 'obsidian-tunnel.service')


def git(*args, cwd=None, ok=(0,)):
    directory = Path(cwd or VAULT)
    p = subprocess.run(['git', '-c', f'safe.directory={directory}', '-C', str(directory), *args],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40)
    if p.returncode not in ok:
        raise RuntimeError(f'git {args[0]} failed (exit {p.returncode}); check repository/network/permissions')
    return p


def record(state, **fields):
    data = {'state':state, 'updated_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'), **fields}
    tmp = STATE / 'status.tmp'
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    tmp.replace(STATE / 'status.json')
    logging.info('%s', json.dumps(data, ensure_ascii=False))


def check_repo():
    gd = VAULT / '.git'
    if any((gd / x).exists() for x in ('MERGE_HEAD','CHERRY_PICK_HEAD','REVERT_HEAD','rebase-merge','rebase-apply','index.lock')) or git('ls-files','-u').stdout:
        raise RuntimeError('Git operation/conflict in progress; sync paused')
    if git('symbolic-ref','--quiet','--short','HEAD').stdout.strip() != b'master':
        raise RuntimeError('Expected master branch; sync paused')


def commit_local():
    git('add','-A','--','.')
    if git('diff','--cached','--quiet',ok=(0,1)).returncode:
        git('commit','-m','Auto-sync notes '+time.strftime('%Y-%m-%d %H:%M:%S %z'))


def fix_owner():
    if not OWNER:
        return
    user = pwd.getpwnam(OWNER)
    # os.walk never descends into symlink directories. Never touch Git metadata.
    for root, dirs, files in os.walk(VAULT, followlinks=False):
        if Path(root) == VAULT:
            dirs[:] = [d for d in dirs if d != '.git']
        for name in dirs + files:
            os.chown(Path(root)/name, user.pw_uid, user.pw_gid, follow_symlinks=False)


def run():
    check_repo()
    commit_local()  # Persist local history even when the network is down.
    git('fetch','--no-tags','origin','+refs/heads/master:refs/remotes/origin/master')
    if git('merge-base','--is-ancestor','origin/master','HEAD',ok=(0,1)).returncode:
        active = []
        if MANAGE:
            active = [u for u in UNITS if subprocess.run(['systemctl','is-active','--quiet',u]).returncode == 0]
        preview = None
        try:
            if active:
                # Pause only for incoming updates; ordinary outgoing sync has no downtime.
                subprocess.run(['systemctl','stop',*reversed(active)],check=True,timeout=45)
            check_repo()
            commit_local()  # Include writes completed between fetch and the maintenance window.
            preview = Path(tempfile.mkdtemp(prefix='merge-',dir=STATE))
            git('worktree','add','--detach',str(preview),'HEAD')
            merged = git('merge','--no-edit','origin/master',cwd=preview,ok=(0,1))
            if merged.returncode:
                paths = git('diff','--name-only','--diff-filter=U',cwd=preview).stdout.decode().splitlines()
                raise RuntimeError('Merge conflict; original notes unchanged; resolve local/remote commits manually: '+', '.join(paths))
            target = git('rev-parse','HEAD',cwd=preview).stdout.decode().strip()
            if git('status','--porcelain').stdout:
                raise RuntimeError('Concurrent filesystem edits detected; pull deferred without changing notes')
            git('merge','--ff-only',target)
            fix_owner()
        finally:
            try:
                if preview is not None:
                    # Only the generated preview is discarded; local/remote commits remain intact.
                    git('worktree','remove','--force',str(preview),ok=(0,128))
            finally:
                if active:
                    subprocess.run(['systemctl','start',*active],check=True,timeout=45)
    git('push','origin','HEAD:refs/heads/master')
    head = git('rev-parse','HEAD').stdout.decode().strip()
    remote = git('ls-remote','origin','refs/heads/master').stdout.decode().split()[0]
    if head != remote:
        raise RuntimeError('Remote changed during verification; retry next minute')
    dirty = bool(git('status','--porcelain').stdout)
    record('pending' if dirty else 'synced',commit=head,remote_commit=remote,worktree_clean=not dirty)


def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    STATE.mkdir(mode=0o700,parents=True,exist_ok=True)
    with (STATE/'sync.lock').open('w') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return
        try:
            run()
        except Exception as exc:
            record('blocked',reason=str(exc),retry='next minute')
            raise SystemExit(1)


if __name__ == '__main__':
    main()
