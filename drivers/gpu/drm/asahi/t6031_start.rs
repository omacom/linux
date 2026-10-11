// SPDX-License-Identifier: GPL-2.0-only OR MIT

//! The T6031 (M3 Max, G15C) start, `asahi.t6031_start=1`.
//!
//! T6031 stays out of the runtime's SoC list. Without `asahi.t6031_start=1` the probe is the
//! same refusal as before: it does not build InitData and it does not start the GPU coprocessor.
//! With `asahi.t6031_start=1` this is one attempt per boot. A second probe in the same boot is
//! refused before any register write. The values are `t6031_knobs`: each parameter's default, or
//! the value it was given. A value a parameter does not accept refuses the attempt. Slots the
//! device tree does not name stay unmapped unless a parameter gives an address. The InitData
//! version defaults to the G15 14.8.3 version and can be replaced with
//! `asahi.t6031_initdata_version`.
//!
//! Read-only status is `/sys/kernel/debug/asahi-t6031/status`. It does not touch a register. If
//! the firmware crashes, its crash log is offered to devcoredump and the status file records how
//! many bytes that was.

use core::sync::atomic::{AtomicBool, AtomicU32, AtomicU64, Ordering};

use kernel::{c_str, device, prelude::*};

use crate::{
    hw,
    initdata::G15RuntimeHwDataB,
    m3_firmware::{self, image_info},
    m3_init_storage as storage,
    m3_soc::{HwDataObject, IoMapping, Soc, T6030_HWDATA_B, T8122_HWDATA_ADDRESS},
    t6031_knobs::{self as knobs, Mapping, Start, Values, GPU_CORE, READ_ONLY_SLOTS, SLOTS},
};

/// `asahi-t6031/status` phase.
const PHASE_IDLE: u32 = 0;
const PHASE_ARMED: u32 = 1;
const PHASE_REFUSED: u32 = 2;
const PHASE_RUNNING: u32 = 3;
const PHASE_CRASHED: u32 = 4;

struct BootStatus {
    phase: AtomicU32,
    initdata: AtomicU64,
    mappings: AtomicU32,
    crash_bytes: AtomicU32,
    outcome: AtomicU32,
}

static STATUS: BootStatus = BootStatus {
    phase: AtomicU32::new(PHASE_IDLE),
    initdata: AtomicU64::new(0),
    mappings: AtomicU32::new(0),
    crash_bytes: AtomicU32::new(0),
    outcome: AtomicU32::new(0),
};

/// One attempt per boot. The first `asahi.t6031_start=1` probe takes it.
static ATTEMPTED: AtomicBool = AtomicBool::new(false);

struct StatusFile;

impl kernel::debugfs::Writer for StatusFile {
    fn write(&self, f: &mut kernel::fmt::Formatter<'_>) -> kernel::fmt::Result {
        let phase = STATUS.phase.load(Ordering::Relaxed);
        let name = match phase {
            PHASE_ARMED => "armed",
            PHASE_REFUSED => "refused",
            PHASE_RUNNING => "firmware-running",
            PHASE_CRASHED => "crashed",
            _ => "idle",
        };
        writeln!(
            f,
            "version=1 phase={} initdata_version={:#x} io_mappings={} crashlog_bytes={} outcome={}",
            name,
            STATUS.initdata.load(Ordering::Relaxed),
            STATUS.mappings.load(Ordering::Relaxed),
            STATUS.crash_bytes.load(Ordering::Relaxed),
            STATUS.outcome.load(Ordering::Relaxed)
        )
    }
}

fn publish_status() {
    static PUBLISHED: AtomicBool = AtomicBool::new(false);
    if PUBLISHED.swap(true, Ordering::AcqRel) {
        return;
    }
    let dir = kernel::debugfs::Dir::new(c"asahi-t6031");
    match KBox::pin_init(dir.read_only_file(c"status", StatusFile), GFP_KERNEL) {
        Ok(file) => {
            core::mem::forget(file);
            core::mem::forget(dir);
        }
        Err(error) => {
            pr_err!("M3 G15C start: status file was not created ({:?})\n", error);
        }
    }
}

fn mark(phase: u32, outcome: u32) {
    STATUS.phase.store(phase, Ordering::Relaxed);
    STATUS.outcome.store(outcome, Ordering::Relaxed);
}

/// The IO maps and HwDataB words of the one armed attempt.
struct Built {
    values: Values,
    count: usize,
    mappings: [Mapping; SLOTS],
    iomaps: [storage::IoMap; SLOTS],
    hwdata_b: G15RuntimeHwDataB,
}

/// The values of one armed boot.
pub(crate) struct Experiment(&'static Built);

/// Whether `soc` is the T6031 table.
pub(crate) fn is_t6031(soc: &Soc) -> bool {
    core::ptr::eq(soc, &crate::m3_soc::T6031)
}

fn pack(src: &[Mapping], dst: &mut [storage::IoMap]) {
    let mut address = storage::IOMAP_BASE;
    for (i, &(slot, physical, total, _, _)) in src.iter().enumerate() {
        let offset = (physical & 0x3fff) as usize;
        let size = (offset + total as usize + 0x3fff) & !0x3fff;
        dst[i] = storage::IoMap {
            slot,
            physical: physical & !0x3fff,
            size,
            address,
            offset,
        };
        address += size as u64 + 0x4000;
    }
}

fn hwdata_b(v: &Values) -> G15RuntimeHwDataB {
    let base = &T6030_HWDATA_B;
    G15RuntimeHwDataB {
        unk_454: v.hwb_454,
        unk_464: base.unk_464,
        unk_a7c: base.unk_a7c,
        unk_a98: base.unk_a98,
        unk_abc: base.unk_abc,
        unk_ae4: base.unk_ae4,
        unk_b20: v.hwb_b20,
        unk_b24: base.unk_b24,
        unk_554: base.unk_554,
        unk_17b8: v.hwb_17b8,
        unit_mask_a: v.unit_mask_a,
        unit_mask_b: v.unit_mask_b,
        unk_1808: base.unk_1808,
        unk_1818: v.hwb_1818,
    }
}

impl Experiment {
    /// The InitData version given to the firmware.
    pub(crate) fn initdata_version(&self) -> u64 {
        self.0.values.initdata_version
    }

    /// The firmware IO mappings of the InitData.
    pub(crate) fn io_mappings(&self) -> &'static [IoMapping] {
        let built: &'static Built = self.0;
        &built.mappings[..built.count]
    }

    /// The runtime's mapping of each of them.
    pub(crate) fn iomaps(&self) -> &'static [storage::IoMap] {
        let built: &'static Built = self.0;
        &built.iomaps[..built.count]
    }

    /// The register block the IO mapping of `slot` must lie in.
    pub(crate) fn io_block(&self, slot: usize, base: u64) -> u64 {
        self.io_mappings()
            .iter()
            .find(|mapping| mapping.0 == slot)
            .map(|mapping| mapping.1)
            .unwrap_or(base)
    }

    /// The HwDataB slots the firmware maps read-only, as a bit mask.
    pub(crate) fn read_only_slots(&self) -> u32 {
        self.io_mappings().iter().fold(0u32, |mask, mapping| {
            if mapping.0 < 32 && READ_ONLY_SLOTS & (1u32 << mapping.0) != 0 {
                mask | (1u32 << mapping.0)
            } else {
                mask
            }
        })
    }

    /// The runtime HwDataB words, including the unit masks.
    pub(crate) fn hwdata_b(&self) -> &'static G15RuntimeHwDataB {
        &self.0.hwdata_b
    }

    /// The HwDataB unit masks A (+0x17c0) and B (+0x17c8).
    pub(crate) fn unit_masks(&self) -> (u64, u32) {
        (self.0.values.unit_mask_a, self.0.values.unit_mask_b)
    }

    /// The SGX write (offset, value) made before the firmware starts, if any.
    pub(crate) fn sgx_setup(&self) -> Option<(usize, u32)> {
        self.0.values.sgx_setup
    }

    /// The highest performance state the firmware may use.
    pub(crate) fn pstate_cap(&self) -> u32 {
        self.0.values.pstate_cap
    }

    /// The power target, in mW, while the boot loader's power model is a stand-in.
    pub(crate) fn power_cap_mw(&self) -> u32 {
        self.0.values.power_cap_mw
    }

    /// Whether this attempt copies the T8122 HwData and Globals words.
    pub(crate) fn fw_words(&self) -> bool {
        self.0.values.fw_words
    }

    /// The hardware configuration: without the CS and AFR states when this attempt turns them off.
    pub(crate) fn hwcfg(&self) -> &'static hw::HwConfig {
        if self.0.values.csafr(true) {
            &hw::t6031::CONFIG
        } else {
            &hw::t6031::CONFIG_NO_CSAFR
        }
    }

    /// The HwData object placement. Aligned and cacheable, unless `t6031_hwdata_object=fixed`.
    pub(crate) fn hwdata_object(&self) -> Option<HwDataObject> {
        if self.0.values.hwdata_aligned {
            Some(HwDataObject {
                address: T8122_HWDATA_ADDRESS,
                cached: true,
            })
        } else {
            None
        }
    }

    /// A firmware revision id given with `asahi.t6031_rev_id`, if this attempt has one.
    pub(crate) fn revision_id(&self) -> Option<hw::GpuRevisionID> {
        Some(match self.0.values.rev_id? {
            1 => hw::GpuRevisionID::A0,
            2 => hw::GpuRevisionID::A1,
            3 => hw::GpuRevisionID::B0,
            4 => hw::GpuRevisionID::B1,
            5 => hw::GpuRevisionID::C0,
            6 => hw::GpuRevisionID::C1,
            _ => return None,
        })
    }

    /// The MTR masks (fast die, alarm). `adt` reads `apple,fast-die0-sensor-mask`.
    pub(crate) fn mtr_masks(&self, dev: &device::Device) -> Result<(u64, u64)> {
        match self.0.values.mtr {
            knobs::Mtr::Masks(fast, alarm) => Ok((fast, alarm)),
            knobs::Mtr::Adt => {
                let node = dev.of_node().ok_or(ENODEV)?;
                let fast = node
                    .get_property::<u64>(c_str!("apple,fast-die0-sensor-mask"))
                    .map_err(|_| ENODEV)?;
                Ok((fast, 0))
            }
        }
    }

    /// Zero the one boot-entropy record in `text`. `t6031_tag=search` requires exactly one tag.
    pub(crate) fn normalize_text(&self, text: &mut [u8]) -> Result {
        let layout = &m3_firmware::T6031_LAYOUT;
        if text.len() != layout.text_size as usize {
            return Err(ENODEV);
        }
        let tag = &layout.entropy_tag;
        let at = if let Some(offset) = self.0.values.tag {
            if text.get(offset..offset + tag.len()) != Some(tag.as_slice()) {
                return Err(ENODEV);
            }
            offset
        } else {
            let mut found = None;
            let last = text.len().saturating_sub(tag.len() + 8);
            for offset in 0..=last {
                if &text[offset..offset + tag.len()] == tag.as_slice() {
                    if found.is_some() {
                        return Err(ENODEV);
                    }
                    found = Some(offset);
                }
            }
            found.ok_or(ENODEV)?
        };
        text[at + tag.len()..at + tag.len() + 8].fill(0);
        Ok(())
    }

    /// Accept the loaded image, or refuse it before the coprocessor starts.
    ///
    /// A given `t6031_image_uuid` or `t6031_image_hash` must match. With neither, a well-formed
    /// identity header is enough; the log prints the UUID and the text hash so a later boot can
    /// pin them.
    pub(crate) fn admit_image(&self, dev: &device::Device, text: &[u8], digest: &[u8; 32]) -> Result {
        let info = image_info(text);
        let prefix = u64::from_be_bytes(digest[..8].try_into().map_err(|_| EINVAL)?);
        dev_info!(
            dev,
            "M3 G15C start: image identity header {} text-sha256 prefix {:#018x}\n",
            if info.is_some() { "present" } else { "absent" },
            prefix
        );
        if let Some(info) = info.as_ref() {
            let hex = uuid_text(&info.uuid);
            if let Ok(text) = core::str::from_utf8(&hex) {
                dev_info!(dev, "M3 G15C start: image UUID {}\n", text);
            }
        }
        if let Some(want) = self.0.values.image_uuid {
            let uuid = info.as_ref().ok_or(ENODEV)?.uuid;
            if uuid != want {
                dev_err!(dev, "M3 G15C start: refused: image UUID does not match asahi.t6031_image_uuid\n");
                return Err(ENODEV);
            }
        }
        if let Some(want) = self.0.values.image_hash {
            if prefix != want {
                dev_err!(
                    dev,
                    "M3 G15C start: refused: text SHA-256 prefix {:#018x} is not asahi.t6031_image_hash {:#018x}\n",
                    prefix,
                    want
                );
                return Err(ENODEV);
            }
        }
        if self.0.values.image_uuid.is_none() && self.0.values.image_hash.is_none() && info.is_none() {
            dev_err!(
                dev,
                "M3 G15C start: refused: the image has no identity header and neither asahi.t6031_image_uuid nor asahi.t6031_image_hash was given\n"
            );
            return Err(ENODEV);
        }
        Ok(())
    }
}

/// Decide whether `soc` starts.
///
/// Any SoC but T6031: Ok(None). T6031 without `asahi.t6031_start=1`: Ok(None). T6031 with it:
/// the one attempt, or a refusal.
pub(crate) fn arm(dev: &device::Device, soc: &Soc) -> Result<Option<Experiment>> {
    if !is_t6031(soc) {
        return Ok(None);
    }
    let raw = crate::m3_params::t6031_params();
    match knobs::start(&raw) {
        Start::On => {}
        Start::Off => {
            if raw.values_given() {
                dev_info!(
                    dev,
                    "M3 G15C start: asahi.t6031_* values given without asahi.t6031_start=1; ignored\n"
                );
            }
            return Ok(None);
        }
        Start::Invalid => {
            dev_err!(
                dev,
                "M3 G15C start: refused: asahi.t6031_start has a value it does not accept (0 or 1); GPU startup disabled\n"
            );
            mark(PHASE_REFUSED, ENODEV.to_errno() as u32);
            return Err(ENODEV);
        }
    }
    publish_status();
    if ATTEMPTED.swap(true, Ordering::AcqRel) {
        dev_err!(
            dev,
            "M3 G15C start: refused: this boot already attempted the one start; GPU startup disabled\n"
        );
        mark(PHASE_REFUSED, ENODEV.to_errno() as u32);
        return Err(ENODEV);
    }
    let values = match knobs::resolve(&raw) {
        Ok(values) => values,
        Err(refusal) => {
            dev_err!(
                dev,
                "M3 G15C start: refused: asahi.{} has a value it does not accept ({}); GPU startup disabled\n",
                refusal.name,
                refusal.accepts
            );
            mark(PHASE_REFUSED, ENODEV.to_errno() as u32);
            return Err(ENODEV);
        }
    };
    if values.gpu_core != GPU_CORE {
        dev_err!(
            dev,
            "M3 G15C start: refused: asahi.t6031_gpu_core {} is not the table's core type {}; GPU startup disabled\n",
            values.gpu_core,
            GPU_CORE
        );
        mark(PHASE_REFUSED, ENODEV.to_errno() as u32);
        return Err(ENODEV);
    }
    if values.rev_id.is_some_and(|id| id > 6) {
        dev_err!(
            dev,
            "M3 G15C start: refused: asahi.t6031_rev_id {} has no identity entry in this start (1 to 6); GPU startup disabled\n",
            values.rev_id.unwrap_or(0)
        );
        mark(PHASE_REFUSED, ENODEV.to_errno() as u32);
        return Err(ENODEV);
    }
    let (mappings, count) = knobs::mappings(&values);
    let mut iomaps = [storage::IoMap {
        slot: 0,
        physical: 0,
        size: 0,
        address: 0,
        offset: 0,
    }; SLOTS];
    pack(&mappings[..count], &mut iomaps[..count]);
    if storage::validate_iomaps(&iomaps[..count]).is_err() {
        dev_err!(
            dev,
            "M3 G15C start: refused: the IO maps do not fit the runtime window; GPU startup disabled\n"
        );
        mark(PHASE_REFUSED, EINVAL.to_errno() as u32);
        return Err(EINVAL);
    }
    let built = KBox::new(
        Built {
            hwdata_b: hwdata_b(&values),
            values,
            count,
            mappings,
            iomaps,
        },
        GFP_KERNEL,
    )?;
    let built: &'static Built = KBox::leak(built);
    STATUS.initdata.store(values.initdata_version, Ordering::Relaxed);
    STATUS.mappings.store(count as u32, Ordering::Relaxed);
    mark(PHASE_ARMED, 0);
    dev_warn!(
        dev,
        "M3 G15C start: armed (asahi.t6031_start=1, one attempt this boot): initdata_version={:#018x} io_mappings={} fender={:#x} pstate_cap={} power_cap_mw={}\n",
        values.initdata_version,
        count,
        values.fender,
        values.pstate_cap,
        values.power_cap_mw
    );
    Ok(Some(Experiment(built)))
}

/// Log, on a T6031 with `asahi.t6031_start=1`, that resource admission refused it.
pub(crate) fn not_admitted(dev: &device::Device, soc: &Soc) {
    if is_t6031(soc) && knobs::start(&crate::m3_params::t6031_params()) == Start::On {
        publish_status();
        dev_err!(
            dev,
            "M3 G15C start: not armed: resource admission refused the GPU (see the lines above); the boot loader did not hand it over completely\n"
        );
        mark(PHASE_REFUSED, ENODEV.to_errno() as u32);
    }
}

/// Log that an armed start stopped at `stage` before the firmware was running.
pub(crate) fn refused(dev: &device::Device, experiment: Option<&Experiment>, stage: &str, error: Error) {
    if experiment.is_some() {
        dev_err!(
            dev,
            "M3 G15C start: refused at {} ({:?}); the firmware was not started, see the lines above\n",
            stage,
            error
        );
        mark(PHASE_REFUSED, error.to_errno() as u32);
    }
}

/// A GPU coprocessor setup step failed before the firmware could be started.
pub(crate) fn coproc_setup_refused(dev: &device::Device, error: Error) {
    dev_err!(
        dev,
        "M3 G15C start: refused at the GPU coprocessor setup (RTKit/mailbox) ({:?}); the firmware was not started\n",
        error
    );
    mark(PHASE_REFUSED, error.to_errno() as u32);
}

/// The coprocessor start or the InitData upload failed. `started`: endpoints were offered.
pub(crate) fn prepare_verdict(dev: &device::Device, started: bool, error: Error) {
    if started {
        dev_err!(
            dev,
            "M3 G15C verdict: driver-refused ({:?}): the GPU firmware is up, but the driver did not publish the InitData\n",
            error
        );
    } else {
        dev_err!(
            dev,
            "M3 G15C verdict: firmware-boot-failed ({:?}): the GPU coprocessor did not start, or its RTKit did not offer endpoints 0x20/0x21; no InitData was published\n",
            error
        );
    }
    mark(PHASE_REFUSED, error.to_errno() as u32);
}

/// The firmware's answer to the published InitData.
pub(crate) fn boot_verdict(
    dev: &device::Device,
    version: u64,
    step: crate::t8122_start::BootStep,
    accepted: bool,
    crashed: bool,
    result: Result,
) {
    use crate::t8122_start::BootStep;
    let Err(error) = result else {
        dev_info!(
            dev,
            "M3 G15C verdict: firmware-running: the firmware accepted the InitData (version {:#x}) and the device controls; no job has run yet\n",
            version
        );
        mark(PHASE_RUNNING, 0);
        return;
    };
    if accepted || step == BootStep::PostReady {
        dev_err!(
            dev,
            "M3 G15C verdict: firmware-running-check-failed ({:?}): the firmware accepted the InitData (version {:#x}) then a post-boot check failed; crashed={}\n",
            error,
            version,
            u8::from(crashed)
        );
        mark(if crashed { PHASE_CRASHED } else { PHASE_REFUSED }, error.to_errno() as u32);
        return;
    }
    let phase = if crashed { PHASE_CRASHED } else { PHASE_REFUSED };
    match step {
        BootStep::Publish => dev_err!(
            dev,
            "M3 G15C verdict: publish-failed ({:?}): the InitData publish (endpoint 0x20, version {:#x}) was not sent\n",
            error,
            version
        ),
        BootStep::DeviceControl => dev_err!(
            dev,
            "M3 G15C verdict: device-control-failed ({:?}): a device-control message failed after the InitData (version {:#x}) was published\n",
            error,
            version
        ),
        _ if crashed => dev_err!(
            dev,
            "M3 G15C verdict: initdata-rejected ({:?}): the firmware crashed after the InitData (version {:#x}) was published; see the crash log\n",
            error,
            version
        ),
        _ => dev_err!(
            dev,
            "M3 G15C verdict: initdata-rejected ({:?}): the firmware did not acknowledge the InitData (version {:#x}) within 2 s\n",
            error,
            version
        ),
    }
    mark(phase, error.to_errno() as u32);
}

/// A job-path step failed outside the completion wait.
pub(crate) fn job_setup_failed_verdict(dev: &device::Device, error: Error) {
    dev_err!(
        dev,
        "M3 G15C verdict: job-failed-before-wait ({:?}): a submit, doorbell or diagnostic step failed\n",
        error
    );
    mark(PHASE_REFUSED, error.to_errno() as u32);
}

/// The firmware ran a job above the performance-state cap.
pub(crate) fn cap_violated_verdict(dev: &device::Device, error: Error) {
    dev_err!(
        dev,
        "M3 G15C verdict: cap-violated ({:?}): after a job the firmware reported a performance state above the cap\n",
        error
    );
    mark(PHASE_REFUSED, error.to_errno() as u32);
}

/// A job failed.
pub(crate) fn job_failed_verdict(dev: &device::Device, primary: Error, crashed: bool) {
    dev_err!(
        dev,
        "M3 G15C verdict: job-faulted ({:?}): crashed={}; see the lines around this one\n",
        primary,
        u8::from(crashed)
    );
    mark(if crashed { PHASE_CRASHED } else { PHASE_REFUSED }, primary.to_errno() as u32);
}

/// The first job of a kind retired.
pub(crate) fn job_completed_verdict(dev: &device::Device, kind: usize, gpu_ns: u64) {
    let what = if kind == 0 { "render" } else { "compute" };
    dev_info!(
        dev,
        "M3 G15C verdict: job-completed: the first {} job finished, {} ns of GPU time\n",
        what,
        gpu_ns
    );
    mark(PHASE_RUNNING, 0);
}

struct CrashLog {
    bytes: KVec<u8>,
}

impl kernel::devcoredump::DevCoreDump for CrashLog {
    fn read(&self, output: &mut [u8], offset: usize) -> Result<usize> {
        if offset >= self.bytes.len() {
            return Ok(0);
        }
        let length = output.len().min(self.bytes.len() - offset);
        output[..length].copy_from_slice(&self.bytes[offset..offset + length]);
        Ok(length)
    }
}

/// Offer the firmware crash log to devcoredump. No-op unless this boot armed a T6031 start.
/// The bytes are the log the firmware already wrote; this does not read a GPU register.
pub(crate) fn capture_crashlog(dev: &device::Device, crashlog: &[u8]) {
    if !is_status_armed() {
        return;
    }
    const CAP: usize = 256 * 1024;
    let kept = crashlog.len().min(CAP);
    STATUS.crash_bytes.store(crashlog.len() as u32, Ordering::Relaxed);
    mark(PHASE_CRASHED, 0);
    dev_err!(
        dev,
        "M3 G15C start: firmware crash log {} bytes (offering {})\n",
        crashlog.len(),
        kept
    );
    #[cfg(CONFIG_DEV_COREDUMP)]
    {
        let mut bytes = KVec::new();
        if bytes.extend_from_slice(&crashlog[..kept], GFP_NOWAIT).is_err() {
            dev_err!(dev, "M3 G15C start: crash log was not copied; it is not in devcoredump\n");
            return;
        }
        let owned = match KBox::new(CrashLog { bytes }, GFP_NOWAIT) {
            Ok(owned) => owned,
            Err(_) => {
                dev_err!(dev, "M3 G15C start: crash log was not offered to devcoredump\n");
                return;
            }
        };
        kernel::devcoredump::dev_coredump(
            dev,
            &crate::THIS_MODULE,
            owned,
            GFP_NOWAIT,
            kernel::devcoredump::DEFAULT_TIMEOUT,
        );
        dev_info!(
            dev,
            "M3 G15C start: {}-byte firmware crash log offered to devcoredump\n",
            kept
        );
    }
}

fn is_status_armed() -> bool {
    ATTEMPTED.load(Ordering::Acquire)
}

/// 32 hex digits of `uuid`, for the identity log. There is no UUID module parameter; a later
/// boot pins the image with `asahi.t6031_image_hash`.
fn uuid_text(uuid: &[u8; 16]) -> [u8; 32] {
    let mut out = [0u8; 32];
    for (i, byte) in uuid.iter().enumerate() {
        const HEX: &[u8; 16] = b"0123456789abcdef";
        out[i * 2] = HEX[usize::from(byte >> 4)];
        out[i * 2 + 1] = HEX[usize::from(byte & 0xf)];
    }
    out
}
