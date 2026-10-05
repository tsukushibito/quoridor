# SIGMA-FIXED-QUEUE / 試行1 / 契約版1

目標quoridor-4lc、子issue quoridor-4lc.7。experiment / 01a0f31d-6d15-7620-bb63-4b4f878e4746、報告先coordinator / 01a0f31b-3409-75f2-a30e-453a50484f94。
目標契約 docs/design/ai-sigma-research-goal.md 版1全文・AGENTS/common/experiment/team design/AI設計/storage policy/handoffを継承した自律権限による実依頼。追加subagent/委譲0。場所 /workspaces/quoridor/.worktree/ai-sigma / codex/ai-sigma。目標/.1/既存M2/UI/描画/主checkout/他worktreeは変更しない。
開始wrapper ready、目標/.5/.7をshowしてpause確認、.7だけ本人claim。.5報告は観測として受領し最終独立受入れ保留。.5をcloseせず、既存source/raw/log/binary/fixtureと終了状態をimmutableに保持する。あなたは.5停止済みなのでこの別1要因試作のcode writerを継続。source移譲はしない。

入力:
SIGMA-B0-PROFILE報告 SHA256 be856e7727e129931d46bf0a8bef9dff836608583bde9a8d016994261329b044、.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/ の原B0/最終source/immutable binaries/raw/fixture。現HEAD1482df8da6dd91c95db211aeaa914af775b2bc76＋launch移入＋.5diff/hashが基準。元.5feature-offを今回対照にする。profiling器は採用speed比較のtimerに使わず無効で測る。
統括独立replay .artifacts/ai-sigma/verification/PROFILE-COORD-1/summary.json は全6caseで探索/合法/距離/transition等の出力厳密一致とexclusive保存、R_exp最小.9757以上を再確認。ただし原bin6warm/粗時計20warmの短い別再現でwalled-midgameのmedian overhead5.13%となり5%gate不成立、他5case0.41–4.02%。.5元結果の全gate通過とこの条件差を混ぜず、計測器の全面受入れは保留。full時計gate超過は既存negative器結果として保持。native/Wasm最適化gain、同時間棋力はまだ未測定。

問い/仮説/反証:
壁距離wall_distanceのqueue heap/VecDeque操作だけを固定配列に換えると、同じBFS順/距離/合法手/探索結果のまま速くなる。候補は[81要素]のcell+distance queue、head/tailでFIFO。seenはenqueue前にsetされ各cell1回なので最大81entries。neighborsの順序、早期goal/invalid入力・到達不能・距離、壁表現、合法壁候補、再検証、探索評価/limits/PUCT/tieは変えない。
許可しない同時変更: BFS省略、bitboard flood、距離map、reachable専用簡略化、buffer再利用、unchecked play、合法手間引き、評価prior/solver/PV/FPU/規約/時間adapter。今回queue1要因だけ。速度改善がなくても別方法へ勝手に広げずnegative/保留を報告。Legal+BFS全unionが支配でもqueueだけの改善量を事前断定しない。

所有scope:
crates/quoridor-core/src/position.rsのwall_distanceと必要importのみ、対応core differential tests、診断用bin/scriptのAB比較出力、tests/e2e/phase3-performance.spec.tsの全探索開始から結果配送までwall計測とrun固有出力のみ（製品bridge/UI/API変更なし）。scripts/devの既存専用runnerは今回deadline/runの設定追加が必要なら許可、既存Beads/research-team/toolchainは不変更。source snapshot/patch、build/native/wasm生成物、runs/SIGMA-FIXED-QUEUE/、docs/reports/ai-sigma-experiment-fixed-queue.md。モデルdownload、依存version/lock変更、training環境更新、Wasm public API変更なし。

予算:
起動60分、最後5分は保存/停止/reportに確保。全体締切UTC2026-10-01T01:17:58.145139+00:00/JST10:17:58、18:47UTC頃残り約6時間31分。準備2論理CPU（2,4/jobs2）、測定CPU2単一、RAM4GiB/GPU0、追加保存/取得1GiB以内、.5既存build/npmと今回を合わせexperiment所有新規2GiB以下。現在.5実量約520396800bytes（0.485GiB、RSS観測1.559GiB）、12GiB全体上限に対して初期文書/起動reserve込みで保守的に既存約0.55GiBを使用基準とする。.5の未使用3.5GiB予約は解放し、今回追加1GiBを予約。正確全体残量は他owner .6fixture集計待ち、2GiB所有上限＋小文書以外の枠は未配分。GPU/学習/正式対戦0。
並行hypothesis .6はCPU0/1CPU/1GiB/32MiBのtext/小fixtureのみ。LLM統括+あなた+hypothesis最大3。criticの.5/今回独立検証はhypothesisの枠解放後に統括が別契約で配分。重い独立再実行が来る場合はあなたのbuild/測定と同じ窓で重ねない。

実施/固定条件/受入れ:
1. .5baseline source/binary/生成Wasmを変更前にsnapshot/hash、対応するlock/compiler/fixture/seedを固定。browser測定口を追加するならまず元BFS版でその測定口をbuild/runする。候補の生成物と取り違えないようbaseline/candidateを別pathとmanifestに保存。
2. queue候補だけを実装。test referenceは元VecDeque BFSをtest-onlyへ残し、本番へ二実装を増やさない。原6fixtureに加え、seed20261001固定で少なくとも1000合法replay局面を結果前生成/hash固定し両playerのdistance、全合法IDs/順序、全合法transitionを基準snapshot版/参照実装と照合。壁多数/0walls/到達境界、goal/jump/P2も含める。不正盤面を合法fixtureと呼ばない。81queue上限、seen1enqueueの証明と必要なassert/testを残す。
3. feature-off、元6case192sims/seed1979/512nodes/depth24/step4で維持対照のsearchstats/root action/prior/visits/value bit/合法順/全transition/距離を厳密比較。一致しなければ停止、不採用、失敗証拠保持。core/ai既存＋必要differential tests、fmt/clippy/diff checkを通す。
4. 速度試験は勝敗/対局なし。native両binaryに同じdiagnostic harness/timeout/affinity、warmup1+10sample、AB/BA順で3roundの事前固定計30warm/case/variant。同compiler/release/profileoff、limits同一、原6と追加fixtureを別集計。median/p95/max・speed ratio・raw全sample/メモリ、0未満のgainも保存。結果を見てsample/seed/入力を都合よく追加しない。
5. Browserはbaseline/candidate同一release/test-hook/UI/CPU2/read-onlyChromium設定でphase3-performance単独を比較、slice/cancel/arena/memoryに加えstart→合法result配送の全探索wallを測定。測定口自体のinput/hashを固定、warmupを明示、複数round AB/BA順（少なくとも3warm/case/variant×2round、結果前固定）を予算内で実施。baseline/candidateのserver/workerを同時に動かさずport/PID終了確認。artifactは別ディレクトリへ保存し.5rawを上書きしない。広いUI suite再試行は今回しない。.5UI timeoutは原因未確認のまま保全、performance単独成功で消さない。browser測定が不成立ならnative-only候補として保留しWasm採用を宣言しない。
6. 採用条件は正しさ一致・native/Wasmに安定した実時間gainの根拠・cancel/memory回帰なし・独立再実行。今回担当報告では候補/採用提案だけ、統括が独立確認後決める。目安native median5%以上改善を支持、5%未満は小さい/不明確と報告、局面別劣化やtailのばらつきを平均で隠さない。gainの閾値を超えただけで棋力改善とはしない。

停止/再現/報告:
runnerにPID/PGID/start/end/timeout/jobID/command/cwd/lock/input/binaryhash/affinity/RSS/storage/exit/signal/log、checkpoint該当なし。各job timeoutは子60分・全体残時間以内、資源guardは上限前に停止。準備と測定を重ねず他者負荷/SMTは記録、正式無競合を主張しない。pause/異常で自己groupのみ停止wait回収、preview/Chromium/portを確認、他者kill0。終了時書込停止と予算消費/残量をhandoff報告。送信前Beads目標/子pause確認、backup sync、既存report --to coordinator --issue quoridor-4lc --body-file /workspaces/quoridor/.worktree/ai-sigma/docs/reports/ai-sigma-experiment-fixed-queue.md（UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1）。状態はBeads、受入れ待ちin_progress、独立受入れ後本人close。個別完了で目標を閉じない。
