#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only OR MIT
"""Host controls for shared Thunderbolt DP clock ownership."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import resource
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]
CASES = ['m2-admission', 'm1-admission', 'm1max-admission', 'm2pro-sequence',
         'm3pro-sequence', 'single-stop', 'stop-first', 'stop-second',
         'rate-change', 'force-stop', 'first-poll-failure', 'lock-failure',
         'first-command-failure', 'second-command-failure', 'busy-pll', 'busy-mode']
NAMES = ['apple_atc_tunnel_is_t600x', 'apple_atc_tunnel_is_t8103_style',
         'atc_tunnel_stop_t8103', 'atc_tunnel_pclk_t8103',
         'atc_tunnel_wake_t8103', 'atc_tunnel_start_t8103',
         'apple_atc_dp_tunnel_rate']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ref')
    parser.add_argument('--out', type=Path)
    parser.add_argument('cases', nargs='*', choices=CASES)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('dp_controls', ROOT / 'tools/asahi/dp-release-tests.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def read(path):
        return subprocess.check_output(['git', 'show', f'{args.ref}:{path}'], cwd=ROOT, text=True) if args.ref else (ROOT / path).read_text()
    source = read('drivers/phy/apple/atc.c')
    bodies = [module.function(source, name) for name in NAMES]
    bodies.insert(0, module.function(read('drivers/phy/apple/atc-tunnel.h'), 'apple_atc_t602x_gate'))
    lines = iter(source.splitlines(keepends=True))
    definitions = []
    for line in lines:
        if line.startswith('#define'):
            definition = line
            while line.rstrip().endswith('\\'):
                line = next(lines)
                definition += line
            definitions.append(definition)
    defines = ''.join(definitions)
    thunderbolt = read('drivers/thunderbolt/apple.c')
    table = re.search(r'static const struct of_device_id apple_dpin_qualified_soc\[\] = \{.*?\n\};', thunderbolt, re.S).group()
    begin = thunderbolt.index('const struct apple_dpin_policy *\napple_dpin_policy_select')
    end = thunderbolt.index('\n}', begin) + 2
    policy = thunderbolt[begin:end]
    bodies.append(policy)

    with tempfile.TemporaryDirectory(prefix='tunnel-clock-') as directory:
        output = args.out or Path(directory)
        output.mkdir(parents=True, exist_ok=True)
        code = (ROOT / 'tools/asahi/tunnel-clock/fixture.c').read_text().replace('/* REGISTER_DEFINES */', defines).replace('/* POLICY_TABLE */', table).replace('/* PRODUCTION_FUNCTIONS */', '\n'.join(bodies))
        (output / 'production.c').write_text(code)
        subprocess.run(['cc', '-std=gnu11', '-g', '-Wall', '-Werror', '-Wno-unused-function', str(output / 'production.c'), '-o', str(output / 'production')], check=True)
        def no_core():
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        results = []
        for case in args.cases or CASES:
            run = subprocess.run([str(output / 'production'), case], capture_output=True, text=True, preexec_fn=no_core)
            results.append({'case': case, 'exit': run.returncode, 'stderr': run.stderr})
        receipt = {'ref': args.ref, 'bodies': {name: hashlib.sha256(body.encode()).hexdigest() for name, body in zip(['apple_atc_t602x_gate'] + NAMES + ['apple_dpin_policy_select'], bodies)}, 'policy_table_sha256': hashlib.sha256(table.encode()).hexdigest(), 'translation_sha256': hashlib.sha256(code.encode()).hexdigest(), 'results': results}
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(results, indent=2))
        if any(result['exit'] for result in results):
            raise SystemExit(1)
if __name__ == '__main__':
    main()
