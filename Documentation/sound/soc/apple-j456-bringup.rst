.. SPDX-License-Identifier: GPL-2.0-only

J456 experimental speaker bring-up (RFC)
=======================================

This draft describes opt-in kernel bring-up for the four-port M1 iMac
(``apple,j456``). It is not complete protected speaker support and must not
be enabled by default. Related distribution report:
https://github.com/omacom/omarchy-mac/issues/187

Scope
-----

The device tree connects four SSM3515 amplifiers to two MCA ports. The
machine driver avoids a capture route on playback-only speaker codecs and
requires an explicit ``j456_quiet_test`` opt-in on J456. The draft fixes the
DAC ceiling at -42 dB, retains digital mute at codec startup, locks the
lowest analog gain, enables HPF and configures the nominal 1 V hardware
limiter before enabling it. Missing controls or failed writes reject probe.
There is no userspace volume-unlock control for this J456 path.

The codec exposes read-only volatile status with I/O error propagation,
checks physical configuration against cached registers in PCM prepare, and
forces mute if those values disagree. A read-only, default-off J456-only
``j456_no_auto_powerdown`` parameter allows investigation of automatic
zero-sample power-down. This parameter is diagnostic, not a proposed final
power-management interface. The codec changes require regression review
on other SSM3515 users; they are not all J456-specific.

The limiter is not validated thermal or excursion protection. This draft
adds neither voltage/current feedback nor an equivalent speaker safety
model. The physical-register check is a startup check, not a continuous
hardware interlock. Even the low diagnostic ceiling is not a measured
safe operating envelope.

Observed local behavior
-----------------------

On kernel 7.1.13-3-2-ARCH, related experimental modules plus a separate
stereo-to-four-channel crossover/EQ graph and userspace supervisor produced
usable Cliamp playback. The owner reported continuous, improved sound at
an explicitly authorized local -3 dB ceiling. That local ceiling is NOT
included here or recommended for other machines.

A continuous zero-valued source pinned to 48 kHz prevented a subsequently
observed playback dropout during stream-transition tests. Before pinning,
the graph could run at 44.1 kHz with 48 kHz hardware; the original dropout
was recorded as PCM no longer RUNNING, but its exact transition was not
captured. A graph-rate change is a hypothesis, not proven root cause.

Muted startup tests have produced transient overtemperature-warning and
undervoltage flags. Disabling automatic power-down alone did not eliminate
all such observations. The local supervisor retains strict checks during
active playback and mutes before stopping the graph. No active fault mask
was weakened. The separately working microphone was preserved.

A 60-second muted test with five source attach/detach cycles passed with
the pinned clock. A later 60-sample live observation at the local -3 dB
ceiling had zero amplifier status flags and continuously RUNNING PCM.
These observations do not establish speaker temperature, excursion,
limiter overshoot, or long-term reliability.

Reproducible software checks
----------------------------

The standalone source tests below need Python 3 and a C compiler, not
Apple reference files or audio hardware. They compile the actual modified
C functions with mocked kernel interfaces. From the source tree root::

    python3 tools/testing/selftests/alsa/j456_control_lock.py
    python3 tools/testing/selftests/alsa/j456_ssm3515_prepare.py
    python3 tools/testing/selftests/alsa/j456_ssm3515_status.py
    python3 tools/testing/selftests/alsa/j456_ssm3515_power.py

They exercise missing controls and write failures, ordered limiter locks,
physical register mismatches and forced mute, status-read errors, and
J456-only diagnostic power handling. They are source-level review harnesses,
not installed-target kselftests; final test placement is open for review.

The rebased driver sources build as external modules with W=1 against the
tested machine's 7.1.13-3-2-ARCH headers. This is not a complete build or
hardware test of the target Omarchy branch. The public -42 dB draft has not
replaced the owner's working local -3 dB modules.

Before a supported release
--------------------------

* Validate amplifier transfer, limiter threshold/overshoot and sustained
  thermal and mechanical limits for each physical speaker.
* Resolve startup fault/power behavior and review failure handling through
  reset, direct ALSA playback and userspace failure.
* Test the final configuration through reboot and suspend/resume.
* Review effects on other SSM3515 machines and run target-kernel build and
  device-tree schema validation.
* Supply reviewed, redistributable userspace filtering/protection and
  distribution packaging. This kernel draft alone is not an audio setup.

Provenance
----------

This contribution is AI-assisted. Existing upstream source copyright and
SPDX identifiers are retained. New register definitions and controls are
based on the public Analog Devices SSM3515 datasheet:
https://www.analog.com/media/en/technical-documentation/data-sheets/ssm3515.pdf

Private Apple binaries, disassembly, extracted tuning coefficients,
recordings, personal diagnostics, compiled modules and local installation
scripts are not part of this contribution. The local filtering reference
needs separate provenance/licensing review before any publication. No
human review, DCO sign-off or general protection certification is implied
by this draft.
