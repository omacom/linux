#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Fault-inject the actual codec prepare function using a mock regmap.

This verifies the driver's startup gate, not electrical behavior or I2C hardware.
"""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[4]
source = (root / 'sound/soc/codecs/ssm3515.c').read_text()
start = source.index('static int ssm3515_prepare(')
end = source.index('\nstatic int ssm3515_hw_params(', start)
function = source[start:end]
definitions = '\n'.join(re.findall(r'^#define SSM3515_.*$', source, re.M))
stub = r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#define BIT(n) (1U << (n))
#define GENMASK(h, l) (((~0U) << (l)) & ((~0U) >> (31-(h))))
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define dev_err(...) do {} while (0)
struct regmap { unsigned cache[12], actual[12]; };
struct ssm3515_data { struct regmap *regmap; };
struct snd_soc_component { struct ssm3515_data *data; };
struct snd_soc_dai { struct snd_soc_component *component; };
struct snd_pcm_substream { int unused; };
static int fail_cache = -1, fail_actual = -1, fail_write;
static int write_count, actual_reads;
static void *snd_soc_component_get_drvdata(struct snd_soc_component *c) {
    return c->data;
}
static int regmap_read(struct regmap *m, unsigned r, unsigned *v) {
    if ((int)r == fail_cache) return -EAGAIN;
    *v = m->cache[r]; return 0;
}
static int regmap_read_bypassed(struct regmap *m, unsigned r, unsigned *v) {
    actual_reads++;
    if ((int)r == fail_actual) return -EREMOTEIO;
    *v = m->actual[r]; return 0;
}
static int regmap_write(struct regmap *m, unsigned r, unsigned v) {
    write_count++;
    if (fail_write) return -ENXIO;
    m->cache[r] = m->actual[r] = v; return 0;
}
'''
tests = r'''
int main(void) {
    struct regmap m;
    struct ssm3515_data data = { .regmap = &m };
    struct snd_soc_component c = { .data = &data };
    struct snd_soc_dai dai = { .component = &c };
    unsigned regs[] = { SSM3515_GEC, SSM3515_DAC, SSM3515_DAC_VOL,
        SSM3515_SAI1, SSM3515_SAI2, SSM3515_LIM1, SSM3515_LIM2 };
    memset(&m, 0, sizeof(m));
    assert(ssm3515_prepare(NULL, &dai) == 0);
    assert(actual_reads == 7 && write_count == 0);
    for (unsigned i = 0; i < ARRAY_SIZE(regs); i++) {
        for (unsigned bit = 0; bit < 8; bit++) {
            memset(&m, 0, sizeof(m)); write_count = 0;
            m.cache[SSM3515_DAC] = m.actual[SSM3515_DAC] = SSM3515_DAC_MUTE;
            m.actual[regs[i]] ^= BIT(bit);
            assert(ssm3515_prepare(NULL, &dai) == -EIO);
            assert(write_count == 1); /* Must not skip an already-cached mute. */
            assert(m.actual[SSM3515_DAC] == SSM3515_DAC_MUTE);
        }
        memset(&m, 0, sizeof(m));
        fail_cache = regs[i];
        assert(ssm3515_prepare(NULL, &dai) == -EAGAIN);
        fail_cache = -1;
        fail_actual = regs[i];
        assert(ssm3515_prepare(NULL, &dai) == -EREMOTEIO);
        fail_actual = -1;
    }
    memset(&m, 0, sizeof(m));
    m.actual[SSM3515_LIM1] = 1;
    fail_write = 1;
    assert(ssm3515_prepare(NULL, &dai) == -ENXIO);
    puts("PASS: physical readback required; all register-bit mismatches rejected; forced mute and I/O failure propagation checked");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp)
    (path / 'test.c').write_text(stub + definitions + '\n' + function + tests)
    subprocess.run(['gcc', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                    '-o', str(path / 'test'), str(path / 'test.c')], check=True)
    subprocess.run([str(path / 'test')], check=True)
