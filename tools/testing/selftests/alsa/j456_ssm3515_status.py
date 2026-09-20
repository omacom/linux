#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise actual status getter: faults preserved, I/O errors not masked."""
from pathlib import Path
import subprocess
import tempfile
root = Path(__file__).resolve().parents[4]
source = (root/'sound/soc/codecs/ssm3515.c').read_text()
function = source[source.index('static int ssm3515_status_get('):source.index('static const struct snd_kcontrol_new ssm3515_snd_controls[]')]
stub = r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#define SSM3515_STATUS 10
struct regmap { unsigned status; int error; };
struct ssm3515_data { struct regmap *regmap; };
struct snd_soc_component { struct ssm3515_data *data; };
struct snd_kcontrol { struct snd_soc_component *component; };
struct snd_ctl_elem_value { struct { struct { long value[1]; } integer; } value; };
static struct snd_soc_component *snd_kcontrol_chip(struct snd_kcontrol *k) { return k->component; }
static void *snd_soc_component_get_drvdata(struct snd_soc_component *c) { return c->data; }
static int regmap_read(struct regmap *m, unsigned reg, unsigned *value) {
    assert(reg == SSM3515_STATUS);
    if (m->error) return m->error;
    *value = m->status; return 0;
}
'''
test = r'''
int main(void) {
    struct regmap m = {0};
    struct ssm3515_data d = {&m};
    struct snd_soc_component c = {&d};
    struct snd_kcontrol k = {&c};
    struct snd_ctl_elem_value v = {0};
    for (unsigned i=0; i<256; i++) {
        m.status=i;
        assert(ssm3515_status_get(&k,&v)==0);
        assert(v.value.integer.value[0]==(i&127));
    }
    for (int e=-1; e>=-4095; e--) {
        m.error=e; v.value.integer.value[0]=999;
        assert(ssm3515_status_get(&k,&v)==e);
        assert(v.value.integer.value[0]==999);
    }
    puts("PASS: all status bits preserved; all Linux error values propagate without fabricated status");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp); (p/'test.c').write_text(stub+function+test)
    subprocess.run(['gcc','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
