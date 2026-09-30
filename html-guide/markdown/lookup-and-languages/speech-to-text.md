---
title: Speech to text
weight: 12
description: Settings → Speech to text (/settings/speech/) — an optional program, two Whisper models and optional per-language exact-word-time networks that make a transcript on this computer while you add a video; the processor (the CPU always, an NVIDIA graphics card when Parseh can prove it works), what each part costs, who may get and remove them, where the files are, and whose work they are.
---

A video you add needs a transcript, and the transcript is usually what
you do not have. **Speech to text** makes one on the computer Parseh runs
on: it listens to the video's sound with **Whisper**, a speech-recognition
model, and hands the page you are adding the video on a timed transcript
that you can read, correct and add like any other.

It is **optional** in every sense. Until you press a button on its page
nothing is fetched, Parseh's own installation is exactly the size it was,
and the page a video is added on is the page it always was, with a
transcript field you fill in yourself. It is the same on a computer with no
graphics card at all.

## Getting there

| From | What you press |
|---|---|
| Settings | the door **Speech to text**, beside **Reading help**, **Network**, **Updating Parseh** and **LaTeX drawings** |
| The address bar | `/settings/speech/` on the server |

It is **not** a part of [the reading-help page](reading-help.md). That page
is about reading what nobody has glossed; this is a tool of the page a video
is *added* on, and it has a door of its own. The reading-help page carries
one line pointing here.

On a phone the page opens with the phone's own bar, like its sibling
Settings pages, and it does everything the computer's does.

## Who may use it

**Any device that has been let in** may get, stop and remove anything on
this page: the computer, a phone on the Wi-Fi, another computer. The door's
pill says *any device let in*, and there is no lock line and no dead button
anywhere on it.

It is safe to leave open because **nothing a device sends becomes anything
that is fetched.** The only bytes that can ever arrive are the ones this
version of Parseh names: the packages of one hash-pinned list, each checked
against a SHA-256 Parseh ships with, and the files of two models at one
fixed version of their repository, each checked against its own. A model is
one of two names and a way of running it one of three. Whoever presses the
button gets the same files. Removing a part is refused while an install or
a transcription is using it — and a transcription of a YouTube video is using
it from the moment it starts, for as long as the video plays, and not only
once all its sound has arrived.

## What is on the page

The page has four parts, one under the other.

**What it is** says in five lines what is written here: it is optional, it
happens on this computer and nothing is sent to a speech-recognition
service, it works with no graphics card, the models are large, and it is
offered only while adding a video ([how the page uses it](../videos/adding-a-video.md#speech-to-text)).

**Processor** says what the transcript will be made on — [below](#the-processor).

**The program and the models** are three rows, made the way every row of
the reading help is made: a state with a sign and a word, what it holds or
would cost, a bar with the time left while it comes, **Stop**, and whose
work it is, with its licence, on the last line.

| Row | What it is | What it costs, and where it is kept |
|---|---|---|
| **The speech program** | faster-whisper and CTranslate2, with the libraries they need, in a folder of its own | about 128 MB to download and 431 MB kept on Linux (about 85 MB and 260 MB on Windows, less on a Mac); `stt/runtime/` |
| **faster-whisper / large-v3-turbo** — *Recommended · faster and lighter* | the model to start with | 1.6 GB; `stt/models/large-v3-turbo/` |
| **faster-whisper / large-v3** — *Higher accuracy · larger and slower* | the model for what the turbo one gets wrong | 3.1 GB; `stt/models/large-v3/` |

Those are the only two models. There is no smaller one, no other program and
no service: the processor is a separate choice from the model, and the two
are never confused.

**Getting a model gets everything it needs.** Pressing **Get it** on a model
when the program is not there installs the program first and then the model,
under one bar, and the row says so before it starts (*this includes the
speech program, which comes first*). Nothing is fetched by pressing anything
else: opening **Add a video** never installs anything.

**Languages** lists every language Parseh has, each in its own script and
the right-to-left ones right-to-left, with a tick for those Whisper knows.
All eleven of Parseh's are ticked: Persian, Arabic, Italian, Japanese,
French, German, Turkish, English, Hindi, Spanish and Chinese. A language you
added yourself is ticked if Whisper has a code for it, and marked *not
offered* if it does not.

Under each offered language is an **Exact word times** row. Its separate,
optional CTC network is about 340–361 MiB installed, and its row says the
size before **Get it**, download progress, **Stop** or **Remove**, its licence
and its attribution. It is not needed to transcribe: Whisper works with no
such network. When installed, it lets the add page make word boundaries from
the recording while leaving Whisper's captions unchanged. All eleven offered
languages have one; each download is pinned to an immutable public
`parseh/aligner-<language>` revision and hash-checked before it is installed
under `stt/aligners/<language>/`.

### A row's states

| Pill | What it means |
|---|---|
| **✓ Installed** | here and complete. The row says what it holds — *faster-whisper 1.2.1 · CTranslate2 4.8.2 · 431 MB*. |
| **↻ Built by an older Parseh** or **… by a newer Parseh** | the program was made by another version of Parseh, whose pinned list differs from this one's. It is not run; **Install it again** makes this version's, once, and takes the old one away only when the new one is whole. |
| **↻ Built for another Python** | the folder was made for a different Python than the one this Parseh runs on (the program is built for Python 3.12). **Install it again** replaces it. |
| **! Incomplete** | the folder is there and something the list names is not. **Install it again**. |
| **↓ Downloading · 62%**, then **↻ Installing** | on its way. A model's bar counts every file of it together; the program's counts the packages' bytes, and then puts them in place. |
| **○ Not yet** | not here, with what it would cost. |
| **! Stopped** | you pressed **Stop**, or the line dropped, and why is in words. A model carries on from where it stopped (**Carry on**). The program starts again from the beginning: pip, which installs it, cannot carry on a half-fetched file, and the row says so before you start. |
| **– Not available** | this computer cannot have it, and why (below). No button is offered that could not work. |

A model that is here while the program is not says so under it — it cannot be
used until the program is back.

## The processor

**CPU · ready.** *Speech to text will work on this computer. A compatible
NVIDIA graphics card can make it considerably faster, but one is not
required.* That is the first sentence about the processor, and it is true of
every computer the program installs on: the CPU is the way it always works,
and it is never described as second-class. It computes in **int8**, on as
many threads as the computer has physical cores, at most eight — more is not
faster (on the computer it was measured on, 8 threads took 24 seconds where
24 threads took 34).

**The graphics card** is used only when Parseh has *proved* it can be, and
never on the strength of a name or of an NVIDIA program being installed. The
proof is a look, made by a program of its own that never loads a model, that
asks three things separately: whether the driver sees a card, whether the
speech program's own build lists a half-precision type the card can compute
in, and whether **cuBLAS for CUDA 12 loads** — counting the card is not
enough, because with cuBLAS missing the count is still one and the model even
loads, and it is the first sentence of the transcript that fails. The page
opens with a look, and **Check again** looks once more; that is its own
button, for after you have installed something the card needed.

It answers one of four ways:

| The page says | What it means |
|---|---|
| **○ No NVIDIA graphics card** | none was found — or this kind of computer has a build of the program with no graphics-card support at all (a Mac, or Linux on an ARM processor), which is said, and not looked for. |
| **! Found, not ready** | *NVIDIA GPU found, but speech-to-text acceleration is not ready. CPU transcription will still work.* With the piece that is missing, by name, and what this installation needs. |
| **✓ GPU acceleration ready** | *Automatic mode will use the graphics card for faster transcription. You can still choose CPU if you prefer.* Beside the card's name, and its memory under **technical details**. |
| a look that failed | said in words, and taken as a card that is not ready — never as one that is. |

**Technical details**, folded under the row, say what the look found: the
version of the program, the CPU's compute type and threads, the card, its
driver, the compute type chosen for it, where cuBLAS was found, and when the
look was made.

### Automatic, CPU, NVIDIA GPU

These are chosen when a video is added, and the page says what each does:

- **Automatic — recommended.** Uses the card when it is ready and the CPU
  otherwise, and silently and reliably the CPU when there is no card:
  Automatic never causes a failed attempt. If the card cannot start the model
  after all (its memory, most likely), Parseh continues on the CPU and says so.
- **CPU.** Always uses the CPU, whatever the computer has.
- **NVIDIA GPU.** Offered only where the card is ready. Chosen and then
  failing, it says why and does not quietly switch.

The compute type is never asked for. On a card Parseh uses `int8_float16`
where the card can, then `float16`; a card that can do neither is *found, not
ready* and the CPU is used.

**A card is not always faster.** These are figures from one computer, for
one 57-second clip, and only that: the turbo model took 24 seconds on the
CPU (8 threads), 11 seconds on a GTX 1650 in `int8_float16`, and 42 seconds
on the same card in `float16`, which is why the card's type is chosen for it.
large-v3 took 109 seconds on the CPU and needed about 6 GB of memory there;
on the 4 GB card it did not fit in `float16` and ran, in `int8_float16`, in
48 seconds. Real speech, a real video and a different computer will differ.

### How to enable GPU acceleration

Graphics acceleration needs, for the version of the speech program this
Parseh installs (CTranslate2 4.8.2):

- an NVIDIA graphics driver that runs CUDA 12 programs, from the card's
  maker or your system's driver tool;
- cuBLAS for CUDA 12 (`libcublas.so.12` on Linux, `cublas64_12.dll` on
  Windows), which comes with NVIDIA's CUDA Toolkit 12: choose a 12.x release
  from [NVIDIA's archive](https://developer.nvidia.com/cuda-toolkit-archive),
  because the newest CUDA has a cuBLAS of another number, which this version
  cannot use.

**cuDNN is not needed.** The documentation of faster-whisper still says it
is; the CTranslate2 the program carries stopped needing it in its 4.6.3.
This list is made from one table in Parseh (`GPU_NEEDS` in `lib/getstt.py`),
next to the version of the program, so a later version that asks for
something else changes what this page says with it.

**Parseh installs none of it.** It never fetches the graphics card's
software, and never changes a driver: those are the computer's. When you
have installed them, press **Check again** on the page — nothing else is
needed, and CPU transcription worked all the time.

Only the builds for Linux and Windows on an x86-64 processor carry card
support; on a Mac, or on Linux on ARM, the CPU is what there is.

## Which computers can have it

The program is built for **Python 3.12** and for five kinds of computer: Linux
on x86-64 (glibc 2.28 or newer) and on ARM64, Windows on x86-64, a Mac with
Apple silicon (macOS 14 or newer) and an Intel Mac (macOS 13 or newer). On a
computer that is none of these — another Python, another processor, an older
Mac, a Linux without glibc, no pip — the rows say **Not available**, with why,
and offer no button. On Windows, the program's files have names up to 125
characters long, so a Parseh folder nested deeper than about a hundred
characters is refused with a sentence, unless Windows has long paths turned on.

- **Another Python, or a Python with no pip.** Parseh's own environment has
  Python 3.12 and pip: make it once by double-clicking **install.bat** on
  Windows or **Parseh.command** on a Mac (or running `install.sh` on Linux),
  then start Parseh again.
- **A folder too deep on Windows.** Either move Parseh's folder nearer the top
  of a drive, or turn long paths on: open the Registry Editor, go to
  `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`, set the
  value **LongPathsEnabled** to `1` (or turn on *Enable Win32 long paths* in
  the Group Policy Editor), and restart Windows. Microsoft's page on it is
  [Maximum Path Length Limitation](https://learn.microsoft.com/windows/win32/fileio/maximum-file-path-limitation).

## Where the files live

| Path | What it is |
|---|---|
| `stt/runtime/<generation>-cp312/` | the program, made by pip from `lib/stt-requirements.txt`. The folder's **name is the record**: the number of this version's pinned list, and the Python it was made for — which is how *installed by an older Parseh* and *for another Python* are told without any file of records. |
| `stt/models/<model>/` | a model's five files and a `meta.json` saying where it is from and when it was made. |
| `stt/models/<model>.part/` | a model that was stopped, kept for the next press. |
| `stt/tmp/` | the sound of a video while it is being transcribed. **Deleted** when the job ends, and swept again whenever Parseh starts, in case it was stopped in between. |

None of it is in Parseh's own environment: the program is never on the
server's own path (it brings its own numpy), and everything that uses it —
the transcription, and the look at the graphics card — is a separate process
that ends when Parseh does. `stt/` is kept, like `dict/` and `mt/`, by an
[update](../getting-started/updating.md#what-it-keeps): it is in neither
release's list of files, so no update, forward or back, touches a byte of it;
git ignores it; and no [backup](../getting-started/backups.md) holds it —
fetch it again here.

**Going back to a0.4.0 leaves `stt/` exactly as it is.** That version has no
page to remove it, and does not read it; if you do not want the gigabytes
while you are on it, take the `stt/` folder off by hand, and get speech to text
again on the version that has the page.

## Whose work it is

Each row says whose work it is and its licence, linked, and
[the licences page](../reference/licences.md) lists them all.

- The program: **faster-whisper**, **CTranslate2** and **onnxruntime** are
  under the MIT licence; **PyAV** is under BSD-3-Clause, and the FFmpeg
  libraries inside its packages report LGPL-3.0-or-later, while the codec
  libraries beside them keep their own licences; the rest of what the list
  names, and the backends CTranslate2's packages bundle (Intel MKL and oneDNN
  in the Linux one), are under the licence each comes with. Parseh, which is
  GPL-3.0-or-later, ships none of it: your own press of **Get it** fetches it
  from PyPI.
- The models: OpenAI's Whisper large-v3 and large-v3-turbo, converted to
  CTranslate2's format (by Systran, and by Mobius Labs for the turbo one; the
  repository is now `dropbox-dash/faster-whisper-large-v3-turbo`), under the
  MIT licence, fetched from Hugging Face at a fixed version.
- Exact-word-time networks: Parseh's `aligner-zh`, `aligner-ja`, `aligner-hi`,
  `aligner-ar`, `aligner-fa`, `aligner-tr`, `aligner-es`, `aligner-de`,
  `aligner-fr`, `aligner-it` and `aligner-en` repositories on Hugging Face,
  fetched at the pinned revision. They run through onnxruntime; their notices
  and licences travel with each installed row (Apache-2.0, except Hindi MIT
  and Turkish CC-BY-4.0).

The hosts it talks to, and only when you press a button, are `pypi.org` and
`files.pythonhosted.org` for the program, and `huggingface.co` (which answers
with a redirect to its own file host) for the models. Once installed,
transcribing a film on this computer needs no network at all.
