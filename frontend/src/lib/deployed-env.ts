const DEPLOYED = new Set(['production', 'prod', 'staging']);

/** True for any environment a real user can reach, staging included. Mirrors backend is_deployed_env. */
export function isDeployedEnv(env: NodeJS.ProcessEnv = process.env): boolean {
  return [env.ENVIRONMENT, env.NODE_ENV, env.NEXT_PUBLIC_ENVIRONMENT].some((m) =>
    DEPLOYED.has((m ?? '').toLowerCase()),
  );
}
