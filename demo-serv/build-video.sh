#!/usr/bin/env bash
# Build the SERV Hackathon Edition 01 demo video from the 4 rendered frames.
# Uses ffmpeg to sequence frames with crossfade transitions.
#
# Output: demo-serv/elcaro-serv-hackathon-edition-01.mp4
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
FRAMES="$DIR/frames"
CLIPS="$DIR/clips"
OUT="$DIR"

mkdir -p "$CLIPS"

DUR_PER_FRAME=5  # seconds per slide

echo "=== SERV Hackathon Edition 01 — Demo Video ==="
echo "Frames:"
ls "$FRAMES"/*.png

# ─── 1. Render frame clips ──────────────────────────────────────────────────
echo "Rendering frame clips..."

for i in 1 2 3 4; do
  ffmpeg -y -loop 1 -i "$FRAMES/0${i}-*.png" \
    -t "$DUR_PER_FRAME" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black" \
    -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -r 30 \
    "$CLIPS/seg-${i}.mp4" 2>/dev/null
done

# ─── 2. Concatenate ─────────────────────────────────────────────────────────
echo "Assembling video..."

cat > "$CLIPS/concat.txt" << EOF
file 'seg-1.mp4'
file 'seg-2.mp4'
file 'seg-3.mp4'
file 'seg-4.mp4'
EOF

cd "$CLIPS"
ffmpeg -f concat -safe 0 -i concat.txt -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -r 30 \
  "$OUT/elcaro-serv-hackathon-edition-01.mp4" 2>/dev/null

echo "=== Demo video: $OUT/elcaro-serv-hackathon-edition-01.mp4 ==="
ls -lh "$OUT/elcaro-serv-hackathon-edition-01.mp4"
ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUT/elcaro-serv-hackathon-edition-01.mp4" | xargs -I{} echo "Duration: {}s"
