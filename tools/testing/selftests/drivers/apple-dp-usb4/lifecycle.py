#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Host fault-injection test of the actual tb_dp_activate() implementation.

Extract the function rather than copying it. Stubs model adapter operations;
this does not emulate Apple firmware, AUX transport or the full connection manager.
"""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(os.environ.get('KSRC') or Path(__file__).resolve().parents[5])
source = (root / 'drivers/thunderbolt/tunnel.c').read_text()
start = source.index('static int tb_dp_activate(')
end = source.index('\n}\n', start) + 3
function = source[start:end]
preamble = r'''
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>
#define TB_DP_VIDEO_PATH_OUT 0
#define TB_DP_AUX_PATH_OUT 1
#define TB_DP_AUX_PATH_IN 2
struct tb_nhi;
struct tb_nhi_ops { int (*dp_tunnel_set)(struct tb_nhi *, unsigned int, bool); };
struct tb_nhi { const struct tb_nhi_ops *ops; };
struct tb { struct tb_nhi *nhi; };
struct tb_switch { int route; };
struct tb_port { struct tb_switch *sw; unsigned int port; bool out, enabled; };
struct hop { int in_hop_index, next_hop_index; };
struct tb_path { int path_length; struct hop hops[1]; };
struct tb_tunnel { struct tb *tb; struct tb_port *src_port, *dst_port;
                   struct tb_path **paths; bool dp_source_connected; };
static int calls_on, calls_off, polls, fail_source, fail_port, warnings;
static struct tb_port *src, *dst;
static int tb_route(struct tb_switch *s) { return s->route; }
static bool tb_port_is_dpout(struct tb_port *p) { return p->out; }
static void tb_dp_port_set_hops(struct tb_port *p, int a, int b, int c)
{ (void)p; (void)a; (void)b; (void)c; }
static void tb_dp_dprx_stop(struct tb_tunnel *t) { (void)t; }
static void tb_dp_port_hpd_clear(struct tb_port *p) { (void)p; }
static int tb_dp_port_enable(struct tb_port *p, bool on)
{
 if (on && fail_port == (int)p->port) return -EIO;
 p->enabled = on; return 0;
}
static int tb_dp_dprx_start(struct tb_tunnel *t)
{ (void)t; polls++; return -EINPROGRESS; }
#define tb_tunnel_warn(...) ((void)warnings++)
static int notify(struct tb_nhi *n, unsigned int port, bool on)
{
 (void)n; assert(port == src->port);
 /* Both adapters must still be enabled on connect AND on release. */
 assert(src->enabled && dst->enabled);
 if (on) calls_on++; else calls_off++;
 return fail_source;
}
'''
main = r'''
int main(void)
{
 struct tb_nhi_ops ops = { notify };
 struct tb_nhi nhi = { &ops };
 struct tb tb = { &nhi };
 struct tb_switch host = { 0 };
 struct tb_port in = { &host, 5, false, false }, out = { &host, 13, true, false };
 struct tb_path path = { 1, {{ 8, 9 }} };
 struct tb_path *paths[] = { &path, &path, &path };
 struct tb_tunnel t = { &tb, &in, &out, paths, false };
 src = &in; dst = &out;
 /* Normal asynchronous start and idempotent teardown. */
 assert(tb_dp_activate(&t, true) == -EINPROGRESS);
 assert(calls_on == 1 && polls == 1 && t.dp_source_connected);
 assert(tb_dp_activate(&t, false) == 0);
 assert(calls_off == 1 && !t.dp_source_connected && !in.enabled && !out.enabled);
 assert(tb_dp_activate(&t, false) == 0 && calls_off == 1);
 /* An adapter failure must not acquire a source or start DPRX. */
 fail_port = 13;
 assert(tb_dp_activate(&t, true) == -EIO);
 assert(calls_on == 1 && polls == 1);
 assert(tb_dp_activate(&t, false) == 0 && calls_off == 1);
 fail_port = 0;
 /* Failed source acquisition is not owned by this tunnel. */
 fail_source = -EBUSY;
 assert(tb_dp_activate(&t, true) == -EBUSY);
 assert(!t.dp_source_connected && polls == 1);
 assert(tb_dp_activate(&t, false) == 0 && calls_off == 1);
 fail_source = 0;
 /* Failed release warns, still tears down transport, and is not repeated. */
 assert(tb_dp_activate(&t, true) == -EINPROGRESS);
 fail_source = -ETIMEDOUT;
 assert(tb_dp_activate(&t, false) == 0 && warnings == 1);
 assert(!t.dp_source_connected && !in.enabled && !out.enabled);
 assert(tb_dp_activate(&t, false) == 0 && calls_off == 2);
 fail_source = 0;
 /* Remote sources and drivers without a hook retain generic behavior. */
 host.route = 1;
 int saved = calls_on;
 assert(tb_dp_activate(&t, true) == -EINPROGRESS && calls_on == saved);
 assert(tb_dp_activate(&t, false) == 0);
 host.route = 0; nhi.ops = NULL;
 assert(tb_dp_activate(&t, true) == -EINPROGRESS && calls_on == saved);
 assert(tb_dp_activate(&t, false) == 0);
 puts("PASS: source ordering, adapter/acquisition/release failures, repeated teardown, optional/remote sources");
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='apple-usb4-test-') as tmp:
    srcfile = Path(tmp) / 'test.c'
    executable = Path(tmp) / 'test'
    srcfile.write_text(preamble + function + main)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=undefined,address', str(srcfile), '-o', str(executable)], check=True)
    # The kselftest runner wraps tests in stdbuf (LD_PRELOAD); ASan must come first.
    subprocess.run([str(executable)], check=True,
                   env={k: v for k, v in os.environ.items() if k != 'LD_PRELOAD'})
