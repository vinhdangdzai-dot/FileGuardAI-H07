"""Create a review PR for this repository using the user's Git credential helper.

Never prints/stores credentials. No merge operation. Explicit --create only.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import urllib.error
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
GIT = 'C:/Program Files/Git/cmd/git.exe' if os.name == 'nt' else 'git'
REPOSITORY = 'vinhdangdzai-dot/FileGuardAI-H07'


def git(*args, **kwargs):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never')
    return subprocess.run([GIT, *args], cwd=ROOT, env=env, capture_output=True, text=True,
                          encoding='utf-8', timeout=90, **kwargs)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--create', action='store_true')
    p.add_argument('--body-file', type=Path)
    args = p.parse_args()
    credential = git('-c', 'credential.interactive=false', 'credential', 'fill',
                     input='protocol=https\nhost=github.com\n\n')
    values = dict(line.split('=', 1) for line in credential.stdout.splitlines() if '=' in line)
    token = values.get('password')
    if not token:
        print('GitHub credential helper has no usable noninteractive credential. No push/PR performed.')
        return 2

    def api(path, body=None):
        headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                   'User-Agent': 'FileGuardAI-H07-PR', 'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json'}
        request = Request('https://api.github.com/' + path,
                          data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with urlopen(request, timeout=30) as r:
            return json.load(r)

    try:
        repo = api('repos/' + REPOSITORY)
        print('Repository accessible. Push permission:', bool(repo.get('permissions', {}).get('push')))
        if not args.create:
            return 0
        branch = git('branch', '--show-current').stdout.strip()
        if not branch.startswith('h07/') or branch in ('main', 'master'):
            raise ValueError('Use a dedicated h07 review branch')
        if git('status', '--porcelain').stdout.strip():
            raise ValueError('Commit the concrete, reviewed changes before publication')
        if args.body_file is None:
            raise ValueError('--body-file is required')
        body = args.body_file.read_text(encoding='utf-8')
        pushed = git('push', '--set-upstream', 'origin', branch)
        if pushed.returncode:
            print('Push failed. No PR was created; inspect local Git credentials/network.')
            return 3
        prs = api(f'repos/{REPOSITORY}/pulls?state=open&head=vinhdangdzai-dot:{branch}')
        if prs:
            pr = prs[0]
        else:
            pr = api(f'repos/{REPOSITORY}/pulls', {'title': 'Complete H07 minimum requirements: security, evaluation and thesis evidence',
                      'head': branch, 'base': 'main', 'body': body, 'draft': True})
        print('Review PR:', pr['html_url'])
        print('Draft:', pr['draft'], '; merged:', pr.get('merged', False))
        return 0
    except urllib.error.HTTPError as exc:
        print('GitHub API returned HTTP', exc.code, '; no merge attempted.')
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
