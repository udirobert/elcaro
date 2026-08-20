// Elcaro Miner — PM2 ecosystem config
// Start: pm2 start deploy/ecosystem.config.cjs
// From:  /home/linuxuser/elcaro/

module.exports = {
  apps: [
    {
      name: "elcaro-miner",
      script: ".venv/bin/uvicorn",
      // Binds 0.0.0.0 so Coolify's Traefik container can reach the miner via
      // host.docker.internal. Public exposure is prevented by ufw: port 8848 is
      // only allowed from 10.0.0.0/8 (the Docker bridge networks).
      args: "miner.api:app --host 0.0.0.0 --port 8848",
      cwd: "/home/linuxuser/elcaro",
      interpreter: "none",
      env: {
        PORT: "8848",
        PYTHONUNBUFFERED: "1",
      },
      // Restart policy
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      // Logging
      error_file: "/home/linuxuser/.pm2/logs/elcaro-miner-error.log",
      out_file: "/home/linuxuser/.pm2/logs/elcaro-miner-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      // Resource limits
      max_memory_restart: "512M",
    },
  ],
};
