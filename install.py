#!/usr/bin/env python3
"""Build native account icons locally; keep all private state outside this repo."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import plistlib
import shlex
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE / 'src'))
from profiles import load_registry, save_registry, state_root, validate_profile


def build_icon(compiler, badge, destination, work):
    full = work / 'icon.png'
    subprocess.run([str(compiler), str(full), badge], check=True)
    iconset = work / 'Account.iconset'
    iconset.mkdir()
    for size in [16, 32, 128, 256, 512]:
        for scale in [1, 2]:
            name = f'icon_{size}x{size}' + ('@2x' if scale == 2 else '') + '.png'
            subprocess.run(['/usr/bin/sips', '-z', str(size*scale), str(size*scale),
                            str(full), '--out', str(iconset / name)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['/usr/bin/iconutil', '-c', 'icns', str(iconset), '-o', str(destination)], check=True)


def backup_path(path, backups):
    if not path.exists() and not path.is_symlink():
        return
    backups.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = backups / path.name
    if path.is_dir() and not path.is_symlink():
        shutil.copytree(path, target, symlinks=True)
    else:
        shutil.copy2(path, target, follow_symlinks=False)


def install_command(path, content, backups):
    if path.exists() or path.is_symlink():
        legacy = path.name == 'codex-account-2' and path.is_symlink() and 'Codex 第二账号.app/Contents/MacOS/codex-account-2' in str(path.readlink())
        owned = not path.is_symlink() and 'Managed by Codex Profiles' in path.read_text()
        if not legacy and not owned:
            raise ValueError(f'Refusing to replace an unrelated command: {path}')
        backup_path(path, backups)
        path.unlink()
    path.write_text(content)
    path.chmod(0o755)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', default='b', help='Account to create a Dock launcher for (default: b).')
    parser.add_argument('--pin', action='store_true', help='Back up and update Dock pins.')
    parser.add_argument('--root', type=Path, default=state_root(), help=argparse.SUPPRESS)
    parser.add_argument('--applications-dir', type=Path, default=Path.home() / 'Applications', help=argparse.SUPPRESS)
    parser.add_argument('--bin-dir', type=Path, default=Path.home() / '.local/bin', help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = args.root.expanduser().absolute()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if (root / 'profiles.json').exists():
        registry = load_registry(root)
    else:
        registry = {'version': 1, 'profiles': {
            'a': {'name': 'Codex 第一账号', 'home': str(Path.home()/'.codex'),
                  'desktop_data': str(Path.home()/'Library/Application Support/Codex')},
            'b': {'name': 'Codex 第二账号', 'home': str(Path.home()/'.codex-account-2'),
                  'desktop_data': str(Path.home()/'Library/Application Support/Codex Account 2')},
        }}
    if args.profile not in registry['profiles']:
        raise ValueError('Register the account first with codex-profile add.')
    for identifier, profile in registry['profiles'].items():
        validate_profile(identifier, profile, registry['profiles'])
    profile = registry['profiles'][args.profile]
    app = args.applications_dir.expanduser().absolute() / (profile['name'] + '.app')
    bundle_id = 'local.codex.profiles.' + args.profile
    if app.exists():
        existing = plistlib.loads((app/'Contents/Info.plist').read_bytes()).get('CFBundleIdentifier')
        if existing not in {bundle_id, 'local.codex.second-account-launcher'}:
            raise ValueError(f'Refusing to replace an unrelated application: {app}')
        processes = subprocess.check_output(['ps', '-axo', 'comm='], text=True).splitlines()
        if str(app/'Contents/MacOS/AccountLauncher') in [x.strip() for x in processes]:
            raise ValueError('Quit the account launcher before upgrading it; the official app may remain open.')
    engine = root/'engine'
    python = shutil.which('python3') or sys.executable
    backups = root/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')

    with tempfile.TemporaryDirectory(prefix='codex-profiles-build-') as temp:
        work = Path(temp)
        launcher = work/'AccountLauncher'
        icon_tool = work/'MakeIcon'
        focus_tool = work/'FocusApp'
        for source, target in [('AccountLauncher.swift', launcher), ('MakeIcon.swift', icon_tool), ('FocusApp.swift', focus_tool)]:
            subprocess.run(['xcrun', 'swiftc', '-O', '-framework', 'AppKit', str(SOURCE/'src'/source), '-o', str(target)], check=True)
        staging = work/app.name
        contents = staging/'Contents'
        (contents/'MacOS').mkdir(parents=True)
        (contents/'Resources').mkdir()
        shutil.copy2(launcher, contents/'MacOS/AccountLauncher')
        badge = str(list(registry['profiles']).index(args.profile) + 1)
        build_icon(icon_tool, badge, contents/'Resources/Account.icns', work)
        info = {'CFBundleIdentifier': bundle_id, 'CFBundleName': profile['name'],
                'CFBundleDisplayName': profile['name'], 'CFBundleExecutable': 'AccountLauncher',
                'CFBundlePackageType': 'APPL', 'CFBundleVersion': '2', 'CFBundleShortVersionString': '0.2.0',
                'CFBundleIconFile': 'Account.icns', 'NSHighResolutionCapable': True,
                'AccountProfile': args.profile, 'AccountPython': python,
                'AccountEngine': str(engine/'src/profiles.py'), 'AccountRoot': str(root)}
        (contents/'Info.plist').write_bytes(plistlib.dumps(info))
        subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(staging)], check=True)
        backup_path(app, backups)
        backup_path(root/'profiles.json', backups)
        if SOURCE != engine:
            backup_path(engine, backups)
            (engine/'src').mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE/'install.py', engine/'install.py')
            for name in ['profiles.py', 'AccountLauncher.swift', 'MakeIcon.swift', 'FocusApp.swift']:
                shutil.copy2(SOURCE/'src'/name, engine/'src'/name)
        (engine/'bin').mkdir(parents=True, exist_ok=True)
        shutil.copy2(focus_tool, engine/'bin/FocusApp')
        app.parent.mkdir(parents=True, exist_ok=True)
        if app.exists():
            shutil.rmtree(app)  # Only an identified managed launcher, after backup.
        shutil.copytree(staging, app)
        profile['launcher'] = str(app)
        save_registry(root, registry)

    bin_dir = args.bin_dir.expanduser().absolute()
    bin_dir.mkdir(parents=True, exist_ok=True)
    prefix = '#!/bin/bash\n# Managed by Codex Profiles\n'
    engine_command = shlex.join([python, str(engine/'src/profiles.py'), '--root', str(root)])
    install_command(bin_dir/'codex-profile', prefix + 'exec ' + engine_command + ' "$@"\n', backups)
    if 'b' in registry['profiles']:
        compatibility = prefix + 'mode="${1:-desktop}"\nif [ "$#" -gt 0 ]; then shift; fi\ncase "$mode" in\n'
        for mode in ['desktop', 'cli', 'status']:
            compatibility += f'  {mode}) exec {engine_command} {mode} b "$@" ;;\n'
        compatibility += '  *) printf "Usage: codex-account-2 [desktop|cli|status]\\n" >&2; exit 2 ;;\nesac\n'
        install_command(bin_dir/'codex-account-2', compatibility, backups)
    if args.pin:
        subprocess.run([python, str(engine/'src/profiles.py'), '--root', str(root), 'pin', args.profile], check=True)
    print(f'Launcher: {app}\nCommand: {bin_dir / "codex-profile"}\nRegistry: {root / "profiles.json"}')
    print('The ordinary codex command and all account credentials are unchanged.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'Installation failed: {error}', file=sys.stderr)
        sys.exit(1)
