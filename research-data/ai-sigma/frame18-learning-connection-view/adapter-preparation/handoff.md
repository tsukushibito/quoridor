# 227 phase2 preparation handoff

Source API: `tools/ai-sigma-frame18-learning/manifest_adapter.py`.
CLI (future authorized label-free data only):

    /usr/bin/python3 -B tools/ai-sigma-frame18-learning/manifest_adapter.py --plan PLAN.json --metadata LABEL_FREE.jsonl.gz --out NEW_IMMUTABLE_DIR

Plan: kind QF1-dynamic-plan; games: game_id/family/split/cohort/expected_rows, train_slot for train. stages: increasing family counts ending at maximum, e.g. [192,576]. Sibling families share partition, cohort, train_slot. Explicit source_split only for new-manifest aliases, never edit old dataset. Owner row counts required; no inferred missing rows. Source IDs/history/state retained. canonical distances already STM ordered.

Optional training_labels_advertised={path,sha256}; prep never opens it. Actual training requires later owner authorization and `loader.load_training_stage(path)`; test label artifacts forbidden. No-advertisement manifests are QF1-stage-preparation; advertisement stage manifests retain training_ready=false until authorized verification. Fixed maximum OR-mask hash is shared by all stage manifests. Zero-row and zeroeligible planned families remain in denominators.

configuration(train_rows,val_rows,scale_path,scale_SHA) returns shared-supported config plus separate private settings. Dense early points and initial-function preserving scale adapter remain a future thin runner integration; shared CLI is interval/raw-distance. No real NN or label evaluation occurred here. Synthetic fixture32 PASS/expected rejection; immutable current code version in source-freeze.json. Real dataset owner must qualify actual row identities/labels/view before learning. Model parity/sample costs belong future concrete contract.

Proposal only: saved new96 train alias + fresh480train/96val/96test=672; nestedtrain192/576. Gen7*96 known35.3min+unknown, planned50–75min total. CPU learning2*120s; 14point sample formula and freeze-before-one-test per report. Dataset512MiB+learner32MiB is an unallocated plan, not current permission. Current227 scope4MiB/guard3/forecast2 unchanged; no parent increment.

Fixture: r1 NOT_STARTED_ADMISSION (runtimefield), repaired r2 CPU0 start11:08:07.065029/end11:08:07.157659, child83457/tick36506838 wait/currentexact0. Source ready for readonly use after stop/hash. NN/model/train/test/GPU0. No mainmirror/sharedtrainer changes.
