//! All hot game/search/inference ownership stays inside one native process.
pub mod config;
pub mod resources;
pub mod runtime;
pub use config::{Config, Engine};
pub use runtime::{RunReport, run};
