use quoridor_runner::config::Config;
fn config() -> Config {
    serde_json::from_value(serde_json::json!({"run_id":"test","output":"out","games":2,"workers":1,"engines":[{"kind":"distance","depth":1}]})).unwrap()
}
#[test]
fn rejects_unknown_keys_limits_and_missing_backend() {
    assert!(config().validate().is_ok());
    assert!(serde_json::from_value::<Config>(serde_json::json!({"run_id":"test","output":"out","engines":[{"kind":"distance"}],"unknown":true})).is_err());
    let mut c = config();
    c.max_batch = 0;
    assert!(c.validate().is_err());
    c.max_batch = 8;
    c.engines[0].kind = "mcts".into();
    assert!(c.validate().is_err());
}
#[test]
fn host_reserve_is_not_overridden_by_explicit_memory() {
    let a = quoridor_runner::resources::admit(1, &[], false, 0, Some(u64::MAX)).unwrap();
    assert!(a.memory_limit <= a.memory_available);
    let b = quoridor_runner::resources::admit(1, &[65535], false, 0, None);
    assert!(b.is_err());
}

#[test]
fn paired_arena_counts_are_admitted_by_family_before_execution() {
    let mut c = config();
    c.engines.push(c.engines[0].clone());
    c.games = 8;
    assert_eq!(c.split_counts().unwrap(), (4, 2));
    assert!(c.validate().is_ok());
    c.train_games = Some(5);
    assert!(c.validate().unwrap_err().contains("color pairs"));
    c.train_games = Some(4);
    c.validation_games = Some(1);
    assert!(c.validate().is_err());
    c.validation_games = Some(2);
    c.games = 7;
    assert!(c.validate().is_err());
    c.games = 8;
    c.train_games = Some(usize::MAX - 1);
    assert!(c.validate().is_err());
}
