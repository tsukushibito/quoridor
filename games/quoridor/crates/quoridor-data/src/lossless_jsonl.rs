//! Bounded single-member gzip IO. Content identity is exact uncompressed bytes.
use crate::{Result, file_sha};
use flate2::{Compression, GzBuilder, bufread::GzDecoder, write::GzEncoder};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{self, BufReader, Read, Write},
    os::unix::fs::PermissionsExt,
    path::{Path, PathBuf},
};

pub const ENCODING: &str = "gzip-single-member-v1";
pub const BUFFER: usize = 65536;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FileRef {
    pub path: PathBuf,
    pub sha256: String,
    pub bytes: u64,
    pub mode: String,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Content {
    pub encoding: String,
    pub compressed: FileRef,
    pub raw_sha256: String,
    pub raw_bytes: u64,
}

struct LimitedFile {
    file: File,
    used: u64,
    cap: u64,
    disabled: bool,
}
impl Write for LimitedFile {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        if self.disabled
            || self
                .used
                .checked_add(bytes.len() as u64)
                .is_none_or(|n| n > self.cap)
        {
            self.disabled = true;
            return Err(io::Error::other("compressed output upper refused"));
        }
        match self.file.write(bytes) {
            Ok(n) => {
                self.used += n as u64;
                Ok(n)
            }
            Err(e) => {
                self.disabled = true;
                Err(e)
            }
        }
    }
    fn flush(&mut self) -> io::Result<()> {
        if self.disabled {
            return Err(io::Error::other("failed gzip sink remains disabled"));
        }
        self.file.flush()
    }
}

pub struct Writer {
    encoder: Option<GzEncoder<LimitedFile>>,
    path: PathBuf,
    raw_hash: Sha256,
    raw_bytes: u64,
    raw_cap: u64,
}
impl Writer {
    pub fn create(path: &Path, raw_cap: u64, compressed_cap: u64) -> Result<Self> {
        if raw_cap == 0 || compressed_cap == 0 {
            return Err("explicit encoding bounds required".into());
        }
        let file = OpenOptions::new().create_new(true).write(true).open(path)?;
        Ok(Self {
            encoder: Some(GzBuilder::new().mtime(0).write(
                LimitedFile {
                    file,
                    used: 0,
                    cap: compressed_cap,
                    disabled: false,
                },
                Compression::fast(),
            )),
            path: path.into(),
            raw_hash: Sha256::new(),
            raw_bytes: 0,
            raw_cap,
        })
    }
    pub fn compressed_bytes(&self) -> Result<u64> {
        if let Some(e) = &self.encoder {
            Ok(e.get_ref().used)
        } else {
            Ok(std::fs::metadata(&self.path)?.len())
        }
    }
    pub fn raw_bytes(&self) -> u64 {
        self.raw_bytes
    }
    pub fn append(&mut self, raw: &[u8]) -> Result<()> {
        let next = self
            .raw_bytes
            .checked_add(raw.len() as u64)
            .ok_or("raw content overflow")?;
        if next > self.raw_cap {
            if let Some(e) = &mut self.encoder {
                e.get_mut().disabled = true;
            }
            return Err("uncompressed content upper refused".into());
        }
        let e = self.encoder.as_mut().ok_or("closed gzip writer")?;
        // Hash precisely accepted logical bytes; failed partial writes never publish Content.
        if let Err(primary) = e.write_all(raw) {
            e.get_mut().disabled = true;
            return Err(primary.into());
        }
        self.raw_hash.update(raw);
        self.raw_bytes = next;
        Ok(())
    }
    pub fn sync_data(&mut self) -> Result<()> {
        let e = self.encoder.as_mut().ok_or("closed gzip writer")?;
        if let Err(primary) = e.flush() {
            e.get_mut().disabled = true;
            return Err(primary.into());
        }
        if let Err(primary) = e.get_ref().file.sync_data() {
            e.get_mut().disabled = true;
            return Err(primary.into());
        }
        Ok(())
    }
    pub fn finish(&mut self) -> Result<Content> {
        let mut e = self
            .encoder
            .take()
            .ok_or("gzip finalization already attempted")?;
        let primary = e.try_finish().err();
        // Disable all drop-time output: failed trailers cannot be retried into success.
        let sync = e.get_ref().file.sync_all().err();
        e.get_mut().disabled = true;
        drop(e);
        if primary.is_some() || sync.is_some() {
            return Err(
                format!("gzip finalization primary:{primary:?}; secondary_sync:{sync:?}").into(),
            );
        }
        let m = std::fs::metadata(&self.path)?;
        Ok(Content {
            encoding: ENCODING.into(),
            raw_sha256: format!("{:x}", self.raw_hash.clone().finalize()),
            raw_bytes: self.raw_bytes,
            compressed: FileRef {
                path: self.path.clone(),
                sha256: file_sha(&self.path)?,
                bytes: m.len(),
                mode: format!("{:04o}", m.permissions().mode() & 0o7777),
            },
        })
    }
}
impl Drop for Writer {
    fn drop(&mut self) {
        if let Some(mut e) = self.encoder.take() {
            e.get_mut().disabled = true;
            drop(e);
        }
    }
}

pub struct Reader {
    decoder: GzDecoder<BufReader<File>>,
    expected: Content,
    hash: Sha256,
    used: u64,
    ended: bool,
    failed: bool,
}
impl Reader {
    pub fn open(content: &Content) -> Result<Self> {
        let p = &content.compressed.path;
        let m = std::fs::symlink_metadata(p)?;
        if content.encoding != ENCODING
            || !m.is_file()
            || m.len() != content.compressed.bytes
            || format!("{:04o}", m.permissions().mode() & 0o7777) != content.compressed.mode
            || file_sha(p)? != content.compressed.sha256
            || content.raw_sha256.len() != 64
            || !content
                .raw_sha256
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err("actual gzip FileRef/content identity differs".into());
        }
        Ok(Self {
            decoder: GzDecoder::new(BufReader::with_capacity(BUFFER, File::open(p)?)),
            expected: content.clone(),
            hash: Sha256::new(),
            used: 0,
            ended: false,
            failed: false,
        })
    }
}
impl Read for Reader {
    fn read(&mut self, output: &mut [u8]) -> io::Result<usize> {
        if self.failed {
            return Err(io::Error::other(
                "previous gzip read failure remains authoritative",
            ));
        }
        if output.is_empty() || self.ended {
            return Ok(0);
        }
        let n = match self.decoder.read(output) {
            Ok(n) => n,
            Err(e) => {
                self.failed = true;
                return Err(e);
            }
        }; // CRC/truncated trailer checked by the installed codec.
        if n == 0 {
            let mut trailing = [0];
            let remaining = match self.decoder.get_mut().read(&mut trailing) {
                Ok(n) => n,
                Err(e) => {
                    self.failed = true;
                    return Err(e);
                }
            };
            if remaining != 0
                || self.used != self.expected.raw_bytes
                || format!("{:x}", self.hash.clone().finalize()) != self.expected.raw_sha256
            {
                self.failed = true;
                return Err(io::Error::other(
                    "gzip trailing/member/raw content mismatch",
                ));
            }
            let m = match std::fs::symlink_metadata(&self.expected.compressed.path) {
                Ok(m) => m,
                Err(e) => {
                    self.failed = true;
                    return Err(e);
                }
            };
            if !m.is_file()
                || m.len() != self.expected.compressed.bytes
                || format!("{:04o}", m.permissions().mode() & 0o7777)
                    != self.expected.compressed.mode
            {
                self.failed = true;
                return Err(io::Error::other("compressed FileRef changed during decode"));
            }
            self.ended = true;
        } else {
            self.used = match self.used.checked_add(n as u64) {
                Some(n) => n,
                None => {
                    self.failed = true;
                    return Err(io::Error::other("decoded count overflow"));
                }
            };
            if self.used > self.expected.raw_bytes {
                self.failed = true;
                return Err(io::Error::other("decoded byte cap exceeded"));
            }
            self.hash.update(&output[..n]);
        }
        Ok(n)
    }
}

/// Streaming correspondence at ordinary finalization; no semantic/scientific certificate.
pub fn verify(content: &Content) -> Result<()> {
    let mut r = Reader::open(content)?;
    let mut buffer = [0u8; BUFFER];
    while r.read(&mut buffer)? != 0 {}
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn path(name: &str) -> PathBuf {
        std::env::temp_dir().join(format!("codec362-{}-{name}", std::process::id()))
    }
    #[test]
    fn exact_fp32_jsonl_order_roundtrip_no_raw_file() {
        let p = path("roundtrip.gz");
        let raw=b"{\"raw_value_bits\":2147483648,\"raw_value\":-0.0}\n{\"raw_value_bits\":1073741824,\"raw_value\":2.0}\n";
        let mut w = Writer::create(&p, 4096, 8192).unwrap();
        w.append(raw).unwrap();
        let c = w.finish().unwrap();
        let mut decoded = vec![];
        Reader::open(&c).unwrap().read_to_end(&mut decoded).unwrap();
        assert_eq!(decoded, raw);
        assert_eq!(c.raw_bytes, raw.len() as u64);
        std::fs::remove_file(p).unwrap();
    }
    #[test]
    fn partial_trailer_and_extra_member_refuse() {
        let p = path("truncated.gz");
        let mut w = Writer::create(&p, 4096, 8192).unwrap();
        w.append(b"{}\n").unwrap();
        let mut c = w.finish().unwrap();
        let mut bytes = std::fs::read(&p).unwrap();
        bytes.truncate(bytes.len() - 3);
        std::fs::write(&p, &bytes).unwrap();
        c.compressed.bytes = bytes.len() as u64;
        c.compressed.sha256 = file_sha(&p).unwrap();
        let mut failed = Reader::open(&c).unwrap();
        assert!(failed.read_to_end(&mut vec![]).is_err());
        assert!(failed.read(&mut [0; 1]).is_err());
        let mut encoded = GzBuilder::new()
            .mtime(0)
            .write(Vec::new(), Compression::fast());
        encoded.write_all(b"{}\n").unwrap();
        let member = encoded.finish().unwrap();
        let mut extra = member.clone();
        extra.extend_from_slice(&member);
        std::fs::write(&p, &extra).unwrap();
        c.compressed.bytes = extra.len() as u64;
        c.compressed.sha256 = file_sha(&p).unwrap();
        let mut failed = Reader::open(&c).unwrap();
        assert!(failed.read_to_end(&mut vec![]).is_err());
        assert!(failed.read(&mut [0; 1]).is_err());
        let mut extra = member;
        extra.extend(b"unbound trailing bytes");
        std::fs::write(&p, &extra).unwrap();
        c.compressed.bytes = extra.len() as u64;
        c.compressed.sha256 = file_sha(&p).unwrap();
        assert!(Reader::open(&c).unwrap().read_to_end(&mut vec![]).is_err());
        std::fs::remove_file(p).unwrap();
    }
    #[test]
    fn failed_sink_cannot_publish_content_or_drop_salvage() {
        let p = path("cap.gz");
        let mut w = Writer::create(&p, 4096, 1).unwrap();
        let _ = w.append(b"{}\n");
        assert!(w.finish().is_err());
        let n = std::fs::metadata(&p).unwrap().len();
        drop(w);
        assert_eq!(std::fs::metadata(&p).unwrap().len(), n);
        std::fs::remove_file(p).unwrap();
    }
}
