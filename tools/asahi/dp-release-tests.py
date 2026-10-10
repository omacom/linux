#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only OR MIT
"""Host controls for Type-C display release and port reconfiguration."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FUNCTIONS = {
    'drivers/gpu/drm/apple/dcp.c': [
        'dcp_dptx_release_locked', 'dcp_dptx_disconnect',
        'dcp_dptx_disconnect_drained', 'dcp_dptx_disconnect_oob',
        'dcp_dptx_connect_tile', 'dcp_dptx_connect',
        'dcp_dptx_park', 'dcp_external_retry_work', 'dcp_external_sink_irq'],
    'drivers/gpu/drm/apple/dcp-fabric.c': [
        'dcp_tb_split_teardown_locked', 'dcp_tb_split_join_locked',
        'dcp_tb_split_locked', 'dcp_tb_release_locked', 'dcp_tunnel_set_rate',
        'dcp_typec_route_activate', 'dcp_typec_route_deactivate',
        'dcp_rebalance_deactivate', 'dcp_follow_release', 'dcp_follow_owned',
        'dcp_follow_retained', 'dcp_follow_detach',
        'dcp_follow_activate', 'dcp_follow_attach',
        'dcp_reclaim_release', 'dcp_reclaim_retained',
        'dcp_fabric_hdmi_retry', 'dcp_typec_route_is_dp', 'dcp_typec_route_set',
        'dcp_typec_route_unregister'],
    'drivers/gpu/drm/apple/dptxep.c': ['dptxport_call_set_tiled_display_hint'],
    'drivers/gpu/drm/apple/dcp-fabric-session.h': ['dcp_fabric_binding_request', 'dcp_fabric_callback_valid'],
    'drivers/gpu/drm/apple/dcp-fabric-core.c': ['dcp_fabric_follow_execute'],
    'drivers/gpu/drm/apple/dcp-fabric-effects.h': ['dcp_fabric_reclaim_execute'],
    'drivers/usb/typec/tipd/core.c': [
        'cd321x_dp_hpd', 'cd321x_dp_release_first',
        'cd321x_retry_revalidation', 'cd321x_update_work'],
}
CASES = ['release-success', 'release-failure', 'hpd-failure',
         'release-repeat', 'invalid-cache-repeat', 'replug',
         'safe-release-failure', 'safe-release-success',
         'owner-route', 'cached-update', 'tunnel', 'legacy-controller',
         'no-route', 'remove-release-failure', 'remove-hpd-failure',
         'remove-secondary', 'remove-tunnel', 'remove-crossbar-failure',
         'retry-exhaustion', 'suspended', 'legacy-dcp',
         'activate-release-failure', 'activate-success',
         'rebalance-hpd-failure', 'rebalance-release-failure', 'rebalance-success',
         'follow-hpd-failure', 'follow-release-failure', 'follow-success',
         'hdmi-release-failure', 'hdmi-success',
         'native-retry-hpd-failure', 'native-retry-release-failure',
         'native-retry-success', 'sink-irq-release-failure', 'sink-irq-success',
         'reclaim-retained', 'reclaim-released-error', 'reclaim-success',
         'follow-executor-retained', 'follow-executor-second-retained',
         'follow-executor-destination-retained', 'follow-executor-null-callback',
         'follow-restore-occupied', 'follow-executor-reverse-restore',
         'reclaim-null-retained', 'reclaim-null-released-error',
         'tile-hint-valid', 'tile-hint-short', 'tile-hint-location',
         'tile-hint-many', 'tile-hint-overflow', 'tile-hint-zero-size',
         'tile-hint-single', 'tile-rate-stop', 'tile-rate-error',
         'tile-teardown-hpd-failure', 'tile-teardown-release-failure',
         'tile-teardown-remove-hpd', 'tile-teardown-remove-release',
         'tile-teardown-success', 'tile-park-hpd-failure',
         'tile-park-release-failure', 'tile-park-success',
         'tile-split-connect-failure', 'tile-split-unsupported-connect',
         'tile-split-source-failure', 'tile-split-preselect-failure',
         'tile-split-no-hint', 'tile-split-wait-hint', 'tile-split-success',
         'tile-follow-source-failure', 'tile-follow-preselect-failure',
         'tile-follow-main-release-failure', 'tile-follow-success',
         'tile-split-retained-connect-failure', 'tile-parent-connect-failure',
         'tile-parent-connect-success', 'tile-main-release-hpd-failure',
         'tile-main-release-failure', 'tile-main-release-success']


def function(source, name):
    match = re.search(r'^(?:static\s+)?(?:inline\s+)?(?:int|void|bool)\s+' + name +
                      r'\([^;]*?\)\n\{', source, re.M | re.S)
    if not match:
        raise ValueError(name)
    pos = source.index('{', match.start()) + 1
    level = 1
    while level:
        level += (source[pos] == '{') - (source[pos] == '}')
        pos += 1
    return source[match.start():pos] + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ref')
    parser.add_argument('--out', type=Path)
    parser.add_argument('cases', nargs='*', choices=CASES)
    args = parser.parse_args()
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dp-release-') as directory:
        output = args.out or Path(directory)
        bodies, hashes, additions = [], {}, []
        for path, names in sorted(FUNCTIONS.items(), key=lambda item: item[0] != 'drivers/gpu/drm/apple/dcp-fabric-session.h'):
            source = (subprocess.check_output(['git', 'show', f'{args.ref}:{path}'],
                       cwd=ROOT, text=True) if args.ref else (ROOT / path).read_text())
            for name in names:
                try:
                    body = function(source, name)
                except ValueError:
                    if not args.ref or name not in ('dcp_follow_owned', 'dcp_follow_retained', 'dcp_reclaim_retained', 'dcp_tb_split_teardown_locked', 'dcp_tb_split_join_locked', 'dcp_tb_split_locked', 'dcp_tb_release_locked', 'dcp_tunnel_set_rate', 'dptxport_call_set_tiled_display_hint'):
                        raise
                    body = function((ROOT / path).read_text(), name)
                    additions.append(name)
                if name == 'dcp_dptx_connect_tile' and body.startswith('static void'):
                    body = body.replace('static void', 'static int', 1).replace('\t\treturn;', '\t\treturn 0;')
                    body = body.rstrip()[:-1] + '\treturn ret;\n}\n'
                    additions.append('tile_connect_return_adapter')
                if name == 'dcp_tb_split_teardown_locked'  and body.startswith('static void'):
                    body = body.replace('static void', 'static int', 1).replace(
                        'struct apple_dcp_typec_port *port)',
                        'struct apple_dcp_typec_port *port, bool force)')
                    body = body.replace('\t\treturn;', '\t\treturn 0;')
                    body = body.rstrip()[:-1] + '\treturn 0;\n}\n'
                    additions.append('teardown_return_adapter')
                if 'teardown_return_adapter' in additions:
                    body = re.sub(r'dcp_tb_split_teardown_locked\((port|route->port)\);',
                                  r'dcp_tb_split_teardown_locked(\1, false);', body)
                bodies.append(body)
                hashes[name] = hashlib.sha256(body.encode()).hexdigest()
        header = (subprocess.check_output(['git', 'show',
                  f'{args.ref}:drivers/usb/typec/tipd/cd321x-pm.h'], cwd=ROOT,
                  text=True) if args.ref else
                  (ROOT / 'drivers/usb/typec/tipd/cd321x-pm.h').read_text())
        header = header.replace('#include <linux/types.h>', '')
        fixture = (ROOT / 'tools/asahi/dp-release/fixture.c').read_text()
        code = fixture.replace('/* PM_HEADER */', header).replace(
            '/* PRODUCTION_FUNCTIONS */', '\n'.join(bodies))
        unit = output / 'production.c'
        unit.write_text(code)
        subprocess.run(['cc', '-std=gnu11', '-g', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', '-Wno-unused-function',
                        '-Wno-unused-variable', '-Wno-missing-field-initializers',
                        str(unit), '-o', str(output / 'production')], check=True)
        def no_core():
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        results = []
        for case in args.cases or CASES:
            run = subprocess.run([str(output / 'production'), case],
                                 capture_output=True, text=True, preexec_fn=no_core)
            results.append({'case': case, 'exit': run.returncode,
                            'stdout': run.stdout, 'stderr': run.stderr})
        receipt = {'ref': args.ref, 'bodies': hashes,
                   'shared_ownership_queries': additions,
                   'translation_sha256': hashlib.sha256(code.encode()).hexdigest(),
                   'results': results}
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(results, indent=2))
        if any(result['exit'] for result in results):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
