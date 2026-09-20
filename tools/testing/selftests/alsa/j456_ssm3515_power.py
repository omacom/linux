#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check actual probe's diagnostic scope, mute ordering and I/O failures."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[4];s=(r/'sound/soc/codecs/ssm3515.c').read_text();f=s[s.index('static int ssm3515_probe('):s.index('static int ssm3515_mute(')]
stub=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#define SSM3515_PWR 0
#define SSM3515_DAC 2
#define SSM3515_DAC_VOL 3
#define SSM3515_PWR_APWDN_EN 128
#define SSM3515_PWR_SPWDN 1
#define SSM3515_DAC_MUTE 64
struct snd_soc_component { unsigned regs[4]; };
static bool j456_no_auto_powerdown, model;
static int calls,fail;
static bool of_machine_is_compatible(const char *name) { (void)name;return model; }
static int snd_soc_component_write(struct snd_soc_component*c,unsigned r,unsigned v) {
 if (++calls==fail) return -EREMOTEIO;
 c->regs[r]=v;return 0;
}
static int snd_soc_component_update_bits(struct snd_soc_component*c,unsigned r,unsigned mask,unsigned v) {
 if (++calls==fail) return -EREMOTEIO;
 if (r==SSM3515_PWR) { assert(c->regs[2]&64);assert(c->regs[3]==255); }
 c->regs[r]=(c->regs[r]&~mask)|(v&mask);return 0;
}
'''
test=r'''
int main(void) {
 for (int enabled=0;enabled<2;enabled++) for (int imac=0;imac<2;imac++) {
  struct snd_soc_component c={{129,0,50,64}};
  j456_no_auto_powerdown=enabled;model=imac;calls=0;fail=0;
  int ret=ssm3515_probe(&c);
  if(enabled&&!imac){assert(ret==-EINVAL);assert(c.regs[0]==129);}
  else {assert(ret==0);assert(c.regs[0]==(enabled?0:128));}
 }
 model=true;j456_no_auto_powerdown=true;
 for(fail=1;fail<=4;fail++) {
  struct snd_soc_component c={{129,0,50,64}};calls=0;
  assert(ssm3515_probe(&c)==-EREMOTEIO);assert(calls==fail);
 }
 puts("PASS: diagnosis opt-in and J456-only; digital mute precedes power writes; all write failures propagated");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(stub+f+test);subprocess.run(['gcc','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
