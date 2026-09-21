/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
#ifndef _LINUX_PHY_APPLE_ATC_H
#define _LINUX_PHY_APPLE_ATC_H

/* PHY_MODE_DP submode: lease the USB4 DP source PCLK1, without changing lanes.
 * Configure with DP set_rate only; release with PHY_MODE_DP submode 0 after
 * the DPIN source is inactive. One tunnel clock consumer per ATC.
 */
#define APPLE_ATCPHY_DP_TUNNEL 1

#endif
