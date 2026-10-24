//! Saved evaluation publication. The qualified parent owns grouping and exclusion math.
use super::*;
use crate::research_manifest::FileRef;
use serde_json::{Value, json};
use std::collections::BTreeMap;

const CONTROL: u64 = 65536;
const CENSUS: u64 = 4 * 1024 * 1024;
const PARENT: u64 = 512 * 1024 * 1024;

fn reference(value: &Value, key: &str) -> Result<FileRef> {
    Ok(serde_json::from_value(value[key].clone())?)
}
fn array<'a>(value: &'a Value, key: &str) -> Result<&'a Vec<Value>> {
    value[key]
        .as_array()
        .ok_or_else(|| format!("evaluation {key} array missing").into())
}
fn text<'a>(value: &'a Value, key: &str) -> Result<&'a str> {
    value[key]
        .as_str()
        .ok_or_else(|| format!("evaluation {key} string missing").into())
}
fn require(condition: bool, message: &str) -> Result<()> {
    if condition {
        Ok(())
    } else {
        Err(message.into())
    }
}
fn same_ref(value: &Value, expected: &FileRef) -> Result<bool> {
    Ok(serde_json::from_value::<FileRef>(value.clone())? == *expected)
}

/// Read/hash each parent once with the existing custody reader. Unselected root
/// JSON stays opaque: only its id/family/source metadata is interpreted below.
pub(super) fn prepare(c: &EvaluationInputConfig) -> Result<Value> {
    let s = &c.saved_evaluation;
    require(
        c.output.is_absolute() && s.components > 0 && s.components <= 128,
        "bounded evaluation-only count and fresh absolute output required",
    )?;
    let authority = read_input_reference_max(&s.authority, CONTROL)?;
    let projection = read_input_reference_max(&s.checked_dispositions, CENSUS)?;
    require(
        authority["status"]
            == "CHECKED_IDENTITY_AUTHORITY_AND_LOCATORS_ONLY_NOT_NEW_ELIGIBILITY_OR_PUBLICATION"
            && same_ref(
                &authority["checkedIdentityProjection"],
                &s.checked_dispositions,
            )?,
        "checked evaluation authority/projection identity differs",
    )?;
    let pool_ref = reference(&authority, "parentPool")?;
    let selection_ref = reference(&authority, "saved1408Selection")?;
    let census_ref = reference(&authority, "nativeCensus")?;
    let config_ref = reference(&authority, "originalNativeConfig")?;
    let exclusion_ref = reference(&authority, "originalExclusionAuthority")?;
    let bindings_ref = reference(&authority, "actualSavedSelectionNormalBindings")?;
    let pool = read_input_reference_max(&pool_ref, CONTROL)?;
    let selection = read_input_reference_max(&selection_ref, CONTROL)?;
    let bindings = read_input_reference_max(&bindings_ref, CONTROL)?;
    let config = read_input_reference_max(&config_ref, CONTROL)?;
    let exclusions = read_input_reference_max(&exclusion_ref, CONTROL)?;
    let census = read_input_reference_max(&census_ref, CENSUS)?;
    let parent_ref = reference(&pool["native"], "partition")?;
    let source_ref = reference(&pool["native"], "source_observations")?;
    let schedule_ref = reference(&pool["native"], "schedule")?;
    let selected_ref = reference(&selection["native"], "partition")?;
    require(
        pool["status"] == "COMPLETE_FIXED8192_POOL_BEFORE_FIRST1408"
            && pool["sourcePoolComplete"] == true
            && pool["native"] == authority["parentFileRefs"]
            && selection["status"]
                == "SAVED1408_NATIVE_SELECTION_ACCEPTED_NOT_CLASSES_LABELS_OR_FIT"
            && selection["native"] == authority["selectedFileRefs"]
            && pool["native"]["outcomes_selected"] == false
            && selection["native"]["outcomes_selected"] == false
            && pool["normalBuild"] == authority["sourceBuildByRef"]
            && bindings["refs"]["normalBuild"] == pool["normalBuild"]
            && same_ref(&selection["binding"], &bindings_ref)?
            && same_ref(&bindings["refs"]["sourcePoolCollection"], &pool_ref)?
            && same_ref(&bindings["refs"]["selectionCensus"], &census_ref)?
            && same_ref(&pool["refs"]["input-generation.json"], &config_ref)?
            && same_ref(&pool["exclusion_authority"], &exclusion_ref)?
            && same_ref(&selection["native"]["selection_census"], &census_ref)?
            && same_ref(&selection["native"]["source_observations"], &source_ref)?,
        "qualified parent/selection/normal binding differs",
    )?;
    let selection_config_ref = reference(&bindings["refs"], "config")?;
    let selection_config = read_input_reference_max(&selection_config_ref, CONTROL)?;
    let subset = &selection_config["saved_subset"];
    require(
        same_ref(&subset["schedule"], &schedule_ref)?
            && same_ref(&subset["source_config"], &config_ref)?
            && same_ref(&subset["census"], &census_ref)?
            && same_ref(&subset["exposure_parent"], &exclusion_ref)?
            && subset["excluded_prefix_components"] == 0
            && subset["split_counts"] == selection["native"]["actual_components"]
            && selection_config["prefix_seed"] == config["prefix_seed"]
            && selection_config["split_seed"] == config["split_seed"]
            && selection_config["families"] == config["families"]
            && selection["native"]["component_deficits"]
                == json!({"train":0,"validation":0,"test":0})
            && config["families"] == 8192
            && config["trajectory"]["wall_layer_observations"] == json!([0, 1, 0])
            && exclusions["schema"] == "research.named-prefix-exclusion-authority.v1"
            && exclusions == authority["sourceExclusionAuthorityByRef"]
            && config["excluded_books"] == exclusions["excluded_books"]
            && config["excluded_static_inputs"] == exclusions["excluded_static_inputs"]
            && same_ref(&exclusions["nativeInputConfig"], &config_ref)?
            && exclusions["excluded_books"]
                .as_array()
                .is_some_and(|v| !v.is_empty())
            && !exclusions["excluded_static_inputs"].is_null(),
        "saved selection or inherited named exclusion scope differs",
    )?;
    require(
        projection["schema"] == "research.checked-published-rank-selection-disposition.v1"
            && projection["columns"]
                == json!([
                    "rank0",
                    "component",
                    "member_ids",
                    "source_series_ids",
                    "disposition",
                    "prospective_split",
                    "actual_selected1408_split",
                    "current_disposition"
                ])
            && same_ref(&projection["originalNativeCensus"], &census_ref)?
            && same_ref(&projection["actualNativeSelectedPartition"], &selected_ref)?
            && same_ref(&projection["qualifiedOriginalPool"], &pool_ref)?
            && same_ref(&projection["qualifiedSavedSelection"], &selection_ref)?
            && same_ref(&projection["sourceObservationsByRef"], &source_ref)?
            && same_ref(&projection["publishedScheduleByRef"], &schedule_ref)?
            && same_ref(&projection["nativeInputConfig"], &config_ref)?
            && same_ref(&projection["sourceExclusionAuthorityByRef"], &exclusion_ref)?
            && projection["nativeRankSeed"] == config["split_seed"]
            && census["schema"] == "research.identity-only-component-census.v2"
            && census["columns"]
                == json!([
                    "rank0",
                    "component",
                    "member_ids",
                    "source_series_ids",
                    "disposition",
                    "prospective_split"
                ])
            && same_ref(&census["partition"], &parent_ref)?
            && same_ref(&census["publishedScheduleByRef"], &schedule_ref)?
            && same_ref(&census["nativeInputConfig"], &config_ref)?
            && same_ref(&census["sourceCollection"], &pool_ref)?
            && same_ref(&census["exposureParent"], &exclusion_ref)?
            && census["sourceExclusionAuthority"] == exclusions
            && census["componentRankSeed"] == config["split_seed"],
        "published native rank/projection authority differs",
    )?;
    // These are opaque parent JSON reads, including protected bytes/prefix arrays.
    // No SeriesPartition reconstruction or unselected ContextRecord/rules audit.
    let parent = read_input_reference_max(&parent_ref, PARENT)?;
    let selected = read_input_reference_max(&selected_ref, PARENT)?;
    let schedule = read_input_reference_max(&schedule_ref, PARENT)?;
    require(
        parent["actual"] == pool["native"]["actual_components"]
            && parent["deficits"] == pool["native"]["component_deficits"]
            && parent["requested"] == pool["native"]["requested_components"]
            && parent["requested"] == config["trajectory"]["split_counts"]
            && parent["partition"]["seed"] == config["split_seed"]
            && selected["actual"] == selection["native"]["actual_components"]
            && selected["requested"] == selection["native"]["requested_components"]
            && selected["deficits"] == selection["native"]["component_deficits"]
            && same_ref(&selected["selection"]["source_partition"], &parent_ref)?
            && same_ref(&selected["selection"]["source_observations"], &source_ref)?
            && same_ref(&selected["selection"]["census"], &census_ref)?
            && same_ref(&selected["selection"]["source_schedule"], &schedule_ref)?
            && same_ref(&selected["selection"]["source_config"], &config_ref)?
            && same_ref(&selected["selection"]["exposure_parent"], &exclusion_ref)?
            && selected["selection"]["split_counts"] == selected["actual"]
            && selected["partition"]["seed"] == config["split_seed"]
            && schedule["generator_version"] == quoridor_data::common_corpus::VERSION
            && same_ref(&schedule["partition"], &parent_ref)?
            && same_ref(&schedule["source_observations"], &source_ref)?
            && schedule["prefix_seed"] == config["prefix_seed"]
            && schedule["split_seed"] == config["split_seed"]
            && schedule["trajectory"] == config["trajectory"]
            && schedule["excluded_books"] == config["excluded_books"]
            && schedule["excluded_static_inputs"] == config["excluded_static_inputs"]
            && array(&schedule, "series")?.len() == 8192,
        "qualified full parent/schedule correspondence differs",
    )?;
    let plan = checked_components(
        &parent,
        &selected,
        &schedule,
        &census,
        &projection,
        s.components,
    )?;
    require(
        authority["checkedNativeRanks"].as_u64() == Some(plan.parent_components as u64)
            && authority["checkedExcludedWholeComponents"].as_u64() == Some(plan.excluded as u64)
            && authority["protectedH"].as_u64() == Some(plan.protected_h as u64)
            && authority["originalDeficit"] == pool["native"]["component_deficits"]["train"],
        "authority actual component census differs",
    )?;
    let counts = &selection["native"]["actual_components"];
    require(
        census["counts"]
            == json!({
                "originalSurvivors":plan.parent_components,"originalDeficit":authority["originalDeficit"],
                "excludedComponents":0,"eligibleNamedScope":plan.parent_components
            })
            && census["prospective"]
                == json!({
                    "selected":plan.excluded,"train":counts["train"],"validation":counts["validation"],
                    "holdout":counts["test"],"deficitWithinNamedScope":0
                }),
        "qualified original census summary differs",
    )?;
    let source = read_input_reference_max(&source_ref, PARENT)?;
    require(
        source["schema"] == "quoridor-prefix-series-full-history-v1"
            && source["teacher_labels"] == false
            && same_ref(&source["partition"], &parent_ref)?,
        "bound unlabelled full-history source differs",
    )?;
    let (families, mapping) = evaluation_rows(&source, &parent, &schedule, &plan)?;
    // No output directory or complete book exists until every check/audit succeeds.
    std::fs::create_dir(&c.output)?;
    let marker = c.output.join("INCOMPLETE");
    std::fs::write(
        &marker,
        "evaluation publication incomplete; no arena admitted\n",
    )?;
    let producer = json!({"authority":s.authority,"checked_dispositions":s.checked_dispositions,
        "source_observations":source_ref,"source_schedule":schedule_ref,
        "original_partition":parent_ref,"excluded_selection":selected_ref});
    let book = publish(
        &c.output,
        "book.json",
        &json!({
            "complete":true,"rules":"research-standard-2p-threefold-goal-first-v1",
            "families":families,"producer_provenance":producer
        }),
    )?;
    let mapping_ref = publish(
        &c.output,
        "evaluation-census.json",
        &json!({
            "schema":"quoridor-native-saved-evaluation-census-v1","producer":producer,
            "parent_components":plan.parent_components,"excluded_components":plan.excluded,
            "protected_H_components":plan.protected_h,"eligible_named_scope":plan.eligible,
            "selected_components":s.components,"deficit":0,"evaluation_only":true,
            "excluded_from_future_fit":true,"members":mapping
        }),
    )?;
    let result = json!({"book":book,"evaluation_census":mapping_ref,
        "selected_components":s.components,"eligible_named_scope":plan.eligible,
        "excluded_components":plan.excluded,"protected_H_typed_context_or_rules_audits":0,
        "opaque_parent_JSON_read_including_protected_bytes":true,
        "typed_context_rows":s.components,"generated_transitions":0,
        "search_calls":0,"teacher_calls":0,"fit_calls":0});
    write_input_json(&c.output, "publication.json", &result)?;
    std::fs::remove_file(marker)?;
    Ok(result)
}

fn publish(output: &std::path::Path, name: &str, value: &Value) -> Result<FileRef> {
    use std::os::unix::fs::PermissionsExt;
    let bound = write_input_json(output, name, value)?;
    let metadata = std::fs::metadata(&bound.path)?;
    Ok(FileRef {
        path: bound.path,
        sha256: bound.sha256,
        bytes: metadata.len(),
        mode: format!("{:04o}", metadata.permissions().mode() & 0o777),
    })
}

struct EvaluationPlan {
    members: Vec<(usize, String, String, String)>,
    parent_components: usize,
    excluded: usize,
    protected_h: usize,
    eligible: usize,
}

/// Verify metadata membership over EVERY original component without interpreting
/// any prefix, board, feature or history. Selection follows the published order.
fn checked_components(
    parent: &Value,
    selected: &Value,
    schedule: &Value,
    census: &Value,
    projection: &Value,
    wanted: usize,
) -> Result<EvaluationPlan> {
    let mut original = BTreeMap::new();
    let mut components: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let mut source_components = BTreeMap::new();
    for a in array(&parent["partition"], "assignments")? {
        let id = text(a, "game")?.to_string();
        let family = text(a, "family")?.to_string();
        let source = parent["source_series"][&id]
            .as_str()
            .ok_or("parent source identity missing")?
            .to_string();
        require(
            original
                .insert(id.clone(), (family.clone(), source.clone()))
                .is_none(),
            "duplicate original member identity",
        )?;
        if let Some(previous) = source_components.insert(source, family.clone()) {
            require(
                previous == family,
                "source series crosses original components",
            )?;
        }
        components.entry(family).or_default().insert(id);
    }
    require(
        parent["source_series"].as_object().map(|v| v.len()) == Some(original.len()),
        "complete original source membership required",
    )?;
    let mut excluded_members = BTreeMap::new();
    let mut actual_counts = [BTreeSet::new(), BTreeSet::new(), BTreeSet::new()];
    for a in array(&selected["partition"], "assignments")? {
        let id = text(a, "game")?;
        let family = text(a, "family")?;
        let split = text(a, "split")?;
        let index = match split {
            "train" => 0,
            "validation" => 1,
            "test" => 2,
            _ => return Err("unknown protected selection split".into()),
        };
        let old = original
            .get(id)
            .ok_or("selected member absent from original")?;
        require(
            old.0 == family
                && selected["source_series"][id] == old.1
                && excluded_members
                    .insert(id.to_string(), split.to_string())
                    .is_none(),
            "selected member/source/family mismatch",
        )?;
        actual_counts[index].insert(family.to_string());
    }
    require(
        selected["actual"]
            == json!({"train":actual_counts[0].len(),
        "validation":actual_counts[1].len(),"test":actual_counts[2].len()}),
        "actual protected component split counts differ",
    )?;
    require(
        selected["source_series"].as_object().map(|v| v.len()) == Some(excluded_members.len()),
        "complete protected source membership required",
    )?;
    let records = array(projection, "records")?;
    let native = array(census, "records")?;
    let ranked = array(schedule, "ranked_components")?;
    require(
        records.len() == native.len()
            && records.len() == ranked.len()
            && records.len() == components.len(),
        "complete published rank census required",
    )?;
    let mut seen_components = BTreeSet::new();
    let mut seen_members = BTreeSet::new();
    let mut members = Vec::new();
    let mut excluded = 0;
    let mut protected_h = 0;
    let mut eligible = 0;
    let mut disposition_counts = [0usize; 4];
    for (rank, ((row, old), identity)) in records.iter().zip(native).zip(ranked).enumerate() {
        let fields = row.as_array().ok_or("ranked disposition row required")?;
        require(
            fields.len() == 8
                && fields[..6] == old.as_array().ok_or("native census row")?[..]
                && fields[0].as_u64() == Some(rank as u64)
                && fields[1] == *identity,
            "published rank/census row differs",
        )?;
        let family = fields[1].as_str().ok_or("component identity required")?;
        let actual = components
            .get(family)
            .ok_or("component absent from parent")?;
        let ids: Vec<String> = serde_json::from_value(fields[2].clone())?;
        let sources: Vec<String> = serde_json::from_value(fields[3].clone())?;
        let actual_sources = actual
            .iter()
            .map(|id| original[id].1.clone())
            .collect::<BTreeSet<_>>();
        require(
            seen_components.insert(family.to_string())
                && ids.len() == actual.len()
                && ids.iter().cloned().collect::<BTreeSet<_>>() == *actual
                && sources.len() == actual_sources.len()
                && sources.iter().cloned().collect::<BTreeSet<_>>() == actual_sources
                && ids.iter().all(|id| seen_members.insert(id.clone()))
                && fields[4] == "eligible_named_scope",
            "whole member/source identity differs",
        )?;
        let splits = ids
            .iter()
            .filter_map(|id| excluded_members.get(id))
            .collect::<BTreeSet<_>>();
        let selected_count = ids
            .iter()
            .filter(|id| excluded_members.contains_key(*id))
            .count();
        if selected_count != 0 {
            require(
                selected_count == ids.len() && splits.len() == 1,
                "partial or cross-split protected component",
            )?;
            let split = *splits.iter().next().ok_or("selected split missing")?;
            let (index, disposition) = match split.as_str() {
                "train" => (0, "EXCLUDED_TRAIN1024"),
                "validation" => (1, "EXCLUDED_SELECTION_V256"),
                "test" => (2, "PROTECTED_H128"),
                _ => return Err("unsupported protected split".into()),
            };
            require(
                fields[5] == split.as_str()
                    && fields[6] == split.as_str()
                    && fields[7] == disposition,
                "protected1408 disposition mismatch",
            )?;
            disposition_counts[index] += 1;
            protected_h += usize::from(index == 2);
            excluded += 1;
        } else {
            require(
                fields[5].is_null()
                    && fields[6].is_null()
                    && fields[7] == "NOT_SELECTED1408_ELIGIBILITY_NOT_CLAIMED",
                "unselected component disposition mismatch",
            )?;
            disposition_counts[3] += 1;
            eligible += 1;
            if members.len() < wanted {
                require(
                    ids.len() == 1 && sources.len() == 1,
                    "selected evaluation component is multimember; no representative clipping",
                )?;
                members.push((rank, family.to_string(), ids[0].clone(), sources[0].clone()));
            }
        }
    }
    require(
        seen_members.len() == original.len()
            && projection["counts"]
                == json!({
            "EXCLUDED_TRAIN1024":disposition_counts[0],"EXCLUDED_SELECTION_V256":disposition_counts[1],
            "PROTECTED_H128":disposition_counts[2],
            "NOT_SELECTED1408_ELIGIBILITY_NOT_CLAIMED":disposition_counts[3]}),
        "complete member/disposition counts differ",
    )?;
    if members.len() != wanted {
        return Err(format!(
            "evaluation component deficit {}: eligible {eligible}, requested {wanted}",
            wanted.saturating_sub(members.len())
        )
        .into());
    }
    Ok(EvaluationPlan {
        members,
        parent_components: components.len(),
        excluded,
        protected_h,
        eligible,
    })
}

/// Metadata of all rows is checked first. Excluded roots/prefixes are not
/// deserialized as InputObservation and never reach ContextRecord::audit.
fn evaluation_rows(
    source: &Value,
    parent: &Value,
    schedule: &Value,
    plan: &EvaluationPlan,
) -> Result<(Vec<crate::value_search_strength::Family>, Vec<Value>)> {
    let mut expected = BTreeMap::new();
    for a in array(&parent["partition"], "assignments")? {
        let id = text(a, "game")?;
        require(
            expected.insert(id, a).is_none(),
            "duplicate parent observation",
        )?;
    }
    let mut rows = BTreeMap::new();
    for row in array(source, "observations")? {
        let id = text(row, "id")?;
        let old = expected.get(id).ok_or("source member absent from parent")?;
        require(
            row["family"] == old["family"]
                && row["split"] == old["split"]
                && row["source_series"] == parent["source_series"][id]
                && rows.insert(id, row).is_none(),
            "source observation identity differs",
        )?;
    }
    require(
        rows.len() == expected.len(),
        "source observation census incomplete",
    )?;
    let mut series = BTreeMap::new();
    for row in array(schedule, "series")? {
        require(
            series.insert(text(row, "id")?, row).is_none(),
            "duplicate source series",
        )?;
    }
    let mut families = Vec::new();
    let mut mapping = Vec::new();
    let mut planned = Vec::new();
    for (family_id, (rank, component, id, source_id)) in plan.members.iter().enumerate() {
        let value = rows
            .get(id.as_str())
            .ok_or("selected source observation missing")?;
        let old = expected[id.as_str()];
        let row: InputObservation = serde_json::from_value((*value).clone())?;
        let series_row = series
            .get(source_id.as_str())
            .ok_or("source series missing")?;
        let original_seed = series_row["seed"].as_u64().ok_or("source seed required")?;
        require(
            series_row["source_attempts"] == 1
                && row.prefix == serde_json::from_value::<Vec<u16>>(old["prefix"].clone())?
                && row.canonical_prefix == super::canonical_prefix(&row.prefix)?,
            "evaluation original prefix/canonical/attempt identity differs",
        )?;
        let context = row.root.audit(&row.prefix)?;
        require(
            context.terminal_value().is_none()
                && wall_layer(row.root.stocks) == 1
                && row.prefix.len() <= usize::from(PLY_CAP),
            "evaluation requires original nonterminal midstock context",
        )?;
        planned.push((row.id.clone(), row.prefix.clone()));
        families.push(crate::value_search_strength::Family {
            family_id,
            id: row.id,
            attempt_id: 0,
            seed: original_seed,
            prefix: row.prefix,
            root_key: row.root.state_key,
            history_counts: row.root.history,
        });
        mapping.push(
            json!({"family_id":family_id,"native_rank":rank,"component":component,
            "observation":id,"source_series":source_id,"source_seed":original_seed}),
        );
    }
    // Reuse native exact/LR endpoint/full-prefix component ownership for selected
    // evaluation roots only. Its internal split values are not published or used.
    let checked = partition_families(&planned, 0)?;
    require(
        checked
            .assignments
            .iter()
            .map(|a| &a.family)
            .collect::<BTreeSet<_>>()
            .len()
            == families.len()
            && checked
                .assignments
                .iter()
                .zip(&plan.members)
                .all(|(a, member)| a.family == member.1),
        "selected evaluation roots merge or differ from qualified native component identity",
    )?;
    Ok((families, mapping))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture(excluded: [usize; 3]) -> (Value, Value, Value, Value, Value, Value) {
        let count: usize = excluded.iter().sum();
        let mut assignments = Vec::<Value>::new();
        let mut selected_assignments = Vec::<Value>::new();
        let mut sources = serde_json::Map::new();
        let mut selected_sources = serde_json::Map::new();
        let mut rows = Vec::<Value>::new();
        let mut records = Vec::<Value>::new();
        let mut native = Vec::<Value>::new();
        let mut ranked = Vec::<Value>::new();
        let mut series = Vec::<Value>::new();
        for i in 0..count + 2 {
            let id = format!("observation-{i:04}");
            let family = format!("component-{i:04}");
            let source = format!("source-{i:04}");
            let split = if i < excluded[0] {
                Some("train")
            } else if i < excluded[0] + excluded[1] {
                Some("validation")
            } else if i < count {
                Some("test")
            } else {
                None
            };
            let disposition = match split {
                Some("train") => "EXCLUDED_TRAIN1024",
                Some("validation") => "EXCLUDED_SELECTION_V256",
                Some("test") => "PROTECTED_H128",
                _ => "NOT_SELECTED1408_ELIGIBILITY_NOT_CLAIMED",
            };
            // Invalid opaque protected geometry/history must never enter the
            // typed native decoder. Only the two evaluation views are genuine.
            let (prefix, canonical, root) = if i < count {
                (
                    json!("protected prefix is not interpreted"),
                    Value::Null,
                    json!("protected ContextRecord decoder must not run"),
                )
            } else {
                (Value::Null, Value::Null, Value::Null)
            };
            assignments.push(json!({"game":id,"family":family,"split":"train","prefix":prefix}));
            sources.insert(id.clone(), json!(source));
            if let Some(split) = split {
                selected_assignments.push(json!({"game":id,"family":family,"split":split,
                    "prefix":"protected selected prefix is not interpreted"}));
                selected_sources.insert(id.clone(), json!(source));
            }
            rows.push(
                json!({"id":id,"family":family,"split":"train","source_series":source,
                "prefix":prefix,"canonical_prefix":canonical,"root":root}),
            );
            native.push(json!([
                i,
                family,
                [id],
                [source],
                "eligible_named_scope",
                split
            ]));
            records.push(json!([
                i,
                family,
                [id],
                [source],
                "eligible_named_scope",
                split,
                split,
                disposition
            ]));
            ranked.push(json!(family));
            series.push(json!({"id":source,"seed":i as u64,"source_attempts":1}));
        }
        let parent = json!({"partition":{"assignments":assignments},"source_series":sources});
        let selected = json!({"partition":{"assignments":selected_assignments},
            "source_series":selected_sources,
            "actual":{"train":excluded[0],"validation":excluded[1],"test":excluded[2]}});
        let schedule = json!({"ranked_components":ranked,"series":series});
        let census = json!({"records":native});
        let projection = json!({"records":records,"counts":{
            "EXCLUDED_TRAIN1024":excluded[0],"EXCLUDED_SELECTION_V256":excluded[1],
            "PROTECTED_H128":excluded[2],"NOT_SELECTED1408_ELIGIBILITY_NOT_CLAIMED":2}});
        let source = json!({"observations":rows});
        (parent, selected, schedule, census, projection, source)
    }

    #[test]
    fn protected1408_is_excluded_before_typed_context_decode() {
        let (mut parent, selected, mut schedule, mut census, mut projection, mut source) =
            fixture([1024, 256, 128]);
        let mut planned = Vec::new();
        for view in 0..2 {
            let mut context = SigmaContext::from_prefix(&[]).unwrap();
            let mut prefix = Vec::new();
            for _ in 0..10 {
                let before = context.position().walls_remaining;
                let mut walls = context
                    .legal_ids()
                    .into_iter()
                    .filter_map(|action| {
                        let child = context.play(action).ok()?;
                        (child.position().walls_remaining != before).then_some((action, child))
                    })
                    .collect::<Vec<_>>();
                walls.sort_by_key(|v| v.0);
                let (action, child) = if view == 0 {
                    walls.remove(0)
                } else {
                    walls.pop().unwrap()
                };
                prefix.push(action);
                context = child;
            }
            let index = 1408 + view;
            parent["partition"]["assignments"][index]["prefix"] = json!(prefix);
            source["observations"][index]["prefix"] = json!(prefix);
            source["observations"][index]["canonical_prefix"] =
                json!(super::super::canonical_prefix(&prefix).unwrap());
            source["observations"][index]["root"] = json!(ContextRecord::from_context(&context));
            planned.push((format!("observation-{index:04}"), prefix));
        }
        let native = partition_families(&planned, 0).unwrap();
        for (view, assignment) in native.assignments.iter().enumerate() {
            let index = 1408 + view;
            parent["partition"]["assignments"][index]["family"] = json!(assignment.family);
            source["observations"][index]["family"] = json!(assignment.family);
            projection["records"][index][1] = json!(assignment.family);
            census["records"][index][1] = json!(assignment.family);
            schedule["ranked_components"][index] = json!(assignment.family);
        }
        let plan =
            checked_components(&parent, &selected, &schedule, &census, &projection, 2).unwrap();
        assert_eq!(
            (
                plan.parent_components,
                plan.excluded,
                plan.protected_h,
                plan.eligible
            ),
            (1410, 1408, 128, 2)
        );
        let (families, mapping) = evaluation_rows(&source, &parent, &schedule, &plan).unwrap();
        assert_eq!(families.len(), 2);
        assert_eq!(mapping.len(), 2);
        assert_eq!(families[0].id, "observation-1408");
        assert_eq!(families[1].id, "observation-1409");
        assert_eq!((families[0].seed, families[1].seed), (1408, 1409));
        assert_eq!(families[0].attempt_id, 0);
        let keys = serde_json::to_value(&families[0])
            .unwrap()
            .as_object()
            .unwrap()
            .keys()
            .cloned()
            .collect::<BTreeSet<_>>();
        assert_eq!(
            keys,
            [
                "family_id",
                "id",
                "attempt_id",
                "seed",
                "prefix",
                "root_key",
                "history_counts"
            ]
            .into_iter()
            .map(str::to_string)
            .collect()
        );
        // No T/V/H split is invented for the evaluation projection.
        assert!(mapping.iter().all(|v| v.get("split").is_none()));
    }

    #[test]
    fn corrupt_rank_member_source_protection_multimember_and_deficit_refuse() {
        let fixture = fixture([2, 1, 1]);
        for case in 0..7 {
            let (mut parent, selected, schedule, mut census, mut projection, _source) =
                fixture.clone();
            match case {
                0 => projection["records"][0][0] = json!(99),
                1 => {
                    projection["records"][0][2] = json!(["unknown-member"]);
                    census["records"][0][2] = projection["records"][0][2].clone();
                }
                2 => {
                    projection["records"][0][3] = json!(["wrong-source"]);
                    census["records"][0][3] = projection["records"][0][3].clone();
                }
                3 => {
                    projection["records"][4][6] = json!("train");
                    projection["records"][4][7] = json!("EXCLUDED_TRAIN1024");
                }
                4 => {
                    let assignment = json!({"game":"extra-member","family":"component-0004",
                        "split":"train","prefix":"not decoded"});
                    parent["partition"]["assignments"]
                        .as_array_mut()
                        .unwrap()
                        .push(assignment);
                    parent["source_series"]["extra-member"] = json!("extra-source");
                    projection["records"][4][2] = json!(["observation-0004", "extra-member"]);
                    projection["records"][4][3] = json!(["source-0004", "extra-source"]);
                    census["records"][4][2] = projection["records"][4][2].clone();
                    census["records"][4][3] = projection["records"][4][3].clone();
                }
                5 => {
                    projection["records"].as_array_mut().unwrap().pop();
                }
                _ => {}
            }
            let wanted = if case == 6 { 3 } else { 2 };
            let error =
                checked_components(&parent, &selected, &schedule, &census, &projection, wanted)
                    .err()
                    .expect("corrupt authority must refuse before any publication")
                    .to_string();
            if case == 4 {
                assert!(error.contains("multimember"), "{error}");
            }
            if case == 6 {
                assert!(error.contains("deficit 1"), "{error}");
            }
        }
    }

    #[test]
    fn malformed_authority_refuses_before_output_creation() {
        use std::os::unix::fs::PermissionsExt;
        let root =
            std::env::temp_dir().join(format!("saved-evaluation-authority-{}", std::process::id()));
        std::fs::create_dir(&root).unwrap();
        let write = |name: &str, value: Value| {
            let b = write_input_json(&root, name, &value).unwrap();
            let metadata = std::fs::metadata(&b.path).unwrap();
            FileRef {
                path: b.path,
                sha256: b.sha256,
                bytes: metadata.len(),
                mode: format!("{:04o}", metadata.permissions().mode() & 0o777),
            }
        };
        let authority = write("authority.json", json!({"status":"UNKNOWN"}));
        let checked_dispositions = write("projection.json", json!({}));
        let c = EvaluationInputConfig {
            saved_evaluation: SavedEvaluationInput {
                authority,
                checked_dispositions,
                components: 128,
            },
            output: root.join("not-published"),
        };
        let request: InputPreparation =
            serde_json::from_value(serde_json::to_value(&c).unwrap()).unwrap();
        let error = prepare_input_request(&request).unwrap_err().to_string();
        assert!(error.contains("checked evaluation authority"), "{error}");
        assert!(!c.output.exists());
        for name in ["authority.json", "projection.json"] {
            std::fs::remove_file(root.join(name)).unwrap();
        }
        std::fs::remove_dir(root).unwrap();
    }
}
