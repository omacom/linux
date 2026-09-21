/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
#ifndef _APPLE_DPIN_H
#define _APPLE_DPIN_H

struct apple_dpin;
struct device;
struct device_node;

struct apple_dpin *devm_apple_dpin_get(struct device *dev,
				     struct device_node *node, unsigned int index);
int apple_dpin_begin(struct apple_dpin *dpin, void (*notify)(void *, bool), void *cookie);
int apple_dpin_end(struct apple_dpin *dpin);
int apple_dpin_set_active(struct apple_dpin *dpin, bool active);
bool apple_dpin_hpd(struct apple_dpin *dpin);
int apple_dpin_register(void);
void apple_dpin_unregister(void);
#endif
