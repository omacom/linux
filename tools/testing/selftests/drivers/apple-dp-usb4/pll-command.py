#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check that the actual AUSPLL command helper propagates handshake timeouts."""
import os
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(os.environ.get('KSRC') or Path(__file__).resolve().parents[5])
source = (root / 'drivers/phy/apple/atc.c').read_text()
start = source.index('static int atcphy_auspll_apb_command(')
end = source.index('\n}', start) + 2
names = ['AUSPLL_APB_CMD_OVERRIDE', 'AUSPLL_APB_CMD_OVERRIDE_CMD',
         'AUSPLL_APB_CMD_OVERRIDE_REQ', 'AUSPLL_APB_CMD_OVERRIDE_ACK',
         'AUSPLL_APB_CMD_OVERRIDE_UNK28']
definitions = '\n'.join(re.search(r'^#define ' + name + r'\s+.*$', source,
                                     re.MULTILINE).group() for name in names)
code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
typedef uint32_t u32;
#define BIT(n) (1U<<(n))
#define GENMASK(h,l) ((~0U<<(l)) & (~0U>>(31-(h))))
#define FIELD_PREP(mask,v) (((v)<<__builtin_ctz(mask))&(mask))
#define dev_warn(...) ((void)0)
'''+definitions+r'''
struct apple_atcphy { struct { void *core; } regs; void *dev; };
static uint32_t value, submitted;
static int timeout;
static u32 readl(void *p) { (void)p; return value; }
static void writel(u32 v, void *p) { (void)p; value=submitted=v; }
static void core_clear32(struct apple_atcphy *a, unsigned reg, u32 mask)
{ (void)a; assert(reg==AUSPLL_APB_CMD_OVERRIDE); value &= ~mask; }
#define readl_poll_timeout(addr,reg,cond,delay,limit) ({ \
 assert((delay)==10 && (limit)==10000); \
 if(!timeout) value |= AUSPLL_APB_CMD_OVERRIDE_ACK; \
 (reg)=readl(addr); (cond)?0:-ETIMEDOUT; })
'''+source[start:end]+r'''
int main(void)
{
 unsigned char registers[AUSPLL_APB_CMD_OVERRIDE+4];
 struct apple_atcphy a={.regs.core=registers};
 const unsigned commands[]={0,0x2000,0x2800};
 for(unsigned i=0;i<3;i++) for(timeout=0;timeout<2;timeout++) {
  value=0x80000000; /* unrelated state must survive */
  int ret=atcphy_auspll_apb_command(&a,commands[i]);
  assert(ret==(timeout?-ETIMEDOUT:0));
  assert(submitted & AUSPLL_APB_CMD_OVERRIDE_REQ);
  assert(submitted & AUSPLL_APB_CMD_OVERRIDE_UNK28);
  assert((submitted & AUSPLL_APB_CMD_OVERRIDE_CMD)==
         FIELD_PREP(AUSPLL_APB_CMD_OVERRIDE_CMD,commands[i]));
  assert(!(value & AUSPLL_APB_CMD_OVERRIDE_REQ));
  assert(value & 0x80000000);
 }
 puts("PASS: PLL initial/tunnel/native commands propagate timeout and clear request on both outcomes");
}
'''
with tempfile.TemporaryDirectory(prefix='apple-pll-command-') as tmp:
    src = Path(tmp) / 'test.c'
    binary = Path(tmp) / 'test'
    src.write_text(code)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=undefined', '-g', str(src), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
