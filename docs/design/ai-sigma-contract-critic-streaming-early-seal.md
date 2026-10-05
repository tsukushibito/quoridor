# SIGMA-EARLY-SEAL-INDEPENDENT / quoridor-4lc.64 / 試行1・契約1

critic 01a0f31d-8227-7e03-a7e6-915b4918c11b → coordinator。親継続版2 `docs/design/ai-sigma-continuation-20261001.md` SHA6766deb7b6588c702ba1516558952fb1e6c6d09def7dd155c174f44eb5d3987f 全文継承。終了Oct2 01:00UTC、重job停止00:50、監督終了00:55、global LLM3、CPU/RAM/累積12GiB・許可範囲不変。受領から処理35分/提出45分、新jobは処理期限5分前まで。絶対全体期限との早い方。通常の自律研究の独立検証依頼であり、旧 .56/.60 の再試行や期限延長ではない。容量障害再発なら保存・自己job停止・報告し、この契約から盲目的な再start/model変更/server再起動をしない。

## 入力・所有

writer .63 はsource/runtime停止済み。統括のread-only照合では旧688入力、最終451payload、source58 checks一致、記録77 PID/starttick現在不在。新NNを行わず正常12件の算術と予約reserve89/cutoff402/seal411を確認した。独立受入れ前の読み取り支持であり、全期間回収証明ではない。固定入力は次の実bytes。

- `.artifacts/ai-sigma/continuation-20261001/SIGMA-STREAMING-EARLY-SEAL/final-manifest.json` SHA c877e781d72d1a71cc8c667a7298ffd245058a011a7beb56640490155235a4d9。
- 同 `source-frozen.json` SHA c5381302d6573605242d06ede2f173e8fb68102c3ad9121a6d68e4070a5b411d、最終revision3。
- `docs/reports/ai-sigma-experiment-streaming-early-seal.md` SHA58996b0567e1688fd1336bdae39a55f7503581ba386fb0f07cbe471fe9f769a3。
- 同 `all-public-requests-combined.json` SHA e568c46084c12f7a52404575af52c9e17302476efa5ae5a549cbce47470f5da8、`preregister.json` SHA22d2fa771906345eae0c06f7b8c6bacd2daf62e5e0a68c1607eb28800df3a654。

自己書込は `.artifacts/ai-sigma/continuation-20261001/CRITIC-STREAMING-EARLY-SEAL/` と `docs/reports/ai-sigma-critic-streaming-early-seal.md` のみ。原 .63/.62/.59、model/immutable Wasm/ORT、製品/rootlockはread-only。元新toolは `tools/ai-sigma-streaming-early-seal/`。必要copyは自己域、絶対入力/output/temp/deadline/guard・結果前の指定診断選択だけpatch、方式/誤分類/時計条件を修正しない。原最終版・過去失敗版を区別する。新checker/注入は自己copy、差分保存。入力前後hashとwriter停止・旧自己外部job停止を確認後だけruntime。

## 判別と結果前固定

「推論を待たず完成cacheを返せる」ことと「全体T内の合法配送・取消後の次手資源公平」を別に反証する。T500、reserve89、commit余裕9、seal411、cutoff402を固定し、この独立試験で再選定しない。NN最大値へreserveを広げて救済しない。

保存20要求を独立再集計。正常12、steady9（warm sample=-1、steady0/1/2）、NN0終端2、境界6。全正常p95/max340210.191msの元warm失敗、条件付き11、steady9を別列で保持。元原cancel ACK欠測/誤分類修正、未実行19のみ継続、均一一版一窓の20完遂でないこと、初回control文書追記hash拒否と3618byte期待原文固定を保管する。文書の原期待SHAと保存prefix/fullcurrentの一致は監査するが、実コード入力へ任意prefix切取りを許す根拠にしない。統括checkerの最初のsteady6誤集計→sample>=0で9への訂正も保存済み。

最終revision3の実ブラウザ診断は結果前に固定して一窓・一版のみ。先に完成cp後cancel→次要求の連続時計を一度実施し、その後正常3golden各warm1+sample2（計9上限）。重要境界は各一度、上限6（NN0合法goal/人工200、初回無し、検証完了cutoff跨ぎ、受信fault、caller busyまたは遅延通知は静的知見で選択して実行前に列挙）。固定8sim direct24cpは元保存rawの独立照合を基本とし、新全control実NN再試行はしない。未成立前提は未成立のまま記録し、同一suiteを救済再測定しない。startup/warm/通常/境界/取消を別分母にし、NN0校正payloadをNN成果にしない。

各runtimeの正しい `fixture.legal_prefix`、ID・長さ・型・finite・strict value[-1,1]・合法Action/prior/stats/完成owned cp、request/gen/epoch/prefix/history/key/model/schema/limits/token/sequenceを先に検査。固定参照の数値はabs<=1e-4+1e-4*abs(ref)、不正shapeを切り詰めて比較しない。モデル/ORT threads1とrootP2対応を保存。完成backup後からcp不変性、受信検証終了とcopy/freeze終了時刻でcutoff再確認、遅配/partial/foreign/逆順・重複/世代を反証。主側sealにWorker query/NN awaitがないことをsourceと実経路で確認。

t0はimmutable入力供給可能・変換前、合法性/identity/format/encoding後Node stampまで。page/Workerの時計区間/drift/end包含、timer wake遅延、cp完了→受信→検証完了→seal→配送の鮮度/費用を記録。実 `session.run` のAPI await区間とexact kernel命令時刻を区別し、人工busyだけの成功を実ORT跨ぎへ格上げしない。全配送lateはreject/nullで救済0、初回cp無しnull/fallback0、NN0終端を人工到達証明へ格上げしない。

cancel/fault後は旧探索handle/activeNN/live_searches=0を実ACKで確認してから次NN、次t0は先のpublic stampで固定しcleanup/free/必要freshloadを時計外へ逃がさない。取消自体は成功Actionではない。seal前受信fault全discard、seal後faultは公開不変という受信順政策の限界を明記し、故障生成時刻の全知を主張しない。旧PID0→fresh・最後の自己回収はboot/PID/starttickとkernel sole-root/adoption/waitの来歴で確認、forcedと自然停止、現在不在と当時controlled回収を別列にする。未知identityへsignal/wait禁止。参照AIにも同caller/時計/通知頻度/残処理課金を適用できるかは静的レビューまで、参照C1/FPU.2/temp0/order/root展開sim外は変更しない。

## 資源・停止・受入れ

CPU静的0/runtime2単logical、NNthreads1、RAM3GiB guard2.5、各重job最大180秒。新64MiB guard56は既critic128MiB内、combined112MiBを維持し不足なら停止、追加予約0。累積12GiBをリセットせず、条件付き未配分3,626,595,885Bは範囲外共有増分/peak欠測付きの旧予約値として保持。専用TMP/XDG、PID/starttick/command/hash/UTC/monotonic/exit/RSS/affinity/保存量を記録。静的重読取を自己NNと重ねず、他重NN停止を確認。瞬間peak/背景負荷保証をしない。

build/compile/download/依存更新/共有更新/製品/学習/GPU/対局/holdout/追加委譲/他者kill0。actual_go=false、独立通過だけで試合開始・棋力達成・採用を認定しない。Atract/BORT/CB0とH1backend/H2探索・故障/H3IPC-checkpoint/H4標本を維持、旧32局/NI未立証/旧g287/過去容量・期限・scope逸脱を消さない。文書より先にruntime-stop/hashafter、短い暫定報告を先保存して提出時間を確保。受領・claim・実開始をBeadsに記録、終了時backup/report。自issueは受入れ待ち、goal/他者close0。.60blockedや .56旧期限は変更しない。
