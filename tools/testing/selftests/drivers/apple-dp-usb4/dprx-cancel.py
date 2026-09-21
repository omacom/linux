#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the actual DPRX poll cancel path with a mocked workqueue.

Regression for the Thunderbolt domain reference leak: when a DP tunnel is
torn down while its DPRX capabilities poll is still pending, the completion
callback never runs, so the cancel hook must release the callback data.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(os.environ.get('KSRC') or Path(__file__).resolve().parents[5])
tunnel = (root / 'drivers/thunderbolt/tunnel.c').read_text()
tb = (root / 'drivers/thunderbolt/tb.c').read_text()


def function(source, name):
    """Return the definition of static function @name (not a mention in a comment)."""
    match = re.search(r'(?m)^static [^\n]*\b' + re.escape(name) + r'\(', source)
    assert match, name
    start = match.start()
    end = source.index('\n}', start) + 2
    return source[start:end]


one_dp = function(tb, 'tb_tunnel_one_dp')
assert 'tb_domain_get(tb));' in one_dp, 'DP tunnel callback data must be a domain reference'
alloc = one_dp.index('tb_tunnel_alloc_dp(')
assert one_dp.index('tunnel->callback_cancel = tb_dp_tunnel_cancel;') > alloc, \
    'cancel hook must be registered right after allocation'

code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
struct tb { int index; int refs; };
struct tb_tunnel {
 bool dprx_started, dprx_canceled;
 int dprx_work;
 void (*callback)(struct tb_tunnel *, void *);
 void *callback_data;
 void (*callback_cancel)(struct tb_tunnel *, void *);
 int refs;
};
static bool cancel_result;
static int cancel_calls, tunnel_puts, domain_puts, dbg_calls;
static bool cancel_delayed_work(int *work) { (void)work; cancel_calls++; return cancel_result; }
static void tb_tunnel_put(struct tb_tunnel *t) { t->refs--; tunnel_puts++; }
static void tb_domain_put(struct tb *tb) { tb->refs--; domain_puts++; }
#define tb_tunnel_dbg(t, ...) do { (void)(t); dbg_calls++; } while (0)
'''
code += function(tunnel, 'tb_dp_dprx_stop') + '\n'
code += function(tb, 'tb_dp_tunnel_cancel') + r'''
static void reset(struct tb *tb, struct tb_tunnel *t)
{
 tb->refs = 1; t->refs = 1; t->dprx_started = true; t->dprx_canceled = false;
 t->callback_data = tb; t->callback_cancel = tb_dp_tunnel_cancel;
 cancel_calls = tunnel_puts = domain_puts = dbg_calls = 0;
}
int main(void)
{
 struct tb tb = {0};
 struct tb_tunnel t = {0};
 /* Pending poll cancelled: the callback never runs, so the domain reference is dropped here. */
 reset(&tb, &t); cancel_result = true;
 tb_dp_dprx_stop(&t);
 assert(!t.dprx_started && t.dprx_canceled && cancel_calls == 1);
 assert(domain_puts == 1 && tb.refs == 0 && tunnel_puts == 1 && t.refs == 0 && dbg_calls == 1);
 /* Poll already running: the work itself calls the callback and puts the tunnel; nothing here. */
 reset(&tb, &t); cancel_result = false;
 tb_dp_dprx_stop(&t);
 assert(!t.dprx_started && t.dprx_canceled && cancel_calls == 1);
 assert(domain_puts == 0 && tb.refs == 1 && tunnel_puts == 0 && t.refs == 1);
 /* Not started: nothing to cancel. */
 reset(&tb, &t); t.dprx_started = false; cancel_result = true;
 tb_dp_dprx_stop(&t);
 assert(cancel_calls == 0 && domain_puts == 0 && tunnel_puts == 0 && !t.dprx_canceled);
 /* No cancel hook registered (other tunnel types): only the tunnel reference is dropped. */
 reset(&tb, &t); t.callback_cancel = NULL; cancel_result = true;
 tb_dp_dprx_stop(&t);
 assert(domain_puts == 0 && tunnel_puts == 1 && t.refs == 0);
 puts("dprx-cancel: 4 cases pass");
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp) / 'test.c'
    src.write_text(code)
    exe = Path(tmp) / 'test'
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Werror', '-fsanitize=undefined',
                    '-o', str(exe), str(src)], check=True)
    subprocess.run([str(exe)], check=True)
