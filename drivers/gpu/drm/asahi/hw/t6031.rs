// SPDX-License-Identifier: GPL-2.0-only OR MIT
#![allow(dead_code)]

//! Hardware configuration for T6031 (M3 Max, G15C): one die, four clusters of ten core slots.
//!
//! Groundwork only: the T6031 M3 table (`m3_soc::T6031`) points at it, and nothing reads that
//! table yet. The addresses are CPU physical addresses from the J516C ADT, whose `/arm-io` maps
//! child 0 to 0x2_0000_0000 (not 0x2_1000_0000 as on T6030 and T8122), so no T6030 register
//! address is reused here unless the ADT shows the block at the same place.

use crate::f32;

use super::*;
use crate::t6031_knobs::{self as knobs, SUPERSET};

/// The firmware IO mappings, one per HwDataB slot (31 on G15). Each slot a start could fill has
/// its largest candidate here (`t6031_knobs::SUPERSET`); a slot none fills is `None`.
const fn io_mappings() -> [Option<IOMapping>; 31] {
    let mut table = [None; 31];
    let mut i = 0;
    while i < SUPERSET.len() {
        let (slot, phys, total, _, writable) = SUPERSET[i];
        let base = phys & !0x3fff;
        let size = ((phys & 0x3fff) + total as u64 + 0x3fff) & !0x3fff;
        table[slot] = Some(IOMapping::new(base as usize, false, 1, size as usize, 0, writable));
        i += 1;
    }
    table
}

const IO_MAPPINGS: [Option<IOMapping>; 31] = io_mappings();

/// T6031 (M3 Max, G15C): one die, four clusters of ten core slots, with CS and AFR clock domains.
pub(crate) const HWCONFIG_T6031: super::HwConfig = HwConfig {
    chip_id: 0x6031,
    gpu_gen: GpuGen::G15,       // ID_VERSION[31:24] == 7
    gpu_variant: GpuVariant::C, // ID_VERSION[23:16] == 4, one die
    // The next entry of the firmware core type list after G15G (22) and G15S (23); not
    // confirmed (`t6031_knobs::GPU_CORE` lists the alternatives).
    gpu_core: Some(GpuCore::G15C),

    // The 24 MHz reference clock, 42-bit UAT roots and output addresses, as on every AGX3 part.
    base_clock_hz: 24_000_000,
    uat_ias: 42,
    uat_oas: 42,
    num_dies: 1,
    // Four voltage tables in the ADT (perf-state-table-count 4), ten slots each.
    max_num_clusters: 4,
    max_num_cores: 10,
    max_num_frags: 10,
    max_num_gps: 4,

    // Not read by the M3 runtime, which keeps its own buffer layout (`m3_pass_layout`); the
    // T6030 values, which are t602x's per-cluster sizes.
    preempt1_size: 0x540,
    preempt2_size: 0x280,
    preempt3_size: 0x40,
    compute_preempt1_size: 0x25980,
    clustering: Some(HwClusteringConfig {
        meta1_blocksize: 0x44,
        meta2_size: 0xc0 * 16,
        meta3_size: 0x280 * 16,
        meta4_size: 0x10 * 128,
        max_splits: 64,
    }),
    render: HwRenderConfig {
        tiling_control: 0x180340,
    },

    // The T6030 values; the M3 runtime's InitData clears or replaces these words.
    da: HwConfigA {
        unk_87c: 500,
        unk_8cc: 11000,
        unk_e24: 125,
    },
    db: HwConfigB {
        // The chip revision's major number: /arm-io chip-revision 0x12 >> 4.
        unk_454: 1,
        unk_4e0: 4,
        unk_534: 0,
        unk_ab8: 0,
        unk_abc: 0,
        unk_b30: 0,
    },
    // G15 leaves the hws1/hws2/hws3 curves zero.
    shared1_tab: &[],
    shared1_a4: 0,
    shared2_tab: &[],
    shared2_unk_508: 0,
    shared2_curves: None,
    shared3_unk: 0,
    shared3_tab: &[],
    // The J516C ADT's gpu-idleoff-standby-timer.
    idle_off_standby_timer_default: 1500,
    unk_hws2_4: Some(f32!([1.0, 0.8, 0.2, 0.9, 0.1, 0.25, 0.7, 0.9])),
    unk_hws2_24: 6,
    global_unk_54: 4000,
    sram_k: f32!(1.02),
    unk_coef_a: &[],
    unk_coef_b: &[],
    global_tab: Some(&[
        0x00, 0x01, 0x02, 0x01, 0x01, 0x5a, 0x4b, 0x01, 0x01, 0x01, 0x02, 0x5a, 0x4b, 0x01, 0x01,
        0x01, 0x01, 0x5a, 0x4b, 0x01, 0x01,
    ]),
    // The J516C ADT has cs-perf-states and afr-perf-states. HWCONFIG_T6031_NO_CSAFR is the same
    // without them, for a boot loader that does not give the CS/AFR tables.
    has_csafr: true,
    // Not known: the ADT's fast-die mask (0x8080) is not in the runtime's form
    // (`t6031_knobs::MTR_*` lists the candidates).
    fast_sensor_mask: [0, 0],
    fast_sensor_mask_alt: [0, 0],
    fast_die0_sensor_present: 0,
    io_mappings: &IO_MAPPINGS,
    // Fender scratch SRAM: Fender + 0x60000, 128 KiB, as on T6030.
    sram_base: Some(knobs::FENDER as usize + 0x6_0000),
    sram_size: Some(0x20000),
};

/// The same without the CS and AFR performance states.
pub(crate) const HWCONFIG_T6031_NO_CSAFR: super::HwConfig = HwConfig {
    has_csafr: false,
    ..HWCONFIG_T6031
};

/// Both configurations as statics: the runtime's UAT check (`mmu`) compares the table's
/// configuration by address.
pub(crate) static CONFIG: HwConfig = HWCONFIG_T6031;
pub(crate) static CONFIG_NO_CSAFR: HwConfig = HWCONFIG_T6031_NO_CSAFR;
