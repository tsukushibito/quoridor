'use strict';
const fs=require('fs'),path=require('path'),Module=require('module'),crypto=require('crypto');
// Thin guard over the stopped165 engine; original bytes are never rewritten.
const file=path.resolve(__dirname,'../ai-sigma-native-baseline/engine.cjs'),original=fs.readFileSync(file,'utf8');
const binding=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../research-data/ai-sigma/173-native-ni-arena/binding.json')));
if(crypto.createHash('sha256').update(original).digest('hex')!==binding.engine_source_SHA256)throw Error('SOURCE_BINDING');
const needle="if(stopped)throw Error('guard');const t=now();let n;";if(!original.includes(needle))throw Error('GUARD_PATCH_SOURCE');
const source=original.replace(needle,"if(stopped)throw Error('guard');if(!q.mock&&count>=(q.NN_limit??0))throw Error('NN_BUDGET');const t=now();let n;");
const m=new Module(file,module);m.filename=file;m.paths=Module._nodeModulePaths(path.dirname(file));m._compile(source,file);
