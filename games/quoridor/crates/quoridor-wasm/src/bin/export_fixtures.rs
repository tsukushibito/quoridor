use quoridor_core::Game;
use quoridor_wasm::wire::GameViewDto;
use serde::Serialize;

#[derive(Serialize)]
struct Fixture {
    name: &'static str,
    actions: Vec<u16>,
    view: GameViewDto,
}
fn capture(name: &'static str, game: &mut Game) -> Fixture {
    Fixture {
        name,
        actions: game.history().to_vec(),
        view: game.view().into(),
    }
}
fn main() {
    let mut game = Game::new();
    let mut fixtures = vec![capture("initial", &mut game)];
    for action in [13, 67, 81, 66, 14, 65] {
        game.apply_action(action).expect("fixed legal fixture");
    }
    fixtures.push(capture("opening", &mut game));
    let mut seed = 0x17b9_1a83_u64;
    for _ in 0..22 {
        let view = game.view();
        if view.winner.is_some() {
            break;
        }
        let actions: Vec<_> = view
            .legal_mask
            .iter()
            .enumerate()
            .filter_map(|(id, &legal)| (legal == 1).then_some(id as u16))
            .collect();
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        game.apply_action(actions[(seed as usize) % actions.len()])
            .expect("generated legal fixture");
    }
    fixtures.push(capture("midgame", &mut game));
    println!(
        "{}",
        serde_json::to_string_pretty(&fixtures).expect("fixed fixture serialization")
    );
}
