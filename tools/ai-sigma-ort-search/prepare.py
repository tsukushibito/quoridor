from pathlib import Path
p=Path('src/kernel.rs');s=p.read_text().replace('pub mod research;','#[path = "research.rs"]\npub mod research;')
start=s.index('        let value = if output.value.is_finite()',s.index('    fn expand('))
end=s.index('    fn simulate(',start)
body=s[start:end];s=s[:start]+'        self.expand_output(index, legal, output)\n    }\n    fn expand_output(&mut self, index:usize, legal:Vec<u16>, output:Evaluation)->f32 {\n'+body+s[end:]
p.write_text(s)
