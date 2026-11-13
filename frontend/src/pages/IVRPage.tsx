import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Phone,
  PhoneCall,
  PhoneOff,
  Volume2,
  VolumeX,
  RotateCcw,
  MapPin,
  Search,
  Navigation,
  Hospital,
  AlertCircle,
  CheckCircle2,
  ArrowLeft,
  Languages,
  ShieldCheck,
  Building2,
  PhoneForwarded,
  Clock,
  Sparkles,
  Info,
  ChevronRight,
  Delete,
  Hash,
  Asterisk,
} from 'lucide-react';
import {
  ivrSimulationService,
  IVRSimulationResponse,
  IVRFacilitySummary,
  PincodeResolution,
} from '../services/ivrSimulationService';
import { authService } from '../services/authService';
import { Village } from '../types';

interface TranscriptItem {
  id: string;
  sender: 'system' | 'user';
  text: string;
  timestamp: string;
  type?: 'speech' | 'keypad' | 'info' | 'error';
}

export const IVRPage: React.FC = () => {
  // Call status: IDLE | DIALING | IN_CALL | ENDED
  const [callStatus, setCallStatus] = useState<'IDLE' | 'DIALING' | 'IN_CALL' | 'ENDED'>('IDLE');
  const [callTimer, setCallTimer] = useState(0);
  const [language, setLanguage] = useState<'ta' | 'en'>('ta');
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speechAvailable, setSpeechAvailable] = useState(true);

  // State machine data from simulation
  const [simState, setSimState] = useState<IVRSimulationResponse | null>(null);
  const [callSid, setCallSid] = useState<string>('');
  const [currentMenu, setCurrentMenu] = useState<string>('LANGUAGE_SELECT');
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // PIN Code input state
  const [pinInput, setPinInput] = useState<string>('');
  const [pincodeError, setPincodeError] = useState<string | null>(null);
  const [resolvedLocation, setResolvedLocation] = useState<PincodeResolution | null>(null);

  // Village search fallback state
  const [showVillageModal, setShowVillageModal] = useState(false);
  const [villageSearchTerm, setVillageSearchTerm] = useState('');
  const [villageSuggestions, setVillageSuggestions] = useState<Village[]>([]);
  const [isSearchingVillages, setIsSearchingVillages] = useState(false);

  // Geo status
  const [geoStatus, setGeoStatus] = useState<'idle' | 'detecting' | 'granted' | 'denied'>('idle');

  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const timerIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ---------------------------------------------------------------------------
  // Audio DTMF Sound Synthesizer (0-cost Web Audio API)
  // ---------------------------------------------------------------------------
  const playDtmfTone = useCallback((digit: string) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const dtmfFreqs: Record<string, [number, number]> = {
        '1': [697, 1209],
        '2': [697, 1336],
        '3': [697, 1477],
        '4': [770, 1209],
        '5': [770, 1336],
        '6': [770, 1477],
        '7': [852, 1209],
        '8': [852, 1336],
        '9': [852, 1477],
        '*': [941, 1209],
        '0': [941, 1336],
        '#': [941, 1477],
      };
      const freqs = dtmfFreqs[digit] || [750, 1250];
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();

      osc1.frequency.value = freqs[0];
      osc2.frequency.value = freqs[1];
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);

      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);

      osc1.start();
      osc2.start();
      osc1.stop(ctx.currentTime + 0.12);
      osc2.stop(ctx.currentTime + 0.12);
    } catch {
      // AudioContext blocked or unsupported
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Speech Synthesis Engine (Native Web Speech API)
  // Voices load asynchronously in browsers — we cache them after voiceschanged
  // fires, then pick the best Tamil / English voice for each utterance.
  // ---------------------------------------------------------------------------
  const cachedVoicesRef = useRef<SpeechSynthesisVoice[]>([]);

  // Load voices once and keep them cached. Chrome fires voiceschanged; Firefox
  // populates synchronously; Safari also fires the event.
  // Also check if a Tamil TTS voice is available and update speechAvailable state.
  useEffect(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;

    const loadVoices = () => {
      const v = window.speechSynthesis.getVoices();
      if (v.length > 0) {
        cachedVoicesRef.current = v;
        // Check if Tamil voice is available
        const hasTamilVoice = v.some((voice) => voice.lang === 'ta-IN' || voice.lang.startsWith('ta'));
        setSpeechAvailable(hasTamilVoice);
      }
    };

    loadVoices(); // may already be populated on Firefox / Safari
    window.speechSynthesis.addEventListener('voiceschanged', loadVoices);
    return () => window.speechSynthesis.removeEventListener('voiceschanged', loadVoices);
  }, []);

  /** Pick the best available voice for the given language tag. */
  const pickVoice = (langTag: string): SpeechSynthesisVoice | null => {
    const voices = cachedVoicesRef.current;
    if (!voices.length) return null;
    // Exact match first, then prefix match
    return (
      voices.find((v) => v.lang === langTag) ||
      voices.find((v) => v.lang.startsWith(langTag.split('-')[0])) ||
      null
    );
  };

  /**
   * Speak `text` using the correct language voice.
   *
   * With the backend now returning `speak_text_ta` and `speak_text_en` separately,
   * this function receives clean single-language text from `pickSpeakText`.
   * When Tamil mode is active it always receives pure Tamil text; when English mode
   * is active it always receives pure English text.
   *
   * Fallback: if no `ta-IN` voice is installed on the device the text is still
   * queued without an explicit voice — the browser uses its default engine which
   * may not render Tamil correctly, so we show a no-Tamil-TTS hint instead of
   * silently failing.
   */
  const speakText = useCallback(
    (text: string, lang: 'ta' | 'en') => {
      if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
        setSpeechAvailable(false);
        return;
      }

      window.speechSynthesis.cancel();
      if (isMuted) return;

      // Detect whether text contains Tamil Unicode (U+0B80–U+0BFF)
      const hasTamil = /[\u0B80-\u0BFF]/.test(text);

      if (!hasTamil || lang === 'en') {
        // Pure English path — single utterance
        const utt = new SpeechSynthesisUtterance(text);
        utt.lang = 'en-IN';
        utt.rate = 0.92;
        utt.pitch = 1.0;
        const voice = pickVoice('en-IN') || pickVoice('en-GB') || pickVoice('en');
        if (voice) utt.voice = voice;
        utt.onstart = () => setIsSpeaking(true);
        utt.onend = () => setIsSpeaking(false);
        utt.onerror = () => setIsSpeaking(false);
        window.speechSynthesis.speak(utt);
        return;
      }

      // Tamil path — backend now sends pure Tamil text in speak_text_ta.
      // Split on " / " only as a safety fallback for any residual bilingual text.
      const tamilVoice = pickVoice('ta-IN') || pickVoice('ta');
      const englishVoice = pickVoice('en-IN') || pickVoice('en-GB') || pickVoice('en');

      const parts = text.split(/\s*\/\s*/);
      const segments: Array<{ text: string; langTag: string }> = [];
      parts.forEach((part) => {
        const isTamilPart = /[\u0B80-\u0BFF]/.test(part);
        if (part.trim()) {
          segments.push({ text: part.trim(), langTag: isTamilPart ? 'ta-IN' : 'en-IN' });
        }
      });

      if (segments.length === 0) return;

      // Queue utterances — only the first fires onstart, only the last fires onend
      segments.forEach((seg, idx) => {
        const utt = new SpeechSynthesisUtterance(seg.text);
        utt.lang = seg.langTag;
        utt.rate = seg.langTag === 'ta-IN' ? 0.88 : 0.92; // Tamil slightly slower
        utt.pitch = 1.0;

        // Assign the best available voice for each segment
        const voice = seg.langTag === 'ta-IN' ? (tamilVoice || null) : englishVoice;
        if (voice) utt.voice = voice;

        if (idx === 0) utt.onstart = () => setIsSpeaking(true);
        if (idx === segments.length - 1) {
          utt.onend = () => setIsSpeaking(false);
          utt.onerror = () => setIsSpeaking(false);
        }

        window.speechSynthesis.speak(utt);
      });
    },
    [isMuted]
  );

  // Stop all audio on cleanup or end call
  const stopSpeech = useCallback(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
  }, []);

  /**
   * Pick the best text to speak from an IVR response.
   * Prefers the language-specific field (speak_text_ta / speak_text_en) over
   * the combined speak_text, so each TTS engine receives clean, unmixed text.
   */
  const pickSpeakText = useCallback(
    (res: IVRSimulationResponse, lang: 'ta' | 'en'): string => {
      if (lang === 'ta' && res.speak_text_ta) return res.speak_text_ta;
      if (lang === 'en' && res.speak_text_en) return res.speak_text_en;
      return res.speak_text;
    },
    []
  );

  useEffect(() => {
    return () => {
      stopSpeech();
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, [stopSpeech]);

  // Scroll transcript to bottom on new message
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  // Format Call Timer (mm:ss)
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // ---------------------------------------------------------------------------
  // Call Flow Actions
  // ---------------------------------------------------------------------------
  const handleStartCall = async () => {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      setCallStatus('DIALING');
      playDtmfTone('1');

      // Add to transcript
      const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      setTranscript([
        {
          id: 't-start',
          sender: 'system',
          text: '📞 Dialing NALAM AI Healthcare Helpline (1800-202-CARE)...',
          timestamp: now,
          type: 'info',
        },
      ]);

      const res = await ivrSimulationService.startSimulation(language);
      setSimState(res);
      setCallSid(res.call_sid);
      setCurrentMenu(res.current_menu);
      setCallStatus('IN_CALL');

      // Start call duration timer
      setCallTimer(0);
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = setInterval(() => {
        setCallTimer((prev) => prev + 1);
      }, 1000);

      // Add system speech to transcript
      setTranscript((prev) => [
        ...prev,
        {
          id: `t-sys-${Date.now()}`,
          sender: 'system',
          text: res.speak_text,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          type: 'speech',
        },
      ]);

      speakText(pickSpeakText(res, language), language);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to connect simulated helpline. Please try again.');
      setCallStatus('IDLE');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEndCall = () => {
    stopSpeech();
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    setCallStatus('ENDED');
    setTranscript((prev) => [
      ...prev,
      {
        id: `t-end-${Date.now()}`,
        sender: 'system',
        text:
          language === 'ta'
            ? 'அழைப்பு முடிந்தது. NALAM AI உதவி மையத்தை அழைத்ததற்கு நன்றி.'
            : 'Call ended. Thank you for calling NALAM AI Healthcare Helpline.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        type: 'info',
      },
    ]);
  };

  const handleKeypadPress = async (digit: string) => {
    playDtmfTone(digit);

    // If not in call, pressing keypad does not navigate
    if (callStatus !== 'IN_CALL') return;

    // Add user keypad press to transcript
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setTranscript((prev) => [
      ...prev,
      {
        id: `t-user-${Date.now()}`,
        sender: 'user',
        text: `Pressed Keypad: [ ${digit} ]`,
        timestamp: timeStr,
        type: 'keypad',
      },
    ]);

    // Handle PIN input accumulation if currently in LOCATION_INPUT menu
    if (currentMenu === 'LOCATION_INPUT') {
      if (digit === '*') {
        // Trigger Geolocation
        handleDetectLocation();
        return;
      }
      if (digit === '4') {
        // Trigger Village search modal
        setShowVillageModal(true);
        return;
      }
      if (digit === '#') {
        // Submit PIN code
        if (pinInput.length === 6) {
          handlePinSubmit(pinInput);
        } else {
          setPincodeError(
            language === 'ta'
              ? 'தயவுசெய்து 6 இலக்க அஞ்சல் குறியீட்டை உள்ளிட்டு # அழுத்தவும்.'
              : 'Please enter all 6 digits of your PIN code before pressing pound.'
          );
        }
        return;
      }
      if (['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'].includes(digit)) {
        if (pinInput.length < 6) {
          const newPin = pinInput + digit;
          setPinInput(newPin);
          setPincodeError(null);
          // If 6 digits completed, auto-submit or wait for #
          if (newPin.length === 6) {
            handlePinSubmit(newPin);
          }
          return;
        }
      }
    }

    // Standard menu navigation submission to backend simulation
    try {
      setIsLoading(true);
      const res = await ivrSimulationService.sendInput({
        call_sid: callSid,
        digits: digit,
        current_menu: currentMenu,
        language: language,
      });

      setSimState(res);
      setCurrentMenu(res.current_menu);
      if (res.language) setLanguage(res.language);

      setTranscript((prev) => [
        ...prev,
        {
          id: `t-sys-${Date.now()}`,
          sender: 'system',
          text: res.speak_text,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          type: 'speech',
        },
      ]);

      speakText(pickSpeakText(res, res.language || language), res.language || language);
    } catch (err: any) {
      setErrorMessage(err.message || 'Keypad processing error.');
    } finally {
      setIsLoading(false);
    }
  };

  // Submit 6-digit PIN code to backend
  const handlePinSubmit = async (pincode: string) => {
    try {
      setIsLoading(true);
      setPincodeError(null);

      // 1. Resolve PIN code
      const pinRes = await ivrSimulationService.resolvePincode(pincode);
      setResolvedLocation(pinRes);

      // Add info to transcript
      setTranscript((prev) => [
        ...prev,
        {
          id: `t-pin-${Date.now()}`,
          sender: 'system',
          text: `📍 Postal PIN Resolved: ${pinRes.locality}, ${pinRes.district}, ${pinRes.state} (Approximate Area)`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          type: 'info',
        },
      ]);

      // 2. Submit to simulation state machine with resolved location
      const res = await ivrSimulationService.sendInput({
        call_sid: callSid,
        digits: pincode,
        current_menu: 'LOCATION_INPUT',
        language: language,
        location_data: {
          latitude: pinRes.latitude,
          longitude: pinRes.longitude,
          name: `${pinRes.locality}, ${pinRes.district}`,
        },
      });

      setSimState(res);
      setCurrentMenu(res.current_menu);
      setPinInput('');

      setTranscript((prev) => [
        ...prev,
        {
          id: `t-sys-${Date.now()}`,
          sender: 'system',
          text: res.speak_text,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          type: 'speech',
        },
      ]);

      speakText(pickSpeakText(res, language), language);
    } catch (err: any) {
      setPincodeError(err.message || 'PIN code could not be resolved. Please try village search.');
    } finally {
      setIsLoading(false);
    }
  };

  // Optional Geolocation detection
  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      setGeoStatus('denied');
      setTranscript((prev) => [
        ...prev,
        {
          id: `t-geo-${Date.now()}`,
          sender: 'system',
          text: '⚠️ Browser geolocation is unsupported on this device. Please enter your 6-digit PIN code.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          type: 'error',
        },
      ]);
      return;
    }

    setGeoStatus('detecting');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        setGeoStatus('granted');
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;

        setTranscript((prev) => [
          ...prev,
          {
            id: `t-geo-${Date.now()}`,
            sender: 'system',
            text: `📍 Device GPS Location Detected: Latitude ${lat.toFixed(4)}, Longitude ${lon.toFixed(4)}`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            type: 'info',
          },
        ]);

        try {
          setIsLoading(true);
          const res = await ivrSimulationService.sendInput({
            call_sid: callSid,
            digits: '*',
            current_menu: 'LOCATION_INPUT',
            language: language,
            location_data: {
              latitude: lat,
              longitude: lon,
              name: language === 'ta' ? 'சாதன ஜி.பி.எஸ் இருப்பிடம்' : 'Device GPS Location',
            },
          });

          setSimState(res);
          setCurrentMenu(res.current_menu);

          setTranscript((prev) => [
            ...prev,
            {
              id: `t-sys-${Date.now()}`,
              sender: 'system',
              text: res.speak_text,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
              type: 'speech',
            },
          ]);

          speakText(pickSpeakText(res, language), language);
        } catch (err: any) {
          setErrorMessage(err.message || 'Failed to retrieve facilities for coordinates.');
        } finally {
          setIsLoading(false);
        }
      },
      () => {
        setGeoStatus('denied');
        const deniedMsg =
          language === 'ta'
            ? 'இருப்பிட அனுமதி மறுக்கப்பட்டது. உங்கள் 6 இலக்க அஞ்சல் குறியீட்டை (PIN code) உள்ளிடவும்.'
            : 'Location permission denied. Please enter your 6-digit PIN code instead.';
        setTranscript((prev) => [
          ...prev,
          {
            id: `t-geo-${Date.now()}`,
            sender: 'system',
            text: `⚠️ ${deniedMsg}`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            type: 'error',
          },
        ]);
        speakText(deniedMsg, language);
      },
      { timeout: 8000 }
    );
  };

  // Village search fallback handler
  const handleVillageSelect = async (village: Village) => {
    setShowVillageModal(false);
    setTranscript((prev) => [
      ...prev,
      {
        id: `t-vil-${Date.now()}`,
        sender: 'system',
        text: `📍 Selected Village: ${village.name}, ${village.district}, ${village.state || ''}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        type: 'info',
      },
    ]);

    try {
      setIsLoading(true);
      const res = await ivrSimulationService.sendInput({
        call_sid: callSid,
        digits: village.name,
        current_menu: 'LOCATION_INPUT',
        language: language,
        location_data: {
          latitude: village.latitude,
          longitude: village.longitude,
          name: `${village.name}, ${village.district}`,
        },
      });

      setSimState(res);
      setCurrentMenu(res.current_menu);

      setTranscript((prev) => [
        ...prev,
        {
          id: `t-sys-${Date.now()}`,
          sender: 'system',
          text: res.speak_text,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          type: 'speech',
        },
      ]);

      speakText(pickSpeakText(res, language), language);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to find facilities near village.');
    } finally {
      setIsLoading(false);
    }
  };

  // Physical Keyboard Listener for DTMF keys
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept if user is typing in a search text input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      const key = e.key;
      if (['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '#'].includes(key)) {
        e.preventDefault();
        handleKeypadPress(key);
      } else if (key === 'Backspace' && currentMenu === 'LOCATION_INPUT') {
        e.preventDefault();
        setPinInput((prev) => prev.slice(0, -1));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeypadPress, currentMenu]);

  // Village search debounced query
  useEffect(() => {
    if (!villageSearchTerm.trim() || villageSearchTerm.length < 2) {
      setVillageSuggestions([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        setIsSearchingVillages(true);
        const results = await authService.searchVillages(villageSearchTerm.trim(), 10);
        setVillageSuggestions(results);
      } catch {
        setVillageSuggestions([]);
      } finally {
        setIsSearchingVillages(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [villageSearchTerm]);

  // Keypad button configuration
  const keypadButtons = [
    { digit: '1', sub: '.,\'' },
    { digit: '2', sub: 'ABC' },
    { digit: '3', sub: 'DEF' },
    { digit: '4', sub: 'GHI' },
    { digit: '5', sub: 'JKL' },
    { digit: '6', sub: 'MNO' },
    { digit: '7', sub: 'PQRS' },
    { digit: '8', sub: 'TUV' },
    { digit: '9', sub: 'WXYZ' },
    { digit: '*', sub: 'GPS' },
    { digit: '0', sub: 'MENU' },
    { digit: '#', sub: 'ENTER' },
  ];

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="bg-slate-800/90 backdrop-blur border-b border-slate-700/80 sticky top-0 z-30 px-4 py-3">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-xs sm:text-sm text-slate-400 hover:text-white transition px-2.5 py-1.5 rounded-lg hover:bg-slate-700/60"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to NALAM AI</span>
            </Link>
            <div className="h-4 w-px bg-slate-700" />
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-900/30">
                <Phone className="w-4 h-4 text-white" />
              </div>
              <div>
                <h1 className="text-base font-bold text-white leading-tight flex items-center gap-2">
                  NALAM AI Voice Helpline
                  <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                    Simulated IVR
                  </span>
                </h1>
                <p className="text-xs text-slate-400">Zero-Cost Voice Access for Rural Feature Phones</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Language Toggle */}
            <div className="flex items-center bg-slate-700/70 p-0.5 rounded-lg border border-slate-600/60">
              <button
                type="button"
                onClick={() => {
                  setLanguage('ta');
                  if (callStatus === 'IN_CALL') handleKeypadPress('1');
                }}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition ${
                  language === 'ta'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                தமிழ் (Tamil)
              </button>
              <button
                type="button"
                onClick={() => {
                  setLanguage('en');
                  if (callStatus === 'IN_CALL') handleKeypadPress('2');
                }}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition ${
                  language === 'en'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                English
              </button>
            </div>

            {/* Mute Button */}
            <button
              type="button"
              onClick={() => {
                const nextMute = !isMuted;
                setIsMuted(nextMute);
                if (nextMute) stopSpeech();
              }}
              className={`p-2 rounded-lg border transition ${
                isMuted
                  ? 'bg-amber-950/60 text-amber-300 border-amber-800/80'
                  : 'bg-slate-700/70 text-slate-300 border-slate-600/60 hover:text-white'
              }`}
              title={isMuted ? 'Unmute Spoken Audio' : 'Mute Spoken Audio'}
              aria-label={isMuted ? 'Unmute Audio' : 'Mute Audio'}
            >
              {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </header>

      {/* Zero-cost Public Notice Banner */}
      <div className="bg-emerald-950/40 border-b border-emerald-900/40 px-4 py-2">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-emerald-300 gap-2">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>
              <strong>Zero-Cost Public Helpline Simulation:</strong> Demonstrating phone-keypad healthcare search without internet or login. Connects to real Indian healthcare facilities database.
            </span>
          </div>
          <span className="hidden sm:inline font-mono text-emerald-400/80">Toll-Free: 1800-202-CARE</span>
        </div>
      </div>

      {/* Tamil TTS Availability Warning — only shown when no ta-IN voice is found */}
      {!speechAvailable && language === 'ta' && (
        <div className="bg-amber-950/60 border-b border-amber-800/60 px-4 py-2">
          <div className="max-w-7xl mx-auto flex items-center gap-2 text-xs text-amber-300">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Tamil voice not available:</strong> Your browser does not have a Tamil (ta-IN) text-to-speech voice installed. The transcript is shown in Tamil below. For spoken Tamil audio, install a Tamil TTS voice in your OS settings, or switch to <strong>English</strong> mode above.
            </span>
          </div>
        </div>
      )}

      {/* Tamil TTS Availability Warning — only shown when no ta-IN voice is found */}
      {!speechAvailable && language === 'ta' && (
        <div className="bg-amber-950/60 border-b border-amber-800/60 px-4 py-2">
          <div className="max-w-7xl mx-auto flex items-center gap-2 text-xs text-amber-300">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Tamil voice not available:</strong> Your browser does not have a Tamil (ta-IN) text-to-speech voice installed. The transcript is displayed in Tamil below. For spoken Tamil audio, install a Tamil TTS voice or switch to English mode.
            </span>
          </div>
        </div>
      )}

      {/* Main Interactive Screen Grid */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Simulated Phone Handset (Cols 1-5) */}
        <div className="lg:col-span-5 flex flex-col items-center">
          <div className="w-full max-w-sm bg-gradient-to-b from-slate-800 to-slate-850 border-2 border-slate-700 rounded-3xl p-5 shadow-2xl relative">
            {/* Phone Speaker Notch */}
            <div className="w-20 h-1.5 bg-slate-700 rounded-full mx-auto mb-4" />

            {/* Phone Screen Display */}
            <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 mb-5 shadow-inner">
              {/* Screen Top Status Bar */}
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-2 border-b border-slate-800/60 pb-1.5">
                <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  NALAM AI Net
                </span>
                <span className="flex items-center gap-2">
                  {callStatus === 'IN_CALL' && (
                    <span className="text-emerald-300 font-mono flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatTime(callTimer)}
                    </span>
                  )}
                  <span>4G VoLTE</span>
                </span>
              </div>

              {/* Call State Title */}
              <div className="text-center py-2">
                {callStatus === 'IDLE' && (
                  <div>
                    <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">Ready to Call</div>
                    <div className="text-lg font-bold text-white mt-0.5">1800-202-CARE</div>
                    <p className="text-[11px] text-slate-400 mt-1">Press "Start Call" to begin simulated IVR</p>
                  </div>
                )}

                {callStatus === 'DIALING' && (
                  <div className="animate-pulse">
                    <div className="text-xs uppercase tracking-wider text-amber-400 font-semibold">Connecting...</div>
                    <div className="text-lg font-bold text-white mt-0.5">1800-202-2273</div>
                    <p className="text-[11px] text-slate-400 mt-1">Simulating cellular exchange connection</p>
                  </div>
                )}

                {callStatus === 'IN_CALL' && (
                  <div>
                    <div className="flex items-center justify-center gap-1.5 text-xs uppercase tracking-wider text-emerald-400 font-semibold">
                      <span className="w-2 h-2 rounded-full bg-emerald-500" />
                      Call in Progress
                    </div>
                    <div className="text-base font-bold text-white mt-0.5">
                      {language === 'ta' ? 'NALAM AI சுகாதார உதவி' : 'NALAM AI Health Desk'}
                    </div>

                    {/* Speech Waveform Animation */}
                    <div className="h-6 flex items-center justify-center gap-1 my-2">
                      {isSpeaking ? (
                        <>
                          <div className="w-1 bg-emerald-400 h-3 animate-bounce" style={{ animationDelay: '0ms' }} />
                          <div className="w-1 bg-emerald-400 h-5 animate-bounce" style={{ animationDelay: '150ms' }} />
                          <div className="w-1 bg-emerald-400 h-2 animate-bounce" style={{ animationDelay: '300ms' }} />
                          <div className="w-1 bg-emerald-400 h-6 animate-bounce" style={{ animationDelay: '75ms' }} />
                          <div className="w-1 bg-emerald-400 h-4 animate-bounce" style={{ animationDelay: '225ms' }} />
                        </>
                      ) : (
                        <span className="text-[11px] text-slate-400 italic">Listening for keypad input...</span>
                      )}
                    </div>

                    <div className="text-xs text-slate-300 font-mono bg-slate-900/80 px-2 py-1 rounded border border-slate-800">
                      Menu: <span className="text-emerald-400 font-semibold">{currentMenu}</span>
                    </div>
                  </div>
                )}

                {callStatus === 'ENDED' && (
                  <div>
                    <div className="text-xs uppercase tracking-wider text-rose-400 font-semibold">Call Disconnected</div>
                    <div className="text-base font-bold text-white mt-0.5">Call Summary</div>
                    <p className="text-[11px] text-slate-400 mt-1">Duration: {formatTime(callTimer)}</p>
                  </div>
                )}
              </div>

              {/* PIN Code Keypad Input Buffer */}
              {callStatus === 'IN_CALL' && currentMenu === 'LOCATION_INPUT' && (
                <div className="mt-2 pt-2 border-t border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase font-semibold text-center mb-1">
                    Enter 6-Digit Indian PIN Code:
                  </div>
                  <div className="flex items-center justify-center gap-1.5 font-mono text-base font-bold">
                    {[0, 1, 2, 3, 4, 5].map((idx) => (
                      <span
                        key={idx}
                        className={`w-7 h-8 flex items-center justify-center rounded border ${
                          pinInput[idx]
                            ? 'bg-emerald-950 text-emerald-300 border-emerald-600 shadow-sm'
                            : 'bg-slate-900 text-slate-600 border-slate-800'
                        }`}
                      >
                        {pinInput[idx] || '_'}
                      </span>
                    ))}
                  </div>

                  {pincodeError && (
                    <div className="text-[11px] text-rose-400 text-center mt-1.5 flex items-center justify-center gap-1">
                      <AlertCircle className="w-3 h-3" />
                      {pincodeError}
                    </div>
                  )}

                  <div className="flex items-center justify-between gap-1 mt-2 text-[10px]">
                    <button
                      type="button"
                      onClick={() => setPinInput((prev) => prev.slice(0, -1))}
                      disabled={pinInput.length === 0}
                      className="px-2 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 rounded text-slate-300 transition"
                    >
                      ⌫ Backspace
                    </button>
                    <button
                      type="button"
                      onClick={() => setPinInput('')}
                      disabled={pinInput.length === 0}
                      className="px-2 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 rounded text-slate-300 transition"
                    >
                      Clear
                    </button>
                    <button
                      type="button"
                      onClick={() => pinInput.length === 6 && handlePinSubmit(pinInput)}
                      disabled={pinInput.length !== 6}
                      className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white rounded font-semibold transition"
                    >
                      Submit (#)
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* 12-Button Telephone Keypad */}
            <div className="grid grid-cols-3 gap-3 mb-5" role="group" aria-label="Telephone Keypad">
              {keypadButtons.map((btn) => (
                <button
                  key={btn.digit}
                  type="button"
                  onClick={() => handleKeypadPress(btn.digit)}
                  disabled={isLoading}
                  className="bg-slate-700/80 hover:bg-slate-600/90 active:scale-95 active:bg-emerald-600 text-white font-bold h-13 rounded-2xl flex flex-col items-center justify-center border border-slate-600/60 shadow-md transition disabled:opacity-50"
                  aria-label={`Digit ${btn.digit}`}
                >
                  <span className="text-xl leading-none text-white font-mono">{btn.digit}</span>
                  <span className="text-[9px] text-slate-300/80 tracking-widest font-normal uppercase mt-0.5">
                    {btn.sub}
                  </span>
                </button>
              ))}
            </div>

            {/* Call Action Bar (Start / End / Menu / Repeat) */}
            <div className="grid grid-cols-2 gap-3 mb-3">
              {callStatus !== 'IN_CALL' ? (
                <button
                  type="button"
                  onClick={handleStartCall}
                  disabled={isLoading}
                  className="col-span-2 py-3 bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-900/40 transition"
                >
                  <PhoneCall className="w-5 h-5" />
                  <span>Start Call (டயல் செய்)</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleEndCall}
                  className="col-span-2 py-3 bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-rose-900/40 transition"
                >
                  <PhoneOff className="w-5 h-5" />
                  <span>End Call (முடிக்க)</span>
                </button>
              )}

              {/* Repeat Button (Press 9) */}
              <button
                type="button"
                onClick={() => handleKeypadPress('9')}
                disabled={callStatus !== 'IN_CALL' || isLoading}
                className="py-2.5 bg-slate-700/80 hover:bg-slate-600 active:bg-slate-700 disabled:opacity-40 text-slate-200 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 border border-slate-600/60 transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Repeat (9)</span>
              </button>

              {/* Main Menu Button (Press 0) */}
              <button
                type="button"
                onClick={() => handleKeypadPress('0')}
                disabled={callStatus !== 'IN_CALL' || isLoading}
                className="py-2.5 bg-slate-700/80 hover:bg-slate-600 active:bg-slate-700 disabled:opacity-40 text-slate-200 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 border border-slate-600/60 transition"
              >
                <ChevronRight className="w-3.5 h-3.5" />
                <span>Main Menu (0)</span>
              </button>
            </div>

            {/* Quick helper shortcuts */}
            <div className="pt-3 border-t border-slate-700/60 flex items-center justify-between text-[11px] text-slate-400">
              <span>Shortcuts: Press 0-9 on keyboard</span>
              <span className="font-mono text-emerald-400/90">Web Audio DTMF</span>
            </div>
          </div>
        </div>

        {/* Right Column: Live Spoken Transcript & Interactive Context (Cols 6-12) */}
        <div className="lg:col-span-7 flex flex-col gap-5">
          {/* Active Interaction Context Card */}
          <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-4 sm:p-5 shadow-lg">
            <div className="flex items-center justify-between gap-3 mb-3 pb-2 border-b border-slate-700/70">
              <div className="flex items-center gap-2">
                <Hospital className="w-5 h-5 text-emerald-400" />
                <h2 className="text-sm sm:text-base font-bold text-white">
                  {language === 'ta' ? 'அழைப்பு வழிநடத்துதல் மற்றும் சேவைகள்' : 'Call Guidance & Healthcare Actions'}
                </h2>
              </div>
              <span className="text-xs font-mono text-slate-400">
                Menu State: <strong className="text-emerald-300">{currentMenu}</strong>
              </span>
            </div>

            {/* Option 1 Sub-panel: Location Selection */}
            {currentMenu === 'LOCATION_INPUT' && (
              <div className="space-y-4">
                <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-3.5">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-300 mb-1 flex items-center gap-1.5">
                    <MapPin className="w-4 h-4 text-emerald-400" />
                    {language === 'ta' ? 'இருப்பிடத்தைத் தேர்ந்தெடுப்பது எப்படி?' : 'How to Provide Location:'}
                  </h3>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {language === 'ta'
                      ? '1. உங்கள் தொலைபேசி கீபேடில் 6 இலக்க அஞ்சல் குறியீட்டை (PIN code) உள்ளிட்டு # அழுத்தவும் (எ.கா. 637211#).\n2. அல்லது சாதனத்தின் GPS இருப்பிடத்தைப் பயன்படுத்த * அழுத்தவும்.\n3. அல்லது கிராமத்தின் பெயரைத் தேட 4-ஐ அழுத்தவும்.'
                      : '1. Enter your 6-digit Indian PIN code on the keypad and press pound (e.g., 637211#).\n2. Or press star (*) to detect your device GPS location.\n3. Or press 4 to search by village/locality name.'}
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Optional Browser GPS Detection */}
                  <button
                    type="button"
                    onClick={handleDetectLocation}
                    disabled={callStatus !== 'IN_CALL' || isLoading}
                    className="p-3 rounded-xl bg-slate-900/90 hover:bg-slate-700/80 border border-slate-700 hover:border-emerald-500 text-left transition flex items-start gap-3 disabled:opacity-50"
                  >
                    <div className="p-2 rounded-lg bg-emerald-950 text-emerald-400 border border-emerald-800 shrink-0">
                      <Navigation className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white flex items-center gap-1">
                        {language === 'ta' ? 'ஜி.பி.எஸ் இருப்பிடம்' : 'Detect GPS Location'}
                        <span className="text-[10px] text-emerald-400 font-mono">(Press *)</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {geoStatus === 'detecting'
                          ? 'Detecting...'
                          : geoStatus === 'denied'
                          ? 'Permission denied'
                          : 'Optional with explicit permission'}
                      </p>
                    </div>
                  </button>

                  {/* Village / Locality Fallback */}
                  <button
                    type="button"
                    onClick={() => setShowVillageModal(true)}
                    disabled={callStatus !== 'IN_CALL' || isLoading}
                    className="p-3 rounded-xl bg-slate-900/90 hover:bg-slate-700/80 border border-slate-700 hover:border-emerald-500 text-left transition flex items-start gap-3 disabled:opacity-50"
                  >
                    <div className="p-2 rounded-lg bg-indigo-950 text-indigo-400 border border-indigo-800 shrink-0">
                      <Search className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white flex items-center gap-1">
                        {language === 'ta' ? 'கிராமப் பெயர் தேடல்' : 'Village Name Search'}
                        <span className="text-[10px] text-indigo-400 font-mono">(Press 4)</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {language === 'ta' ? 'அஞ்சல் குறியீடு தெரியாவிட்டால்' : 'Fallback if PIN code unknown'}
                      </p>
                    </div>
                  </button>
                </div>
              </div>
            )}

            {/* Option 1 Results Sub-panel: Healthcare Facilities Display */}
            {currentMenu === 'FACILITIES_RESULTS' && simState?.facilities && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-300 bg-slate-900/70 p-2.5 rounded-lg border border-slate-700">
                  <span>
                    📍 Location: <strong>{simState.location_name}</strong>
                    {simState.is_approximate && (
                      <span className="ml-1 text-amber-400 text-[10px] uppercase font-semibold">
                        (Approximate Postal Area)
                      </span>
                    )}
                  </span>
                  <span className="text-emerald-400 font-semibold font-mono">
                    Found {simState.facilities.length} Nearest
                  </span>
                </div>

                <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                  {simState.facilities.map((fac, idx) => (
                    <div
                      key={fac.id || idx}
                      className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-3 flex items-start justify-between gap-3"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-white">
                            {idx + 1}. {fac.name}
                          </span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                            {fac.facility_type}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400">{fac.address || `${fac.district}, ${fac.state}`}</p>
                      </div>

                      <div className="text-right shrink-0">
                        <div className="text-sm font-bold font-mono text-emerald-400">
                          {fac.distance_km.toFixed(1)} km
                        </div>
                        <div className="text-[10px] text-slate-500">distance</div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex items-center justify-between text-xs pt-1">
                  <button
                    type="button"
                    onClick={() => handleKeypadPress('1')}
                    className="text-emerald-400 hover:text-emerald-300 font-semibold flex items-center gap-1"
                  >
                    <span>Hear Next Facility (Press 1)</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleKeypadPress('0')}
                    className="text-slate-400 hover:text-white"
                  >
                    Back to Main Menu (Press 0)
                  </button>
                </div>
              </div>
            )}

            {/* Option 2 Sub-panel: Services Overview */}
            {currentMenu === 'SERVICES_INFO' && (
              <div className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                  <div className="bg-slate-900/80 border border-slate-700 p-2.5 rounded-lg">
                    <strong className="text-emerald-400 block mb-0.5">Primary Health Centres (PHC)</strong>
                    <span className="text-slate-300 text-[11px]">
                      Outpatient diagnosis, antenatal checkups, and free essential medicines distribution.
                    </span>
                  </div>
                  <div className="bg-slate-900/80 border border-slate-700 p-2.5 rounded-lg">
                    <strong className="text-emerald-400 block mb-0.5">Community Health Centres (CHC)</strong>
                    <span className="text-slate-300 text-[11px]">
                      30-bed hospital care, emergency surgical triage, pediatric and obstetric specialists.
                    </span>
                  </div>
                  <div className="bg-slate-900/80 border border-slate-700 p-2.5 rounded-lg">
                    <strong className="text-emerald-400 block mb-0.5">Health Sub-Centres</strong>
                    <span className="text-slate-300 text-[11px]">
                      Village first-contact primary healthcare, routine immunization, and maternal advice.
                    </span>
                  </div>
                  <div className="bg-slate-900/80 border border-slate-700 p-2.5 rounded-lg">
                    <strong className="text-emerald-400 block mb-0.5">ASHA Community Workers</strong>
                    <span className="text-slate-300 text-[11px]">
                      Door-to-door consultations, institutional delivery support, and medical escalations.
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <button
                    type="button"
                    onClick={() => handleKeypadPress('0')}
                    className="text-xs text-slate-400 hover:text-white"
                  >
                    Return to Main Menu (Press 0)
                  </button>
                </div>
              </div>
            )}

            {/* Option 3 Sub-panel: Emergency Assistance Contacts */}
            {currentMenu === 'ASSISTANCE_INFO' && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                  <div className="bg-slate-900/90 border border-rose-900/60 p-2.5 rounded-xl">
                    <div className="text-rose-400 font-bold text-base font-mono">112</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">National Emergency</div>
                  </div>
                  <div className="bg-slate-900/90 border border-emerald-900/60 p-2.5 rounded-xl">
                    <div className="text-emerald-400 font-bold text-base font-mono">108</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">Free Ambulance</div>
                  </div>
                  <div className="bg-slate-900/90 border border-indigo-900/60 p-2.5 rounded-xl">
                    <div className="text-indigo-400 font-bold text-base font-mono">104</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">Health Helpline</div>
                  </div>
                  <div className="bg-slate-900/90 border border-amber-900/60 p-2.5 rounded-xl">
                    <div className="text-amber-400 font-bold text-xs font-mono">1800-202-CARE</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">NALAM AI Desk</div>
                  </div>
                </div>
                <div className="text-right">
                  <button
                    type="button"
                    onClick={() => handleKeypadPress('0')}
                    className="text-xs text-slate-400 hover:text-white"
                  >
                    Return to Main Menu (Press 0)
                  </button>
                </div>
              </div>
            )}

            {/* Main Menu Quick Navigation Helper */}
            {currentMenu === 'MAIN_MENU' && (
              <div className="space-y-2">
                <p className="text-xs text-slate-300">
                  {language === 'ta'
                    ? 'தொலைபேசி கீபேடில் பொருத்தமான எண்ணை அழுத்தவும்:'
                    : 'Press the corresponding digit on your telephone keypad:'}
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                  <button
                    type="button"
                    onClick={() => handleKeypadPress('1')}
                    className="p-2.5 rounded-lg bg-slate-900/90 hover:bg-slate-700/80 border border-slate-700 text-left transition flex items-center justify-between"
                  >
                    <span className="font-semibold text-white">1. Find Facilities</span>
                    <span className="font-mono text-emerald-400 font-bold">[ 1 ]</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleKeypadPress('2')}
                    className="p-2.5 rounded-lg bg-slate-900/90 hover:bg-slate-700/80 border border-slate-700 text-left transition flex items-center justify-between"
                  >
                    <span className="font-semibold text-white">2. Health Services</span>
                    <span className="font-mono text-emerald-400 font-bold">[ 2 ]</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleKeypadPress('3')}
                    className="p-2.5 rounded-lg bg-slate-900/90 hover:bg-slate-700/80 border border-slate-700 text-left transition flex items-center justify-between"
                  >
                    <span className="font-semibold text-white">3. Help & Contacts</span>
                    <span className="font-mono text-emerald-400 font-bold">[ 3 ]</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Live Call Transcript / Accessibility Screen Reader Card */}
          <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-4 sm:p-5 flex-1 flex flex-col shadow-lg">
            <div className="flex items-center justify-between gap-3 mb-3 pb-2 border-b border-slate-700/70">
              <div className="flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">Live Call Spoken Transcript</h3>
              </div>
              <div className="flex items-center gap-2">
                {isSpeaking && (
                  <span className="text-[11px] text-emerald-400 font-mono animate-pulse flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    Speaking Audio...
                  </span>
                )}
                <span className="text-[11px] text-slate-400 font-mono">
                  {transcript.length} messages
                </span>
              </div>
            </div>

            {/* Transcript Messages Container */}
            <div
              className="flex-1 min-h-[220px] max-h-[360px] overflow-y-auto space-y-2.5 pr-1 font-sans text-xs"
              role="log"
              aria-live="polite"
              aria-label="Telephone call spoken transcript"
            >
              {transcript.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 py-10">
                  <Phone className="w-8 h-8 mb-2 opacity-40" />
                  <p>Click "Start Call" to begin voice simulation.</p>
                  <p className="text-[11px] text-slate-600 mt-1">Live audio and keypad actions will appear here.</p>
                </div>
              ) : (
                transcript.map((item) => (
                  <div
                    key={item.id}
                    className={`p-3 rounded-xl border leading-relaxed ${
                      item.sender === 'user'
                        ? 'bg-slate-700/60 border-slate-600 text-slate-200 ml-8'
                        : item.type === 'error'
                        ? 'bg-rose-950/40 border-rose-800/60 text-rose-200'
                        : item.type === 'info'
                        ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-200'
                        : 'bg-slate-900/90 border-slate-750 text-white'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1 text-[10px] text-slate-400 font-mono">
                      <span className="font-semibold text-slate-300">
                        {item.sender === 'user' ? '📱 Caller Keypad' : '🔊 NALAM AI Voice'}
                      </span>
                      <span>{item.timestamp}</span>
                    </div>
                    <div className="whitespace-pre-wrap">{item.text}</div>
                  </div>
                ))
              )}
              <div ref={transcriptEndRef} />
            </div>
          </div>
        </div>
      </main>

      {/* Village Search Fallback Modal */}
      {showVillageModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-850 border border-slate-700 rounded-2xl max-w-lg w-full p-5 shadow-2xl">
            <div className="flex items-center justify-between gap-3 mb-4 pb-2 border-b border-slate-700">
              <div className="flex items-center gap-2">
                <Search className="w-5 h-5 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">
                  {language === 'ta' ? 'கிராமப் பெயர் மூலம் தேடுக' : 'Search by Village or Locality'}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowVillageModal(false)}
                className="text-slate-400 hover:text-white p-1"
              >
                ✕
              </button>
            </div>

            <div className="relative mb-3">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                value={villageSearchTerm}
                onChange={(e) => setVillageSearchTerm(e.target.value)}
                placeholder={
                  language === 'ta'
                    ? 'கிராமம் அல்லது நகரத்தின் பெயரை உள்ளிடவும் (எ.கா: Molasi, Tiruchengode)...'
                    : 'Type village, town, or city name (e.g. Molasi, Rampur)...'
                }
                className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-9 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                autoFocus
              />
              {isSearchingVillages && (
                <div className="absolute right-3 top-3 text-[11px] text-slate-400">Searching...</div>
              )}
            </div>

            {/* Suggestions list */}
            <div className="max-h-52 overflow-y-auto space-y-1.5 mb-4 pr-1 text-xs">
              {villageSuggestions.length === 0 ? (
                <div className="text-center py-6 text-slate-500">
                  {villageSearchTerm.length < 2
                    ? 'Type at least 2 letters to search official Indian settlements.'
                    : 'No matching settlements found. Try another spelling.'}
                </div>
              ) : (
                villageSuggestions.map((v) => (
                  <button
                    key={v.id}
                    type="button"
                    onClick={() => handleVillageSelect(v)}
                    className="w-full text-left p-2.5 rounded-lg bg-slate-900/80 hover:bg-emerald-950/60 border border-slate-700 hover:border-emerald-600 transition flex items-center justify-between"
                  >
                    <div>
                      <span className="font-bold text-white">{v.name}</span>
                      <span className="text-slate-400 ml-2 text-[11px]">
                        {v.subdistrict ? `${v.subdistrict}, ` : ''}{v.district}, {v.state}
                      </span>
                    </div>
                    <span className="text-emerald-400 text-[11px] font-semibold shrink-0">Select</span>
                  </button>
                ))
              )}
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setShowVillageModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IVRPage;
