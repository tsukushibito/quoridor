use quoridor_core::{Position, research::SigmaContext};
use quoridor_nnue::{DistanceFit, EvaluationMode, Features, Model, Topology, encode_qf1};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{
    fs,
    path::PathBuf,
    process::Command,
    sync::atomic::{AtomicU64, Ordering},
};
static SEQ: AtomicU64 = AtomicU64::new(0);
fn tmp() -> PathBuf {
    let p = std::env::temp_dir().join(format!(
        "quoridor-nnue-test-{}-{}",
        std::process::id(),
        SEQ.fetch_add(1, Ordering::Relaxed)
    ));
    fs::create_dir(&p).unwrap();
    p
}
fn weights(t: Topology) -> Vec<f32> {
    (0..t.parameter_count().unwrap())
        .map(|i| (((i * 73 + 19) % 101) as f32 - 50.) / 1024.)
        .collect()
}
fn model(t: Topology) -> Model {
    Model::from_parts(
        t,
        weights(t),
        [0.08, 0.09],
        [0.05, 0.06],
        DistanceFit { a: 0.01, b: 7. },
    )
    .unwrap()
}
fn export(p: &std::path::Path, w: &[f32]) {
    let bytes: Vec<u8> = w.iter().flat_map(|v| v.to_le_bytes()).collect();
    fs::write(p.join("weights.f32"), &bytes).unwrap();
    fs::write(p.join("model.json"),serde_json::to_vec(&json!({"feature":"QF1-f32-STM-scaled-v1","weights":"weights.f32","weights_SHA":format!("{:x}",Sha256::digest(&bytes)),"weights_B":bytes.len(),"little_endian_f32":w.len(),"mu_f32":[0.08f32,0.09f32],"sigma_f32":[0.05f32,0.06f32],"distance_fit":{"a":0.01f32,"b":7.0}})).unwrap()).unwrap();
}
#[test]
fn native_qf1_matches_javascript_full_delta_all_legal_children() {
    let t = Topology::default();
    let w = weights(t);
    let p = tmp();
    export(&p, &w);
    let m = Model::load(p.join("model.json")).unwrap();
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let script = r#"const n=require(process.argv[1]+'/tools/ai-sigma-native/nnue.cjs');const m=n.load(process.argv[2]);let out=[];for(const prefix of [[],[81,163],[13,67,22,58,31,49,40,31],[13,67,22,58,31,49,40,108]]){let s=n.q.r.fromPrefix([]);for(let id of prefix){let a=s.getLegalActions().find(a=>n.q.r.rustAction(s,a)===id);if(!a)throw Error('fixture illegal '+id);s=s.next(a);}const full=n.q.full(s,m.w);let row={prefix,ids:full.ids,distance:full.distance,side:full.side-1,value:n.valueScaled(full,m.w,m.m),children:[]};for(const action of s.getLegalActions()){const id=n.q.r.rustAction(s,action);const child=s.next(action),d=n.q.delta(full,child,m.w);row.children.push({id,ids:d.ids,distance:d.distance,side:d.side-1,value:n.valueScaled(d,m.w,m.m)});}out.push(row);}console.log(JSON.stringify(out));"#;
    let out = Command::new("node")
        .arg("-e")
        .arg(script)
        .arg(&repo)
        .arg(p.join("model.json"))
        .output()
        .unwrap();
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let rows: serde_json::Value = serde_json::from_slice(&out.stdout).unwrap();
    for row in rows.as_array().unwrap() {
        let prefix: Vec<u16> = serde_json::from_value(row["prefix"].clone()).unwrap();
        let c = SigmaContext::from_prefix(&prefix).unwrap();
        let a = m.full(c.position()).unwrap();
        let check = |a: &quoridor_nnue::Accumulator, r: &serde_json::Value| {
            let ids: [Vec<u16>; 2] = serde_json::from_value(r["ids"].clone()).unwrap();
            assert_eq!(a.features.ids, ids);
            assert_eq!(a.features.side, r["side"].as_u64().unwrap() as u8);
            for i in 0..2 {
                assert_eq!(
                    a.features.distance[i],
                    r["distance"][i].as_f64().unwrap() as f32
                );
            }
            assert!(
                (m.evaluate(a).unwrap() - r["value"].as_f64().unwrap() as f32).abs() <= 1e-6,
                "prefix {prefix:?}"
            );
        };
        check(&a, row);
        let parent_bits: Vec<u32> = a.values.iter().flatten().map(|v| v.to_bits()).collect();
        let simd = m.full_mode(c.position(), EvaluationMode::Simd).unwrap();
        assert_eq!(
            m.evaluate(&a).unwrap().to_bits(),
            m.evaluate(&simd).unwrap().to_bits()
        );
        let legal: Vec<u16> = row["children"]
            .as_array()
            .unwrap()
            .iter()
            .map(|r| r["id"].as_u64().unwrap() as u16)
            .collect();
        let mut expected = c.legal_ids();
        expected.sort_unstable();
        let mut actual = legal.clone();
        actual.sort_unstable();
        assert_eq!(expected, actual);
        for r in row["children"].as_array().unwrap() {
            let child = c.play(r["id"].as_u64().unwrap() as u16).unwrap();
            let d = m.delta(&a, child.position()).unwrap();
            check(&d, r);
            let full = m.full(child.position()).unwrap();
            assert!((m.evaluate(&d).unwrap() - m.evaluate(&full).unwrap()).abs() < 1e-5);
            let ds = m.delta(&simd, child.position()).unwrap();
            assert_eq!(
                m.evaluate(&d).unwrap().to_bits(),
                m.evaluate(&ds).unwrap().to_bits()
            );
        }
        assert_eq!(
            parent_bits,
            a.values
                .iter()
                .flatten()
                .map(|v| v.to_bits())
                .collect::<Vec<_>>()
        );
    }
    fs::remove_dir_all(p).unwrap();
}
#[test]
fn scalable_topology_and_quantized_roundtrip_checked_overflow() {
    let m = model(Topology {
        ft_width: 19,
        hidden_width: 11,
    });
    let c = SigmaContext::from_prefix(&[81, 163, 13]).unwrap();
    let full = m.full(c.position()).unwrap();
    assert!(m.evaluate(&full).unwrap().is_finite());
    let q = m.quantize().unwrap();
    let a = q.full(c.position()).unwrap();
    assert!((q.evaluate(&a).unwrap() - m.evaluate(&full).unwrap()).abs() < 0.002);
    for action in c.legal_ids() {
        let p = c.play(action).unwrap().position();
        let d = q.delta(&a, p).unwrap();
        let f = q.full(p).unwrap();
        assert_eq!(d.values, f.values);
        assert_eq!(
            q.evaluate(&d).unwrap().to_bits(),
            q.evaluate(&f).unwrap().to_bits()
        );
    }
    let p = tmp();
    q.save(p.join("quant.json")).unwrap();
    let loaded = quoridor_nnue::QuantizedModel::load(p.join("quant.json")).unwrap();
    assert_eq!(
        loaded
            .evaluate(&loaded.full(c.position()).unwrap())
            .unwrap()
            .to_bits(),
        q.evaluate(&a).unwrap().to_bits()
    );
    let mut corrupt = fs::read(p.join("quant.i16")).unwrap();
    corrupt[3] ^= 1;
    fs::write(p.join("quant.i16"), corrupt).unwrap();
    assert!(quoridor_nnue::QuantizedModel::load(p.join("quant.json")).is_err());
    // Explicit checked addition rather than wrap if an accumulator is corrupted.
    let mut bad = a.clone();
    bad.values[0].fill(i64::MAX);
    let changed = c.play(c.legal_ids()[0]).unwrap();
    assert!(q.delta(&bad, changed.position()).is_err());
    fs::remove_dir_all(p).unwrap();
}
#[test]
fn manifest_rejects_hash_shape_nonfinite_and_foreign_accumulator() {
    let p = tmp();
    let w = weights(Topology::default());
    export(&p, &w);
    let m = Model::load(p.join("model.json")).unwrap();
    let mut bytes = fs::read(p.join("weights.f32")).unwrap();
    bytes[0] ^= 1;
    fs::write(p.join("weights.f32"), &bytes).unwrap();
    assert!(Model::load(p.join("model.json")).is_err());
    let mut bad = w.clone();
    bad[0] = f32::NAN;
    assert!(
        Model::from_parts(
            Topology::default(),
            bad,
            [0.; 2],
            [1.; 2],
            DistanceFit::default()
        )
        .is_err()
    );
    let mut foreign_weights = w.clone();
    foreign_weights[3] += 0.01;
    let foreign = Model::from_parts(
        Topology::default(),
        foreign_weights,
        [0.08, 0.09],
        [0.05, 0.06],
        DistanceFit::default(),
    )
    .unwrap();
    assert!(
        foreign
            .evaluate(&m.full(Position::default()).unwrap())
            .is_err()
    );
    let f = Features {
        ids: [vec![2, 2], vec![1]],
        distance: [0.1, 0.1],
        side: 0,
    };
    assert!(m.full_features(f, EvaluationMode::Scalar).is_err());
    assert!(
        Model::from_parts(
            Topology {
                ft_width: 0,
                hidden_width: 4
            },
            vec![],
            [0.; 2],
            [1.; 2],
            DistanceFit::default()
        )
        .is_err()
    );
    let features = encode_qf1(Position::default()).unwrap();
    assert_eq!(features.ids[0], [4, 157, 300, 311]);
    assert_eq!(features.ids[1], [4, 157, 300, 311]);
    fs::remove_dir_all(p).unwrap();
}

#[test]
fn browser_bytes_loader_and_scalable_manifest_share_validation() {
    let p = tmp();
    let t = Topology {
        ft_width: 17,
        hidden_width: 9,
    };
    let w = weights(t);
    let bytes: Vec<u8> = w.iter().flat_map(|v| v.to_le_bytes()).collect();
    let m = json!({"feature":"QF1-f32-STM-scaled-v2","value_perspective":"side-to-move","topology":{"ft_width":17,"hidden_width":9},"weights":"model.f32","weights_SHA":format!("{:x}",Sha256::digest(&bytes)),"weights_B":bytes.len(),"little_endian_f32":w.len(),"mu_f32":[0.,0.],"sigma_f32":[1.,1.]});
    let raw = serde_json::to_vec(&m).unwrap();
    fs::write(p.join("model.f32"), &bytes).unwrap();
    fs::write(p.join("model.json"), &raw).unwrap();
    let native = Model::load(p.join("model.json")).unwrap();
    let browser = Model::load_bytes(&raw, &bytes).unwrap();
    assert_eq!(native.fingerprint(), browser.fingerprint());
    assert_eq!(browser.topology(), t);
    // Python's json encoder expands numpy.float32 scalers to exact f64
    // decimals. Parsing those decimals must preserve the original f32 value;
    // serde_json's faster default parser can shift the f64 by one ULP.
    let mut exported = m.clone();
    exported["mu_f32"] = serde_json::from_str("[0.105157770216465,0.10060679912567139]").unwrap();
    exported["sigma_f32"] =
        serde_json::from_str("[0.05424855649471283,0.05288631096482277]").unwrap();
    assert!(Model::load_bytes(&serde_json::to_vec(&exported).unwrap(), &bytes).is_ok());
    let mut bad = m.clone();
    bad["mu_f32"][0] = json!(0.1f64);
    assert!(Model::load_bytes(&serde_json::to_vec(&bad).unwrap(), &bytes).is_err());
    let mut bad = m.clone();
    bad["topology"]["ft_width"] = json!(18);
    assert!(Model::load_bytes(&serde_json::to_vec(&bad).unwrap(), &bytes).is_err());
    fs::remove_dir_all(p).unwrap();
}

#[test]
#[ignore = "requires QUORIDOR_TORCH_PYTHON pointing to pinned PyTorch environment"]
fn actual_pytorch_float_model_matches_rust_scalable_input() {
    let python = std::env::var("QUORIDOR_TORCH_PYTHON").expect("set QUORIDOR_TORCH_PYTHON");
    let m = model(Topology::default());
    let p = tmp();
    export(&p, m.weights());
    let mut rows = Vec::new();
    for prefix in [vec![], vec![81, 163], vec![13, 67, 22, 58, 31, 49, 40, 31]] {
        let c = SigmaContext::from_prefix(&prefix).unwrap();
        let a = m.full(c.position()).unwrap();
        rows.push(json!({"ids":a.features.ids,"distance":a.features.distance,"side":a.features.side,"rust":m.evaluate(&a).unwrap()}));
    }
    fs::write(p.join("rows.json"), serde_json::to_vec(&rows).unwrap()).unwrap();
    let script = r#"import sys,json,torch,struct
from pathlib import Path
torch.set_num_threads(1)
p=Path(sys.argv[1]); m=json.loads((p/'model.json').read_text()); w=torch.tensor(struct.unpack('<12193f',(p/'weights.f32').read_bytes()),dtype=torch.float32)
W=w[:9984].reshape(32,312);b=w[9984:10016];H=w[10016:12128].reshape(32,66);hb=w[12128:12160];O=w[12160:12192];ob=w[12192]
rows=json.loads((p/'rows.json').read_text());out=[]
with torch.inference_mode():
 for r in rows:
  features=torch.zeros(2,312,dtype=torch.float32)
  for side in range(2): features[side,r['ids'][side]]=1
  a=torch.relu(features@W.T+b);s=r['side'];d=(torch.tensor(r['distance'])-torch.tensor(m['mu_f32']))/torch.tensor(m['sigma_f32']);x=torch.cat((a[s],a[1-s],d));v=torch.tanh(torch.relu(H@x+hb)@O+ob);out.append(float(v))
print(json.dumps(out))"#;
    let out = Command::new(python)
        .args(["-c", script])
        .arg(&p)
        .env("OMP_NUM_THREADS", "1")
        .env("MKL_NUM_THREADS", "1")
        .output()
        .unwrap();
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let values: Vec<f32> = serde_json::from_slice(&out.stdout).unwrap();
    for (v, r) in values.iter().zip(&rows) {
        assert!((*v - r["rust"].as_f64().unwrap() as f32).abs() < 1e-5);
    }
    fs::remove_dir_all(p).unwrap();
}
