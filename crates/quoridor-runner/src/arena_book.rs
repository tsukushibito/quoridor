//! Convert NN0 legal-prefix preparation into a frozen eight-family book.
use crate::arena::{self, Book, BookUse, Cohort, Opening, Reference};
use quoridor_core::research::{HistoryKey, SigmaContext};
use quoridor_data::Result;
use serde_json::{Value, json};
pub fn from_preparation(p: &Value, source_sha256: String) -> Result<Book> {
    let rows = p["rows"].as_array().ok_or("BOOK_ROWS")?;
    if p["schema"] != "native-prefix-selection-v1"
        || p["seed"] != 32710001_u64
        || rows.len() != 8
        || !arena::sha_valid(&source_sha256)
    {
        return Err("BOOK_SCHEMA_EIGHT_SEED".into());
    }
    let settings = json!({"seed":32710001,"opening_plies":[0,2,4,6,8,10,12,14],"max_attempts":32,"min_distance":2,"max_distance_difference":2,"pawn_fraction":0.5,"primary_shallow_slots":8,"preparation_node_cap":250000});
    if p["generation"] != settings {
        return Err("BOOK_PREBOUND_SETTINGS".into());
    }
    let ids: Vec<String> = (0..8).map(|i| format!("best51-prefix-{i}")).collect();
    let mut openings = Vec::new();
    let mut seen = std::collections::BTreeSet::new();
    for (slot, r) in rows.iter().enumerate() {
        let prefix: Vec<u16> = serde_json::from_value(r["prefix"].clone())?;
        let attempt = r["attempt"].as_u64().ok_or("BOOK_ATTEMPT")?;
        if r["slot"] != slot
            || prefix.len() != slot * 2
            || attempt >= 32
            || r["shallow_terminal_depth2"] != false
            || !seen.insert(prefix.clone())
        {
            return Err("BOOK_INCOMPLETE_DUPLICATE_CHECK".into());
        }
        let context = SigmaContext::from_prefix(&prefix)?;
        if context.terminal_value().is_some() {
            return Err("BOOK_EARLY_TERMINAL".into());
        }
        let key = HistoryKey::from(context.position()).sigma_string();
        let history: Vec<_> = context
            .history_counts()
            .iter()
            .map(|(k, n)| (k.sigma_string(), *n))
            .collect();
        if r["feature"]["key"] != key || r["feature"]["history"] != json!(history) {
            return Err("BOOK_HISTORY_BINDING".into());
        }
        openings.push(Opening {id:ids[slot].clone(),cohort:if slot==0 {Cohort::Initial}else{Cohort::Main},lineage:"common-initial/PRNG32710001".into(),siblings:ids.iter().filter(|id|**id!=ids[slot]).cloned().collect(),original_seed:Some(32710001),
            reference:Some(Reference {source_sha256:source_sha256.clone(),model_sha256:None,settings:json!({"preparation_sha256":arena::json_digest(p)?,"family_slot":slot,"attempted_candidates":attempt+1,"full_history":history,"depth2_nonterminal":true}),q_definition:None,q_perspective:None,q_aggregation:None,q:None}),
            selection_reason:"Targetblind NN0 depth2 nonterminal and wall-distance filters; no learned/Sigma outcome or calibrated balance guarantee.".into(),candidate_pool_size:attempt+1,prefix});
    }
    Ok(Book {id:"best51-distance-eight-prefix-v1".into(),usage:BookUse::Main,frozen_before_candidate_results:true,independence:"Eight families share initial state/PRNG lineage; bootstrap is conditional on this fixed correlated book, no general strength precision guarantee.".into(),openings})
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn partial_book_is_not_relabelled_eight_pairs() {
        assert!(
            from_preparation(
                &json!({"schema":"native-prefix-selection-v1","seed":32710001,"rows":[]}),
                "a".repeat(64)
            )
            .is_err()
        );
    }
}
