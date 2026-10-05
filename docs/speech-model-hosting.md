# Optional speech-model downloads

Converted model weights are published separately on Hugging Face, one complete
CTranslate2 package per model. Parseh releases contain the installer and pinned
catalogue, with no model weights or conversion tools. Installation starts only
when the user chooses **Get it** in Settings → Speech to text.

The installer downloads each asset from the catalogue's immutable repository
revision, checks its size and SHA-256, supports cancellation/resume, and validates
the complete package before atomic installation. Model cards, original attribution,
fine-tune licences and OpenAI Whisper's underlying MIT notice are retained.

The conversion, publication and qualification code has moved into a separate
project, `Parseh-model-packaging`, beside the development checkout, published in
[parseh-io/whisper-ct2-conversion](https://github.com/parseh-io/whisper-ct2-conversion).
It does not run in the Parseh environment. Generated weights, scratch files and
credentials are ignored by Git; no main-branch merge is required to publish them.

Weight licences remain independent of Parseh's GPL code licence. The six local
conversions declare MIT or Apache-2.0; Collabora Hindi remains under CC-BY-4.0.

See [Hugging Face model cards](https://huggingface.co/docs/hub/model-cards) and
[licence metadata](https://huggingface.co/docs/hub/repositories-licenses).
