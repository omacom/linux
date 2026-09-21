# SPDX-License-Identifier: GPL-2.0
# Host-side checks of the Apple USB4 DP source drivers: each script compiles
# the real driver functions against mocked MMIO and firmware replies with
# UBSan (bridge.py and lifecycle.py also with ASan) and needs only a host C
# compiler and python3. The scripts read the driver sources from the kernel
# tree, found relative to the script or through KSRC.
TEST_PROGS := \
	bridge.py \
	connection-attributes.py \
	crossbar.py \
	drive-settings.py \
	dprx-cancel.py \
	lifecycle.py \
	link-configuration.py \
	pll-command.py \
	power-lifecycle.py

TEST_FILES := native-events.json

include ../../lib.mk
