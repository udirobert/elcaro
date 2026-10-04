import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    // Former top-level demo routes consolidated under the /evaluate route
    // family. Temporary redirects so they can move again without fighting
    // cached 308s; request query strings are preserved onto the destination.
    return [
      {
        source: "/evaluate",
        destination: "/evaluate/gauntlet",
        permanent: false,
      },
      {
        source: "/gauntlet",
        destination: "/evaluate/gauntlet",
        permanent: false,
      },
      {
        source: "/redteam",
        destination: "/evaluate/redteam",
        permanent: false,
      },
      {
        source: "/vulnerable",
        destination: "/evaluate/audit",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
