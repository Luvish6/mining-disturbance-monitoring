import {useEffect, useState} from 'react';

export const localSnapshot = import.meta.env.BASE_URL+'local/';

export function useSnapshot<T>(key: string) {
  const [result, setResult] = useState<{data: T; sha256: string}>();
  const [failed, setFailed] = useState(false);
  useEffect(()=>{
    const controller = new AbortController();
    fetch(localSnapshot+key+'.json',{signal:controller.signal})
      .then(response=>{if(!response.ok) throw Error('Unavailable'); return response.json();})
      .then(payload=>setResult(payload))
      .catch(()=>{if(!controller.signal.aborted) setFailed(true);});
    return ()=>controller.abort();
  },[key]);
  return {result, failed};
}
