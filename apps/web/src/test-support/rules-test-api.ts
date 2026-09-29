import { AiClient, RulesClient } from '@quoridor/engine-bridge';
import { RulesGame } from '../../../../packages/engine-bridge/wasm/rules/quoridor_rules.js';

declare global {
  interface Window {
    __QUORIDOR_RULES_TEST_API__?: {
      createGame: typeof RulesClient.createGame;
      validateSearchSnapshot: typeof RulesClient.validateSearchSnapshot;
      RawRulesGame: typeof RulesGame;
      AiClient: typeof AiClient;
    };
  }
}

window.__QUORIDOR_RULES_TEST_API__ = {
  createGame: RulesClient.createGame,
  validateSearchSnapshot: RulesClient.validateSearchSnapshot,
  RawRulesGame: RulesGame,
  AiClient,
};
