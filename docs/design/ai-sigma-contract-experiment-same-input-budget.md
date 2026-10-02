# SIGMA-SAME-INPUT-BUDGET / quoridor-4lc.126 / 契約1・枠8

coordinator→既experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746単独writer。125の有限FPU感度を受入れたが、candidate FPUは未採用。ユーザーCPU Sigma比較継続と枠8内の通常配分。ready/show goal+self・pauseなし/本人担当確認後本課題だけclaim、全文受領・実開始を報告。同saved/model/effort/cwd。旧123/125/119のsource・結果・期限を変更しない。

## 問いと判断を変える出口
119の敗戦は完成手なし/late/責任lossではない。123/125で未訪問Qだけの参照変更は候補への距離を混在方向に変え、A/Bの最終Actionは5入力全て同じだった。規則の類似だけを改善目標にせず、現政策固定で同じ入力と採用時間を与えたとき、採用可能な完成評価量と初回準備費がどの程度異なるかを測る。異なる対局軌跡のNN中央値では判別できないため、同入力・順序反転の少数診断へ移す。

125の保存敗戦根NN0案は部分採用し、先に119の該当初期根の入力対応/初回CP/採用量/自己waitを必要8根だけ確認する。追加実測はその同入力対照であり、全棋譜・全rootを再検算しない。原情報欠測は補完せず、新計測と分ける。

4入力の各反復で候補の採用completed量が一貫して小さい傾向なら政策固定の準備/throughput案を優先する。順序/入力で優劣が逆転する、同量でもAction差が残る、又は必要量が取れなければ単一費用原因と断定せず、戦術/終端尺度や深部規則の必要最小対照へ移す。これは記述的な選定分岐で統計的因果や119全敗因の証明ではない。自動C/FPU調整はしない。結果で次の判断が変わらない見込みがあれば、追加NNを増やす前に不足を報告する。

## 固定入力・測定条件
119のAI前固定prefix-document SHA c8104df06585717c54900e02afcf62a9133a91fdfc2a25732da38dcc7b286e27から登録順prefix1,2,3,7を採用する。119で参照が両色勝った例の事後選定であり、代表標本/均衡/IID/holdoutではない。各prefixの元board/side/history/生成seedをそのまま使う。結果後の入力補充/差替えなし。探索seed1979、候補immutableC1.5/固定Sigma、モデル/ORT1.21.0 CPU/Wasm/係数/FPU/order/tie/finish/caps変更0。

受入れ112/119の専用2Worker・各model/session/SAB/generation/control、browser mainの時計/合法性/採用・数値/結果、Node外側起動監視回収終了後保存を維持。モデル2sessionを保持、重み毎回転送0。各探索は新世代・新tree/context、tree/history検索cache再利用0（入力履歴は指定の同bytes）。先読みなし。

startup固定gate6は別分母。prefix1で候補→参照のwarm要求各1（計2、steadyと別）。steadyはprefix順1,2,3,7、各4要求で各engine2回、順序は第1/3入力C→R→R→C、第2/4入力R→C→C→R。steady16＋warm2＝最大18要求、追加機能要求/対局0。結果前に入力・順序・全条件SHA/configを固定。successful要求の好成績再試行置換なし。非成立/取消/fault/late/初回無し・未実施も全分母へ保持。

T500/cutoff402/adopt411/bounded readを維持。通常採用はNN/ACKを待たない。今回の孤立した入力費用診断では各要求の後に両Workerの旧zeroを確認して次要求へ進み、意図的に残NNと次探索のCPU重なりを除く。これは実対局の相手t0旧ACK非前提を変更する実装ではない。採用/旧返却discard/新仕事抑止・自旧回収を維持し、通常2Worker対局の公平性へ外挿しない。

first completed CP、初回API await、root準備の保存可能なspan、adopt予定/実時刻・完成CP sequence、採用時のcompleted backup/rootN/sim/edge和/NN開始と終了・terminal-noNN・discard・自己wait、public Action/合法性、ACK/stopを分ける。候補/参照のroot展開計数規約は明記し、同rootNを同仕事量/CPUに変換しない。API awaitを純NN/kernel時刻とせず、重いper-step instrumentationを締切経路へ追加しない。既取得可能なCP統計と軽いmarkerを利用し、欠測を0補完しない。既詳細CPは採用/zero後にbrowser内で検査する。

同入力features648/rootNN137・priorの対応を両engineで確認し、fixed参照の無いprefixは自己整合/両engine一致までで一般NN一致を主張しない。最大8 steady根（各入力両engine最初）を結果前選定。start/end Workerclock区間を保存、途中drift・exactAtomicstore・内核CPU・硬いOS保証は未確認。旧WDLやK32 wrapper費用と統合しない。正式NI/Sigma同等/係数採用/actual_go0。

## 所有・普通のデバッグ
自己write tools/ai-sigma-same-input-budget/、.artifacts/ai-sigma/resume-20261002/SAME-INPUT-BUDGET/、research-data/ai-sigma/126-same-input-budget/、docs/reports/ai-sigma-experiment-same-input-budget.md。既glue/runnerの必要readonly importと小差分のみ。原119/123/125/kernel/model/common/roles/registry/92/default Git index編集0、新build/依存取得/GPU/学習/製品統合/push0。

安いschema/入力/順序/計数と構文/mockを先行し、許可された自己glue修正は同課題・総予算で反復可。故障を棋力やNN不一致へ変換せず元run/失敗を保持。起動直前にproc/exe+argvとreaderror/未知owner拒否・自己旧回収/外heavy/headroom/保存forecastを確認し、helper失敗後のlaunch0を必須分岐にする。125 Chrome停止現物と現在identityを確認して重jobは直列に行う。LLM active数を拒否理由にしない。

## 配分・期限・引渡し
静的CPU0/RAM1guard896MiB、各60秒/累計180秒。全Chrome NN0もCPU[2]単logical、ORT各1thread、2session込みRAM6GiB currentRSS guard5.5GiB、親CPU4/RAM8内。他heavy停止。各browser120秒・各要求timeout20秒・累計heavy240秒（初期化/warm/失敗も含む）。自己保存64MiB guard56MiBは既experiment entry内、親12GiB追加予約0。現在保持/Git/temp/圧縮peak確認、共有/他owner物削除0。旧保持/未確認量は保守的に残す。

処理は受領20分又は14:00UTC、新runは受領17分又は13:57、提出は受領30分又は14:10の早い方。親14:05:49新重job停止/14:10:49監督/14:13:49monitor/14:15:49終了は不変。余裕不足なら最大18未実施を明記して停止する。別契約で期限迂回0。

停止前にModel2/search/main timer/message/monitorcallback・innercontrolledとouter同identitywait/remainingunknownを分けて保存。source/runtime-stop/hashafterと必要版/Git/input/run/command/resources/全要求/失敗・保存archive復元/短報告を固定、Beads backup→coordinator。現在不在を自然終了/全期間証明にしない。必要独立確認は主張と残時間で統括が停止版へ選び、新承認層/全copy/毎run契約を追加しない。
