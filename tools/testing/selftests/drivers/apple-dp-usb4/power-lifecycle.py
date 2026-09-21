#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Replay DPMS/deactivation ordering against extracted driver functions.

Firmware and MMIO are mocks. This checks host lifecycle decisions, not video
delivery, real callback concurrency, or firmware behavior after the change.
"""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(os.environ.get('KSRC') or Path(__file__).resolve().parents[5])
driver = root / 'drivers/gpu/drm/apple'


def function(file, marker):
    text = (driver / file).read_text()
    start = text.index(marker)
    end = text.index('\n}', start) + 2
    return text[start:end]


code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
typedef uint32_t __le32;
typedef uint64_t u64;
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define cpu_to_le32(x) (x)
#define min(x,y) ((x)<(y)?(x):(y))
#define dev_info(...) ((void)0)
#define dev_warn(...) ((void)0)
#define dev_err(...) ((void)0)
#define lockdep_assert_held(x) ((void)0)
#define msecs_to_jiffies(x) (x)
#define DPTX_RECONNECT_DELAY 1000
#define DCP_FIRMWARE_V_12_3 1
#define DCP_FIRMWARE_V_13_5 2
#define PHY_MODE_DP 1
#define PHY_MODE_INVALID 0
#define WARN_ONCE(...) ((void)0)
#define system_freezable_wq 0
struct completion { bool done; };
static void reinit_completion(struct completion *c) { c->done=false; }
static void complete_all(struct completion *c) { c->done=true; }
static int wait_for_completion_timeout(struct completion *c, int timeout)
{ assert(timeout==1000); return c->done; }
struct apple_dcp;
struct endpoint { struct apple_dcp *dcp; void *wq; };
struct apple_epic_service { void *cookie; struct endpoint *ep; };
struct dptx_port {
 bool enabled, connected;
 struct completion deactivate_completion;
 int deactivate_status;
 unsigned link_rate, pending_link_rate;
 struct apple_epic_service *service;
 void *atcphy;
};
struct apple_connector { bool connected; int hotplug_wq; void *drm_edid; };
struct port { void *owner; bool hpd, applied_valid; };
struct apple_dcp_typec_route {
 struct apple_dcp *dcp; struct port *port; int dpin;
 void *dpin_bridge[2], *dpin_xbar[2], *phy;
};
struct apple_dcp {
 unsigned int dptx_core, index;
 bool usb4_poweroff, usb4_hpd, usb4_claimed, phy_managed_by_typec;
 bool typec, typec_cable_connected, main_display, during_modeset;
 bool pending_hotplug, pending_hotplug_connected, valid_mode;
 int fw_compat, typec_reconnect_tries, typec_reconnect_wq, usb4_connect_work, vblank_wq;
 void *dev, *avep, *hdmi_hpd;
 struct dptx_port dptxport[1];
 struct apple_dcp_typec_route *active_typec_route;
 struct apple_connector *connector;
 struct endpoint *dptxep;
};
struct platform_device { struct apple_dcp *dcp; };
static struct apple_dcp *platform_get_drvdata(struct platform_device *p) { return p->dcp; }
static int releases, physical_ends, gates, phy_ends, detaches, hotplugs;
static int connect_calls, native_disconnects, ack_error, release_error, end_error;
static bool ack_on_release, defer_power_callbacks;
static int hpd_error, gate_error, phy_error, detach_error;
static bool dcp_is_typec_output(struct apple_dcp *d) { return d->typec; }
static void cancel_work(void *w) { (void)w; }
static void cancel_delayed_work(void *w) { (void)w; }
static void mod_delayed_work(int q, void *w, int t) { (void)q;(void)w;(void)t; }
static void schedule_work(void *w) { (void)w; hotplugs++; }
static void flush_workqueue(void *w) { (void)w; }
static void av_service_disconnect(struct apple_dcp *d) { (void)d; }
static void av_service_connect(struct apple_dcp *d) { (void)d; }
static int dcp_dptx_connect(struct apple_dcp *d, int p)
{ (void)d; (void)p; connect_calls++; return 0; }
static int dcp_dptx_disconnect(struct apple_dcp *d, int p)
{ d->dptxport[p].connected=false; native_disconnects++; return 0; }
static int gpiod_get_value_cansleep(void *p) { return !!p; }
static int apple_dpin_set_active(void *p, bool active)
{ (void)p; (void)active; return ack_error; }
static int phy_set_mode_ext(void *p, int mode, int submode)
{ (void)p; (void)mode; (void)submode; phy_ends++; return phy_error; }
static int apple_dpxbar_set_active(void *p, bool active)
{ (void)p; assert(!active); gates++; return gate_error; }
static int apple_dpin_end(void *p) { (void)p; physical_ends++; return end_error; }
static int dcp_typec_route_deactivate(struct apple_dcp_typec_route *r)
{ if(detach_error) return detach_error; r->dcp->dptx_core=0; detaches++; return 0; }
static void disconnected_hpd_event(struct apple_connector *c)
{ if(c) c->connected=false; }
static int dptxport_set_hpd(struct apple_epic_service *s, bool hpd)
{ (void)s; assert(!hpd); return hpd_error; }
'''
code += function('dcp.c', 'bool dcp_usb4_ignore_poweroff_hotplug(')
code += function('iomfb_template.c', 'static void dcpep_cb_hotplug(')
code += function('dptxep.c', 'static int\ndptxport_call_activate(')
code += function('dptxep.c', 'static int\ndptxport_call_deactivate(')
code += r'''
static int dptxport_release_display(struct apple_epic_service *s)
{
 __le32 data=0, reply=0;
 releases++;
 if(ack_on_release) dptxport_call_deactivate(s,&data,4,&reply,4);
 return release_error;
}
static void _dcp_poweroff(struct apple_dcp *d)
{ u64 connected=0; if(!defer_power_callbacks) dcpep_cb_hotplug(d,&connected); }
static void iomfb_poweron_v13_3(struct apple_dcp *d)
{ u64 connected=1; if(!defer_power_callbacks) dcpep_cb_hotplug(d,&connected); }
#define iomfb_poweron_v12_3 iomfb_poweron_v13_3
'''
code += function('dcp.c', 'static int dcp_usb4_release(struct apple_dcp_typec_route *route)\n{')
code += function('dcp.c', 'void dcp_poweroff(')
code += function('dcp.c', 'void dcp_poweron(')
code += r'''
static void activate(struct apple_epic_service *s)
{ __le32 data=0,reply=0; dptxport_call_activate(s,&data,4,&reply,4); }
static void deactivate(struct apple_epic_service *s)
{ __le32 data=0,reply=0; dptxport_call_deactivate(s,&data,4,&reply,4); }
int main(void)
{
 struct apple_connector con={.connected=true};
 struct port p={.hpd=true,.applied_valid=true};
 struct apple_dcp d={.dptx_core=1,.usb4_hpd=true,.usb4_claimed=true,
   .typec=true,.fw_compat=DCP_FIRMWARE_V_13_5,.valid_mode=true,.connector=&con};
 struct apple_dcp_typec_route route={.dcp=&d,.port=&p};
 struct endpoint ep={.dcp=&d};
 struct apple_epic_service s={.cookie=&d.dptxport[0],.ep=&ep};
 struct platform_device dev={&d};
 d.dptxep=&ep; d.active_typec_route=&route; p.owner=&route;
 d.dptxport[0].enabled=d.dptxport[0].connected=true;
 d.dptxport[0].service=&s;
 activate(&s);
 /* Power-state HPD must not remove a physically connected sleeping monitor. */
 dcp_poweroff(&dev);
 assert(d.usb4_poweroff && con.connected && !d.valid_mode);
 assert(d.dptxport[0].connected && d.usb4_claimed);
 assert(!native_disconnects && !releases && !hotplugs);
 dcp_poweron(&dev);
 assert(!d.usb4_poweroff && con.connected && !connect_calls);
 /* Firmware HPD may arrive after the power RPC returns, as in the trace. */
 defer_power_callbacks=true;
 for(unsigned cycle=0;cycle<20;cycle++) {
  u64 low_after_reply=0, high_after_reply=1;
  d.valid_mode=true;
  dcp_poweroff(&dev);
  assert(d.usb4_poweroff && con.connected);
  dcpep_cb_hotplug(&d,&low_after_reply);
  assert(con.connected && !d.valid_mode && !d.pending_hotplug);
  dcp_poweron(&dev);
  assert(!d.usb4_poweroff && con.connected);
  dcpep_cb_hotplug(&d,&high_after_reply);
  assert(con.connected && !native_disconnects && !releases && !connect_calls);
 }
 defer_power_callbacks=false;
 /* Physical HPD low must still reach DRM while the display is off. */
 dcp_poweroff(&dev); d.usb4_hpd=false;
 u64 low=0; dcpep_cb_hotplug(&d,&low);
 assert(!con.connected && hotplugs);
 /* Replay observed early DEACTIVATE, then unplug without a second callback. */
 deactivate(&s);
 assert(d.dptxport[0].deactivate_completion.done);
 d.dptxport[0].link_rate=d.dptxport[0].pending_link_rate=30;
 assert(!dcp_usb4_release(&route));
 assert(!d.dptxport[0].link_rate && !d.dptxport[0].pending_link_rate);
 assert(!p.owner && !d.usb4_claimed && !d.usb4_poweroff);
 assert(physical_ends==1 && gates==1 && phy_ends==1 && detaches==1);
 /* A new activation must invalidate the old successful deactivation. */
 d.dptx_core=1; d.usb4_claimed=true; p.owner=&route; activate(&s);
 assert(!d.dptxport[0].deactivate_completion.done);
 assert(dcp_usb4_release(&route)==-ETIMEDOUT);
 assert(p.owner==&route && d.usb4_claimed && detaches==1 && gates==1);
 /* Failed acknowledgment and failed release RPC must retain ownership. */
 ack_on_release=true; ack_error=-EIO;
 assert(dcp_usb4_release(&route)==-EIO && p.owner==&route);
 ack_error=0; release_error=-EIO;
 assert(dcp_usb4_release(&route)==-EIO && detaches==1);
 release_error=0; end_error=-ETIMEDOUT;
 assert(dcp_usb4_release(&route)==-ETIMEDOUT && p.owner==&route && detaches==1);
 end_error=0;
 /* Failure at each remaining release stage must prevent route reuse. */
 hpd_error=-EIO; d.usb4_claimed=true;
 int gates_before=gates;
 assert(dcp_usb4_release(&route)==-EIO && p.owner==&route);
 assert(gates==gates_before && d.usb4_claimed);
 hpd_error=0; gate_error=-EIO;
 assert(dcp_usb4_release(&route)==-EIO && p.owner==&route && detaches==1);
 gate_error=0; phy_error=-EIO;
 assert(dcp_usb4_release(&route)==-EIO && p.owner==&route && detaches==1);
 phy_error=0; detach_error=-EIO;
 d.dptxport[0].link_rate=d.dptxport[0].pending_link_rate=20;
 assert(dcp_usb4_release(&route)==-EIO && p.owner==&route && detaches==1);
 assert(d.dptxport[0].link_rate==20 && d.dptxport[0].pending_link_rate==20);
 detach_error=0;
 assert(!dcp_usb4_release(&route) && !p.owner && detaches==2);
 assert(!d.dptxport[0].link_rate && !d.dptxport[0].pending_link_rate);
 /* Native Type-C poweroff retains its existing session-release behavior. */
 d.typec_cable_connected=true; d.dptxport[0].connected=true;
 con.connected=true; dcp_poweroff(&dev);
 assert(native_disconnects==1 && !d.dptxport[0].connected && !con.connected);
 puts("PASS: USB4 DPMS retains connector/session; 20 deferred-callback cycles, wake, physical unplug, early ACK, reactivation, release-stage failures, native poweroff");
}
'''
with tempfile.TemporaryDirectory(prefix='apple-usb4-power-') as tmp:
    source = Path(tmp) / 'test.c'
    binary = Path(tmp) / 'test'
    source.write_text(code)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', '-fsanitize=undefined',
                    '-g', str(source), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
