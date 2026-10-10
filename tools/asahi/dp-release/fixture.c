/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32; typedef uint64_t u64; typedef uint8_t u8;
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define smp_load_acquire(p) (*(p))
#define smp_store_release(p,v) (*(p)=(v))
#define JOIN_(a,b) a##b
#define JOIN(a,b) JOIN_(a,b)
#define guard(x) __attribute__((unused)) void *JOIN(_guard_,__LINE__) =
#define scoped_guard(x,p) for (bool once=true; once; once=false)
#define lockdep_assert_held(x) ((void)0)
#define dev_warn(...) ((void)0)
#define dev_info(...) ((void)0)
#define dev_err(...) ((void)0)
#define IS_ERR(p) false
#define PTR_ERR(p) (-EIO)
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define to_delayed_work(w) container_of(w,struct delayed_work,work)
#define le32_to_cpu(v) (v)
#define TYPEC_STATE_SAFE 0
#define TYPEC_DP_STATE_A 10
#define TYPEC_DP_STATE_F 15
#define USB_TYPEC_DP_SID 0xff01
#define DP_STATUS_HPD_STATE 1
#define DP_STATUS_IRQ_HPD 2
#define TYPEC_THUNDERBOLT_SWITCH_OFF 0
#define TYPEC_PWR_MODE_USB 0
#define TYPEC_PWR_MODE_PD 1
#define TPS_STATUS_PLUG_PRESENT 1
#define TPS_STATUS_PLUG_UPSIDE_DOWN 2
#define TPS_DATA_STATUS_TBT_CONNECTION 4
#define CD321X_DATA_STATUS_USB4_CONNECTION 8
#define TPS_DATA_STATUS_USB2_CONNECTION 16
#define TPS_DATA_STATUS_USB3_CONNECTION 32
#define TPS_DATA_STATUS_DP_CONNECTION 64
#define TPS_DATA_STATUS_DP_PIN_ASSIGNMENT_MASK 128
#define CD321X_DATA_STATUS_HPD_LEVEL 256
#define TPS_DATA_STATUS_USB_DATA_ROLE 512
#define TPS_POWER_STATUS_PWROPMODE(v) (v)
#define TPS_STATUS_TO_UPSIDE_DOWN(v) ((v)&2)
#define TPS_STATUS_TO_TYPEC_PORTROLE(v) 0
#define TPS_STATUS_TO_TYPEC_VCONN(v) 0
#define TPS_STATUS_TO_TYPEC_DATAROLE(v) 0
#define CD321X_DEBOUNCE_DELAY_MS 20
#define system_freezable_wq 0
#define msecs_to_jiffies(v) (v)
#define connector_status_disconnected 0
#define connector_status_connected 1

enum usb_role {USB_ROLE_NONE,USB_ROLE_HOST,USB_ROLE_DEVICE};
enum typec_pwr_opmode {power_dummy};
enum typec_orientation {TYPEC_ORIENTATION_NONE,TYPEC_ORIENTATION_NORMAL,TYPEC_ORIENTATION_REVERSE};
struct work_struct {int unused;};
struct delayed_work {struct work_struct work;};
/* PM_HEADER */
struct typec_altmode {u32 svid;};
struct typec_displayport_data {u32 status,conf;};
struct typec_mux_state {struct typec_altmode *alt; int mode; void *data;};
struct typec_mux_dev {void *data;};
struct typec_thunderbolt_switch_data {int state;};
struct usb_pd_identity {int identity;};
struct typec_partner_desc {bool usb_pd; int accessory; struct usb_pd_identity *identity;};
#define TYPEC_ACCESSORY_NONE 0
struct apple_connector {bool connected; void *dcp;int bl_sync_wq;
 struct {unsigned possible_crtcs;} *port_encoder;unsigned candidate_crtcs;};
struct mux_control {int id;struct {struct mux_control *mux;unsigned controllers;} *chip;};
struct apple_epic_service;
struct phy;
struct dcp_fabric_session {u64 generation,cookie;};
struct apple_epic_service {void *cookie;struct {struct apple_dcp *dcp;} *ep;};
struct dptxport_apcall_set_tiled {u32 retcode;};
static unsigned long jiffies;
#define time_before(a,b) ((a)<(b))
#define cpu_to_le32(v) (v)
#define min(a,b) ((a)<(b)?(a):(b))
static u32 get_unaligned_le32(const void *p){const u8 *b=p;return b[0]|((u32)b[1]<<8)|((u32)b[2]<<16)|((u32)b[3]<<24);}
#define DPTX_TILE_HINT_LOC_X 0x08
#define DPTX_TILE_HINT_LOC_Y 0x0c
#define DPTX_TILE_HINT_TILES_H 0x30
#define DPTX_TILE_HINT_TILES_V 0x34
#define DPTX_TILE_HINT_WIDTH 0x38
#define DPTX_TILE_HINT_HEIGHT 0x3c
#define DPTX_TILE_HINT_MIN_SIZE 0x40
#define DRM_MODE_CONNECTOR_USB 1
#define MUX_IDLE_DISCONNECT -1
#define symbol_get(n) (&n)
#define symbol_put(n) ((void)0)
struct platform_device;
struct apple_dcp_typec_route;
struct apple_dcp {void *dev; bool external,external_native,external_link_ready;
    struct dptx_port {bool enabled,connected;void *service,*atcphy;bool tile_hint;u8 tiles_h,tiles_v,tile_x,tile_y;u32 unit;} dptxport[2];
    struct {bool active,ready,xbar_up,clock_ok;struct mux_control *xbar;int mux_state;u64 generation;int(*set_active)(void *,bool);void *binding;} split;
    struct {bool t6020_tunnel_flow;} hw;
    int hpd_mutex,typec_iomfb_hpd_ready; bool typec_cable_connected,typec_crtc_off;
    u64 typec_generation; struct delayed_work external_retry_wq,typec_reconnect_wq,placeholder_edid_wq;
    void *avep; struct apple_connector *connector,*typec_connector;
    int hdmi_hpd; bool active,tb_retiring; struct apple_dcp_typec_route *active_typec_route;
    int tb_lock;void *phy,*fixed_phy,*direct_xbar_up,*tb_dpin_ctx;bool dptx_tunnel,tb_clock_ok,ext_backlight;
    void *tb_dpin_set_active;unsigned dptx_dfp_port,dptx_phy,fixed_dptx_phy;
    u64 tb_generation;struct apple_connector *fixed_connector;
    int nr_typec_routes;struct {struct {int unused;} base;} *crtc;
    bool typec_follow_retiring,typec_follow_start,placeholder_retried;unsigned typec_reconnect_tries;u64 typec_follow_gen;
    u64 external_retry_generation;struct {bool valid;} mode_state;
    int fixed_connector_type,connector_type,fixed_mux_index;
    struct mux_control *xbar;bool fixed_route_selected;
    struct {void *phy;int dptx_phy;} typec_routes[1];};
struct apple_dcp_typec_port {bool applied_valid,hpd,dp_wanted,dp_hpd;
    void *applied_alt; int applied_mode; u32 applied_status,applied_conf;
    struct apple_dcp_typec_route *owner,*secondary_owner,*preferred_route,*target;struct apple_connector *connector,*secondary_connector;
    struct apple_dcp *split_dcp;unsigned long tile_hint_deadline;struct {int count;} routes; int link; void *connector_np;};
struct apple_dcp_typec_route {struct apple_dcp *dcp; struct apple_dcp_typec_port *port;
    bool tunnel,dual_stream,xbar_up,selected; int core,port_link,mux_index;
    struct typec_mux_dev *typec_mux;struct mux_control *xbar,*active_xbar,*dpin[2];
    unsigned tunnel_dpin,dptx_phy;void *phy;u64 tunnel_generation;};
struct dcp_typec_follow_slot {struct apple_dcp_typec_route *from,*to;
    struct apple_dcp_typec_port *port;bool tunnel;unsigned dpin;
    void *set_active,*binding;u64 tunnel_generation,attachment_generation;bool split;u64 split_generation;int(*split_set_active)(void *,bool);void *split_binding;};
struct dcp_typec_follow_context {struct dcp_typec_follow_slot slots[2];};
struct dcp_hdmi_reclaim_context {struct apple_dcp *from;struct apple_dcp_typec_route *owner,*target;};
struct dcp_fabric_reclaim_ops {int (*release)(void *);bool (*retained)(void *);void (*unplug)(void *);void (*connect_hdmi)(void *);int (*activate)(void *,bool);void (*publish)(void *,bool);void (*lost)(void *);};
struct dcp_fabric_follow_ops {int (*prepare)(void *,unsigned);int (*validate)(void *,unsigned);int (*detach)(void *,unsigned,bool);bool (*retained)(void *,unsigned,bool);int (*attach)(void *,unsigned,bool);void (*publish)(void *,unsigned,bool);void (*lost)(void *,unsigned);};
struct dcp_deactivate_context {struct apple_dcp_typec_port *port;struct apple_dcp_typec_route *owner;struct apple_dcp *dcp;};
struct tps6598x {void *data,*dev,*port,*psy,*partner; int lock,role_sw;u32 data_status;};
struct cd321x_status {u32 status,status_changed,data_status,data_status_changed,pwr_status;
    bool dp_sid_event,dp_sid_hpd_low,dp_sid_irq;struct usb_pd_identity partner_identity;
    struct {u32 status_rx;} dp_sid_status;};
struct cd321x {struct tps6598x tps;struct delayed_work update_work,resume_work;
    struct cd321x_pm_state pm;struct cd321x_status update_status;bool display_route_active;
    bool state_valid,dp_sid_valid,cur_partner_is_pd;struct typec_mux_state state;
    struct typec_altmode *port_altmode_dp;u32 dp_status,dp_conf;
    struct usb_pd_identity cur_partner_identity;void *connector_fwnode,*tbt_switch,*mux;};
struct dcp_tb_attach_context {unsigned dpin;bool active;u64 generation;int(*set_active)(void *,bool);void *binding;};
static int tipd_sn201202x_data,other_tipd_data;
static int dcp_typec_fabric_lock,dcp_tb_handoff_lock,dcp_dual_stream_routes;
static int binding_drains;
static int preselect_error,source_error,connect_error,clock_calls,clock_error;
static unsigned clock_dpin,clock_rate;
static int hpd_error,release_error,hpd_calls,release_calls,crossbar_calls;
static int role_changes,safe_changes,orientation_changes,tbt_changes,queues,connect_calls;
static int deactivations,rebalance_calls,freed_ports,unregisters;
static int xbar_error,xbar_selections,xbar_deselections,hdmi_reinits,hdmi_errors,reconnects,attachment_changes;
static int sink_irq_error=-EIO,hdmi_level;
static int unplug_calls,move_calls,publish_calls,lost_calls,restore_count;
static unsigned restore_order[2];
static int detach_fault=-1,attach_fault=-1,destination_fault=-1;
static bool detached_error,detached[2],destination_owned[2];
static bool keep_order,route_available=true;
static struct apple_dcp *first_dcp;
static struct typec_mux_dev *current_mux;
static struct apple_dcp_typec_route *spare_route;
static int dcp_typec_route_set(struct typec_mux_dev *,struct typec_mux_state *);
void dcp_fabric_hdmi_retry(struct apple_dcp *);
static void mutex_lock(int *p) {} static void mutex_unlock(int *p) {}
static void dcpext_scanout_invalidate(struct apple_dcp *d) {}
static int dptxport_release_display(void *s) { release_calls++;return release_error; }
static int dptxport_set_hpd(void *s,bool hpd) {assert(!hpd);hpd_calls++;return hpd_error;}
static int dcp_direct_crossbar_link(struct apple_dcp *d,bool up){assert(!up);crossbar_calls++;return 0;}
static bool dcp_is_typec_output(struct apple_dcp *d){return true;}
static struct apple_dcp *platform_get_drvdata(void *p){return p;}
static void *to_platform_device(void *p){return p;}
static void reinit_completion(int *c){}
static void disconnected_hpd_event(struct apple_connector *c){if(c)c->connected=false;}
static void av_service_disconnect(struct apple_dcp *d){}
static void cancel_delayed_work(struct delayed_work *w){}
static void cancel_delayed_work_sync(struct delayed_work *w){}
static struct apple_dcp_typec_route *typec_mux_get_drvdata(struct typec_mux_dev *m){return m->data;}
static bool dcp_typec_keep_order(void){return keep_order;}
static struct apple_dcp_typec_route *dcp_typec_rebalance_locked(void *a,int b){rebalance_calls++;return NULL;}
static int mux_control_deselect(struct mux_control *m){xbar_deselections++;return xbar_error;}
static int mux_control_select(struct mux_control *m,int s){xbar_selections++;return 0;}
static int dcp_dpxbar_preselect(struct mux_control *m,int s){return s==MUX_IDLE_DISCONNECT?0:preselect_error;}
static int dcp_dpxbar_tunnel_select_source(struct mux_control *m,int s){return s==-1?0:source_error;}
static int apple_atc_dp_tunnel_rate(void *p,unsigned dpin,unsigned rate){clock_calls++;clock_dpin=dpin;clock_rate=rate;return clock_error;}
static int dcp_dpxbar_link(struct mux_control *m,bool up){crossbar_calls++;return 0;}
static bool of_machine_is_compatible(const char *s){return false;}
static bool dcp_modes_end_typec(struct apple_dcp *d,struct apple_dcp_typec_route *r){deactivations++;return false;}
static bool dcp_typec_dual_stream(void){return false;}
static void apple_connector_set_pipeline(struct apple_connector *c,void *p){c->dcp=p;}
static void schedule_work(int *w){}

static void dcp_typec_pipeline_freed(void){}
static int gpiod_get_value_cansleep(int p){return hdmi_level;}
static int dcp_dptx_connect(struct apple_dcp *,u32);
static struct dcp_fabric_session dcp_session_locked(struct apple_dcp *d){return (struct dcp_fabric_session){1,d->tb_generation};}
static int dcp_dptx_connect_session(struct apple_dcp *d,u32 p,struct dcp_fabric_session session,bool cable,bool recovery){connect_calls++;if(!connect_error)d->dptxport[p].connected=true;return p?connect_error:0;}
static int dcp_dptx_connect_oob(void *d,int p){connect_calls++;return 0;}
static struct apple_dcp_typec_route *dcp_typec_free_route(struct apple_dcp_typec_port *p){return route_available?spare_route:NULL;}


static int dcp_dptx_recover_irq(struct apple_dcp *d){return 0;}
static void dcp_retrain_oob(struct apple_connector *c){}
static void typec_mux_unregister(struct typec_mux_dev *m){unregisters++;}
static void dcp_tb_binding_drain(struct apple_dcp *d){binding_drains++;}
static void list_del(int *l){}
static void atomic_dec(int *p){(*p)--;}
static bool list_empty(void *l){return true;}
static void of_node_put(void *p){}
static void kfree(void *p){
    struct apple_dcp_typec_port *port=p;
    assert(!port->owner&&!port->secondary_owner&&!port->preferred_route);
    freed_ports++;
}
static int typec_mux_set(void *m,struct typec_mux_state *s){return dcp_typec_route_set(m,s);}
static enum usb_role usb_role_switch_get_role(int r){return USB_ROLE_HOST;}
static int usb_role_switch_set_role(int r,enum usb_role role){role_changes++;return 0;}
static int typec_thunderbolt_switch_set(void *s,struct typec_thunderbolt_switch_data *d){tbt_changes++;return 0;}
static void drm_connector_oob_hotplug_event(void *p,int s){}
static void typec_unregister_partner(void *p){}
static int typec_set_mode(void *p,int m){safe_changes++;struct typec_mux_state s={.mode=m};return typec_mux_set(current_mux,&s);}
static void typec_set_pwr_opmode(void *p,int m){}
static void typec_set_pwr_role(void *p,int m){}
static void typec_set_vconn_role(void *p,int m){}
static void typec_set_data_role(void *p,int m){}
static void typec_set_orientation(void *p,int m){orientation_changes++;}
static void power_supply_changed(void *p){}
static void *typec_register_partner(void *p,struct typec_partner_desc *d){return (void *)1;}
static void typec_partner_set_identity(void *p){}
static void cd321x_dp_sid_replay(struct cd321x *c,struct cd321x_status *s){}
static int cd321x_typec_update_mode(struct tps6598x *t,struct cd321x_status *s,bool *busy){*busy=false;return 0;}
static void mod_delayed_work(int q,struct delayed_work *w,int delay){queues++;}
static void dcp_modes_begin_attachment(struct apple_dcp *d){attachment_changes++;}
static void apple_connector_edid_set_live(struct apple_connector *c,bool live){}
static bool dcp_typec_narrows(struct apple_dcp *d){return false;}
static unsigned drm_crtc_index(void *p){return 0;}
static unsigned dcp_fabric_connector_mask(bool a,bool b,bool c,unsigned d,unsigned e){return e;}
static bool dcp_fabric_movable(int *a,int *b){return a&&a!=b;}
static char *dev_name(void *p){return "dcp";}
static int dcp_rebalance_deactivate_ops;
static bool dcp_fabric_run_deactivate(void *ops,struct dcp_deactivate_context *ctx);
static void dcp_hdmi_connect_failed(struct apple_dcp *d,int ret){hdmi_errors=ret;}
static int dcp_fixed_hdmi_reinit_locked(struct apple_dcp *d,const char *s){hdmi_reinits++;return 0;}
static int dcp_fixed_output_select(struct apple_dcp *d){xbar_selections++;return 0;}
static bool iomfb_v14_7_external_release(struct apple_dcp *d){return true;}
static bool iomfb_v14_7_external_failed(struct apple_dcp *d){return false;}
static bool dcp_external_crtc_showing(struct apple_dcp *d){return false;}
static void dcp_mode_set_valid(void *s,bool v){}
static void dcp_mode_invalidate(void *s){}
static void dcp_queue_hotplug(struct apple_connector *c){}
static void dcp_queue_typec_reconnect(struct apple_dcp *d,int delay){reconnects++;}
static int dptxport_sink_irq(struct apple_epic_service *s){return sink_irq_error;}
static struct mux_control *dcp_typec_tunnel_ctl(struct apple_dcp_typec_route *r,unsigned i){return r->xbar;}
static void dcp_tunnel_prepare(struct apple_dcp_typec_route *r,struct mux_control *m){}
static u64 dcp_modes_transfer_begin(struct apple_dcp *d){return 1;}


static int dcp_typec_route_deactivate(struct apple_dcp_typec_route *);
static int dcp_tb_split_teardown_locked(struct apple_dcp_typec_port *,bool);
static int dcp_tb_split_join_locked(struct apple_dcp_typec_port *,struct apple_dcp_typec_route *,struct mux_control *,u64,int(*)(void *,bool),void *);
/* PRODUCTION_FUNCTIONS */
static bool dcp_fabric_run_deactivate(void *ops,struct dcp_deactivate_context *ctx){
    int ret=dcp_typec_route_deactivate(ctx->owner);
    if(!ret)ctx->port->owner=NULL;
    return !!ret;
}

static int reclaim_release_adapter(void *ctx){
    int ret=dcp_reclaim_release(ctx);
    if(detached_error){dcp_typec_route_deactivate(((struct dcp_hdmi_reclaim_context *)ctx)->owner);((struct dcp_hdmi_reclaim_context *)ctx)->owner->port->owner=NULL;return -EIO;}
    return ret;
}
static void reclaim_unplug_adapter(void *ctx){unplug_calls++;}
static void reclaim_hdmi_adapter(void *ctx){move_calls++;}
static int reclaim_activate_adapter(void *ctx,bool restore){restore_count+=restore;move_calls+=!restore;return 0;}
static void reclaim_publish_adapter(void *ctx,bool restore){publish_calls++;}
static void reclaim_lost_adapter(void *ctx){lost_calls++;}
static int follow_prepare_adapter(void *ctx,unsigned i){return 0;}
static int follow_validate_adapter(void *ctx,unsigned i){return 0;}
static int follow_detach_adapter(void *ctx,unsigned i,bool destination){
    struct dcp_typec_follow_context *c=ctx;
    struct apple_dcp_typec_route *r=destination?c->slots[i].to:c->slots[i].from;
    if(destination&&(int)i==destination_fault)return -EIO;
    release_error=!destination&&(int)i==detach_fault?-EIO:0;
    int ret=dcp_follow_detach(ctx,i,destination);
    if(!ret){if(destination)destination_owned[i]=false;else detached[i]=true;}
    assert(ret||!r->selected);
    return ret;
}
static int follow_attach_adapter(void *ctx,unsigned i,bool restore){
    struct dcp_typec_follow_context *c=ctx;
    struct apple_dcp_typec_route *r=restore?c->slots[i].from:c->slots[i].to;
    if(restore){assert(!dcp_follow_owned(c->slots[i].from)&&!dcp_follow_owned(c->slots[i].to));restore_order[restore_count++]=i;}
    else if((int)i==attach_fault)return -EIO;
    int ret=dcp_follow_attach(ctx,i,restore);
    if(!ret)destination_owned[i]=!restore;
    return ret;
}
static void follow_publish_adapter(void *ctx,unsigned i,bool restore){publish_calls++;}
static void follow_lost_adapter(void *ctx,unsigned i){lost_calls++;}

static int tile_active(void *binding,bool active){return 0;}
static void put32(u8 *b,unsigned offset,u32 value){for(unsigned i=0;i<4;i++)b[offset+i]=value>>(8*i);}
int main(int argc,char **argv)
{
    assert(argc==2);const char *name=argv[1];
    struct typec_altmode alt={.svid=USB_TYPEC_DP_SID};
    struct apple_connector con={.connected=true};
    struct mux_control xbar={0};
    struct apple_dcp d={.dev=&d,.external=true,.external_native=true,.connector=&con,
        .typec_connector=&con,.typec_cable_connected=true,.dptxport={{true,true,&d}},.fixed_connector_type=DRM_MODE_CONNECTOR_USB};
    con.dcp=&d;
    struct apple_dcp_typec_port p={.hpd=true,.dp_wanted=true,.dp_hpd=true,.routes={1},.connector=&con};
    struct typec_mux_dev mux={0};
    struct apple_dcp_typec_route route={.dcp=&d,.port=&p,.typec_mux=&mux,.xbar=&xbar,.selected=true};
    struct apple_dcp other={.dev=&other};
    struct apple_dcp_typec_route not_owner={.dcp=&other,.port=&p};
    p.owner=p.preferred_route=&route;d.active_typec_route=&route;mux.data=&route;
    first_dcp=&d;current_mux=&mux;spare_route=&route;
    struct cd321x c={.tps={.data=&tipd_sn201202x_data,.partner=(void *)1},
        .display_route_active=true,.state_valid=true,.state={.alt=&alt,.mode=TYPEC_DP_STATE_A},
        .port_altmode_dp=&alt,.dp_status=DP_STATUS_HPD_STATE|DP_STATUS_IRQ_HPD,.mux=&mux};
    c.pm.phase=CD321X_PM_RUNNING;c.update_status.status_changed=TPS_STATUS_PLUG_PRESENT;
    if(!strncmp(name,"tile-",5)){
        d.external=d.external_native=false;d.phy=&d;d.dptx_tunnel=true;
        d.dptxport[1].enabled=true;d.dptxport[1].service=&other;
        route.tunnel=true;route.tunnel_generation=d.tb_generation=7;
        d.dptxport[0].tile_hint=true;d.dptxport[0].tiles_h=2;d.dptxport[0].tiles_v=1;
        route.dpin[1]=&xbar;
        if(!strncmp(name,"tile-parent-connect-",20)){
            d.split.active=true;d.split.ready=true;
            if(strstr(name,"failure"))connect_error=-EIO;
            int ret=dcp_dptx_connect(&d,0);
            assert(ret==connect_error&&connect_calls==2);
        }else if(!strncmp(name,"tile-main-release-",18)){
            if(strstr(name,"hpd"))hpd_error=-ETIMEDOUT;
            if(strstr(name,"failure"))release_error=-EIO;
            int ret=dcp_tb_release_locked(&p,0);
            if(hpd_error||release_error)assert(ret&&p.owner==&route&&route.selected&&!binding_drains&&!xbar_deselections);
            else assert(!ret&&!p.owner&&!route.selected&&binding_drains==1);
        }else if(!strncmp(name,"tile-hint-",10)){
            u8 payload[64]={0};struct dptxport_apcall_set_tiled reply={0};
            struct apple_epic_service service={.cookie=&d.dptxport[0]};
            put32(payload,0x30,2);put32(payload,0x34,1);put32(payload,0x38,5120);put32(payload,0x3c,2880);
            if(!strcmp(name,"tile-hint-location"))put32(payload,8,2);
            if(!strcmp(name,"tile-hint-many"))put32(payload,0x30,256);
            if(!strcmp(name,"tile-hint-overflow")){put32(payload,0x30,0x80000002);put32(payload,0x34,2);}
            if(!strcmp(name,"tile-hint-zero-size"))put32(payload,0x38,0);
            if(!strcmp(name,"tile-hint-single"))put32(payload,0x30,1);
            int ret=dptxport_call_set_tiled_display_hint(&service,payload,!strcmp(name,"tile-hint-short")?63:64,&reply,sizeof(reply));
            assert(!ret&&reply.retcode==1);
            assert(d.dptxport[0].tile_hint==!strcmp(name,"tile-hint-valid"));
        }else if(!strncmp(name,"tile-follow-",12)){
            struct dcp_typec_follow_slot slot={.port=&p,.tunnel=true,.split=true,.dpin=0,.tunnel_generation=7,.split_generation=8,.split_set_active=tile_active};
            p.owner=NULL;d.active_typec_route=NULL;route.selected=false;
            if(!strcmp(name,"tile-follow-source-failure"))source_error=-EIO;
            if(!strcmp(name,"tile-follow-preselect-failure"))preselect_error=-ETIMEDOUT;
            if(!strcmp(name,"tile-follow-main-release-failure"))release_error=-EIO;
            int ret=dcp_follow_activate(&route,&slot);
            if(source_error||preselect_error)assert(ret&&(p.owner==NULL)&&!route.selected&&!d.split.active&&!p.split_dcp&&!release_calls);
            else if(release_error)assert(ret&&!p.owner&&!route.selected&&!d.split.active&&!p.split_dcp);
            else assert(!ret&&p.owner==&route&&route.selected&&p.split_dcp==&d&&d.split.active&&d.split.ready);
        }else if(!strcmp(name,"tile-rate-stop")||!strcmp(name,"tile-rate-error")){
            d.split.active=true;d.split.xbar_up=true;d.split.xbar=&xbar;d.split.clock_ok=true;
            if(strstr(name,"error"))clock_error=-EIO;
            int ret=dcp_tunnel_set_rate(&d,(struct phy *)&d,1,0);
            assert(ret==clock_error&&clock_calls==1&&clock_dpin==1&&!clock_rate&&!d.split.clock_ok);
        }else if(!strncmp(name,"tile-teardown-",14)||!strncmp(name,"tile-park-",10)){
            p.split_dcp=&d;d.split.active=d.split.ready=true;d.split.xbar=&xbar;d.split.set_active=tile_active;d.split.binding=&p;d.dptxport[1].connected=true;
            if(strstr(name,"hpd"))hpd_error=-ETIMEDOUT;
            if(strstr(name,"release"))release_error=-EIO;
            bool force=strstr(name,"remove")!=NULL;int ret;
            if(!strncmp(name,"tile-park-",10))ret=dcp_dptx_park(&d);else ret=dcp_tb_split_teardown_locked(&p,force);
            if((hpd_error||release_error)&&!force)assert(ret&&p.split_dcp==&d&&d.split.active&&d.split.binding==&p&&!clock_calls&&!xbar_deselections);
            else if(!strncmp(name,"tile-park-",10))assert(!ret&&!d.dptxport[0].connected&&!d.dptxport[1].connected);
            else assert(!ret&&!p.split_dcp&&!d.split.active&&!d.split.binding&&!d.split.xbar&&clock_calls==1&&clock_dpin==1);
        }else{
            struct dcp_tb_attach_context req={.dpin=1,.active=true,.generation=8,.set_active=tile_active,.binding=&p};
            if(!strcmp(name,"tile-split-connect-failure"))connect_error=-EIO;
            if(!strcmp(name,"tile-split-retained-connect-failure")){connect_error=-EIO;release_error=-ETIMEDOUT;d.dptxport[1].connected=true;}
            if(!strcmp(name,"tile-split-unsupported-connect"))connect_error=-EOPNOTSUPP;
            if(!strcmp(name,"tile-split-source-failure"))source_error=-EIO;
            if(!strcmp(name,"tile-split-preselect-failure"))preselect_error=-ETIMEDOUT;
            if(!strcmp(name,"tile-split-no-hint")){d.dptxport[0].tile_hint=false;p.tile_hint_deadline=0;}
            if(!strcmp(name,"tile-split-wait-hint")){d.dptxport[0].tile_hint=false;p.tile_hint_deadline=10;}
            int ret=dcp_tb_split_locked(&p,&req);
            if(!strcmp(name,"tile-split-no-hint"))assert(ret==-EOPNOTSUPP&&!p.split_dcp&&!connect_calls);
            else if(!strcmp(name,"tile-split-wait-hint"))assert(ret==-ENODEV&&!p.split_dcp&&!connect_calls);
            else if(!strcmp(name,"tile-split-retained-connect-failure")){
                assert(ret==-ETIMEDOUT&&p.split_dcp==&d&&d.split.active&&!d.split.ready);
                assert(dcp_tb_split_locked(&p,&req)==-EAGAIN);
                req.active=false;release_error=0;assert(!dcp_tb_split_locked(&p,&req)&&!p.split_dcp&&p.owner==&route);
            }
            else if(connect_error||source_error||preselect_error)assert(ret&&ret!=-EOPNOTSUPP&&!p.split_dcp&&!d.split.active&&p.owner==&route&&route.selected);
            else {
                assert(!ret&&p.split_dcp==&d&&d.split.ready&&d.dptxport[1].connected&&p.owner==&route);
                assert(!dcp_tb_split_locked(&p,&req));
                req.generation=9;assert(dcp_tb_split_locked(&p,&req)==-ESTALE);req.generation=8;
                req.active=false;assert(!dcp_tb_split_locked(&p,&req)&&!p.split_dcp&&p.owner==&route);
            }
        }
        return 0;
    }
    if(!strcmp(name,"release-failure")||!strcmp(name,"release-repeat")||!strcmp(name,"safe-release-failure")||!strcmp(name,"remove-release-failure"))release_error=-EIO;
    if(!strcmp(name,"hpd-failure")||!strcmp(name,"remove-hpd-failure"))hpd_error=-ETIMEDOUT;
    if(!strcmp(name,"invalid-cache-repeat")){c.state_valid=false;release_error=-EIO;}
    if(!strcmp(name,"owner-route"))mux.data=&not_owner;
    if(!strcmp(name,"legacy-controller"))c.tps.data=&other_tipd_data;
    if(!strcmp(name,"legacy-dcp"))d.external=d.external_native=false;
    if(!strcmp(name,"suspended"))c.pm.phase=CD321X_PM_PREPARED;
    if(!strcmp(name,"retry-exhaustion"))release_error=-EIO;
    if(strstr(name,"-hpd-failure"))hpd_error=-ETIMEDOUT;
    if(strstr(name,"-release-failure"))release_error=-EIO;
    if(!strcmp(name,"remove-crossbar-failure"))xbar_error=-EIO;
    if(!strcmp(name,"no-route")){c.display_route_active=false;p.owner=NULL;p.hpd=false;}
    if(!strcmp(name,"tunnel")||!strcmp(name,"remove-tunnel"))route.tunnel=true;
    if(!strncmp(name,"reclaim-",8)){
        struct dcp_hdmi_reclaim_context ctx={.from=&d,.owner=&route};
        struct dcp_fabric_reclaim_ops ops={.release=reclaim_release_adapter,.retained=dcp_reclaim_retained,.unplug=reclaim_unplug_adapter,.connect_hdmi=reclaim_hdmi_adapter,.activate=reclaim_activate_adapter,.publish=reclaim_publish_adapter,.lost=reclaim_lost_adapter};
        if(!strcmp(name,"reclaim-retained"))release_error=-EIO;
        if(!strcmp(name,"reclaim-released-error")||!strcmp(name,"reclaim-null-released-error"))detached_error=true;
        if(strstr(name,"null-")){ops.retained=NULL;if(!detached_error)release_error=-EIO;}
        int ret=dcp_fabric_reclaim_execute(&ops,&ctx);
        if(release_error&&ops.retained)assert(ret==-EIO&&p.owner==&route&&!unplug_calls&&!move_calls&&!restore_count&&!lost_calls&&!publish_calls);
        else if(release_error)assert(ret==-EIO&&unplug_calls==1&&restore_count==1&&publish_calls==1);
        else if(detached_error)assert(ret==-EIO&&unplug_calls==1&&restore_count==1&&publish_calls==1&&!lost_calls);
        else assert(!ret&&unplug_calls==1&&move_calls==2&&publish_calls==1&&!restore_count);
    }else if(!strncmp(name,"follow-executor-",16)){
        struct apple_dcp d1={.dev=&d1},t0={.dev=&t0},t1={.dev=&t1};
        struct apple_dcp_typec_port p1={0};
        struct apple_dcp_typec_route from1={.dcp=&d1,.port=&p1,.selected=true},to0={.dcp=&t0,.port=&p},to1={.dcp=&t1,.port=&p1};
        d1.active_typec_route=&from1;p1.owner=&from1;
        struct dcp_typec_follow_context ctx={.slots={{.from=&route,.to=&to0,.port=&p},{.from=&from1,.to=&to1,.port=&p1}}};
        struct dcp_fabric_follow_ops ops={.prepare=follow_prepare_adapter,.validate=follow_validate_adapter,.detach=follow_detach_adapter,.retained=dcp_follow_retained,.attach=follow_attach_adapter,.publish=follow_publish_adapter,.lost=follow_lost_adapter};
        unsigned count=1;
        if(!strcmp(name,"follow-executor-retained"))detach_fault=0;
        if(!strcmp(name,"follow-executor-second-retained")){count=2;detach_fault=1;d1.dptxport[0].enabled=d1.dptxport[0].connected=true;}
        if(!strcmp(name,"follow-executor-destination-retained")){count=2;attach_fault=1;destination_fault=0;t0.dptxport[0].enabled=t0.dptxport[0].connected=true;}
        if(!strcmp(name,"follow-executor-null-callback")){count=2;attach_fault=1;ops.retained=NULL;}
        if(!strcmp(name,"follow-executor-reverse-restore")){count=2;attach_fault=0;}
        int ret=dcp_fabric_follow_execute(&ops,&ctx,count);
        assert(ret==-EIO&&!lost_calls);
        if(detach_fault==0)assert(p.owner==&route&&!restore_count&&!publish_calls);
        if(detach_fault==1)assert(p1.owner==&from1&&restore_count==1&&restore_order[0]==0&&!destination_owned[0]);
        if(destination_fault==0)assert(p.owner==&to0&&destination_owned[0]&&p1.owner==&from1&&restore_count==1&&publish_calls==2);
        if(!ops.retained)assert(restore_count==2&&restore_order[0]==0&&restore_order[1]==1&&publish_calls==2);
        if(!strcmp(name,"follow-executor-reverse-restore"))assert(restore_count==2&&restore_order[0]==1&&restore_order[1]==0&&publish_calls==2);
    }else if(!strcmp(name,"follow-restore-occupied")){
        struct dcp_typec_follow_context ctx={.slots={{.from=&route,.to=&not_owner,.port=&p}}};
        d.active_typec_route=&not_owner;
        assert(dcp_follow_attach(&ctx,0,true)==-EBUSY);
        assert(!release_calls&&!xbar_selections&&!xbar_deselections&&!attachment_changes);
    }else if(!strncmp(name,"activate-",9)){
        struct mux_control fixed={0};d.xbar=&fixed;d.fixed_route_selected=true;
        p.owner=NULL;d.active_typec_route=NULL;
        int ret=dcp_typec_route_activate(&route,&xbar);
        if(release_error)assert(ret==-EIO&&!xbar_selections&&!xbar_deselections&&!attachment_changes&&d.fixed_route_selected&&!d.active_typec_route&&d.dptxport[0].connected);
        else assert(!ret&&xbar_selections==1&&xbar_deselections==1&&d.active_typec_route==&route);
    }else if(!strncmp(name,"rebalance-",10)){
        p.target=&not_owner;
        bool ret=dcp_rebalance_deactivate(NULL,&p);
        if(hpd_error||release_error)assert(ret&&p.owner==&route&&p.hpd&&!deactivations&&!xbar_deselections);
        else assert(!ret&&!p.owner&&!p.hpd&&deactivations==1);
    }else if(!strncmp(name,"follow-",7)){
        int ret=dcp_follow_release(&route);
        if(hpd_error||release_error)assert(ret&&p.owner==&route&&d.typec_connector==&con&&!deactivations&&!xbar_deselections&&!attachment_changes);
        else assert(!ret&&!p.owner&&!d.active_typec_route&&deactivations==1);
    }else if(!strncmp(name,"hdmi-",5)){
        d.active_typec_route=NULL;d.hdmi_hpd=1;hdmi_level=1;
        dcp_fabric_hdmi_retry(&d);
        if(release_error)assert(!hdmi_reinits&&!xbar_selections&&!connect_calls&&hdmi_errors==-EIO);
        else assert(hdmi_reinits==1&&xbar_selections==1&&connect_calls==1);
    }else if(!strncmp(name,"native-retry-",13)){
        d.external_retry_generation=d.typec_generation;
        dcp_external_retry_work(&d.external_retry_wq.work);
        if(hpd_error||release_error)assert(!reconnects&&d.dptxport[0].connected&&!crossbar_calls);
        else assert(reconnects==1&&!d.dptxport[0].connected);
    }else if(!strncmp(name,"sink-irq-",9)){
        dcp_external_sink_irq(&d);
        if(release_error)assert(!connect_calls&&d.dptxport[0].connected&&!crossbar_calls);
        else assert(connect_calls==1&&!d.dptxport[0].connected);
    }else if(!strcmp(name,"retry-exhaustion")){
        cd321x_update_work(&c.update_work.work);
        for(int i=0;i<CD321X_RESUME_ATTEMPTS;i++){
            assert(cd321x_pm_begin_read(&c.pm));cd321x_pm_snapshot_ready(&c.pm);
            cd321x_update_work(&c.update_work.work);
        }
        assert(c.pm.phase==CD321X_PM_STALE&&!role_changes&&!safe_changes&&p.owner==&route);
        assert(release_calls==1+CD321X_RESUME_ATTEMPTS&&queues==CD321X_RESUME_ATTEMPTS);
    }else if(!strcmp(name,"suspended")){
        cd321x_update_work(&c.update_work.work);
        assert(!hpd_calls&&!release_calls&&!role_changes&&!safe_changes&&!orientation_changes);
    }else if(!strncmp(name,"remove-",7)){
        if(!strcmp(name,"remove-secondary")){p.secondary_owner=&route;p.owner=NULL;}
        dcp_typec_route_unregister(&route);
        assert(!p.owner&&!p.secondary_owner&&!p.preferred_route);
        assert(!d.active_typec_route&&!d.typec_connector);
        assert(freed_ports==1&&unregisters==1&&deactivations==1);
    } else if(!strncmp(name,"safe-",5)){
        struct typec_mux_state state={.mode=TYPEC_STATE_SAFE};
        int ret=dcp_typec_route_set(&mux,&state);
        if(release_error){assert(ret==-EIO&&p.owner==&route&&p.hpd&&p.dp_hpd&&p.dp_wanted&&!p.applied_valid);assert(!deactivations&&!crossbar_calls);}
        else assert(!ret&&!p.owner&&!p.hpd&&!p.dp_wanted&&deactivations==1);
    } else if(!strcmp(name,"cached-update")){
        struct typec_displayport_data data={.status=DP_STATUS_HPD_STATE,.conf=4};
        struct typec_mux_state state={.alt=&alt,.mode=TYPEC_DP_STATE_A,.data=&data};
        p.applied_valid=true;p.applied_alt=&alt;p.applied_mode=state.mode;p.applied_status=data.status;p.applied_conf=data.conf;
        assert(!dcp_typec_route_set(&mux,&state));assert(!hpd_calls&&!release_calls&&!connect_calls);
    } else {
        cd321x_update_work(&c.update_work.work);
        if(hpd_error||release_error){
            assert(!role_changes&&!safe_changes&&!orientation_changes&&!tbt_changes);
            assert(p.owner==&route&&p.hpd&&p.dp_hpd&&!p.applied_valid);
            assert(d.dptxport[0].connected&&!crossbar_calls&&!deactivations);
            assert(!c.state_valid&&(c.dp_status&DP_STATUS_HPD_STATE)&&queues==1);
            if(hpd_error)assert(!release_calls);
            if(!strcmp(name,"release-repeat")){
                release_error=0;assert(cd321x_pm_begin_read(&c.pm));cd321x_pm_snapshot_ready(&c.pm);cd321x_update_work(&c.update_work.work);
                assert(release_calls==2&&!p.owner&&!d.dptxport[0].connected&&safe_changes==1&&role_changes==1);
            }
        }else{
            assert(role_changes==1&&safe_changes==1&&orientation_changes==1);
            if(!strcmp(name,"tunnel"))assert(p.owner==&route&&p.hpd&&!release_calls&&!hpd_calls);
            else assert(!p.owner&&!p.hpd);
            if(!strcmp(name,"release-success"))assert(hpd_calls==1&&release_calls==1&&crossbar_calls==1);
            if(!strcmp(name,"owner-route"))assert(hpd_calls==1&&release_calls==1&&!other.dptxport[0].connected);
            if(!strcmp(name,"replug")){
                struct typec_displayport_data data={.status=DP_STATUS_HPD_STATE};
                struct typec_mux_state state={.alt=&alt,.mode=TYPEC_DP_STATE_A,.data=&data};
                assert(!dcp_typec_route_set(&mux,&state)&&p.owner==&route&&p.hpd&&connect_calls==1);
            }
        }
    }
    printf("%s: PASS\n",name);return 0;
}
