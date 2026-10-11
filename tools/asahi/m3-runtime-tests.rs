// SPDX-License-Identifier: GPL-2.0-only OR MIT

//! Host tests for the production M3 admission, IO ownership, thermal policy, the T8122 and T6031
//! start experiments' parameters and the multi-cluster pass layout.
#![allow(dead_code)]

#[path = "../../drivers/gpu/drm/asahi/t8122_admission.rs"]
mod t8122_admission;
#[path = "../../drivers/gpu/drm/asahi/agx_resources.rs"]
mod agx_resources;
#[path = "../../drivers/gpu/drm/asahi/m3_init_layout.rs"]
mod m3_init_layout;
#[path = "../../drivers/gpu/drm/asahi/m3_init_storage.rs"]
mod m3_init_storage;
#[path = "../../drivers/gpu/drm/asahi/m3_thermal_policy.rs"]
mod m3_thermal_policy;

use agx_resources as m3_resources;
#[path = "../../drivers/gpu/drm/asahi/m3_firmware.rs"]
mod m3_firmware;
#[path = "../../drivers/gpu/drm/asahi/t8122_knobs.rs"]
mod t8122_knobs;
#[path = "../../drivers/gpu/drm/asahi/t6031_knobs.rs"]
mod t6031_knobs;
#[path = "../../drivers/gpu/drm/asahi/m3_pass_layout.rs"]
mod m3_pass_layout;
