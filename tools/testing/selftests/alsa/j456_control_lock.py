#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the actual new control-lock function with mocked ALSA controls.

This checks its error handling and scope, not hardware or kernel integration.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
codec = (ROOT / 'sound/soc/codecs/ssm3515.c').read_text()
controls = codec.split('static const struct snd_kcontrol_new ssm3515_snd_controls[] = {', 1)[1].split('\n};', 1)[0]
for suffix in re.findall(r'SOC_\w+\("([^"]+)"', controls):
    for prefix in ('Left Tweeter', 'Right Tweeter', 'Left Woofer', 'Right Woofer'):
        name = prefix + ' ' + suffix
        assert len(name.encode()) < 44, f'ALSA would truncate control: {name}'
code = (ROOT / 'sound/soc/apple/macaudio.c').read_text()
start = code.index('static int macaudio_ssm3515_lock_controls(')
end = code.index('\nstatic int macaudio_fixup_controls(', start)
function = code[start:end]
matching = (ROOT / 'sound/soc/soc-ops.c').read_text()
start = matching.index('bool snd_soc_control_matches(')
end = matching.index('\nEXPORT_SYMBOL_GPL(snd_soc_control_matches);', start)
matching = matching[start:end]

stub = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>
#define SNDRV_CTL_ELEM_ACCESS_WRITE 2
#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))
static int sequence;
static bool allocation_failure;
#define kzalloc_obj(x) (allocation_failure ? NULL : calloc(1, sizeof(x)))
#define kfree free
struct snd_ctl_elem_value {
    union {
        struct { long value[8]; } integer;
        struct { unsigned item[8]; } enumerated;
    } value;
};
struct snd_kcontrol {
    struct { char name[44]; } id;
    int count;
    struct { unsigned access; } vd[1];
    int (*put)(struct snd_kcontrol *, struct snd_ctl_elem_value *);
    struct snd_kcontrol *next;
    int result;
    long written;
    int write_sequence;
};
struct snd_card { struct snd_kcontrol *controls; };
struct snd_soc_card { struct snd_card *snd_card; };
#define list_for_each_entry(pos, head, member) \
    for ((pos) = *(head); (pos); (pos) = (pos)->next)
static int put(struct snd_kcontrol *k, struct snd_ctl_elem_value *v) {
    if (k->result < 0) return k->result;
    k->written = v->value.integer.value[0];
    k->write_sequence = ++sequence;
    return k->result;
}
'''
tests = r'''
int main(void) {
    struct snd_kcontrol controls[30];
    struct snd_card snd = { .controls = controls };
    struct snd_soc_card card = { .snd_card = &snd };
    const char *positions[] = {
        "Left Tweeter", "Right Tweeter", "Left Woofer", "Right Woofer"
    };
    const char *suffixes[] = {
        "DAC Analog Gain Select", "HPF Switch", "Limiter Threshold",
        "Limiter Attack Rate", "Limiter Release Rate",
        "Limiter Tracking Switch", "Limiter Mode"
    };
    const long expected[] = { 0, 1, 31, 3, 0, 0, 1 };
    memset(controls, 0, sizeof(controls));
    for (int i = 0; i < 30; i++) {
        controls[i].count = 1;
        controls[i].vd[0].access = 3;
        controls[i].put = put;
        controls[i].written = -99;
        controls[i].next = i == 29 ? NULL : &controls[i+1];
        controls[i].result = i & 1; /* Both ALSA success return values. */
    }
    for (int kind = 0; kind < 7; kind++) {
        for (int i = 0; i < 4; i++) {
            assert(snprintf(controls[kind*4+i].id.name, sizeof(controls[kind*4+i].id.name), "%s %s", positions[i], suffixes[kind]) < (int)sizeof(controls[kind*4+i].id.name));
        }
    }
    strcpy(controls[28].id.name, "Jack ADC HPF Switch");
    strcpy(controls[29].id.name, "Jack DAC HPF Switch");
    assert(macaudio_ssm3515_lock_controls(&card) == 0);
    for (int i = 0; i < 28; i++) {
        assert(!(controls[i].vd[0].access & SNDRV_CTL_ELEM_ACCESS_WRITE));
        assert(controls[i].written == expected[i/4]);
        if (i < 24) assert(controls[i].write_sequence < controls[24].write_sequence);
    }
    for (int i = 28; i < 30; i++) {
        assert(controls[i].vd[0].access == 3);
        assert(controls[i].written == -99);
    }
    for (int missing = 0; missing < 28; missing++) {
        char name[44];
        for (int i = 0; i < 30; i++) controls[i].written = -99;
        strcpy(name, controls[missing].id.name);
        strcpy(controls[missing].id.name, "Unexpected control");
        assert(macaudio_ssm3515_lock_controls(&card) == -EINVAL);
        if (missing < 24) {
            for (int i = 24; i < 28; i++) assert(controls[i].written == -99);
        }
        strcpy(controls[missing].id.name, name);
    }
    for (int failure = 0; failure < 28; failure++) {
        for (int i = 0; i < 30; i++) controls[i].written = -99;
        controls[failure].result = -EIO;
        assert(macaudio_ssm3515_lock_controls(&card) == -EIO);
        if (failure < 24) {
            for (int i = 24; i < 28; i++) assert(controls[i].written == -99);
        }
        controls[failure].result = 0;
    }
    allocation_failure = true;
    assert(macaudio_ssm3515_lock_controls(&card) == -ENOMEM);
    puts("PASS: gain/HPF/limiter locked; limiter enabled last; jack untouched; missing controls and I/O/allocation failures rejected");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / 'test.c'
    exe = Path(tmp) / 'test'
    c.write_text(stub + matching + function + tests)
    subprocess.run(['gcc', '-Wall', '-Wextra', '-Werror', '-o', str(exe), str(c)], check=True)
    subprocess.run([str(exe)], check=True)
