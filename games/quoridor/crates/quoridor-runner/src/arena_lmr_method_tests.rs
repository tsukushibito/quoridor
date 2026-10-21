//! Config/clock boundaries only; no replay, evaluator, Search or game.
use super::*;

#[test]
fn arena408_method_names_clocks_and_evaluator_mode_correspondence() {
    let (_, _, mut c, _, _) = super::generic_arena_361_tests::fixture(2, 64);
    c.arena.as_mut().unwrap().comparison = Comparison::WholeWallTime;
    c.arena.as_mut().unwrap().return_reserve_ms = 5;
    for (engine, method) in c.engines.iter_mut().zip(["fixed_one", "depth_rank"]) {
        engine.time_ms = Some(100);
        engine.ordering_profile = Some("control".into());
        engine.lmr = true;
        engine.lmr_method = Some(method.into());
    }
    assert!(c.arena.as_ref().unwrap().validate(&c).is_ok());
    let mut off = c.clone();
    off.engines[0].lmr = false;
    off.engines[0].lmr_method = Some("unknown".into());
    assert!(off.arena.as_ref().unwrap().validate(&off).is_err());
    c.arena.as_mut().unwrap().comparison = Comparison::EvaluatorWallTime;
    assert!(c.arena.as_ref().unwrap().validate(&c).is_err());
    c.engines[1].lmr_method = c.engines[0].lmr_method.clone();
    assert!(c.arena.as_ref().unwrap().validate(&c).is_ok());
    c.engines[1].time_ms = Some(101);
    assert!(c.arena.as_ref().unwrap().validate(&c).is_err());
    assert_eq!(c.arena.as_ref().unwrap().return_reserve_ms, 5);
}
