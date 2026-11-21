#!/bin/sh
# Assemble the film from the five scene masters.
#   sh assemble.sh <dir with s1.mp4 s2.mp4 s3.mp4 s4a.mp4 s4b.mp4 s5.mp4> <out dir> [width height]
# Scenes are joined with soft dissolves (no hard cuts), the title fades in over the
# last seconds of the finale, then the Local Howl end card.
set -e
IN=$1; OUT=$2; W=${3:-3840}; H=${4:-2160}
HERE=$(cd "$(dirname "$0")" && pwd)
X=0.75                      # dissolve length (s)
CARD=3.5                    # end card hold (s)
mkdir -p "$OUT"
dur() { ffprobe -v error -show_entries format=duration -of csv=p=0 "$1"; }
D1=$(dur $IN/s1.mp4); D2=$(dur $IN/s2.mp4); D3=$(dur $IN/s3.mp4); D4=$(dur $IN/s4a.mp4); D5=$(dur $IN/s4b.mp4); D6=$(dur $IN/s5.mp4)
O1=$(echo "$D1-$X" | bc -l)
O2=$(echo "$O1+$D2-$X" | bc -l)
O3=$(echo "$O2+$D3-$X" | bc -l)
O4=$(echo "$O3+$D4-$X" | bc -l)
O5=$(echo "$O4+$D5-$X" | bc -l)
T6=$(echo "$O5+$D6" | bc -l)            # end of the finale
O6=$(echo "$T6-1.0" | bc -l)            # dissolve into the end card
TS=$(echo "$T6-6.0" | bc -l)            # title in
N="fps=24,scale=$W:$H:flags=lanczos,setsar=1,format=yuv420p"
ffmpeg -v error -y \
  -i $IN/s1.mp4 -i $IN/s2.mp4 -i $IN/s3.mp4 -i $IN/s4a.mp4 -i $IN/s4b.mp4 -i $IN/s5.mp4 \
  -loop 1 -t $(echo "$T6+1" | bc -l) -i $HERE/title_overlay.png \
  -loop 1 -t $(echo "$CARD+1.0" | bc -l) -i $HERE/end_card.png \
  -filter_complex "
   [0:v]$N[a];[1:v]$N[b];[2:v]$N[c];[3:v]$N[d];[4:v]$N[e];[5:v]$N[f];
   [a][b]xfade=transition=fade:duration=$X:offset=$O1[ab];
   [ab][c]xfade=transition=fade:duration=$X:offset=$O2[abc];
   [abc][d]xfade=transition=fade:duration=$X:offset=$O3[abcd];
   [abcd][e]xfade=transition=fade:duration=$X:offset=$O4[abcde];
   [abcde][f]xfade=transition=fade:duration=$X:offset=$O5[film];
   [6:v]scale=$W:$H,format=rgba,fade=t=in:st=$TS:d=1.2:alpha=1[ttl];
   [film][ttl]overlay=0:0:shortest=1,format=yuv420p[filmt];
   [7:v]fps=24,scale=$W:$H,setsar=1,format=yuv420p[card];
   [filmt][card]xfade=transition=fade:duration=1.0:offset=$O6,fade=t=in:st=0:d=0.6[v]" \
  -map "[v]" -c:v libx264 -preset medium -crf ${CRF:-15} -pix_fmt yuv420p -movflags +faststart -an \
  $OUT/stl_rebuilt_in_3d_${W}x${H}.mp4
ffprobe -v error -show_entries format=duration,size -of csv=p=0 $OUT/stl_rebuilt_in_3d_${W}x${H}.mp4
