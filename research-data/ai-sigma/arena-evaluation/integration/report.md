# 棋力評価環境の統合

停止版14pathのarena/book/history・受理時計・pair集計・来歴manifest・audit/recoveryをmainのrunnerへ統合した。開始prefixは合法手の全履歴を保持し、同じprefixを色交換2slotへ配分する。NNUE重みや探索数学は変更しない。学習教師のdatasetはarenaで生成しない。

運用小試験はD/D一手ゴール2slotと事前pause2slot。最初の2対局は正常終了しP1が双方勝ち、完全pair score .5。検証guardの「履歴長1」assertionが、14prefix+実着手1=15を誤認して最初のjobは失敗となった。原費/失敗を保存し、対局は繰り返さず、第二cancel jobで保存済みsmokeをaudit/recoverした。取消2slotは未開始・typedcancelled/unknownで、引分けへ変換しない。全4予定slot、started2/completed2/unknown2、completepair1/incompletepair1。全予定分母のscore範囲[.25,.75]は精度区間やEloではない。一pairのbootstrap CIは出さない。

両runのaudit/recoverがPASS。取消時のdurable journal復元not_started2と、最終resultのcancelled2を区別する。全子のdirect wait、cleanup/remaining空と記録PID/start不在を確認した。Native7.447060秒/180・2job/4slotを消費し、元software394.955721秒+prep上界15、初回guard失敗を含む旧費/UNKNOWNを保持する。新推論/モデル/対局増量はない。

時計は暫定strict_unknown。返却後・全履歴合法検査後の受理を測り、内部完成反復のtimestampや硬い返却保証を持たない。forfeit・公平な実棋力・Elo・同時間Sigma・探索二版adapterは未認定/未実装。100/500ms presetは次の調整用で今回未実行。

Rootは停止版source SHAを照合し、mainへ学習コードと組み合わせて限定data3/manifest2/arena9/config3/nativeundo1、release build/Clippyを確認した。主な運用入口は[runner手順](../../../../crates/quoridor-runner/README.md)と[preset案内](../../../../configs/arena/README.md)。実運用・全失敗/停止/来歴とraw小証拠は[evidence.tar.gz](evidence.tar.gz)、復元SHAは[verification.json](verification.json)。モデル/比較ELF・旧WT・科学資産は削除・複製しない。
