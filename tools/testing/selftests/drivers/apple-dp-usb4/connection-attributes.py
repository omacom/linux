#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check real connection RPC builders against native DP IN role evidence.

The expected bytes come from the independently decoded macOS 13.5 DP IN
attributes and the working native capture, not a duplicate of the C builder.
No firmware or hardware is simulated.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(os.environ.get('KSRC') or Path(__file__).resolve().parents[5])
source = (root / 'drivers/gpu/drm/apple/dptxep.c').read_text()
header = (root / 'drivers/gpu/drm/apple/dptxep.h').read_text()


def function(name):
    match = re.search(r'(?m)^(?:static )?(?:u32|int)\s+' + name + r'\(', source)
    assert match, name
    return source[match.start():source.index('\n}', match.start()) + 2]


code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <endian.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef uint32_t __le32;
#define BIT(n) (1U << (n))
#define GENMASK(h,l) ((~0U >> (31-(h))) & (~0U << (l)))
#define FIELD_PREP(mask,val) (((u32)(val) << __builtin_ctz(mask)) & (mask))
#define cpu_to_le32(x) htole32(x)
#define le32_to_cpu(x) le32toh(x)
#define trace_dptxport_validate_connection(p,...) ((void)(p))
#define trace_dptxport_connect(p,...) ((void)(p))
#define dev_notice(...) ((void)0)
#define dev_info(...) ((void)0)
struct dptx_port { int unused; };
struct apple_epic_service { struct dptx_port *cookie; };
static unsigned rpc, corrupt, calls;
static int error;
static uint8_t expected[8];
static int afk_service_call(struct apple_epic_service *s, unsigned group,
                           unsigned command, const void *data, size_t length,
                           size_t padding, void *reply, size_t reply_size,
                           size_t reply_padding)
{
 assert(s && !group && command==rpc);
 assert(length==8 && reply_size==8);
 assert(padding==(rpc==12 ? 40U:24U) && reply_padding==padding);
 assert(!memcmp(data,expected,8));
 calls++;
 if (error) return error;
 memcpy(reply,data,8);
 if (corrupt) ((uint8_t *)reply)[corrupt-1]^=1;
 return 0;
}
'''
code += '\n'.join(line for line in header.splitlines()
                  if line.startswith('#define DCPDPTX_REMOTE_PORT_')) + '\n'
start = source.index('struct dcpdptx_connection_cmd {')
code += source[start:source.index('\n}', start) + 2] + ';\n'
for name in ('dptxport_connection_attributes', 'dptxport_validate_connection',
             'dptxport_connect'):
    code += function(name) + '\n'
code += r'''
int main(void)
{
 struct dptx_port p={0};
 struct apple_epic_service s={&p};
 /* Native rear-left DP IN0: role1, HPD1, target0x8001. */
 const uint8_t native[]={1,1,0,0,1,0x80,0,0};
 memcpy(expected,native,8);
 rpc=12; assert(!dptxport_validate_connection(&s,1,0,0));
 rpc=11; assert(!dptxport_connect(&s,1,0,0,true));
 /* Both logical DP INs retain role1 on all three board ports. */
 for (unsigned atc=0;atc<3;atc++) {
  for (unsigned dest=1;dest<=2;dest++) {
   expected[4]=(atc<<4)|dest;
   rpc=12; assert(!dptxport_validate_connection(&s,dest,atc,0));
   rpc=11; assert(!dptxport_connect(&s,dest,atc,0,true));
  }
 }
 /* Preserve die addressing and independent HPD encoding. */
 expected[4]=0x21; expected[5]=0x81;
 rpc=12; assert(!dptxport_validate_connection(&s,1,2,1));
 expected[1]=0;
 rpc=11; assert(!dptxport_connect(&s,1,2,1,false));
 /* Ordinary DP/HDMI destination0 keeps the existing role0 payload. */
 expected[0]=0; expected[1]=1; expected[4]=0x20; expected[5]=0x80;
 rpc=12; assert(!dptxport_validate_connection(&s,0,2,0));
 rpc=11; assert(!dptxport_connect(&s,0,2,0,true));
 expected[1]=0; expected[4]=0x50;
 assert(!dptxport_connect(&s,0,5,0,false));
 /* Firmware validation must reject corrupted role, HPD or destination. */
 memcpy(expected,native,8); rpc=12;
 for (unsigned i=1;i<=8;i++) {
  corrupt=i;
  assert(dptxport_validate_connection(&s,1,0,0)==-EINVAL);
 }
 corrupt=0; error=-ETIMEDOUT;
 assert(dptxport_validate_connection(&s,1,0,0)==-ETIMEDOUT);
 rpc=11; assert(dptxport_connect(&s,1,0,0,true)==-ETIMEDOUT);
 error=0; corrupt=5;
 assert(dptxport_connect(&s,1,0,0,true)==-EINVAL);
 assert(calls==30);
 puts("PASS: native role/HPD bytes, both DP INs, all ports, die address, native DP/HDMI preservation, reply corruption and transport errors");
}
'''
with tempfile.TemporaryDirectory(prefix='apple-connection-attributes-') as tmp:
    src, exe = Path(tmp) / 'test.c', Path(tmp) / 'test'
    src.write_text(code)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=undefined', str(src), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
