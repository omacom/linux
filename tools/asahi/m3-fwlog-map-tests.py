#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check firmware-log and render reservations through the DRM fixed-node path."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'drivers/gpu/drm/asahi/'


def function(source, marker):
    start = source.index(marker)
    begin = source.index('{', start)
    end, depth = begin + 1, 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


RUST = r'''
#![allow(dead_code)]
mod m3_init_layout; mod m3_init_storage; mod m3_pass_layout; mod m3_shared_layout;
fn span(address:u64,size:usize)->(u64,u64) {
 let start=address & !0x3fff;let end=(address+size as u64+0x3fff)&!0x3fff;(start,end-start)
}
fn main(){
 for i in 0..m3_init_storage::COUNT {let a=m3_init_storage::allocation(i).unwrap();
  let (p,n)=span(a.address,a.size);println!("init:{i} {p:x} {n:x}");}
 for i in 0..m3_shared_layout::COUNT {let a=m3_shared_layout::allocation(i).unwrap();
  if a.space==m3_pass_layout::Space::Firmware {let (p,n)=span(a.address,a.size);println!("render:{i} {p:x} {n:x}");}}
 let (p,n)=span(0xfffffc200062bfe0,16);println!("initbm {p:x} {n:x}");
 for slot in 0..m3_pass_layout::SLOTS {for field in m3_pass_layout::FIELDS {
  let a=m3_pass_layout::board_allocation(slot,field,CLUSTERS).unwrap();
  if a.space==m3_pass_layout::Space::Firmware {let(p,n)=span(a.address,a.size);println!("pass:{slot}:{field:?} {p:x} {n:x}");}}}
}
'''

C = r'''
#include <assert.h>
#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
typedef uint64_t u64;
struct drm_mm;
struct drm_mm_node {u64 start,size,color,hole_size;unsigned long flags;int node_list;struct drm_mm *mm;};
struct drm_mm {void(*color_adjust)(struct drm_mm_node*,unsigned long,u64*,u64*);struct drm_mm_node occupied[2048],hole;unsigned count;};
#define unlikely(x) (x)
#define DRM_MM_NODE_ALLOCATED_BIT 0
#define __set_bit(b,p) (*(p)|=1ul<<(b))
#define list_add(a,b) ((void)0)
#define rm_hole(n) ((void)0)
#define add_hole(n) ((void)0)
#define save_stack(n) ((void)0)
#define __drm_mm_hole_node_start(n) ((n)->start)
/* This fixture computes holes from retained reservations instead of a red-black
 * tree. The production fixed-node function still checks the returned bounds
 * and publishes its node only after that check. */
static struct drm_mm_node *find_hole_addr(struct drm_mm *mm,u64 address,u64 size) {
 u64 start=0,end=UINT64_MAX;
 for(unsigned i=0;i<mm->count;i++) {
  struct drm_mm_node *n=&mm->occupied[i];u64 last=n->start+n->size;
  if(last<=address && last>start)start=last;
 }
 for(unsigned i=0;i<mm->count;i++) {
  struct drm_mm_node *n=&mm->occupied[i];
  if(n->start>=start && n->start<end)end=n->start;
 }
 mm->hole=(struct drm_mm_node){.start=start,.hole_size=end-start,.mm=mm};return &mm->hole;
}
static void drm_mm_interval_tree_add_node(struct drm_mm_node *hole,struct drm_mm_node *node) {
 assert(node->mm->count<2048);node->mm->occupied[node->mm->count++]=*node;
}
RESERVE
int main(int argc,char **argv){
 assert(argc==2);FILE *f=fopen(argv[1],"r");assert(f);struct drm_mm mm={0};char name[128];u64 address,size;
 while(fscanf(f,"%127s %"SCNx64" %"SCNx64,name,&address,&size)==3){
  struct drm_mm_node node={.start=address,.size=size};unsigned before=mm.count;
  int ret=drm_mm_reserve_node(&mm,&node);
  if(ret){fprintf(stderr,"reservation rejected %s address=%"PRIx64" size=%"PRIx64" errno=%d retained=%u\n",name,address,size,ret,mm.count);assert(mm.count==before);fclose(f);return 1;}
 }
 fclose(f);printf("PASS %u fixed firmware reservations including render buffer manager\n",mm.count);
 /* Adjacent spans remain valid; exact page and wrapping spans refuse. */
 struct drm_mm_node overlap={.start=address,.size=size};unsigned before=mm.count;
 assert(drm_mm_reserve_node(&mm,&overlap)==-ENOSPC && mm.count==before);
 struct drm_mm_node wrap={.start=UINT64_MAX-15,.size=32};assert(drm_mm_reserve_node(&mm,&wrap)==-ENOSPC && mm.count==before);
 return 0;
}
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ref', default='HEAD')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--expect-collision', action='store_true')
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    def source(path):
        return subprocess.check_output(['git', 'show', args.ref + ':' + path], cwd=ROOT)
    hashes = {}
    for name in ['m3_init_layout.rs', 'm3_init_storage.rs', 'm3_pass_layout.rs', 'm3_shared_layout.rs']:
        content = source(PREFIX + name)
        (args.out / name).write_bytes(content)
        hashes[PREFIX + name] = hashlib.sha256(content).hexdigest()
    mm = source('drivers/gpu/drm/drm_mm.c').decode()
    body = function(mm, 'int drm_mm_reserve_node(')
    (args.out / 'reserve.c').write_text(C.replace('RESERVE', body))
    subprocess.run(['cc', '-Wall', '-fsanitize=address,undefined', '-g', str(args.out / 'reserve.c'), '-o', str(args.out / 'reserve')], check=True)
    results = {}
    for clusters in [1, 2]:
        (args.out / 'main.rs').write_text(RUST.replace('CLUSTERS', str(clusters)))
        subprocess.run(['rustc', '--edition=2021', '-Awarnings', str(args.out / 'main.rs'), '-o', str(args.out / 'layouts')], check=True)
        spans = args.out / f'clusters-{clusters}.txt'
        spans.write_bytes(subprocess.check_output([str(args.out / 'layouts')]))
        result = subprocess.run([str(args.out / 'reserve'), str(spans)], capture_output=True, text=True,
                                preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
        (args.out / f'clusters-{clusters}.log').write_text(result.stdout + result.stderr)
        if args.expect_collision:
            assert result.returncode == 1 and 'reservation rejected render:29' in result.stderr and 'errno=-28' in result.stderr, result
        else:
            assert result.returncode == 0, result
        results[clusters] = {'exit': result.returncode, 'output': result.stdout + result.stderr}
    receipt = {'ref': subprocess.check_output(['git', 'rev-parse', args.ref], cwd=ROOT, text=True).strip(),
               'source_sha256': hashes, 'drm_mm_reserve_node_sha256': hashlib.sha256(body.encode()).hexdigest(),
               'controls': results, 'scope': 'Actual full Rust layout functions and actual C drm_mm_reserve_node body; controlled hole lookup/tree insertion replaces RB/list storage. Models fixed page reservations only, not full GPU startup or hardware.',
               'hardware': False}
    (args.out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
