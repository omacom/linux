#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Native first-link/retrain/stop ordering against actual callback C functions.

Expected transitions come from the macOS 13.5 host implementation and a
native capture of a working TS4 link. Hardware operations are fault-injected mocks;
this cannot establish electrical or firmware video delivery.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(os.environ.get('KSRC') or Path(__file__).resolve().parents[5])
source = (root / 'drivers/gpu/drm/apple/dptxep.c').read_text()


def function(name):
    match = re.search(r'static int\s+' + name + r'\(', source)
    assert match, name
    end = source.index('\n}', match.start()) + 2
    return source[match.start():end]


code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
typedef uint8_t u8;
typedef uint32_t __le32;
#define cpu_to_le32(x) (x)
#define le32_to_cpu(x) (x)
#define dev_err(...) ((void)0)
#define trace_dptxport_call_set_link_rate(...) ((void)0)
enum { LINK_RATE_RBR=6, LINK_RATE_HBR=10, LINK_RATE_HBR2=20, LINK_RATE_HBR3=30 };
union phy_configure_opts {
 struct { unsigned link_rate; bool set_rate, set_lanes, set_voltages; } dp;
};
struct dptx_port {
 union phy_configure_opts phy_ops;
 void *atcphy;
 u32 link_rate, pending_link_rate;
};
struct apple_dcp_typec_route { void *dpin_bridge[2], *dpin_xbar[2]; unsigned dpin; };
struct apple_dcp { unsigned dptx_core; void *dev; struct apple_dcp_typec_route *active_typec_route; };
struct endpoint { struct apple_dcp *dcp; };
struct apple_epic_service { void *cookie; struct endpoint *ep; };
enum { BRIDGE_OFF=1, BRIDGE_ON, CROSSBAR_OFF, CROSSBAR_ON, RATE, LEGACY_DELAY };
static unsigned events[32], count, fail_at;
static int record(unsigned event)
{ assert(count<32); events[count++]=event; return count==fail_at ? -EIO:0; }
static int apple_dpin_set_active(void *p, bool on)
{ assert(p==(void *)1); return record(on ? BRIDGE_ON:BRIDGE_OFF); }
static int apple_dpxbar_set_active(void *p, bool on)
{ assert(p==(void *)2); return record(on ? CROSSBAR_ON:CROSSBAR_OFF); }
static int phy_configure(void *p, union phy_configure_opts *o)
{ assert(p==(void *)3 && o->dp.set_rate); return record(RATE); }
static void mdelay(unsigned n) { assert(n==10); record(LEGACY_DELAY); }
static void expect(const unsigned *e, unsigned n)
{ assert(count==n && !memcmp(events,e,n*sizeof(*e))); count=0; }
'''
start = source.index('struct dptxport_apcall_link_rate {')
code += source[start:source.index('\n}', start) + 2] + ';\n'
for name in ['dptxport_call_will_change_link_config',
             'dptxport_call_did_change_link_config', 'dptxport_call_set_link_rate']:
    code += function(name) + '\n'
code += r'''
static int set_rate(struct apple_epic_service *s, unsigned rate)
{
 struct dptxport_apcall_link_rate req={.link_rate=rate}, reply={0};
 int r=dptxport_call_set_link_rate(s,&req,sizeof(req),&reply,sizeof(reply));
 if (!r) assert(reply.retcode==0 && reply.link_rate==rate);
 return r;
}
int main(void)
{
 struct apple_dcp_typec_route route={.dpin_bridge={(void *)1},.dpin_xbar={(void *)2}};
 struct apple_dcp dcp={.dptx_core=1,.active_typec_route=&route};
 struct endpoint ep={&dcp};
 struct dptx_port port={.atcphy=(void *)3};
 struct apple_epic_service service={&port,&ep};
 const unsigned up[]={RATE,CROSSBAR_ON,BRIDGE_ON};
 const unsigned down[]={BRIDGE_OFF,CROSSBAR_OFF,BRIDGE_ON};
 /* First-link WillChange must not pulse DPIN inactive before its first rate. */
 assert(!dptxport_call_will_change_link_config(&service) && !count);
 assert(!set_rate(&service,30));
 assert(!dptxport_call_did_change_link_config(&service)); expect(up,3);
 /* Retraining retains native inactive -> crossbar down -> AUX active order. */
 assert(!dptxport_call_will_change_link_config(&service)); expect(down,3);
 assert(!set_rate(&service,20));
 assert(!dptxport_call_did_change_link_config(&service)); expect(up,3);
 /* Disconnect: zero-rate DidChange cannot re-enable a clockless crossbar. */
 assert(!dptxport_call_will_change_link_config(&service)); expect(down,3);
 assert(!set_rate(&service,0));
 assert(!dptxport_call_did_change_link_config(&service));
 const unsigned off[]={RATE}; expect(off,1);
 assert(!port.link_rate && !port.pending_link_rate);
 assert(!dptxport_call_will_change_link_config(&service) && !count);
 /* A failed clock operation must not replace the last successful rate. */
 assert(!set_rate(&service,30)); count=0; fail_at=1;
 assert(set_rate(&service,0)==-EIO && port.link_rate==30);
 count=0; fail_at=0;
 for (unsigned step=1; step<=3; step++) {
  fail_at=step;
  assert(dptxport_call_will_change_link_config(&service)==-EIO);
  assert(count==step); count=0;
 }
 fail_at=1;
 assert(dptxport_call_did_change_link_config(&service)==-EIO && count==1); count=0;
 fail_at=2;
 assert(dptxport_call_did_change_link_config(&service)==-EIO);
 const unsigned rollback[]={CROSSBAR_ON,BRIDGE_ON,CROSSBAR_OFF}; expect(rollback,3);
 fail_at=0;
 /* Native DP (non-tunnel) keeps its original link-change behavior. */
 dcp.dptx_core=0;
 assert(!dptxport_call_will_change_link_config(&service) && !count);
 assert(!dptxport_call_did_change_link_config(&service));
 const unsigned delay[]={LEGACY_DELAY}; expect(delay,1);
 puts("PASS: native initial link, retrain, zero-rate shutdown, clock errors, rollback, native-DP behavior");
}
'''
with tempfile.TemporaryDirectory(prefix='apple-link-config-') as tmp:
    src, exe = Path(tmp) / 'test.c', Path(tmp) / 'test'
    src.write_text(code)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=undefined', str(src), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
