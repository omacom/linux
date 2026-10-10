#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only OR MIT
"""Host controls for retained domains, wake IRQs, USB roles and country policy."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def function(source, name):
    match = re.search(r'^(?:static\s+)?(?:inline\s+)?(?:int|void|bool|struct ieee80211_channel \*)\s*' +
                      name + r'\([^;]*?\)\n\{', source, re.M | re.S)
    if not match:
        raise ValueError(name)
    end = source.index('{', match.start()) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[match.start():end]


PREFIX = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32; typedef int32_t s32;
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define lockdep_assert_held(x) ((void)0)
#define dev_err(...) ((void)0)
#define dev_warn(...) ((void)0)
#define dev_info_ratelimited(...) ((void)0)
#define WARN_ON_ONCE(x) ((void)(x))
#define spin_lock_irqsave(l,f) ((f)=0)
#define spin_unlock_irqrestore(l,f) ((void)(f))
#define PD_FLAG_DEV_LINK_ON 1
struct device { bool syscore,wakeup; int wake_irq; void *of_node; };
struct dockchannel { struct device *dev; int rx_irq; };
struct dev_pm_domain_list { unsigned num_pds; struct device **pd_devs; };
struct dev_pm_domain_attach_data { unsigned pd_flags; };
static int domain_count,attach_error,action_error,wakeup_error,irq_error;
static unsigned attach_calls,wakeup_calls,irq_calls,core_exits,role_exits,reset_calls;
static struct device pd0,pd1;static struct device *pd_devices[]={&pd0,&pd1};
static struct dev_pm_domain_list domains={2,pd_devices};
static void (*cleanup)(void *);static void *cleanup_data;
static int of_count_phandle_with_args(void*n,const char*a,const char*b){return domain_count;}
static int devm_pm_domain_attach_list(struct device*d,struct dev_pm_domain_attach_data*a,struct dev_pm_domain_list**l){attach_calls++;assert(a->pd_flags==PD_FLAG_DEV_LINK_ON);*l=&domains;return attach_error;}
static void dev_pm_syscore_device(struct device*d,bool v){d->syscore=v;}
static int devm_add_action_or_reset(struct device*d,void(*f)(void*),void*p){if(action_error){f(p);return action_error;}cleanup=f;cleanup_data=p;return 0;}
static int devm_device_init_wakeup(struct device*d){wakeup_calls++;if(!wakeup_error)d->wakeup=true;return wakeup_error;}
static int devm_pm_set_wake_irq(struct device*d,int i){irq_calls++;if(!irq_error)d->wake_irq=i;return irq_error;}
enum dwc3_apple_state {DWC3_APPLE_PROBE_PENDING,DWC3_APPLE_NO_CABLE,DWC3_APPLE_HOST,DWC3_APPLE_DEVICE,DWC3_APPLE_SUSPENDED};
struct dwc3 {int unused;};
struct dwc3_apple {struct device*dev;struct dwc3 dwc;int lock,reset;enum dwc3_apple_state state;bool fixed_hub;};
static int core_error,host_error,gadget_error,reset_error;
static int dwc3_apple_core_start(struct dwc3_apple*a,enum dwc3_apple_state s){return core_error;}
static void dwc3_apple_set_role(struct dwc3_apple*a,enum dwc3_apple_state s){}
static int dwc3_host_init(struct dwc3*d){return host_error;}
static int dwc3_gadget_init(struct dwc3*d){return gadget_error;}
static void dwc3_host_exit(struct dwc3*d){role_exits++;}
static void dwc3_gadget_exit(struct dwc3*d){role_exits++;}
static void dwc3_enable_susphy(struct dwc3*d,bool v){assert(v);}
static void dwc3_core_exit(struct dwc3*d){core_exits++;}
static int reset_control_assert(int r){reset_calls++;return reset_error;}
static u16 get_unaligned_le16(const u8*p){return p[0]|p[1]<<8;}
static u32 get_unaligned_le32(const u8*p){return p[0]|p[1]<<8|p[2]<<16|p[3]<<24;}
static void put_unaligned_le16(u16 v,u8*p){p[0]=v;p[1]=v>>8;}
static void put_unaligned_le32(u32 v,u8*p){p[0]=v;p[1]=v>>8;p[2]=v>>16;p[3]=v>>24;}
#define IEEE80211_CHAN_DISABLED 1
#define IEEE80211_CHAN_RADAR 2
#define IEEE80211_CHAN_NO_OFDM 4
#define IEEE80211_CHAN_NO_20MHZ 8
#define IEEE80211_CHAN_PSD 16
#define IEEE80211_CHAN_IR_CONCURRENT 32
#define WLAN_REASON_DEAUTH_LEAVING 3
#define __assign_bit(i,b,v) ((b)[(i)/64]=((b)[(i)/64]&~(1ULL<<((i)%64)))|((uint64_t)!!(v)<<((i)%64)))
#define for_each_set_bit(i,b,n) for((i)=0;(i)<(n);(i)++) if((b)[(i)/64]&(1ULL<<((i)%64)))
#define bitmap_zero(b,n) memset((b),0,8)
struct ieee80211_channel {unsigned flags,hw_value;int max_power;};
struct wiphy {void*priv;};struct net_device {int unused;};
struct regulatory_request {u8 alpha2[2];unsigned initiator;};
static unsigned rtnl_depth,wiphy_depth,schedules;
static void rtnl_lock(void){assert(!rtnl_depth++);}
static void rtnl_unlock(void){assert(rtnl_depth--==1);}
static void wiphy_lock(struct wiphy*w){assert(rtnl_depth&& !wiphy_depth++);}
static void wiphy_unlock(struct wiphy*w){assert(wiphy_depth--==1);}
struct mt7932 {struct ieee80211_channel channels[13],channels5[4];struct wiphy*wiphy;struct net_device*netdev;struct {struct device dev;}*pdev;struct mt7932_reg_snapshot reg_desired;unsigned reg_generation,response_lock,startup_work;bool reg_pending,stopping,interface_registered,connecting;int connect_error,assoc_start,assoc_done,discovery_done;uint64_t policy_disabled[1];};
static struct mt7932 *mt_from_wiphy(struct wiphy*w){return w->priv;}
static int mt7932_domain_5g_bw(void){return 0;}
static void netif_stop_queue(struct net_device*n){}
static void complete(int*c){}
static void schedule_work(unsigned*w){schedules++;}
'''

MAIN = r'''
int main(int argc,char**argv){
 assert(argc==2);struct device d={};struct dockchannel dc={.dev=&d,.rx_irq=42};
 if(!strcmp(argv[1],"wake")){
  assert(!dockchannel_init_wakeup(&dc)&&d.wakeup&&d.wake_irq==42);
  wakeup_error=-ENOMEM;assert(dockchannel_init_wakeup(&dc)==-ENOMEM&&irq_calls==1);
  wakeup_error=0;irq_error=-EINVAL;assert(dockchannel_init_wakeup(&dc)==-EINVAL);
 }else if(!strcmp(argv[1],"sep")){
  domain_count=1;assert(!sep_pm_keep_domains(&d)&&!attach_calls);
  domain_count=2;attach_error=-EAGAIN;assert(sep_pm_keep_domains(&d)==-EAGAIN&&!pd0.syscore);
  attach_error=0;assert(!sep_pm_keep_domains(&d)&&pd0.syscore&&pd1.syscore&&cleanup);
  cleanup(cleanup_data);assert(!pd0.syscore&&!pd1.syscore);
  action_error=-ENOMEM;assert(sep_pm_keep_domains(&d)==-ENOMEM&&!pd0.syscore&&!pd1.syscore);
 }else if(!strcmp(argv[1],"usb")){
  for(unsigned fixed=0;fixed<2;fixed++)for(unsigned role=DWC3_APPLE_HOST;role<=DWC3_APPLE_DEVICE;role++){
   struct dwc3_apple a={.dev=&d,.fixed_hub=fixed,.state=DWC3_APPLE_PROBE_PENDING};
   assert(!dwc3_apple_init(&a,role)&&d.syscore&&a.state==role);
   assert(!dwc3_apple_exit(&a)&&!d.syscore&&a.state==DWC3_APPLE_NO_CABLE);
   unsigned n=core_exits;assert(!dwc3_apple_exit(&a)&&core_exits==n);
   core_error=-EIO;assert(dwc3_apple_init(&a,role)==-EIO&&!d.syscore);core_error=0;
   host_error=gadget_error=-ENOMEM;n=core_exits;assert(dwc3_apple_init(&a,role)==-ENOMEM&&!d.syscore&&core_exits==n+1);host_error=gadget_error=0;
   assert(!dwc3_apple_init(&a,role)&&d.syscore);reset_error=-EIO;assert(dwc3_apple_exit(&a)==-EIO&&!d.syscore);reset_error=0;
  }
 }else if(!strcmp(argv[1],"regulatory")){
  struct mt7932 m={.reg_generation=7};struct wiphy w={.priv=&m};m.wiphy=&w;
  struct mt7932_policy p={};u8 tables[9][1020]={};
  for(unsigned i=0;i<9;i++){p.table[i+1]=tables[i];tables[i][4]=0;}
  tables[0][4]=8;tables[1][4]=5;tables[2][4]=4;
  for(unsigned i=0;i<17;i++){unsigned t=i<8?0:i<13?1:2,j=i<8?i:i<13?i-8:i-13;
   struct ieee80211_channel*c=mt_channel(&m,i);c->hw_value=i<13?i+1:36+(i-13)*4;c->max_power=20;
   memset(tables[t]+44+j*122,0xc4,122);tables[t][44+j*122]=c->hw_value;
   if(i!=10)tables[t][45+j*122]=1;
  }
  assert(!mt7932_policy_permits(&p,11)&&mt7932_policy_permits(&p,10)&&!mt7932_policy_permits(&p,165));
  struct regulatory_request request={.alpha2={'U','S'}};mt_regulatory_notify(&w,&request);m.reg_pending=false;
  unsigned generation=m.reg_generation;mt_policy_disable(&m,&p,generation-1);assert(!m.channels[10].flags&&!m.policy_disabled[0]);
  mt_policy_disable(&m,&p,generation);assert(m.channels[10].flags==1&&m.policy_disabled[0]==(1ULL<<10));
  struct mt7932_reg_snapshot reg=m.reg_desired;mt7932_policy_filter(&reg,&p);assert(reg.length==12+16*8&&reg.domain[8]==12&&reg.domain[9]==4);
  for(unsigned i=0;i<16;i++)assert(get_unaligned_le16(reg.domain+12+i*8)!=11);
  m.channels[10].flags=0;mt_regulatory_notify(&w,&request);assert(m.reg_generation==generation&&m.channels[10].flags==1);
  m.channels[10].flags=0;request.alpha2[0]='C';request.alpha2[1]='A';mt_regulatory_notify(&w,&request);assert(m.reg_generation==generation+1&&!m.policy_disabled[0]);
  m.stopping=true;unsigned n=m.reg_generation;request.alpha2[0]='U';mt_regulatory_notify(&w,&request);assert(m.reg_generation==n);
 }
 puts("PASS");return 0;
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--old-usb', action='store_true')
    parser.add_argument('--old-regulatory', action='store_true')
    parser.add_argument('--mutation', choices=['sep-syscore', 'wake-irq', 'stale-policy'])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    files = {
        'drivers/soc/apple/dockchannel.c': ['dockchannel_init_wakeup'],
        'drivers/soc/apple/pm_shim.c': ['sep_pm_release_domains', 'sep_pm_keep_domains'],
        'drivers/usb/dwc3/dwc3-apple.c': ['dwc3_apple_init', 'dwc3_apple_exit'],
        'drivers/net/wireless/mediatek/mt7932/startup.c': ['mt_channel', 'mt_policy_disable', 'mt_regulatory_notify'],
    }
    bodies = {}
    for path, names in files.items():
        source = (ROOT/path).read_text()
        for name in names:
            text = source
            if args.old_usb and path.endswith('dwc3-apple.c') or args.old_regulatory and name == 'mt_regulatory_notify':
                text = subprocess.check_output(['git', 'show', '990a45b609dd:'+path], cwd=ROOT, text=True)
            bodies[name] = function(text, name)
    header = (ROOT/'drivers/net/wireless/mediatek/mt7932/regulatory.h').read_text()
    at = PREFIX.index('struct mt7932 {')
    code = PREFIX[:at] + header + PREFIX[at:] + '\n'.join(bodies.values()) + MAIN
    if not args.old_usb:
        code = code.replace(',DWC3_APPLE_SUSPENDED', '')
    if args.mutation == 'sep-syscore':
        code = code.replace('dev_pm_syscore_device(list->pd_devs[i], true);', 'dev_pm_syscore_device(list->pd_devs[i], false);')
    if args.mutation == 'wake-irq':
        code = code.replace('return devm_pm_set_wake_irq(dockchannel->dev, dockchannel->rx_irq);', 'return 0;')
    if args.mutation == 'stale-policy':
        code = code.replace('generation != READ_ONCE(m->reg_generation)', 'false')
    source = args.output/'controls.c'; source.write_text(code)
    binary = args.output/'controls'
    subprocess.run(['cc', '-std=gnu11', '-g', '-Wall', '-Werror', '-Wno-unused-function',
                    '-Wno-unused-variable', '-fsanitize=address,undefined', '-fno-pie', '-no-pie',
                    str(source), '-o', str(binary)], check=True)
    def no_core():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    results = []
    for case in ['wake', 'sep', 'usb', 'regulatory']:
        run = subprocess.run([str(binary), case], capture_output=True, text=True, preexec_fn=no_core)
        results.append({'case': case, 'exit': run.returncode, 'stderr': run.stderr})
    receipt = {'bodies': {n: hashlib.sha256(b.encode()).hexdigest() for n,b in bodies.items()},
               'translation_sha256': hashlib.sha256(code.encode()).hexdigest(),
               'old_usb': args.old_usb, 'old_regulatory': args.old_regulatory,
               'mutation': args.mutation, 'results': results}
    (args.output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(results, indent=2))
    if any(x['exit'] for x in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
