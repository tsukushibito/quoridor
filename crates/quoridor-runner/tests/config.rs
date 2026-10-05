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
