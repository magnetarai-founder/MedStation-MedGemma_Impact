# Whisper Installation Guide for ElohimOS

**Purpose:** Enable local audio transcription for Insights Lab

---

## Option 1: Python Whisper (Easiest)

```bash
# Install openai-whisper
pip install openai-whisper

# This will download the model automatically on first use
# Models: tiny, base, small, medium, large
# Recommendation: Use "base" for good balance of speed/accuracy
```

**Pros:**
- Easy to install
- Works immediately
- Good accuracy

**Cons:**
- Slower than whisper.cpp
- Uses more RAM

---

## Option 2: Whisper.cpp (Fastest - Recommended)

```bash
# Clone whisper.cpp
cd ~
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp

# Build with Metal acceleration (macOS)
make clean
WHISPER_METAL=1 make

# Download the base model
bash ./models/download-ggml-model.sh base.en

# Test it
./main -m models/ggml-base.en.bin -f samples/jfk.wav
```

**Pros:**
- **10x faster** than Python version
- Uses Metal GPU acceleration
- Lower RAM usage
- C++ = blazing fast

**Cons:**
- Requires compilation
- Slightly more setup

---

## How ElohimOS Uses Whisper

The `insights_service.py` backend checks for Whisper in this order:

1. **whisper.cpp** - If `~/whisper.cpp/main` exists, uses this (fastest)
2. **Python whisper** - Falls back to `import whisper` if whisper.cpp not found
3. **Error** - If neither is available, returns helpful error message

---

## Testing Transcription

Once installed, test the Insights Lab:

1. Navigate to **Team → Docs & Sheets**
2. Create a **New Document → Insight**
3. Click **"Upload Audio"**
4. Select a voice memo (.m4a from iPhone, or .mp3, .wav)
5. Wait for transcription (5-30 seconds depending on length)
6. Transcript appears in left pane automatically
7. Click **"Analyze with AI"** to get theological analysis

---

## Supported Audio Formats

- `.m4a` (iPhone voice memos)
- `.mp3`
- `.wav`
- `.webm`
- `.mp4` (audio track)
- `.ogg`

---

## Troubleshooting

### "Whisper transcription not available"
- Install Python whisper: `pip install openai-whisper`
- Or build whisper.cpp as shown above

### Transcription is slow
- Use whisper.cpp instead of Python version
- Or use smaller model: `base.en` instead of `large`

### Out of memory
- Use smaller model: `tiny.en` or `base.en`
- Close other applications
- Whisper.cpp uses less RAM than Python version

### Audio file not uploading
- Check file format (must be audio)
- Max file size: 50MB
- iPhone voice memos work best (.m4a)

---

## Model Sizes & Performance

| Model | Size | Speed | Accuracy | RAM |
|-------|------|-------|----------|-----|
| tiny.en | 75MB | Very Fast | Good | 1GB |
| base.en | 142MB | Fast | Better | 1GB |
| small.en | 466MB | Medium | Great | 2GB |
| medium.en | 1.5GB | Slow | Excellent | 5GB |
| large | 2.9GB | Very Slow | Best | 10GB |

**Recommendation:** Use `base.en` for best balance of speed/accuracy.

---

## Next Steps

Once Whisper is installed:
1. Test with a short voice memo first
2. Try the "Analyze with AI" feature
3. Experiment with longer reflections (up to 10 minutes)
4. Lock your insights for privacy (Cmd+Shift+L quick-lock coming soon)

---

**Note:** All transcription happens **locally** on your Mac. Audio files never leave your machine. This is critical for missionaries in hostile environments where privacy is paramount.
