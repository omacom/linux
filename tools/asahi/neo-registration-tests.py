#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only OR MIT
"""Exercise display registration, SoC admission and registration failure cleanup."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def function(source, name):
    match = re.search(r'^(?:static )?(?:int|void) __init ' + name + r'\(void\)', source, re.M)
    assert match, name
    end = source.index('\n}', match.end()) + 2
    return source[match.start():end]


def driver_name(source, symbol):
    start = source.index('static struct platform_driver ' + symbol + ' =')
    end = source.index('\n};', start)
    return re.search(r'\.name\s*=\s*"([^"]+)"', source[start:end])[1]


def check(root):
    legacy = root / 'drivers/gpu/drm/apple'
    neo = root / 'drivers/gpu/drm/apple-neo'
    files = {str(p): p.read_text() for d in (legacy, neo)
             for p in (d/'audio.c', d/'dcp.c', d/'apple_drv.c')}
    code = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#define __init
#define IS_ENABLED(x) x
#define CONFIG_DRM_APPLE_AUDIO AUDIO
#define CONFIG_DRM_APPLE_NEO_AUDIO AUDIO
struct platform_driver { const char *name; };
static struct platform_driver drivers[6];
static struct platform_driver *registered[6];
static unsigned count, attempts, unregisters;
static int fail_at = -1;
static bool t8140, firmware_only;
static bool of_machine_is_compatible(const char *name) {
 assert(!strcmp(name,"apple,t8140")); return t8140;
}
static bool drm_firmware_drivers_only(void) { return firmware_only; }
static int platform_driver_register(struct platform_driver *driver) {
 if ((int)attempts++ == fail_at) return -EIO;
 for (unsigned i=0;i<count;i++)
  if (!strcmp(driver->name,registered[i]->name)) return -EBUSY;
 assert(count<6);registered[count++]=driver;return 0;
}
static void platform_driver_unregister(struct platform_driver *driver) {
 for (unsigned i=0;i<count;i++) if (registered[i]==driver) {
  memmove(registered+i,registered+i+1,(count-i-1)*sizeof(*registered));
  count--;unregisters++;return;
 }
 assert(!"unregister of an unregistered driver");
}
static void dcp_audio_unregister(void) {platform_driver_unregister(&drivers[0]);}
static void dcp_unregister(void) {platform_driver_unregister(&drivers[1]);}
static void neo_dcp_audio_unregister(void) {platform_driver_unregister(&drivers[3]);}
static void neo_dcp_unregister(void) {platform_driver_unregister(&drivers[4]);}
FUNCTIONS
int main(void) {
 NAMES
 /* Built-in Neo must register nothing on any legacy machine. */
 for (unsigned board=0;board<8;board++) {
  t8140=false;attempts=count=unregisters=0;
  assert(appledrm_neo_register()==-ENODEV);assert(!attempts&&!count);
  assert(!appledrm_register());assert(count==2+AUDIO);
  platform_driver_unregister(&drivers[2]);dcp_unregister();
  if(AUDIO)dcp_audio_unregister();assert(!count);
 }
 /* Registration names remain disjoint even if both modules are loaded. */
 t8140=true;attempts=0;assert(!appledrm_neo_register());assert(count==2+AUDIO);
 assert(!appledrm_register());assert(count==2*(2+AUDIO));
 platform_driver_unregister(&drivers[2]);dcp_unregister();if(AUDIO)dcp_audio_unregister();
 platform_driver_unregister(&drivers[5]);neo_dcp_unregister();if(AUDIO)neo_dcp_audio_unregister();
 assert(!count);
 /* A failed registration must return its error and unwind only successes. */
 for (int failure=0;failure<2+AUDIO;failure++) {
  attempts=unregisters=0;fail_at=failure;
  assert(appledrm_neo_register()==-EIO);assert(!count);
  assert(unregisters==(unsigned)failure);
 }
 fail_at=-1;attempts=0;firmware_only=true;
 assert(appledrm_neo_register()==-ENODEV);assert(!attempts&&!count);
 puts("PASS actual display registration: legacy isolation, unique names, Neo admission and error unwind");
}
'''
    functions = []
    names = []
    for index, directory in enumerate((legacy, neo)):
        for offset, (file, symbol, fn) in enumerate((
                ('audio.c', 'neo_dcpaud_driver' if index else 'dcpaud_driver',
                 'neo_dcp_audio_register' if index else 'dcp_audio_register'),
                ('dcp.c', 'apple_platform_driver', 'neo_dcp_register' if index else 'dcp_register'),
                ('apple_drv.c', 'apple_platform_driver', 'appledrm_neo_register' if index else 'appledrm_register'))):
            source = files[str(directory/file)]
            slot = index*3+offset
            functions.append(function(source, fn).replace('&'+symbol, '&drivers['+str(slot)+']'))
            names.append('drivers[%d].name="%s";' % (slot, driver_name(source, symbol)))
    code = code.replace('FUNCTIONS', '\n'.join(functions)).replace('NAMES', '\n'.join(names))
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        (tmp/'test.c').write_text(code)
        for audio in (0, 1):
            subprocess.run(['cc', '-std=gnu11', '-Werror', '-DAUDIO='+str(audio),
                            str(tmp/'test.c'), '-o', str(tmp/'test')], check=True)
            subprocess.run([str(tmp/'test')], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT)
    check(parser.parse_args().source)
