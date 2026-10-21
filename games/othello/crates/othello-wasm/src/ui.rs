//! Rust owns the confirmed game and UI decisions. The host executes only typed
//! browser effects; asynchronous completions carry Rust-issued ownership tokens.

use othello_core::GameState;
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
enum Mode {
    Local,
    Ai,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct SavedGame {
    version: u8,
    game: String,
    mode: Mode,
    human_side: u8,
    state: GameState,
}

const SAVE_KEY: &str = "othello.game.v1";
const KEEP_SAVE: &str =
    "元の保存を保持しています。続きから再試行するか、新しい対局を選んでください。";

#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Token {
    generation: u32,
    request: u32,
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "camelCase", deny_unknown_fields)]
enum Action {
    New {
        mode: Mode,
        #[serde(rename = "humanSide")]
        human_side: u8,
    },
    Setup {
        mode: Mode,
        #[serde(rename = "humanSide")]
        human_side: u8,
    },
    Resume {},
    Confirm {
        token: Token,
        accepted: bool,
        error: Option<String>,
    },
    Loaded {
        token: Token,
        raw: Option<String>,
        error: Option<String>,
    },
    Written {
        token: Token,
        error: Option<String>,
    },
    Play {
        index: u32,
    },
    Pass {},
    RetryAi {},
    Cancel {},
    AiReply {
        token: Token,
        state: GameState,
        r#move: Option<u32>,
        error: Option<String>,
    },
    Save {},
    Dispose {},
}

#[derive(Serialize)]
#[serde(tag = "kind", rename_all = "camelCase")]
enum Effect {
    CancelWorker,
    Confirm {
        token: Token,
        message: &'static str,
    },
    ReadSave {
        token: Token,
        key: &'static str,
    },
    WriteSave {
        token: Token,
        key: &'static str,
        raw: String,
    },
    Think {
        token: Token,
        state: GameState,
    },
}

enum Confirmation {
    New(Mode, u8),
    Resume,
}

struct PendingConfirmation {
    token: Token,
    action: Confirmation,
    previous_preserve: bool,
    previous_paused: bool,
    previous_warning: Option<String>,
    previous_message: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct Cell {
    index: u32,
    stone: u8,
    legal: bool,
    enabled: bool,
    label: String,
    text: &'static str,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct View {
    generation: u32,
    has_game: bool,
    mode: Mode,
    human_side: u8,
    busy: bool,
    thinking: bool,
    error: String,
    save_message: String,
    notice: String,
    title: String,
    players: String,
    score: String,
    guide: String,
    cells: Vec<Cell>,
    pass_visible: bool,
    pass_disabled: bool,
    retry_ai_visible: bool,
    cancel_visible: bool,
    save_disabled: bool,
    focus_turn: bool,
    exit_warning: Option<String>,
}

#[derive(Serialize)]
struct Output {
    view: View,
    effects: Vec<Effect>,
}

#[derive(Default)]
pub struct Controller {
    game: Option<SavedGame>,
    generation: u32,
    request: u32,
    disposed: bool,
    preserve_save: bool,
    error: String,
    notice: String,
    save_message: String,
    draft_mode: Option<Mode>,
    draft_side: Option<u8>,
    confirmation: Option<PendingConfirmation>,
    reading: Option<Token>,
    writing: Option<Token>,
    ai: Option<(Token, GameState)>,
    paused: bool,
    exit_warning: Option<String>,
}

fn color(side: u8) -> &'static str {
    match side {
        1 => "黒",
        2 => "白",
        _ => "空き",
    }
}
fn coordinate(index: u32) -> String {
    format!("{}{}", (b'A' + (index % 8) as u8) as char, index / 8 + 1)
}

impl Controller {
    fn token(&mut self) -> Token {
        self.request = self
            .request
            .checked_add(1)
            .expect("UI request counter exhausted");
        Token {
            generation: self.generation,
            request: self.request,
        }
    }

    fn invalidate(&mut self, effects: &mut Vec<Effect>) {
        self.generation = self
            .generation
            .checked_add(1)
            .expect("UI generation exhausted");
        self.confirmation = None;
        self.reading = None;
        self.writing = None;
        self.ai = None;
        effects.push(Effect::CancelWorker);
    }

    fn busy(&self) -> bool {
        self.confirmation.is_some() || self.reading.is_some() || self.ai.is_some()
    }
    fn can_save(&self) -> bool {
        self.game.is_some() && !self.preserve_save && !self.busy() && !self.disposed
    }

    fn save(&mut self, effects: &mut Vec<Effect>) {
        if !self.can_save() {
            if self.preserve_save {
                self.exit_warning = Some(KEEP_SAVE.into());
                self.save_message = KEEP_SAVE.into();
            }
            return;
        }
        let raw = serde_json::to_string(self.game.as_ref().expect("confirmed game"))
            .expect("finite game JSON");
        let token = self.token();
        self.writing = Some(token);
        effects.push(Effect::WriteSave {
            token,
            key: SAVE_KEY,
            raw,
        });
    }

    fn human_turn(&self) -> bool {
        self.game
            .as_ref()
            .is_some_and(|g| g.mode == Mode::Local || g.state.to_move() == g.human_side)
    }

    fn think(&mut self, effects: &mut Vec<Effect>) {
        if self.disposed || self.busy() || self.paused || self.preserve_save || self.human_turn() {
            return;
        }
        let Some(game) = self.game.as_ref() else {
            return;
        };
        let status = game.state.status();
        if status.terminal {
            return;
        }
        if status.must_pass {
            let next = game.state.pass().expect("Rust required pass");
            self.commit_state(
                next,
                "簡易AIは合法手がないためパスしました。".into(),
                effects,
            );
        } else {
            let state = game.state.clone();
            let token = self.token();
            self.ai = Some((token, state.clone()));
            effects.push(Effect::Think { token, state });
        }
    }

    fn commit_state(&mut self, state: GameState, notice: String, effects: &mut Vec<Effect>) {
        self.invalidate(effects);
        self.game.as_mut().expect("confirmed game").state = state;
        self.notice = notice;
        self.error.clear();
        self.paused = false;
        self.save(effects);
        self.think(effects);
    }

    fn ask(&mut self, action: Confirmation, effects: &mut Vec<Effect>) {
        let previous_preserve = self.preserve_save;
        let previous_paused = self.paused;
        let previous_warning = self.exit_warning.clone();
        let previous_message = self.save_message.clone();
        self.invalidate(effects);
        self.preserve_save = true;
        self.exit_warning = Some(KEEP_SAVE.into());
        self.save_message = KEEP_SAVE.into();
        self.error.clear();
        let token = self.token();
        let message = match action {
            Confirmation::New(_, _) => "新しい対局を始め、Othelloの保存枠を置き換えますか？",
            Confirmation::Resume => "現在の対局を中断して、保存したOthelloを再開しますか？",
        };
        self.confirmation = Some(PendingConfirmation {
            token,
            action,
            previous_preserve,
            previous_paused,
            previous_warning,
            previous_message,
        });
        effects.push(Effect::Confirm { token, message });
    }

    fn apply(&mut self, action: Action, effects: &mut Vec<Effect>) -> Result<bool, String> {
        // A synchronous final save acknowledgement may arrive during dispose.
        if let Action::Written { token, error } = action {
            if self.writing == Some(token) {
                self.writing = None;
                self.exit_warning = error
                    .as_ref()
                    .map(|e| format!("Othelloを保存できませんでした。{e}"));
                self.save_message = self
                    .exit_warning
                    .clone()
                    .unwrap_or_else(|| "この端末に保存しました。".into());
            }
            return Ok(false);
        }
        if self.disposed {
            return Ok(false);
        }
        let mut focus = false;
        match action {
            Action::New { mode, human_side } => {
                if !matches!(human_side, 1 | 2) {
                    return Err("担当する色を確認できません。".into());
                }
                self.draft_mode = Some(mode);
                self.draft_side = Some(human_side);
                self.ask(Confirmation::New(mode, human_side), effects);
            }
            Action::Setup { mode, human_side } => {
                if !matches!(human_side, 1 | 2) {
                    return Err("担当する色を確認できません。".into());
                }
                self.draft_mode = Some(mode);
                self.draft_side = Some(human_side);
                self.invalidate(effects);
                self.paused = true;
                self.notice = "設定変更は新しい対局で反映します。対局を中断しました。".into();
            }
            Action::Resume {} => self.ask(Confirmation::Resume, effects),
            Action::Confirm {
                token,
                accepted,
                error,
            } => {
                if self.confirmation.as_ref().map(|p| p.token) != Some(token) {
                    return Ok(false);
                }
                let pending = self.confirmation.take().expect("owned confirmation");
                if !accepted || error.is_some() {
                    self.preserve_save = pending.previous_preserve;
                    self.exit_warning = pending.previous_warning;
                    self.save_message = pending.previous_message;
                    self.notice = "取り消しました。元の対局と保存を保持しています。".into();
                    self.paused = pending.previous_paused;
                    if let Some(error) = error {
                        return Err(error);
                    }
                    self.think(effects);
                } else {
                    match pending.action {
                        Confirmation::New(mode, human_side) => {
                            self.game = Some(SavedGame {
                                version: 1,
                                game: "othello".into(),
                                mode,
                                human_side,
                                state: GameState::new(),
                            });
                            self.preserve_save = false;
                            self.paused = false;
                            self.error.clear();
                            self.notice = "新しい対局です。黒から始めます。".into();
                            self.save(effects);
                            self.think(effects);
                            focus = true;
                        }
                        Confirmation::Resume => {
                            let token = self.token();
                            self.reading = Some(token);
                            effects.push(Effect::ReadSave {
                                token,
                                key: SAVE_KEY,
                            });
                        }
                    }
                }
            }
            Action::Loaded { token, raw, error } => {
                if self.reading != Some(token) {
                    return Ok(false);
                }
                self.reading = None;
                if let Some(error) = error {
                    return Err(error);
                }
                let raw = raw.ok_or("保存したOthelloの対局がありません。")?;
                let saved: SavedGame = serde_json::from_str(&raw)
                    .map_err(|_| "保存形式を確認できません。元の保存を保持しています。")?;
                if saved.version != 1
                    || saved.game != "othello"
                    || !matches!(saved.human_side, 1 | 2)
                {
                    return Err("保存のバージョン・対戦方式・担当する色を確認できません。".into());
                }
                // GameState deserialization already strictly validates every board field.
                self.draft_mode = Some(saved.mode);
                self.draft_side = Some(saved.human_side);
                self.game = Some(saved);
                self.preserve_save = false;
                self.paused = false;
                self.error.clear();
                self.notice = "保存した対局を再開しました。".into();
                self.save(effects);
                self.think(effects);
                focus = true;
            }
            Action::Play { index } => {
                if self.busy() || self.paused || !self.human_turn() || self.preserve_save {
                    return Ok(false);
                }
                let game = self.game.as_ref().ok_or("対局を選んでください。")?;
                let next = game.state.play(index).map_err(|e| e.to_string())?;
                self.commit_state(
                    next,
                    format!("{} に置きました。", coordinate(index)),
                    effects,
                );
                focus = true;
            }
            Action::Pass {} => {
                if self.busy() || self.paused || !self.human_turn() || self.preserve_save {
                    return Ok(false);
                }
                let game = self.game.as_ref().ok_or("対局を選んでください。")?;
                let next = game.state.pass().map_err(|e| e.to_string())?;
                let notice = format!(
                    "{}は合法手がないためパスしました。",
                    color(game.state.to_move())
                );
                self.commit_state(next, notice, effects);
                focus = true;
            }
            Action::AiReply {
                token,
                state,
                r#move,
                error,
            } => {
                if self.ai.as_ref().map(|p| p.0) != Some(token) {
                    return Ok(false);
                }
                let (_, expected) = self.ai.take().expect("owned worker");
                effects.push(Effect::CancelWorker);
                if state != expected || self.game.as_ref().map(|g| &g.state) != Some(&expected) {
                    return Err("AIの応答局面が一致しません。再試行できます。".into());
                }
                if let Some(error) = error {
                    return Err(error);
                }
                let index = r#move.ok_or("AIが手を返しませんでした。再試行できます。")?;
                let next = expected.play(index).map_err(|e| e.to_string())?;
                self.commit_state(
                    next,
                    format!("簡易AIが {} に置きました。", coordinate(index)),
                    effects,
                );
                focus = true;
            }
            Action::RetryAi {} => {
                self.invalidate(effects);
                self.error.clear();
                self.paused = false;
                self.think(effects);
            }
            Action::Cancel {} => {
                self.invalidate(effects);
                self.paused = true;
                self.notice = "処理を中断しました。確認済みの局面を保持しています。".into();
            }
            Action::Save {} => self.save(effects),
            Action::Dispose {} => {
                let eligible = self.can_save() || (self.ai.is_some() && !self.preserve_save);
                self.invalidate(effects);
                if eligible {
                    self.save(effects);
                } else if self.preserve_save {
                    self.exit_warning = Some(KEEP_SAVE.into());
                }
                self.disposed = true;
            }
            Action::Written { .. } => unreachable!(),
        }
        Ok(focus)
    }

    fn view(&self, focus_turn: bool) -> View {
        let status = self.game.as_ref().map(|g| g.state.status());
        let busy = self.busy();
        let human = self.human_turn();
        let thinking = self.ai.is_some();
        let mode = self.draft_mode.unwrap_or(Mode::Local);
        let human_side = self.draft_side.unwrap_or(1);
        let mut view = View {
            generation: self.generation,
            has_game: self.game.is_some(),
            mode,
            human_side,
            busy,
            thinking,
            error: self.error.clone(),
            save_message: self.save_message.clone(),
            notice: self.notice.clone(),
            title: String::new(),
            players: String::new(),
            score: String::new(),
            guide: String::new(),
            cells: vec![],
            pass_visible: false,
            pass_disabled: true,
            retry_ai_visible: false,
            cancel_visible: thinking,
            save_disabled: !self.can_save(),
            focus_turn,
            exit_warning: self.exit_warning.clone(),
        };
        if let (Some(game), Some(status)) = (&self.game, status) {
            view.title = if status.terminal {
                status.winner.map_or_else(
                    || "終局：引分け".into(),
                    |w| format!("終局：{}の勝ち", color(w)),
                )
            } else {
                format!(
                    "{}の手番{}",
                    color(game.state.to_move()),
                    if thinking {
                        " · 簡易AIが考えています…"
                    } else {
                        ""
                    }
                )
            };
            view.players = if game.mode == Mode::Local {
                "ローカル2人 · 黒：人間 ／ 白：人間".into()
            } else {
                format!(
                    "簡易AI（非学習）と対戦 · 人間：{} ／ 簡易AI：{}",
                    color(game.human_side),
                    color(3 - game.human_side)
                )
            };
            view.score = format!("黒 {} 石 ／ 白 {} 石", status.black, status.white);
            view.guide = if status.terminal {
                "対局が終わりました。新しい対局を選べます。".into()
            } else if self.paused {
                "対局を中断しています。新しい対局・続きから・簡易AIの再試行を選べます。".into()
            } else if status.must_pass {
                format!(
                    "{}には合法手がありません。パスが必要です。",
                    color(game.state.to_move())
                )
            } else {
                "印のあるマスに置けます。Tabまたは矢印キーで移動し、Enter・Spaceで置きます。".into()
            };
            view.pass_visible = status.must_pass && human;
            view.pass_disabled = busy || self.paused || self.preserve_save;
            view.retry_ai_visible = !human && !status.terminal && !busy && !self.preserve_save;
            view.cells = game
                .state
                .board()
                .iter()
                .enumerate()
                .map(|(i, &stone)| {
                    let legal = status.legal_moves.contains(&(i as u32));
                    Cell {
                        index: i as u32,
                        stone,
                        legal,
                        enabled: legal && human && !busy && !self.paused && !self.preserve_save,
                        label: format!(
                            "{} {}{}",
                            coordinate(i as u32),
                            color(stone),
                            if legal { " 合法手" } else { "" }
                        ),
                        text: match stone {
                            1 => "●",
                            2 => "○",
                            _ => {
                                if legal {
                                    "·"
                                } else {
                                    ""
                                }
                            }
                        },
                    }
                })
                .collect();
        }
        view
    }

    pub fn dispatch(&mut self, input: &str) -> String {
        let mut effects = vec![];
        let result = serde_json::from_str::<Action>(input)
            .map_err(|_| "操作形式を確認できません。".to_string())
            .and_then(|action| self.apply(action, &mut effects));
        let focus = match result {
            Ok(focus) => focus,
            Err(error) => {
                if !self.disposed {
                    self.error = error;
                }
                false
            }
        };
        serde_json::to_string(&Output {
            view: self.view(focus),
            effects,
        })
        .expect("finite UI JSON")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::{Value, json};

    fn send(ui: &mut Controller, action: Value) -> Value {
        serde_json::from_str(&ui.dispatch(&action.to_string())).unwrap()
    }
    fn effect(output: &Value, kind: &str) -> Value {
        output["effects"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| e["kind"] == kind)
            .cloned()
            .unwrap()
    }
    fn has(output: &Value, kind: &str) -> bool {
        output["effects"]
            .as_array()
            .unwrap()
            .iter()
            .any(|e| e["kind"] == kind)
    }
    fn start(ui: &mut Controller, mode: &str, side: u8) -> Value {
        let asking = send(ui, json!({"kind":"new","mode":mode,"humanSide":side}));
        assert!(!has(&asking, "writeSave"));
        send(
            ui,
            json!({"kind":"confirm","token":effect(&asking,"confirm")["token"],"accepted":true}),
        )
    }
    fn resume(ui: &mut Controller) -> Value {
        let asking = send(ui, json!({"kind":"resume"}));
        let reading = send(
            ui,
            json!({"kind":"confirm","token":effect(&asking,"confirm")["token"],"accepted":true}),
        );
        effect(&reading, "readSave")["token"].clone()
    }
    fn saved(board: Vec<u8>, side: u8, mode: &str, human: u8) -> String {
        json!({"version":1,"game":"othello","mode":mode,"humanSide":human,"state":{"version":1,"board":board,"toMove":side}}).to_string()
    }

    #[test]
    fn ui_new_confirmation_and_local_move_are_rust_confirmed() {
        let mut ui = Controller::default();
        assert!(!has(&send(&mut ui, json!({"kind":"save"})), "writeSave"));
        let initial = start(&mut ui, "local", 1);
        assert_eq!(effect(&initial, "writeSave")["key"], SAVE_KEY);
        assert_eq!(initial["view"]["cells"][19]["enabled"], true);
        let before = ui.game.as_ref().unwrap().state.clone();
        let illegal = send(&mut ui, json!({"kind":"play","index":0}));
        assert!(!has(&illegal, "writeSave"));
        assert_eq!(ui.game.as_ref().unwrap().state, before);
        let moved = send(&mut ui, json!({"kind":"play","index":19}));
        assert_eq!(moved["view"]["score"], "黒 4 石 ／ 白 1 石");
        let saved: SavedGame =
            serde_json::from_str(effect(&moved, "writeSave")["raw"].as_str().unwrap()).unwrap();
        assert_eq!(saved.state, before.play(19).unwrap());
    }

    #[test]
    fn ui_stale_confirmation_and_cancel_keep_original_state_and_slot() {
        let mut ui = Controller::default();
        start(&mut ui, "local", 1);
        let old = send(&mut ui, json!({"kind":"new","mode":"ai","humanSide":2}));
        let current = send(&mut ui, json!({"kind":"new","mode":"local","humanSide":1}));
        let stale = send(
            &mut ui,
            json!({"kind":"confirm","token":effect(&old,"confirm")["token"],"accepted":true}),
        );
        assert!(!has(&stale, "think") && !has(&stale, "writeSave"));
        let cancelled = send(
            &mut ui,
            json!({"kind":"confirm","token":effect(&current,"confirm")["token"],"accepted":false}),
        );
        assert!(!has(&cancelled, "writeSave"));
        assert_eq!(ui.game.as_ref().unwrap().mode, Mode::Local);
    }

    #[test]
    fn ui_corrupt_pending_and_failed_resume_never_overwrite_saved_bytes() {
        for bad in [
            "{bad".to_string(),
            json!({"version":2}).to_string(),
            saved(vec![9; 64], 1, "local", 1),
            saved(vec![0; 64], 1, "learned", 1),
            saved(vec![0; 64], 1, "local", 0),
        ] {
            let mut ui = Controller::default();
            start(&mut ui, "local", 1);
            let old = ui.game.as_ref().unwrap().state.clone();
            let token = resume(&mut ui);
            let pending = send(&mut ui, json!({"kind":"save"}));
            assert!(!has(&pending, "writeSave"));
            let failed = send(
                &mut ui,
                json!({"kind":"loaded","token":token,"raw":bad,"error":null}),
            );
            assert!(!has(&failed, "writeSave"));
            assert_eq!(ui.game.as_ref().unwrap().state, old);
            let stopped = send(&mut ui, json!({"kind":"dispose"}));
            assert!(!has(&stopped, "writeSave"));
            assert!(
                stopped["view"]["exitWarning"]
                    .as_str()
                    .unwrap()
                    .contains("保持")
            );
            assert!(!has(
                &send(
                    &mut ui,
                    json!({"kind":"loaded","token":token,"raw":null,"error":"late"})
                ),
                "writeSave"
            ));
        }
        let mut ui = Controller::default();
        start(&mut ui, "local", 1);
        let token = resume(&mut ui);
        assert!(!has(&send(&mut ui, json!({"kind":"dispose"})), "writeSave"));
        assert!(!has(
            &send(
                &mut ui,
                json!({"kind":"loaded","token":token,"raw":saved(vec![0;64],1,"local",1),"error":null})
            ),
            "writeSave"
        ));
    }

    #[test]
    fn ui_validated_resume_required_pass_and_terminal_use_core_rules() {
        let mut ui = Controller::default();
        let token = resume(&mut ui);
        let mut board = vec![0; 64];
        board[0] = 1;
        board[1] = 2;
        let loaded = send(
            &mut ui,
            json!({"kind":"loaded","token":token,"raw":saved(board,2,"local",1),"error":null}),
        );
        assert_eq!(loaded["view"]["passVisible"], true);
        assert!(!has(
            &send(&mut ui, json!({"kind":"play","index":2})),
            "writeSave"
        ));
        let passed = send(&mut ui, json!({"kind":"pass"}));
        assert_eq!(passed["view"]["passVisible"], false);
        let ended = send(&mut ui, json!({"kind":"play","index":2}));
        assert_eq!(ended["view"]["title"], "終局：黒の勝ち");
        assert!(!has(&send(&mut ui, json!({"kind":"pass"})), "writeSave"));
        let mut ui = Controller::default();
        let token = resume(&mut ui);
        let ended = send(
            &mut ui,
            json!({"kind":"loaded","token":token,"raw":saved(vec![0;64],1,"local",1),"error":null}),
        );
        assert_eq!(ended["view"]["title"], "終局：引分け");
    }

    #[test]
    fn ui_worker_requires_rust_token_and_original_board_and_ignores_replay() {
        let mut ui = Controller::default();
        let started = start(&mut ui, "ai", 2);
        let request = effect(&started, "think");
        assert!(!has(
            &send(&mut ui, json!({"kind":"play","index":19})),
            "writeSave"
        ));
        let original = ui.game.as_ref().unwrap().state.clone();
        let mut stale = request["token"].clone();
        stale["request"] = json!(999);
        assert!(!has(
            &send(
                &mut ui,
                json!({"kind":"aiReply","token":stale,"state":request["state"],"move":19,"error":null})
            ),
            "writeSave"
        ));
        let valid = json!({"kind":"aiReply","token":request["token"],"state":request["state"],"move":19,"error":null});
        let applied = send(&mut ui, valid.clone());
        assert!(has(&applied, "writeSave"));
        assert_eq!(ui.game.as_ref().unwrap().state, original.play(19).unwrap());
        assert!(!has(&send(&mut ui, valid), "writeSave"));
        let mut ui = Controller::default();
        let req = effect(&start(&mut ui, "ai", 2), "think");
        let wrong = GameState::new().play(19).unwrap();
        let failed = send(
            &mut ui,
            json!({"kind":"aiReply","token":req["token"],"state":wrong,"move":18,"error":null}),
        );
        assert!(!has(&failed, "writeSave"));
        assert_eq!(failed["view"]["retryAiVisible"], true);
        assert_eq!(ui.game.as_ref().unwrap().state, GameState::new());
    }

    #[test]
    fn ui_setup_new_cancel_and_dispose_synchronously_revoke_workers() {
        for kind in ["setup", "cancel", "new", "dispose"] {
            let mut ui = Controller::default();
            let req = effect(&start(&mut ui, "ai", 2), "think");
            let action = if matches!(kind, "setup" | "new") {
                json!({"kind":kind,"mode":"local","humanSide":1})
            } else {
                json!({"kind":kind})
            };
            let revoked = send(&mut ui, action);
            assert!(has(&revoked, "cancelWorker"));
            assert!(revoked["view"]["generation"].as_u64() > req["token"]["generation"].as_u64());
            let stale = send(
                &mut ui,
                json!({"kind":"aiReply","token":req["token"],"state":req["state"],"move":19,"error":null}),
            );
            assert!(!has(&stale, "writeSave"));
            assert_eq!(ui.game.as_ref().unwrap().state, GameState::new());
        }
    }

    #[test]
    fn ui_ai_error_retry_and_required_pass_do_not_fake_a_human_move() {
        let mut ui = Controller::default();
        let req = effect(&start(&mut ui, "ai", 2), "think");
        let failed = send(
            &mut ui,
            json!({"kind":"aiReply","token":req["token"],"state":req["state"],"move":null,"error":"worker failed"}),
        );
        assert_eq!(failed["view"]["retryAiVisible"], true);
        assert!(!has(&failed, "writeSave"));
        let retried = send(&mut ui, json!({"kind":"retryAi"}));
        assert!(has(&retried, "think"));
        assert_ne!(effect(&retried, "think")["token"], req["token"]);
        let mut ui = Controller::default();
        let token = resume(&mut ui);
        let mut board = vec![0; 64];
        board[0] = 1;
        board[1] = 2;
        let passed = send(
            &mut ui,
            json!({"kind":"loaded","token":token,"raw":saved(board,2,"ai",1),"error":null}),
        );
        assert!(!has(&passed, "think"));
        assert_eq!(ui.game.as_ref().unwrap().state.to_move(), 1);
        assert!(passed["view"]["notice"].as_str().unwrap().contains("パス"));
    }

    #[test]
    fn ui_save_failure_and_explicit_new_after_bad_resume_keep_honest_eligibility() {
        let mut ui = Controller::default();
        let initial = start(&mut ui, "local", 1);
        let failed = send(
            &mut ui,
            json!({"kind":"written","token":effect(&initial,"writeSave")["token"],"error":"quota"}),
        );
        assert!(
            failed["view"]["exitWarning"]
                .as_str()
                .unwrap()
                .contains("quota")
        );
        let token = resume(&mut ui);
        send(
            &mut ui,
            json!({"kind":"loaded","token":token,"raw":null,"error":"denied"}),
        );
        assert!(!has(&send(&mut ui, json!({"kind":"save"})), "writeSave"));
        let replaced = start(&mut ui, "local", 1);
        assert!(has(&replaced, "writeSave"));
        let confirmed = send(
            &mut ui,
            json!({"kind":"written","token":effect(&replaced,"writeSave")["token"],"error":null}),
        );
        assert_eq!(confirmed["view"]["exitWarning"], Value::Null);
    }
}
