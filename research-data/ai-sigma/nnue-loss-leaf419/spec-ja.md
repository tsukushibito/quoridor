# 419.1：敗戦局面・候補・共通葉の固定診断仕様

本仕様と `fixed-inputs.json` は419の新しいSearch／forwardの前に固定する。対象は保存383の3親だけ。設計完了はsource／software／数値成功を意味しない。同じ419.1は設計引渡し後も開き、元の一度の有限結果を解析する。Astra、新session、再帰委譲は使わない。

## 固定入力と浅い二horizon

| 親            | NNUE手番 | 実在庫P0/P1 | 原NNUE実着手 | 原完成深さ／探索値STM | 今回の親horizon |
| ------------- | -------- | ----------- | ------------ | --------------------- | --------------- |
| slot4 / ply11 | P1       | 6 / 8       | 156 = V(d2)  | 3 / 0.95947003        | 2, 3            |
| slot4 / ply39 | P1       | 0 / 2       | 192 = V(h6)  | 5 / 0.99928635        | 2, 3            |
| slot5 / ply12 | P0       | 8 / 8       | 104 = H(h3)  | 3 / 0.87524366        | 2, 3            |

この順序を保ち、新しい数値を見て別rootへ補充しない。最初と最後は原完成D3に接続でき、低在庫の中央はD5再現を求めず、全合法応手を保存できる浅い比較へ狭める。原値はsearched値でありstatic値ではない。D3とD5の差、旧95ms・TT4K・持続セッションと新cold・時間制限なし・TT1Mの差を残す。

原RAW gzip一つの第1／第2行を一度だけstream読取し、行全体（LF込み）のSHA・bytes、3つのprefix、当該実着手、完成observationを383の選択済みposition recordと照合済み。詳細は `raw-selected-prefixes.json` と `selected-input-byte-checks.json`。原完全prefixは11／39／12手、順序付き履歴は12／40／13局面。3親は同じfamily0の2ゲームに属し、独立3標本へ水増ししない。

native側では現役 `measurement::replay` の `SigmaContext::from_prefix`、normal検査、全prefixの終局非通過、rules・total_ply・手番・在庫・root key・全履歴照合を一度行う。JSONの状態／履歴は比較期待値であってchronology certificateではない。opening4手のcounts、盤面だけ、`from_counts`で代用しない。入力不一致は原error／UNKNOWNとして停止し、別親で埋めない。

## 評価器・通常探索・候補union

NNUEはfresh353 no-output-bypass BEST43のみ。descriptor `46ec2c47…`、weights `046fe926…`、typed evaluator `96a5f41f…` を現役measurementのResidualModel／ResidualEvaluator factoryで照合する。Dはmodels空の既存 `original-distance-a0-b8-tanh`。標準化した距離head入力はa=b=0でも残す。plain NNUE、BEST51、旧355の3評価器設定へ置換しない。SIMDは両入口で明示false。

各呼出しはfresh session／空TT・ordering history、Control/no-policy、PVS ON、TT 1,048,576 slots、時間上限なし、1,000,000累積nodes。LMR、Cheap、zero-stock approximation、safe-race leaf、診断用以外のobserverは明示OFF。現研究標準や製品／generator defaultを変えない。両評価器とも既存LEGACY domain（nonterminal有限[-1,1]、true goal ±2、threefold 0）を使い、true terminalをstaticより先に扱う。

先に通常の全合法root探索を、親順・horizon 2→3・NNUE→Dの固定順で最大12回行う。これらのhorizon3呼出しが候補選択の観測も兼ねる。追加のanchor探索はしない。

各親の候補Cは、**原NNUE実着手、通常NNUE H3の完成推奨、通常D H3の完成推奨**の和集合。ActionIDでdedupし昇順保存、最大3。H3が未完成ならその推奨は欠測のままにし、最後のH2 snapshotや別horizon／rootで補充しない。正常な別評価器のH3推奨と原実着手は使える。同じCをH2とH3の両方へ使う。通常H2の選択がC外ならその事実を記録し、Cを拡張しない。これは全合法root推奨と候補部分集合の比較範囲の違いである。

各C×2評価器×2horizonのforced呼出しは最大36。重複した候補／同一requestは一度だけ実行し、複数の役割から同じcall IDを参照する。通常root探索と単一手制限root探索は異なるrequestであり、偶然同じ着手／値でも同じ呼出しだったとはしない。通常＋forcedは最大48回、NNUE側最大24回、合計48M nodes。原cap／取消／error／未入場はUNKNOWN、refillやcap増量はしない。

### forcedの正確な意味

親horizon Hは固定するroot action一手を含み、そのchildは深さH−1、非root ply1、親STMのfull window `[-∞,+∞]`。Hをchild深さへ二重に加減しない。通常と同じ親完全履歴からcanonical child／context／path／make-unmakeを通り、返値の親視点への符号反転は一度。

既存 `SearchInvocation` と通常の反復深化・`Search::child` へ薄く接続する。1..Hの反復を一つの呼出し・同じTT／ordering／scratch／cumulative 1Mで行い、途中反復ごとにcapをresetしない。子を別rootとして通常Searchする旧355 callerや417の専用資格を緩めたAPIでは代用しない。別negamax／本番Search loopは作らない。

単一手制限rootの値を、全合法rootの通常Exact TT entryとして格納・再利用しない。fresh forced sessionでも反復間の親Exact hitの誤用を防ぐ必要がある。child側の通常TTは実board／fullhistory／domain／depth／boundの既存資格を保つ。強制action、要求親H、実child深さ、完成反復、window／bound、stop、PV／合法性、raw statsを記録する。未完了要求Hへ下位完成snapshotの値を昇格しない。

## 一つの共通診断木からH2／H3を得る

親rootでCのみを展開し、その後は**全合法応手**を親から3plyまで展開する。Cの外を剪定した通常root minimaxとは呼ばない。候補別subtreeの全合法有限horizon値と、C内の順位が対象である。全合法root探索との値／選択対応は別表にする。

既存 `value_search_compare::tree` のterminal-first／同じ合法展開／同じ葉で複数評価／辺ごとの符号反転を狭く共用し、2評価器とcompact記録へ合わせる。旧355のbook、モデル、3評価器、4096、100k局所／800k全体などの固定条件は持ち込まない。新しい実験用Search loopや全TT snapshotは作らない。

H3の木を一度だけ作り、非終端のply2とply3で同じ局面・同じ完全pathのNNUE／D static値を各一度評価する。ply2の値はH2 frontierとして、ply3の値はH3 frontierとして使う。H2用の再展開・再forwardはしない。terminalは深さに関係なく先に確定し、以後を展開しない。TT／alpha-beta剪定／path合流は使わず、同じ盤面への別履歴経路は別nodeのまま。

9x9では各方向のpawn候補は高々2、壁候補は64H+64Vなので合法分岐数の安全な上界は136。3親×最大3root候補では、rootを含むH3 visits上界は `3 + 9 + 9×136 + 9×136² = 167700`。これはsource上界であって実測件数／性能ではない。全300,000 visitsの既存許可上限を別に実制御し、全体のhead論理counterへも課金する。部分展開・cap・取消・errorなら当該nodeと未完成のancestorのbackupをUNKNOWNにし、未展開枝の無視やstatic補完でexactにしない。完成H2がH3中断時にも保存済みの全合法H2 frontierから得られる場合だけ、そのH2を独立してCOMPLETEと示せる。

compact記録はroot prefix参照、node／parent／action／ply、terminal種別、合法child数と実child数、完成状態、保存static値、必要なbacked-up値で十分。fullhistory／81cell／FT配列を全nodeへ複製せず、pathから再構成する。出力cap超過も元失敗／UNKNOWNで止め、欠落した枝を完全としない。既存のimmutable output／bounded publicationを再用する。

`v(node)=max_a(-v(child))` とし、static・terminalともそのnodeのSTM値を保存する。候補値はchild値を一度negateした親STM。数値tie集合は通常のf32等値（±0もtie）、表示用canonical手は最小ActionID。float bitsは別に保存する。通常Searchの同点手は実orderingに依存し得るため、canonical手との相違だけで評価誤りとしない。

## 葉・値の起源と一度のhead view

canonical residual ownerの**同じ一計算**から、distance baseline、linear residual、有限検査直前の合成FP32 pre-tanh、f64 tanh→FP32 post値を取り出す最小のdiagnostic viewを設ける。既存observed callbackはrouting二boolだけなので拡張点が必要。post値のatanh推定、headの二重実行、runnerでの別formulaは使わない。通常OFFにinput clone／snapshot／scan／毎node時計／追加headを入れない。

木のstatic frontierにはNNUE pre/postのbitsとD正本post値、必要な距離／尺度参照を結ぶ。raw距離D/80、head内の `(distance−mu)/sigma`、descriptorのscaler identity、STM／root視点を区別する。詳細input／feature／accumulator viewは後述の最大256追跡状態だけに絞れる。terminal値にNNUE logitを捏造しない。

通常Search／forcedのroot searched値、PV末端、TT boundはstatic NN値ではない。既存の最小情報で起源を追えないTT数値はUNKNOWN。共通木はTTなしなので、terminal／static frontierからの有限backupの由来を完全に示せる。この違いをtrace基盤増設や全TT保存で埋めない。

## 事前固定する保存木への介入

介入は追加Search／forward／fitではなく、完成した保存木の値だけを変えて全体をrebackupする。parent×HごとにNNUEとDのC内argmax tie集合を比べる。異なる場合、各々のcanonical winnerをaN／aDとする（同じcanonical手でもtie集合差は残す）。各評価器のbackupでaN／aDそれぞれからcanonical最適応手を辿る、最大4本のpathを機械的に選ぶ。

この最大4pathの非terminal frontier endpointをActionID列辞書順にdedupする。各endpoint一つずつ、および全endpoint同時の最大5対照で、**NNUEのlocal-STM post値だけを同じ葉のD正本post値へ置換**する。terminal・他の葉・root候補・scale・tie規則は固定する。毎対照で全応手をrebackupし、PVを固定して代替応手を無視しない。元値／置換値／node path／候補値／tie集合／winner／新PVを保存する。最大3親×2H×5=30の保存算術対照で、変化しなくても別の葉集合を探索・補充しない。

全static値をDへ置いた対照は既にD baselineのbackupに相当する。Dを正解とする介入ではない。「この固定木ではこの置換により選択が変わった」までを局所機序として述べる。単独endpointが効かず、同時置換だけが効いた／どれも効かなかった結果も残す。原局面が既に全手負けか、有限horizonの最良手が真の勝ちかはこの介入では判定しない。

## full／delta／undoの限定照合とcounter

完成木でaN／aDを辿る最大4canonical path（順位差なしなら同じ規則のwinner path）と3rootだけを実追跡状態として選ぶ。parent×2H×4path×最大3ply＋3rootで高々75到達状態、dedup後は減る。最大256の許可を埋めるための追加状態探索はしない。完全root prefix＋pathをidentityとし、盤面だけで合流しない。

現 `nnue-diagnose::qualify_residual` のprimitiveで、canonical make／unmake、fullとdeltaの特徴／距離／値、親input／accumulator／出力の前後復元を比較する。全qualificationや旧成功suiteは実行しない。exactな構造／親復元、FT誤差、値bitsと既存の数値alert基準を分け、FP32 full／delta差を無根拠にbit同一としない。alertや未観測を除外・再計測で消さない。

論理NNUE評価はSearch、共通木、head view、full/delta/復元の追加評価を一つの25M counterで会計する。Search側は最大24×1M node由来。木は300k visits以内、root／parityの追加headを1状態最大4評価・最大256としても `24M+300000+1024+3 < 25M`。traceが既存headの値を返すだけなら追加評価と二重計上しない。物理FT full／delta、physical head、logical evaluate、prepareのみ、木visits、Search nodes／callsを分離する。

## 必要な限定検証と引渡し

source作者とは別の既存Sol担当が、forcedのH−1／ply1／window／root-TT制限、完全履歴・terminal／make-undo／error-cancel、共通木の完成性／符号／tie、head viewの非干渉、保存介入での代替応手への切替を限定確認する。新しいtoy owning定義と必要compile／Clippy／genuine releaseはRootが担当し、旧成功suite／実モデル全資格は再演しない。新しい科学の許可や人間spec再承認を待つ段階は作らない。

最終解析では通常／forced／共通木のcandidate表、最大3親の実続行との対応、少なくとも一つの静的SVG／PNG図を示す。旧敗戦・旧searched optimismに接続する限界、同じ有限木の順位差、介入が支持／反証した範囲、未知のTT／時計／真のWDLを分ける。Dとの一致、深い評価器の合意、原ゲームの敗戦をoracleとしない。足りない比較は最小の問いとして最大3件まで記すだけで実行しない。

Main／Git／Cargo／数値launch／統合は324、sourceは419.2、私有設計／後日の解析は同じ419.1。実reader／child／TMP／handles／leasesをSTOPしてから引渡し、実timing中は重いhelper／IOを保持しない。raw・source・software・原FAILED／NULLとdisk masks／費UNKNOWN、全pause、製品generator default、models／weights／sealsは保持する。
