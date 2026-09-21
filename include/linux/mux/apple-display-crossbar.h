/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
#ifndef _LINUX_MUX_APPLE_DISPLAY_CROSSBAR_H
#define _LINUX_MUX_APPLE_DISPLAY_CROSSBAR_H

#include <linux/types.h>

struct mux_control;
/* Caller must hold a selected DPIN mux throughout the operation. */
int apple_dpxbar_set_active(struct mux_control *mux, bool active);

#endif
