// SPDX-License-Identifier: GPL-2.0-only OR MIT

//! Device coredump support.
//!
//! C header: [`include/linux/devcoredump.h`](srctree/include/linux/devcoredump.h)

use crate::{
    alloc, bindings, device,
    error::{code::EIO, from_result},
    prelude::Result,
    time::Jiffies,
    types::ForeignOwnable,
    ThisModule,
};

use core::ops::Deref;

/// The default timeout for device coredumps.
pub const DEFAULT_TIMEOUT: Jiffies = bindings::DEVCD_TIMEOUT as Jiffies;

/// Trait to implement reading from a device coredump.
///
/// Users must implement this trait to provide device coredump support.
pub trait DevCoreDump {
    /// Reads part of the coredump into `buf`, starting at `offset`.
    ///
    /// Returns how many bytes were written. Return `Ok(0)` once there is nothing left to read.
    ///
    /// Userspace can read from several threads at once, so this may run concurrently.
    fn read(&self, buf: &mut [u8], offset: usize) -> Result<usize>;
}

/// # Safety
///
/// `buffer` must point to `count` writable bytes, and `data` must come from `T::into_foreign()`
/// and not have been freed yet.
unsafe extern "C" fn read_callback<
    'a,
    T: ForeignOwnable<Borrowed<'a>: Deref<Target = D>>,
    D: DevCoreDump,
>(
    buffer: *mut crate::ffi::c_char,
    offset: bindings::loff_t,
    count: usize,
    data: *mut crate::ffi::c_void,
    _datalen: usize,
) -> isize {
    // SAFETY: `data` comes from `T::into_foreign()` and has not been freed yet.
    let coredump = unsafe { T::borrow(data.cast()) };
    // The core hands us an uninitialized buffer and copies back however many bytes we report.
    // Initialize every byte before calling the reader; unwritten bytes remain zero.
    //
    // SAFETY: `buffer` points to `count` writable bytes.
    unsafe { buffer.write_bytes(0, count) };
    // SAFETY: Same as above, and the buffer is initialized now.
    let buf = unsafe { core::slice::from_raw_parts_mut(buffer.cast::<u8>(), count) };

    from_result(|| {
        let len = coredump.read(buf, offset.try_into()?)?;

        if len > count {
            return Err(EIO);
        }

        Ok(len.try_into()?)
    })
}

#[macros::kunit_tests(rust_devcoredump_kunit)]
mod tests {
    use super::*;
    use crate::prelude::*;

    enum Reader {
        Unwritten,
        Partial,
        Oversized,
        Error,
        Eof,
    }

    impl DevCoreDump for Reader {
        fn read(&self, buf: &mut [u8], offset: usize) -> Result<usize> {
            match self {
                Self::Unwritten => Ok(buf.len()),
                Self::Partial => {
                    buf[..3].copy_from_slice(&[offset as u8, 0x12, 0x34]);
                    Ok(3)
                }
                Self::Oversized => Ok(buf.len() + 1),
                Self::Error => Err(EIO),
                Self::Eof => Ok(0),
            }
        }
    }

    fn read(reader: Reader, offset: bindings::loff_t) -> Result<(isize, [u8; 18])> {
        let dump = KBox::new(reader, GFP_KERNEL)?;
        let data = dump.into_foreign();
        let mut buffer = [0xa5u8; 18];

        // SAFETY: The middle 16 bytes are writable and `data` owns a live Reader.
        let len = unsafe {
            read_callback::<KBox<Reader>, Reader>(
                buffer.as_mut_ptr().add(1).cast(),
                offset,
                16,
                data,
                0,
            )
        };
        // SAFETY: The callback has returned; this is the only release of `data`.
        unsafe { free_callback::<KBox<Reader>, Reader>(data) };

        assert_eq!(buffer[0], 0xa5);
        assert_eq!(buffer[17], 0xa5);
        Ok((len, buffer))
    }

    #[test]
    fn unwritten_bytes_are_zero() -> Result {
        let (len, buffer) = read(Reader::Unwritten, 0)?;
        assert_eq!(len, 16);
        assert_eq!(&buffer[1..17], &[0; 16]);
        Ok(())
    }

    #[test]
    fn partial_read_preserves_offset() -> Result {
        let (len, buffer) = read(Reader::Partial, 7)?;
        assert_eq!(len, 3);
        assert_eq!(&buffer[1..4], &[7, 0x12, 0x34]);
        assert_eq!(&buffer[4..17], &[0; 13]);
        Ok(())
    }

    #[test]
    fn oversized_read_is_rejected() -> Result {
        let (len, _) = read(Reader::Oversized, 0)?;
        assert_eq!(len, EIO.to_errno() as isize);
        Ok(())
    }

    #[test]
    fn negative_offset_is_rejected() -> Result {
        let (len, _) = read(Reader::Partial, -1)?;
        assert_eq!(len, EINVAL.to_errno() as isize);
        Ok(())
    }

    #[test]
    fn error_and_eof_are_preserved() -> Result {
        assert_eq!(read(Reader::Error, 0)?.0, EIO.to_errno() as isize);
        assert_eq!(read(Reader::Eof, 0)?.0, 0);
        Ok(())
    }
}

/// # Safety
///
/// `data` must come from `T::into_foreign()`, and must not be used again after this call.
unsafe extern "C" fn free_callback<
    'a,
    T: ForeignOwnable<Borrowed<'a>: Deref<Target = D>>,
    D: DevCoreDump,
>(
    data: *mut crate::ffi::c_void,
) {
    // SAFETY: `data` comes from `T::into_foreign()`, and we own it from here on.
    unsafe {
        T::from_foreign(data.cast());
    }
}

/// Registers a coredump for the given device.
///
/// The core takes ownership of `coredump` and drops it when userspace dismisses the dump or
/// `timeout` runs out. If the dump cannot be registered, for example because the previous one for
/// `dev` is still pending, it is dropped right away.
///
/// `module` should be the module implementing [`DevCoreDump`]: it stays pinned for as long as the
/// dump is around.
pub fn dev_coredump<'a, T, D>(
    dev: &device::Device,
    module: &'static ThisModule,
    coredump: T,
    gfp: alloc::Flags,
    timeout: Jiffies,
) where
    // The owner is borrowed concurrently and dropped later from a workqueue.
    T: ForeignOwnable<Borrowed<'a>: Deref<Target = D>> + Send + Sync + 'static,
    D: DevCoreDump + Sync,
{
    // SAFETY: `dev` and `module` are valid, and the core takes its own references to them. The
    // pointer from `into_foreign()` only ever reaches our two callbacks, and `free_callback` runs
    // last and exactly once.
    unsafe {
        bindings::dev_coredumpm_timeout(
            dev.as_raw(),
            module.0,
            coredump.into_foreign(),
            0,
            gfp.as_raw(),
            Some(read_callback::<'a, T, D>),
            Some(free_callback::<'a, T, D>),
            timeout,
        )
    }
}
