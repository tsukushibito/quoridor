// SPDX-License-Identifier: GPL-3.0-or-later
//! Explicit weight-owned full search. Never switches existing UI/default search.

use othello_core::{
    full_eval::{FullWeights, TableInterpretation},
    full_search::{FullSearch, FullSearchOptions, MpcCoefficients},
};
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub struct FullSearchModel {
    engine: FullSearch,
}

#[wasm_bindgen]
impl FullSearchModel {
    /// Inputs are loaded once; callers bind source/weight/image identities.
    /// Coefficients must be an explicit JSON object (original defaults are
    /// exposed by original_mpc_coefficients_json), not an implicit model switch.
    #[wasm_bindgen(constructor)]
    pub fn new(
        midgame: &[u8],
        ordering: &[u8],
        interpretation: &str,
        hash_level: u8,
        coefficients: &str,
    ) -> Result<FullSearchModel, JsValue> {
        let interpretation: TableInterpretation =
            interpretation.parse().map_err(super::js_error)?;
        let coefficients: MpcCoefficients =
            serde_json::from_str(coefficients).map_err(super::js_error)?;
        let weights = FullWeights::from_bytes(midgame, ordering).map_err(super::js_error)?;
        Ok(Self {
            engine: FullSearch::new(weights, interpretation, hash_level, coefficients)
                .map_err(super::js_error)?,
        })
    }
    pub fn clear(&mut self) {
        self.engine.clear();
    }
    /// Synchronous Wasm cancellation still requires terminating the actual
    /// Worker. postMessage cannot interrupt a running Wasm call/event loop.
    pub fn search_json(&mut self, input: &str, options: &str) -> Result<String, JsValue> {
        let state = super::state(input)?;
        let options: FullSearchOptions = serde_json::from_str(options).map_err(super::js_error)?;
        #[cfg(target_arch = "wasm32")]
        let result = self
            .engine
            .search(&state, options, super::browser_now, || false);
        #[cfg(not(target_arch = "wasm32"))]
        let result = self.engine.search_native(&state, options);
        super::json(&result.map_err(super::js_error)?)
    }
}

#[wasm_bindgen]
pub fn original_mpc_coefficients_json() -> Result<String, JsValue> {
    super::json(&MpcCoefficients::default())
}
