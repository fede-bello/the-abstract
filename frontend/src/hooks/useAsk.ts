import useSWRMutation from 'swr/mutation';

import { getClient } from '@/data/client';
import type { AskResponse, AskScope } from '@/data/types';

interface AskArg {
  question: string;
  scope: AskScope;
}

/** Fire-on-submit Q&A. Dummy for now (canned answers); same shape as the future RAG endpoint. */
export function useAsk() {
  return useSWRMutation<AskResponse, Error, 'ask', AskArg>('ask', (_key, { arg }) =>
    getClient().askDummy(arg.question, arg.scope),
  );
}
