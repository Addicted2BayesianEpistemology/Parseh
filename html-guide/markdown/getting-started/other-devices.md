---
title: From a phone or another computer
linkTitle: From a phone
weight: 4
description: The addresses Parseh can be reached at, why it speaks HTTPS, and the certificate every browser asks you about once.
---

Parseh runs on one computer, but it is a web server: a phone, a tablet or
a laptop that can reach that computer can use it too — read a book on the
sofa while the narration plays, study a deck on the train. Nothing needs
installing on the phone; a browser is all it takes.

## Which address

When Parseh starts it prints every address it can be reached at, and the
hub says the same at its foot, under **Reachable at**:

```text
  https://100.101.102.103:8765/              (tailscale)
  https://192.168.1.20:8765/                 (local network)
  https://localhost:8765/                    (this machine)
```

| Address | Who can use it |
|---|---|
| **tailscale** — one starting with `100.` | any of your own devices on your Tailscale network, wherever they are |
| **local network** | a device on the same Wi-Fi or network as the computer |
| **localhost** | only the computer Parseh runs on |

The list is what Parseh can find by the computer's own name, and on some
computers the local network address is not among what that finds. It works
all the same, and the computer's network settings show what it is; if the
certificate does not name it, a browser reaching Parseh by it warns about
the certificate as for any other address, and is accepted the same way.

**Tailscale** is a private network between your own devices, which lets a
phone reach the computer at home from anywhere as if it were in the next
room — and nobody else. Parseh has nothing to set up for it: where the
`tailscale` program is installed, Parseh asks it for the address and puts
it first, and puts the computer's name on your tailnet into its
certificate too.

On a phone, open the address in the browser and bookmark it. The hub's
[mobile interface](mobile-mode.md), made for reading on a phone, is one
tap away on its **Browser | Mobile** switch.

The server listens on every network the computer is connected to, so any
device that can reach the computer can reach Parseh. On Windows the
firewall asks, the first time, whether Python may accept connections:
allow it, or only the computer itself can reach Parseh.

## Why HTTPS

Parseh speaks HTTPS, the secure kind of address, even though it only ever
talks to your own devices. The reason is the browsers: a few things a page
can do, they allow only on a secure address, and the one plain `http://`
address they count as secure is `localhost` — the computer Parseh runs on.
From any other device, a phone or another computer, these three need the
`https://` address:

| What | The buttons |
|---|---|
| **the studio's copying** | a click on text in the language you are learning, in a document or the editor's preview, which copies it; **Copy prompt only** and **Copy prompt + question** on the prompt page; **Copy complete prompt**, under **Generate with LLM…** in the editor |
| **capturing a video's frame** for a card | **📷 capture the current frame**, in the player's card sheet |
| **recording a YouTube video's sound** from its tab, to cut a card's recording out of it | **🔊 cut the audio…**, in the same sheet — in Chrome or Edge, on a computer |

Without a secure address the studio says *Clipboard unavailable*, and the
player says that the capture, or the recording, needs the page opened at
the toolbox's https address.

Every other copy works on either kind of address — shift-click in a
book's reader, a prompt for an LLM copied from a book or a video, the
copy buttons of the card sheets and of the pages for adding a book or a
video: where the browser keeps its clipboard back, they copy the older
way, which every browser still allows.

An old `http://` bookmark on the same port is not an error: Parseh sends it
on to the `https://` address.

## The certificate

HTTPS needs a certificate, and Parseh makes its own the first time it
starts — with `openssl`, which the environment carries — for every name and
every address the computer has at that moment: `localhost`, its name, its
local addresses, its Tailscale address and name. It keeps it in `.tls/` in
the Parseh folder.

It is **self-signed**: nobody but Parseh vouches for it, so **every browser
warns you about it once**, on each device. The warning page always has a
way through — in Chrome **Advanced**, then **Proceed** — and once you have
accepted it that browser does not ask again. This is the whole ceremony:
it is your own server on your own network, and nobody else is being asked
to trust it.

**When the computer's addresses change** — another network, or Tailscale
installed afterwards — the certificate does not name the new ones, and a
browser reaching Parseh by one of them warns again. No page has a button
for a fresh certificate; Parseh makes one as it starts whenever it finds
none, so:

1. stop Parseh with **⏻ stop**;
2. delete the folder `.tls` in the Parseh folder — on Linux and macOS a
   name that begins with a dot is hidden, so first show hidden files in
   the file manager (Ctrl+H in most Linux file managers, ⌘⇧. in the
   Finder);
3. start Parseh again, the way you always do: it makes a new certificate,
   for every name and address the computer has now.

Every browser then warns once more, about the new certificate.

> **For the command line.** `./serve.sh cert`, then `./serve.sh restart`,
> does the same on Linux and macOS. On Windows, `serve.bat cert` makes the
> new certificate; then stop Parseh and start it again.

## Plain http

On a Windows computer with no OpenSSL at all, Parseh cannot make a
certificate, and serves plain `http://` instead ([the Windows
wizard](windows-wizard.md) offers to install OpenSSL). On that computer
everything works; from a phone or another computer everything works but
the three things [above](#why-https), which need the secure address.

> **For the command line.** `python3 serve.py --http` serves plain http
> on purpose, for debugging.

On Linux and macOS a missing `openssl` is not quietly worked round: the
server refuses to start without a certificate, and says why:

```text
openssl is needed to make the certificate (apt install openssl),
or run with --http to serve without TLS
```

The environment the installer makes carries one, so this happens only on
a computer serving without it.

## Keeping it to one computer

> **For the command line.** `./serve.sh` always listens on every network.
> To keep Parseh to the computer it runs on, start it in the foreground
> with `python3 serve.py --local`; to listen on one address only — the
> Tailscale one, say — use `python3 serve.py --host 100.101.102.103`.

## Each device keeps its own settings

The theme, the language picked on the hub's chips, the **Browser | Mobile**
choice, where you are in a book: a browser keeps these for itself, so your
phone and your computer each have their own. They are kept per address,
too — the same phone opening Parseh once by its Tailscale address and once
by its local one keeps two sets.

And the **⏻ stop** button stops the server for everybody: stopped from the
phone, Parseh stops on the computer as well.
