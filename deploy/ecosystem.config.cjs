// Elcaro Miner — PM2 ecosystem config
// Start: pm2 start deploy/ecosystem.config.cjs
// From:  /home/linuxuser/elcaro/

module.exports = {
  apps: [
    {
      name: "elcaro-miner",
      script: ".venv/bin/uvicorn",
      args: "miner.api:app --host 127.0.0.1 --port 8848",
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
