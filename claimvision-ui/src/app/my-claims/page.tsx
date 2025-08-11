import { Suspense } from 'react';
import MyClaimsClient from './MyClaimsClient';

export default function Page() {
  return (
    <Suspense fallback={<div>Loading…</div>}>
      <MyClaimsClient />
    </Suspense>
  );
}
