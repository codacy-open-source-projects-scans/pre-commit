from __future__ import annotations

import contextlib
import os
import sys
from collections.abc import Generator
from collections.abc import Sequence

from pre_commit import lang_base
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output

ENVIRONMENT_DIR = 'lua_env'
get_default_version = lang_base.basic_get_default_version
health_check = lang_base.basic_health_check
run_hook = lang_base.basic_run_hook


def _get_lua_version() -> str:  # pragma: win32 no cover
    """Get the Lua version used in file paths."""
    _, stdout, _ = cmd_output('luarocks', 'config', '--lua-ver')
    return stdout.strip()


def get_env_patch(d: str) -> PatchesT:  # pragma: win32 no cover
    version = _get_lua_version()
    so_ext = 'dll' if sys.platform == 'win32' else 'so'
    return (
        ('PATH', (os.path.join(d, 'bin'), os.pathsep, Var('PATH'))),
        (
            'LUA_PATH', (
                os.path.join(d, 'share', 'lua', version, '?.lua;'),
                os.path.join(d, 'share', 'lua', version, '?', 'init.lua;;'),
            ),
        ),
        (
            'LUA_CPATH',
            (os.path.join(d, 'lib', 'lua', version, f'?.{so_ext};;'),),
        ),
    )


@contextlib.contextmanager  # pragma: win32 no cover
def in_env(prefix: Prefix, version: str) -> Generator[None]:
    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with envcontext(get_env_patch(envdir)):
        yield


def install_environment(
    prefix: Prefix,
    version: str,
    additional_dependencies: Sequence[str],
) -> None:  # pragma: win32 no cover
    lang_base.assert_version_default('lua', version)

    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with in_env(prefix, version):
        # luarocks doesn't bootstrap a tree prior to installing
        # so ensure the directory exists.
        os.makedirs(envdir, exist_ok=True)

        # Older luarocks (e.g., 2.4.2) expect the rockspec as an arg
        for rockspec in prefix.star('.rockspec'):
            make_cmd = ('luarocks', '--tree', envdir, 'make', rockspec)
            lang_base.setup_cmd(prefix, make_cmd)

        # luarocks can't install multiple packages at once
        # so install them individually.
        for dependency in additional_dependencies:
            cmd = ('luarocks', '--tree', envdir, 'install', dependency)
            lang_base.setup_cmd(prefix, cmd)
