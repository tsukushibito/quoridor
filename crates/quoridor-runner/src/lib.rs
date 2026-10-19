//! Common arena owns games; native engines and bounded upstream helper children own Search.
pub mod arena;
pub mod arena_book;
pub mod arena_clock;
mod arena_manifest;
pub mod arena_statistics;
pub mod claustrophobia;
pub mod config;
pub mod research_manifest;
pub mod resources;
pub mod runtime;
mod sigma_clock;
mod sigma_evaluator;
pub mod teacher_pilot;
pub mod teacher_pilot_execution;
pub mod value_search_strength;
pub use arena_manifest::audit as audit_arena;
pub use arena_manifest::recover as recover_arena;
pub use config::{Config, Engine};
pub use runtime::{RunReport, run};

pub mod value_search_compare;

// Single temporary 360 inlet; no normal arena profile selection.
#[cfg(feature = "measurement")]
pub mod measurement;
