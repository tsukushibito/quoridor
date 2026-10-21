// Browser bytes only. Rust owns the key, envelope validation and save eligibility.
export type StoragePort = Pick<Storage, 'getItem' | 'setItem'>;
export function createRepository(storage: () => StoragePort) {
  return {
    read(key: string): string | null {
      return storage().getItem(key);
    },
    write(key: string, raw: string): void {
      storage().setItem(key, raw);
    },
  };
}
export type Repository = ReturnType<typeof createRepository>;
