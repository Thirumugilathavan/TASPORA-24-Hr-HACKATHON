/**
 * Browser Audio Recorder for Gnani.ai Prisma STT.
 * 
 * Captures microphone audio using the Web Audio API, downsamples cleanly to 16,000 Hz mono,
 * and encodes directly into standard 16-bit PCM WAV (RIFF/WAVE container).
 * 
 * Provides real-time volume metering for visual animated waveforms.
 */

export interface RecordedAudioResult {
  blob: Blob;
  base64: string;
  durationSeconds: number;
}

export class AudioRecorder {
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStreamSource: MediaStreamAudioSourceNode | null = null;
  private scriptProcessor: ScriptProcessorNode | null = null;
  private analyser: AnalyserNode | null = null;
  private audioBuffers: Float32Array[] = [];
  private recordingStartTime = 0;
  private isCurrentlyRecording = false;
  private animFrameId: number | null = null;

  /**
   * Starts microphone recording.
   * @param onVolumeChange Callback receiving normalized volume level (0.0 to 1.0)
   */
  async start(onVolumeChange?: (volume: number) => void): Promise<void> {
    if (this.isCurrentlyRecording) return;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('Microphone access is not supported by your browser.');
    }

    // Request microphone access
    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    this.audioContext = new AudioContextClass();

    this.mediaStreamSource = this.audioContext.createMediaStreamSource(this.mediaStream);

    // Audio Analyser for real-time waveform volume
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    this.mediaStreamSource.connect(this.analyser);

    // ScriptProcessor to collect raw PCM samples
    const bufferSize = 4096;
    this.scriptProcessor = this.audioContext.createScriptProcessor(bufferSize, 1, 1);
    this.audioBuffers = [];
    this.recordingStartTime = Date.now();
    this.isCurrentlyRecording = true;

    this.scriptProcessor.onaudioprocess = (e) => {
      if (!this.isCurrentlyRecording) return;
      const inputData = e.inputBuffer.getChannelData(0);
      // Clone buffer
      this.audioBuffers.push(new Float32Array(inputData));
    };

    this.mediaStreamSource.connect(this.scriptProcessor);
    this.scriptProcessor.connect(this.audioContext.destination);

    // Run volume monitoring loop
    if (onVolumeChange && this.analyser) {
      const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
      const updateVolume = () => {
        if (!this.isCurrentlyRecording || !this.analyser) return;
        this.analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const average = sum / dataArray.length;
        const normalized = Math.min(1.0, Math.max(0.0, average / 128.0));
        onVolumeChange(normalized);
        this.animFrameId = requestAnimationFrame(updateVolume);
      };
      this.animFrameId = requestAnimationFrame(updateVolume);
    }
  }

  /**
   * Stops recording and returns the encoded 16-bit PCM WAV result.
   */
  async stop(): Promise<RecordedAudioResult> {
    if (!this.isCurrentlyRecording) {
      throw new Error('Audio recorder is not currently recording.');
    }

    this.isCurrentlyRecording = false;
    const durationSeconds = Math.max(0.1, (Date.now() - this.recordingStartTime) / 1000);

    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }

    // Disconnect audio nodes
    if (this.scriptProcessor) {
      this.scriptProcessor.disconnect();
      this.scriptProcessor.onaudioprocess = null;
    }
    if (this.mediaStreamSource) {
      this.mediaStreamSource.disconnect();
    }
    if (this.analyser) {
      this.analyser.disconnect();
    }

    // Stop all media tracks
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    const inputSampleRate = this.audioContext?.sampleRate || 44100;
    if (this.audioContext && this.audioContext.state !== 'closed') {
      await this.audioContext.close();
      this.audioContext = null;
    }

    // Flatten collected Float32 audio chunks
    const totalLength = this.audioBuffers.reduce((acc, curr) => acc + curr.length, 0);
    const mergedAudio = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of this.audioBuffers) {
      mergedAudio.set(chunk, offset);
      offset += chunk.length;
    }
    this.audioBuffers = [];

    // Downsample to 16,000 Hz for optimal Gnani STT accuracy
    const targetSampleRate = 16000;
    const resampledAudio = this.downsampleAudio(mergedAudio, inputSampleRate, targetSampleRate);

    // Encode to 16-bit PCM WAV
    const wavBlob = this.encodeWAV(resampledAudio, targetSampleRate);
    const base64 = await this.blobToBase64(wavBlob);

    return {
      blob: wavBlob,
      base64,
      durationSeconds: Math.round(durationSeconds * 10) / 10,
    };
  }

  /**
   * Cancels recording without generating audio.
   */
  cancel(): void {
    this.isCurrentlyRecording = false;
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    if (this.scriptProcessor) {
      this.scriptProcessor.disconnect();
      this.scriptProcessor.onaudioprocess = null;
    }
    if (this.mediaStreamSource) {
      this.mediaStreamSource.disconnect();
    }
    if (this.analyser) {
      this.analyser.disconnect();
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.audioBuffers = [];
  }

  isRecording(): boolean {
    return this.isCurrentlyRecording;
  }

  private downsampleAudio(inputBuffer: Float32Array, inputRate: number, targetRate: number): Float32Array {
    if (inputRate === targetRate) return inputBuffer;
    if (inputRate < targetRate) return inputBuffer; // Cannot upsample meaningfully

    const ratio = inputRate / targetRate;
    const newLength = Math.round(inputBuffer.length / ratio);
    const result = new Float32Array(newLength);

    let offsetResult = 0;
    let offsetBuffer = 0;

    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
      let accum = 0;
      let count = 0;
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < inputBuffer.length; i++) {
        accum += inputBuffer[i];
        count++;
      }
      result[offsetResult] = count > 0 ? accum / count : 0;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }

    return result;
  }

  private encodeWAV(samples: Float32Array, sampleRate: number): Blob {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    // RIFF chunk descriptor
    this.writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    this.writeString(view, 8, 'WAVE');

    // "fmt " sub-chunk
    this.writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
    view.setUint16(20, 1, true); // AudioFormat (1 for PCM)
    view.setUint16(22, 1, true); // NumChannels (1 for Mono)
    view.setUint32(24, sampleRate, true); // SampleRate
    view.setUint32(28, sampleRate * 2, true); // ByteRate (SampleRate * NumChannels * BitsPerSample/8)
    view.setUint16(32, 2, true); // BlockAlign (NumChannels * BitsPerSample/8)
    view.setUint16(34, 16, true); // BitsPerSample (16 bits)

    // "data" sub-chunk
    this.writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    // Write 16-bit PCM audio samples
    let index = 44;
    for (let i = 0; i < samples.length; i++) {
      // Clamp between -1.0 and 1.0
      const s = Math.max(-1, Math.min(1, samples[i]));
      // Convert to 16-bit signed integer (-32768 to 32767)
      const val = s < 0 ? s * 0x8000 : s * 0x7fff;
      view.setInt16(index, val, true);
      index += 2;
    }

    return new Blob([view], { type: 'audio/wav' });
  }

  private writeString(view: DataView, offset: number, string: string): void {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }

  private blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const dataUrl = reader.result as string;
        // Strip data:audio/wav;base64, prefix
        const base64 = dataUrl.split(',')[1] || '';
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }
}
