#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual crossbar code: preserve legacy register order and leased ownership.

Uses a register model; this cannot establish electrical or firmware correctness.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile
root = Path(os.environ.get('KSRC') or Path(__file__).resolve().parents[5])
source = (root / 'drivers/mux/apple-display-crossbar.c').read_text()
# The pre-DP IN apple_dpxbar_set(), verbatim, is the regression oracle for
# the legacy register order; the new implementation must drive the same
# writes for DPPHY selections.
old = r'''
static int apple_dpxbar_set(struct mux_control *mux, int state)
{
	struct apple_dpxbar *dpxbar = mux_chip_priv(mux->chip);
	unsigned int index = mux_control_get_index(mux);
	unsigned long flags;
	unsigned int mux_state;
	unsigned int dispext_bit;
	unsigned int dispext_bit_en;
	unsigned int atc_bit;
	bool enable;
	int ret = 0;
	u32 mux_mask, mux_set;

	if (state == MUX_IDLE_DISCONNECT) {
		/*
		 * Technically this will select dispext0,0 in the mux control
		 * register. Practically that doesn't matter since everything
		 * else is disabled.
		 */
		mux_state = 0;
		enable = false;
	} else if (state >= 0 && state < 9) {
		dispext_bit = 1 << state;
		dispext_bit_en = 1 << (2 * state);
		mux_state = state;
		enable = true;
	} else {
		return -EINVAL;
	}

	switch (index) {
	case MUX_DPPHY:
		mux_mask = CROSSBAR_MUX_CTRL_DPPHY_SELECT0 |
			   CROSSBAR_MUX_CTRL_DPPHY_SELECT1;
		mux_set =
			FIELD_PREP(CROSSBAR_MUX_CTRL_DPPHY_SELECT0, mux_state) |
			FIELD_PREP(CROSSBAR_MUX_CTRL_DPPHY_SELECT1, mux_state);
		atc_bit = ATC_DPPHY;
		break;
	case MUX_DPIN0:
		mux_mask = CROSSBAR_MUX_CTRL_DPIN0_SELECT0 |
			   CROSSBAR_MUX_CTRL_DPIN0_SELECT1;
		mux_set =
			FIELD_PREP(CROSSBAR_MUX_CTRL_DPIN0_SELECT0, mux_state) |
			FIELD_PREP(CROSSBAR_MUX_CTRL_DPIN0_SELECT1, mux_state);
		atc_bit = ATC_DPIN0;
		break;
	case MUX_DPIN1:
		mux_mask = CROSSBAR_MUX_CTRL_DPIN1_SELECT0 |
			   CROSSBAR_MUX_CTRL_DPIN1_SELECT1;
		mux_set =
			FIELD_PREP(CROSSBAR_MUX_CTRL_DPIN1_SELECT0, mux_state) |
			FIELD_PREP(CROSSBAR_MUX_CTRL_DPIN1_SELECT1, mux_state);
		atc_bit = ATC_DPIN1;
		break;
	default:
		return -EINVAL;
	}

	spin_lock_irqsave(&dpxbar->lock, flags);

	/* ensure the selected dispext isn't already used in this crossbar */
	if (enable) {
		for (int i = 0; i < MUX_MAX; ++i) {
			if (i == index)
				continue;
			if (dpxbar->selected_dispext[i] == state) {
				spin_unlock_irqrestore(&dpxbar->lock, flags);
				return -EBUSY;
			}
		}
	}

	dpxbar_set32(dpxbar, OUT_N_CLK_EN, atc_bit);
	dpxbar_clear32(dpxbar, OUT_UNK_EN, atc_bit);
	dpxbar_clear32(dpxbar, OUT_PCLK1_EN, atc_bit);
	dpxbar_clear32(dpxbar, CROSSBAR_ATC_EN, atc_bit);

	if (dpxbar->selected_dispext[index] >= 0) {
		u32 prev_dispext_bit = 1 << dpxbar->selected_dispext[index];
		u32 prev_dispext_bit_en = 1 << (2 * dpxbar->selected_dispext[index]);

		dpxbar_set32(dpxbar, FIFO_WR_N_CLK_EN, prev_dispext_bit);
		dpxbar_set32(dpxbar, FIFO_RD_N_CLK_EN, prev_dispext_bit);
		dpxbar_clear32(dpxbar, FIFO_WR_UNK_EN, prev_dispext_bit);
		dpxbar_clear32(dpxbar, FIFO_RD_UNK_EN, prev_dispext_bit_en);
		dpxbar_clear32(dpxbar, FIFO_WR_DPTX_CLK_EN, prev_dispext_bit);
		dpxbar_clear32(dpxbar, FIFO_RD_PCLK1_EN, prev_dispext_bit);
		dpxbar_clear32(dpxbar, CROSSBAR_DISPEXT_EN, prev_dispext_bit);

		dpxbar->selected_dispext[index] = -1;
	}

	dpxbar_mask32(dpxbar, CROSSBAR_MUX_CTRL, mux_mask, mux_set);

	if (enable) {
		dpxbar_clear32(dpxbar, FIFO_WR_N_CLK_EN, dispext_bit);
		dpxbar_clear32(dpxbar, FIFO_RD_N_CLK_EN, dispext_bit);
		dpxbar_clear32(dpxbar, OUT_N_CLK_EN, atc_bit);
		dpxbar_set32(dpxbar, FIFO_WR_UNK_EN, dispext_bit);
		dpxbar_set32(dpxbar, FIFO_RD_UNK_EN, dispext_bit_en);
		dpxbar_set32(dpxbar, OUT_UNK_EN, atc_bit);
		dpxbar_set32(dpxbar, FIFO_WR_DPTX_CLK_EN, dispext_bit);
		dpxbar_set32(dpxbar, FIFO_RD_PCLK1_EN, dispext_bit);
		dpxbar_set32(dpxbar, OUT_PCLK1_EN, atc_bit);
		dpxbar_set32(dpxbar, CROSSBAR_ATC_EN, atc_bit);
		dpxbar_set32(dpxbar, CROSSBAR_DISPEXT_EN, dispext_bit);

		/*
		 * Work around some HW quirk:
		 * Without toggling the RD_PCLK enable here the connection
		 * doesn't come up. Testing has shown that a delay of about
		 * 5 usec is required which is doubled here to be on the
		 * safe side.
		 */
		dpxbar_clear32(dpxbar, FIFO_RD_PCLK1_EN, dispext_bit);
		udelay(10);
		dpxbar_set32(dpxbar, FIFO_RD_PCLK1_EN, dispext_bit);

		dpxbar->selected_dispext[index] = state;
	}

	spin_unlock_irqrestore(&dpxbar->lock, flags);

	if (enable)
		dev_info(dpxbar->dev, "Switched %s to dispext%u,%u\n",
			 apple_dpxbar_names[index], mux_state >> 1,
			 mux_state & 1);
	else
		dev_info(dpxbar->dev, "Switched %s to disconnected state\n",
			 apple_dpxbar_names[index]);

	return ret;
}
'''
def fn(s, name):
    m = re.search(r'(?m)^(?:static )?(?:inline )?(?:int|void)\s+' + name + r'\(', s)
    assert m, name
    return s[m.start():s.index('\n}\n', m.start()) + 3]
pre = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
typedef uint32_t u32;
#define BIT(n) (1U << (n))
#define GENMASK(h,l) ((~0U >> (31-(h))) & (~0U << (l)))
#define FIELD_PREP(m,v) (((v) << __builtin_ctz(m)) & (m))
#define MUX_IDLE_DISCONNECT -2
#define spin_lock_irqsave(l,f) ((void)(l), (f)=0)
#define spin_unlock_irqrestore(l,f) ((void)(l), (void)(f))
#define dev_info(...) ((void)0)
#define dev_warn(...) ((void)0)
#define udelay(x) ((void)(x))
struct mux_control;
struct mux_control_ops { int (*set)(struct mux_control *,int); };
struct apple_dpxbar_hw { unsigned n_ufp; u32 tunable; const struct mux_control_ops *ops; bool dpin_cycle_slip_workaround; };
struct apple_dpxbar { void *dev; const struct apple_dpxbar_hw *hw; void *regs; int selected_dispext[3]; bool active[3]; int lock; };
struct mux_chip { struct apple_dpxbar *priv; const struct mux_control_ops *ops; };
struct mux_control { struct mux_chip *chip; unsigned index; };
static void *mux_chip_priv(struct mux_chip *m) { return m->priv; }
static unsigned mux_control_get_index(struct mux_control *m) { return m->index; }
static u32 events[256]; static unsigned count;
static u32 readl(void *p) { return *(u32 *)p; }
static void writel(u32 v, void *p) { assert(count < 256); events[count++]=v; *(u32 *)p=v; }
'''
defines = '\n'.join(l for l in source.splitlines() if l.startswith('#define '))
enum = 'enum { MUX_DPPHY = 0, MUX_DPIN0 = 1, MUX_DPIN1 = 2, MUX_MAX = 3 };\n'
code = pre + defines + '\n' + enum
for name in ['dpxbar_mask32','dpxbar_set32','dpxbar_clear32','apple_dpxbar_link_down','apple_dpxbar_dpin_take_down','apple_dpxbar_link_up','apple_dpxbar_set']:
    code += fn(source,name)
code += '\nstatic const struct mux_control_ops apple_dpxbar_ops = { apple_dpxbar_set };\n'
code += fn(source,'apple_dpxbar_set_active')
code += fn(old,'apple_dpxbar_set').replace('apple_dpxbar_set(', 'legacy_set(')
code += r'''
int main(void) {
 u32 regs[1024], reference[1024], saved_events[256];
 static const struct apple_dpxbar_hw hw = { .dpin_cycle_slip_workaround = false };
 struct apple_dpxbar x = { .hw=&hw, .regs=regs }, old = { .hw=&hw, .regs=reference };
 struct mux_chip chip = { &x, &apple_dpxbar_ops }, oldchip = { &old, &apple_dpxbar_ops };
 struct mux_control mux = { &chip, MUX_DPPHY }, oldmux = { &oldchip, MUX_DPPHY };
 /* The native DP PHY destination keeps the legacy bring-up at selection. */
 for (int prior=-1; prior<9; prior++) for (int next=-2; next<9; next++) {
  if (next == -1) continue;
  for (unsigned i=0;i<1024;i++) regs[i]=reference[i]=0xa55aa55a;
  for (unsigned i=0;i<3;i++) x.selected_dispext[i]=old.selected_dispext[i]=-1;
  x.selected_dispext[MUX_DPPHY]=old.selected_dispext[MUX_DPPHY]=prior;
  count=0; assert(!legacy_set(&oldmux,next)); unsigned n=count;
  memcpy(saved_events,events,n*sizeof(u32));
  count=0; assert(!apple_dpxbar_set(&mux,next));
  assert(count==n && !memcmp(saved_events,events,n*sizeof(u32)));
  assert(!memcmp(regs,reference,sizeof(regs)));
  assert(!memcmp(x.selected_dispext,old.selected_dispext,sizeof(x.selected_dispext)));
 }
 /* DP IN destinations: selection writes the selector only (native connect). */
 for (unsigned index=MUX_DPIN0; index<=MUX_DPIN1; index++) for (int next=0; next<9; next++) {
  u32 atc = index==MUX_DPIN0 ? ATC_DPIN0 : ATC_DPIN1;
  memset(regs,0,sizeof(regs));
  for (unsigned i=0;i<3;i++) x.selected_dispext[i]=-1;
  mux.index=index; count=0;
  assert(!apple_dpxbar_set(&mux,next));
  assert(!(regs[CROSSBAR_DISPEXT_EN/4] & BIT(next)) && !(regs[FIFO_WR_DPTX_CLK_EN/4] & BIT(next)));
  assert(!(regs[FIFO_RD_PCLK1_EN/4] & BIT(next)) && !(regs[OUT_PCLK1_EN/4] & atc) && !(regs[CROSSBAR_ATC_EN/4] & atc));
  u32 route=regs[CROSSBAR_MUX_CTRL/4]; assert(!x.active[index] && x.selected_dispext[index]==next);
  assert(!apple_dpxbar_set_active(&mux,true));
  assert(x.active[index] && (regs[CROSSBAR_DISPEXT_EN/4] & BIT(next)) && (regs[FIFO_WR_DPTX_CLK_EN/4] & BIT(next)));
  assert((regs[FIFO_RD_PCLK1_EN/4] & BIT(next)) && (regs[OUT_PCLK1_EN/4] & atc) && (regs[CROSSBAR_ATC_EN/4] & atc));
  assert(!(regs[FIFO_WR_N_CLK_EN/4] & BIT(next)) && !(regs[OUT_N_CLK_EN/4] & atc));
  assert(!apple_dpxbar_set_active(&mux,false));
  /* Native takeConnectionDown: enables off, clocks gated, destination enable retained. */
  assert(!x.active[index] && !(regs[CROSSBAR_DISPEXT_EN/4] & BIT(next)) && !(regs[FIFO_WR_DPTX_CLK_EN/4] & BIT(next)));
  assert(!(regs[FIFO_RD_PCLK1_EN/4] & BIT(next)) && !(regs[OUT_PCLK1_EN/4] & atc));
  assert((regs[FIFO_WR_N_CLK_EN/4] & BIT(next)) && (regs[FIFO_RD_N_CLK_EN/4] & BIT(next)) && (regs[OUT_N_CLK_EN/4] & atc));
  assert((regs[CROSSBAR_ATC_EN/4] & atc) && regs[CROSSBAR_MUX_CTRL/4]==route && x.selected_dispext[index]==next);
 }
 memset(regs,0,sizeof(regs));
 for (unsigned i=0;i<3;i++) x.selected_dispext[i]=-1;
 mux.index=MUX_DPIN0; count=0;
 assert(apple_dpxbar_set_active(&mux,true)==-ENOLINK && !count);
 assert(!apple_dpxbar_set(&mux,2)); u32 route=regs[CROSSBAR_MUX_CTRL/4];
 count=0; assert(!apple_dpxbar_set_active(&mux,false) && !count && !x.active[MUX_DPIN0]);
 assert(!apple_dpxbar_set_active(&mux,true)); assert(x.active[MUX_DPIN0]);
 count=0; assert(!apple_dpxbar_set_active(&mux,false));
 assert(count && !x.active[MUX_DPIN0]);
 assert(x.selected_dispext[MUX_DPIN0]==2 && regs[CROSSBAR_MUX_CTRL/4]==route);
 count=0; assert(!apple_dpxbar_set_active(&mux,false) && !count);
 struct mux_control other={ &chip, MUX_DPIN1 };
 assert(apple_dpxbar_set(&other,2)==-EBUSY && !count);
 assert(!apple_dpxbar_set_active(&mux,true));
 assert(x.active[MUX_DPIN0] && regs[CROSSBAR_MUX_CTRL/4]==route);
 count=0; assert(!apple_dpxbar_set_active(&mux,true) && !count);
 assert(!apple_dpxbar_set(&mux,MUX_IDLE_DISCONNECT));
 count=0; assert(apple_dpxbar_set_active(&mux,true)==-ENOLINK && !count);
 mux.index=MUX_DPPHY;
 assert(apple_dpxbar_set_active(&mux,true)==-EOPNOTSUPP && !count);
 mux.index=MUX_DPIN0; chip.ops=NULL;
 assert(apple_dpxbar_set_active(&mux,true)==-EOPNOTSUPP && !count);
 puts("PASS: DP PHY selection preserves legacy MMIO order/state; DP IN selection is selector-only, native bring-up/take-down retains ownership and destination enable");
}
'''
with tempfile.TemporaryDirectory(prefix='apple-crossbar-test-') as tmp:
    src=Path(tmp)/'test.c'; exe=Path(tmp)/'test'; src.write_text(code)
    subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-sign-compare','-fsanitize=undefined',str(src),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
