//! Rust owns the confirmed game and UI decisions. The host executes only typed
//! browser effects; asynchronous completions carry Rust-issued ownership tokens.

use othello_core::GameState;
use othello_core::full_search::{FullSearchOptions, MpcCoefficients};
use othello_core::search::{ScoreKind, SearchResult};
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
enum Mode {
    Local,
    Ai,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
enum Strategy {
    #[default]
    Simple,
    SearchV1,
    FullModel,
}

impl Strategy {
    fn label(self) -> &'static str {
        match self {
            Self::Simple => "簡易AI（非学習）",
            Self::SearchV1 => "探索AI（非学習・1秒）",
            Self::FullModel => "フル探索AI（評価ファイル使用・1秒）",
        }
    }
    fn short_label(self) -> &'static str {
        match self {
            Self::Simple => "簡易AI",
            Self::SearchV1 => "探索AI（1秒）",
            Self::FullModel => "フル探索AI（1秒）",
        }
    }
}

const MAIN_BYTES: u64 = 38_243_826;
const ENDING_BYTES: u64 = 472_392;
const MAIN_SHA: &str = "0a8acbcbc23067933627f1bcc83c3f7ae6b7ff3e603d174a3364271fcaeeef2f";
const ENDING_SHA: &str = "bd908885e8bb85e72a9be2b0399f8ca52ed40a138bcaaecca3d13710945b9a93";
const SELECT_MODEL: &str = "フル探索AIには、この端末の評価ファイル2点を選択・確認してください。";
const RESELECT_MODEL: &str =
    "フル探索AIには、この端末の評価ファイル2点を再選択してください。元の保存は保持しています。";

#[derive(Clone, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ModelIdentity {
    version: u8,
    main_sha256: String,
    ending_sha256: String,
}
fn fixed_identity() -> ModelIdentity {
    ModelIdentity {
        version: 1,
        main_sha256: MAIN_SHA.into(),
        ending_sha256: ENDING_SHA.into(),
    }
}
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct ModelSpec {
    identity: ModelIdentity,
    main_bytes: u64,
    ending_bytes: u64,
    interpretation: &'static str,
    hash_level: u8,
    ready_timeout_ms: u32,
    reply_timeout_ms: u32,
    options: FullSearchOptions,
}
fn model_spec() -> ModelSpec {
    ModelSpec {
        identity: fixed_identity(),
        main_bytes: MAIN_BYTES,
        ending_bytes: ENDING_BYTES,
        interpretation: "simd",
        hash_level: 20,
        ready_timeout_ms: 30_000,
        reply_timeout_ms: 1_100,
        options: FullSearchOptions::default(),
    }
}
#[derive(Clone, Copy, Deserialize)]
#[serde(rename_all = "camelCase")]
enum AiPhase {
    Initializing,
    Thinking,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct SavedGame {
    version: u8,
    game: String,
    mode: Mode,
    human_side: u8,
    // Version1 saves made before strategy selection deliberately mean Simple.
    #[serde(default)]
    strategy: Strategy,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    model_identity: Option<ModelIdentity>,
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
        strategy: Strategy,
    },
    Setup {
        mode: Mode,
        #[serde(rename = "humanSide")]
        human_side: u8,
        strategy: Strategy,
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
        state: serde_json::Value,
        strategy: Strategy,
        r#move: Option<u32>,
        #[serde(rename = "searchResult")]
        search_result: Option<serde_json::Value>,
        #[serde(rename = "fullResult")]
        full_result: Option<serde_json::Value>,
        #[serde(rename = "modelIdentity")]
        model_identity: Option<serde_json::Value>,
        error: Option<String>,
    },
    ModelFilesChanged {},
    LoadModel {},
    ModelReply {
        token: Token,
        identity: Option<ModelIdentity>,
        #[serde(rename = "mainBytes")]
        main_bytes: Option<u64>,
        #[serde(rename = "endingBytes")]
        ending_bytes: Option<u64>,
        error: Option<String>,
    },
    AiPhase {
        token: Token,
        phase: AiPhase,
        #[serde(rename = "modelIdentity")]
        model_identity: Option<ModelIdentity>,
    },
    Save {},
    Dispose {},
}

#[derive(Serialize)]
#[serde(tag = "kind", rename_all = "camelCase")]
enum Effect {
    CancelWorker,
    ResetModel,
    ForgetModel,
    LoadModel {
        token: Token,
        spec: ModelSpec,
    },
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
        strategy: Strategy,
        #[serde(skip_serializing_if = "Option::is_none")]
        model: Option<ModelSpec>,
    },
}

enum Confirmation {
    New(Mode, u8, Strategy),
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
    strategy: Strategy,
    busy: bool,
    thinking: bool,
    ai_phase: &'static str,
    model_required: bool,
    model_status: &'static str,
    model_message: String,
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
    draft_strategy: Option<Strategy>,
    confirmation: Option<PendingConfirmation>,
    reading: Option<Token>,
    writing: Option<Token>,
    ai: Option<(Token, GameState, Strategy)>,
    paused: bool,
    model_identity: Option<ModelIdentity>,
    model_loading: Option<Token>,
    model_block_save: bool,
    model_failed: bool,
    model_message: String,
    ai_model: Option<ModelIdentity>,
    ai_started: bool,
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

fn validate_search_result(
    strategy: Strategy,
    index: Option<u32>,
    raw: Option<serde_json::Value>,
) -> Result<(), String> {
    if strategy == Strategy::Simple {
        return if raw.is_none() {
            Ok(())
        } else {
            Err("簡易AIの応答に探索結果が混在しています。再試行できます。".into())
        };
    }
    let result: SearchResult =
        serde_json::from_value(raw.ok_or("探索結果がありません。再試行できます。")?)
            .map_err(|_| "探索結果の形式を確認できません。再試行できます。")?;
    if result.cancelled {
        return Err("探索が取り消されました。再試行できます。".into());
    }
    if result.r#move != index
        || !result.elapsed_ms.is_finite()
        || result.elapsed_ms < 0.0
        || result.completed_depth > 64
        || match result.score_kind {
            ScoreKind::Heuristic => result.proven,
            ScoreKind::DiscDifference => !result.proven || !(-64..=64).contains(&result.score),
        }
    {
        return Err("探索結果が一致しません。再試行できます。".into());
    }
    // timedOut is normal: the core returns the last completed iteration, or its
    // legal fallback. Score/depth/proof are diagnostics, not a UI strength claim.
    Ok(())
}

// Actual full-owner schema, kept distinct from baseline SearchResult.
#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct FullReply {
    r#move: Option<u32>,
    raw_score: Option<i32>,
    score: Option<i32>,
    score_units: String,
    score_kind: String,
    proven: bool,
    completed_depth: u8,
    selectivity: u8,
    probability: Option<f64>,
    is_end_search: bool,
    nodes: u64,
    elapsed_ms: f64,
    stopped: Option<String>,
    interpretation: String,
    tt_bytes: usize,
    coefficients: MpcCoefficients,
    must_pass: bool,
    terminal: bool,
}
fn validate_full_result(
    state: &GameState,
    index: Option<u32>,
    raw: Option<serde_json::Value>,
) -> Result<(), String> {
    let r: FullReply = serde_json::from_value(raw.ok_or("フル探索の結果がありません。")?)
        .map_err(|_| "フル探索の結果形式を確認できません。")?;
    let status = state.status();
    let defaults = MpcCoefficients::default();
    let got = [
        r.coefficients.a,
        r.coefficients.b,
        r.coefficients.c,
        r.coefficients.d,
        r.coefficients.e,
        r.coefficients.f,
        r.coefficients.g,
    ];
    let expected = [
        defaults.a, defaults.b, defaults.c, defaults.d, defaults.e, defaults.f, defaults.g,
    ];
    let uncompleted = r.completed_depth == 0
        && r.raw_score.is_none()
        && r.score.is_none()
        && r.score_kind == "uncompleted"
        && !r.proven
        && !r.is_end_search
        && r.stopped.as_deref() == Some("timeout");
    let completed = r.completed_depth > 0
        && r.raw_score.is_some_and(|v| (-64..=64).contains(&v))
        && r.score.is_some_and(|v| (-64..=64).contains(&v))
        && if r.proven {
            r.is_end_search && r.selectivity == 6 && r.score_kind == "terminalEmptyAward"
        } else {
            r.score_kind == "heuristic"
        };
    if r.r#move != index
        || r.score_units != "engine-disc"
        || r.interpretation != "simd"
        || r.completed_depth > 60
        || r.selectivity > 6
        || r.tt_bytes == 0
        || r.tt_bytes > 32 * 1024 * 1024
        || !r.elapsed_ms.is_finite()
        || r.elapsed_ms < 0.0
        || r.probability
            .is_some_and(|p| !p.is_finite() || !(0.0..=100.0).contains(&p))
        || r.stopped.as_deref().is_some_and(|s| s != "timeout")
        || !got
            .iter()
            .zip(expected)
            .all(|(a, b)| a.to_bits() == b.to_bits())
        || r.must_pass != status.must_pass
        || r.terminal != status.terminal
        || !(uncompleted || completed)
    {
        return Err("フル探索の応答が一致しません。再試行できます。".into());
    }
    // Actual nodes/score kind/proof are retained as their own schema, not recast.
    let _ = r.nodes;
    Ok(())
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

    fn revoke_requests(&mut self) {
        self.generation = self
            .generation
            .checked_add(1)
            .expect("UI generation exhausted");
        self.confirmation = None;
        self.reading = None;
        self.writing = None;
        self.ai = None;
        self.ai_model = None;
        self.ai_started = false;
        if self.model_loading.is_some() {
            self.model_message =
                "評価ファイルの準備を中断しました。もう一度確認・準備できます。".into();
        }
        self.model_loading = None;
    }
    fn invalidate(&mut self, effects: &mut Vec<Effect>) {
        self.revoke_requests();
        effects.push(Effect::CancelWorker);
    }
    fn advance(&mut self, effects: &mut Vec<Effect>) {
        if self
            .game
            .as_ref()
            .is_some_and(|g| g.strategy == Strategy::FullModel)
        {
            self.revoke_requests();
        } else {
            self.invalidate(effects);
        }
    }

    fn busy(&self) -> bool {
        self.confirmation.is_some()
            || self.reading.is_some()
            || self.ai.is_some()
            || self.model_loading.is_some()
    }
    fn can_save(&self) -> bool {
        self.game.is_some()
            && !self.preserve_save
            && !self.model_block_save
            && !self.busy()
            && !self.disposed
    }

    fn save(&mut self, effects: &mut Vec<Effect>) {
        if !self.can_save() {
            if self.preserve_save || self.model_block_save {
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
        if self.disposed
            || self.busy()
            || self.paused
            || self.preserve_save
            || self.model_block_save
            || self.human_turn()
        {
            return;
        }
        let Some(game) = self.game.as_ref() else {
            return;
        };
        if game.strategy == Strategy::FullModel
            && self.model_identity.as_ref() != game.model_identity.as_ref()
        {
            self.model_message = if self.model_block_save {
                RESELECT_MODEL
            } else {
                SELECT_MODEL
            }
            .into();
            return;
        }
        let status = game.state.status();
        if status.terminal {
            return;
        }
        if status.must_pass {
            let next = game.state.pass().expect("Rust required pass");
            let notice = format!(
                "{}は合法手がないためパスしました。",
                game.strategy.short_label()
            );
            self.commit_state(next, notice, effects);
        } else {
            let state = game.state.clone();
            let strategy = game.strategy;
            self.ai_model = if strategy == Strategy::FullModel {
                self.model_identity.clone()
            } else {
                None
            };
            self.ai_started = false;
            let token = self.token();
            self.ai = Some((token, state.clone(), strategy));
            effects.push(Effect::Think {
                token,
                state,
                strategy,
                model: (strategy == Strategy::FullModel).then(model_spec),
            });
        }
    }

    fn commit_state(&mut self, state: GameState, notice: String, effects: &mut Vec<Effect>) {
        self.advance(effects);
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
        let keep_idle = self.ai.is_none()
            && self.model_loading.is_none()
            && self.model_identity.is_some()
            && matches!(&action, Confirmation::New(Mode::Ai, _, Strategy::FullModel));
        if keep_idle {
            self.revoke_requests();
        } else {
            self.invalidate(effects);
        }
        self.preserve_save = true;
        self.exit_warning = Some(KEEP_SAVE.into());
        self.save_message = KEEP_SAVE.into();
        self.error.clear();
        let token = self.token();
        let message = match action {
            Confirmation::New(_, _, _) => "新しい対局を始め、Othelloの保存枠を置き換えますか？",
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
            Action::New {
                mode,
                human_side,
                strategy,
            } => {
                if !matches!(human_side, 1 | 2) {
                    return Err("担当する色を確認できません。".into());
                }
                // Local two-player games never require evaluation Files.
                let strategy = if mode == Mode::Local && strategy == Strategy::FullModel {
                    Strategy::Simple
                } else {
                    strategy
                };
                self.draft_mode = Some(mode);
                self.draft_side = Some(human_side);
                self.draft_strategy = Some(strategy);
                self.ask(Confirmation::New(mode, human_side, strategy), effects);
            }
            Action::Setup {
                mode,
                human_side,
                strategy,
            } => {
                if !matches!(human_side, 1 | 2) {
                    return Err("担当する色を確認できません。".into());
                }
                // Local two-player games never require evaluation Files.
                let strategy = if mode == Mode::Local && strategy == Strategy::FullModel {
                    Strategy::Simple
                } else {
                    strategy
                };
                self.draft_mode = Some(mode);
                self.draft_side = Some(human_side);
                self.draft_strategy = Some(strategy);
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
                        Confirmation::New(mode, human_side, strategy) => {
                            self.game = Some(SavedGame {
                                version: 1,
                                game: "othello".into(),
                                mode,
                                human_side,
                                strategy,
                                model_identity: (strategy == Strategy::FullModel)
                                    .then(fixed_identity),
                                state: GameState::new(),
                            });
                            self.preserve_save = false;
                            self.model_block_save = false;
                            if strategy == Strategy::FullModel {
                                if self.model_identity.is_none() {
                                    self.model_failed = false;
                                    self.model_message = SELECT_MODEL.into();
                                }
                                effects.push(Effect::ResetModel);
                            }
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
                    || (saved.mode == Mode::Local && saved.strategy == Strategy::FullModel)
                    || if saved.strategy == Strategy::FullModel {
                        saved.model_identity.as_ref() != Some(&fixed_identity())
                    } else {
                        saved.model_identity.is_some()
                    }
                {
                    return Err("保存のバージョン・対戦方式・担当する色を確認できません。".into());
                }
                // GameState deserialization already strictly validates every board field.
                self.draft_mode = Some(saved.mode);
                self.draft_side = Some(saved.human_side);
                self.draft_strategy = Some(saved.strategy);
                let needs_files = saved.strategy == Strategy::FullModel;
                self.game = Some(saved);
                self.preserve_save = false;
                self.model_block_save = needs_files;
                if needs_files {
                    self.model_identity = None;
                    self.model_failed = false;
                    self.model_message = RESELECT_MODEL.into();
                    effects.push(Effect::ForgetModel);
                }
                self.paused = false;
                self.error.clear();
                self.notice = "保存した対局を再開しました。".into();
                self.save(effects);
                self.think(effects);
                focus = true;
            }
            Action::Play { index } => {
                if self.busy()
                    || self.paused
                    || !self.human_turn()
                    || self.preserve_save
                    || self.model_block_save
                {
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
                if self.busy()
                    || self.paused
                    || !self.human_turn()
                    || self.preserve_save
                    || self.model_block_save
                {
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
                strategy,
                r#move,
                search_result,
                full_result,
                model_identity,
                error,
            } => {
                if self.ai.as_ref().map(|p| p.0) != Some(token) {
                    return Ok(false);
                }
                let (_, expected, expected_strategy) = self.ai.take().expect("owned worker");
                let expected_model = self.ai_model.take();
                self.ai_started = false;
                if expected_strategy != Strategy::FullModel {
                    effects.push(Effect::CancelWorker);
                }
                let parsed: Result<GameState, _> = serde_json::from_value(state);
                let state = match parsed {
                    Ok(state) => state,
                    Err(_) => {
                        effects.push(Effect::CancelWorker);
                        return Err("AIの応答局面の形式を確認できません。再試行できます。".into());
                    }
                };
                let parsed_identity: Result<Option<ModelIdentity>, _> =
                    model_identity.map(serde_json::from_value).transpose();
                let model_identity = match parsed_identity {
                    Ok(identity) => identity,
                    Err(_) => {
                        effects.push(Effect::CancelWorker);
                        return Err("AIの評価ファイル識別子の形式を確認できません。".into());
                    }
                };
                if strategy != expected_strategy
                    || state != expected
                    || self.game.as_ref().map(|g| (&g.state, g.strategy))
                        != Some((&expected, expected_strategy))
                {
                    effects.push(Effect::CancelWorker);
                    return Err("AIの応答局面・方式が一致しません。再試行できます。".into());
                }
                if let Some(error) = error {
                    effects.push(Effect::CancelWorker);
                    return Err(error);
                }
                let checked = if strategy == Strategy::FullModel {
                    if model_identity != expected_model
                        || model_identity != self.model_identity
                        || self.game.as_ref().and_then(|g| g.model_identity.as_ref())
                            != model_identity.as_ref()
                        || search_result.is_some()
                    {
                        Err("フル探索の評価ファイルidentityが一致しません。".into())
                    } else {
                        validate_full_result(&expected, r#move, full_result)
                    }
                } else if full_result.is_some() || model_identity.is_some() {
                    Err("AIの応答方式が混在しています。".into())
                } else {
                    validate_search_result(strategy, r#move, search_result)
                };
                if let Err(error) = checked {
                    effects.push(Effect::CancelWorker);
                    return Err(error);
                }
                let next = r#move
                    .ok_or("AIが手を返しませんでした。再試行できます。".to_string())
                    .and_then(|index| expected.play(index).map_err(|e| e.to_string()));
                let next = match next {
                    Ok(next) => next,
                    Err(error) => {
                        effects.push(Effect::CancelWorker);
                        return Err(error);
                    }
                };
                let index = r#move.expect("validated move");
                self.commit_state(
                    next,
                    format!(
                        "{}が {} に置きました。",
                        strategy.short_label(),
                        coordinate(index)
                    ),
                    effects,
                );
                focus = true;
            }
            Action::ModelFilesChanged {} => {
                self.invalidate(effects);
                self.model_identity = None;
                self.model_failed = false;
                self.model_block_save = self.game.is_some();
                self.model_message =
                    "評価ファイル2点を選び、「評価ファイルを確認・準備」を押してください。".into();
                self.error.clear();
            }
            Action::LoadModel {} => {
                self.invalidate(effects);
                self.model_identity = None;
                self.model_failed = false;
                self.model_block_save = self.game.is_some();
                self.model_message = "評価ファイルを確認・準備しています…".into();
                self.error.clear();
                let token = self.token();
                self.model_loading = Some(token);
                effects.push(Effect::LoadModel {
                    token,
                    spec: model_spec(),
                });
            }
            Action::ModelReply {
                token,
                identity,
                main_bytes,
                ending_bytes,
                error,
            } => {
                if self.model_loading != Some(token) {
                    return Ok(false);
                }
                self.model_loading = None;
                let error = error.or_else(|| {
                    (identity.as_ref() != Some(&fixed_identity())
                        || main_bytes != Some(MAIN_BYTES)
                        || ending_bytes != Some(ENDING_BYTES))
                    .then(|| "指定の評価ファイル2点を確認できません。".into())
                });
                if let Some(error) = error {
                    self.model_failed = true;
                    self.model_message = error.clone();
                    effects.push(Effect::CancelWorker);
                    return Err(error);
                }
                self.model_identity = identity;
                self.model_failed = false;
                self.model_block_save = false;
                self.model_message =
                    "この画面内で評価ファイルを選択済みです。フル探索は1手1秒です。".into();
                if self
                    .game
                    .as_ref()
                    .is_some_and(|g| g.strategy == Strategy::FullModel)
                {
                    self.save(effects);
                    self.think(effects);
                }
            }
            Action::AiPhase {
                token,
                phase,
                model_identity,
            } => {
                if self.ai.as_ref().map(|a| a.0) == Some(token)
                    && self.ai_model == model_identity
                    && model_identity.is_some()
                {
                    self.ai_started = matches!(phase, AiPhase::Thinking);
                }
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
                let eligible = self.can_save()
                    || (self.ai.is_some() && !self.preserve_save && !self.model_block_save);
                let had_model = self.model_identity.is_some() || self.model_loading.is_some();
                self.invalidate(effects);
                if had_model {
                    effects.push(Effect::ForgetModel);
                }
                self.model_identity = None;
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
        let strategy = self.draft_strategy.unwrap_or_default();
        let mut view = View {
            generation: self.generation,
            has_game: self.game.is_some(),
            mode,
            human_side,
            strategy,
            busy,
            thinking,
            ai_phase: if !thinking {
                "idle"
            } else if self.ai_model.is_some() && !self.ai_started {
                "initializing"
            } else {
                "thinking"
            },
            model_required: strategy == Strategy::FullModel
                || self
                    .game
                    .as_ref()
                    .is_some_and(|g| g.strategy == Strategy::FullModel),
            model_status: if self.model_loading.is_some() {
                "loading"
            } else if self.model_identity.is_some() {
                "ready"
            } else if self.model_failed {
                "error"
            } else {
                "unloaded"
            },
            model_message: if self.model_message.is_empty() {
                "ローカルの評価ファイル2点が必要です。".into()
            } else {
                self.model_message.clone()
            },
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
            cancel_visible: thinking || self.model_loading.is_some(),
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
                        if self.ai_model.is_some() && !self.ai_started {
                            " · 評価ファイルを準備しています…".into()
                        } else {
                            format!(" · {}が考えています…", game.strategy.short_label())
                        }
                    } else {
                        String::new()
                    }
                )
            };
            view.players = if game.mode == Mode::Local {
                "ローカル2人 · 黒：人間 ／ 白：人間".into()
            } else {
                format!(
                    "{}と対戦 · 人間：{} ／ {}：{}",
                    game.strategy.label(),
                    color(game.human_side),
                    game.strategy.short_label(),
                    color(3 - game.human_side)
                )
            };
            view.score = format!("黒 {} 石 ／ 白 {} 石", status.black, status.white);
            view.guide = if status.terminal {
                "対局が終わりました。新しい対局を選べます。".into()
            } else if game.strategy == Strategy::FullModel
                && (self.model_identity.is_none() || self.model_block_save)
            {
                if self.model_block_save {
                    RESELECT_MODEL
                } else {
                    SELECT_MODEL
                }
                .into()
            } else if self.paused {
                "対局を中断しています。新しい対局・続きから・AIの再試行を選べます。".into()
            } else if status.must_pass {
                format!(
                    "{}には合法手がありません。パスが必要です。",
                    color(game.state.to_move())
                )
            } else {
                "印のあるマスに置けます。Tabまたは矢印キーで移動し、Enter・Spaceで置きます。".into()
            };
            view.pass_visible = status.must_pass && human;
            view.pass_disabled = busy || self.paused || self.preserve_save || self.model_block_save;
            view.retry_ai_visible = !human
                && !status.terminal
                && !busy
                && !self.preserve_save
                && !self.model_block_save
                && (game.strategy != Strategy::FullModel || self.model_identity.is_some());
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
                        enabled: legal
                            && human
                            && !busy
                            && !self.paused
                            && !self.preserve_save
                            && !self.model_block_save,
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
        let asking = send(
            ui,
            json!({"kind":"new","strategy":"simple","mode":mode,"humanSide":side}),
        );
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
        let old = send(
            &mut ui,
            json!({"kind":"new","strategy":"simple","mode":"ai","humanSide":2}),
        );
        let current = send(
            &mut ui,
            json!({"kind":"new","strategy":"simple","mode":"local","humanSide":1}),
        );
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
                json!({"kind":"aiReply","strategy":"simple","token":stale,"state":request["state"],"move":19,"error":null})
            ),
            "writeSave"
        ));
        let valid = json!({"kind":"aiReply","strategy":"simple","token":request["token"],"state":request["state"],"move":19,"error":null});
        let applied = send(&mut ui, valid.clone());
        assert!(has(&applied, "writeSave"));
        assert_eq!(ui.game.as_ref().unwrap().state, original.play(19).unwrap());
        assert!(!has(&send(&mut ui, valid), "writeSave"));
        let mut ui = Controller::default();
        let req = effect(&start(&mut ui, "ai", 2), "think");
        let wrong = GameState::new().play(19).unwrap();
        let failed = send(
            &mut ui,
            json!({"kind":"aiReply","strategy":"simple","token":req["token"],"state":wrong,"move":18,"error":null}),
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
                json!({"kind":kind,"strategy":"simple","mode":"local","humanSide":1})
            } else {
                json!({"kind":kind})
            };
            let revoked = send(&mut ui, action);
            assert!(has(&revoked, "cancelWorker"));
            assert!(revoked["view"]["generation"].as_u64() > req["token"]["generation"].as_u64());
            let stale = send(
                &mut ui,
                json!({"kind":"aiReply","strategy":"simple","token":req["token"],"state":req["state"],"move":19,"error":null}),
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
            json!({"kind":"aiReply","strategy":"simple","token":req["token"],"state":req["state"],"move":null,"error":"worker failed"}),
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

    fn start_search(ui: &mut Controller) -> Value {
        let ask = send(
            ui,
            json!({"kind":"new","mode":"ai","humanSide":2,"strategy":"searchV1"}),
        );
        let started = send(
            ui,
            json!({"kind":"confirm","token":effect(&ask,"confirm")["token"],"accepted":true}),
        );
        assert!(
            started["view"]["players"]
                .as_str()
                .unwrap()
                .contains("探索AI（非学習・1秒）")
        );
        assert_eq!(effect(&started, "think")["strategy"], "searchV1");
        effect(&started, "think")
    }
    // Transport fixtures only. No actual search is executed by these UI units.
    fn search_reply(request: &Value) -> Value {
        json!({"kind":"aiReply","token":request["token"],"state":request["state"],"strategy":"searchV1","move":19,"error":null,
          "searchResult":{"move":19,"score":123,"scoreKind":"heuristic","completedDepth":2,"nodes":10,"elapsedMs":1000.2,"timedOut":true,"cancelled":false,"proven":false}})
    }

    #[test]
    fn ui_search_legacy_save_defaults_simple_and_explicit_strategy_persists() {
        let mut ui = Controller::default();
        let simple = start(&mut ui, "ai", 2);
        assert_eq!(effect(&simple, "think")["strategy"], "simple");
        let mut legacy: Value =
            serde_json::from_str(effect(&simple, "writeSave")["raw"].as_str().unwrap()).unwrap();
        assert_eq!(legacy["strategy"], "simple");
        legacy.as_object_mut().unwrap().remove("strategy");
        let token = resume(&mut ui);
        let loaded = send(
            &mut ui,
            json!({"kind":"loaded","token":token,"raw":legacy.to_string(),"error":null}),
        );
        assert_eq!(effect(&loaded, "think")["strategy"], "simple");
        legacy["strategy"] = json!("searchV1");
        let token = resume(&mut ui);
        let loaded = send(
            &mut ui,
            json!({"kind":"loaded","token":token,"raw":legacy.to_string(),"error":null}),
        );
        assert_eq!(effect(&loaded, "think")["strategy"], "searchV1");
        let saved: Value =
            serde_json::from_str(effect(&loaded, "writeSave")["raw"].as_str().unwrap()).unwrap();
        assert_eq!(saved["strategy"], "searchV1");
    }

    #[test]
    fn ui_search_completed_timeout_is_accepted_without_persisting_diagnostics() {
        let mut ui = Controller::default();
        let req = start_search(&mut ui);
        let moved = send(&mut ui, search_reply(&req));
        assert_eq!(moved["view"]["score"], "黒 4 石 ／ 白 1 石");
        assert!(moved["view"]["error"].as_str().unwrap().is_empty());
        let saved: Value =
            serde_json::from_str(effect(&moved, "writeSave")["raw"].as_str().unwrap()).unwrap();
        assert_eq!(saved["strategy"], "searchV1");
        assert!(saved.get("searchResult").is_none());
        assert!(!has(&send(&mut ui, search_reply(&req)), "writeSave"));
    }

    #[test]
    fn ui_search_bad_cancelled_and_illegal_results_offer_retry_without_save() {
        for case in 0..10 {
            let mut ui = Controller::default();
            let req = start_search(&mut ui);
            let mut reply = search_reply(&req);
            match case {
                0 => reply["searchResult"] = Value::Null,
                1 => reply["searchResult"] = json!({"bad":true}),
                2 => reply["searchResult"]["cancelled"] = json!(true),
                3 => reply["searchResult"]["move"] = json!(26),
                4 => reply["searchResult"]["proven"] = json!(true),
                5 => {
                    reply["searchResult"]["scoreKind"] = json!("discDifference");
                    reply["searchResult"]["proven"] = json!(true);
                    reply["searchResult"]["score"] = json!(65);
                }
                6 => reply["searchResult"]["elapsedMs"] = json!(-1),
                7 => reply["searchResult"]["completedDepth"] = json!(65),
                8 => {
                    reply["move"] = json!(0);
                    reply["searchResult"]["move"] = json!(0);
                }
                _ => reply["searchResult"]["scoreKind"] = json!("unknown"),
            }
            let failed = send(&mut ui, reply);
            assert!(!has(&failed, "writeSave"), "case {case}");
            assert_eq!(failed["view"]["retryAiVisible"], true, "case {case}");
            assert_eq!(ui.game.as_ref().unwrap().state, GameState::new());
            let retry = send(&mut ui, json!({"kind":"retryAi"}));
            assert_ne!(effect(&retry, "think")["token"], req["token"]);
        }
    }

    #[test]
    fn ui_search_strategy_and_board_identity_are_checked_by_rust() {
        let mut ui = Controller::default();
        let req = start_search(&mut ui);
        let mut stale = search_reply(&req);
        stale["token"]["request"] = json!(999);
        stale["strategy"] = json!("simple");
        assert_eq!(send(&mut ui, stale)["view"]["thinking"], true);
        let mut wrong = search_reply(&req);
        wrong["strategy"] = json!("simple");
        wrong["searchResult"] = Value::Null;
        let rejected = send(&mut ui, wrong);
        assert_eq!(rejected["view"]["retryAiVisible"], true);
        assert!(!has(&rejected, "writeSave"));
        let retry = effect(&send(&mut ui, json!({"kind":"retryAi"})), "think");
        let mut wrong = search_reply(&retry);
        wrong["state"] = serde_json::to_value(GameState::new().play(19).unwrap()).unwrap();
        assert!(!has(&send(&mut ui, wrong), "writeSave"));
        assert_eq!(ui.game.as_ref().unwrap().state, GameState::new());
    }

    #[test]
    fn ui_search_strategy_change_new_resume_cancel_dispose_revoke_old_reply() {
        for kind in ["setup", "new", "resume", "cancel", "dispose"] {
            let mut ui = Controller::default();
            let req = start_search(&mut ui);
            let action = if matches!(kind, "setup" | "new") {
                json!({"kind":kind,"mode":"ai","humanSide":2,"strategy":"simple"})
            } else {
                json!({"kind":kind})
            };
            let stopped = send(&mut ui, action);
            assert!(has(&stopped, "cancelWorker"));
            assert!(stopped["view"]["generation"].as_u64() > req["token"]["generation"].as_u64());
            assert!(!has(&send(&mut ui, search_reply(&req)), "writeSave"));
            assert_eq!(ui.game.as_ref().unwrap().state, GameState::new());
        }
    }

    #[test]
    fn ui_search_required_pass_and_terminal_do_not_launch_worker() {
        for terminal in [false, true] {
            let mut ui = Controller::default();
            let mut board = vec![0; 64];
            if !terminal {
                board[0] = 1;
                board[1] = 2;
            }
            let mut raw: Value = serde_json::from_str(&saved(board, 2, "ai", 1)).unwrap();
            raw["strategy"] = json!("searchV1");
            let token = resume(&mut ui);
            let loaded = send(
                &mut ui,
                json!({"kind":"loaded","token":token,"raw":raw.to_string(),"error":null}),
            );
            assert!(!has(&loaded, "think"));
            if !terminal {
                assert_eq!(ui.game.as_ref().unwrap().state.to_move(), 1);
                assert!(
                    loaded["view"]["notice"]
                        .as_str()
                        .unwrap()
                        .contains("探索AI")
                );
            }
        }
    }

    #[test]
    fn ui_search_invalid_strategy_resume_preserves_original_save() {
        for strategy in [json!("learned"), Value::Null, json!(7)] {
            let mut ui = Controller::default();
            start_search(&mut ui);
            let mut raw = serde_json::to_value(ui.game.as_ref().unwrap()).unwrap();
            raw["strategy"] = strategy;
            let token = resume(&mut ui);
            assert!(!has(
                &send(
                    &mut ui,
                    json!({"kind":"loaded","token":token,"raw":raw.to_string(),"error":null})
                ),
                "writeSave"
            ));
            assert!(!has(&send(&mut ui, json!({"kind":"save"})), "writeSave"));
            assert!(!has(&send(&mut ui, json!({"kind":"dispose"})), "writeSave"));
        }
    }

    // Model-free controller fixtures: these prove UI decisions, not engine numerics.
    fn fixture_model_ready(ui: &mut Controller) -> Value {
        let loading = send(ui, json!({"kind":"loadModel"}));
        send(
            ui,
            json!({"kind":"modelReply", "token":effect(&loading,"loadModel")["token"],
            "identity":fixed_identity(), "mainBytes":MAIN_BYTES, "endingBytes":ENDING_BYTES, "error":null}),
        )
    }
    fn fixture_full_start(ui: &mut Controller) -> Value {
        fixture_model_ready(ui);
        let asking = send(
            ui,
            json!({"kind":"new","mode":"ai","humanSide":2,"strategy":"fullModel"}),
        );
        send(
            ui,
            json!({"kind":"confirm","token":effect(&asking,"confirm")["token"],"accepted":true}),
        )
    }
    fn fixture_full_reply(think: &Value) -> Value {
        let state: GameState = serde_json::from_value(think["state"].clone()).unwrap();
        let index = state.status().legal_moves[0];
        json!({"kind":"aiReply","token":think["token"],"state":think["state"],
            "strategy":"fullModel","move":index,"modelIdentity":fixed_identity(),"error":null,"searchResult":null,
            "fullResult":{"move":index,"rawScore":0,"score":0,"scoreUnits":"engine-disc","scoreKind":"heuristic",
                "proven":false,"completedDepth":1,"selectivity":0,"probability":74.0,"isEndSearch":false,
                "nodes":7,"elapsedMs":1.0,"stopped":null,"interpretation":"simd","ttBytes":25165872,
                "coefficients":MpcCoefficients::default(),"mustPass":false,"terminal":false}})
    }

    #[test]
    fn ui_full_model_fixture_normal_reply_and_human_move_keep_idle_owner() {
        let mut ui = Controller::default();
        let initial = fixture_full_start(&mut ui);
        assert!(has(&initial, "resetModel"));
        let think = effect(&initial, "think");
        let spec = &think["model"];
        assert_eq!(spec["options"]["timeMs"], 1000);
        assert_eq!(spec["options"]["maxDepth"], 60);
        assert_eq!(spec["options"]["fixedDepth"], Value::Null);
        assert_eq!(spec["readyTimeoutMs"], 30000);
        assert_eq!(spec["replyTimeoutMs"], 1100);
        let moved = send(&mut ui, fixture_full_reply(&think));
        assert!(!has(&moved, "cancelWorker") && !has(&moved, "resetModel"));
        assert!(has(&moved, "writeSave"));
        assert!(ui.ai.is_none());
        let human = ui.game.as_ref().unwrap().state.status().legal_moves[0];
        let next = send(&mut ui, json!({"kind":"play","index":human}));
        assert!(has(&next, "think"));
        assert!(!has(&next, "cancelWorker") && !has(&next, "resetModel"));
        assert_ne!(effect(&next, "think")["token"], think["token"]);
        assert_eq!(
            effect(&next, "think")["model"]["identity"],
            spec["identity"]
        );
    }

    #[test]
    fn ui_full_model_fixture_cancel_reset_dispose_revoke_old_authority() {
        let mut ui = Controller::default();
        let initial = fixture_full_start(&mut ui);
        let think = effect(&initial, "think");
        let before = ui.game.as_ref().unwrap().state.clone();
        let cancelled = send(&mut ui, json!({"kind":"cancel"}));
        assert!(has(&cancelled, "cancelWorker"));
        let stale = send(&mut ui, fixture_full_reply(&think));
        assert!(!has(&stale, "writeSave"));
        assert_eq!(ui.game.as_ref().unwrap().state, before);
        let retried = send(&mut ui, json!({"kind":"retryAi"}));
        let fresh = effect(&retried, "think");
        assert_ne!(fresh["token"], think["token"]);
        let asking = send(
            &mut ui,
            json!({"kind":"new","mode":"ai","humanSide":2,"strategy":"fullModel"}),
        );
        assert!(has(&asking, "cancelWorker"));
        let reset = send(
            &mut ui,
            json!({"kind":"confirm","token":effect(&asking,"confirm")["token"],"accepted":true}),
        );
        assert!(has(&reset, "resetModel"));
        assert!(!has(
            &send(&mut ui, fixture_full_reply(&fresh)),
            "writeSave"
        ));
        let current = effect(&reset, "think");
        let stopped = send(&mut ui, json!({"kind":"dispose"}));
        assert!(has(&stopped, "cancelWorker") && has(&stopped, "forgetModel"));
        assert!(!has(
            &send(&mut ui, fixture_full_reply(&current)),
            "writeSave"
        ));
    }

    #[test]
    fn ui_full_model_fixture_resume_reselect_and_identity_only_save() {
        let mut source = Controller::default();
        let initial = fixture_full_start(&mut source);
        let raw = effect(&initial, "writeSave")["raw"]
            .as_str()
            .unwrap()
            .to_owned();
        let stored: Value = serde_json::from_str(&raw).unwrap();
        assert_eq!(stored["strategy"], "fullModel");
        assert_eq!(stored["modelIdentity"], json!(fixed_identity()));
        assert!(stored.get("files").is_none() && stored.get("weights").is_none());
        let mut ui = Controller::default();
        let token = resume(&mut ui);
        let loaded = send(
            &mut ui,
            json!({"kind":"loaded","token":token,"raw":raw,"error":null}),
        );
        assert!(has(&loaded, "forgetModel"));
        assert!(!has(&loaded, "think") && !has(&loaded, "writeSave"));
        assert!(loaded["view"]["saveDisabled"].as_bool().unwrap());
        assert!(!has(&send(&mut ui, json!({"kind":"retryAi"})), "think"));
        assert!(!has(&send(&mut ui, json!({"kind":"save"})), "writeSave"));
        let ready = fixture_model_ready(&mut ui);
        assert!(has(&ready, "writeSave") && has(&ready, "think"));
        let mut unselected = Controller::default();
        let token = resume(&mut unselected);
        send(
            &mut unselected,
            json!({"kind":"loaded","token":token,"raw":stored.to_string(),"error":null}),
        );
        assert!(!has(
            &send(&mut unselected, json!({"kind":"dispose"})),
            "writeSave"
        ));
    }

    #[test]
    fn ui_full_model_fixture_wrong_pair_and_malformed_reply_refuse_without_fallback() {
        let mut ui = Controller::default();
        let initial = fixture_full_start(&mut ui);
        let think = effect(&initial, "think");
        let before = ui.game.as_ref().unwrap().state.clone();
        let mut bad = fixture_full_reply(&think);
        bad["modelIdentity"]["mainSha256"] = json!("wrong");
        let refused = send(&mut ui, bad);
        assert!(has(&refused, "cancelWorker") && !has(&refused, "writeSave"));
        assert_eq!(ui.game.as_ref().unwrap().state, before);
        let retried = send(&mut ui, json!({"kind":"retryAi"}));
        let mut malformed = fixture_full_reply(&effect(&retried, "think"));
        malformed["state"] = json!({"invalid":"wire board"});
        let refused = send(&mut ui, malformed);
        assert!(has(&refused, "cancelWorker") && !refused["view"]["thinking"].as_bool().unwrap());
        send(&mut ui, json!({"kind":"modelFilesChanged"}));
        let loading = send(&mut ui, json!({"kind":"loadModel"}));
        let bad_pair = send(
            &mut ui,
            json!({"kind":"modelReply","token":effect(&loading,"loadModel")["token"],
            "identity":fixed_identity(),"mainBytes":1,"endingBytes":ENDING_BYTES,"error":null}),
        );
        assert_eq!(bad_pair["view"]["modelStatus"], "error");
        assert!(!has(&bad_pair, "think") && !has(&bad_pair, "writeSave"));
        assert!(!has(&send(&mut ui, json!({"kind":"dispose"})), "writeSave"));
    }

    #[test]
    fn ui_full_model_fixture_pending_and_corrupt_resume_survive_model_preparation() {
        for raw in [
            "{bad".to_string(),
            json!({"version":1,"game":"othello","mode":"ai","humanSide":2,
            "strategy":"unknownFull","state":GameState::new()})
            .to_string(),
        ] {
            let mut ui = Controller::default();
            start(&mut ui, "local", 1);
            let before = ui.game.as_ref().unwrap().state.clone();
            let token = resume(&mut ui);
            assert!(!has(&send(&mut ui, json!({"kind":"save"})), "writeSave"));
            let loaded = send(
                &mut ui,
                json!({"kind":"loaded","token":token,"raw":raw,"error":null}),
            );
            assert!(!has(&loaded, "writeSave"));
            let ready = fixture_model_ready(&mut ui);
            assert!(!has(&ready, "writeSave") && !has(&ready, "think"));
            assert_eq!(ui.game.as_ref().unwrap().state, before);
            assert!(!has(&send(&mut ui, json!({"kind":"dispose"})), "writeSave"));
        }
        let mut local = Controller::default();
        let ask = send(
            &mut local,
            json!({"kind":"new","mode":"local","humanSide":1,"strategy":"fullModel"}),
        );
        let started = send(
            &mut local,
            json!({"kind":"confirm","token":effect(&ask,"confirm")["token"],"accepted":true}),
        );
        assert_eq!(started["view"]["strategy"], "simple");
        assert!(!has(&started, "think") && !has(&started, "loadModel"));
    }
}
