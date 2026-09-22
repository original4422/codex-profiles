#!/usr/bin/env python3
"""Account-scoped launchers. No authentication token reading or copying."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import plistlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlparse


def state_root():
    return Path.home() / 'Library/Application Support/Codex Profiles'


def clean_environment(source=None):
    return {k: v for k, v in (os.environ if source is None else source).items()
            if not k.startswith('CODEX_') and k not in
            {'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'ELECTRON_RUN_AS_NODE'}}


def absolute(value):
    return str(Path(value).expanduser().absolute())


def overlaps(left, right):
    a, b = Path(left).resolve(), Path(right).resolve()
    return a == b or a in b.parents or b in a.parents


def validate_profile(identifier, profile, others):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,31}', identifier):
        raise ValueError('Profile ID must be 1–32 lowercase letters, digits or hyphens; start with a letter.')
    paths = [profile['home'], profile['desktop_data']]
    for path in paths:
        if not Path(path).is_absolute() or Path(path).is_symlink():
            raise ValueError('Profile paths must be absolute, non-symlink directories.')
        if Path(path).resolve() in [Path('/'), Path.home().resolve()]:
            raise ValueError('A profile cannot use the filesystem root or your home directory.')
    if overlaps(*paths):
        raise ValueError('Codex home and desktop data must be separate directories.')
    for other_id, other in others.items():
        if other_id == identifier:
            continue
        if any(overlaps(x, other[y]) for x in paths for y in ['home', 'desktop_data']):
            raise ValueError(f'Profile directories overlap with account {other_id}.')


def save_registry(root, data):
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=root, prefix='.profiles-', suffix='.json')
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(data, output, ensure_ascii=False, indent=2)
            output.write('\n')
        os.replace(name, root / 'profiles.json')
    finally:
        if os.path.exists(name):
            os.unlink(name)


def load_registry(root):
    data = json.loads((root / 'profiles.json').read_text())
    for identifier, profile in data['profiles'].items():
        validate_profile(identifier, profile, data['profiles'])
    return data


def prepare_profile(profile):
    # Existing account files are never rewritten, and auth.json is never read.
    for key in ['home', 'desktop_data']:
        directory = Path(profile[key])
        if directory.is_symlink():
            raise ValueError(f'Refusing symlinked profile directory: {directory}')
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    config = Path(profile['home']) / 'config.toml'
    if not config.exists():
        with config.open('x') as output:
            output.write('cli_auth_credentials_store = "file"\nforced_login_method = "chatgpt"\n')


def find_app(profile):
    candidates = [Path(profile['app'])] if profile.get('app') else [
        Path('/Applications/ChatGPT.app'), Path.home() / 'Applications/ChatGPT.app',
        Path('/Applications/Codex.app'), Path.home() / 'Applications/Codex.app']
    for app in candidates:
        if os.access(app / 'Contents/Resources/codex', os.X_OK):
            return app
    raise ValueError('Official ChatGPT/Codex app not found. Set the profile app path with --app.')


def desktop_invocation(profile, app, source=None):
    env = clean_environment(source)
    env['CODEX_HOME'] = profile['home']
    env['CODEX_ELECTRON_USER_DATA_PATH'] = profile['desktop_data']
    return ['/usr/bin/open', '-n', '--env', 'CODEX_HOME=' + profile['home'],
            '--env', 'CODEX_ELECTRON_USER_DATA_PATH=' + profile['desktop_data'],
            str(app), '--args', '--user-data-dir=' + profile['desktop_data']], env


def find_profile_pid(profile, app):
    """Match an existing process by the data files it actually has open, not app name."""
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    executable = str(app / 'Contents/MacOS' / info['CFBundleExecutable'])
    prefix = str(Path(profile['desktop_data']).resolve()) + '/'
    rows = subprocess.check_output(['/bin/ps', '-axo', 'pid=,comm='], text=True).splitlines()
    for row in rows:
        parts = row.strip().split(None, 1)
        if len(parts) != 2 or parts[1] != executable:
            continue
        opened = subprocess.run(['/usr/sbin/lsof', '-p', parts[0], '-Fn'],
                                capture_output=True, text=True, timeout=10).stdout.splitlines()
        if any(line.startswith('n' + prefix) for line in opened):
            return parts[0]
    return None


def launch_desktop(root, profile):
    app = find_app(profile)
    pid = find_profile_pid(profile, app)
    if pid:
        # Especially important for the original/default profile: its existing
        # macOS process may not hold Electron's explicit-profile singleton lock.
        helper = root / 'engine/bin/FocusApp'
        subprocess.run([str(helper), pid], check=True, env=clean_environment())
        return
    args, env = desktop_invocation(profile, app)
    subprocess.run(args, env=env, check=True)


def run_cli(profile, arguments):
    executable = shutil.which('codex')
    if not executable:
        executable = str(find_app(profile) / 'Contents/Resources/codex')
    env = clean_environment()
    env['CODEX_HOME'] = profile['home']
    os.execvpe(executable, [executable, *arguments], env)


def dock_tile(app, name, bundle_id):
    return {'tile-type': 'file-tile', 'tile-data': {
        'file-data': {'_CFURLString': app.as_uri() + '/', '_CFURLStringType': 15},
        'file-label': name, 'bundle-identifier': bundle_id, 'file-type': 41}}


def tile_path(tile):
    return unquote(urlparse(tile.get('tile-data', {}).get('file-data', {}).get('_CFURLString', '')).path).rstrip('/')


def pin_tiles(tiles, app, name, bundle_id):
    """Keep one original-app pin, replace its duplicates with the account pin."""
    result, seen_official, pinned = [], set(), False
    target = str(app).rstrip('/')
    for tile in tiles:
        path = tile_path(tile)
        if path == target:
            if not pinned:
                result.append(tile)
                pinned = True
            continue
        official = tile.get('tile-data', {}).get('bundle-identifier') == 'com.openai.codex'
        if official and path in seen_official:
            if not pinned:
                result.append(dock_tile(app, name, bundle_id))
                pinned = True
            continue
        if official:
            seen_official.add(path)
        result.append(tile)
    if not pinned:
        result.append(dock_tile(app, name, bundle_id))
    return result


def pin_dock(root, profile):
    app = Path(profile['launcher'])
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    before = subprocess.check_output(['/usr/bin/defaults', 'export', 'com.apple.dock', '-'])
    data = plistlib.loads(before)
    old = data.get('persistent-apps', [])
    new = pin_tiles(old, app, profile['name'], info['CFBundleIdentifier'])
    if old == new:
        print('Dock already points to the account launcher.')
        return
    backups = root / 'backups'
    backups.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup = backups / ('dock-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.plist')
    backup.write_bytes(before)
    current = plistlib.loads(subprocess.check_output(['/usr/bin/defaults', 'export', 'com.apple.dock', '-']))
    if current.get('persistent-apps', []) != old:
        raise ValueError('Dock changed while preparing the update; retry.')
    # Write only persistent-apps, preserving all other Dock preferences.
    subprocess.run(['/usr/bin/defaults', 'write', 'com.apple.dock', 'persistent-apps', '-array',
                    *[plistlib.dumps(t).decode() for t in new]], check=True)
    subprocess.run(['/usr/bin/killall', '-u', str(os.getuid()), 'Dock'], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f'Pinned {app.name}; previous Dock preferences saved to {backup}')


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description='Open an account in the official desktop app or Codex CLI.')
    parser.add_argument('--root', type=Path, default=state_root(), help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('list')
    for command in ['desktop', 'status', 'doctor', 'terminal', 'pin']:
        commands.add_parser(command).add_argument('profile')
    cli = commands.add_parser('cli')
    cli.add_argument('profile')
    cli.add_argument('arguments', nargs=argparse.REMAINDER)
    add = commands.add_parser('add')
    add.add_argument('profile')
    add.add_argument('--name', required=True)
    add.add_argument('--home')
    add.add_argument('--desktop-data')
    add.add_argument('--app')
    options = parser.parse_args()
    root = options.root.expanduser().absolute()
    data = load_registry(root)
    if options.command == 'list':
        for identifier, profile in data['profiles'].items():
            print(f"{identifier}: {profile['name']}\n  CODEX_HOME={profile['home']}\n  desktop={profile['desktop_data']}")
        return
    if options.command == 'add':
        if options.profile in data['profiles']:
            raise ValueError('That account profile already exists.')
        if not options.name.strip() or any(x in options.name for x in '/\\\x00\n\r'):
            raise ValueError('Choose a nonempty display name without path separators or line breaks.')
        profile = {'name': options.name, 'home': absolute(options.home or root / 'accounts' / options.profile),
                   'desktop_data': absolute(options.desktop_data or root / 'desktop' / options.profile)}
        if options.app:
            profile['app'] = absolute(options.app)
        validate_profile(options.profile, profile, data['profiles'])
        data['profiles'][options.profile] = profile
        save_registry(root, data)
        print(f'Registered {options.profile}. Build its icon with:')
        print(shlex.join([sys.executable, str(root / 'engine/install.py'), '--profile', options.profile]))
        return
    if options.profile not in data['profiles']:
        raise ValueError('Unknown account profile; run codex-profile list.')
    profile = data['profiles'][options.profile]
    if options.command == 'doctor':
        app = find_app(profile)
        print(f"Profile: {options.profile}\nCODEX_HOME: {profile['home']}\nDesktop data: {profile['desktop_data']}\nApp: {app}")
        print('File-based login cache present:', (Path(profile['home']) / 'auth.json').exists())
        launcher = profile.get('launcher')
        if launcher:
            print('Launcher:', launcher)
            dock = plistlib.loads(subprocess.check_output(['/usr/bin/defaults', 'export', 'com.apple.dock', '-']))
            print('Dock points to account launcher:', any(tile_path(t) == launcher for t in dock.get('persistent-apps', [])))
        print('This checks paths, not login validity or the identity of the signed-in account.')
        return
    if options.command == 'pin':
        pin_dock(root, profile)
        return
    prepare_profile(profile)
    if options.command == 'desktop':
        launch_desktop(root, profile)
    elif options.command == 'terminal':
        directory = root / 'terminals'
        directory.mkdir(mode=0o700, exist_ok=True)
        script = directory / (options.profile + '.command')
        script.write_text('#!/bin/bash\ncd "$HOME"\nexec ' + shlex.join([
            sys.executable, str(Path(__file__).resolve()), '--root', str(root), 'cli', options.profile]) + '\n')
        script.chmod(0o700)
        subprocess.run(['/usr/bin/open', '-a', 'Terminal', str(script)], check=True)
    else:
        run_cli(profile, ['login', 'status'] if options.command == 'status' else options.arguments)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(f'codex-profile: {error}', file=sys.stderr)
        sys.exit(1)
