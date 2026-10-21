#![cfg(feature = "research")]
use quoridor_core::research::SigmaContext;

#[test]
fn make_unmake_preserves_whole_context_for_every_legal_child() {
    let mut context = SigmaContext::from_prefix(&[13, 67, 81, 146]).unwrap();
    let position = context.position();
    let history = context.history_counts();
    let ply = context.total_ply();
    for id in context.legal_ids() {
        let expected = context.play(id).unwrap();
        let undo = context.make_move(id).unwrap();
        assert_eq!(context.position(), expected.position());
        assert_eq!(context.history_counts(), expected.history_counts());
        context.unmake_move(undo).unwrap();
        assert_eq!(context.position(), position);
        assert_eq!(context.history_counts(), history);
        assert_eq!(context.total_ply(), ply);
    }
}

#[test]
fn out_of_order_undo_is_rejected_without_mutation() {
    let mut c = SigmaContext::from_prefix(&[]).unwrap();
    let first = c.make_move(13).unwrap();
    let second = c.make_move(67).unwrap();
    let position = c.position();
    assert!(c.unmake_move(first).is_err());
    assert_eq!(c.position(), position);
    c.unmake_move(second).unwrap();
    assert_eq!(c.total_ply(), 1);
}
