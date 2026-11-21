#!/bin/sh
# Three 15 s vertical (9:16, 1080x1920) cuts from the 4K scene masters.
#   sh verticals.sh <dir with s1.mp4 ... s5.mp4> <out dir>
# Each cut: footage, then a 2 s Local Howl end tag. Crop windows keep the subject in frame.
set -e
IN=$1; OUT=$2
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"
# part <file> <start s> <length s> <crop x as fraction of spare width 0..1>
part() { echo "trim=start=$2:duration=$3,setpts=PTS-STARTPTS,fps=24,crop=1215:2160:(iw-1215)*$4:0,scale=1080:1920:flags=lanczos,setsar=1,format=yuv420p"; }
cut3() {  # name  f1 s1 l1 x1  f2 s2 l2 x2  f3 s3 l3 x3
  name=$1
  ffmpeg -v error -y -i $IN/$2 -i $IN/$6 -i $IN/${10} -loop 1 -t 3 -i $HERE/end_card_vertical.png \
    -filter_complex "
      [0:v]$(part x $3 $4 $5)[a];[1:v]$(part x $7 $8 $9)[b];[2:v]$(part x ${11} ${12} ${13})[c];
      [3:v]fps=24,scale=1080:1920,setsar=1,format=yuv420p[k];
      [a][b]xfade=transition=fade:duration=0.5:offset=$(echo "$4-0.5" | bc -l)[ab];
      [ab][c]xfade=transition=fade:duration=0.5:offset=$(echo "$4+$8-1.0" | bc -l)[abc];
      [abc][k]xfade=transition=fade:duration=0.6:offset=$(echo "$4+$8+${12}-1.6" | bc -l),trim=duration=15[v]" \
    -map "[v]" -c:v libx264 -preset medium -crf 16 -pix_fmt yuv420p -movflags +faststart -an $OUT/$name.mp4
  ffprobe -v error -show_entries format=duration -of csv=p=0 $OUT/$name.mp4
}
# The Arch: dawn push-in, grounds with the pack, sunset pull-back
cut3 vertical_arch      s1.mp4 5.0 5.0 0.50   s2.mp4 15.0 5.0 0.62   s5.mp4 16.4 4.7 0.50
# Downtown: Washington Avenue crane down, the pack at street level
cut3 vertical_downtown  s3.mp4 0.5 4.5 0.50   s3.mp4 5.6 4.3 0.70    s3.mp4 9.3 6.6 0.86
# The Loop: Walk of Fame, Blueberry Hill, the Pageant and the Moonrise moon
cut3 vertical_loop      s4a.mp4 2.4 5.5 0.04  s4a.mp4 6.0 4.0 0.66   s4b.mp4 4.5 5.5 0.88
