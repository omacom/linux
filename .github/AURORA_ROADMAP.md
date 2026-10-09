# Aurora kernel development roadmap

Status: 2026-10-08. Development landing branch: [`omacom/linux:integration/aurora`](https://github.com/omacom/linux/tree/integration/aurora). This roadmap proposes the next kernel work and records the evidence required to complete it. It does not change existing branches or installed systems.

## Baseline

The landing branch starts at [`8087c56eb7e9`](https://github.com/omacom/linux/commit/8087c56eb7e9cde3f45b8230b2d681e49b21df2b), the source tip of [12.6 stable](https://github.com/iconidentify/aurora-linux/releases/tag/sep-7.1.12.aurora2-12.6-stable). Its compiled kernel is [`c4647169e329`](https://github.com/omacom/linux/commit/c4647169e329b77f4b75d8367cb6f7603e07fc5b); the later commits change installer tools. The published kernel package SHA-256 is `d954e8c90f57b33d19d4a166d6f70225d7377abed59b35f3e20ac6d20427a39f`.

12.6 includes display route following and rollback, base-M2 SEP DMA admission, immediate trusted-key private-key admission, bounded Bluetooth startup recovery, AOP error handling, DP-alt-mode lifetime corrections, Thunderbolt RX page recycling, calibration collection fixes and ANE failed-probe cleanup. Inclusion does not establish every board's hardware acceptance.

Custom Hyprland, Aquamarine and Omarchy desktop fixes are excluded from 12.6 stable. Desktop failures below retain their own ownership and acceptance requirements.

## Next kernel work

Priorities describe impact, not a promised release date. **P1** is broken core functionality or persistent-secret recovery; **P2** is bounded recovery or qualification. Readiness is separate: a candidate needs review and tests; an investigation needs the stated comparison before a fix is selected.

### P1: shared Thunderbolt pixel clock stops while a stream remains active

**Readiness:** candidate available. **Area:** ATC PHY / displays. **Original:** [PR #73](https://github.com/iconidentify/aurora-linux/pull/73), [J314S report](https://github.com/iconidentify/aurora-linux/issues/39#issuecomment-6061463214).

On J314S / M1 Pro with an LG UltraFine 5K and 12.6, login and DPMS can work, but ending the monitor's unused second DP tunnel darkens the active first stream after approximately 6–10 seconds. This is distinct from the corrected CRTC-routing failure. T8103/T600X share one tunnel clock; the current [stop path](https://github.com/omacom/linux/blob/c4647169e329b77f4b75d8367cb6f7603e07fc5b/drivers/phy/apple/atc.c#L3417) stops it when either DP IN receives a zero rate.

Christian Bartels's candidate [`f30bfdfd27b7`](https://github.com/cb2206/linux/commit/f30bfdfd27b78d86a3c67e1f1e6c97fa675292e3) tracks active DP IN users and stops the shared clock when the last user leaves. The author reports J314S login, suspend, replug and DPMS success with the patched module. It is not integrated; base M1 and M1 Max are untested.

Next: review start failure, same-rate requests, rate changes, repeated stops and power-domain restoration. Preserve the distinct T602X and T6030 clock paths.

Done when: controls show either stream can stop without stopping its active peer, final-user stop turns the clock off, failed starts do not add a user, and reset/rate-change behavior cannot leave stale ownership. Build the affected ARM64 object and verify the final candidate on J314S through login, DPMS, suspend and replug. Record separate T8103/T6001 qualification rather than inferring it.

### P1: preserve existing trusted keys across identity-keybag changes

**Readiness:** investigation and lifecycle design. **Area:** SEP. **Original:** [issue #31](https://github.com/iconidentify/aurora-linux/issues/31).

J316S / M1 Pro, OS firmware 13.5 and system firmware 26.4, reported reference-key unseal failures after an identity-keybag update. A later unchanged-content resnapshot survived reboot; the content-change dependency is suspected, not established for every save. Fingerprint-enrollment persistence and sealed-secret persistence have separate acceptance criteria.

Start at [identity resnapshot](https://github.com/omacom/linux/blob/c4647169e329b77f4b75d8367cb6f7603e07fc5b/drivers/soc/apple/sks.rs#L1015), its [verify/save caller](https://github.com/omacom/linux/blob/c4647169e329b77f4b75d8367cb6f7603e07fc5b/drivers/soc/apple/sbio.rs#L906), and [reference-key admission/unseal](https://github.com/omacom/linux/blob/c4647169e329b77f4b75d8367cb6f7603e07fc5b/drivers/soc/apple/refkey.rs#L248). The shipped seal round trip rejects an unusable new blob; it does not repair persistence or recover stranded blobs.

Next: distinguish unchanged resnapshot, enrollment/deletion and sensor re-registration with a content-changing save; determine how the existing private-key binding is preserved. Keep production keybags, reference keys, fingerprint state and sealed data intact. Use a separately prepared test context for mutating reproductions.

Done when: blobs sealed before the operation recover byte-identical keys after each admitted state change and cold reboot, new/load still works, enrollment and matching survive reboot, interrupted/error paths preserve recoverable state, and failures return explicit errors without replacing the reference key. Regenerating keys and orphaning old blobs is not a resolution.

### P1: GPU firmware crashes during loaded-GPU resume on M1 Max

**Readiness:** needs comparison evidence. **Area:** GPU / power management. **Original:** [issue #74](https://github.com/iconidentify/aurora-linux/issues/74).

J316C / T6001, OS firmware 13.5 and system firmware 26.6.2, 12.6, stock Honeykrisp Mesa 26.2.2, Studio Display over Thunderbolt: a running GPU benchmark was followed by s2idle, failed keyboard wake, then power-button wake and an RTKit GPU crash. Submissions failed with `ENODEV`; the display link recovered. There is no older-kernel or idle-GPU comparison, and the relationship between keyboard wake and GPU failure is unknown.

Next: on the same board and firmware, compare idle and loaded suspend on 12.6 and an available known-good kernel. Record wake method, exact packages, first GPU fault, in-flight job behavior and DRM link state. The [GPU crash callback](https://github.com/omacom/linux/blob/c4647169e329b77f4b75d8367cb6f7603e07fc5b/drivers/gpu/drm/asahi/gpu.rs#L1075) records failure; it is not an established cause.

Done when: a reproducible trigger and first failure identify the required change, then the corrected candidate resumes with successful rendering under both idle and loaded conditions. Keep wake-source failure separate if the evidence does not connect it. The J293 userspace capture abort below is a different failure.

### P2: replenish exhausted Thunderbolt RX descriptors after memory returns

**Readiness:** implementation-ready recovery requirement. **Area:** networking. **Original:** [issue #69](https://github.com/iconidentify/aurora-linux/issues/69).

[RX allocation](https://github.com/omacom/linux/blob/c4647169e329b77f4b75d8367cb6f7603e07fc5b/drivers/net/thunderbolt/main.c#L532) can fail; [NAPI poll](https://github.com/omacom/linux/blob/c4647169e329b77f4b75d8367cb6f7603e07fc5b/drivers/net/thunderbolt/main.c#L838) can complete after the ring has drained. An empty ring cannot generate the next receive completion needed to retry allocation. This source-level recovery limitation has no reported hardware occurrence or measured throughput impact.

Next: add a bounded retry that preserves NAPI/page-pool ownership and cancels before disconnect, stop, suspend or pool destruction. Do not introduce a second concurrent ring consumer or a busy retry loop.

Done when: an allocation-failure control drains the ring, restores memory and receives traffic without a link reset. Teardown with retry pending must leave no callback using freed state. Retain normal transfer, partial-packet and early-IRQ checks; record hardware reconnect/suspend and transfer integrity separately from host controls.

### Dual-stream 5K: complete route following and failed-attachment rollback

**Readiness:** candidate series with required corrections. **Area:** DCP / Thunderbolt. **Original:** [PR #22](https://github.com/iconidentify/aurora-linux/pull/22).

The LG UltraFine 5K needs two DP streams feeding one DCP. Christian Bartels reports J314S 5K operation with the tile-follow companion included in his test tree. The submitted series still needs that companion and complete setup error handling.

A newer [J313 report](https://github.com/iconidentify/aurora-linux/pull/22#issuecomment-6069188567) shows a physically checked full-panel pattern and hot-replug on 12.4 plus [`fa42a758b128`](https://github.com/tao-io/aurora-linux/commit/fa42a758b1282e275adf743b9098d27b68827c84). That candidate returns setup errors and tears down failed attachments, but still publishes split state before setup completes. It needs review; it does not establish final-source suspend, brightness, USB, camera or audio acceptance.

Next: include the tile-follow companion, propagate required source-select/preselect/connect errors, and publish a live split only after successful setup. A failed split must preserve the original route and permit retry. Keep the shared-clock correction above independently correct; dual-stream support must not mask its failure.

Done when: failure controls cover every required setup stage and both teardown orders. The final candidate displays both tiles without a seam or duplicate connector through cold boot, DPMS, suspend, replug and route movement; ordinary single-stream and independent dock monitors still work. Qualify M2 separately and retain the unsupported T6030 DP IN 1 boundary.

### M3 Air: qualify the exact native OpenGL profile

**Readiness:** matched experimental stack; hardware rendering proof pending. **Area:** GPU / firmware admission. **Original:** [issue #35](https://github.com/iconidentify/aurora-linux/issues/35), [diagnostic draft #50](https://github.com/iconidentify/aurora-linux/pull/50).

J613 25G83 uses exact firmware compatibility 26.6.2, HAL200 and USC3, with an explicit persistent profile. [HAL reporting and VM acknowledgement](https://github.com/omacom/linux/blob/c4647169e329b77f4b75d8367cb6f7603e07fc5b/include/uapi/drm/asahi_drm.h#L204) must keep legacy clients out of the HAL200 command path. Native Vulkan25 is unavailable; helper/scratch and compressed-ZLS restrictions remain explicit.

Next: update the diagnostic draft against the current layouts; exercise the matched profile's actual EGL/Gallium known-answer readback, native display startup and desktop use. Preserve 14.x/Pro graphics selection, M1/M2 behavior and per-Mac calibration. Build success alone does not establish rendering or power qualification.

Done when: exact stack/profile identities accompany visible and readback-verified rendering, mismatched clients are refused, legacy profiles retain their existing behavior, and unsupported shaders fail explicitly. Hardware power and broader conformance remain separately qualified.

## Retest and remaining capability queue

Keep independent triggers separate when creating Omacom tickets. The original numbers in this table refer to `iconidentify/aurora-linux`; they are not Omacom issue numbers.

| Original reports | Current boundary and next acceptance |
| --- | --- |
| [#39](https://github.com/iconidentify/aurora-linux/issues/39), [#45](https://github.com/iconidentify/aurora-linux/issues/45) | CRTC-following source fix shipped. J316S reporter confirms the original Studio Display failure fixed on 12.6 stable. J314S routing works but the separate shared-clock blackout above remains. Preserve M2 Max dual-direct evidence and final-version retests. |
| [#27](https://github.com/iconidentify/aurora-linux/issues/27) | Dock-unplug to direct-adapter recovery fix shipped; original J314S same-port sequence needs the stated current-source test. |
| [#28](https://github.com/iconidentify/aurora-linux/issues/28), [#24](https://github.com/iconidentify/aurora-linux/issues/24), [#38](https://github.com/iconidentify/aurora-linux/issues/38), [#30](https://github.com/iconidentify/aurora-linux/issues/30), [#55](https://github.com/iconidentify/aurora-linux/issues/55) | Distinct HPD/input-switch loss, ACIO link-error recovery, port-specific direct-USB-C wake, CRTC-off tunnel churn and software-rendered late hotplug. Record port, IRQ delivery, route and rendering backend. Delivered-IRQ recovery does not prove a missing IRQ's cause. |
| [#33](https://github.com/iconidentify/aurora-linux/issues/33), duplicate [#51](https://github.com/iconidentify/aurora-linux/issues/51) | DMA fix shipped. Stock J413 now reports SEP attach, enrollment, sudo/polkit/lock authentication and reboot restoration. J415 acceptance remains separate. J413 polling fallback and profile-label wording are follow-ups, not enrollment failures. |
| [#25](https://github.com/iconidentify/aurora-linux/issues/25), [#16](https://github.com/iconidentify/aurora-linux/issues/16) | Original transient SEP attach/session failures need reproducible current-source evidence; preserve working enrollments and key material. |
| [#20](https://github.com/iconidentify/aurora-linux/issues/20), [#21](https://github.com/iconidentify/aurora-linux/issues/21) | Bluetooth bounded startup recovery and AOP error handling shipped; original J516S radio/ALS and resume retests remain. An untyped historical timeout has no established endpoint-specific cause. |
| [#29](https://github.com/iconidentify/aurora-linux/issues/29), [#13](https://github.com/iconidentify/aurora-linux/issues/13) | Display sleep qualification: record time to picture and retained versus re-enumerated tunnels; extend the accepted M1 boundary to the specified M2/M3 hardware. |
| [#49](https://github.com/iconidentify/aurora-linux/issues/49), [#54](https://github.com/iconidentify/aurora-linux/issues/54) | GPU MMU fault and dma-buf plane-offset corruption remain separate. The Mesa offset fix is built; final Vulkan/EGL/Zink pixel acceptance remains. Retest the original GPU fault with normal application/sandbox settings. |
| [#12](https://github.com/iconidentify/aurora-linux/issues/12), [#40](https://github.com/iconidentify/aurora-linux/issues/40) | Base-M2 Thunderbolt picture and display-audio qualification: actual picture/audio, hotplug and suspend evidence before support/default changes. |
| [#5](https://github.com/iconidentify/aurora-linux/issues/5), [#18](https://github.com/iconidentify/aurora-linux/issues/18), [#19](https://github.com/iconidentify/aurora-linux/issues/19) | Per-Mac provisioning and real ANE jobs, a separately designed login-keyring API, and AVE session/DMA/V4L2 lifecycle. Probe success is not an inference job; trusted-key documentation is already present. |

## Desktop and distribution handoffs

These retain their impact and original evidence, but their fixes belong with the affected userspace or integration code.

| Original | Handoff |
| --- | --- |
| [#53](https://github.com/iconidentify/aurora-linux/issues/53), P0 | Existing Omarchy lock-intent/authentication fix is implemented and reviewed. It is excluded from 12.6 stable. Integrate through the shared desktop and verify installed suspend/crash/restart and authenticated next login. This is delivery and acceptance of an existing fix, not a newly discovered kernel security bug. |
| [#75](https://github.com/iconidentify/aurora-linux/issues/75), P1; [#56](https://github.com/iconidentify/aurora-linux/issues/56), P2 | J293 capture admission and M3 Pro connector teardown have separate userspace fixes. The patched J293 pair survived a targeted same-kernel resume/capture retest; initial EGL invalidation and kernel contribution are unresolved. Custom desktop packages are excluded from stable; pursue application fixes without claiming a kernel repair. |
| [#77](https://github.com/iconidentify/aurora-linux/issues/77), [#78](https://github.com/iconidentify/aurora-linux/issues/78) | Installer cannot obtain `libva-v4l2_request-avd` on the reported installations. The recipe exists in Omacom's package tree; repository availability/configuration needs checking. Keep software-decode fallback explicit. |

New boot reports [#76](https://github.com/iconidentify/aurora-linux/issues/76), [#77](https://github.com/iconidentify/aurora-linux/issues/77) and [#78](https://github.com/iconidentify/aurora-linux/issues/78) show one-shot boot, promotion and two reboots on J414C, J293 and J316C. J414C uses an out-of-tree ANE module, so it does not qualify the in-tree driver. Single GPU benchmark runs preserve output digests but do not establish performance. Trackpad workqueue-name truncation is a warning-level follow-up; haptics were not tested. Keep the J316C resume failure open despite its boot successes.

A [J414C Studio Display report](https://github.com/iconidentify/aurora-linux/issues/39#issuecomment-6065414598) adds Type-C configure and Thunderbolt-domain timeouts on the first plug, followed by successful internal retry and a visible picture. Replug had no timeout. Record a bounded cold-first-plug comparison before classifying this as a regression; it does not establish failed display routing.

## Ticket and change acceptance

Each recreated ticket needs a single trigger, affected board/SoC, OS and system firmware, exact kernel/source and userspace versions, reproduction steps, expected/observed behavior, first relevant error, immutable code links, known-good comparisons, dependencies, and explicit completion criteria. Separate reported facts from suspected causes, host controls from physical tests, and source integration from release inclusion.

An implementation candidate needs tests of the production path, including the original failing behavior and meaningful error/lifetime cases, an affected ARM64 build, review of the final diff, and hardware acceptance where the behavior depends on hardware. Preserve original author attribution. Report limitations and untested models; a success on another board does not close the original failure.

Create feature/fix branches from `integration/aurora` and propose changes back to it. A roadmap entry is not approval to change `aurora-wip`, the default branch, installed boot defaults or release contents.

## Tracker migration

Omacom kernel issues are currently disabled. Enable them before creating the kernel work tickets above; link those tickets back into this roadmap. The first ticket set should cover the shared-clock failure, trusted-key persistence, M1 Max resume comparisons, RX refill recovery and dual-stream 5K closure. Route userspace/distribution tickets to their actual implementation repositories.

Keep the original repository's issues, contributor discussions and release assets available during the transition. Add reciprocal links and a disposition to each original only after the destination exists. Confirmed duplicates and completed test reports can close with their evidence intact; unresolved bugs close as migrated only after their new owner/ticket is recorded. Archive the old repository after active work and incoming reports have a working destination; deleting it would break release downloads and evidence links used here.
