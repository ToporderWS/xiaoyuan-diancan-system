# -*- coding: utf-8 -*-
"""配置一致性校验 —— 保证「同一个后端地址」全项目只有一份事实，且没有散落硬编码。

为什么要这个脚本：
    对外地址在项目里有 **三个必须保持一致** 的落点：
        1) backend/config.py            PUBLIC_API_BASE / PUBLIC_STATIC_BASE
        2) miniprogram/utils/config.js  PROFILES.dev.API_BASE / STATIC_BASE
        3) admin-pc/src/config.js       LAN_API_BASE / LAN_STATIC_BASE
    真机 / 生产切 HTTPS 时，任何一处漏改都会表现为「图片或接口部分可用」，
    非常难查。所以把一致性做成可自动执行的检查。

顺带检查：
    - dev 档位必须是 http 局域网地址（与后端默认一致）
    - prod 档位要么留空（未配置），要么必须是 https（不允许半填 / 填 http）
    - 页面代码里不允许再出现裸 IP（防止域名散落硬编码）

用法（在 backend 目录下）：
    python scripts/check_config_sync.py            # 默认校验 dev 三处一致
    python scripts/check_config_sync.py --prod     # 额外要求 prod 三处已配置且一致
"""
import argparse
import os
import re
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.dirname(BACKEND)
sys.path.insert(0, BACKEND)

from config import Config  # noqa: E402

MP_CONFIG = os.path.join(PROJECT, 'miniprogram', 'utils', 'config.js')
PC_CONFIG = os.path.join(PROJECT, 'admin-pc', 'src', 'config.js')
PC_ENV_EXAMPLE = os.path.join(PROJECT, 'admin-pc', '.env.example')

# 允许出现裸 IP 的文件白名单（这些文件本身就是配置落点）
HARDCODE_ALLOW = {
    os.path.join(PROJECT, 'miniprogram', 'utils', 'config.js'),
    os.path.join(PROJECT, 'admin-pc', 'src', 'config.js'),
    os.path.join(PROJECT, 'backend', 'config.py'),
    os.path.join(PROJECT, 'backend', 'scripts', 'e2e_check.py'),
    os.path.join(PROJECT, 'backend', 'scripts', 'check_static.py'),
    os.path.join(PROJECT, 'backend', 'scripts', 'check_config_sync.py'),
    os.path.join(PROJECT, 'backend', 'scripts', 'seed_demo.py'),
    os.path.join(PROJECT, 'admin-pc', '.env.example'),
    os.path.join(PROJECT, 'backend', '.env'),
}

PASS, FAIL = [], []


def check(name, cond, extra=''):
    (PASS if cond else FAIL).append(name)
    print(('  [OK]   ' if cond else '  [FAIL] ') + name
          + (('   -> ' + str(extra)[:240]) if not cond and extra else ''))


def read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def strip_js_comments(text):
    """剥离 JS 注释 —— 必须做，否则注释里的示例地址会被当成真实配置。

    注意 `//` 的判定：用负向后顾排除 `:`，避免把 `http://` / `https://` 误当注释。
    """
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'(?<!:)//[^\n]*', '', text)
    return text


def block(text, key):
    """取出 `key: { ... }` 花括号内文本（非嵌套场景足够用）。"""
    m = re.search(re.escape(key) + r'\s*:\s*\{(.*?)\}', text, re.S)
    return m.group(1) if m else ''


def quoted(text, name):
    m = re.search(re.escape(name) + r'\s*:\s*[\'"]([^\'"]*)[\'"]', text)
    return m.group(1) if m else None


def assigned(text, name):
    m = re.search(re.escape(name) + r'\s*=\s*[\'"]([^\'"]*)[\'"]', text)
    return m.group(1) if m else None


def env_value(text, name):
    """解析 .env 风格文件（NAME=value，忽略被 # 注释掉的行）。"""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        m = re.match(re.escape(name) + r'\s*=\s*(.+)$', s)
        if m:
            return m.group(1).strip().strip('\'"')
    return None


def scan_hardcode(root, exts, skip_dirs):
    hits = []
    for r, ds, fs in os.walk(root):
        ds[:] = [d for d in ds if d not in skip_dirs]
        for f in fs:
            if not f.endswith(exts):
                continue
            p = os.path.join(r, f)
            if os.path.abspath(p) in HARDCODE_ALLOW:
                continue
            for i, line in enumerate(read(p).splitlines(), 1):
                if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?', line):
                    hits.append('%s:%d  %s' % (os.path.relpath(p, PROJECT), i, line.strip()[:110]))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prod', action='store_true', help='额外要求 prod（HTTPS）三处已配置且一致')
    args = ap.parse_args()

    print('=' * 74)
    print('  配置一致性校验（API_BASE / STATIC_BASE 全项目单一来源）')
    print('=' * 74)

    be_api, be_static = Config.PUBLIC_API_BASE, Config.PUBLIC_STATIC_BASE

    mp = strip_js_comments(read(MP_CONFIG))
    mp_dev, mp_prod = block(mp, 'dev'), block(mp, 'prod')
    mp_api, mp_static = quoted(mp_dev, 'API_BASE'), quoted(mp_dev, 'STATIC_BASE')
    mp_p_api, mp_p_static = quoted(mp_prod, 'API_BASE'), quoted(mp_prod, 'STATIC_BASE')

    pc = strip_js_comments(read(PC_CONFIG))
    pc_api, pc_static = assigned(pc, 'LAN_API_BASE'), assigned(pc, 'LAN_STATIC_BASE')

    print('\n[1] 三处 dev / 开发地址读取')
    for label, api, static in (('backend/config.py        ', be_api, be_static),
                               ('miniprogram dev 档位     ', mp_api, mp_static),
                               ('admin-pc LAN 兜底        ', pc_api, pc_static)):
        print('    %s API=%-46s STATIC=%s' % (label, api, static))

    print('\n[2] dev 三处一致性')
    check('API_BASE 三处一致（后端 = 小程序 = PC）',
          bool(be_api) and be_api == mp_api == pc_api, '%s | %s | %s' % (be_api, mp_api, pc_api))
    check('STATIC_BASE 三处一致（后端 = 小程序 = PC）',
          bool(be_static) and be_static == mp_static == pc_static,
          '%s | %s | %s' % (be_static, mp_static, pc_static))
    check('STATIC_BASE 以 / 结尾（拼接文件名不会漏斜杠）',
          all(s and s.endswith('/') for s in (be_static, mp_static, pc_static)))
    check('API_BASE 以 /api 结尾',
          all(s and s.endswith('/api') for s in (be_api, mp_api, pc_api)))
    check('dev 档位为 http 局域网地址（与后端默认一致）',
          bool(mp_api) and mp_api.startswith('http://') and bool(pc_api) and pc_api.startswith('http://'))

    print('\n[3] prod 档位（HTTPS）')
    prod_configured = bool(mp_p_api) or bool(mp_p_static)
    if not prod_configured:
        print('    [..]   prod 档位留空 —— 属于「未配置」，未伪造域名，符合预期')
        check('prod 档位不半填（要么两个都空，要么两个都填）',
              not mp_p_api and not mp_p_static, 'API=%r STATIC=%r' % (mp_p_api, mp_p_static))
    else:
        check('prod API_BASE 为 https', mp_p_api.startswith('https://'), mp_p_api)
        check('prod STATIC_BASE 为 https', mp_p_static.startswith('https://'), mp_p_static)
        ex_api = env_value(read(PC_ENV_EXAMPLE), 'VITE_API_BASE') if os.path.exists(PC_ENV_EXAMPLE) else None
        ex_static = env_value(read(PC_ENV_EXAMPLE), 'VITE_STATIC_BASE') if os.path.exists(PC_ENV_EXAMPLE) else None
        if ex_api and 'your-domain' not in ex_api:
            check('prod API_BASE 与 admin-pc/.env.example 一致', ex_api == mp_p_api,
                  '%s | %s' % (ex_api, mp_p_api))
        if ex_static and 'your-domain' not in ex_static:
            check('prod STATIC_BASE 与 admin-pc/.env.example 一致', ex_static == mp_p_static,
                  '%s | %s' % (ex_static, mp_p_static))

    if args.prod:
        check('--prod 模式：prod 档位必须已配置', prod_configured, 'PROFILES.prod 仍为空')
        check('--prod 模式：backend PUBLIC_* 必须已是 https',
              be_api.startswith('https://') and be_static.startswith('https://'),
              '%s | %s' % (be_api, be_static))

    print('\n[4] 硬编码扫描（页面 / api / utils 层不允许出现裸 IP）')
    hits = []
    hits += scan_hardcode(os.path.join(PROJECT, 'miniprogram', 'pages'), ('.vue', '.js'),
                          {'node_modules', 'unpackage'})
    hits += scan_hardcode(os.path.join(PROJECT, 'miniprogram', 'api'), ('.js',), {'node_modules'})
    hits += scan_hardcode(os.path.join(PROJECT, 'miniprogram', 'utils'), ('.js',), {'node_modules'})
    hits += scan_hardcode(os.path.join(PROJECT, 'admin-pc', 'src'), ('.vue', '.js'), {'node_modules'})
    check('无裸 IP 硬编码', not hits, '\n          ' + '\n          '.join(hits[:8]))

    print('\n' + '=' * 74)
    print('  结果：%d 项通过，%d 项失败' % (len(PASS), len(FAIL)))
    for f in FAIL:
        print('   x ' + f)
    print('=' * 74)
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
