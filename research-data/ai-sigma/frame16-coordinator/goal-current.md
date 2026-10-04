# 現在のNNUE研究優先順位（frame16）

05:55:50–07:55:50 UTCの明示許可内。新heavy07:45:50、監督07:50:50、monitor07:53:50、最終証拠07:55:50は92所有。CPU4/RAM8GiB/保存12GiB/同saved六role・model/effortを維持する。

最大の未解決点は、NNが距離基準に届かない差が訓練適合不足か汎化不足か、どの局面群の残差関係で生じるか。保存済み同train96/val24で、200stepはtrainでも距離未達、400stepはtrainを超えてvalidationで悪化する。早期と後期を区別して比較する。

主配分216 experimentは4653train/1248val、同STM rootmean、gameequalMSEでtrain-only距離・定数とplain209/標準化211各200/400を合わせる。保存曲線を再利用し、必要な4小CPUforwardだけでper-row残差・群別の差を補う。訓練/教師/test/GPUは開始しない。solewriterと資源・期限は[契約](../../research-data/ai-sigma/frame16-coordinator/fit-gap-contract.md)。担当は実配送/本人claim/static開始済み。

217 criticは主計画の優先順位を独立に問い、label-free群と保存算術の必要検算を担当する。[契約](../../research-data/ai-sigma/frame16-coordinator/fit-gap-critic-contract.md)。92は旧exact停止確認から現role・親16期限binding/validate・実runningloaded・終了回収を所有する。主研究は運用全履歴や全稿承認待ちにしない。

fresh独立testは転移の確認にはなるが現在の距離未達の関係を説明しないため保留。追加seed/LR/幅/arenaも分析前の主仕事にしない。216の実残差観測から判断を変える最大1低費用対照を統括が選び、既枠内で実配送する。原因分析と効果確認評価を区別し、意味のある結果でこの主計画を更新する。

旧testは選定へ戻さず173正式198局非学習。再用validation利益を独立test利益にせず、rootmean蒸留と真z・棋力を分ける。frame14/15の成績・期限・失敗/欠測は各原report/data/Gitに保持し、最高棋力goal未達を維持する。

92は06:13:31実freshstart・current exact scheduler/monitor一致・24binding hash一致を確認。初回監督turnは06:16:36 interruptedでApp Server履歴上終了、点検内容/全面成功とは区別する。217の選定前修正を採用し、MSE差を元gameequal重みで残差振幅項と誤差とのcross項に分け、排他的binのsigned寄与・weight massを全体へ足し戻す。追加forward/予算resetはない。


## 実残差から更新した主配分

216の4checkpoint補完は23604samples/CPU2単1/1.515544s/全子wait・exact不在、旧集計parity最大2.94e-10。標準化200はtrain .548566856 > 距離 .405943737、val .613916444 > .485146813。400はtrain .257283205 < 距離だがval .648771505へ悪化する。N−Dとy−Dの相関はtrain .607338、validation .047912。validation gap .163624692 = displacement .192934292 − 2cross .029309600、meanbias²と距離clipの寄与は小さい。後半の補正がgameを跨いで転移する関係を主な未解決点とする。唯一原因や教師真値は認定しない。

次の最大1は216同課題・元budget内の固定ridge residualreadout対照を実配送した。学習済みstandard400のhidden32を5901一回だけ抽出し、train-only gameequal/列標準化・lambda .01固定で33係数をfit、clamp(D+readout)を同validationへ適用する。旧randomfeature head204との違い、unclipped fitとclipped評価を明示し、optimizer再学習はしない。総NN29505<=30000、既scope/CPU/RAM/保持予約内、phase1成功結果を保持した別phase。[条件全文](../../research-data/ai-sigma/frame16-coordinator/216-residual-head-amendment.md)。担当216実steer accepted06:23:26。

単純予測振幅縮小はalignmentの弱さを確認できてもhidden表現が運ぶ関係を試せないため保留。fresh独立testや追加LR/幅/seed/教師/arenaは原因判断より先行させない。218 hypothesisへ独立仮説・競合案の選定見解を06:25:01実配送、静的viewのみでモデル/forward0。217はphase1必要独立算術と残予算内の選定異論を担当し、180capをresetしない。全稿承認gateは設けない。

217のwallラベル修正を採用: walls_total/binsは残壁在庫の合計であり、配置済み壁数・盤面複雑さとは解釈しない。必要placed=20−remainingはNN0派生、原科学値は保持する。
