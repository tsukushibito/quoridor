use quoridor_core::research::{SigmaContext, features};
fn main() {
    let mut context = SigmaContext::from_prefix(&[]).unwrap();
    let mut inputs = vec![features(context.position()).to_vec()];
    for i in 0..23 {
        let legal = context.legal_ids();
        let start = (i * 31 + 17) % legal.len();
        let next = (0..legal.len())
            .find_map(|n| {
                context
                    .play(legal[(start + n) % legal.len()])
                    .ok()
                    .filter(|p| p.terminal_value().is_none())
            })
            .unwrap();
        context = next;
        inputs.push(features(context.position()).to_vec());
    }
    println!("{}", serde_json::to_string(&inputs).unwrap());
}
