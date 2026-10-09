//! All hot game/search/inference ownership stays inside one native process.
pub mod arena;
pub mod arena_book;
pub mod arena_clock;
mod arena_manifest;
pub mod arena_statistics;
pub mod config;
pub mod resources;
pub mod runtime;
mod sigma_clock;
pub mod sigma_qualification;
pub mod teacher_pilot;
pub mod teacher_pilot_execution;
pub use arena_manifest::audit as audit_arena;
pub use arena_manifest::recover as recover_arena;
pub use arena_manifest::source_bindings as compiled_source_bindings;
pub use config::{Config, Engine};
pub use runtime::{RunReport, run};
