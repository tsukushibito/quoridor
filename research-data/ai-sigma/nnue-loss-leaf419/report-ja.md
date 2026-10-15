# 419.1：NNUE敗戦局面の候補・葉評価・保存介入

**原operational outcomeはFAILEDです。** 原job `0e278638-f237-4bdf-bf94-4c0df7a2d693` は、計算とOutput.finish後、CLIが全木をstdoutへ再serializeした際にfull command capture limitへ達しました。nativeはSIGTERM／exit−15、pipe_drain失敗、原cleanup=false、signal-mask=pending／persist=attemptedを保持します。outer jobのexit1・cleanup=true、後続collectorでのfresh absence／directreap／handles／TMP停止確認は別scopeであり、nativeの原FAILEDや欠けたstdoutを成功へ書き換えません。再実行・補充は0です。

以下は原 `data/result.json`（SHA `12032a29…`、18,954,604 B）とjournalの小さいparity3行から得た**有限保存観測**です。原fileは変更せず、モデル／library／image payloadを読まず、新Search・forward・対局・solver・bootstrapは実行していません。

## 得られた限定的な結論

固定C内のNNUE有限backupとDの順位は、3親×H2/H3の6組中5組で異なりました。事前固定した23介入を保存木全体で再計算し、3組で単一葉の置換がC内canonical選択を変える4例を確認しました。これは同じ有限木の計算上の依存です。Dが正しい、原敗戦がその葉の誤評価だけで生じた、あるいは全合法rootで介入後も同じ新手を選ぶという証明ではありません。

H3のslot4/ply11とslot5/ply12では、固定endpoint4葉を同時にD値へ置いても元のNNUE候補が残りました。別の未置換応手へPVが移るためであり、「最初のPV葉一つを直せば選択が直る」とは一般化できません。

## 固定条件・分母・保存整合

対象は元spec `51935438…`／入力 `b26fb4d5…` のslot4/ply11、slot4/ply39、slot5/ply12だけです。同じ開始familyの2ゲームで、うち2親は同じgameです。独立3標本や棋力比較ではありません。原383の12敗戦や他の局面へ母数を広げません。

BEST43 fresh353（weights `046fe926…`、descriptor `46ec2c47…`、typed evaluator `96a5f41f…`）とD(0,8,tanh)、Control/PVS/TT1M、LMR・Cheap・旧近似・safe leaf OFF、time=None、cold session、H2/H3です。source `1e998c915e8e…`、Build `421f5ef8…`、immutable image `ad14f7b4…` を原settingsの参照で束縛しました。simd=falseは既存FT selectorの指定で、canonical guarded head routingまで全scalar化したという意味ではありません。

CはH3の原NNUE実着手＋完成N/D推奨から一度作り、H2/H3へ共有しています。Cの大きさは2／3／2なので、`12 + 4×(2+3+2) = 40` 呼出しが今回の全予定です。最大48との差8は未入場の追加実験枠ではありません。

| 保存分母         | 実数と範囲                                                        |
| ---------------- | ----------------------------------------------------------------- |
| Search           | 40 unique、全40 COMPLETE／Exact、parent_restored=true             |
| 仕事             | 74,064 nodes、NNUE Searchのlogical評価36,975                      |
| 共通木           | 22,791＋467＋24,319＝47,577 visits、static評価47,567、terminal葉0 |
| parity           | 35状態＝3root＋32edge、追加logical評価131                         |
| logical NNUE合計 | 36,975＋47,567＋131＝84,673（上限25Mと区別）                      |
| 保存介入         | 23件。単独4件・同時3件でC内action変更、計7件。独立試行率ではない  |

非root途中nodeのrecorded legal数＝展開child数、全parent link／到達性、96,072個の保存backup値、6組のrank／tie、固定endpointと35parity pathの選択対応、23介入と新PVを照合し一致しました。合法手そのものをsolverで再生成した検査ではなく、既受入れsource／native入力admissionと今回の保存整合の範囲を分けます。

通常12callは全合法root、forced28callは同じ親Hにroot一手を含みchild H−1／ply1／full window、restricted root numeric TT=falseです。14個のD forced値は木とbit一致。Nは8/14がbit一致し、最大4 ULP／絶対2.3841858e−7の差があります。共通木のfull headとSearchのdelta経路をbit同一と決めつけません。短いSearch PVを欠けた葉まで補完し、static起源と呼ぶこともしません。

## 6組の候補順位

ここで示す値は**保存共通木のC内・親STM値**です。完全な有限horizon backupであり、真のgame WDLではありません。各候補の全値と通常／forced参照は [candidate-table.tsv](candidate-table.tsv)、全介入は [interventions.tsv](interventions.tsv) と [saved-analysis-result.json](saved-analysis-result.json) にあります。

| 親/H        | C          | NのC内選択・値  | DのC内選択・値  | 通常alllegal N / D      | 単独変更／対象葉 | 同時置換後のC内選択 |
| ----------- | ---------- | --------------- | --------------- | ----------------------- | ---------------- | ------------------- |
| slot4/11 H2 | 68,156     | 156 / +0.855743 | 68 / −0.379949  | 156 / 68                | 2 / 4            | 68                  |
| slot4/11 H3 | 68,156     | 156 / +0.959470 | 68 / −0.291313  | 156 / 68                | 0 / 4            | 156                 |
| slot4/39 H2 | 60,184,192 | 192 / +0.999947 | 184 / −0.800499 | 192 / 184               | 1 / 2            | 60                  |
| slot4/39 H3 | 60,184,192 | 60 / +0.999424  | 184 / −0.604368 | 60 / 184                | 1 / 4            | 192                 |
| slot5/12 H2 | 100,104    | 100 / −0.735160 | 100 / −0.291313 | **101 / 85（両方C外）** | 対象外           | 介入なし            |
| slot5/12 H3 | 100,104    | 104 / +0.875244 | 100 / −0.099668 | 104 / 100               | 0 / 4            | 104                 |

slot5/ply12のH2は通常Nが101・+0.340979、Dが85・−0.291313を選びます。C内の負値を全合法rootの結果へ読み替えません。原規則どおりCは追加していません。slot4/ply39 H2のDで184と192を分ける差は1 ULP（5.9604645e−8）しかなく、この厳密なFP32順序を頑健な数学的優劣とは呼びません。

## 主例：slot4/ply11 H2、葉[156,91]

[静的な候補・葉の図（SVG）](finite-leaf-example.svg)。原RAWは383 batch-002 gzip第1行、SHA `647ea66a…`／166,565 B（LF込み）。親の完全prefix11手とrootは固定入力の `distance-slot004-ply011`、STM=P1、在庫P0/P1=6/8です。

| C内の候補   | 保存N値                 | 保存D値      | 葉[156,91]だけ置換したN backup |
| ----------- | ----------------------- | ------------ | ------------------------------ |
| 68 = f8     | +0.270587772            | −0.379949003 | +0.270587772（C内選択）        |
| 156 = V(d2) | +0.855743170（C内選択） | −0.462117195 | −0.291312635                   |

対象は原result `$.trees[0].tree.nodes[12765]`、path `[156,91]`＝V(d2)→H(c2)。H2なので葉もP1視点です。正本viewのpre-tanhは **+1.277222633**、postは **+0.855743170**。同じ葉のD正本postは **−0.291312635**。raw距離入力はD/80の `[0.125,0.0874999985]`、canonical head内の標準化distance slotsは `[+0.396665901,−0.223517105]` です。baseline=0でも距離head入力は残り、logitをpostのatanhから推定していません。

この葉のlocal-STM postだけを保存D値へ置き、他の葉・候補・scale・tie規則を固定して**全応手を再backup**すると、C内選択は156→68へ変わります。これは「同じ有限木で、特定の葉の評価差が選択を支えていた」という具体的な依存を示します。別の固定葉 `[156,196]` 単独でもC内選択は68になります。

通常N H2の実PVも `[156,91]`、searched値は+0.855743110で、木とは1 ULP差です。ただしSearch/TTの数値起源全体はUNKNOWNのままです。また原対局の実応手は91ではなく **123**、実続行は `[156,123,203,…]` でした。この葉を実戦で踏んだ、原敗戦の唯一の原因だった、68なら勝てた、という証拠ではありません。介入後のC外root手を含むargmaxも未計算です。

### H3で同じ説明が尽きない理由

同じ親H3では、元のcanonical葉 `[156,193,207]` を置換すると、保存応手が `[156,193,140]`（node21614）へ変わります。この未置換葉はlocal N=−0.938093364／D=0、親視点N=+0.938093364です。固定4endpointを同時置換しても156の値は+0.938093364、68は+0.576767683で、C内の156が残ります。

slot5/ply12 H3も、元葉 `[104,149,87]` の置換後に `[104,149,110]`（node18767）へ移り、親N値+0.803020954が残ります。同時置換後の100は+0.627308011なので104が残りました。この2例は代替葉へのbackup切替が実際に保存されており、一つのPVを固定したままの説明を避ける必要があります。新PV末端の追加parity／forwardは行っておらず、その状態固有のfull/delta照合はUNKNOWNです。

## 低在庫の飽和と視点

slot4/ply39は原D5では192・+0.99928635でした。今回NはH2で192・+0.999947429、H3では60=g7・+0.999423683です。Dは両Hで184=V(h5)。旧D5と新H3を同じ仕事・内部状態として比較しません。

H3の固定葉 `[60,53,61]`（node141）はrootから3手後なのでSTM=P0、rootはP1です。local N=−0.999423683（pre=−4.075870037）、D=+0.800498962。これを同じlocal STMのまま置換してから符号をbackupすると、C内選択は60→192へ移ります。**D推奨184にはなりません。** 一部のD値置換と全木D評価は異なります。全endpoint同時置換でも192が残り、真の勝利や敗因を確定するものではありません。通常Searchの保存PVは `[60,53]` の2手です。ここでの3手pathは共通木のwitnessであり、欠けた実Search PVを補完したものではありません。

## full/delta・尺度・起源の確認と限界

original journalの `kind=bounded_parity` は第42／44／46行だけ一度stream decodeし、巨大common-tree行はdecodeしていません。保存記録は35状態すべて親復元exact、32edgeすべてfeatures／shape exact、FT/value alert 0です。post値bitsから32edgeの値誤差とalertを再計算し、記録と一致しました。post bit一致は21、最大値差2.3841858e−7。最大FT誤差7.6293945e−6はproducerの記録で、未保存の全FT配列から独立再計算したものではありません。bit一致と許容誤差内を区別し、tree frontierの対応するfull head値／pre-tanh bitsは一致しました。

今回の追跡範囲で供給・復元破損を示すalertはありません。しかし全状態の無欠陥、実Searchの全物理FT/head回数、旧warm TTの再現を証明した検査ではありません。Search logical評価、diagnostic full=47,634／delta=32／head=47,698は異なる単位で、重複して仕事や費用へ足しません。TT保持83,886,128 Bは各sessionのbody gaugeでありRSSではありません。

3木の全葉は非terminalです。負のheuristicやtanhの±1近傍を確定負け／勝ちとせず、「全Cが既に負けていた」も未判定です。原383のNNUE完成深さ3／5／3との接続は、初期の2親（slot4/11・slot5/12）で新N H3が原着手・PVに対応し、低在庫親ではhorizon依存を確認できた範囲に限ります。新cold TT1M・現行source・no timeと旧持続状態・95ms・TT4Kは同一ではありません。

## 引渡す最小の次の問い

1. Rootが重要な局所機序として採用する場合だけ、別の既存Sol担当へ主例の元node・介入・C範囲に限定した独立確認を渡せます。本分析者は設計者本人なので、その独立レビューとは兼用しません。
2. 別枠420向けに、単独置換でC内選択が変わった既存4endpointだけを [existing-endpoint-input-support.json](existing-endpoint-input-support.json) へ付記しました。完全prefix／原tree pointer／parity行参照付きで、補充・新root・新forwardは0です。補助評価が正解になるという前提もありません。
3. H3で残った代替応手群の評価差、有限horizon、原実続行との差は競合する未解決点です。今回の23介入で不足した部分を、単一葉の修正で解決したとは扱わず、追加Search／対局／model変更を自動発行しません。

## 版・費用・停止

original software outerはFAILED v4=9.967235303、v5=18.954639776、v7=9.388188455、PASS v8=134.336477404秒、合計172.646540938秒。原numerical outer FAILED=6.942283608秒を一度だけ数えると、既知outerの和は179.588824546秒です。native内部1.625379838秒、保存resultのpublication前1.477589097秒は内包され、加算しません。全source／LLM／controller／保存解析／金銭費とcontinuous family RSSはUNKNOWNです。

原result `12032a29…`、journal `8c6363aa…`、native receipt `bd9e7ce4…`、Root collection `b4af1049…` と固定spec/inputは前後SHA-size-modeで保持しました。原failed manifest `ccfa8f0a…` はRoot collectionに束縛されたFileRefを参照し、本解析でpayload再読や再finalizeはしていません。詳細は解析completion／selectedrefs／実STOPへ束縛します。private成果のformatter/lint・保存整合を確認後、本人419.1だけverify／close／backupし、current324へ一度返します。

この解析はsource・runtimeを変更せず、原FAILED／NULLとdisk masks／stdout欠損／旧費UNKNOWNを保持します。mixed/learner全prep-pipeline、323 USERPAUSE、製品generator default OFF、models/weights/seals/oldfits96、foreign変更、414未発行は不変です。
