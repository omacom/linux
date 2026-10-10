/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint8_t u8;typedef uint32_t u32;typedef uint64_t u64;
#define BIT(n) (1U<<(n))
#define GENMASK(h,l) ((~0U>>(31-(h)))&(~0U<<(l)))
#define FIELD_PREP(mask,v) (((u32)(v)<<__builtin_ctz(mask))&(mask))
#define U32_MAX UINT32_MAX
#define JOIN_(a,b) a##b
#define JOIN(a,b) JOIN_(a,b)
#define guard(x) __attribute__((unused)) void *JOIN(guard_,__LINE__)=
#define lockdep_assert_held(x) ((void)0)
#define dev_dbg(...) ((void)0)
#define dev_err(...) ((void)0)
#define EXPORT_SYMBOL_GPL(x)
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define APPLE_ATCPHY_MODE_USB4 1
#define APPLE_ATCPHY_MODE_TBT 2
#define resource_size(p) ((p)->size)
struct resource {u64 start,size;};
struct apple_atcphy {int lock,mode;void *dev,*np;
 struct {u8 *core;} regs;struct {struct resource *core;} res;
 bool tunnel_clock_on,tunnel_dual_stream,tunnel_routes_present;
 u8 tunnel_rate;unsigned tunnel_users;int dp_link_rate;};
struct phy {const void *ops;struct apple_atcphy *data;};
static int apple_atc_dp_phy_ops;
static const char *soc;
static unsigned poll_count,apb_count,stop_count,writes;
static int poll_fault=-1,apb_fault=-1,other_calls;
static struct apple_atcphy *phy_get_drvdata(struct phy *p){return p->data;}
static bool of_machine_is_compatible(const char *s){return !strcmp(soc,s);}
static bool apple_atc_tunnel_is_t6030(struct apple_atcphy *p){return of_machine_is_compatible("apple,t6030");}
static bool apple_atc_t602x_core_valid(void *p,u64 base,u64 size){return true;}
static void atcphy_restore_after_pd_off(struct apple_atcphy *p){}
static int atc_t8122_tunnel_stop(struct apple_atcphy *p){other_calls++;return 0;}
static int atc_t8122_tunnel_start(struct apple_atcphy *p,u8 rate){other_calls++;return 0;}
static void atc_tunnel_stop_t602x(struct apple_atcphy *p,unsigned dpin){other_calls++;}
static int atc_tunnel_set_t602x(struct apple_atcphy *p,unsigned dpin,u8 rate){other_calls++;return 0;}
static u32 readl(const void *p){u32 v;memcpy(&v,p,4);return v;}
static void writel(u32 value,void *p){writes++;memcpy(p,&value,4);}
static void core_clear32(struct apple_atcphy *p,unsigned off,u32 mask){writel(readl(p->regs.core+off)&~mask,p->regs.core+off);}
static void core_set32(struct apple_atcphy *p,unsigned off,u32 mask){writel(readl(p->regs.core+off)|mask,p->regs.core+off);}
static void core_mask32(struct apple_atcphy *p,unsigned off,u32 mask,u32 value){writel((readl(p->regs.core+off)&~mask)|(value&mask),p->regs.core+off);}
static void udelay(unsigned usec){}
static int atcphy_auspll_apb_command(struct apple_atcphy *p,u32 cmd){if(cmd==3){stop_count++;return 0;}return (int)apb_count++==apb_fault?-ETIMEDOUT:0;}
#define readl_poll_timeout(address,value,condition,interval,timeout) ({int r=(int)poll_count++==poll_fault?-ETIMEDOUT:0;(value)=~0U;assert(r||(condition));r;})
/* REGISTER_DEFINES */
struct device_node {const char *compatible;};
struct of_device_id {const char *compatible;};
struct apple_dpin_policy {int flow;};
#define APPLE_DPIN_PRE_POST 1
static struct apple_dpin_policy apple_dpin_disabled;
static bool of_match_node(const struct of_device_id *ids,const struct device_node *root){for(;ids->compatible;ids++)if(!strcmp(ids->compatible,root->compatible))return true;return false;}
/* POLICY_TABLE */
/* PRODUCTION_FUNCTIONS */
int main(int argc,char **argv){
 assert(argc==2);const char *name=argv[1];
 struct apple_dpin_policy m1={0},m2={APPLE_DPIN_PRE_POST};
 struct device_node root={"apple,t8112"};
 assert(apple_dpin_policy_select(&m1,&root,false)==&m1);
 assert(apple_dpin_policy_select(&m1,&root,true)==&m1);
 root.compatible="apple,t6020";assert(apple_dpin_policy_select(&m2,&root,false)==&apple_dpin_disabled);
 assert(apple_dpin_policy_select(&m2,&root,true)==&m2);
 root.compatible="apple,unknown";assert(apple_dpin_policy_select(&m1,&root,true)==&apple_dpin_disabled);
 soc="apple,t6000";
 if(!strcmp(name,"m2-admission"))soc="apple,t8112";
 if(!strcmp(name,"m1-admission"))soc="apple,t8103";
 if(!strcmp(name,"m1max-admission"))soc="apple,t6001";
 if(!strcmp(name,"m2pro-sequence"))soc="apple,t6020";
 if(!strcmp(name,"m3pro-sequence"))soc="apple,t6030";
 u8 regs[0x20000]={0};struct resource res={.start=0x703000000ULL,.size=0x20000};
 struct apple_atcphy d={.regs.core=regs,.res.core=&res,.mode=APPLE_ATCPHY_MODE_USB4,.tunnel_routes_present=true,.tunnel_dual_stream=true};
 struct phy phy={.ops=&apple_atc_dp_phy_ops,.data=&d};
 if(!strcmp(name,"first-poll-failure"))poll_fault=0;
 if(!strcmp(name,"lock-failure"))poll_fault=1;
 if(!strcmp(name,"first-command-failure"))apb_fault=0;
 if(!strcmp(name,"second-command-failure"))apb_fault=1;
 if(!strcmp(name,"busy-pll"))writel(AUSPLL_CLKOUT_MASTER_DRVR_EN,regs+AUSPLL_CLKOUT_MASTER);
 if(!strcmp(name,"busy-mode"))d.mode=0;
 unsigned before=writes;int ret=apple_atc_dp_tunnel_rate(&phy,0,0x14);
 if(strstr(name,"failure")||!strncmp(name,"busy-",5)){
  assert(ret&& !d.tunnel_users&&!d.tunnel_clock_on&&!d.tunnel_rate);
  if(poll_fault==1||apb_fault>=0)assert(stop_count==1);
  else assert(!stop_count&&writes==before);
 }else if(!strcmp(name,"m2pro-sequence")||!strcmp(name,"m3pro-sequence")){
  assert(!ret&&other_calls==1&&!d.tunnel_users&&!writes);
 }else{
  assert(!ret&&d.tunnel_clock_on&&d.tunnel_users==1&&d.tunnel_rate==0x14);
  if(!strcmp(name,"single-stop")){
   assert(!apple_atc_dp_tunnel_rate(&phy,0,0));assert(!d.tunnel_clock_on&&!d.tunnel_users&&stop_count==1);
  }else{
   unsigned first_writes=writes;
   assert(!apple_atc_dp_tunnel_rate(&phy,1,0x14)&&d.tunnel_users==3&&writes==first_writes);
   if(!strcmp(name,"rate-change"))assert(!apple_atc_dp_tunnel_rate(&phy,1,0x1e)&&d.tunnel_users==3&&d.tunnel_rate==0x1e);
   if(!strcmp(name,"force-stop")){atc_tunnel_stop_t8103(&d);assert(!d.tunnel_users&&!d.tunnel_clock_on&&stop_count==1);}
   else {
    unsigned stopped=!strcmp(name,"stop-first")?0:1,remaining=1-stopped;
    assert(!apple_atc_dp_tunnel_rate(&phy,stopped,0)&&d.tunnel_clock_on&&d.tunnel_users==BIT(remaining)&&!stop_count);
    assert(!apple_atc_dp_tunnel_rate(&phy,stopped,0)&&d.tunnel_clock_on&&!stop_count);
    assert(!apple_atc_dp_tunnel_rate(&phy,remaining,0)&&!d.tunnel_clock_on&&!d.tunnel_users&&stop_count==1);
    assert(!apple_atc_dp_tunnel_rate(&phy,remaining,0)&&stop_count==1);
   }
  }
 }
 assert(apple_atc_dp_tunnel_rate(&phy,2,0x14)==-EINVAL);
 assert(apple_atc_dp_tunnel_rate(NULL,0,0)==-EINVAL);
 return 0;
}
