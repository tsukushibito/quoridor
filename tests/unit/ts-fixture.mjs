import { readFileSync } from 'node:fs';
import { stripTypeScriptTypes } from 'node:module';
import vm from 'node:vm';

// Transform only the requested source in memory using the installed Node runtime.
// Every runtime import must be an explicit fixture port; Wasm, renderers and
// scientific runtimes cannot load through this linker.
export async function loadTs(url, imports, globals = {}) {
  const context = vm.createContext({
    performance,
    setTimeout,
    clearTimeout,
    console,
    URL,
    Uint8Array,
    TextDecoder,
    ...globals,
  });
  const compiled = stripTypeScriptTypes(readFileSync(url, 'utf8'), {
    mode: 'transform',
    sourceUrl: url.href,
  });
  const module = new vm.SourceTextModule(compiled, {
    context,
    identifier: url.href,
    initializeImportMeta: (meta) => {
      meta.url = url.href;
    },
  });
  await module.link((name) => {
    if (!Object.hasOwn(imports, name)) throw Error(`Blocked runtime import: ${name}`);
    const port = imports[name],
      names = Object.keys(port);
    return new vm.SyntheticModule(
      names,
      function () {
        for (const key of names) this.setExport(key, port[key]);
      },
      { context },
    );
  });
  await module.evaluate();
  return module.namespace;
}
