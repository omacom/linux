.. SPDX-License-Identifier: GPL-2.0-only

===========================================
USB4 DisplayPort tunneling on Apple silicon
===========================================

Apple silicon Macs can drive a DisplayPort display behind a USB4 dock. The
stream comes from an external display coprocessor (``dcpext``), leaves the
SoC through the ATC DP IN bridge of the Type-C port and enters the DP IN
adapter of the USB4 host router, which tunnels it to the DP OUT adapter of
the dock. This document describes the Linux implementation, tested on a
MacBook Pro 16" (j316c) with a CalDigit TS4.

Enabling
--------

The source is opt-in::

  appledrm.usb4_dp=1

Without it the display driver refuses the source request with
``-EOPNOTSUPP`` and the Thunderbolt connection manager aborts the DP tunnel
activation; the dock's other tunnels are unaffected.

Device tree
-----------

Per Type-C port the board describes:

- an ``apple,t6000-dpin`` node per DP IN bridge (two per ATC), with its
  registers and interrupt;
- on the ``dcpext`` that may drive the port, a ``typec-routes`` route for
  it, plus two ``dcpext``-level properties: ``apple,typec-dpin`` holds two
  bridge phandles per route index (positions ``2*reg`` and ``2*reg+1``),
  and the ``mux-control-names`` gain ``typecN-dpin0`` / ``typecN-dpin1``
  next to the existing ``typecN`` PHY and mux entries;
- on the ``cio`` node, ``apple,usb4-dp-connector`` pointing at the Type-C
  connector, which is how the Thunderbolt driver finds the DCP route.

On the j316c Type-C port 0 is offered to ``dcpext0`` only, the pipeline
macOS uses for a tunneled display on that port. ``dcpext0`` also drives the
HDMI output, so HDMI and a tunneled display on port 0 share one DCP.

Connection sequence
-------------------

#. The connection manager pairs a host DP IN with the dock's DP OUT and
   activates the tunnel. Through ``tb_nhi_ops.dp_tunnel_set`` the Apple NHI
   driver asks the display driver for a source for that DP IN.
#. The display driver picks a ``dcpext`` route for the port, switches the
   display crossbar so the pipeline feeds the DP IN bridge, puts the ATC PHY
   into USB4 tunnel mode (common power, sleep overrides, lane reset and the
   PCLK outputs) and starts the bridge (``apple_dpin_begin``).
#. The bridge raises HPD. The display driver then connects the DPTX
   endpoint of the DCP to the DP IN target and the DCP trains the link. The
   connection attributes carry role 1 with HPD; without the role byte the
   firmware accepts the request but never sends video. The rate callbacks
   of the DPTX endpoint program one AUSPLL frequency and the three PCLK
   dividers, no lane or AUX configuration. A rate of zero releases the
   tunnel clocks.
#. The connection manager's DPRX poll completes and video flows.

On disconnect the DPTX endpoint is released, the crossbar destination is
disabled, the bridge is stopped, the tunnel clocks are gated and the
crossbar route is returned, before the adapters and paths disappear. A route whose release fails stays reserved
until reboot rather than being handed to another port.

System sleep
------------

The CIO firmware keeps the USB4 link up across system sleep. Routers put to
sleep by the connection manager never see the link go down, come back with
Sleep and Sleep Ready still set, and fail a few seconds after resume. On
these hosts the driver leaves routers awake (``QUIRK_NO_LINK_SLEEP``), and
after resume rescans the host router and re-offers the DP IN and DP OUT
resources released at suspend so the tunnel is re-created.

Port hand-over
--------------

Each Type-C port has its own connector and encoder. When the dock moves to
another port, the old connector is disconnected while its CRTC is still
bound; a compositor that refuses to disable a disconnected output would
leave the new connector without a CRTC. The driver releases the stale CRTC
itself shortly after the disconnect.

Limitations
-----------

- One tunneled display per ``dcpext``.
- The TS4 exposes a two-lane DP OUT (HBR3 x2); 4K120 and above are not
  available through it.
- Type-C port 0 shares ``dcpext0`` with HDMI on the j316c.
- Hyprland/aquamarine 0.56 drop the first DPMS-on after DPMS-off.

Testing
-------

Host-side checks compile the real driver functions against mocked MMIO and
firmware replies::

  make -C tools/testing/selftests TARGETS=drivers/apple-dp-usb4 run_tests

On hardware, check in this order: the tunnel activates and the DPRX poll
completes; picture, keyboard and mouse on every port and cable orientation;
unplug and replug; moving the dock between ports; display sleep; system
sleep with the dock attached, waiting at least a minute after resume.
