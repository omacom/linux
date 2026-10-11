# Aurora development roadmap

Status: 2026-10-11. Active development: [`integration/aurora`](https://github.com/omacom/linux-aurora/tree/integration/aurora). [Live roadmap tracker](https://github.com/omacom/linux-aurora/issues/56).

## Release and repository baseline

The current Omacom release is [Aurora 2026.10.11.13](https://github.com/omacom/linux-aurora/releases/tag/aurora-2026.10.11.13), tagged at `5dcdeb8cda8dafe203d4d2f03952ade392c3fe23`. Its compiled kernel source is `a85f8eee2fd54ed9e7237f25d1f085e9d7848111`; later source changes deliver the installer from Omacom. Kernel/headers version is `7.1.12.aurora2-20261011.13`.

The personal `iconidentify/aurora-linux` repository is retained as a frozen historical location at its existing [2026.10.10.12 release](https://github.com/iconidentify/aurora-linux/releases/tag/aurora-2026.10.10.12), source tip `a462e4377673e20668c7162757f545580548baf5`. Existing source branches, issues, comments and release assets remain available. No published release assets are rewritten. New reports and development belong in [Omacom issues](https://github.com/omacom/linux-aurora/issues).

Bootloader source is in [omacom/m1n1](https://github.com/omacom/m1n1): `integration/aurora` at `d05ba17dfb771871d608225be42968bbb1e75a18` and the separate Neo branch `integration/neo` at `1b36287e04788f4a028e6180c64d3d96e49f06b1`. Kernel integration tickets link bootloader dependencies; bootloader fixes belong in that repo. Mesa source remains in its component repository, with compiled matched packages delivered in the kernel release.

## Implementation order

Priority and readiness are separate. P0 is an existing security-delivery blocker, P1 is core reliability or installation, P2 is recovery/performance/qualification, and P3 is future capability or a bounded follow-up. Candidate code is not a merge or release claim.

1. **Make installation and recovery repeatable:** [#18](https://github.com/omacom/linux-aurora/issues/18), [#19](https://github.com/omacom/linux-aurora/issues/19), [#47](https://github.com/omacom/linux-aurora/issues/47).
2. **Resolve core radio, GPU and key reliability:** [#20](https://github.com/omacom/linux-aurora/issues/20), [#21](https://github.com/omacom/linux-aurora/issues/21), [#22](https://github.com/omacom/linux-aurora/issues/22), [#23](https://github.com/omacom/linux-aurora/issues/23), [#24](https://github.com/omacom/linux-aurora/issues/24), [#25](https://github.com/omacom/linux-aurora/issues/25).
3. **Improve the M3 desktop and ports:** [#30](https://github.com/omacom/linux-aurora/issues/30), [#31](https://github.com/omacom/linux-aurora/issues/31), [#32](https://github.com/omacom/linux-aurora/issues/32), [#33](https://github.com/omacom/linux-aurora/issues/33), [#35](https://github.com/omacom/linux-aurora/issues/35), [#36](https://github.com/omacom/linux-aurora/issues/36).
4. **Finish board-specific qualification:** [#26](https://github.com/omacom/linux-aurora/issues/26), [#34](https://github.com/omacom/linux-aurora/issues/34), [#27](https://github.com/omacom/linux-aurora/issues/27), [#28](https://github.com/omacom/linux-aurora/issues/28), [#41](https://github.com/omacom/linux-aurora/issues/41), [#45](https://github.com/omacom/linux-aurora/issues/45), [#40](https://github.com/omacom/linux-aurora/issues/40).

The existing desktop lock-intent fix remains a [P0 shared-desktop handoff](https://github.com/omacom/linux-aurora/issues/17). Capture and teardown fixes also retain their desktop owners. They do not authorize custom Hyprland/Aquamarine packages in this kernel release.

## Active work

| Priority | Readiness | Implementation owner | Ticket |
| --- | --- | --- | --- |
| P0 | blocked | desktop | [#17 Desktop handoff: deliver and qualify existing lock-intent recovery fix](https://github.com/omacom/linux-aurora/issues/17) |
| P1 | candidate | installer | [#18 Installer: resume interrupted downloads without weakening checksum admission](https://github.com/omacom/linux-aurora/issues/18) |
| P1 | investigation | installer | [#19 EFI history cleanup: tolerate module-header symlinks while protecting boot references](https://github.com/omacom/linux-aurora/issues/19) |
| P1 | investigation | kernel | [#20 J700 Neo: recover association after repeated ASSOC_START without replaying unrelated calibration](https://github.com/omacom/linux-aurora/issues/20) |
| P1 | investigation | kernel | [#21 J493 M2 Bluetooth: TX timeouts after s2idle require manual radio reset](https://github.com/omacom/linux-aurora/issues/21) |
| P1 | investigation | kernel | [#22 J516S: forced WebRender native compositor still causes GPU MMU fault and DEVICE LOST](https://github.com/omacom/linux-aurora/issues/22) |
| P1 | investigation | kernel | [#23 SEP: preserve sealed trusted keys through content-changing keybag saves and reboot](https://github.com/omacom/linux-aurora/issues/23) |
| P1 | investigation | kernel | [#24 J316C M1 Max: GPU firmware crash after loaded s2idle resume](https://github.com/omacom/linux-aurora/issues/24) |
| P1 | candidate | kernel | [#25 G14X compute preemption: review candidate while preserving M1 throughput and M3 queues](https://github.com/omacom/linux-aurora/issues/25) |
| P1 | needs-retest | integration | [#26 M3 Air: qualify each shipped J613/J615 firmware profile separately](https://github.com/omacom/linux-aurora/issues/26) |
| P1 | investigation | kernel | [#27 Thunderbolt sink HPD loss: recover input switching without dock replug](https://github.com/omacom/linux-aurora/issues/27) |
| P1 | needs-retest | kernel | [#28 M2 Max direct USB-C: recover wake hotplug without a missing-event assumption](https://github.com/omacom/linux-aurora/issues/28) |
| P1 | blocked | desktop | [#29 Desktop handoff: upstream-compatible J293 SHM capture fix after resume](https://github.com/omacom/linux-aurora/issues/29) |
| P2 | investigation | kernel | [#30 M3 Pro: add correctly described PCIe tunnel hosts for remaining Thunderbolt ports](https://github.com/omacom/linux-aurora/issues/30) |
| P2 | investigation | kernel | [#31 J516S: 120 Hz mode produces approximately60 Hz page-flip completions](https://github.com/omacom/linux-aurora/issues/31) |
| P2 | investigation | kernel | [#32 14.x M3 panels: implement real backlight control on J613 and J516S](https://github.com/omacom/linux-aurora/issues/32) |
| P2 | investigation | kernel | [#33 J516S AOP: early firmware crash leaves ambient-light sensors absent](https://github.com/omacom/linux-aurora/issues/33) |
| P2 | needs-retest | kernel | [#34 J613 night light: confirm shipped D208 repair on the original14.x trigger](https://github.com/omacom/linux-aurora/issues/34) |
| P2 | investigation | integration | [#35 M3 Pro Vulkan: isolate vkQuake throughput deficit against matched workload](https://github.com/omacom/linux-aurora/issues/35) |
| P2 | candidate | integration | [#36 M3 Pro native OpenGL: package and qualify the working experimental desktop path](https://github.com/omacom/linux-aurora/issues/36) |
| P2 | needs-retest | kernel | [#37 J314S ACIO link error: recover black Studio Display while DRM still reports active](https://github.com/omacom/linux-aurora/issues/37) |
| P2 | needs-retest | kernel | [#38 Dock DPMS: establish whether CRTC off/on still tears down the tunnel](https://github.com/omacom/linux-aurora/issues/38) |
| P2 | investigation | kernel | [#39 Software-rendered desktop: make late USB-C hotplug obtain a usable display route](https://github.com/omacom/linux-aurora/issues/39) |
| P2 | needs-retest | kernel | [#40 External-display sleep: extend qualified behavior without bypassing M3 link guard](https://github.com/omacom/linux-aurora/issues/40) |
| P2 | needs-retest | kernel | [#41 Display routing: complete remaining board/port retests of the shipped CRTC fix](https://github.com/omacom/linux-aurora/issues/41) |
| P2 | investigation | kernel | [#42 M1 Pro SEP: retain unresolved attach and post-resume session failures](https://github.com/omacom/linux-aurora/issues/42) |
| P2 | blocked | desktop | [#43 Desktop handoff: qualify connector teardown fix through logout and greeter restart](https://github.com/omacom/linux-aurora/issues/43) |
| P2 | investigation | userspace | [#44 Browser AVD integration: enable hardware decode with the media sandbox retained](https://github.com/omacom/linux-aurora/issues/44) |
| P2 | needs-retest | kernel | [#45 Dual-stream 5K: qualify the integrated tile and rollback paths across supported boards](https://github.com/omacom/linux-aurora/issues/45) |
| P2 | investigation | integration | [#46 Per-Mac provisioning: document and test stock-install firmware and calibration](https://github.com/omacom/linux-aurora/issues/46) |
| P2 | investigation | installer | [#47 M3 Pro clean stage1: qualify explicit handoff admission on the supported stub](https://github.com/omacom/linux-aurora/issues/47) |
| P3 | needs-retest | kernel | [#48 Display audio: qualify HDMI/DP audio before changing its default](https://github.com/omacom/linux-aurora/issues/48) |
| P3 | candidate | installer | [#49 SMC survey test: synchronize stale-sample fixture without changing load safety](https://github.com/omacom/linux-aurora/issues/49) |
| P3 | blocked | kernel | [#50 J413/J415 hibernation: implement platform prerequisites before enabling images](https://github.com/omacom/linux-aurora/issues/50) |
| P3 | blocked | kernel | [#51 Neo AVE: complete standard video encoding and safe session teardown](https://github.com/omacom/linux-aurora/issues/51) |
| P3 | blocked | kernel | [#52 SEP login-keyring integration: decide a userspace API after persistence is sound](https://github.com/omacom/linux-aurora/issues/52) |
| P3 | investigation | kernel | [#53 T8112 Touch ID: describe data-ready interrupt without breaking working polling](https://github.com/omacom/linux-aurora/issues/53) |
| P3 | blocked | kernel | [#54 J613 legacy diagnostics: update prepared-image compute fixtures to the current ABI](https://github.com/omacom/linux-aurora/issues/54) |

## Candidate and existing pull requests

| PR | Disposition |
| --- | --- |
| [#55](https://github.com/omacom/linux-aurora/pull/55) | Joshua Warren’s resumable-download candidate, ported to the current baseline; draft pending the actual download/installer error controls. Continues personal #146. |
| [#16](https://github.com/omacom/linux-aurora/pull/16) | Joshua Warren’s G14X preemption candidate, already submitted directly in Omacom; review its generation/default dispatch and correctness/cost. Continues personal #137. No duplicate PR is needed. |
| [Personal #50](https://github.com/iconidentify/aurora-linux/pull/50) | Legacy prepared-image diagnostics are preserved, but need a current fixture rebase before reuse. Follow-up is [#54](https://github.com/omacom/linux-aurora/issues/54). |
| [#1](https://github.com/omacom/linux-aurora/pull/1), [#2](https://github.com/omacom/linux-aurora/pull/2), [#5](https://github.com/omacom/linux-aurora/pull/5), [#10](https://github.com/omacom/linux-aurora/pull/10) | Their exact source tips are contained in the current integration commit. No repeat import into this branch is needed; each existing PR retains its original target-branch context. |
| [#6](https://github.com/omacom/linux-aurora/pull/6), [#7](https://github.com/omacom/linux-aurora/pull/7), [#9](https://github.com/omacom/linux-aurora/pull/9) | Bluetooth, SEP and Thunderbolt work overlap current support. Compare the remaining production delta before proposing another import; a different commit ID alone is not missing functionality. |
| [#8](https://github.com/omacom/linux-aurora/pull/8) | J456 iMac speaker RFC: P3, explicit opt-in, not qualified for default amplifier enablement. Retain amplifier protection, DSP and hardware acceptance prerequisites. |

## Progress already established

Scott confirms the original Neo native-panel failure is resolved with live-session handoff: desktop, native GL and Honeykrisp Vulkan pass. His J613 exact26.6.2 installation cold-boots and passes the installed GPU checker. Neither establishes J615 hardware acceptance or full conformance. Exact26.6.2 Air profiles remain GL-only; 14.x/Pro Vulkan and Neo are distinct profiles.

The shared Thunderbolt clock fix, RX refill recovery, tile-following/rollback and base-M2 tunnel allowlists are already integrated. They are not still implementation candidates merely because the older roadmap listed them. Named display/board retests remain separate. M3 Pro still refuses actual system sleep while a display link is up; an EBUSY attempt is not a passed suspend/resume.

| Original fixed report | Matching acceptance; remaining work is separate |
| --- | --- |
| [#122 Neo native panel, desktop and GL/Vulkan](https://github.com/iconidentify/aurora-linux/issues/122) | Original reporter has a passing retest; follow-ups remain in the active queue. |
| [#84 AV1 original decode failure](https://github.com/iconidentify/aurora-linux/issues/84) | Original reporter has a passing retest; follow-ups remain in the active queue. |
| [#54 dma-buf plane offsets and video chroma](https://github.com/iconidentify/aurora-linux/issues/54) | Original reporter has a passing retest; follow-ups remain in the active queue. |
| [#33 J413/J415 SEP DMA, enrollment and reboot restore](https://github.com/iconidentify/aurora-linux/issues/33) | Original reporter has a passing retest; follow-ups remain in the active queue. |
| [#27 J314S dock-to-adapter recovery](https://github.com/iconidentify/aurora-linux/issues/27) | Original reporter has a passing retest; follow-ups remain in the active queue. |
| [#20 J516S Bluetooth startup](https://github.com/iconidentify/aurora-linux/issues/20) | Original reporter has a passing retest; follow-ups remain in the active queue. |

## Original open-thread destinations

Historical numbers below belong to `iconidentify/aurora-linux`. A migrated thread is not a claim that the bug was fixed.

| Original | Current disposition |
| --- | --- |
| [#5](https://github.com/iconidentify/aurora-linux/issues/5) | [#46](https://github.com/omacom/linux-aurora/issues/46) |
| [#12](https://github.com/iconidentify/aurora-linux/issues/12) | [#45](https://github.com/omacom/linux-aurora/issues/45) |
| [#13](https://github.com/iconidentify/aurora-linux/issues/13) | [#40](https://github.com/omacom/linux-aurora/issues/40) |
| [#16](https://github.com/iconidentify/aurora-linux/issues/16) | [#42](https://github.com/omacom/linux-aurora/issues/42), [#45](https://github.com/omacom/linux-aurora/issues/45) |
| [#18](https://github.com/iconidentify/aurora-linux/issues/18) | [#52](https://github.com/omacom/linux-aurora/issues/52) |
| [#19](https://github.com/iconidentify/aurora-linux/issues/19) | [#51](https://github.com/omacom/linux-aurora/issues/51) |
| [#20](https://github.com/iconidentify/aurora-linux/issues/20) | Original failure addressed; see separate capability/qualification tickets above |
| [#21](https://github.com/iconidentify/aurora-linux/issues/21) | [#33](https://github.com/omacom/linux-aurora/issues/33) |
| [#24](https://github.com/iconidentify/aurora-linux/issues/24) | [#37](https://github.com/omacom/linux-aurora/issues/37) |
| [#25](https://github.com/iconidentify/aurora-linux/issues/25) | [#42](https://github.com/omacom/linux-aurora/issues/42) |
| [#27](https://github.com/iconidentify/aurora-linux/issues/27) | Original failure addressed; see separate capability/qualification tickets above |
| [#28](https://github.com/iconidentify/aurora-linux/issues/28) | [#27](https://github.com/omacom/linux-aurora/issues/27) |
| [#29](https://github.com/iconidentify/aurora-linux/issues/29) | [#40](https://github.com/omacom/linux-aurora/issues/40) |
| [#30](https://github.com/iconidentify/aurora-linux/issues/30) | [#38](https://github.com/omacom/linux-aurora/issues/38) |
| [#31](https://github.com/iconidentify/aurora-linux/issues/31) | [#23](https://github.com/omacom/linux-aurora/issues/23) |
| [#33](https://github.com/iconidentify/aurora-linux/issues/33) | Original failure addressed; [#53](https://github.com/omacom/linux-aurora/issues/53) |
| [#35](https://github.com/iconidentify/aurora-linux/issues/35) | [#19](https://github.com/omacom/linux-aurora/issues/19), [#26](https://github.com/omacom/linux-aurora/issues/26) |
| [#38](https://github.com/iconidentify/aurora-linux/issues/38) | [#28](https://github.com/omacom/linux-aurora/issues/28) |
| [#39](https://github.com/iconidentify/aurora-linux/issues/39) | [#41](https://github.com/omacom/linux-aurora/issues/41) |
| [#40](https://github.com/iconidentify/aurora-linux/issues/40) | [#48](https://github.com/omacom/linux-aurora/issues/48) |
| [#41](https://github.com/iconidentify/aurora-linux/issues/41) | Replaced by [current roadmap](https://github.com/omacom/linux-aurora/issues/56) |
| [#49](https://github.com/iconidentify/aurora-linux/issues/49) | [#22](https://github.com/omacom/linux-aurora/issues/22), [#44](https://github.com/omacom/linux-aurora/issues/44) |
| [#50](https://github.com/iconidentify/aurora-linux/pull/50) | [#54](https://github.com/omacom/linux-aurora/issues/54) |
| [#53](https://github.com/iconidentify/aurora-linux/issues/53) | [#17](https://github.com/omacom/linux-aurora/issues/17) |
| [#54](https://github.com/iconidentify/aurora-linux/issues/54) | Original failure addressed; [#44](https://github.com/omacom/linux-aurora/issues/44) |
| [#55](https://github.com/iconidentify/aurora-linux/issues/55) | [#39](https://github.com/omacom/linux-aurora/issues/39) |
| [#56](https://github.com/iconidentify/aurora-linux/issues/56) | [#43](https://github.com/omacom/linux-aurora/issues/43) |
| [#57](https://github.com/iconidentify/aurora-linux/issues/57) | Replaced by [current roadmap](https://github.com/omacom/linux-aurora/issues/56) |
| [#74](https://github.com/iconidentify/aurora-linux/issues/74) | [#24](https://github.com/omacom/linux-aurora/issues/24) |
| [#75](https://github.com/iconidentify/aurora-linux/issues/75) | [#29](https://github.com/omacom/linux-aurora/issues/29) |
| [#79](https://github.com/iconidentify/aurora-linux/issues/79) | [#34](https://github.com/omacom/linux-aurora/issues/34) |
| [#80](https://github.com/iconidentify/aurora-linux/issues/80) | [#32](https://github.com/omacom/linux-aurora/issues/32) |
| [#82](https://github.com/iconidentify/aurora-linux/issues/82) | [#26](https://github.com/omacom/linux-aurora/issues/26) |
| [#84](https://github.com/iconidentify/aurora-linux/issues/84) | Original failure addressed; [#44](https://github.com/omacom/linux-aurora/issues/44) |
| [#86](https://github.com/iconidentify/aurora-linux/issues/86) | [#47](https://github.com/omacom/linux-aurora/issues/47) |
| [#87](https://github.com/iconidentify/aurora-linux/issues/87) | [#31](https://github.com/omacom/linux-aurora/issues/31), [#32](https://github.com/omacom/linux-aurora/issues/32) |
| [#99](https://github.com/iconidentify/aurora-linux/issues/99) | [#50](https://github.com/omacom/linux-aurora/issues/50) |
| [#103](https://github.com/iconidentify/aurora-linux/issues/103) | [#49](https://github.com/omacom/linux-aurora/issues/49) |
| [#109](https://github.com/iconidentify/aurora-linux/issues/109) | [#26](https://github.com/omacom/linux-aurora/issues/26) |
| [#122](https://github.com/iconidentify/aurora-linux/issues/122) | Original failure addressed; see separate capability/qualification tickets above |
| [#135](https://github.com/iconidentify/aurora-linux/issues/135) | [#20](https://github.com/omacom/linux-aurora/issues/20) |
| [#137](https://github.com/iconidentify/aurora-linux/pull/137) | Candidate continues in [PR #16](https://github.com/omacom/linux-aurora/pull/16) and [#25](https://github.com/omacom/linux-aurora/issues/25) |
| [#144](https://github.com/iconidentify/aurora-linux/issues/144) | [#30](https://github.com/omacom/linux-aurora/issues/30) |
| [#145](https://github.com/iconidentify/aurora-linux/issues/145) | [#35](https://github.com/omacom/linux-aurora/issues/35) |
| [#146](https://github.com/iconidentify/aurora-linux/pull/146) | Candidate continues in [PR #55](https://github.com/omacom/linux-aurora/pull/55) and [#18](https://github.com/omacom/linux-aurora/issues/18) |
| [#147](https://github.com/iconidentify/aurora-linux/issues/147) | [#21](https://github.com/omacom/linux-aurora/issues/21) |
