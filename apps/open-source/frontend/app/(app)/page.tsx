import { headers } from 'next/headers';
import { App } from '@/components/app';
import { getAppConfig } from '@/lib/utils';

export default async function Page() {
  const hdrs = await headers();
  const appConfig = await getAppConfig(hdrs);

  // Correctly read the environment variables on the server side
  const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  return <App appConfig={appConfig} livekitUrl={livekitUrl} apiUrl={apiUrl} />;
}