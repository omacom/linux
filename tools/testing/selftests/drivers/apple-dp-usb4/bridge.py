#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise actual DPIN/ATC functions with mocked MMIO and native event order.

No firmware, AUX link, scheduler, real interrupts or electrical timing is
emulated here.
The ACK/PLL models are explicit assumptions, independently fault-injected.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(os.environ.get('KSRC') or Path(__file__).resolve().parents[5])
here = Path(__file__).resolve().parent
args = argparse.ArgumentParser()
args.add_argument('--no-sanitizers', action='store_true')
args = args.parse_args()
fixture = json.loads((here / 'native-events.json').read_text())
dp = (root / 'drivers/gpu/drm/apple/dpin.c').read_text()
atc = (root / 'drivers/phy/apple/atc.c').read_text()

def function(source, name):
    match = re.search(r'(?m)^(?:static )?(?:inline )?(?:int|void|bool|irqreturn_t)\s+' + name + r'\(', source)
    assert match, name
    start = match.start()
    end = source.index('\n}\n', start) + 3
    return source[start:end]

preamble = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
typedef uint32_t u32;
typedef uint16_t u16;
typedef uint8_t u8;
#define __iomem
#define BIT(n) (1U << (n))
#define GENMASK(h,l) ((~0U >> (31-(h))) & (~0U << (l)))
#define FIELD_PREP(mask,val) (((u32)(val) << __builtin_ctz(mask)) & (mask))
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,y) ((x) = (y))
#define dev_info(d,...) ((void)(d))
#define dev_err(d,...) ((void)(d))
#define dev_err_ratelimited(d,...) ((void)(d))
#define dev_warn_ratelimited(d,...) ((void)(d))
struct device { int dummy; };
struct mutex { bool locked; };
static void mutex_lock(struct mutex *m) { assert(!m->locked); m->locked = true; }
static void mutex_unlock(struct mutex *m) { assert(m->locked); m->locked = false; }
struct auto_lock { struct mutex *m; };
static struct auto_lock take_guard(struct mutex *m) { mutex_lock(m); return (struct auto_lock){m}; }
static void drop_guard(struct auto_lock *a) { mutex_unlock(a->m); }
#define guard(x) struct auto_lock _guard __attribute__((cleanup(drop_guard))) = take_guard
#define lockdep_assert_held(m) assert((m)->locked)
typedef int irqreturn_t;
#define IRQ_NONE 0
#define IRQ_HANDLED 1
static unsigned long jiffies;
#define msecs_to_jiffies(ms) (ms)
#define time_after_eq(a,b) ((long)((a)-(b)) >= 0)
static u32 dpregs[8], atcregs[0x8000/4];
static unsigned writes, pm_refs, pm_fail, irq_on, notifications, pulses;
static unsigned ack_at, drop_hpd_at, unstable, sleeps, apb_calls, apb_fail_at;
static unsigned commands[8];
static bool ack_follows;
static bool clock_address(unsigned off)
{
 switch (off) {
 case 0x8: case 0x1b0: case 0x7000: case 0x2080: case 0x2084:
 case 0x2088: case 0x2224: case 0x2208: case 0x2220: case 0x2214:
 case 0x2200: return true;
 default: return false;
 }
}
static u32 readl(const void *p)
{
 if (p == &dpregs[1] && unstable) return ++unstable;
 return *(const u32 *)p;
}
static void writel(u32 value, void *p)
{
 uintptr_t a = (uintptr_t)p;
 writes++;
 if (a >= (uintptr_t)dpregs && a < (uintptr_t)(dpregs+8)) {
  unsigned off = (a-(uintptr_t)dpregs)/4;
  assert(off == 0 || off == 1 || off == 2 || off == 3);
  if (off == 0) dpregs[0] &= ~(value & 3); /* W1C events, level unchanged */
  else if (off == 1) dpregs[1] &= ~value;
  else dpregs[off] = value;
  if (off == 3 && ack_follows && !ack_at) dpregs[4] = (dpregs[4]&~1U)|(value&1);
 } else {
  assert(a >= (uintptr_t)atcregs && a < (uintptr_t)(atcregs+0x8000/4));
  assert(clock_address(a-(uintptr_t)atcregs)); /* Never physical lanes/AUX/CIO */
  *(u32 *)p = value;
 }
}
static void usleep_range(unsigned min, unsigned max)
{
 (void)max; jiffies += min/1000; sleeps++;
 if (ack_follows && ack_at && jiffies >= ack_at) dpregs[4]=(dpregs[4]&~1U)|(dpregs[3]&1);
 if (drop_hpd_at && jiffies >= drop_hpd_at) dpregs[0] &= ~4U;
}
static void udelay(unsigned us) { (void)us; }
static int pm_runtime_resume_and_get(struct device *d)
{ (void)d; if (pm_fail) return -EIO; pm_refs++; return 0; }
static int pm_runtime_put_sync(struct device *d)
{ (void)d; assert(pm_refs); pm_refs--; return 0; }
static void enable_irq(int irq) { (void)irq; assert(!irq_on); irq_on=1; }
static void disable_irq(int irq) { (void)irq; assert(irq_on); irq_on=0; }
static void notify(void *cookie, bool pulse)
{ assert(cookie == dpregs); notifications++; pulses += pulse; }
#define readl_poll_timeout(addr,reg,cond,delay,timeout) \
 ({ int _ret = -ETIMEDOUT; for (unsigned _n=0; _n<4; _n++) { \
 (reg)=readl(addr); if (cond) { _ret=0; break; } } _ret; })
'''
# Import the actual register definitions and actual small driver state structures.
dpdefs = dp[dp.index('#define DPIN_HPD'):dp.index('static void dpin_mask')]
atcdefs = '\n'.join(l for l in atc.splitlines() if l.startswith('#define ') and not l.endswith('\\'))
enums = atc[atc.index('enum atcphy_generation {'):atc.index('/**', atc.index('enum atcphy_generation {'))]
cfgstart = atc.index('struct atcphy_dp_link_rate_configuration {')
cfg = atc[cfgstart:atc.index('\n};', cfgstart)+3]
state = r'''
enum atcphy_mode { APPLE_ATCPHY_MODE_OFF, APPLE_ATCPHY_MODE_USB4 };
enum phy_mode { PHY_MODE_INVALID, PHY_MODE_DP };
#define APPLE_ATCPHY_DP_TUNNEL 1
struct apple_atcphy {
 struct device *dev;
 struct mutex lock;
 enum atcphy_mode mode;
 bool dp_tunnel, dp_tunnel_pll, dp_tunnel_open;
 struct { void *core; } regs;
 struct { enum atcphy_generation gen; } *hw;
};
struct phy { struct apple_atcphy *data; };
struct phy_configure_opts_dp { unsigned link_rate; bool set_rate, set_lanes, set_voltages; };
union phy_configure_opts { struct phy_configure_opts_dp dp; };
static struct apple_atcphy *phy_get_drvdata(struct phy *p) { return p->data; }
static int atcphy_dp_configure(struct apple_atcphy *a, enum atcphy_dp_link_rate lr)
{ (void)a; (void)lr; return -EOPNOTSUPP; }
static void core_mask32(struct apple_atcphy *a, u32 off, u32 mask, u32 set)
{ void *p = (char *)a->regs.core+off; writel((readl(p)&~mask)|set,p); }
static void core_set32(struct apple_atcphy *a, u32 off, u32 set)
{ core_mask32(a,off,0,set); }
static void core_clear32(struct apple_atcphy *a, u32 off, u32 mask)
{ core_mask32(a,off,mask,0); }
static int atcphy_auspll_apb_command(struct apple_atcphy *a, unsigned cmd)
{ (void)a; assert(apb_calls<8); commands[apb_calls++]=cmd; return apb_fail_at==apb_calls ? -EIO:0; }
'''
funcs = ''.join(function(dp, n) for n in ['dpin_mask','apple_dpin_irq','apple_dpin_hpd',
    'apple_dpin_begin','__apple_dpin_set_active','apple_dpin_set_active',
    'apple_dpin_end'])
funcs += ''.join(function(atc,n) for n in ['atcphy_dp_program_pll',
    'atcphy_dp_tunnel_open','atcphy_dp_tunnel_configure',
    'atcphy_dp_tunnel_unconfigure','atcphy_dpphy_set_mode','atcphy_dpphy_configure'])
main = r'''
static int rate(struct apple_atcphy *a, unsigned wire)
{
 enum atcphy_dp_link_rate lr;
 switch(wire) { case 6: lr=ATCPHY_DP_LINK_RATE_RBR; break;
 case 10: lr=ATCPHY_DP_LINK_RATE_HBR; break; case 20: lr=ATCPHY_DP_LINK_RATE_HBR2; break;
 case 30: lr=ATCPHY_DP_LINK_RATE_HBR3; break; default: assert(false); }
 mutex_lock(&a->lock); int r=atcphy_dp_tunnel_configure(a,lr); mutex_unlock(&a->lock); return r;
}
int main(void)
{
 struct device dev={0};
 struct apple_dpin d={.dev=&dev,.regs=dpregs,.irq=1};
 struct apple_atcphy a={.dev=&dev,.mode=APPLE_ATCPHY_MODE_USB4,.regs={atcregs}};
 typeof(*a.hw) hw={.gen=ATCPHY_GENERATION_T8103}; a.hw=&hw;
 struct phy phy={&a};
 ack_follows=true;
 dpregs[3]=dpregs[4]=0x81; /* unrelated control/status bits survive */
 dpregs[2]=0x80;
 atcregs[0xa74/4]=1; atcregs[0x7044/4]=8;
 assert(apple_dpin_set_active(&d,true)==-ENOLINK && writes==0);
 pm_fail=1; assert(apple_dpin_begin(&d,notify,dpregs)==-EIO && !pm_refs && !irq_on);
 pm_fail=0;
 assert(apple_dpin_begin(&d,notify,dpregs)==0 && pm_refs==1 && irq_on);
 assert(apple_dpin_begin(&d,notify,dpregs)==-EBUSY && pm_refs==1);
 assert(dpregs[2]==0x83 && !apple_dpin_hpd(&d));
 assert(atcphy_dpphy_set_mode(&phy,PHY_MODE_DP,1)==0);
 assert(atcphy_dpphy_set_mode(&phy,PHY_MODE_DP,1)==-EBUSY);
'''
for event in fixture['events']:
    if event[0] == 'hpd':
        level, pulse = event[1:]
        main += f' dpregs[0]={4*level + (0 if pulse else 1 if level else 2)}; dpregs[1]={2 if pulse else 1}; assert(apple_dpin_irq(1,&d)==IRQ_HANDLED); assert(apple_dpin_hpd(&d)=={level});\n'
    elif event[0] == 'active':
        main += f' assert(apple_dpin_set_active(&d,{int(event[1])})==0); assert((dpregs[3]&1)=={int(not event[1])});\n'
    else:
        wire=event[1]
        main += f' assert(rate(&a,{wire})==0); assert(((atcregs[0x7000/4]>>4)&7)=={dict(zip([6,10,20,30],[4,3,1,0]))[wire]});\n'
main += r'''
 assert(notifications==2 && pulses==1);
 assert(apb_calls==2 && commands[0]==0 && commands[1]==0x2000);
 assert(atcregs[0x2080/4]==0x1e0e021c && atcregs[0x2084/4]==0);
 assert((atcregs[0x2088/4]&0x7fffff)==0x654a00);
 assert(((atcregs[0x2208/4]>>16)&31)==1);
 assert((atcregs[0x2200/4]&0x54)==0x54);
 /* All supported rates change only the PCLK divider after PLL setup. */
 assert(rate(&a,6)==0 && rate(&a,10)==0 && apb_calls==2);
 /* Native SetLinkRate(0) gates DP outputs and sends APB command 3 while
  * retaining the tunnel lease. A later rate must reinitialize the PLL. */
 union phy_configure_opts zero={.dp={.set_rate=true,.link_rate=0}};
 atcregs[0x2200/4] |= 0x80000000U;
 assert(!atcphy_dpphy_configure(&phy,&zero));
 assert(a.dp_tunnel && !a.dp_tunnel_pll && !a.dp_tunnel_open);
 assert(atcregs[0x2200/4]==0x80000000U && commands[2]==3 && apb_calls==3);
 unsigned stopped_writes=writes;
 assert(!atcphy_dpphy_configure(&phy,&zero) && writes==stopped_writes && apb_calls==3);
 assert(!rate(&a,30) && a.dp_tunnel_pll && a.dp_tunnel_open && apb_calls==5);
 assert(commands[3]==0 && commands[4]==0x2000);
 apb_fail_at=6;
 assert(atcphy_dpphy_configure(&phy,&zero)==-EIO && a.dp_tunnel && a.dp_tunnel_pll);
 apb_fail_at=0;
 assert(!atcphy_dpphy_configure(&phy,&zero) && !a.dp_tunnel_pll && apb_calls==7);
 apb_calls=0;
 assert(!rate(&a,30));
 /* Real low HPD rejects activation, not a synthetic plug. */
 dpregs[0]=0; unsigned prior=writes;
 assert(apple_dpin_set_active(&d,true)==-ENOLINK && writes==prior);
 /* ACK does not arrive: deadline, retained lease, IRQ and power. */
 ack_follows=false; dpregs[4]=0x80; jiffies=0;
 assert(apple_dpin_end(&d)==-ETIMEDOUT && d.leased && pm_refs==1 && irq_on);
 assert(jiffies==1000 && sleeps==1000);
 ack_follows=true;
 assert(apple_dpin_end(&d)==0 && !d.leased && !pm_refs && !irq_on && dpregs[2]==0x80);
 prior=writes; assert(apple_dpin_end(&d)==0 && writes==prior);
 assert(atcphy_dpphy_set_mode(&phy,PHY_MODE_DP,0)==0 && !(atcregs[0x2200/4]&0x54));
 assert(commands[2]==3);
 /* Physical detach while activation waits must terminate promptly. */
 assert(apple_dpin_begin(&d,notify,dpregs)==0);
 dpregs[0]=4; dpregs[4]=0x81; ack_follows=false; jiffies=0; drop_hpd_at=3;
 assert(apple_dpin_set_active(&d,true)==-ENOLINK && jiffies==3);
 drop_hpd_at=0; ack_follows=true; ack_at=5; jiffies=0; dpregs[0]=4;
 assert(apple_dpin_set_active(&d,true)==0 && jiffies==5);
 ack_at=0;
 /* An unstable IRQ snapshot must mask its sources rather than livelock. */
 unstable=1; assert(apple_dpin_irq(1,&d)==IRQ_HANDLED && unstable==33);
 assert(!(dpregs[2]&3)); unstable=0;
 assert(apple_dpin_end(&d)==0);
 /* Missing PLL lock and APB failures propagate without caching success. */
 assert(atcphy_dpphy_set_mode(&phy,PHY_MODE_DP,1)==0);
 atcregs[0x7044/4]=0; apb_calls=0;
 assert(rate(&a,30)==-ETIMEDOUT && !a.dp_tunnel_pll && !(atcregs[0x2200/4]&0x54));
 atcregs[0x7044/4]=8; apb_calls=0; apb_fail_at=1;
 assert(rate(&a,30)==-EIO && !a.dp_tunnel_pll);
 apb_calls=0; apb_fail_at=2; assert(rate(&a,30)==-EIO && !a.dp_tunnel_pll);
 apb_calls=0; apb_fail_at=0; assert(rate(&a,30)==0 && a.dp_tunnel_pll);
 a.mode=APPLE_ATCPHY_MODE_OFF; prior=writes;
 assert(rate(&a,30)==-ENOLINK && writes==prior);
 assert(atcphy_dpphy_set_mode(&phy,PHY_MODE_DP,0)==0 && writes==prior);
 assert(atcphy_dpphy_set_mode(&phy,PHY_MODE_DP,1)==-ENOLINK);
 a.mode=APPLE_ATCPHY_MODE_USB4; hw.gen=ATCPHY_GENERATION_T8122;
 assert(atcphy_dpphy_set_mode(&phy,PHY_MODE_DP,1)==-EOPNOTSUPP);
 puts("PASS: native event replay, real HPD, IRQ acknowledgement/bounds, ACK timeout/detach, retained ownership, PLL faults, divider rates, MMIO allowlist");
}
'''
with tempfile.TemporaryDirectory(prefix='apple-dpin-test-') as tmp:
    srcfile=Path(tmp)/'test.c'; exe=Path(tmp)/'test'
    srcfile.write_text(preamble+dpdefs+atcdefs+'\n'+enums+cfg+state+funcs+main)
    command=['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter']
    if not args.no_sanitizers:
        command += ['-fsanitize=address,undefined']
    subprocess.run(command+[str(srcfile),'-o',str(exe)],check=True)
    # The kselftest runner wraps tests in stdbuf (LD_PRELOAD); ASan must come first.
    subprocess.run([str(exe)], check=True,
                   env={k: v for k, v in os.environ.items() if k != 'LD_PRELOAD'})
