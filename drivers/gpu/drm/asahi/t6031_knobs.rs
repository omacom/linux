// SPDX-License-Identifier: GPL-2.0-only OR MIT
#![cfg_attr(not(test), allow(dead_code))]

//! Definitions for a T6031 (M3 Max, G15C) GPU start: the values of the G15C runtime
//! configuration that the J516C device tree does not give, each with a default and the
//! alternatives to try, and the firmware IO mappings they select. Data only: no kernel parameter
//! reads them and nothing in the driver uses them yet. The host tests (tools/asahi) check them.
//!
//! The names are the parameter names a start would take (`asahi.t6031_<name>`). A value a
//! definition does not accept is a refusal naming it, never a fall back to the default.

/// A parameter that is not given.
pub(crate) const UNSET: u64 = u64::MAX;
/// A parameter whose text is not one of its accepted values.
pub(crate) const INVALID: u64 = u64::MAX - 1;

/// The GPU register window (ADT sgx reg[0], CPU physical).
pub(crate) const SGX: u64 = 0x4_0800_0000;
/// Its size in the ADT.
pub(crate) const SGX_SIZE: u64 = 0x3fd_c000;
/// The Fender block (ADT sgx reg[1]), SGX + 0xd00000 as on T6030 and T8122.
pub(crate) const FENDER: u64 = SGX + 0xd0_0000;
/// The interrupt controller of die 0 (`t6031-die0.dtsi`).
pub(crate) const AIC: u64 = 0x2_9240_0000;
/// The Fender window sizes: the ADT sgx reg[1] size (0x16c000) less 0x28000, the difference on
/// T6030 and T8122 (the default), and the whole ADT range.
pub(crate) const FENDER_RULE: u32 = 0x14_4000;
pub(crate) const FENDER_ADT: u32 = 0x16_c000;
/// The GPU clock-generator offsets in SGX: T6030's (the default; the T6031 GPU block keeps the
/// T6030 offsets of every block the ADT shows) and T8122's.
pub(crate) const CLOCK_GEN_E5C: u64 = 0xe5_c000;
pub(crate) const CLOCK_GEN_E1C: u64 = 0xe1_c000;
/// The SGX setup write of T6030 and T8122 (offset, value).
pub(crate) const SGX_SETUP: (usize, u32) = (0xd1_4000, 0x7_0001);
/// The memory-cache candidates: elements of T6030's size from T6030's base.
pub(crate) const MCACHE_BASE: u64 = 0x2_2000_0000;
pub(crate) const MCACHE_ELEMENT: u32 = 0x9_5000;
pub(crate) const MCACHE_MAX: u32 = 8;
/// The ANE doorbell register of T6030 and of T8122.
pub(crate) const ANE_T6030: u64 = 0x3_0945_c000;
pub(crate) const ANE_T8122: u64 = 0x3_1145_c000;
/// The CPU physical range an address given for a slot must lie in: the SoC register space
/// below DRAM that `/arm-io` maps on T6031.
pub(crate) const MMIO_START: u64 = 0x2_0000_0000;
pub(crate) const MMIO_END: u64 = 0x6_0000_0000;
/// The default performance-state ceiling: the lowest state.
pub(crate) const PSTATE_CAP: u32 = 1;
/// The highest ceiling accepted: the driver's own limit without its temperature controller
/// (`m3_adt_config::ADT_MAX_PSTATE_LIMIT`).
pub(crate) const PSTATE_CAP_MAX: u32 = 5;
/// The default unit masks: T6030's, with one cluster bit for each of the four clusters.
pub(crate) const UNIT_MASK_A: u64 = 0x7_0000_000f;
pub(crate) const UNIT_MASK_B: u32 = 0x7;
pub(crate) const UNIT_MASK_A_LIMIT: u64 = 0x7_0000_000f;
pub(crate) const UNIT_MASK_B_LIMIT: u64 = 0xf;
/// The default HwDataB words: +0xa2c the chip revision's major number (/arm-io chip-revision
/// 0x12 >> 4), +0xb20 the core slots (4 x 10), +0x17b8 and +0x1818 T6030's.
pub(crate) const HWB_454: u32 = 1;
pub(crate) const HWB_B20: u32 = 0x28;
pub(crate) const HWB_17B8: u32 = 5;
pub(crate) const HWB_1818: u32 = 1;
/// The default firmware GPU core type: G15C in the firmware's core type list (`hw::GpuCore`,
/// where G15G = 22 and G15S = 23 are the values the T8122 and T6030 firmware take).
pub(crate) const GPU_CORE: u32 = 24;
/// The power target while the boot loader's power model is a stand-in, in mW.
pub(crate) const POWER_CAP_MW: u32 = 30_000;
pub(crate) const POWER_CAP_MW_RANGE: (u32, u32) = (5_000, 80_000);
/// The MTR masks of the `t6030` and `t8122` choices (fast die, alarm).
pub(crate) const MTR_T6030: (u64, u64) = (0x402a_002b, 0);
pub(crate) const MTR_T8122: (u64, u64) = (0x4248, 0x4b48);

/// Parse a decimal or `0x`-prefixed hexadecimal `u64`. A leading sign is not accepted.
fn number(text: &str) -> Option<u64> {
    if text.starts_with(['+', '-']) {
        return None;
    }
    match text.strip_prefix("0x").or_else(|| text.strip_prefix("0X")) {
        Some(hex) if !hex.starts_with(['+', '-']) => u64::from_str_radix(hex, 16).ok(),
        Some(_) => None,
        None => text.parse::<u64>().ok(),
    }
}

/// Parse a parameter's text: one of `names`, else a number. Anything else, and the two
/// reserved values, give [`INVALID`].
fn parse(text: &str, names: &[(&str, u64)]) -> u64 {
    let text = text.trim();
    if let Some(&(_, value)) = names.iter().find(|(name, _)| *name == text) {
        return value;
    }
    number(text).filter(|v| *v < INVALID).unwrap_or(INVALID)
}

pub(crate) fn parse_number(text: &str) -> u64 {
    parse(text, &[])
}

pub(crate) fn parse_fender(text: &str) -> u64 {
    parse(text, &[("rule", FENDER_RULE as u64), ("adt", FENDER_ADT as u64)])
}

/// `none` is 1, so that 0 is never a clock-generator offset.
pub(crate) fn parse_clkgen(text: &str) -> u64 {
    parse(text, &[("e5c", CLOCK_GEN_E5C), ("e1c", CLOCK_GEN_E1C), ("none", 1)])
}

pub(crate) fn parse_sgx_setup(text: &str) -> u64 {
    parse(text, &[("none", 0), ("t6030", 1)])
}

pub(crate) fn parse_mcache(text: &str) -> u64 {
    parse(text, &[("none", 0), ("x2", 2), ("x4", 4), ("x8", 8)])
}

pub(crate) fn parse_aic_swint(text: &str) -> u64 {
    parse(text, &[("page", 0), ("reg", 1)])
}

pub(crate) fn parse_slot7(text: &str) -> u64 {
    parse(text, &[("none", 0), ("rule", 1)])
}

pub(crate) fn parse_gifaf(text: &str) -> u64 {
    parse(text, &[("none", 0), ("fender", 1)])
}

/// An unknown slot: `none` (0) or a page-aligned physical address.
pub(crate) fn parse_slot(text: &str) -> u64 {
    parse(text, &[("none", 0)])
}

pub(crate) fn parse_ane(text: &str) -> u64 {
    parse(text, &[("none", 0), ("t6030", ANE_T6030), ("t8122", ANE_T8122)])
}

pub(crate) fn parse_mtr(text: &str) -> u64 {
    parse(text, &[("t6030", 0), ("t8122", 1), ("adt", 2), ("none", 3)])
}

pub(crate) fn parse_fw_words(text: &str) -> u64 {
    parse(text, &[("none", 0), ("t8122", 1)])
}

pub(crate) fn parse_hwdata_object(text: &str) -> u64 {
    parse(text, &[("fixed", 0), ("aligned", 1)])
}

/// `auto` is unset: the revision read decides.
pub(crate) fn parse_rev_id(text: &str) -> u64 {
    parse(text, &[("auto", UNSET - 2)])
}

pub(crate) fn parse_tristate(text: &str) -> u64 {
    parse(text, &[("auto", 0), ("on", 1), ("off", 2)])
}

/// `search` (the default) finds the tag in the loaded image.
pub(crate) fn parse_tag(text: &str) -> u64 {
    parse(text, &[("search", UNSET - 2)])
}

/// Parse a UUID: 32 hexadecimal digits, with or without the four dashes.
pub(crate) fn parse_uuid(text: &str) -> Option<[u8; 16]> {
    let text = text.trim();
    let dashes = text.bytes().filter(|b| *b == b'-').count();
    let hex = text.bytes().filter(|b| *b != b'-');
    if (dashes != 0 && dashes != 4) || text.len() != 32 + dashes {
        return None;
    }
    if dashes == 4 && [8, 13, 18, 23].iter().any(|i| text.as_bytes()[*i] != b'-') {
        return None;
    }
    let mut uuid = [0u8; 16];
    for (i, digit) in hex.enumerate() {
        let v = (digit as char).to_digit(16)? as u8;
        uuid[i / 2] |= v << if i % 2 == 0 { 4 } else { 0 };
    }
    Some(uuid)
}

/// The UUID parameter as given.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub(crate) enum UuidParam {
    Unset,
    Invalid,
    Set([u8; 16]),
}

/// The parameters as given: [`UNSET`], [`INVALID`] or a value.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub(crate) struct Raw {
    pub(crate) start: u64,
    pub(crate) image_uuid: UuidParam,
    pub(crate) image_hash: u64,
    pub(crate) tag: u64,
    pub(crate) initdata_version: u64,
    pub(crate) pstate_cap: u64,
    pub(crate) fender: u64,
    pub(crate) clkgen: u64,
    pub(crate) sgx_setup: u64,
    pub(crate) mcache: u64,
    pub(crate) aic_swint: u64,
    pub(crate) slot7: u64,
    pub(crate) gifaf: u64,
    pub(crate) slot21: u64,
    pub(crate) slot24: u64,
    pub(crate) slot28: u64,
    pub(crate) ane: u64,
    pub(crate) io_drop: u64,
    pub(crate) mtr: u64,
    pub(crate) mtr_fast_die: u64,
    pub(crate) mtr_alarm: u64,
    pub(crate) unit_mask_a: u64,
    pub(crate) unit_mask_b: u64,
    pub(crate) hwb_454: u64,
    pub(crate) hwb_b20: u64,
    pub(crate) hwb_17b8: u64,
    pub(crate) hwb_1818: u64,
    pub(crate) fw_words: u64,
    pub(crate) hwdata_object: u64,
    pub(crate) gpu_core: u64,
    pub(crate) rev_id: u64,
    pub(crate) csafr: u64,
    pub(crate) power_cap_mw: u64,
}

impl Raw {
    /// No parameter given.
    pub(crate) const NONE: Raw = Raw {
        start: UNSET,
        image_uuid: UuidParam::Unset,
        image_hash: UNSET,
        tag: UNSET,
        initdata_version: UNSET,
        pstate_cap: UNSET,
        fender: UNSET,
        clkgen: UNSET,
        sgx_setup: UNSET,
        mcache: UNSET,
        aic_swint: UNSET,
        slot7: UNSET,
        gifaf: UNSET,
        slot21: UNSET,
        slot24: UNSET,
        slot28: UNSET,
        ane: UNSET,
        io_drop: UNSET,
        mtr: UNSET,
        mtr_fast_die: UNSET,
        mtr_alarm: UNSET,
        unit_mask_a: UNSET,
        unit_mask_b: UNSET,
        hwb_454: UNSET,
        hwb_b20: UNSET,
        hwb_17b8: UNSET,
        hwb_1818: UNSET,
        fw_words: UNSET,
        hwdata_object: UNSET,
        gpu_core: UNSET,
        rev_id: UNSET,
        csafr: UNSET,
        power_cap_mw: UNSET,
    };

    /// Whether any parameter other than `t6031_start` was given.
    pub(crate) fn values_given(&self) -> bool {
        self.image_uuid != UuidParam::Unset
            || [
                self.image_hash,
                self.tag,
                self.initdata_version,
                self.pstate_cap,
                self.fender,
                self.clkgen,
                self.sgx_setup,
                self.mcache,
                self.aic_swint,
                self.slot7,
                self.gifaf,
                self.slot21,
                self.slot24,
                self.slot28,
                self.ane,
                self.io_drop,
                self.mtr,
                self.mtr_fast_die,
                self.mtr_alarm,
                self.unit_mask_a,
                self.unit_mask_b,
                self.hwb_454,
                self.hwb_b20,
                self.hwb_17b8,
                self.hwb_1818,
                self.fw_words,
                self.hwdata_object,
                self.gpu_core,
                self.rev_id,
                self.csafr,
                self.power_cap_mw,
            ]
            .iter()
            .any(|v| *v != UNSET)
    }
}

/// What `t6031_start` asks for.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub(crate) enum Start {
    /// Not given, or 0.
    Off,
    /// 1.
    On,
    /// Anything else.
    Invalid,
}

pub(crate) fn start(raw: &Raw) -> Start {
    match raw.start {
        UNSET | 0 => Start::Off,
        1 => Start::On,
        _ => Start::Invalid,
    }
}

/// An `auto`/`on`/`off` choice.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub(crate) enum Tristate {
    Auto,
    On,
    Off,
}

fn tristate(v: u64) -> Option<Tristate> {
    match v {
        UNSET | 0 => Some(Tristate::Auto),
        1 => Some(Tristate::On),
        2 => Some(Tristate::Off),
        _ => None,
    }
}

/// The AIC software-interrupt mapping of slot 2.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub(crate) enum AicSwInt {
    /// The 16 KiB page at AIC + 0x14000, as on T6030 (the default).
    Page,
    /// The one register the ADT's meta-sw-interrupt names (AIC + 0x14084), as T8122 maps its own.
    Register,
}

/// The MTR sensor masks: from a choice, or as given.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub(crate) enum Mtr {
    /// Fast-die and alarm masks.
    Masks(u64, u64),
    /// The boot loader's `apple,fast-die0-sensor-mask` as the fast-die mask, no alarm mask.
    Adt,
}

/// The values of one boot.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub(crate) struct Values {
    pub(crate) image_uuid: Option<[u8; 16]>,
    pub(crate) image_hash: Option<u64>,
    pub(crate) tag: Option<usize>,
    pub(crate) initdata_version: u64,
    pub(crate) pstate_cap: u32,
    pub(crate) fender: u32,
    pub(crate) clock_gen: Option<u64>,
    pub(crate) sgx_setup: Option<(usize, u32)>,
    pub(crate) mcache: u32,
    pub(crate) aic_swint: AicSwInt,
    pub(crate) slot7: bool,
    pub(crate) gifaf: bool,
    pub(crate) slot21: Option<u64>,
    pub(crate) slot24: Option<u64>,
    pub(crate) slot28: Option<u64>,
    pub(crate) ane: Option<u64>,
    pub(crate) io_drop: u32,
    pub(crate) mtr: Mtr,
    pub(crate) unit_mask_a: u64,
    pub(crate) unit_mask_b: u32,
    pub(crate) hwb_454: u32,
    pub(crate) hwb_b20: u32,
    pub(crate) hwb_17b8: u32,
    pub(crate) hwb_1818: u32,
    pub(crate) fw_words: bool,
    pub(crate) hwdata_aligned: bool,
    pub(crate) gpu_core: u32,
    pub(crate) rev_id: Option<u32>,
    pub(crate) csafr: Tristate,
    pub(crate) power_cap_mw: u32,
}

/// A parameter given with a value it does not accept: its name and what it accepts.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub(crate) struct Refusal {
    pub(crate) name: &'static str,
    pub(crate) accepts: &'static str,
}

/// A parameter's value, its default when not given; None when invalid.
fn given(param: u64, default: u64) -> Option<u64> {
    match param {
        UNSET => Some(default),
        INVALID => None,
        v => Some(v),
    }
}

/// The default slots a tester may leave out with `t6031_io_drop`: all but Fender (0), RGX
/// (3) and the clock generator (29, which has its own parameter).
pub(crate) const IO_DROP_ALLOWED: u32 =
    (1 << 1) | (1 << 2) | (1 << 9) | (1 << 12) | (1 << 18) | (1 << 19) | (1 << 20) | (1 << 23)
        | (1 << 26);

/// An address for an unknown slot: 0 (none), or a 16 KiB-aligned address in the SoC register
/// space outside the GPU's own blocks that have a slot.
fn slot_address(v: u64) -> Option<Option<u64>> {
    match v {
        0 => Some(None),
        v if v % 0x4000 == 0 && (MMIO_START..MMIO_END).contains(&v) => Some(Some(v)),
        _ => None,
    }
}

/// Resolve the parameters. The first parameter with a value it does not accept is the refusal.
pub(crate) fn resolve(raw: &Raw) -> Result<Values, Refusal> {
    let refuse = |name, accepts| Refusal { name, accepts };
    let image_uuid = match raw.image_uuid {
        UuidParam::Unset => None,
        UuidParam::Set(uuid) => Some(uuid),
        UuidParam::Invalid => {
            return Err(refuse("t6031_image_uuid", "32 hexadecimal digits, with or without dashes"))
        }
    };
    let image_hash = match raw.image_hash {
        UNSET => None,
        INVALID => return Err(refuse("t6031_image_hash", "16 hexadecimal digits: the first 8 bytes of the image text SHA-256")),
        v => Some(v),
    };
    let tag = match raw.tag {
        UNSET | 0xffff_ffff_ffff_fffd => None,
        v if v < 0x6_4000 - 16 => Some(v as usize),
        _ => return Err(refuse("t6031_tag", "search, or an offset inside the text segment")),
    };
    let initdata_version = given(raw.initdata_version, crate::m3_firmware::G15_V14_8_3_INITDATA)
        .filter(|v| *v != 0)
        .ok_or(refuse("t6031_initdata_version", "a nonzero number, at most 0xfffffffffffffffd"))?;
    let pstate_cap = given(raw.pstate_cap, PSTATE_CAP as u64)
        .filter(|v| (1..=u64::from(PSTATE_CAP_MAX)).contains(v))
        .ok_or(refuse("t6031_pstate_cap", "1 to 5"))? as u32;
    let fender = match given(raw.fender, FENDER_RULE as u64) {
        Some(v) if v == FENDER_RULE as u64 || v == FENDER_ADT as u64 => v as u32,
        _ => return Err(refuse("t6031_fender", "rule (0x144000) or adt (0x16c000)")),
    };
    let clock_gen = match given(raw.clkgen, CLOCK_GEN_E5C) {
        Some(1) => None,
        Some(v) if v == CLOCK_GEN_E5C || v == CLOCK_GEN_E1C => Some(v),
        _ => return Err(refuse("t6031_clkgen", "e5c, e1c or none")),
    };
    let sgx_setup = match given(raw.sgx_setup, 1) {
        Some(0) => None,
        Some(1) => Some(SGX_SETUP),
        _ => return Err(refuse("t6031_sgx_setup", "t6030 or none")),
    };
    let mcache = match given(raw.mcache, 0) {
        Some(v @ (0 | 2 | 4 | 8)) => v as u32,
        _ => return Err(refuse("t6031_mcache", "none, x2, x4 or x8")),
    };
    let aic_swint = match given(raw.aic_swint, 0) {
        Some(0) => AicSwInt::Page,
        Some(1) => AicSwInt::Register,
        _ => return Err(refuse("t6031_aic_swint", "page or reg")),
    };
    let slot7 = match given(raw.slot7, 0) {
        Some(v @ (0 | 1)) => v == 1,
        _ => return Err(refuse("t6031_slot7", "none or rule")),
    };
    let gifaf = match given(raw.gifaf, 0) {
        Some(v @ (0 | 1)) => v == 1,
        _ => return Err(refuse("t6031_gifaf", "none or fender")),
    };
    const SLOT: &str = "none, or a 16 KiB-aligned address from 0x200000000 below 0x600000000";
    let slot21 = given(raw.slot21, 0).and_then(slot_address).ok_or(refuse("t6031_slot21", SLOT))?;
    let slot24 = given(raw.slot24, 0).and_then(slot_address).ok_or(refuse("t6031_slot24", SLOT))?;
    let slot28 = given(raw.slot28, 0).and_then(slot_address).ok_or(refuse("t6031_slot28", SLOT))?;
    let ane = match given(raw.ane, 0) {
        Some(0) => None,
        Some(v) if (MMIO_START..MMIO_END).contains(&v) && v % 0x1000 == 0 => Some(v),
        _ => {
            return Err(refuse(
                "t6031_ane",
                "none, t6030, t8122, or a 4 KiB-aligned address from 0x200000000 below 0x600000000",
            ))
        }
    };
    let io_drop = given(raw.io_drop, 0)
        .filter(|v| *v & !u64::from(IO_DROP_ALLOWED) == 0)
        .ok_or(refuse("t6031_io_drop", "a mask of slots 1, 2, 9, 12, 18, 19, 20, 23 and 26"))?
        as u32;
    let mtr_choice = match given(raw.mtr, 0) {
        Some(0) => Mtr::Masks(MTR_T6030.0, MTR_T6030.1),
        Some(1) => Mtr::Masks(MTR_T8122.0, MTR_T8122.1),
        Some(2) => Mtr::Adt,
        Some(3) => Mtr::Masks(0, 0),
        _ => return Err(refuse("t6031_mtr", "t6030, t8122, adt or none")),
    };
    let fast_die = match raw.mtr_fast_die {
        UNSET => None,
        INVALID => return Err(refuse("t6031_mtr_fast_die", "a 64-bit mask")),
        v => Some(v),
    };
    let alarm = match raw.mtr_alarm {
        UNSET => None,
        INVALID => return Err(refuse("t6031_mtr_alarm", "a 64-bit mask")),
        v => Some(v),
    };
    let mtr = match (mtr_choice, fast_die, alarm) {
        (m, None, None) => m,
        (Mtr::Masks(f, a), fast, alarm) => Mtr::Masks(fast.unwrap_or(f), alarm.unwrap_or(a)),
        (Mtr::Adt, _, _) => {
            return Err(refuse("t6031_mtr", "t6030, t8122 or none with t6031_mtr_fast_die/_alarm"))
        }
    };
    let unit_mask_a = given(raw.unit_mask_a, UNIT_MASK_A)
        .filter(|v| *v != 0 && *v & !UNIT_MASK_A_LIMIT == 0)
        .ok_or(refuse("t6031_unit_mask_a", "nonzero, no bits outside 0x70000000f"))?;
    let unit_mask_b = given(raw.unit_mask_b, UNIT_MASK_B as u64)
        .filter(|v| *v != 0 && *v & !UNIT_MASK_B_LIMIT == 0)
        .ok_or(refuse("t6031_unit_mask_b", "nonzero, no bits outside 0xf"))? as u32;
    let word = |v: u64, d: u32, name: &'static str| {
        given(v, u64::from(d))
            .filter(|v| *v <= u64::from(u32::MAX))
            .map(|v| v as u32)
            .ok_or(refuse(name, "a 32-bit number"))
    };
    let hwb_454 = word(raw.hwb_454, HWB_454, "t6031_hwb_454")?;
    let hwb_b20 = word(raw.hwb_b20, HWB_B20, "t6031_hwb_b20")?;
    let hwb_17b8 = word(raw.hwb_17b8, HWB_17B8, "t6031_hwb_17b8")?;
    let hwb_1818 = word(raw.hwb_1818, HWB_1818, "t6031_hwb_1818")?;
    let fw_words = match given(raw.fw_words, 0) {
        Some(v @ (0 | 1)) => v == 1,
        _ => return Err(refuse("t6031_fw_words", "none or t8122")),
    };
    let hwdata_aligned = match given(raw.hwdata_object, 1) {
        Some(v @ (0 | 1)) => v == 1,
        _ => return Err(refuse("t6031_hwdata_object", "aligned or fixed")),
    };
    let gpu_core = given(raw.gpu_core, u64::from(GPU_CORE))
        .filter(|v| (19..=25).contains(v))
        .ok_or(refuse("t6031_gpu_core", "19 to 25"))? as u32;
    let rev_id = match raw.rev_id {
        UNSET | 0xffff_ffff_ffff_fffd => None,
        v if (1..=8).contains(&v) => Some(v as u32),
        _ => return Err(refuse("t6031_rev_id", "auto, or 1 to 8")),
    };
    let csafr = tristate(raw.csafr).ok_or(refuse("t6031_csafr", "auto, on or off"))?;
    let power_cap_mw = given(raw.power_cap_mw, u64::from(POWER_CAP_MW))
        .filter(|v| {
            (u64::from(POWER_CAP_MW_RANGE.0)..=u64::from(POWER_CAP_MW_RANGE.1)).contains(v)
        })
        .ok_or(refuse("t6031_power_cap_mw", "5000 to 80000"))? as u32;
    Ok(Values {
        image_uuid,
        image_hash,
        tag,
        initdata_version,
        pstate_cap,
        fender,
        clock_gen,
        sgx_setup,
        mcache,
        aic_swint,
        slot7,
        gifaf,
        slot21,
        slot24,
        slot28,
        ane,
        io_drop,
        mtr,
        unit_mask_a,
        unit_mask_b,
        hwb_454,
        hwb_b20,
        hwb_17b8,
        hwb_1818,
        fw_words,
        hwdata_aligned,
        gpu_core,
        rev_id,
        csafr,
        power_cap_mw,
    })
}

impl Values {
    /// The MTR masks (fast die, alarm), given the boot loader's fast-die sensor mask.
    pub(crate) fn mtr_masks(&self, adt_fast_die: u64) -> (u64, u64) {
        match self.mtr {
            Mtr::Masks(f, a) => (f, a),
            Mtr::Adt => (adt_fast_die, 0),
        }
    }

    /// Whether this boot publishes the CS and AFR performance states, given whether the boot
    /// loader added every property they need.
    pub(crate) fn csafr(&self, described: bool) -> bool {
        match self.csafr {
            Tristate::Auto => described,
            Tristate::On => true,
            Tristate::Off => false,
        }
    }

    /// The firmware's revision id: as given, or for the revision read, the one the firmware's
    /// revision list gives it. Revision 0x12 has no entry in that list; it takes B1's (4), the
    /// nearest earlier revision, until a start shows otherwise.
    pub(crate) fn rev_id(&self, revision: u32) -> Option<u32> {
        self.rev_id.or(match revision {
            0x00 => Some(1),
            0x01 => Some(2),
            0x10 => Some(3),
            0x11 | 0x12 => Some(4),
            0x20 => Some(5),
            0x21 => Some(6),
            _ => None,
        })
    }

    /// The physical address of the clock generator, if mapped.
    pub(crate) fn clock_gen_address(&self) -> Option<u64> {
        self.clock_gen.map(|offset| SGX + offset)
    }
}

/// One firmware IO mapping: HwDataB slot, physical address, total size, element size, writable
/// (the form of `m3_soc::IoMapping`).
pub(crate) type Mapping = (usize, u64, u32, u32, bool);

/// The number of HwDataB slots the definitions can fill.
pub(crate) const SLOTS: usize = 19;

/// Every slot the definitions can fill, in slot order, each with its largest choice. Laid out once
/// for these (`m3_init_storage::pack_iomaps`), no slot's firmware VA would depend on the values
/// chosen, so a fault address would name the same slot on every boot.
pub(crate) const SUPERSET: [Mapping; SLOTS] = [
    (0, FENDER, FENDER_ADT, FENDER_ADT, true),
    (1, 0x2_0e10_1000, 1, 1, false),
    (2, AIC + 0x1_4000, 0x4000, 0x4000, true),
    (3, SGX, 0x2_0000, 0x2_0000, true),
    (7, 0x2_902b_c000, 0x1000, 0x1000, false),
    (9, SGX + 0xe0_8000, 0x8000, 0x8000, true),
    (10, FENDER + 0xd000, 0x1000, 0x1000, true),
    (11, MCACHE_BASE, MCACHE_MAX * MCACHE_ELEMENT, MCACHE_ELEMENT, true),
    (12, AIC + 0x4_c000, 0x4000, 0x4000, false),
    (18, 0x2_903d_0000, 0x4000, 0x4000, true),
    (19, 0x2_903c_0000, 0x4000, 0x4000, false),
    (20, 0x2_903d_8000, 0x4000, 0x4000, true),
    (21, MMIO_START, 0x4000, 0x4000, false),
    (23, SGX + 0x300_0000, 0x40_0000, 0x40_0000, true),
    (24, MMIO_START, 0x4000, 0x4000, false),
    (25, ANE_T6030, 0x4000, 0x4000, true),
    (26, 0x2_9028_0000, 0x8000, 0x8000, false),
    (28, MMIO_START, 0x4000, 0x4000, false),
    (29, SGX + CLOCK_GEN_E5C, 0x4000, 0x4000, false),
];

/// The slots to map read-only for the firmware when present: those whose address is a candidate
/// rather than a value of the ADT or of the T6030 table's rule (7, 21, 24, 28), and the clock
/// generator (29), which the T8122 start also maps read-only.
pub(crate) const READ_ONLY_SLOTS: u32 = (1 << 7) | (1 << 21) | (1 << 24) | (1 << 28) | (1 << 29);

/// The IO mappings of one boot, in slot order, and how many there are.
pub(crate) fn mappings(v: &Values) -> ([Mapping; SLOTS], usize) {
    let mut out = [(0, 0, 0, 0, false); SLOTS];
    let mut n = 0;
    let mut push = |m: Mapping| {
        out[n] = m;
        n += 1;
    };
    let keep = |slot: usize| v.io_drop & (1 << slot) == 0;
    push((0, FENDER, v.fender, v.fender, true));
    if keep(1) {
        push(SUPERSET[1]);
    }
    if keep(2) {
        push(match v.aic_swint {
            AicSwInt::Page => SUPERSET[2],
            AicSwInt::Register => (2, AIC + 0x1_4084, 1, 1, true),
        });
    }
    push(SUPERSET[3]);
    if v.slot7 {
        push(SUPERSET[4]);
    }
    if keep(9) {
        push(SUPERSET[5]);
    }
    if v.gifaf {
        push(SUPERSET[6]);
    }
    if v.mcache != 0 {
        push((11, MCACHE_BASE, v.mcache * MCACHE_ELEMENT, MCACHE_ELEMENT, true));
    }
    for (slot, at) in [(12, 8), (18, 9), (19, 10), (20, 11)] {
        if keep(slot) {
            push(SUPERSET[at]);
        }
    }
    if let Some(a) = v.slot21 {
        push((21, a, 0x4000, 0x4000, false));
    }
    if keep(23) {
        push(SUPERSET[13]);
    }
    if let Some(a) = v.slot24 {
        push((24, a, 0x4000, 0x4000, false));
    }
    if let Some(a) = v.ane {
        push((25, a, 1, 1, true));
    }
    if keep(26) {
        push(SUPERSET[16]);
    }
    if let Some(a) = v.slot28 {
        push((28, a, 0x4000, 0x4000, false));
    }
    if let Some(a) = v.clock_gen_address() {
        push((29, a, 0x4000, 0x4000, false));
    }
    (out, n)
}

/// The GPU identity the boot loader read with the GPU powered
/// (`/chosen/asahi,t6031-gpu-powered-identity`, the naming contract), and the checks it must pass.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub(crate) struct Identity {
    /// SGX+0xd04000: family [31:24], variant [23:16], revision [15:8].
    pub(crate) id_version: u32,
    /// The revision byte.
    pub(crate) revision: u32,
    /// The core-enable mask over the 40 core slots, cluster 0 lowest.
    pub(crate) core_mask: u64,
    pub(crate) active_cores: u32,
}

/// The core slots of T6031: four clusters of ten.
pub(crate) const CORE_SLOTS: u32 = 40;

/// The GPU revisions with an entry in the revision lists, as the revision byte of the
/// identification word.
pub(crate) const REVISIONS: [u32; 7] = [0x00, 0x01, 0x10, 0x11, 0x12, 0x20, 0x21];

/// Admit the boot loader's reading: the 14.8.3 firmware ABI, a successful guarded read
/// (schema 1, result 1), family 7 variant 4 (G15C), a known revision byte, and a nonzero core
/// mask within the 40 core slots (`masks` are core-mask-0 to core-mask-3; the last two must be 0).
/// The refusal names what failed.
pub(crate) fn validate_identity(
    firmware_compat: &[u32],
    schema: u32,
    result: u32,
    id_version: u32,
    masks: [u32; 4],
) -> Result<Identity, &'static str> {
    if firmware_compat != [14, 8, 3] {
        return Err("apple,firmware-compat is not <14 8 3>");
    }
    if schema != 1 {
        return Err("schema-version is not 1");
    }
    if result != 1 {
        return Err("probe-result is not 1 (the boot loader's read did not succeed)");
    }
    if id_version >> 24 != 7 || (id_version >> 16) & 0xff != 4 {
        return Err("id-version is not family 7, variant 4 (G15C)");
    }
    let revision = (id_version >> 8) & 0xff;
    if !REVISIONS.contains(&revision) {
        return Err("id-version has a revision the GPU revision list does not have");
    }
    let core_mask = u64::from(masks[0]) | (u64::from(masks[1]) << 32);
    if core_mask == 0 || core_mask >> CORE_SLOTS != 0 || masks[2] != 0 || masks[3] != 0 {
        return Err("the core masks are empty or reach beyond the 40 core slots");
    }
    Ok(Identity {
        id_version,
        revision,
        core_mask,
        active_cores: core_mask.count_ones(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn with(edit: impl Fn(&mut Raw)) -> Raw {
        let mut raw = Raw { start: 1, ..Raw::NONE };
        edit(&mut raw);
        raw
    }

    #[test]
    fn nothing_given_is_off() {
        assert_eq!(start(&Raw::NONE), Start::Off);
        assert!(!Raw::NONE.values_given());
        assert_eq!(start(&with(|r| r.start = 0)), Start::Off);
        assert_eq!(start(&with(|_| {})), Start::On);
        assert_eq!(start(&with(|r| r.start = 2)), Start::Invalid);
        assert!(!with(|_| {}).values_given());
        assert!(with(|r| r.pstate_cap = 2).values_given());
        assert!(with(|r| r.image_uuid = UuidParam::Invalid).values_given());
    }

    #[test]
    fn defaults_are_the_first_start() {
        let v = resolve(&with(|_| {})).unwrap();
        assert_eq!((v.image_uuid, v.image_hash, v.tag), (None, None, None));
        assert_eq!(v.initdata_version, 0x0c08_e21e_8380_0490);
        assert_eq!(v.pstate_cap, 1);
        assert_eq!(v.fender, 0x14_4000);
        assert_eq!(v.clock_gen, Some(0xe5_c000));
        assert_eq!(v.sgx_setup, Some((0xd1_4000, 0x7_0001)));
        assert_eq!((v.mcache, v.aic_swint, v.slot7, v.gifaf), (0, AicSwInt::Page, false, false));
        assert_eq!((v.slot21, v.slot24, v.slot28, v.ane, v.io_drop), (None, None, None, None, 0));
        assert_eq!(v.mtr, Mtr::Masks(0x402a_002b, 0));
        assert_eq!((v.unit_mask_a, v.unit_mask_b), (0x7_0000_000f, 7));
        assert_eq!((v.hwb_454, v.hwb_b20, v.hwb_17b8, v.hwb_1818), (1, 0x28, 5, 1));
        assert_eq!((v.fw_words, v.hwdata_aligned, v.gpu_core), (false, true, 24));
        assert_eq!((v.rev_id, v.csafr, v.power_cap_mw), (None, Tristate::Auto, 30_000));
    }

    #[test]
    fn every_alternative_resolves() {
        let v = resolve(&with(|r| {
            r.image_uuid = UuidParam::Set([7; 16]);
            r.image_hash = parse_number("0x11e49f750b671a2b");
            r.tag = parse_tag("0x5d54a");
            r.initdata_version = parse_number("0x123456789abcdef0");
            r.pstate_cap = parse_number("5");
            r.fender = parse_fender("adt");
            r.clkgen = parse_clkgen("e1c");
            r.sgx_setup = parse_sgx_setup("none");
            r.mcache = parse_mcache("x8");
            r.aic_swint = parse_aic_swint("reg");
            r.slot7 = parse_slot7("rule");
            r.gifaf = parse_gifaf("fender");
            r.slot21 = parse_slot("0x40b100000");
            r.slot24 = parse_slot("0x2a0000000");
            r.slot28 = parse_slot("0x2903c4000");
            r.ane = parse_ane("t8122");
            r.io_drop = parse_number("0x4000002");
            r.mtr = parse_mtr("t8122");
            r.mtr_alarm = parse_number("0xffff");
            r.unit_mask_a = parse_number("0x700000003");
            r.unit_mask_b = parse_number("0xf");
            r.hwb_454 = parse_number("2");
            r.hwb_b20 = parse_number("0x14");
            r.hwb_17b8 = parse_number("4");
            r.hwb_1818 = parse_number("0xffffffff");
            r.fw_words = parse_fw_words("t8122");
            r.hwdata_object = parse_hwdata_object("fixed");
            r.gpu_core = parse_number("23");
            r.rev_id = parse_rev_id("5");
            r.csafr = parse_tristate("off");
            r.power_cap_mw = parse_number("60000");
        }))
        .unwrap();
        assert_eq!((v.image_uuid, v.image_hash, v.tag), (Some([7; 16]), Some(0x11e4_9f75_0b67_1a2b), Some(0x5d54a)));
        assert_eq!((v.initdata_version, v.pstate_cap, v.fender), (0x1234_5678_9abc_def0, 5, 0x16_c000));
        assert_eq!((v.clock_gen, v.sgx_setup, v.mcache), (Some(0xe1_c000), None, 8));
        assert_eq!((v.aic_swint, v.slot7, v.gifaf), (AicSwInt::Register, true, true));
        assert_eq!((v.slot21, v.slot24, v.slot28), (Some(0x4_0b10_0000), Some(0x2_a000_0000), Some(0x2_903c_4000)));
        assert_eq!((v.ane, v.io_drop), (Some(ANE_T8122), (1 << 26) | (1 << 1)));
        assert_eq!(v.mtr, Mtr::Masks(0x4248, 0xffff));
        assert_eq!((v.unit_mask_a, v.unit_mask_b), (0x7_0000_0003, 0xf));
        assert_eq!((v.hwb_454, v.hwb_b20, v.hwb_17b8, v.hwb_1818), (2, 0x14, 4, 0xffff_ffff));
        assert_eq!((v.fw_words, v.hwdata_aligned, v.gpu_core, v.rev_id), (true, false, 23, Some(5)));
        assert_eq!((v.csafr, v.power_cap_mw), (Tristate::Off, 60_000));
        // Names and numbers agree.
        assert_eq!(parse_fender("0x144000"), parse_fender("rule"));
        assert_eq!(parse_clkgen("0xe5c000"), parse_clkgen("e5c"));
        assert_eq!(parse_ane("0x30945c000"), parse_ane("t6030"));
        assert_eq!(parse_mcache("2"), parse_mcache("x2"));
        assert_eq!(resolve(&with(|r| r.clkgen = parse_clkgen("none"))).unwrap().clock_gen, None);
        assert_eq!(resolve(&with(|r| r.mtr = parse_mtr("adt"))).unwrap().mtr, Mtr::Adt);
        assert_eq!(resolve(&with(|r| r.mtr = parse_mtr("none"))).unwrap().mtr, Mtr::Masks(0, 0));
        assert_eq!(resolve(&with(|r| r.rev_id = parse_rev_id("auto"))).unwrap().rev_id, None);
        assert_eq!(resolve(&with(|r| r.tag = parse_tag("search"))).unwrap().tag, None);
    }

    #[test]
    fn unaccepted_values_refuse_and_name_the_parameter() {
        let cases: [(fn(&mut Raw), &str); 30] = [
            (|r| r.image_uuid = UuidParam::Invalid, "t6031_image_uuid"),
            (|r| r.image_hash = INVALID, "t6031_image_hash"),
            (|r| r.tag = parse_tag("0x64000"), "t6031_tag"),
            (|r| r.initdata_version = 0, "t6031_initdata_version"),
            (|r| r.pstate_cap = 0, "t6031_pstate_cap"),
            (|r| r.pstate_cap = 6, "t6031_pstate_cap"),
            (|r| r.fender = parse_fender("0x104000"), "t6031_fender"),
            (|r| r.clkgen = parse_clkgen("0"), "t6031_clkgen"),
            (|r| r.clkgen = parse_clkgen("e00"), "t6031_clkgen"),
            (|r| r.sgx_setup = 2, "t6031_sgx_setup"),
            (|r| r.mcache = parse_mcache("x3"), "t6031_mcache"),
            (|r| r.aic_swint = 2, "t6031_aic_swint"),
            (|r| r.slot7 = 2, "t6031_slot7"),
            (|r| r.gifaf = 2, "t6031_gifaf"),
            (|r| r.slot21 = parse_slot("0x40b100004"), "t6031_slot21"),
            (|r| r.slot24 = parse_slot("0x100000000"), "t6031_slot24"),
            (|r| r.slot28 = parse_slot("0x10000000000"), "t6031_slot28"),
            (|r| r.ane = parse_ane("0x30945c004"), "t6031_ane"),
            (|r| r.io_drop = 1, "t6031_io_drop"),
            (|r| r.io_drop = 1 << 29, "t6031_io_drop"),
            (|r| r.mtr = 4, "t6031_mtr"),
            (|r| { r.mtr = parse_mtr("adt"); r.mtr_alarm = 1; }, "t6031_mtr"),
            (|r| r.unit_mask_a = 0x7_0000_001f, "t6031_unit_mask_a"),
            (|r| r.unit_mask_b = 0x10, "t6031_unit_mask_b"),
            (|r| r.hwb_b20 = 1 << 32, "t6031_hwb_b20"),
            (|r| r.fw_words = 2, "t6031_fw_words"),
            (|r| r.gpu_core = 26, "t6031_gpu_core"),
            (|r| r.rev_id = 9, "t6031_rev_id"),
            (|r| r.csafr = 3, "t6031_csafr"),
            (|r| r.power_cap_mw = 100, "t6031_power_cap_mw"),
        ];
        for (edit, name) in cases {
            assert_eq!(resolve(&with(edit)).unwrap_err().name, name);
        }
    }

    #[test]
    fn uuids_parse_with_or_without_dashes_only() {
        let plain = parse_uuid("df697f05f6b533efa13761c4a73d666a").unwrap();
        assert_eq!(plain[..4], [0xdf, 0x69, 0x7f, 0x05]);
        assert_eq!(plain[15], 0x6a);
        assert_eq!(parse_uuid(" DF697F05-F6B5-33EF-A137-61C4A73D666A "), Some(plain));
        for bad in [
            "",
            "df697f05f6b533efa13761c4a73d666",
            "df697f05f6b533efa13761c4a73d666aa",
            "df697f05-f6b533ef-a137-61c4a73d666a",
            "df697f05f6b5-33ef-a137-61c4a73d666a",
            "dg697f05f6b533efa13761c4a73d666a",
            "df697f0-5f6b5-33ef-a137-61c4a73d666a",
        ] {
            assert_eq!(parse_uuid(bad), None, "{bad:?}");
        }
    }

    #[test]
    fn revision_ids_follow_the_read_unless_given() {
        let v = resolve(&with(|_| {})).unwrap();
        assert_eq!(v.rev_id(0x11), Some(4));
        assert_eq!(v.rev_id(0x12), Some(4));
        assert_eq!(v.rev_id(0x20), Some(5));
        assert_eq!(v.rev_id(0x13), None);
        let v = resolve(&with(|r| r.rev_id = 7)).unwrap();
        assert_eq!(v.rev_id(0x12), Some(7));
        assert_eq!(v.rev_id(0x13), Some(7));
    }

    #[test]
    fn mtr_and_csafr_choices() {
        let v = resolve(&with(|_| {})).unwrap();
        assert_eq!(v.mtr_masks(0x8080), (0x402a_002b, 0));
        assert!(v.csafr(true) && !v.csafr(false));
        let v = resolve(&with(|r| r.mtr = parse_mtr("adt"))).unwrap();
        assert_eq!(v.mtr_masks(0x8080), (0x8080, 0));
        let v = resolve(&with(|r| r.csafr = 1)).unwrap();
        assert!(v.csafr(false));
        let v = resolve(&with(|r| r.csafr = 2)).unwrap();
        assert!(!v.csafr(true));
    }

    #[test]
    fn default_mappings_are_the_derivable_slots() {
        let (m, n) = mappings(&resolve(&with(|_| {})).unwrap());
        let slots: Vec<usize> = m[..n].iter().map(|e| e.0).collect();
        assert_eq!(slots, [0, 1, 2, 3, 9, 12, 18, 19, 20, 23, 26, 29]);
        assert_eq!(m[0], (0, 0x4_08d0_0000, 0x14_4000, 0x14_4000, true));
        assert_eq!(m[2], (2, 0x2_9241_4000, 0x4000, 0x4000, true));
        assert_eq!(m[3], (3, 0x4_0800_0000, 0x2_0000, 0x2_0000, true));
        assert_eq!(m[4], (9, 0x4_08e0_8000, 0x8000, 0x8000, true));
        assert_eq!(m[9], (23, 0x4_0b00_0000, 0x40_0000, 0x40_0000, true));
        assert_eq!(m[11], (29, 0x4_08e5_c000, 0x4000, 0x4000, false));
    }

    #[test]
    fn every_mapping_is_its_superset_slots_and_fits_it() {
        let all = resolve(&with(|r| {
            r.fender = parse_fender("adt");
            r.mcache = 8;
            r.aic_swint = 1;
            r.slot7 = 1;
            r.gifaf = 1;
            r.slot21 = 0x4_0b10_0000;
            r.slot24 = 0x2_a000_0000;
            r.slot28 = 0x2_903c_4000;
            r.ane = ANE_T8122;
            r.clkgen = parse_clkgen("e1c");
        }))
        .unwrap();
        let (m, n) = mappings(&all);
        assert_eq!(n, SLOTS);
        for (i, e) in m[..n].iter().enumerate() {
            let s = SUPERSET[i];
            assert_eq!(e.0, s.0);
            assert_eq!(e.4, s.4, "slot {}", e.0);
            // Each fits in the superset entry's 16 KiB pages at its own subpage offset.
            let offset = (e.1 & 0x3fff) as u32;
            assert!(offset + e.2 <= ((s.1 & 0x3fff) as u32 + s.2 + 0x3fff) & !0x3fff, "slot {}", e.0);
            assert!(e.3 != 0 && e.2 % e.3 == 0, "slot {}", e.0);
            assert_eq!(READ_ONLY_SLOTS & (1 << e.0) != 0 && e.4, false, "slot {}", e.0);
        }
        // Slots strictly increase, so no slot appears twice.
        assert!(SUPERSET.windows(2).all(|w| w[0].0 < w[1].0));
        // The dropped slots leave.
        let dropped = resolve(&with(|r| r.io_drop = u64::from(IO_DROP_ALLOWED))).unwrap();
        let (m, n) = mappings(&dropped);
        let slots: Vec<usize> = m[..n].iter().map(|e| e.0).collect();
        assert_eq!(slots, [0, 3, 29]);
        let (m, n) = mappings(&resolve(&with(|r| r.clkgen = parse_clkgen("none"))).unwrap());
        assert!(m[..n].iter().all(|e| e.0 != 29));
    }

    #[test]
    fn grounded_addresses_are_inside_their_blocks() {
        // Fender, RGX, metrology, AFR and the clock generators lie in the ADT's SGX window.
        for (offset, size) in [
            (0xd0_0000, u64::from(FENDER_ADT)),
            (0, 0x2_0000),
            (0xe0_8000, 0x8000),
            (0x300_0000, 0x40_0000),
            (CLOCK_GEN_E5C, 0x4000),
            (CLOCK_GEN_E1C, 0x4000),
        ] {
            assert!(offset + size <= SGX_SIZE);
        }
        // The Fender rule is the ADT size less 0x28000, and both hold the scratch area.
        assert_eq!(FENDER_ADT - FENDER_RULE, 0x2_8000);
        assert!(FENDER_RULE >= 0x8_0000 && FENDER_RULE % 0x4000 == 0 && FENDER_ADT % 0x4000 == 0);
        // The ADT's software-interrupt registers are in the slot-2 page.
        for reg in [0x2_9241_4084u64, 0x2_9241_4284] {
            assert_eq!(reg & !0x3fff, AIC + 0x1_4000);
        }
        assert_eq!(UNIT_MASK_A & !UNIT_MASK_A_LIMIT, 0);
        assert_eq!(u64::from(UNIT_MASK_B) & !UNIT_MASK_B_LIMIT, 0);
    }

    #[test]
    fn identity_admits_g15c_with_up_to_forty_cores_only() {
        let full = [0xffff_ffff, 0xff, 0, 0];
        let id = validate_identity(&[14, 8, 3], 1, 1, 0x0704_1200, full).unwrap();
        assert_eq!((id.revision, id.core_mask, id.active_cores), (0x12, 0xff_ffff_ffff, 40));
        let id = validate_identity(&[14, 8, 3], 1, 1, 0x0704_1100, [0x3ff, 0, 0, 0]).unwrap();
        assert_eq!((id.revision, id.active_cores), (0x11, 10));
        for (compat, schema, result, version, masks) in [
            ([14, 7, 0], 1, 1, 0x0704_1200, full),
            ([14, 8, 3], 2, 1, 0x0704_1200, full),
            ([14, 8, 3], 1, 0, 0x0704_1200, full),
            ([14, 8, 3], 1, 1, 0x0703_1100, full),
            ([14, 8, 3], 1, 1, 0x0604_1200, full),
            ([14, 8, 3], 1, 1, 0x0704_1300, full),
            ([14, 8, 3], 1, 1, 0x0704_1200, [0, 0, 0, 0]),
            ([14, 8, 3], 1, 1, 0x0704_1200, [0xffff_ffff, 0x1ff, 0, 0]),
            ([14, 8, 3], 1, 1, 0x0704_1200, [1, 0, 1, 0]),
            ([14, 8, 3], 1, 1, 0x0704_1200, [1, 0, 0, 1]),
        ] {
            assert!(validate_identity(&compat, schema, result, version, masks).is_err(), "{version:#x} {masks:x?}");
        }
    }
}
