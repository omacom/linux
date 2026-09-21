#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Test actual variable-size DPTX drive-setting handlers with guarded buffers."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[5]
s=(root/'drivers/gpu/drm/apple/dptxep.c').read_text()
a=s.index('struct dptxport_apcall_drive_settings {'); b=s.index('\n};',a)+3
struct=s[a:b]
a=s.index('static int\ndptxport_call_get_drive_settings('); b=s.index('\nstatic int dptxport_call_get_max_link_rate',a)
code=r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
typedef uint32_t __le32; typedef uint64_t __le64;
typedef uint32_t u32; typedef uint8_t u8;
#define le32_to_cpu(x) (x)
#define cpu_to_le32(x) (x)
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define struct_size(p,m,n) (sizeof(*(p)) + sizeof((p)->m[0])*(n))
struct dptx_port { __le64 drive_settings[4]; };
struct apple_epic_service { void *cookie; };
'''+struct+s[a:b]+r'''
int main(void) {
 struct dptx_port port={0}; struct apple_epic_service service={&port};
 union { uint64_t align; unsigned char bytes[96]; } req, out;
 struct dptxport_apcall_drive_settings *r=(void*)req.bytes, *o=(void*)out.bytes;
 assert(sizeof(*r)==32);
 for(unsigned n=0;n<=4;n++) {
  size_t size=32+8*n;
  memset(&req,0,sizeof(req)); memset(&out,0xa5,sizeof(out));
  r->count_or_status=n;
  for(unsigned i=0;i<n;i++) r->settings[i]=0x1234567800000010ULL+i;
  assert(!dptxport_call_set_drive_settings(&service,r,size,o,size));
  assert(o->status_or_count==0 && o->count_or_status==n);
  for(unsigned i=0;i<4;i++) assert(port.drive_settings[i]==(i<n?0x1234567800000010ULL+i:0));
  for(size_t i=size;i<sizeof(out);i++) assert(out.bytes[i]==0xa5);
  r->status_or_count=n; r->count_or_status=0xdeadbeef;
  memset(r->settings,0,8*n); memset(&out,0xa5,sizeof(out));
  assert(!dptxport_call_get_drive_settings(&service,r,size,o,size));
  assert(o->status_or_count==n && o->count_or_status==0);
  assert(!memcmp(o->settings,port.drive_settings,8*n));
  for(size_t i=size;i<sizeof(out);i++) assert(out.bytes[i]==0xa5);
  /* One-byte truncation must fail without modifying output or cache. */
  r->count_or_status=n;
  struct dptx_port saved=port;
  memset(&out,0xa5,sizeof(out));
  assert(dptxport_call_set_drive_settings(&service,r,size-1,o,size)==-EINVAL);
  assert(dptxport_call_set_drive_settings(&service,r,size,o,size-1)==-EINVAL);
  assert(dptxport_call_get_drive_settings(&service,r,size-1,o,size)==-EINVAL);
  assert(dptxport_call_get_drive_settings(&service,r,size,o,size-1)==-EINVAL);
  assert(!memcmp(&saved,&port,sizeof(port)));
  for(size_t i=0;i<sizeof(out);i++) assert(out.bytes[i]==0xa5);
 }
 for(unsigned i=0;i<2;i++) {
  r->count_or_status=r->status_or_count=i?UINT32_MAX:5;
  assert(dptxport_call_set_drive_settings(&service,r,64,o,64)==-EINVAL);
  assert(dptxport_call_get_drive_settings(&service,r,64,o,64)==-EINVAL);
 }
 puts("PASS: 40/48/64-byte requests, zero count, full 64-bit round trip, status/count offsets, truncation and oversized counts");
}
'''
with tempfile.TemporaryDirectory(prefix='dptx-drive-test-') as tmp:
 p=Path(tmp)/'test.c'; exe=Path(tmp)/'test';p.write_text(code)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
