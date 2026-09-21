/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
#ifndef _LINUX_SOC_APPLE_DCP_USB4_H
#define _LINUX_SOC_APPLE_DCP_USB4_H
#include <linux/types.h>
struct device_node;
/* Sleepable; connector is a borrowed OF node, dpin is 0 or 1. */
int apple_dcp_usb4_set(struct device_node *connector, unsigned int dpin,
		      bool enable);
#endif
