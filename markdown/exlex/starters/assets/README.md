# The starters' pictures and recording

The files a starter (`../<code>.md`) names as `images/<name>` and
`audio/<name>`, so that a new document shows a picture and plays a recording
before it has any of its own. The first save that names one copies it into
the document's own `images/` or `audio/` (`store.adopt_starter_media`;
`markdown/README.md`, *The starters' pictures and recording*), once: from
then on it is the document's to keep or delete, and one deleted there is
not copied in again. Until that save the editor's preview shows it from
here (`GET /starter-media/…`).

| file | what it is |
|---|---|
| `images/starter-apple.svg` | a red apple with a leaf, flat, on a pale disc |
| `images/starter-house.svg` | a small house (roof, chimney, door, two windows), flat, on a pale disc |
| `audio/starter-chime.mp3` | a soft two-note chime (G5 then C6), 1.5 s, mono |

Every name starts with `starter-`, so it cannot be mistaken for a file the
owner uploads, and follows the rules a document's own file follows
(`store.IMG_NAME_RE`, `audiofile.NAME_RE`). The pictures are hand-written SVG
1.1: a `viewBox`, plain shapes and flat colours, no text, no script and
nothing fetched from elsewhere — the PDF build turns each into a PDF with
PyMuPDF, which draws exactly this subset. They carry no language and no
direction, so every starter can use them.

The chime was made with ffmpeg: two bell-like tones (the note, its octave at
a fifth of the loudness and its twelfth at a twentieth), each struck in 6 ms
and dying away exponentially, the second 0.4 s after the first, the whole
faded to silence over its last 0.3 s:

```
N1='min(1,t/0.006)*exp(-3.4*t)*(sin(2*PI*783.99*t)+0.22*sin(2*PI*1567.98*t)+0.05*sin(2*PI*2351.97*t))'
N2='gte(t,0.4)*min(1,(t-0.4)/0.006)*exp(-3.0*(t-0.4))*(sin(2*PI*1046.50*(t-0.4))+0.22*sin(2*PI*2093.00*(t-0.4))+0.05*sin(2*PI*3139.50*(t-0.4)))'
ffmpeg -f lavfi -i "aevalsrc='0.45*($N1+$N2)*min(1,(1.5-t)/0.3)':s=44100:c=mono:d=1.5" chime.wav
ffmpeg -i chime.wav -ac 1 -ar 44100 -c:a libmp3lame -b:a 64k -map_metadata -1 \
       -id3v2_version 0 -write_id3v1 0 -fflags +bitexact -flags:a +bitexact starter-chime.mp3
```

A starter that wants another picture or recording adds its file here under a
`starter-` name; nothing else has to change.
